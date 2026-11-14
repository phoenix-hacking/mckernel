#!/usr/bin/env python3
"""Capture a compiler-backed, deliberately non-exhaustive failure-flow map.

``host_module_failure_sites.py`` freezes the active negative-errno tokens.  This
second-stage capture verifies that artifact against the same Kbuild inputs and
asks the recorded GNU compiler for CFG, SSA, and call-graph dumps.  It uses the
SSA def-use chains to identify candidate forwarded returns, callback returns,
error-pointer translations, and error-result guards.  Every flow identity is
bound to the effective source, compiler profile, function statement extent,
reachable compiler-derived entry roots, and normalized IR provenance.

Schema v1 is a checkpoint, not an exhaustiveness oracle.  It intentionally
fails ``--require-exhaustive`` because cross-translation-unit calls, indirect
callback targets, semantic error domains, Rust MIR, and test mappings are not
closed.  Keeping that invariant in the generator prevents this useful evidence
from being mistaken for FP-0006 completion.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import host_module_failure_sites as failure_sites


SCHEMA_VERSION = 1
PROFILE = "compiler-backed-active-host-module-failure-flows-v1"
INPUT_PROFILE = failure_sites.PROFILE
MAX_JSON_BYTES = 128 * 1024 * 1024
MAX_DUMP_BYTES = 256 * 1024 * 1024

FUNCTION_HEADER = re.compile(
    r"^;; Function (?P<name>[^\s(]+) \([^\n]*\)$", re.MULTILINE
)
LOCATION = re.compile(
    r"^\s*\[(?P<file>.+):(?P<line>[0-9]+):(?P<column>[0-9]+)"
    r"(?: [^\]]*)?\]\s*(?P<statement>.*)$"
)
BLOCK = re.compile(r"^\s*<bb (?P<number>[0-9]+)>\s*:")
SSA_NAME = re.compile(r"\b(?:[A-Za-z][A-Za-z0-9_.]*|_[0-9]+)(?:_[0-9]+)?\b")
ASSIGNMENT = re.compile(
    r"^\s*#?\s*(?P<lhs>(?:[A-Za-z][A-Za-z0-9_.]*|_[0-9]+)(?:_[0-9]+)?)"
    r"\s*=\s*(?P<rhs>.+?);?\s*$"
)
RETURN_VALUE = re.compile(r"^\s*return\s+(?P<value>.+?)\s*;\s*$")
DIRECT_CALL = re.compile(r"(?<![A-Za-z0-9_.])(?P<name>[A-Za-z][A-Za-z0-9_]*)\s*\(")
INDIRECT_CALL = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<name>(?:_[0-9]+|[A-Za-z][A-Za-z0-9_.]*_[0-9]+))\s*\("
)
ERRNO_NAME = re.compile(r"(?<![A-Za-z0-9_])(E[A-Z][A-Z0-9_]*)(?![A-Za-z0-9_])")
# Exact Linux errno namespace: asm-generic errno values, conventional aliases,
# and the kernel-only 512+ pseudo-errno values.  A broad ``E[A-Z]+`` match would
# misclassify tokens such as EXPORT_SYMBOL and ERR_PTR as errno names.
LINUX_ERRNO_NAMES = frozenset(
    """
    EPERM ENOENT ESRCH EINTR EIO ENXIO E2BIG ENOEXEC EBADF ECHILD EAGAIN
    ENOMEM EACCES EFAULT ENOTBLK EBUSY EEXIST EXDEV ENODEV ENOTDIR EISDIR
    EINVAL ENFILE EMFILE ENOTTY ETXTBSY EFBIG ENOSPC ESPIPE EROFS EMLINK
    EPIPE EDOM ERANGE EDEADLK ENAMETOOLONG ENOLCK ENOSYS ENOTEMPTY ELOOP
    ENOMSG EIDRM ECHRNG EL2NSYNC EL3HLT EL3RST ELNRNG EUNATCH ENOCSI EL2HLT
    EBADE EBADR EXFULL ENOANO EBADRQC EBADSLT EBFONT ENOSTR ENODATA ETIME
    ENOSR ENONET ENOPKG EREMOTE ENOLINK EADV ESRMNT ECOMM EPROTO EMULTIHOP
    EDOTDOT EBADMSG EOVERFLOW ENOTUNIQ EBADFD EREMCHG ELIBACC ELIBBAD
    ELIBSCN ELIBMAX ELIBEXEC EILSEQ ERESTART ESTRPIPE EUSERS ENOTSOCK
    EDESTADDRREQ EMSGSIZE EPROTOTYPE ENOPROTOOPT EPROTONOSUPPORT
    ESOCKTNOSUPPORT EOPNOTSUPP EPFNOSUPPORT EAFNOSUPPORT EADDRINUSE
    EADDRNOTAVAIL ENETDOWN ENETUNREACH ENETRESET ECONNABORTED ECONNRESET
    ENOBUFS EISCONN ENOTCONN ESHUTDOWN ETOOMANYREFS ETIMEDOUT ECONNREFUSED
    EHOSTDOWN EHOSTUNREACH EALREADY EINPROGRESS ESTALE EUCLEAN ENOTNAM
    ENAVAIL EISNAM EREMOTEIO EDQUOT ENOMEDIUM EMEDIUMTYPE ECANCELED ENOKEY
    EKEYEXPIRED EKEYREVOKED EKEYREJECTED EOWNERDEAD ENOTRECOVERABLE ERFKILL
    EHWPOISON EWOULDBLOCK EDEADLOCK ENOTSUP ERESTARTSYS ERESTARTNOINTR
    ERESTARTNOHAND ENOIOCTLCMD ERESTART_RESTARTBLOCK EPROBE_DEFER EOPENSTALE
    ENOPARAM EBADHANDLE ENOTSYNC EBADCOOKIE ENOTSUPP ETOOSMALL ESERVERFAULT
    EBADTYPE EJUKEBOX EIOCBQUEUED ERECALLCONFLICT ENOGRACE
    """.split()
)
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
SITE_ID = re.compile(r"^HFS-[0-9A-F]{24}$")

DEPENDENCY_FLAGS = {"-M", "-MM", "-MD", "-MMD", "-MG", "-MP"}
DEPENDENCY_VALUE_FLAGS = {"-MF", "-MT", "-MQ", "-MJ"}
OUTPUT_VALUE_FLAGS = {"-o", "--output"}
DUMP_SUFFIXES = {"cfg": ".cfg", "ssa": ".ssa", "cgraph": ".cgraph"}

# Build-derived compiler arguments are evidence, not a permission boundary.
# Never replay options that can load compiler code, select executable helpers,
# expand an unchecked response file, or create outputs outside our temporary
# directory.  Keep this deny-list narrow enough to preserve the recorded Rocky
# kernel profile while failing closed on the driver escape hatches relevant to
# a compiler-only ``-c`` invocation.
UNSAFE_REPLAY_EXACT = frozenset(
    (
        "--coverage",
        "-fbranch-probabilities",
        "-fprofile-arcs",
        "-ftest-coverage",
        "-wrapper",
        "--wrapper",
        "-Xassembler",
        "-Xpreprocessor",
        "-Xlinker",
    )
)
UNSAFE_REPLAY_PREFIXES = (
    "-fplugin",
    "-fprofile",
    "-fauto-profile",
    "-fopt-info",
    "-specs",
    "--specs",
    "-wrapper=",
    "--wrapper=",
    "-iplugindir",
    "-Wa,",
    "-Wp,",
)

FIXED_BLOCKERS = (
    "cross_translation_unit_call_graph_not_linked",
    "indirect_callback_targets_not_resolved",
    "semantic_error_domains_not_proven_for_all_integer_and_pointer_values",
    "rust_mir_and_cfg_not_captured",
    "compiler_statement_extents_are_not_full_lexical_function_ranges",
    "macro_definition_to_expansion_dataflow_not_resolved",
    "failure_flows_not_mapped_one_to_one_to_executable_tests",
)
ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "reason": "schema v1 is a bounded compiler checkpoint with unresolved paths and no per-flow executable-test map",
    "test_mapped": False,
}


class FlowError(RuntimeError):
    """Raised when compiler evidence is missing, inconsistent, or ambiguous."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def duplicate_rejecting_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FlowError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def read_json(path):
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FlowError("cannot read failure-site capture {0}: {1}".format(path, exc))
    if not data or len(data) > MAX_JSON_BYTES:
        raise FlowError("failure-site capture has an invalid size")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=duplicate_rejecting_object
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, FlowError):
            raise
        raise FlowError("cannot parse failure-site capture: {0}".format(exc))
    if not isinstance(value, dict):
        raise FlowError("failure-site capture must be a JSON object")
    return value, {"bytes": len(data), "sha256": sha256_bytes(data)}


