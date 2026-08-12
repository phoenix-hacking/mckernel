#!/usr/bin/env python3
"""Capture active host-module negative-errno sites from compiler evidence.

The legacy host-module build is heavily conditional.  Looking for ``-EINVAL``
and similar spellings in the source tree therefore counts inactive branches and
headers that are not part of the compiled module.  This tool instead consumes
the exact Kbuild ``.cmd`` records emitted by the Rocky build, reconstructs a
side-effect-free preprocessing command, and scans only lines attributed by the
preprocessor to the effective target source.

No command text is ever evaluated by a shell.  Kbuild command text is parsed
with :mod:`shlex`, shell substitution is rejected, and the compiler is invoked
with an argument vector.  The standalone Rust helper has no C preprocessor, so
its exact source bytes are scanned directly while retaining its recorded
``.cmd`` and compiler provenance.
"""

import argparse
import bisect
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1
PROFILE = "compiler-backed-active-host-module-failure-sites-v1"
ERRNO_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])-\s*(?:\(\s*)*(E[A-Z][A-Z0-9_]*)\b"
)
LINE_MARKER_PATTERN = re.compile(
    r'^\s*#\s*(?:line\s+)?(?P<line>[0-9]+)\s+"(?P<file>(?:\\.|[^"\\])*)"'
    r"(?:\s+[0-9]+)*\s*$"
)
ASSIGNMENT_PATTERN = re.compile(r"^(?P<kind>cmd|source)_(?P<key>.+?)\s*:=\s*(?P<value>.*)$")
CONTROL_TOKENS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<", "<>", "&>"}
COMPILE_SEPARATORS = {";", "&&", "||", "|", "&"}
DEPENDENCY_FLAGS = {"-M", "-MM", "-MD", "-MMD", "-MG", "-MP"}
DEPENDENCY_VALUE_FLAGS = {"-MF", "-MT", "-MQ", "-MJ"}
OUTPUT_VALUE_FLAGS = {"-o", "--output"}


# This is the exact x86_64/Rust-helper source closure selected by the current
# Rocky validation build.  Missing records fail the capture instead of silently
# shrinking the oracle.  Assembly inputs do not contain errno-return sites and
# are tracked separately by the assembly policy.
EXPECTED_SOURCES = (
    ("ihk", "c", "ihk/linux/core/host_driver.c", "ihk/linux/core/.host_driver.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mem_alloc.c", "ihk/linux/core/.mem_alloc.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mm.c", "ihk/linux/core/.mm.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mikc.c", "ihk/linux/core/.mikc.o.cmd"),
    ("ihk", "c", "ihk/ikc/linux.c", "ihk/ikc/.linux.o.cmd"),
    ("ihk", "c", "ihk/ikc/master.c", "ihk/ikc/.master.o.cmd"),
    ("ihk", "c", "ihk/ikc/queue.c", "ihk/ikc/.queue.o.cmd"),
    (
        "ihk_smp_x86_64",
        "c",
        "ihk/linux/driver/smp/arch/x86_64/smp-arch-driver.c",
        "ihk/linux/driver/smp/arch/x86_64/.smp-arch-driver.o.cmd",
    ),
    (
        "ihk_smp_x86_64",
        "c",
        "ihk/linux/driver/smp/smp-driver.c",
        "ihk/linux/driver/smp/.smp-driver.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/driver.c",
        "executer/kernel/mcctrl/.driver.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/control.c",
        "executer/kernel/mcctrl/.control.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/syscall.c",
        "executer/kernel/mcctrl/.syscall.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/procfs.c",
        "executer/kernel/mcctrl/.procfs.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/sysfs.c",
        "executer/kernel/mcctrl/.sysfs.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/futex.c",
        "executer/kernel/mcctrl/.futex.o.cmd",
    ),
    (
        "mcctrl",
        "rust",
        "executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
        "executer/kernel/mcctrl/rust/.mcctrl_helpers.o.cmd",
    ),
)