def require_digest(value, label):
    if not isinstance(value, str) or not HEX_DIGEST.match(value):
        raise FlowError("{0} is not a SHA-256 digest".format(label))


def resolved(path):
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise FlowError("cannot resolve path {0}: {1}".format(path, exc))


def require_regular_within(path, root, label):
    path = Path(path)
    if path.is_symlink():
        raise FlowError("{0} must not be a symlink: {1}".format(label, path))
    candidate = resolved(path)
    base = resolved(root)
    try:
        common = os.path.commonpath((str(candidate), str(base)))
    except ValueError:
        common = ""
    if common != str(base):
        raise FlowError("{0} escapes {1}: {2}".format(label, root, path))
    if not candidate.is_file():
        raise FlowError("{0} is missing or not regular: {1}".format(label, path))
    return candidate


def validate_input_shape(capture):
    if capture.get("schema_version") != failure_sites.SCHEMA_VERSION:
        raise FlowError("unsupported failure-site schema")
    if capture.get("profile") != INPUT_PROFILE:
        raise FlowError("unexpected failure-site capture profile")
    sources = capture.get("sources")
    sites = capture.get("failure_sites")
    coverage = capture.get("coverage")
    if not isinstance(sources, list) or not isinstance(sites, list) or not isinstance(coverage, dict):
        raise FlowError("failure-site capture is missing sources, sites, or coverage")
    expected = [(entry[0], entry[1], entry[2], entry[3]) for entry in failure_sites.EXPECTED_SOURCES]
    observed = []
    source_map = {}
    for record in sources:
        if not isinstance(record, dict):
            raise FlowError("failure-site source record is not an object")
        identity = (
            record.get("module"),
            record.get("language"),
            record.get("source"),
            record.get("command_file"),
        )
        if identity in observed:
            raise FlowError("duplicate failure-site source record")
        observed.append(identity)
        source_map[identity[2]] = record
        digests = record.get("digests")
        if not isinstance(digests, dict):
            raise FlowError("source record has no digests: {0}".format(identity[2]))
        compile_argv = record.get("compile_argv")
        if (
            not isinstance(compile_argv, list)
            or len(compile_argv) < 2
            or any(
                not isinstance(word, str) or not word or "\x00" in word
                for word in compile_argv
            )
        ):
            raise FlowError("source record has malformed compiler argv: {0}".format(identity[2]))
        for key in (
            "command_file_sha256",
            "compiler_sha256",
            "config_sha256",
            "effective_source_sha256",
            "preprocessed_sha256",
            "preprocessing_argv_sha256",
            "target_preprocessed_sha256",
        ):
            require_digest(digests.get(key), "{0} {1}".format(identity[2], key))
    if observed != expected:
        raise FlowError("failure-site source closure or ordering changed")
    if coverage.get("source_count") != len(sources):
        raise FlowError("failure-site source count is inconsistent")
    if coverage.get("failure_site_count") != len(sites):
        raise FlowError("failure-site count is inconsistent")
    ids = []
    for site in sites:
        if not isinstance(site, dict) or not SITE_ID.match(str(site.get("id", ""))):
            raise FlowError("malformed failure-site record")
        if site.get("source") not in source_map:
            raise FlowError("failure site names an unknown source")
        if site.get("module") != source_map[site["source"]].get("module"):
            raise FlowError("failure-site module does not match its source")
        if site.get("errno") not in LINUX_ERRNO_NAMES:
            raise FlowError("failure site names an unsupported errno token")
        if site.get("classification") != "explicit_negative_errno_token":
            raise FlowError("failure site has an unsupported classification")
        if site.get("language") != source_map[site["source"]].get("language"):
            raise FlowError("failure-site language does not match its source")
        if not isinstance(site.get("expression"), str) or not site["expression"]:
            raise FlowError("failure site has no captured expression")
        for field in ("line", "column", "end_column"):
            if not isinstance(site.get(field), int) or isinstance(site.get(field), bool) or site[field] < 1:
                raise FlowError("failure site has an invalid {0}".format(field))
        if site["end_column"] <= site["column"]:
            raise FlowError("failure site has an invalid column range")
        for field in ("active_source_sha256", "identity_sha256", "line_sha256", "source_sha256"):
            require_digest(site.get(field), "failure site {0} {1}".format(site["id"], field))
        source_record = source_map[site["source"]]
        if site["source_sha256"] != source_record["digests"]["effective_source_sha256"]:
            raise FlowError("failure site source digest does not match its source record")
        if site["active_source_sha256"] != source_record["digests"]["target_preprocessed_sha256"]:
            raise FlowError("failure site active-source digest does not match its source record")
        identity = {
            "column": site.get("column"),
            "errno": site.get("errno"),
            "language": site.get("language"),
            "line": site.get("line"),
            "module": site.get("module"),
            "source": site.get("source"),
            "source_sha256": site.get("source_sha256"),
        }
        identity_sha256 = sha256_bytes(canonical_bytes(identity))
        if site["identity_sha256"] != identity_sha256:
            raise FlowError("failure-site identity digest is invalid")
        if site["id"] != "HFS-" + identity_sha256[:24].upper():
            raise FlowError("failure-site stable ID is invalid")
        ids.append(site["id"])
    if len(ids) != len(set(ids)):
        raise FlowError("duplicate failure-site ID")
    by_module = {}
    by_language = {}
    by_errno = {}
    for site in sites:
        by_module[site["module"]] = by_module.get(site["module"], 0) + 1
        by_language[site["language"]] = by_language.get(site["language"], 0) + 1
        by_errno[site["errno"]] = by_errno.get(site["errno"], 0) + 1
    expected_coverage = {
        "by_errno": dict(sorted(by_errno.items())),
        "by_language": dict(sorted(by_language.items())),
        "by_module": dict(sorted(by_module.items())),
        "failure_site_count": len(sites),
        "source_count": len(sources),
    }
    if coverage != expected_coverage:
        raise FlowError("failure-site coverage summary is inconsistent")
    return source_map


def normalized_word(word, roots, output=None):
    result = word
    replacements = []
    if output is not None:
        replacements.append((str(resolved(output)), "$OUTPUT"))
    for label, path in roots:
        replacements.append((str(resolved(path)), label))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    for prefix, label in replacements:
        result = result.replace(prefix, label)
    return result


def normalized_argv(argv, roots, output=None):
    return [normalized_word(word, roots, output) for word in argv]


def normalized_dump(data, roots, output=None):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FlowError("compiler dump is not UTF-8: {0}".format(exc))
    text = normalized_word(text, roots, output)
    # GCC cgraph dumps contain allocator addresses in ``Aux: @0x...`` rows.
    # They are process-local diagnostics, not program provenance.
    text = re.sub(r"(?<=@)0x[0-9A-Fa-f]+", "0xADDR", text)
    return text.encode("utf-8")


def unsafe_replay_option(word):
    """Return whether an original driver word may escape bounded replay."""

    return (
        word in UNSAFE_REPLAY_EXACT
        or word.startswith("@")
        or word == "-B"
        or word.startswith("-B")
        or any(word.startswith(prefix) for prefix in UNSAFE_REPLAY_PREFIXES)
    )


def reconstruct_ir_argv(original, source_index, output):
    """Return an output-confined GCC analysis invocation.

    The original preprocessing/configuration flags are retained.  Dependency
    side effects, old outputs, prior dumps, LTO, and save-temps are removed;
    the analysis overlay requests CFG/SSA/cgraph dumps in the temporary output
    directory while preserving the recorded optimization profile.  LTO inputs
    fail closed because schema v1 does not capture a linked whole-program IR.
    """

    if not isinstance(original, list) or len(original) < 2:
        raise FlowError("recorded compiler argv is missing")
    if source_index <= 0 or source_index >= len(original):
        raise FlowError("recorded source index is invalid")
    source_word = original[source_index]
    result = [original[0]]
    index = 1
    saw_compile = False
    while index < len(original):
        word = original[index]
        if index == source_index:
            index += 1
            continue
        if word in DEPENDENCY_FLAGS:
            index += 1
            continue
        if word in DEPENDENCY_VALUE_FLAGS or word in OUTPUT_VALUE_FLAGS:
            if index + 1 >= len(original):
                raise FlowError("compiler flag {0} lacks its value".format(word))
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
        if unsafe_replay_option(word):
            raise FlowError(
                "recorded compiler argv contains an unsafe replay option: {0}".format(
                    word
                )
            )
        if (
            word in ("-E", "-S")
            or word.startswith("-fdump-")
            or word.startswith("-save-temps")
            or word.startswith("-dumpbase")
            or word.startswith("-dumpdir")
            or word.startswith("-auxbase")
        ):
            raise FlowError("recorded compiler argv already requests persistent dumps")
        if word == "-c":
            saw_compile = True
        if word == "-flto" or word.startswith("-flto="):
            raise FlowError("schema v1 cannot analyze a recorded LTO compilation")
        result.append(word)
        index += 1
    if not saw_compile:
        result.append("-c")
    result.extend(
        (
            "-fno-diagnostics-color",
            "-fdump-tree-cfg-lineno",
            "-fdump-tree-ssa-lineno",
            "-fdump-ipa-cgraph-lineno",
            "-o",
            str(output),
            source_word,
        )
    )
    if result.count("-o") != 1 or result.count(source_word) != 1:
        raise FlowError("analysis compiler argv is ambiguous")
    return result


def source_index_in_argv(argv, source, cwd):
    expected = resolved(source)
    matches = []
    for index, word in enumerate(argv[1:], 1):
        if word.startswith("-"):
            continue
        candidate = Path(word)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        if resolved(candidate) == expected:
            matches.append(index)
    if len(matches) != 1:
        raise FlowError("recorded compiler argv contains effective source {0} times".format(len(matches)))
    return matches[0]