class CaptureError(RuntimeError):
    """Raised when compiler-backed evidence is absent or ambiguous."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def file_digest(path):
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CaptureError("cannot read evidence file {0}: {1}".format(path, exc))
    return {"bytes": len(data), "sha256": sha256_bytes(data)}, data


def resolved(path):
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise CaptureError("cannot resolve path {0}: {1}".format(path, exc))


def require_within(path, root, label):
    candidate = str(resolved(path))
    base = str(resolved(root))
    try:
        common = os.path.commonpath((candidate, base))
    except ValueError:
        common = ""
    if common != base:
        raise CaptureError("{0} escapes {1}: {2}".format(label, root, path))


def unfold_make_lines(text):
    # Kbuild writes physical continuations with a backslash immediately before
    # the newline.  Preserve all other backslashes for shlex to interpret.
    return re.sub(r"\\\r?\n[ \t]*", " ", text)


def reject_shell_expansion(value, label):
    if "\x00" in value or "\n" in value or "\r" in value:
        raise CaptureError("{0} contains a control character".format(label))
    for spelling in ("`", "$(", "${", "<(", ">("):
        if spelling in value:
            raise CaptureError("{0} contains forbidden shell expansion {1!r}".format(label, spelling))
    if "$" in value:
        raise CaptureError("{0} contains an unresolved shell variable".format(label))


def shell_words(value, label):
    reject_shell_expansion(value, label)
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError as exc:
        raise CaptureError("cannot parse {0}: {1}".format(label, exc))


def parse_kbuild_cmd_bytes(data, display_path="<memory>"):
    """Return one safely tokenized compiler command and declared source."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaptureError("{0} is not UTF-8: {1}".format(display_path, exc))
    if len(data) > 4 * 1024 * 1024:
        raise CaptureError("{0} is implausibly large".format(display_path))

    assignments = {"cmd": {}, "source": {}}
    for line in unfold_make_lines(text).splitlines():
        match = ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        kind = match.group("kind")
        key = match.group("key").strip()
        if key in assignments[kind]:
            raise CaptureError("duplicate {0}_{1} assignment in {2}".format(kind, key, display_path))
        assignments[kind][key] = match.group("value").strip()

    if len(assignments["cmd"]) != 1:
        raise CaptureError("{0} must contain exactly one cmd_ assignment".format(display_path))
    key, command_text = next(iter(assignments["cmd"].items()))
    if key not in assignments["source"]:
        raise CaptureError("{0} has no source_ assignment matching cmd_{1}".format(display_path, key))
    if len(assignments["source"]) != 1:
        raise CaptureError("{0} must contain exactly one source_ assignment".format(display_path))

    source_words = shell_words(assignments["source"][key], "source_ assignment")
    if len(source_words) != 1 or source_words[0] in CONTROL_TOKENS:
        raise CaptureError("{0} source_ assignment is not one literal path".format(display_path))

    all_words = shell_words(command_text, "cmd_ assignment")
    if not all_words:
        raise CaptureError("{0} has an empty cmd_ assignment".format(display_path))
    split_at = len(all_words)
    separator = None
    for index, word in enumerate(all_words):
        if word in COMPILE_SEPARATORS:
            split_at = index
            separator = word
            break
        if word in CONTROL_TOKENS:
            raise CaptureError("compiler command in {0} contains redirection".format(display_path))
    if separator not in (None, ";"):
        raise CaptureError("compiler command in {0} is joined with {1!r}".format(display_path, separator))
    compiler_argv = all_words[:split_at]
    suffix = all_words[split_at:]
    if len(compiler_argv) < 2:
        raise CaptureError("compiler command in {0} is incomplete".format(display_path))
    if compiler_argv[0].startswith("-") or "=" in compiler_argv[0]:
        raise CaptureError("compiler executable in {0} is not literal".format(display_path))
    for word in compiler_argv:
        if word.startswith("@"):
            raise CaptureError("compiler response files are not captured: {0}".format(word))

    return {
        "assignment_key": key,
        "command_text_sha256": sha256_bytes(command_text.encode("utf-8")),
        "compile_argv": compiler_argv,
        "declared_source": source_words[0],
        "post_compile_token_count": len(suffix),
        "post_compile_tokens_sha256": sha256_bytes(canonical_bytes(suffix)),
    }


def parse_recorded_compile_argv_bytes(data, display_path="<memory>"):
    """Parse the exact argv recorded for the custom Rust compilation."""

    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CaptureError(
            "cannot parse recorded compiler argv {0}: {1}".format(display_path, exc)
        )
    if not isinstance(value, list) or len(value) < 2:
        raise CaptureError(
            "{0} must contain one non-empty compiler argv array".format(display_path)
        )
    for index, word in enumerate(value):
        if not isinstance(word, str) or not word or "\x00" in word:
            raise CaptureError(
                "{0} has an invalid argv element at {1}".format(display_path, index)
            )
        if word in CONTROL_TOKENS:
            raise CaptureError("{0} contains a shell control token".format(display_path))
    return value


def parse_kbuild_cmd(path):
    digest, data = file_digest(path)
    parsed = parse_kbuild_cmd_bytes(data, str(path))
    parsed["file"] = digest
    return parsed


def path_from_command(value, cwd):
    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return resolved(path)


def verify_command_source(command, expected_source, cwd, display_path):
    declared = path_from_command(command["declared_source"], cwd)
    expected = resolved(expected_source)
    if declared != expected:
        raise CaptureError(
            "source_ assignment in {0} names {1}, expected {2}".format(display_path, declared, expected)
        )

    matches = []
    for index, word in enumerate(command["compile_argv"][1:], 1):
        if word.startswith("-"):
            continue
        try:
            candidate = path_from_command(word, cwd)
        except CaptureError:
            continue
        if candidate == expected:
            matches.append(index)
    if len(matches) != 1:
        raise CaptureError(
            "compiler command in {0} contains the effective source {1} times".format(
                display_path, len(matches)
            )
        )
    return matches[0]