def _run_ir_argv(argv, cwd, roots, output, temporary_path, environment=None):
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FlowError("compiler IR invocation failed: {0}".format(exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-6000:]
        raise FlowError(
            "compiler IR invocation exited {0}: {1}".format(
                completed.returncode, stderr.strip()
            )
        )
    dumps = {}
    for name, suffix in DUMP_SUFFIXES.items():
        matches = sorted(temporary_path.glob("*" + suffix))
        if len(matches) != 1:
            raise FlowError("compiler produced {0} {1} dumps".format(len(matches), name))
        try:
            data = matches[0].read_bytes()
        except OSError as exc:
            raise FlowError("cannot read compiler {0} dump: {1}".format(name, exc))
        if not data or len(data) > MAX_DUMP_BYTES:
            raise FlowError("compiler {0} dump has an invalid size".format(name))
        normalized = normalized_dump(data, roots, output)
        dumps[name] = {
            "bytes": len(data),
            "normalized_bytes": normalized,
            "normalized_sha256": sha256_bytes(normalized),
            # Raw bytes stay in memory for source-location parsing.  They are
            # intentionally omitted from the emitted JSON by the caller.
            "raw_bytes": data,
        }
    return {
        "analysis_argv": normalized_argv(argv, roots, output),
        "analysis_argv_sha256": sha256_bytes(
            canonical_bytes(normalized_argv(argv, roots, output))
        ),
        "compiler_stderr_sha256": sha256_bytes(completed.stderr),
        "compiler_stdout_sha256": sha256_bytes(completed.stdout),
        "dumps": dumps,
    }


def run_ir_for_source(argv, source_index, cwd, roots, environment=None):
    with tempfile.TemporaryDirectory(prefix="mckernel-failure-flow-") as temporary:
        temporary_path = Path(temporary)
        output = temporary_path / "flow.o"
        actual = reconstruct_ir_argv(argv, source_index, output)
        return _run_ir_argv(actual, cwd, roots, output, temporary_path, environment)


def location_path(value, cwd):
    for placeholder in ("$REPO", "$BUILD", "$KERNEL", "$OUTPUT"):
        if value == placeholder or value.startswith(placeholder + "/"):
            raise FlowError("normalized placeholder cannot be resolved as a source path")
    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return resolved(path)


def parse_functions(data, target_source, cwd):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FlowError("SSA dump is not UTF-8: {0}".format(exc))
    matches = list(FUNCTION_HEADER.finditer(text))
    functions = []
    target = resolved(target_source)
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        name = match.group("name")
        statements = []
        returns = []
        current_block = None
        for raw_line in section.splitlines():
            block_match = BLOCK.match(raw_line)
            if block_match:
                current_block = int(block_match.group("number"))
                continue
            return_match = RETURN_VALUE.match(raw_line)
            if return_match:
                returns.append(return_match.group("value").strip())
            location_match = LOCATION.match(raw_line)
            if location_match:
                path = location_path(location_match.group("file"), cwd)
                if path != target:
                    continue
                statement_text = location_match.group("statement").strip()
                located_return = RETURN_VALUE.match(statement_text)
                if located_return:
                    returns.append(located_return.group("value").strip())
                if statement_text.startswith("//") or statement_text.startswith("goto "):
                    continue
                statements.append(
                    {
                        "basic_block": current_block,
                        "column": int(location_match.group("column")),
                        "line": int(location_match.group("line")),
                        "text": statement_text,
                    }
                )
                continue
            assignment = ASSIGNMENT.match(raw_line)
            if assignment and "PHI <" in assignment.group("rhs"):
                statements.append(
                    {
                        "basic_block": current_block,
                        "column": None,
                        "line": None,
                        "text": "{0} = {1}".format(
                            assignment.group("lhs"), assignment.group("rhs")
                        ),
                    }
                )
        if statements and any(item["line"] is not None for item in statements):
            located = [item for item in statements if item["line"] is not None]
            functions.append(
                {
                    "name": name,
                    "returns": sorted(set(returns)),
                    "statements": statements,
                    "statement_range": {
                        "end_column": max(item["column"] for item in located),
                        "end_line": max(item["line"] for item in located),
                        "kind": "compiler_statement_extent",
                        "start_column": min(item["column"] for item in located),
                        "start_line": min(item["line"] for item in located),
                    },
                }
            )
    names = [item["name"] for item in functions]
    if len(names) != len(set(names)):
        raise FlowError("compiler SSA dump contains duplicate function names")
    if not functions:
        raise FlowError("compiler SSA dump contains no effective-source functions")
    return functions


def parse_cgraph(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FlowError("call-graph dump is not UTF-8: {0}".format(exc))
    properties = {}
    header = re.compile(r"^(?P<name>[^\s/]+)/[0-9]+ \((?P<label>[^)]*)\)\s*$")
    current = None
    for line in text.splitlines():
        match = header.match(line)
        if match:
            current = match.group("name")
            properties.setdefault(
                current,
                {
                    "address_taken": False,
                    "definition": False,
                    "externally_visible": False,
                    "public": False,
                },
            )
            continue
        if current is None:
            continue
        item = properties[current]
        stripped = line.strip()
        if stripped.startswith("Type: function definition analyzed"):
            item["definition"] = True
        if stripped == "Address is taken.":
            item["address_taken"] = True
        if stripped.startswith("Visibility:"):
            words = set(stripped.split())
            item["externally_visible"] = item["externally_visible"] or (
                "externally_visible" in words
            )
            item["public"] = item["public"] or ("public" in words)
    return properties


def statement_assignment(statement):
    match = ASSIGNMENT.match(statement["text"])
    if not match or statement["text"].lstrip().startswith("if "):
        return None
    return match.group("lhs"), match.group("rhs").rstrip(";").strip()


def variables_in(expression):
    excluded = {
        "PHI",
        "NULL",
        "int",
        "long",
        "short",
        "signed",
        "unsigned",
        "char",
        "void",
        "if",
        "else",
        "return",
    }
    return [name for name in SSA_NAME.findall(expression) if name not in excluded]


def calls_in(expression):
    if "PHI <" in expression:
        # GCC prints predecessor edges as ``ssa_name(bb_number)``; those are
        # not indirect function calls.
        return [], []
    direct = []
    indirect = []
    for match in INDIRECT_CALL.finditer(expression):
        indirect.append(match.group("name"))
    for match in DIRECT_CALL.finditer(expression):
        name = match.group("name")
        if (
            name not in ("if", "return", "sizeof")
            and not name.startswith("__builtin_")
            and name not in indirect
        ):
            direct.append(name)
    return sorted(set(direct)), sorted(set(indirect))


def definitions(function):
    result = {}
    for statement in function["statements"]:
        assignment = statement_assignment(statement)
        if assignment:
            result.setdefault(assignment[0], []).append((statement, assignment[1]))
    return result


def trace_origins(value, defs, function_names, seen=None, depth=0):
    if seen is None:
        seen = set()
    if depth > 32:
        return [{"kind": "unresolved_depth_limit", "value": value}]
    direct, indirect = calls_in(value)
    origins = []
    for name in direct:
        origins.append(
            {
                "callee": name,
                "kind": "internal_callee" if name in function_names else "external_provider",
            }
        )
    for name in indirect:
        origins.append({"callee_expression": name, "kind": "indirect_callback"})
    if re.search(r"(?<![A-Za-z0-9_])-\s*[0-9]+(?:[A-Za-z]*)?\b", value):
        origins.append({"kind": "negative_constant"})
    for variable in variables_in(value):
        if variable in seen:
            continue
        if variable not in defs:
            if re.match(r"^(?:D\.|_[0-9])", variable):
                origins.append({"kind": "unresolved_ssa_value", "value": variable})
            continue
        next_seen = set(seen)
        next_seen.add(variable)
        for _, rhs in defs[variable]:
            origins.extend(
                trace_origins(rhs, defs, function_names, next_seen, depth + 1)
            )
    unique = {}
    for origin in origins:
        unique[canonical_bytes(origin)] = origin
    return [unique[key] for key in sorted(unique)]


def return_terminals(function, source_lines, source_masked_lines=None):
    defs = definitions(function)
    source_masked_lines = source_masked_lines or source_lines
    reachable = {}

    def visit(value, depth=0):
        if depth > 32:
            return
        for variable in variables_in(value):
            if variable in reachable and reachable[variable] <= depth:
                continue
            reachable[variable] = depth
            for _, rhs in defs.get(variable, []):
                visit(rhs, depth + 1)

    for value in function["returns"]:
        visit(value)
    candidates = []
    for variable in sorted(reachable):
        for statement, rhs in defs.get(variable, []):
            if statement["line"] is None:
                continue
            line_text = (
                source_masked_lines[statement["line"] - 1]
                if statement["line"] <= len(source_masked_lines)
                else ""
            )
            if re.search(r"\breturn\b", line_text):
                candidates.append((reachable[variable], statement, rhs))
    if candidates:
        by_location = {}
        for depth, statement, rhs in candidates:
            key = (statement["line"], statement["column"])
            by_location.setdefault(key, []).append((depth, statement, rhs))
        selected = []
        for values in by_location.values():
            minimum_depth = min(item[0] for item in values)
            unique = {}
            for depth, statement, rhs in values:
                if depth == minimum_depth:
                    unique[(statement["line"], statement["column"], rhs)] = (
                        depth, statement, rhs
                    )
            selected.extend(unique.values())
        return [
            (statement, rhs)
            for _, statement, rhs in sorted(
                selected,
                key=lambda item: (
                    item[1]["line"], item[1]["column"], item[0], item[2]
                ),
            )
        ]
    # Compiler lowering can attribute a synthetic result assignment to a macro
    # expansion rather than the physical return line.  Preserve it as an
    # unresolved candidate instead of silently dropping the path.
    terminals = []
    for variable in sorted(reachable):
        for statement, rhs in defs.get(variable, []):
            if statement["line"] is not None:
                terminals.append((statement, rhs))
    return terminals


def function_roots(functions, cgraph):
    roots = {}
    for function in functions:
        name = function["name"]
        props = cgraph.get(name, {})
        found = []
        if props.get("definition") and (props.get("externally_visible") or props.get("public")):
            found.append("external:{0}".format(name))
        if props.get("definition") and props.get("address_taken"):
            found.append("callback:{0}".format(name))
        roots[name] = sorted(found)
    calls = {}
    names = set(roots)
    for function in functions:
        found = set()
        for statement in function["statements"]:
            direct, _ = calls_in(statement["text"])
            found.update(name for name in direct if name in names)
        calls[function["name"]] = found
    reachable = {name: set(values) for name, values in roots.items()}
    changed = True
    while changed:
        changed = False
        for caller, callees in calls.items():
            for callee in callees:
                before = len(reachable[callee])
                reachable[callee].update(reachable[caller])
                if len(reachable[callee]) != before:
                    changed = True
    return {name: sorted(values) for name, values in reachable.items()}


def role_for_return(snippet, origins, errno_names):
    marker_names = set(item[1] for item in flow_markers(snippet))
    if "PTR_ERR" in marker_names:
        return "error_pointer_translation_return"
    if "ERR_PTR" in marker_names:
        return "error_pointer_encoding_return"
    if any(origin["kind"] == "indirect_callback" for origin in origins):
        return "callback_return_candidate"
    if any(origin["kind"] in ("external_provider", "internal_callee") for origin in origins):
        return "provider_return_candidate"
    if errno_names or any(origin["kind"] == "negative_constant" for origin in origins):
        return "explicit_errno_return"
    if re.match(r"^\s*(?:return\s+)?(?:\([^)]*\)\s*)?[+]?0(?:[UL]*)\s*;?\s*$", snippet):
        return "non_failure_constant_return"
    return "unresolved_return_candidate"


def errno_names_in(text):
    return sorted(
        set(name for name in ERRNO_NAME.findall(text) if name in LINUX_ERRNO_NAMES)
    )


def flow_markers(text):
    """Return exact 1-based source columns for error-pointer primitives."""

    found = []
    for macro, role in (
        ("IS_ERR_OR_NULL", "error_pointer_or_null_guard"),
        ("IS_ERR", "error_pointer_guard"),
        ("PTR_ERR", "error_pointer_translation"),
        ("ERR_PTR", "error_pointer_encoding"),
    ):
        pattern = re.compile(r"(?<![A-Za-z0-9_])" + macro + r"\s*\(")
        for match in pattern.finditer(text):
            found.append((match.start() + 1, macro, role))
    return sorted(found)


def has_comparison_operator(text):
    if re.search(r"(?<![<>=!])(?:==|!=|<=|>=)(?![<>=])", text):
        return True
    if re.search(r"(?<![-<>=])<(?![<=])", text):
        return True
    if re.search(r"(?<![-<>=])>(?![>=])", text):
        return True
    return False


def errno_token_role(masked_line):
    if re.search(r"\breturn\b", masked_line):
        return "errno_token_return_context"
    if any(macro == "ERR_PTR" for _, macro, _ in flow_markers(masked_line)):
        return "errno_token_error_pointer_context"
    if has_comparison_operator(masked_line) or re.search(r"\bcase\s+", masked_line):
        return "errno_token_comparison_context"
    return "errno_token_value_context"


def failure_site_errno_column(site):
    expression = site["expression"]
    errno_name = site["errno"]
    if "\n" in expression or "\r" in expression:
        raise FlowError("multiline failure-site expressions require explicit row mapping")
    first = expression.find(errno_name)
    if first < 0 or expression.find(errno_name, first + len(errno_name)) >= 0:
        raise FlowError("failure-site expression has an ambiguous errno token")
    return site["column"] + first


def make_identity_flow(module, source_rel, source_sha256, active_profile, provenance_sha256,
                       function, roots, statement, role, origin, expression):
    identity = {
        "active_compile_profile_sha256": active_profile,
        "expression_role": role,
        "function": function["name"],
        "function_range": function["statement_range"],
        "location": {"column": statement["column"], "line": statement["line"]},
        "module": module,
        "origin": origin,
        "provenance_sha256": provenance_sha256,
        "reachable_entry_roots": roots,
        "source": source_rel,
        "source_sha256": source_sha256,
    }
    digest = sha256_bytes(canonical_bytes(identity))
    return {
        "active_compile_profile_sha256": active_profile,
        "expression": expression.strip(),
        "expression_role": role,
        "function": function["name"],
        "function_range": function["statement_range"],
        "id": "HFF-" + digest[:24].upper(),
        "identity_sha256": digest,
        "location": identity["location"],
        "module": module,
        "origin": origin,
        "provenance_sha256": provenance_sha256,
        "reachable_entry_roots": roots,
        "source": source_rel,
        "source_sha256": source_sha256,
    }


def find_function_for_statement(functions, line, column=None):
    exact = []
    containing = []
    for function in functions:
        if any(item["line"] == line for item in function["statements"]):
            exact.append(function)
        extent = function["statement_range"]
        if extent["start_line"] <= line <= extent["end_line"]:
            containing.append(function)
    candidates = exact or containing
    if len(candidates) == 1:
        return candidates[0]
    return None


def analyze_ir_source(module, source_rel, source_path, source_sha256,
                      active_profile, compiler_provenance_sha256, ir,
                      active_rows, explicit_sites, cwd):
    functions = parse_functions(ir["dumps"]["ssa"]["raw_bytes"], source_path, cwd)
    cgraph = parse_cgraph(ir["dumps"]["cgraph"]["normalized_bytes"])
    roots = function_roots(functions, cgraph)
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FlowError("cannot read effective C source {0}: {1}".format(source_rel, exc))
    source_lines = source_text.splitlines()
    source_masked_lines = failure_sites.mask_non_code(source_text, "c").splitlines()
    if len(source_masked_lines) != len(source_lines):
        raise FlowError("source masking changed the physical line count")
    provenance = {
        "analysis_argv_sha256": ir["analysis_argv_sha256"],
        "cfg_sha256": ir["dumps"]["cfg"]["normalized_sha256"],
        "compiler_sha256": compiler_provenance_sha256,
        "cgraph_sha256": ir["dumps"]["cgraph"]["normalized_sha256"],
        "ssa_sha256": ir["dumps"]["ssa"]["normalized_sha256"],
    }
    provenance_sha256 = sha256_bytes(canonical_bytes(provenance))
    function_names = {item["name"] for item in functions}
    flows = []
    unresolved = []

    for function in functions:
        defs = definitions(function)
        function_root_set = roots[function["name"]]
        if not function_root_set:
            unresolved.append(
                {
                    "function": function["name"],
                    "kind": "no_compiler_entry_root_reaches_function",
                    "source": source_rel,
                }
            )
        marker_seen = set()
        guard_seen = set()
        for statement, rhs in return_terminals(
            function, source_lines, source_masked_lines
        ):
            line = statement["line"]
            snippet = source_lines[line - 1] if 0 < line <= len(source_lines) else statement["text"]
            masked_snippet = (
                source_masked_lines[line - 1]
                if 0 < line <= len(source_masked_lines)
                else statement["text"]
            )
            errno_names = errno_names_in(masked_snippet)
            origins = trace_origins(rhs, defs, function_names)
            role = role_for_return(masked_snippet, origins, errno_names)
            if role == "non_failure_constant_return":
                continue
            origin = {
                "errno_names": errno_names,
                "ssa_origins": origins,
            }
            flows.append(
                make_identity_flow(
                    module, source_rel, source_sha256, active_profile,
                    provenance_sha256, function, function_root_set, statement,
                    role, origin, snippet,
                )
            )
            if role == "unresolved_return_candidate":
                unresolved.append(
                    {
                        "function": function["name"],
                        "kind": "return_value_error_domain_unresolved",
                        "line": line,
                        "source": source_rel,
                    }
                )

        for statement in function["statements"]:
            if statement["line"] is None:
                continue
            line = statement["line"]
            snippet = source_lines[line - 1] if 0 < line <= len(source_lines) else statement["text"]
            masked = (
                source_masked_lines[line - 1]
                if 0 < line <= len(source_masked_lines)
                else statement["text"]
            )
            for marker_column, marker, marker_role in flow_markers(masked):
                marker_key = (line, marker_column, marker_role)
                if marker_key in marker_seen:
                    continue
                marker_seen.add(marker_key)
                marker_statement = dict(statement)
                marker_statement["column"] = marker_column
                flows.append(
                    make_identity_flow(
                        module, source_rel, source_sha256, active_profile,
                        provenance_sha256, function, function_root_set,
                        marker_statement, marker_role,
                        {
                            "macro": marker,
                            "ssa_origins": trace_origins(
                                statement["text"], defs, function_names
                            ),
                        },
                        snippet,
                    )
                )
            role = None
            is_condition = statement["text"].startswith("if ")
            if is_condition:
                if errno_names_in(masked) and has_comparison_operator(masked):
                    role = "errno_result_comparison"
                elif errno_names_in(masked):
                    role = "errno_result_guard_candidate"
                elif has_comparison_operator(masked) and re.search(
                    r"(?<![A-Za-z0-9_])0(?:[UuLl]*)(?![A-Za-z0-9_])", masked
                ):
                    role = "signed_result_guard_candidate"
                else:
                    condition_origins = trace_origins(statement["text"], defs, function_names)
                    if any(
                        item["kind"] in ("external_provider", "internal_callee", "indirect_callback")
                        for item in condition_origins
                    ):
                        role = "provider_result_guard_candidate"
            if role is not None:
                guard_key = (line, statement["column"], role)
                if guard_key in guard_seen:
                    role = None
                else:
                    guard_seen.add(guard_key)
            if role is not None:
                origin = {
                    "errno_names": errno_names_in(masked),
                    "ssa_origins": trace_origins(statement["text"], defs, function_names),
                }
                flows.append(
                    make_identity_flow(
                        module, source_rel, source_sha256, active_profile,
                        provenance_sha256, function, function_root_set, statement,
                        role, origin, snippet,
                    )
                )
    # Map every active errno spelling, including ``-((int)EINVAL)`` forms the
    # token-only first-stage pattern deliberately does not attempt to parse.
    explicit_by_location = {}
    for site in explicit_sites:
        explicit_by_location.setdefault(
            (site["line"], failure_site_errno_column(site), site["errno"]), []
        ).append(site["id"])
    active_masked_rows = failure_sites.mask_non_code(
        "".join(text for _, text in active_rows), "c"
    ).splitlines(keepends=True)
    if len(active_masked_rows) != len(active_rows):
        raise FlowError("active-source masking changed the compiler row count")
    for (line, text), masked in zip(active_rows, active_masked_rows):
        for match in ERRNO_NAME.finditer(masked):
            if match.group(1) not in LINUX_ERRNO_NAMES:
                continue
            function = find_function_for_statement(functions, line, match.start() + 1)
            if function is None:
                unresolved.append(
                    {
                        "errno": match.group(1),
                        "first_stage_site_ids": sorted(
                            explicit_by_location.get(
                                (line, match.start() + 1, match.group(1)), []
                            )
                        ),
                        "kind": "active_errno_token_has_no_unique_compiler_function",
                        "line": line,
                        "source": source_rel,
                    }
                )
                continue
            statement = {
                "column": match.start() + 1,
                "line": line,
            }
            masked_line = masked
            role = errno_token_role(masked_line)
            flows.append(
                make_identity_flow(
                    module, source_rel, source_sha256, active_profile,
                    provenance_sha256, function, roots[function["name"]],
                    statement, role,
                    {
                        "errno": match.group(1),
                        "first_stage_site_ids": sorted(
                            explicit_by_location.get(
                                (line, match.start() + 1, match.group(1)), []
                            )
                        ),
                    },
                    text,
                )
            )

    unique = {}
    for flow in flows:
        if flow["id"] in unique and unique[flow["id"]] != flow:
            raise FlowError("failure-flow ID collision")
        unique[flow["id"]] = flow
    flows = sorted(
        unique.values(),
        key=lambda item: (
            item["source"], item["location"]["line"],
            item["location"]["column"] or 0, item["expression_role"], item["id"],
        ),
    )
    unresolved = sorted(
        {canonical_bytes(item): item for item in unresolved}.values(),
        key=lambda item: canonical_bytes(item),
    )
    function_records = []
    for function in functions:
        function_records.append(
            {
                "name": function["name"],
                "reachable_entry_roots": roots[function["name"]],
                "statement_range": function["statement_range"],
                "statement_sha256": sha256_bytes(canonical_bytes(function["statements"])),
            }
        )
    return {
        "flows": flows,
        "functions": function_records,
        "provenance": provenance,
        "provenance_sha256": provenance_sha256,
        "unresolved": unresolved,
    }


def source_profile(record, roots):
    digests = record["digests"]
    value = {
        "analysis_overlay": [
            "preserve-recorded-optimization",
            "reject-lto",
            "cfg-lineno",
            "ssa-lineno",
            "cgraph-lineno",
        ],
        "command_file_sha256": digests["command_file_sha256"],
        "compiler_sha256": digests["compiler_sha256"],
        "config_sha256": digests["config_sha256"],
        "effective_source_sha256": digests["effective_source_sha256"],
        "input_profile": INPUT_PROFILE,
        "recorded_compile_argv": normalized_argv(record["compile_argv"], roots),
        "target_preprocessed_sha256": digests["target_preprocessed_sha256"],
    }
    return sha256_bytes(canonical_bytes(value)), value


def collect_first_stage_ids(flow_records, unresolved_records):
    mapped = set()
    for flow in flow_records:
        for site_id in flow.get("origin", {}).get("first_stage_site_ids", []):
            mapped.add(site_id)
    for unresolved in unresolved_records:
        for site_id in unresolved.get("first_stage_site_ids", []):
            mapped.add(site_id)
    return mapped


def validate_input_capture_binding(capture, repo):
    provenance = capture.get("provenance")
    if not isinstance(provenance, dict):
        raise FlowError("failure-site capture provenance is missing")
    try:
        repository_commit = failure_sites.git_head(repo)
        ihk_commit = failure_sites.git_head(repo / "ihk")
    except failure_sites.CaptureError as exc:
        raise FlowError("cannot replay repository provenance: {0}".format(exc))
    if provenance.get("repository_commit") != repository_commit:
        raise FlowError("failure-site repository commit differs from checkout")
    if provenance.get("ihk_commit") != ihk_commit:
        raise FlowError("failure-site IHK commit differs from checkout")
    for field, relative in (
        ("compatibility_overlay", "scripts/patches/ihk-linux-compat.patch"),
        ("frozen_inventory", "host-kernel/reference/legacy-host-modules-f2eb7352.json"),
    ):
        record = provenance.get(field)
        if not isinstance(record, dict) or record.get("path") != relative:
            raise FlowError("failure-site {0} provenance is malformed".format(field))
        evidence_path = require_regular_within(
            repo / relative, repo, "failure-site {0} provenance input".format(field)
        )
        digest, _ = failure_sites.file_digest(evidence_path)
        if record.get("sha256") != digest["sha256"]:
            raise FlowError("failure-site {0} provenance differs from checkout".format(field))


def compare_capture_record(expected_record, expected_sites, actual_record, actual_sites, source_rel):
    if canonical_bytes(expected_record) != canonical_bytes(actual_record):
        raise FlowError("failure-site source replay differs for {0}".format(source_rel))
    expected_sorted = sorted(expected_sites, key=lambda item: item["id"])
    actual_sorted = sorted(actual_sites, key=lambda item: item["id"])
    if canonical_bytes(expected_sorted) != canonical_bytes(actual_sorted):
        raise FlowError("failure-site replay differs for {0}".format(source_rel))


def build_capture(repo, build_dir, kernel_dir, failure_site_path, explicit_config=None,
                  environment=None):
    repo = resolved(repo)
    build_dir = resolved(build_dir)
    kernel_dir = resolved(kernel_dir)
    if not repo.is_dir() or not build_dir.is_dir() or not kernel_dir.is_dir():
        raise FlowError("repo, build directory, and kernel directory must exist")
    failure_site_path = require_regular_within(
        failure_site_path, build_dir, "failure-site capture"
    )
    capture, capture_file = read_json(failure_site_path)
    source_map = validate_input_shape(capture)
    validate_input_capture_binding(capture, repo)
    config = failure_sites.config_provenance(kernel_dir, explicit_config)
    input_config = capture.get("kernel_configuration")
    if canonical_bytes(config) != canonical_bytes(input_config):
        raise FlowError("kernel configuration differs from failure-site capture")
    roots = (("$REPO", repo), ("$BUILD", build_dir), ("$KERNEL", kernel_dir))
    sites_by_source = {}
    for site in capture["failure_sites"]:
        sites_by_source.setdefault(site["source"], []).append(site)

    output_sources = []
    all_flows = []
    all_unresolved = []
    total_functions = 0
    for module, language, source_rel, cmd_rel in failure_sites.EXPECTED_SOURCES:
        expected_record = source_map[source_rel]
        expected_source_sites = sites_by_source.get(source_rel, [])
        try:
            if language == "c":
                actual_record, actual_source_sites = failure_sites.capture_c_source(
                    module, source_rel, cmd_rel, repo, build_dir, kernel_dir,
                    config, environment,
                )
            else:
                actual_record, actual_source_sites = failure_sites.capture_rust_source(
                    module, source_rel, cmd_rel, repo, build_dir, kernel_dir,
                    config, environment,
                )
        except failure_sites.CaptureError as exc:
            raise FlowError("failure-site replay failed for {0}: {1}".format(source_rel, exc))
        compare_capture_record(
            expected_record, expected_source_sites, actual_record,
            actual_source_sites, source_rel,
        )
        active_profile_sha256, profile_record = source_profile(expected_record, roots)
        source_path = require_regular_within(repo / source_rel, repo, "effective source")
        source_digest = expected_record["digests"]["effective_source_sha256"]
        try:
            source_data = source_path.read_bytes()
        except OSError as exc:
            raise FlowError("cannot read effective source {0}: {1}".format(source_rel, exc))
        if sha256_bytes(source_data) != source_digest:
            raise FlowError("effective source digest differs from failure-site capture: {0}".format(source_rel))

        if language == "rust":
            rust_unresolved = [
                {
                    "errno": item["errno"],
                    "first_stage_site_ids": [item["id"]],
                    "kind": "rust_failure_site_mir_not_captured",
                    "line": item["line"],
                    "source": source_rel,
                }
                for item in sorted(
                    expected_source_sites,
                    key=lambda value: (
                        value["line"], value["column"], value["id"]
                    ),
                )
            ]
            if not rust_unresolved:
                rust_unresolved.append(
                    {
                        "kind": "rust_mir_and_cfg_not_captured",
                        "source": source_rel,
                    }
                )
            all_unresolved.extend(rust_unresolved)
            output_sources.append(
                {
                    "active_compile_profile": profile_record,
                    "active_compile_profile_sha256": active_profile_sha256,
                    "analysis_status": "unresolved",
                    "blockers": ["rust_mir_and_cfg_not_captured"],
                    "flow_count": 0,
                    "function_count": 0,
                    "language": language,
                    "module": module,
                    "source": source_rel,
                    "source_sha256": source_digest,
                    "unresolved_count": len(rust_unresolved),
                }
            )
            continue

        argv = expected_record["compile_argv"]
        source_index = source_index_in_argv(argv, source_path, kernel_dir)
        ir = run_ir_for_source(argv, source_index, kernel_dir, roots, environment)
        active_rows_output, _ = failure_sites.run_preprocessor(
            failure_sites.reconstruct_preprocess_argv(
                {"compile_argv": argv}, source_index
            ),
            kernel_dir,
            environment,
        )
        active_rows = failure_sites.filter_target_lines(
            active_rows_output, source_path, kernel_dir
        )
        analysis = analyze_ir_source(
            module, source_rel, source_path, source_digest,
            active_profile_sha256, expected_record["digests"]["compiler_sha256"],
            ir, active_rows, expected_source_sites, kernel_dir,
        )
        total_functions += len(analysis["functions"])
        all_flows.extend(analysis["flows"])
        all_unresolved.extend(analysis["unresolved"])
        output_sources.append(
            {
                "active_compile_profile": profile_record,
                "active_compile_profile_sha256": active_profile_sha256,
                "analysis_argv": ir["analysis_argv"],
                "analysis_status": "bounded_compiler_checkpoint",
                "blockers": sorted(
                    set(item["kind"] for item in analysis["unresolved"])
                ),
                "flow_count": len(analysis["flows"]),
                "function_count": len(analysis["functions"]),
                "functions": analysis["functions"],
                "language": language,
                "module": module,
                "provenance": analysis["provenance"],
                "provenance_sha256": analysis["provenance_sha256"],
                "source": source_rel,
                "source_sha256": source_digest,
                "unresolved_count": len(analysis["unresolved"]),
            }
        )

    ids = [item["id"] for item in all_flows]
    if len(ids) != len(set(ids)):
        raise FlowError("failure-flow IDs collide across sources")
    mapped_failure_site_ids = collect_first_stage_ids(all_flows, all_unresolved)
    expected_failure_site_ids = set(
        item["id"] for item in capture["failure_sites"]
    )
    if mapped_failure_site_ids != expected_failure_site_ids:
        raise FlowError(
            "bounded flow capture did not retain every explicit failure-site mapping"
        )
    all_flows.sort(
        key=lambda item: (
            item["module"], item["source"], item["location"]["line"],
            item["location"]["column"] or 0, item["expression_role"], item["id"],
        )
    )
    all_unresolved = sorted(
        {canonical_bytes(item): item for item in all_unresolved}.values(),
        key=lambda item: canonical_bytes(item),
    )
    by_role = {}
    by_module = {}
    for flow in all_flows:
        by_role[flow["expression_role"]] = by_role.get(flow["expression_role"], 0) + 1
        by_module[flow["module"]] = by_module.get(flow["module"], 0) + 1
    return {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "blockers": list(FIXED_BLOCKERS),
        "coverage": {
            "by_module": dict(sorted(by_module.items())),
            "by_role": dict(sorted(by_role.items())),
            "c_source_count": sum(1 for item in output_sources if item["language"] == "c"),
            "explicit_failure_site_input_count": len(capture["failure_sites"]),
            "explicit_failure_site_mapped_count": len(mapped_failure_site_ids),
            "flow_count": len(all_flows),
            "function_count": total_functions,
            "rust_source_count": sum(1 for item in output_sources if item["language"] == "rust"),
            "source_count": len(output_sources),
            "unresolved_count": len(all_unresolved),
        },
        "failure_flows": all_flows,
        "generator": "scripts/host_module_failure_flows.py",
        "input_failure_sites": {
            "artifact_bytes": capture_file["bytes"],
            "artifact_sha256": capture_file["sha256"],
            "profile": capture["profile"],
            "repository_commit": capture.get("provenance", {}).get("repository_commit"),
        },
        "profile": PROFILE,
        "schema_version": SCHEMA_VERSION,
        "sources": output_sources,
        "unresolved_paths": all_unresolved,
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
    parser.add_argument("--failure-sites", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-exhaustive",
        action="store_true",
        help="fail closed; schema v1 can never satisfy this gate",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    if args.require_exhaustive:
        print(
            "host-module failure-flow capture is non-exhaustive by schema; FP-0006 remains IN_PROGRESS",
            file=sys.stderr,
        )
        return 1
    try:
        capture = build_capture(
            args.repo, args.build_dir, args.kernel_dir, args.failure_sites,
            args.config,
        )
        write_capture(args.output, capture)
    except (FlowError, failure_sites.CaptureError) as exc:
        print("host-module failure-flow capture failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "captured {0} bounded failure flows across {1} C functions; "
        "{2} paths remain unresolved and FP-0006 stays IN_PROGRESS".format(
            capture["coverage"]["flow_count"],
            capture["coverage"]["function_count"],
            capture["coverage"]["unresolved_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