def compiler_provenance(executable, environment=None):
    environment = environment or os.environ
    if os.path.isabs(executable):
        invoked = Path(executable)
    else:
        found = shutil.which(executable, path=environment.get("PATH"))
        if not found:
            raise CaptureError("compiler executable is unavailable: {0}".format(executable))
        invoked = Path(found)
    launcher = resolved(invoked)
    if not launcher.is_file():
        raise CaptureError("compiler executable is not a regular file: {0}".format(launcher))
    actual = launcher
    version_first_line = None
    version_stderr_sha256 = None
    version_stdout_sha256 = None
    if invoked.name == "rustc":
        try:
            sysroot_result = subprocess.run(
                [str(invoked), "--print", "sysroot"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            version_result = subprocess.run(
                [str(invoked), "-Vv"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureError("cannot resolve rustc provenance: {0}".format(exc))
        if sysroot_result.returncode != 0 or version_result.returncode != 0:
            raise CaptureError("recorded rustc cannot report its sysroot and version")
        sysroot_text = sysroot_result.stdout.decode("utf-8", errors="strict").strip()
        if not sysroot_text or "\n" in sysroot_text or "\r" in sysroot_text:
            raise CaptureError("recorded rustc returned an invalid sysroot")
        actual = resolved(Path(sysroot_text) / "bin/rustc")
        if not actual.is_file():
            raise CaptureError("rustc sysroot compiler is missing: {0}".format(actual))
        version_lines = version_result.stdout.decode("utf-8", errors="replace").splitlines()
        if not version_lines:
            raise CaptureError("recorded rustc returned no version output")
        version_first_line = version_lines[0]
        version_stdout_sha256 = sha256_bytes(version_result.stdout)
        version_stderr_sha256 = sha256_bytes(version_result.stderr)
    else:
        try:
            version_result = subprocess.run(
                [str(launcher), "--version"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureError("cannot capture compiler version: {0}".format(exc))
        version_lines = version_result.stdout.decode("utf-8", errors="replace").splitlines()
        if version_result.returncode != 0 or not version_lines:
            raise CaptureError("recorded compiler cannot report its version")
        version_first_line = version_lines[0]
        version_stdout_sha256 = sha256_bytes(version_result.stdout)
        version_stderr_sha256 = sha256_bytes(version_result.stderr)

    digest, _ = file_digest(actual)
    result = {
        "invoked_as": executable,
        "resolved_path": str(actual),
        "bytes": digest["bytes"],
        "sha256": digest["sha256"],
        "version_first_line": version_first_line,
        "version_stderr_sha256": version_stderr_sha256,
        "version_stdout_sha256": version_stdout_sha256,
    }
    if launcher != actual:
        launcher_digest, _ = file_digest(launcher)
        result["launcher"] = {
            "bytes": launcher_digest["bytes"],
            "resolved_path": str(launcher),
            "sha256": launcher_digest["sha256"],
        }
    return result


def reconstruct_preprocess_argv(command, source_index):
    """Turn the recorded compilation argv into a read-only preprocessing argv."""

    original = command["compile_argv"]
    result = [original[0]]
    source_word = original[source_index]
    index = 1
    while index < len(original):
        word = original[index]
        if index == source_index:
            index += 1
            continue
        if word in ("-c", "-S", "-E", "-fdirectives-only") or word in DEPENDENCY_FLAGS:
            index += 1
            continue
        if word in DEPENDENCY_VALUE_FLAGS or word in OUTPUT_VALUE_FLAGS:
            if index + 1 >= len(original):
                raise CaptureError("compiler flag {0} lacks its value".format(word))
            index += 2
            continue
        if any(word.startswith(flag) and word != flag for flag in DEPENDENCY_VALUE_FLAGS):
            index += 1
            continue
        if word.startswith("-o") and word != "-o":
            index += 1
            continue
        if word.startswith("--output="):
            index += 1
            continue
        if word.startswith("-Wp,-MD,") or word.startswith("-Wp,-MMD,"):
            index += 1
            continue
        result.append(word)
        index += 1

    result.extend(("-E", "-fdirectives-only", source_word))
    if result.count("-E") != 1 or result.count("-fdirectives-only") != 1:
        raise CaptureError("preprocessing mode reconstruction is ambiguous")
    for forbidden in ("-c", "-S", "-o", "--output"):
        if forbidden in result:
            raise CaptureError("preprocessing argv retains output flag {0}".format(forbidden))
    return result


def run_preprocessor(argv, cwd, environment=None):
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("preprocessor invocation failed: {0}".format(exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise CaptureError(
            "preprocessor exited {0}: {1}".format(completed.returncode, stderr.strip())
        )
    if not completed.stdout:
        raise CaptureError("preprocessor produced no output")
    if len(completed.stdout) > 256 * 1024 * 1024:
        raise CaptureError("preprocessor output exceeds 256 MiB")
    return completed.stdout, completed.stderr


def unescape_marker_filename(value):
    output = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if following in ('"', "\\"):
                output.append(following)
                index += 2
                continue
        output.append(value[index])
        index += 1
    return "".join(output)


def marker_path(filename, cwd):
    if filename.startswith("<") and filename.endswith(">"):
        return None
    path = Path(filename)
    if not path.is_absolute():
        path = cwd / path
    return resolved(path)


def filter_target_lines(preprocessed, target_source, cwd):
    """Return ``(source line, emitted text)`` rows for one effective source."""

    text = preprocessed.decode("utf-8", errors="surrogateescape")
    target = resolved(target_source)
    current_path = None
    current_line = 1
    seen_marker = False
    rows = []
    for output_line in text.splitlines(keepends=True):
        marker = LINE_MARKER_PATTERN.match(output_line.rstrip("\r\n"))
        if marker:
            current_line = int(marker.group("line"))
            filename = unescape_marker_filename(marker.group("file"))
            current_path = marker_path(filename, cwd)
            if current_path == target:
                seen_marker = True
            continue
        if current_path == target:
            rows.append((current_line, output_line))
        current_line += 1
    if not seen_marker:
        raise CaptureError("preprocessor output has no line marker for {0}".format(target))
    if not rows:
        raise CaptureError("preprocessor emitted no active target lines for {0}".format(target))
    return rows


def mask_non_code(text, language):
    """Blank comments and literals while preserving byte positions/newlines."""

    chars = list(text)
    length = len(text)

    def blank(start, end):
        for offset in range(start, end):
            if chars[offset] not in ("\n", "\r"):
                chars[offset] = " "

    index = 0
    while index < length:
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            if end < 0:
                end = length
            blank(index, end)
            index = end
            continue
        if text.startswith("/*", index):
            depth = 1
            end = index + 2
            while end < length and depth:
                if language == "rust" and text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            if depth:
                raise CaptureError("unterminated block comment in {0} input".format(language))
            blank(index, end)
            index = end
            continue

        if language == "rust":
            raw = re.match(r"(?:br|rb|r)(?P<hashes>#{0,255})\"", text[index:])
            if raw:
                hashes = raw.group("hashes")
                terminator = '"' + hashes
                end = text.find(terminator, index + raw.end())
                if end < 0:
                    raise CaptureError("unterminated Rust raw string")
                end += len(terminator)
                blank(index, end)
                index = end
                continue

        prefix_length = 0
        if language == "rust" and text.startswith('b"', index):
            prefix_length = 1
        if text[index + prefix_length : index + prefix_length + 1] == '"':
            end = index + prefix_length + 1
            escaped = False
            while end < length:
                char = text[end]
                end += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    break
            else:
                raise CaptureError("unterminated string literal in {0} input".format(language))
            blank(index, end)
            index = end
            continue

        if text[index] == "'":
            # Treat a quote as a character literal only when a closing quote is
            # nearby.  This avoids consuming Rust lifetimes such as ``'a``.
            end = index + 1
            escaped = False
            closing = None
            while end < min(length, index + 16) and text[end] not in "\r\n":
                char = text[end]
                end += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == "'":
                    closing = end
                    break
            if closing is not None:
                blank(index, closing)
                index = closing
                continue
        index += 1
    return "".join(chars)


def rows_digest(rows):
    normalized = [
        {"line": line, "text": text}
        for line, text in rows
    ]
    return sha256_bytes(canonical_bytes(normalized))


def scan_rows(module, language, source_rel, source_sha256, active_sha256, rows):
    combined = "".join(text for _, text in rows)
    masked = mask_non_code(combined, language)
    starts = []
    position = 0
    for _, text in rows:
        starts.append(position)
        position += len(text)

    sites = []
    for match in ERRNO_PATTERN.finditer(masked):
        row_index = bisect.bisect_right(starts, match.start()) - 1
        if row_index < 0:
            raise CaptureError("cannot map failure-site offset to source line")
        line_number, line_text = rows[row_index]
        column = match.start() - starts[row_index] + 1
        errno = match.group(1)
        identity = {
            "column": column,
            "errno": errno,
            "language": language,
            "line": line_number,
            "module": module,
            "source": source_rel,
            "source_sha256": source_sha256,
        }
        identity_sha256 = sha256_bytes(canonical_bytes(identity))
        sites.append(
            {
                "active_source_sha256": active_sha256,
                "classification": "explicit_negative_errno_token",
                "column": column,
                "end_column": column + (match.end() - match.start()),
                "errno": errno,
                "expression": combined[match.start() : match.end()],
                "id": "HFS-" + identity_sha256[:24].upper(),
                "identity_sha256": identity_sha256,
                "language": language,
                "line": line_number,
                "line_sha256": sha256_bytes(line_text.encode("utf-8", errors="surrogateescape")),
                "module": module,
                "source": source_rel,
                "source_sha256": source_sha256,
            }
        )
    ids = [site["id"] for site in sites]
    if len(ids) != len(set(ids)):
        raise CaptureError("duplicate stable failure-site identity in {0}".format(source_rel))
    return sites


def config_provenance(kernel_dir, explicit_config=None):
    primary = explicit_config or (kernel_dir / ".config")
    primary = resolved(primary)
    if not primary.is_file():
        raise CaptureError("kernel configuration is missing: {0}".format(primary))
    generated = resolved(kernel_dir / "include/generated/autoconf.h")
    if not generated.is_file():
        raise CaptureError("generated kernel configuration is missing: {0}".format(generated))

    paths = [primary, generated]
    optional = resolved(kernel_dir / "include/config/auto.conf")
    if optional.is_file():
        paths.append(optional)
    records = []
    for path in paths:
        digest, _ = file_digest(path)
        try:
            name = str(path.relative_to(resolved(kernel_dir)))
        except ValueError:
            name = str(path)
        records.append({"path": name, "bytes": digest["bytes"], "sha256": digest["sha256"]})
    records.sort(key=lambda item: item["path"])
    return {
        "files": records,
        "primary_sha256": file_digest(primary)[0]["sha256"],
        "sha256": sha256_bytes(canonical_bytes(records)),
    }


def capture_c_source(module, source_rel, cmd_rel, repo, build_dir, kernel_dir, config, environment=None):
    source = repo / source_rel
    command_path = build_dir / cmd_rel
    require_within(source, repo, "effective source")
    require_within(command_path, build_dir, "Kbuild command file")
    if command_path.is_symlink() or not command_path.is_file():
        raise CaptureError("required Kbuild command file is missing or not regular: {0}".format(command_path))
    source_digest, _ = file_digest(source)
    command = parse_kbuild_cmd(command_path)
    source_index = verify_command_source(command, source, kernel_dir, command_path)
    preprocess_argv = reconstruct_preprocess_argv(command, source_index)
    compiler = compiler_provenance(preprocess_argv[0], environment)
    output, stderr = run_preprocessor(preprocess_argv, kernel_dir, environment)
    rows = filter_target_lines(output, source, kernel_dir)
    active_sha256 = rows_digest(rows)
    sites = scan_rows(module, "c", source_rel, source_digest["sha256"], active_sha256, rows)

    record = {
        "active_target_line_count": len(rows),
        "command_file": cmd_rel,
        "compile_argv": command["compile_argv"],
        "digests": {
            "command_file_sha256": command["file"]["sha256"],
            "compiler_sha256": compiler["sha256"],
            "config_sha256": config["sha256"],
            "effective_source_sha256": source_digest["sha256"],
            "preprocessed_sha256": sha256_bytes(output),
            "preprocessor_stderr_sha256": sha256_bytes(stderr),
            "preprocessing_argv_sha256": sha256_bytes(canonical_bytes(preprocess_argv)),
            "target_preprocessed_sha256": active_sha256,
        },
        "failure_site_count": len(sites),
        "language": "c",
        "module": module,
        "post_compile_token_count": command["post_compile_token_count"],
        "post_compile_tokens_sha256": command["post_compile_tokens_sha256"],
        "preprocess_argv": preprocess_argv,
        "preprocessor": compiler,
        "source": source_rel,
    }
    return record, sites


def capture_rust_source(module, source_rel, cmd_rel, repo, build_dir, kernel_dir, config, environment=None):
    source = repo / source_rel
    command_path = build_dir / cmd_rel
    require_within(source, repo, "effective Rust source")
    require_within(command_path, build_dir, "Rust command file")
    if command_path.is_symlink() or not command_path.is_file():
        raise CaptureError("required Rust command file is missing or not regular: {0}".format(command_path))
    source_digest, source_data = file_digest(source)
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaptureError("Rust helper is not UTF-8: {0}".format(exc))
    if re.search(r"#\s*\[\s*cfg\b|\bcfg!\s*\(", source_text):
        raise CaptureError(
            "Rust helper contains conditional compilation; capture expanded Rust input first"
        )
    command = parse_kbuild_cmd(command_path)
    verify_command_source(command, source, kernel_dir, command_path)
    recorded_argv_path = command_path.with_name(command_path.name + ".argv.json")
    if recorded_argv_path.is_symlink() or not recorded_argv_path.is_file():
        raise CaptureError(
            "exact Rust compiler argv capture is missing or not regular: {0}".format(
                recorded_argv_path
            )
        )
    recorded_argv_digest, recorded_argv_data = file_digest(recorded_argv_path)
    recorded_argv = parse_recorded_compile_argv_bytes(
        recorded_argv_data, str(recorded_argv_path)
    )
    source_indexes = [
        index
        for index, word in enumerate(recorded_argv)
        if path_from_command(word, kernel_dir) == resolved(source)
    ]
    if len(source_indexes) != 1:
        raise CaptureError(
            "recorded Rust compiler argv contains the effective source {0} times".format(
                len(source_indexes)
            )
        )
    compiler = compiler_provenance(recorded_argv[0], environment)
    rows = list(enumerate(source_text.splitlines(keepends=True), 1))
    if not rows:
        raise CaptureError("Rust helper source is empty")
    active_sha256 = rows_digest(rows)
    sites = scan_rows(module, "rust", source_rel, source_digest["sha256"], active_sha256, rows)
    record = {
        "active_target_line_count": len(rows),
        "command_file": cmd_rel,
        "compile_argv": recorded_argv,
        "digests": {
            "command_file_sha256": command["file"]["sha256"],
            "compiler_sha256": compiler["sha256"],
            "config_sha256": config["sha256"],
            "effective_source_sha256": source_digest["sha256"],
            "preprocessed_sha256": source_digest["sha256"],
            "preprocessing_argv_sha256": sha256_bytes(canonical_bytes([])),
            "recorded_compile_argv_file_sha256": recorded_argv_digest["sha256"],
            "recorded_compile_argv_sha256": sha256_bytes(canonical_bytes(recorded_argv)),
            "target_preprocessed_sha256": active_sha256,
        },
        "failure_site_count": len(sites),
        "language": "rust",
        "module": module,
        "post_compile_token_count": command["post_compile_token_count"],
        "post_compile_tokens_sha256": command["post_compile_tokens_sha256"],
        "preprocess_argv": [],
        "preprocessing_mode": "exact Rust source; no C preprocessing",
        "recorded_compile_argv_file": str(
            Path(cmd_rel).with_name(Path(cmd_rel).name + ".argv.json")
        ),
        "recorded_compiler": compiler,
        "source": source_rel,
    }
    return record, sites


def git_head(repo):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("cannot resolve repository commit: {0}".format(exc))
    value = completed.stdout.decode("ascii", errors="replace").strip()
    if completed.returncode != 0 or not re.match(r"^[0-9a-f]{40}$", value):
        raise CaptureError("cannot resolve exact repository commit")
    return value


def build_capture(repo, build_dir, kernel_dir, explicit_config=None, environment=None):
    repo = resolved(repo)
    build_dir = resolved(build_dir)
    kernel_dir = resolved(kernel_dir)
    if not repo.is_dir() or not build_dir.is_dir() or not kernel_dir.is_dir():
        raise CaptureError("repo, build directory, and kernel directory must exist")
    config = config_provenance(kernel_dir, explicit_config)
    overlay_path = repo / "scripts/patches/ihk-linux-compat.patch"
    inventory_path = repo / "host-kernel/reference/legacy-host-modules-f2eb7352.json"
    overlay_digest, _ = file_digest(overlay_path)
    inventory_digest, _ = file_digest(inventory_path)
    sources = []
    sites = []
    for module, language, source_rel, cmd_rel in EXPECTED_SOURCES:
        if language == "c":
            record, found = capture_c_source(
                module, source_rel, cmd_rel, repo, build_dir, kernel_dir, config, environment
            )
        else:
            record, found = capture_rust_source(
                module, source_rel, cmd_rel, repo, build_dir, kernel_dir, config, environment
            )
        sources.append(record)
        sites.extend(found)

    sites.sort(key=lambda item: (item["module"], item["source"], item["line"], item["column"], item["errno"]))
    ids = [site["id"] for site in sites]
    if len(ids) != len(set(ids)):
        raise CaptureError("stable failure-site IDs collide across sources")
    expected_modules = {entry[0] for entry in EXPECTED_SOURCES}
    observed_modules = {site["module"] for site in sites}
    if observed_modules != expected_modules:
        raise CaptureError(
            "failure-site capture lost a module: observed={0}, expected={1}".format(
                sorted(observed_modules), sorted(expected_modules)
            )
        )

    by_module = {}
    by_language = {}
    by_errno = {}
    for site in sites:
        by_module[site["module"]] = by_module.get(site["module"], 0) + 1
        by_language[site["language"]] = by_language.get(site["language"], 0) + 1
        by_errno[site["errno"]] = by_errno.get(site["errno"], 0) + 1
    return {
        "coverage": {
            "by_errno": dict(sorted(by_errno.items())),
            "by_language": dict(sorted(by_language.items())),
            "by_module": dict(sorted(by_module.items())),
            "failure_site_count": len(sites),
            "source_count": len(sources),
        },
        "failure_sites": sites,
        "generator": "scripts/host_module_failure_sites.py",
        "kernel_configuration": config,
        "profile": PROFILE,
        "provenance": {
            "compatibility_overlay": {
                "path": str(overlay_path.relative_to(repo)),
                "sha256": overlay_digest["sha256"],
            },
            "frozen_inventory": {
                "path": str(inventory_path.relative_to(repo)),
                "sha256": inventory_digest["sha256"],
            },
            "ihk_commit": git_head(repo / "ihk"),
            "repository_commit": git_head(repo),
        },
        "schema_version": SCHEMA_VERSION,
        "sources": sources,
    }


def write_capture(path, capture):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(capture, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--kernel-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        capture = build_capture(args.repo, args.build_dir, args.kernel_dir, args.config)
        write_capture(args.output, capture)
    except CaptureError as exc:
        print("host-module failure-site capture failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "captured {0} active failure sites from {1} host-module sources".format(
            capture["coverage"]["failure_site_count"], capture["coverage"]["source_count"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
