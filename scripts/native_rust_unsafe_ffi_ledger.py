#!/usr/bin/env python3
"""Validate the fail-closed RS-011 native Rust unsafe/FFI ledger.

The committed ledger is a source-bound review queue, not gate evidence.  This
checker discovers the three native Rust crate roots from the authoritative
stage manifest, walks literal ``mod`` and ``include!`` edges within the project
Rust source root, lexes every reachable input, and accounts for each explicit
unsafe or FFI boundary.  Exact source bytes and normalized token expressions
are independently digested so formatting-only and semantic changes are
distinguishable without making the durable site ID source-derived.

``capture-compiler`` is the compiler-evidence hook.  It consumes the exact
Kbuild ``.cmd`` and rustc dep-info files for all three crates and proves that
the compiled project Rust input closure byte-matches the ledger.  It also binds
the compiler, object, command, dep-info, and RS-001 platform evidence digests.
Neither source validation nor compiler capture can award RS-011 credit;
compiler-expanded unsafe-operation capture and independent review remain
mandatory blockers.
"""

from __future__ import print_function

import argparse
import bisect
import copy
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile


REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = "host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json"
STAGE_MANIFEST_PATH = "host-kernel/kbuild/stage-manifest.json"
SOURCE_LOCK_PATH = "host-kernel/rocky/source-lock.json"
CONFIG_POLICY_PATH = "host-kernel/rocky/config-policy.json"
TOOLCHAIN_LOCK_PATH = "host-kernel/rocky/toolchain-lock.json"
NATIVE_SOURCE_ROOT = "host-kernel/native-rust"
SCHEMA_VERSION = 1
LEDGER_ID = "mckernel-native-rust-unsafe-ffi-ledger-v1"
COMPILER_PROFILE = "mckernel-rs011-compiler-closure-evidence-v1"
EXPECTED_CRATES = ("ihk", "ihk_smp_x86_64", "mcctrl")
EXPECTED_ROOTS = {
    "ihk": "host-kernel/native-rust/ihk.rs",
    "ihk_smp_x86_64": "host-kernel/native-rust/ihk_smp_x86_64.rs",
    "mcctrl": "host-kernel/native-rust/mcctrl.rs",
}
SITE_KINDS = (
    "unsafe_block",
    "unsafe_impl",
    "unsafe_function",
    "unsafe_trait",
    "foreign_block",
    "extern_function",
    "ffi_export",
    "mutable_static",
    "inline_asm",
    "global_asm",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SITE_ID = re.compile(r"^RS011-(?:IHK|SMP|MCC)-[0-9]{4}$")
MAKE_ASSIGNMENT = re.compile(r"^(?P<kind>cmd|source)_(?P<key>.+?)\s*:=\s*(?P<value>.*)$")
CONTROL_TOKENS = frozenset((";", "&&", "||", "|", "&", ">", ">>", "<", "<<", "<>", "&>"))
COMPILER_BLOCKERS = (
    "compiler-expanded unsafe-operation/span capture is not supplied by the selected Rust-for-Linux build",
    "independent owner and unsafe-code review is not registered as immutable evidence",
    "this capture is evidence input only and cannot award RS-011 gate credit",
)
SOURCE_BLOCKERS = (
    "exact Rocky 10.2 rustc commands, dep-info closure, objects, source, config, and toolchain evidence are absent",
    "compiler-expanded unsafe-operation/span capture has not been cross-validated",
    "independent owner and unsafe-code review has not been registered as immutable evidence",
    "source inventory cannot self-attest or award RS-011 gate credit",
)


class LedgerError(Exception):
    """Raised for incomplete, ambiguous, or stale RS-011 evidence."""


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except (IOError, OSError) as error:
        raise LedgerError("cannot hash {0}: {1}".format(path, error))
    return digest.hexdigest()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LedgerError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def read_json(path, label):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=reject_duplicate_keys)
    except LedgerError:
        raise
    except (IOError, OSError, UnicodeError, ValueError) as error:
        raise LedgerError("cannot parse {0}: {1}".format(label, error))
    if not isinstance(value, dict):
        raise LedgerError("{0} must contain one JSON object".format(label))
    return value


def require_keys(value, expected, label):
    if not isinstance(value, dict):
        raise LedgerError("{0} must be an object".format(label))
    actual = set(value)
    expected = set(expected)
    if actual != expected:
        raise LedgerError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )
    return value


def require_nonempty_strings(value, label):
    if not isinstance(value, list) or not value:
        raise LedgerError("{0} must be a non-empty list".format(label))
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise LedgerError("{0} entries must be non-empty strings".format(label))
    if len(value) != len(set(value)):
        raise LedgerError("{0} contains duplicate entries".format(label))


def safe_relative(value, label):
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise LedgerError("{0} is not a normalized repository path".format(label))
    normalized = os.path.normpath(value)
    if normalized != value or value == "." or value.startswith("../") or "/../" in value:
        raise LedgerError("{0} is not a normalized repository path".format(label))
    return value


def regular_file(path, label):
    path = os.path.abspath(path)
    try:
        info = os.lstat(path)
    except OSError as error:
        raise LedgerError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise LedgerError("{0} must be a regular non-symlink file".format(label))
    if os.path.realpath(path) != path:
        raise LedgerError("{0} traverses a symlink".format(label))
    return path


def directory(path, label):
    path = os.path.abspath(path)
    try:
        info = os.lstat(path)
    except OSError as error:
        raise LedgerError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise LedgerError("{0} must be a real non-symlink directory".format(label))
    if os.path.realpath(path) != path:
        raise LedgerError("{0} traverses a symlink".format(label))
    return path


def within(path, root, label):
    path = os.path.realpath(path)
    root = os.path.realpath(root)
    try:
        contained = os.path.commonpath((path, root)) == root
    except ValueError:
        contained = False
    if not contained:
        raise LedgerError("{0} escapes {1}: {2}".format(label, root, path))
    return path


def repository_file(repo, relative, label):
    relative = safe_relative(relative, label)
    repo = os.path.realpath(repo)
    requested = os.path.join(repo, *relative.split("/"))
    resolved = within(requested, repo, label)
    if requested != resolved:
        raise LedgerError("{0} traverses a symlink".format(label))
    return regular_file(requested, label)


def read_source(path, label):
    path = regular_file(path, label)
    try:
        with open(path, "rb") as stream:
            raw = stream.read()
        text = raw.decode("utf-8")
    except (IOError, OSError, UnicodeError) as error:
        raise LedgerError("cannot read {0}: {1}".format(label, error))
    if "\x00" in text:
        raise LedgerError("{0} contains NUL".format(label))
    return raw, text


def ledger_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("ledger_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def evidence_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("evidence_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def line_starts(text):
    starts = [0]
    for match in re.finditer("\n", text):
        starts.append(match.end())
    return starts


def position(starts, offset):
    line_index = bisect.bisect_right(starts, offset) - 1
    return line_index + 1, offset - starts[line_index] + 1


def _raw_string_prefix(text, index):
    cursor = index
    if text.startswith("br", cursor) or text.startswith("cr", cursor):
        cursor += 2
    elif text.startswith("r", cursor):
        cursor += 1
    else:
        return None
    hashes = 0
    while cursor < len(text) and text[cursor] == "#":
        hashes += 1
        cursor += 1
    if cursor >= len(text) or text[cursor] != '"':
        return None
    return cursor + 1, '"' + ("#" * hashes)


def _quoted_end(text, index, quote):
    cursor = index + 1
    while cursor < len(text):
        if text[cursor] == "\\":
            cursor += 2
            continue
        if text[cursor] == quote:
            return cursor + 1
        if quote == "'" and text[cursor] == "\n":
            break
        cursor += 1
    raise LedgerError("unterminated Rust literal at byte {0}".format(index))


def lex_rust(text, label="Rust source"):
    """Return comment-aware Rust tokens without expanding macros."""

    tokens = []
    comments = []
    starts = line_starts(text)
    length = len(text)
    index = 0
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index)
            if end < 0:
                end = length
            start_line, start_column = position(starts, index)
            end_line, end_column = position(starts, max(index, end - 1))
            comments.append(
                {
                    "kind": "line",
                    "start": index,
                    "end": end,
                    "line_start": start_line,
                    "column_start": start_column,
                    "line_end": end_line,
                    "column_end": end_column,
                    "raw": text[index:end],
                }
            )
            index = end
            continue
        if text.startswith("/*", index):
            cursor = index + 2
            depth = 1
            while cursor < length and depth:
                if text.startswith("/*", cursor):
                    depth += 1
                    cursor += 2
                elif text.startswith("*/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise LedgerError("unterminated nested block comment in {0}".format(label))
            start_line, start_column = position(starts, index)
            end_line, end_column = position(starts, cursor - 1)
            comments.append(
                {
                    "kind": "block",
                    "start": index,
                    "end": cursor,
                    "line_start": start_line,
                    "column_start": start_column,
                    "line_end": end_line,
                    "column_end": end_column,
                    "raw": text[index:cursor],
                }
            )
            index = cursor
            continue

        raw_prefix = _raw_string_prefix(text, index)
        if raw_prefix is not None:
            body_start, terminator = raw_prefix
            close = text.find(terminator, body_start)
            if close < 0:
                raise LedgerError("unterminated raw Rust string in {0}".format(label))
            end = close + len(terminator)
            kind = "string"
        elif char == '"' or (
            char in ("b", "c") and index + 1 < length and text[index + 1] == '"'
        ):
            quote_index = index if char == '"' else index + 1
            end = _quoted_end(text, quote_index, '"')
            kind = "string"
        elif char == "'" and index + 2 < length and (
            text[index + 1] == "\\" or text[index + 2] == "'"
        ):
            end = _quoted_end(text, index, "'")
            kind = "char"
        elif char == "b" and index + 2 < length and text[index + 1] == "'":
            end = _quoted_end(text, index + 1, "'")
            kind = "char"
        elif char == "_" or char.isalpha():
            end = index + 1
            while end < length and (text[end] == "_" or text[end].isalnum()):
                end += 1
            kind = "ident"
        elif char.isdigit():
            end = index + 1
            while end < length and (text[end].isalnum() or text[end] in "_."):
                end += 1
            kind = "number"
        else:
            end = index + 1
            kind = "punct"
        start_line, start_column = position(starts, index)
        end_line, end_column = position(starts, end - 1)
        tokens.append(
            {
                "kind": kind,
                "text": text[index:end],
                "start": index,
                "end": end,
                "line_start": start_line,
                "column_start": start_column,
                "line_end": end_line,
                "column_end": end_column,
            }
        )
        index = end
    return tokens, comments


def delimiter_pairs(tokens, label):
    opening = {"(": ")", "[": "]", "{": "}"}
    closing = {value: key for key, value in opening.items()}
    stack = []
    pairs = {}
    for index, token in enumerate(tokens):
        value = token["text"]
        if value in opening:
            stack.append((value, index))
        elif value in closing:
            if not stack or stack[-1][0] != closing[value]:
                raise LedgerError("unbalanced delimiter in {0}".format(label))
            unused, begin = stack.pop()
            pairs[begin] = index
            pairs[index] = begin
    if stack:
        raise LedgerError("unclosed delimiter in {0}".format(label))
    return pairs


def attribute_ranges(tokens, pairs):
    result = []
    index = 0
    while index + 1 < len(tokens):
        if tokens[index]["text"] == "#" and tokens[index + 1]["text"] == "[":
            close = pairs[index + 1]
            result.append((index, close))
            index = close + 1
        else:
            index += 1
    return result


def normalize_comment(raw):
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        value = line.strip()
        if value.startswith("//"):
            value = value[2:]
        elif value.startswith("/*"):
            value = value[2:]
        if value.endswith("*/"):
            value = value[:-2]
        value = value.strip()
        if value.startswith("*"):
            value = value[1:].strip()
        cleaned.append(value)
    return " ".join(item for item in cleaned if item).strip()


def safety_comments(text, comments):
    groups = []
    for comment in comments:
        if (
            groups
            and comment["kind"] == "line"
            and groups[-1][-1]["kind"] == "line"
            and comment["line_start"] == groups[-1][-1]["line_end"] + 1
        ):
            groups[-1].append(comment)
        else:
            groups.append([comment])
    result = []
    for group in groups:
        start = group[0]["start"]
        end = group[-1]["end"]
        raw = text[start:end]
        normalized = normalize_comment(raw)
        marker = normalized.find("SAFETY:")
        if marker < 0:
            continue
        normalized = normalized[marker:]
        result.append(
            {
                "text": normalized,
                "source_sha256": sha256_bytes(raw.encode("utf-8")),
                "line_start": group[0]["line_start"],
                "line_end": group[-1]["line_end"],
                "start": start,
                "end": end,
            }
        )
    return result


def canonical_token_digest(tokens, begin, end):
    values = [token["text"] for token in tokens if token["start"] >= begin and token["end"] <= end]
    if not values:
        raise LedgerError("site contains no Rust tokens")
    return sha256_bytes(canonical_bytes(values))


def _item_end(tokens, pairs, start_index):
    nesting = 0
    index = start_index
    while index < len(tokens):
        value = tokens[index]["text"]
        if value in ("(", "["):
            index = pairs[index] + 1
            continue
        if value == "{":
            return pairs[index]
        if value == ";" and nesting == 0:
            return index
        index += 1
    raise LedgerError("cannot find the end of an unsafe/FFI item")


def _statement_end(tokens, pairs, start_index):
    index = start_index
    while index < len(tokens):
        value = tokens[index]["text"]
        if value in ("(", "[", "{"):
            index = pairs[index] + 1
            continue
        if value == ";":
            return index
        index += 1
    raise LedgerError("cannot find the end of a static declaration")


def _export_item_end(tokens, pairs, start_index):
    """Find the end of an exported fn or data item after its attributes."""

    cursor = start_index
    if cursor < len(tokens) and tokens[cursor]["text"] == "pub":
        cursor += 1
        if cursor < len(tokens) and tokens[cursor]["text"] == "(":
            cursor = pairs[cursor] + 1
    while cursor < len(tokens) and tokens[cursor]["text"] in ("unsafe", "extern"):
        cursor += 1
        if cursor < len(tokens) and tokens[cursor]["kind"] == "string":
            cursor += 1
    if cursor < len(tokens) and tokens[cursor]["text"] == "fn":
        return _item_end(tokens, pairs, cursor)
    return _statement_end(tokens, pairs, cursor)


def _macro_ranges(tokens, pairs):
    result = []
    for index, token in enumerate(tokens):
        if token["text"] != "macro_rules" or index + 3 >= len(tokens):
            continue
        if tokens[index + 1]["text"] != "!" or tokens[index + 2]["kind"] != "ident":
            continue
        if tokens[index + 3]["text"] != "{":
            continue
        result.append((tokens[index + 2]["text"], index, pairs[index + 3]))
    return result


def discover_sites(relative, raw, text):
    tokens, comments = lex_rust(text, relative)
    pairs = delimiter_pairs(tokens, relative)
    attrs = attribute_ranges(tokens, pairs)
    attr_indices = set()
    for begin, end in attrs:
        attr_indices.update(range(begin, end + 1))
    macros = _macro_ranges(tokens, pairs)
    spans = []

    def add(kind, token_begin, token_end):
        begin = tokens[token_begin]["start"]
        end = tokens[token_end]["end"]
        key = (kind, begin, end)
        if key not in {(item[0], item[1], item[2]) for item in spans}:
            spans.append((kind, begin, end, token_begin, token_end))

    for index, token in enumerate(tokens):
        if token["text"] != "unsafe" or index in attr_indices:
            continue
        if index + 1 >= len(tokens):
            raise LedgerError("dangling unsafe token in {0}".format(relative))
        following = tokens[index + 1]["text"]
        if following == "{":
            add("unsafe_block", index, pairs[index + 1])
        elif following == "impl":
            add("unsafe_impl", index, _item_end(tokens, pairs, index))
        elif following == "fn":
            add("unsafe_function", index, _item_end(tokens, pairs, index))
        elif following == "trait":
            add("unsafe_trait", index, _item_end(tokens, pairs, index))
        elif following == "extern":
            # The extern pass below records this as one foreign block.
            continue
        else:
            raise LedgerError(
                "unclassified unsafe syntax in {0} at line {1}".format(relative, token["line_start"])
            )

    for index, token in enumerate(tokens):
        if token["text"] != "extern":
            continue
        cursor = index + 1
        if cursor < len(tokens) and tokens[cursor]["kind"] == "string":
            cursor += 1
        if cursor < len(tokens) and tokens[cursor]["text"] == "{":
            begin = index - 1 if index > 0 and tokens[index - 1]["text"] == "unsafe" else index
            add("foreign_block", begin, pairs[cursor])
        elif cursor < len(tokens) and tokens[cursor]["text"] == "fn":
            begin = index - 1 if index > 0 and tokens[index - 1]["text"] == "unsafe" else index
            add("extern_function", begin, _item_end(tokens, pairs, begin))
        elif cursor < len(tokens) and tokens[cursor]["text"] == "crate":
            continue

    for attr_begin, attr_end in attrs:
        names = [token["text"] for token in tokens[attr_begin : attr_end + 1] if token["kind"] == "ident"]
        if "export_name" not in names and "no_mangle" not in names:
            continue
        item_begin = attr_end + 1
        while item_begin < len(tokens) and tokens[item_begin]["text"] == "#":
            if item_begin + 1 >= len(tokens) or tokens[item_begin + 1]["text"] != "[":
                break
            item_begin = pairs[item_begin + 1] + 1
        add("ffi_export", attr_begin, _export_item_end(tokens, pairs, item_begin))

    for index, token in enumerate(tokens):
        if token["text"] == "static" and index + 1 < len(tokens) and tokens[index + 1]["text"] == "mut":
            add("mutable_static", index, _statement_end(tokens, pairs, index))
        if token["kind"] == "ident" and token["text"] in ("asm", "global_asm"):
            if index + 2 < len(tokens) and tokens[index + 1]["text"] == "!" and tokens[index + 2]["text"] in ("(", "[", "{"):
                kind = "inline_asm" if token["text"] == "asm" else "global_asm"
                add(kind, index, pairs[index + 2])

    safety = safety_comments(text, comments)
    used_comments = set()
    sites = []
    for kind, begin, end, token_begin, unused_token_end in sorted(spans, key=lambda item: (item[1], item[2], item[0])):
        del unused_token_end
        start_line, start_column = position(line_starts(text), begin)
        end_line, end_column = position(line_starts(text), end - 1)
        candidates = [
            (idx, comment)
            for idx, comment in enumerate(safety)
            if idx not in used_comments
            and comment["end"] <= begin
            and start_line - comment["line_end"] <= 8
            and "\n\n" not in text[comment["end"] : begin].replace("\r", "")
        ]
        if not candidates:
            raise LedgerError(
                "{0}:{1} {2} lacks a unique nearby SAFETY comment".format(relative, start_line, kind)
            )
        comment_index, comment = max(candidates, key=lambda item: item[1]["end"])
        used_comments.add(comment_index)
        macro_name = None
        for name, macro_begin, macro_end in macros:
            if macro_begin <= token_begin <= macro_end:
                macro_name = name
                break
        source_bytes = text[begin:end].encode("utf-8")
        sites.append(
            {
                "kind": kind,
                "path": relative,
                "file_sha256": sha256_bytes(raw),
                "byte_start": len(text[:begin].encode("utf-8")),
                "byte_end": len(text[:end].encode("utf-8")),
                "line_start": start_line,
                "column_start": start_column,
                "line_end": end_line,
                "column_end": end_column,
                "source_sha256": sha256_bytes(source_bytes),
                "expression_sha256": canonical_token_digest(tokens, begin, end),
                "macro_context": macro_name,
                "safety_comment": {
                    "text": comment["text"],
                    "source_sha256": comment["source_sha256"],
                    "line_start": comment["line_start"],
                    "line_end": comment["line_end"],
                },
            }
        )
    return sites, tokens, pairs, attrs


def decode_rust_string(token, label):
    value = token["text"]
    match = re.match(r"^(?:b|c)?r(?P<hashes>#{0,})\"(?P<body>.*)\"(?P=hashes)$", value, re.DOTALL)
    if match:
        return match.group("body")
    if value.startswith(('b"', 'c"')):
        value = value[1:]
    if not (value.startswith('"') and value.endswith('"')):
        raise LedgerError("{0} must be one literal Rust string".format(label))
    body = value[1:-1]
    if "\\" in body:
        # Module/include paths never need escapes; rejecting them avoids a
        # second, subtly different Rust string decoder in this authority.
        raise LedgerError("{0} may not use escaped path bytes".format(label))
    return body


def _path_attribute(tokens, pairs, attrs, mod_index):
    cursor = mod_index - 1
    matching = []
    while cursor >= 0 and tokens[cursor]["text"] == "]":
        begin_bracket = pairs[cursor]
        if begin_bracket == 0 or tokens[begin_bracket - 1]["text"] != "#":
            break
        body = tokens[begin_bracket + 1 : cursor]
        if body and body[0]["text"] == "path":
            if len(body) != 3 or body[1]["text"] != "=" or body[2]["kind"] != "string":
                raise LedgerError("#[path] must contain one literal string")
            matching.append(decode_rust_string(body[2], "#[path]"))
        cursor = begin_bracket - 2
    if len(matching) > 1:
        raise LedgerError("external module has multiple #[path] attributes")
    return matching[0] if matching else None


def rust_dependencies(repo, relative, text, tokens, pairs, attrs, is_root):
    repo_native = os.path.join(os.path.realpath(repo), *NATIVE_SOURCE_ROOT.split("/"))
    source = repository_file(repo, relative, "Rust source")
    source_dir = os.path.dirname(source)
    dependencies = []
    for index, token in enumerate(tokens):
        if token["text"] == "include" and index + 2 < len(tokens) and tokens[index + 1]["text"] == "!":
            opening = index + 2
            if tokens[opening]["text"] != "(":
                raise LedgerError("include! must use parentheses in {0}".format(relative))
            closing = pairs[opening]
            args = tokens[opening + 1 : closing]
            if len(args) != 1 or args[0]["kind"] != "string":
                raise LedgerError("dynamic include! is forbidden in project Rust closure: {0}".format(relative))
            included = decode_rust_string(args[0], "include! path")
            if not included.endswith(".rs"):
                raise LedgerError("project include! input must use .rs: {0}".format(included))
            candidate = os.path.normpath(os.path.join(source_dir, included))
            within(candidate, repo_native, "include! input")
            candidate = regular_file(candidate, "include! input")
            dependencies.append(os.path.relpath(candidate, os.path.realpath(repo)).replace(os.sep, "/"))
        if token["text"] != "mod" or index + 2 >= len(tokens) or tokens[index + 1]["kind"] != "ident":
            continue
        if tokens[index + 2]["text"] == "{":
            continue
        if tokens[index + 2]["text"] != ";":
            continue
        module_name = tokens[index + 1]["text"]
        explicit = _path_attribute(tokens, pairs, attrs, index)
        if explicit is not None:
            candidates = [os.path.normpath(os.path.join(source_dir, explicit))]
        else:
            basename = os.path.basename(source)
            if is_root or basename == "mod.rs":
                module_dir = source_dir
            else:
                module_dir = os.path.join(source_dir, os.path.splitext(basename)[0])
            candidates = [
                os.path.join(module_dir, module_name + ".rs"),
                os.path.join(module_dir, module_name, "mod.rs"),
            ]
        present = []
        for candidate in candidates:
            try:
                info = os.lstat(candidate)
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode):
                present.append(candidate)
        if len(present) != 1:
            raise LedgerError(
                "external module {0} in {1} resolves to {2} project files".format(
                    module_name, relative, len(present)
                )
            )
        candidate = within(present[0], repo_native, "external Rust module")
        candidate = regular_file(candidate, "external Rust module")
        dependencies.append(os.path.relpath(candidate, os.path.realpath(repo)).replace(os.sep, "/"))
    return sorted(set(dependencies))


def stage_roots(repo):
    path = repository_file(repo, STAGE_MANIFEST_PATH, "native Rust stage manifest")
    manifest = read_json(path, "native Rust stage manifest")
    modules = manifest.get("modules")
    if not isinstance(modules, list) or len(modules) != len(EXPECTED_CRATES):
        raise LedgerError("stage manifest must contain exactly three native Rust modules")
    roots = []
    for expected, module in zip(EXPECTED_CRATES, modules):
        if not isinstance(module, dict) or module.get("crate") != expected:
            raise LedgerError("stage manifest crate order/identity changed")
        source = module.get("source")
        if not isinstance(source, dict) or source.get("repository_path") != EXPECTED_ROOTS[expected]:
            raise LedgerError("stage manifest redirected the {0} crate root".format(expected))
        source_path = repository_file(repo, source["repository_path"], expected + " crate root")
        if source.get("sha256") != sha256_file(source_path):
            raise LedgerError("stage manifest {0} crate-root digest is stale".format(expected))
        roots.append(
            {
                "crate": expected,
                "path": source["repository_path"],
                "destination": source.get("destination"),
                "sha256": source["sha256"],
            }
        )
    return roots, manifest, path


def discover(repo):
    repo = os.path.realpath(repo)
    roots, unused_manifest, unused_manifest_path = stage_roots(repo)
    del unused_manifest, unused_manifest_path
    by_path = {}
    memberships = {}
    root_inputs = {}
    for root in roots:
        pending = [(root["path"], True)]
        seen = set()
        while pending:
            relative, is_root = pending.pop()
            if relative in seen:
                continue
            seen.add(relative)
            path = repository_file(repo, relative, "reachable project Rust input")
            raw, text = read_source(path, relative)
            sites, tokens, pairs, attrs = discover_sites(relative, raw, text)
            if relative in by_path:
                if by_path[relative]["sha256"] != sha256_bytes(raw):
                    raise LedgerError("shared Rust input changed during discovery: {0}".format(relative))
            else:
                by_path[relative] = {
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                    "sites": sites,
                }
            memberships.setdefault(relative, set()).add(root["crate"])
            for dependency in rust_dependencies(repo, relative, text, tokens, pairs, attrs, is_root):
                pending.append((dependency, False))
        root_inputs[root["crate"]] = sorted(seen)

    inputs = []
    sites = []
    for relative in sorted(by_path):
        record = by_path[relative]
        crates = sorted(memberships[relative], key=EXPECTED_CRATES.index)
        inputs.append(
            {
                "path": relative,
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "crate_roots": crates,
            }
        )
        for site in record["sites"]:
            item = copy.deepcopy(site)
            item["crate_roots"] = crates
            sites.append(item)
    sites.sort(key=lambda item: (item["path"], item["byte_start"], item["kind"]))
    root_records = []
    for root in roots:
        values = root_inputs[root["crate"]]
        root_records.append(
            {
                "crate": root["crate"],
                "path": root["path"],
                "destination": root["destination"],
                "sha256": root["sha256"],
                "transitive_inputs": values,
                "transitive_inputs_sha256": sha256_bytes(canonical_bytes(values)),
            }
        )
    return {
        "roots": root_records,
        "inputs": inputs,
        "source_closure_sha256": sha256_bytes(canonical_bytes(inputs)),
        "sites": sites,
    }


def lock_record(repo, relative, label):
    path = repository_file(repo, relative, label)
    value = read_json(path, label)
    return value, {"path": relative, "sha256": sha256_file(path)}


def expected_locks(repo):
    source, source_record = lock_record(repo, SOURCE_LOCK_PATH, "Rocky source lock")
    config, config_record = lock_record(repo, CONFIG_POLICY_PATH, "Rocky config policy")
    toolchain, toolchain_record = lock_record(repo, TOOLCHAIN_LOCK_PATH, "Rocky toolchain lock")
    unused_stage, stage_record = lock_record(repo, STAGE_MANIFEST_PATH, "native Rust stage manifest")
    del unused_stage
    if source.get("lock_id") != config.get("source_lock_id"):
        raise LedgerError("source/config lock identity diverged")
    if source.get("lock_id") != toolchain.get("source_lock", {}).get("lock_id"):
        raise LedgerError("source/toolchain lock identity diverged")
    target = source.get("target", {})
    rpm = source.get("source_rpm", {})
    expected_target = {
        "distribution": "Rocky Linux",
        "release": "10.2",
        "architecture": "x86_64",
        "kernel_nvr": rpm.get("nvr"),
        "source_rpm_sha256": rpm.get("sha256"),
        "source_lock_id": source.get("lock_id"),
        "config_policy_id": config.get("lock_id"),
        "toolchain_lock_id": toolchain.get("lock_id"),
    }
    if target.get("distribution") != "Rocky Linux" or target.get("release") != "10.2" or target.get("architecture") != "x86_64":
        raise LedgerError("RS-011 locks are not Rocky Linux 10.2 x86_64")
    return {
        "source_lock": source_record,
        "config_policy": config_record,
        "toolchain_lock": toolchain_record,
        "stage_manifest": stage_record,
    }, expected_target


def mechanical_site(site):
    return {
        key: copy.deepcopy(site[key])
        for key in (
            "kind",
            "path",
            "file_sha256",
            "byte_start",
            "byte_end",
            "line_start",
            "column_start",
            "line_end",
            "column_end",
            "source_sha256",
            "expression_sha256",
            "macro_context",
            "crate_roots",
            "safety_comment",
        )
    }


def validate_ledger(ledger, repo):
    require_keys(
        ledger,
        {
            "schema_version",
            "ledger_id",
            "ledger_sha256",
            "gate",
            "target",
            "repository_locks",
            "scope",
            "crate_roots",
            "source_inputs",
            "source_closure_sha256",
            "sites",
            "coverage",
            "readiness",
        },
        "RS-011 ledger",
    )
    if ledger["schema_version"] != SCHEMA_VERSION or ledger["ledger_id"] != LEDGER_ID:
        raise LedgerError("RS-011 ledger schema/identity changed")
    if ledger["ledger_sha256"] != ledger_digest(ledger):
        raise LedgerError("RS-011 ledger digest is stale")
    locks, target = expected_locks(repo)
    if ledger["repository_locks"] != locks or ledger["target"] != target:
        raise LedgerError("RS-011 target or repository lock bindings changed")
    gate = require_keys(
        ledger["gate"],
        {"gate_id", "credit_eligible", "self_attestation_forbidden", "independent_review_required"},
        "RS-011 gate policy",
    )
    if gate != {
        "gate_id": "RS-011",
        "credit_eligible": False,
        "self_attestation_forbidden": True,
        "independent_review_required": True,
    }:
        raise LedgerError("RS-011 ledger permits self-attested credit")
    scope = require_keys(
        ledger["scope"],
        {"native_source_root", "crate_count", "site_kinds", "source_discovery", "compiler_cross_validation"},
        "RS-011 scope",
    )
    if scope != {
        "native_source_root": NATIVE_SOURCE_ROOT,
        "crate_count": 3,
        "site_kinds": list(SITE_KINDS),
        "source_discovery": "literal transitive mod/include closure; unresolved or escaping inputs fail closed",
        "compiler_cross_validation": "exact Kbuild command plus rustc dep-info/object/tool/platform digests required",
    }:
        raise LedgerError("RS-011 ledger scope was weakened")

    discovery = discover(repo)
    if ledger["crate_roots"] != discovery["roots"]:
        raise LedgerError("crate-root/transitive input closure is stale")
    if ledger["source_inputs"] != discovery["inputs"]:
        raise LedgerError("project Rust source input ledger is stale")
    if ledger["source_closure_sha256"] != discovery["source_closure_sha256"]:
        raise LedgerError("project Rust source closure digest is stale")

    committed = ledger["sites"]
    if not isinstance(committed, list) or len(committed) != len(discovery["sites"]):
        raise LedgerError("unsafe/FFI site count differs from source discovery")
    ids = []
    for index, (record, found) in enumerate(zip(committed, discovery["sites"])):
        require_keys(
            record,
            set(mechanical_site(found))
            | {
                "id",
                "caller_obligations",
                "context_constraints",
                "owner",
                "compiler_capture",
                "independent_review",
            },
            "site[{0}]".format(index),
        )
        site_id = record["id"]
        if not isinstance(site_id, str) or not SITE_ID.match(site_id):
            raise LedgerError("site[{0}] has malformed durable ID".format(index))
        ids.append(site_id)
        for key, value in mechanical_site(found).items():
            if record.get(key) != value:
                raise LedgerError("{0} mechanical field changed for {1}".format(key, site_id))
        require_nonempty_strings(record["caller_obligations"], site_id + ".caller_obligations")
        require_nonempty_strings(record["context_constraints"], site_id + ".context_constraints")
        owner = require_keys(record["owner"], {"component", "accountable_role"}, site_id + ".owner")
        if any(not isinstance(owner[key], str) or not owner[key].strip() for key in owner):
            raise LedgerError("{0} owner fields must be non-empty".format(site_id))
        capture = require_keys(
            record["compiler_capture"],
            {"required", "status", "evidence_sha256"},
            site_id + ".compiler_capture",
        )
        if capture != {"required": True, "status": "not_captured", "evidence_sha256": None}:
            raise LedgerError("{0} overclaims compiler cross-validation".format(site_id))
        review = require_keys(
            record["independent_review"],
            {"required", "status", "reviewer", "evidence_sha256"},
            site_id + ".independent_review",
        )
        if review != {
            "required": True,
            "status": "pending",
            "reviewer": None,
            "evidence_sha256": None,
        }:
            raise LedgerError("{0} overclaims independent review".format(site_id))
    if len(ids) != len(set(ids)):
        raise LedgerError("durable unsafe/FFI site IDs are duplicated")

    by_kind = {}
    by_crate = {crate: 0 for crate in EXPECTED_CRATES}
    for record in committed:
        by_kind[record["kind"]] = by_kind.get(record["kind"], 0) + 1
        for crate in record["crate_roots"]:
            by_crate[crate] += 1
    coverage = {
        "source_input_count": len(discovery["inputs"]),
        "site_count": len(committed),
        "site_ids_sha256": sha256_bytes(canonical_bytes(ids)),
        "by_kind": {key: by_kind[key] for key in sorted(by_kind)},
        "by_crate": {key: by_crate[key] for key in EXPECTED_CRATES},
        "source_inventory_status": "complete_for_locked_source_bytes",
    }
    if ledger["coverage"] != coverage:
        raise LedgerError("RS-011 coverage summary is stale")
    readiness = ledger["readiness"]
    if readiness != {
        "gate_status": "NOT_READY",
        "technical_complete": False,
        "credit_eligible": False,
        "compiler_capture_status": "missing",
        "independent_review_status": "pending",
        "blockers": list(SOURCE_BLOCKERS),
    }:
        raise LedgerError("RS-011 readiness must remain fail-closed")
    return discovery


def unfold_make_lines(text):
    return re.sub(r"\\\r?\n[ \t]*", " ", text)


def shell_words(value, label):
    if any(marker in value for marker in ("`", "$(", "${", "<(", ">(")) or "$" in value:
        raise LedgerError("{0} contains shell expansion".format(label))
    if "\x00" in value or "\n" in value or "\r" in value:
        raise LedgerError("{0} contains a control character".format(label))
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError as error:
        raise LedgerError("cannot parse {0}: {1}".format(label, error))


def parse_kbuild_command(path):
    raw, text = read_source(path, "Kbuild compiler command")
    assignments = {"cmd": {}, "source": {}}
    for line in unfold_make_lines(text).splitlines():
        match = MAKE_ASSIGNMENT.match(line)
        if not match:
            continue
        kind = match.group("kind")
        key = match.group("key").strip()
        if key in assignments[kind]:
            raise LedgerError("duplicate {0}_{1} assignment".format(kind, key))
        assignments[kind][key] = match.group("value").strip()
    if len(assignments["cmd"]) != 1:
        raise LedgerError("compiler .cmd must contain exactly one cmd_ assignment")
    key, command_text = next(iter(assignments["cmd"].items()))
    if len(assignments["source"]) != 1 or key not in assignments["source"]:
        raise LedgerError("compiler .cmd must contain one matching source_ assignment")
    words = shell_words(command_text, "Kbuild compiler command")
    split = len(words)
    for index, word in enumerate(words):
        if word in CONTROL_TOKENS:
            if word != ";":
                raise LedgerError("compiler command contains forbidden shell control token")
            split = index
            break
    compile_words = words[:split]
    suffix = words[split:]
    if len(compile_words) < 2:
        raise LedgerError("compiler command is incomplete")
    env_words = []
    while compile_words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", compile_words[0]):
        env_words.append(compile_words.pop(0))
    if len(compile_words) < 2 or os.path.basename(compile_words[0]) not in ("rustc", "rustc.real"):
        raise LedgerError("Kbuild command does not invoke rustc directly")
    if any(word.startswith("@") for word in compile_words):
        raise LedgerError("rustc response files are not captured")
    source_words = shell_words(assignments["source"][key], "Kbuild source assignment")
    if len(source_words) != 1:
        raise LedgerError("Kbuild source assignment must contain one literal path")
    emit = None
    index = 1
    while index < len(compile_words):
        word = compile_words[index]
        if word == "--emit":
            if index + 1 >= len(compile_words):
                raise LedgerError("rustc --emit lacks a value")
            if emit is not None:
                raise LedgerError("rustc command has multiple --emit values")
            emit = compile_words[index + 1]
            index += 2
            continue
        if word.startswith("--emit="):
            if emit is not None:
                raise LedgerError("rustc command has multiple --emit values")
            emit = word.split("=", 1)[1]
        index += 1
    outputs = {}
    if emit is None:
        raise LedgerError("rustc command does not emit dep-info")
    for item in emit.split(","):
        if "=" in item:
            kind, value = item.split("=", 1)
            if kind in outputs:
                raise LedgerError("rustc --emit repeats {0}".format(kind))
            outputs[kind] = value
    if not outputs.get("dep-info") or not outputs.get("obj"):
        raise LedgerError("rustc --emit must name exact dep-info and obj paths")
    return {
        "file": {"bytes": len(raw), "sha256": sha256_bytes(raw)},
        "assignment_key_sha256": sha256_bytes(key.encode("utf-8")),
        "command_argv": compile_words,
        "command_argv_sha256": sha256_bytes(canonical_bytes(compile_words)),
        "environment_assignments_sha256": sha256_bytes(canonical_bytes(env_words)),
        "declared_source": source_words[0],
        "dep_info": outputs["dep-info"],
        "object": outputs["obj"],
        "post_compile_tokens_sha256": sha256_bytes(canonical_bytes(suffix)),
    }


def resolve_command_path(value, kernel_source, kernel_build, label):
    candidates = []
    if os.path.isabs(value):
        candidates.append(value)
    else:
        candidates.extend((os.path.join(kernel_build, value), os.path.join(kernel_source, value)))
    present = []
    for candidate in candidates:
        try:
            resolved = regular_file(candidate, label)
        except LedgerError:
            continue
        if resolved not in present:
            present.append(resolved)
    if len(present) != 1:
        raise LedgerError("{0} resolves to {1} regular files".format(label, len(present)))
    return present[0]


def make_dependencies(path):
    raw, text = read_source(path, "rustc dep-info")
    text = unfold_make_lines(text)
    first = text.splitlines()[0] if text.splitlines() else ""
    separator = None
    escaped = False
    for index, char in enumerate(first):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            separator = index
            break
    if separator is None:
        raise LedgerError("rustc dep-info has no target separator")
    body = first[separator + 1 :]
    values = []
    current = []
    escaped = False
    for char in body:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char.isspace():
            if current:
                values.append("".join(current))
                current = []
        else:
            current.append(char)
    if escaped:
        raise LedgerError("rustc dep-info ends with an escape")
    if current:
        values.append("".join(current))
    if not values or len(values) != len(set(values)):
        raise LedgerError("rustc dep-info dependencies are empty or duplicated")
    return values, {"bytes": len(raw), "sha256": sha256_bytes(raw)}


def compiler_provenance(executable, platform_record):
    if os.path.isabs(executable):
        path = executable
    else:
        path = shutil.which(executable)
    if not path:
        raise LedgerError("recorded rustc is unavailable")
    path = regular_file(path, "recorded rustc")
    compiler_sha256 = sha256_file(path)
    if compiler_sha256 != platform_record.get("sha256"):
        raise LedgerError("recorded rustc bytes differ from platform evidence")
    platform_path = platform_record.get("path")
    if not isinstance(platform_path, str) or os.path.realpath(platform_path) != path:
        raise LedgerError("recorded rustc path differs from platform evidence")
    stdout_sha256 = platform_record.get("stdout_sha256")
    stderr_sha256 = platform_record.get("stderr_sha256")
    excerpt = platform_record.get("version_excerpt")
    if (
        not HEX64.match(str(stdout_sha256))
        or not HEX64.match(str(stderr_sha256))
        or not isinstance(excerpt, str)
        or not excerpt.splitlines()
    ):
        raise LedgerError("platform rustc version capture is incomplete")
    return {
        "path": path,
        "bytes": os.path.getsize(path),
        "sha256": compiler_sha256,
        "version_stdout_sha256": stdout_sha256,
        "version_stderr_sha256": stderr_sha256,
        "version_first_line": excerpt.splitlines()[0],
    }


def parse_named_paths(values, expected, label):
    result = {}
    for value in values:
        if "=" not in value:
            raise LedgerError("{0} must use crate=path".format(label))
        crate, path = value.split("=", 1)
        if crate not in expected or crate in result or not path:
            raise LedgerError("{0} has unknown/duplicate crate {1}".format(label, crate))
        result[crate] = path
    if set(result) != set(expected):
        raise LedgerError("{0} must cover exactly {1}".format(label, ",".join(expected)))
    return result


def git_head(repo):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LedgerError("cannot resolve repository commit: {0}".format(error))
    value = completed.stdout.decode("ascii", errors="replace").strip()
    if completed.returncode != 0 or not HEX40.match(value):
        raise LedgerError("repository commit is not exact")
    return value


def validate_platform_evidence(value, ledger):
    if value.get("profile") != "rocky-10.2-exact-linux-api-evidence-v1":
        raise LedgerError("compiler capture requires RS-001 exact platform evidence")
    if value.get("evidence_sha256") != evidence_digest(value):
        raise LedgerError("RS-001 platform evidence digest is stale")
    target = value.get("target", {})
    if (
        target.get("distribution") != "Rocky Linux"
        or target.get("release") != "10.2"
        or target.get("architecture") != "x86_64"
        or target.get("source_rpm_sha256") != ledger["target"]["source_rpm_sha256"]
    ):
        raise LedgerError("RS-001 platform evidence target differs from RS-011")
    if value.get("source", {}).get("exact_locked_replay") is not True:
        raise LedgerError("RS-001 platform evidence lacks exact source replay")
    selected_config = value.get("configuration", {}).get("selected_config_sha256")
    if not isinstance(selected_config, str) or not HEX64.match(selected_config):
        raise LedgerError("RS-001 platform evidence lacks selected config digest")
    tools = value.get("environment", {}).get("tools", [])
    rustc = [item for item in tools if isinstance(item, dict) and item.get("id") == "rustc"]
    if len(rustc) != 1 or rustc[0].get("status") != "captured" or not HEX64.match(str(rustc[0].get("sha256"))):
        raise LedgerError("RS-001 platform evidence lacks exact rustc provenance")
    readiness = value.get("readiness", {})
    if readiness.get("gate_status") != "NOT_READY" or readiness.get("credit_eligible") is not False:
        raise LedgerError("RS-001 platform evidence improperly claims readiness")
    return selected_config, rustc[0]


def _resolve_dependency(value, kernel_source, kernel_build):
    candidates = []
    if os.path.isabs(value):
        candidates.append(value)
    else:
        candidates.extend((os.path.join(kernel_build, value), os.path.join(kernel_source, value)))
    present = []
    for candidate in candidates:
        if os.path.isfile(candidate) and not os.path.islink(candidate):
            resolved = os.path.realpath(candidate)
            if resolved not in present:
                present.append(resolved)
    if len(present) != 1:
        raise LedgerError("dep-info input resolves ambiguously or is missing: {0}".format(value))
    return present[0]


def build_compiler_evidence(args, repo, ledger):
    kernel_source = directory(args.kernel_source, "kernel source")
    kernel_build = directory(args.kernel_build, "kernel build")
    staged_root = directory(args.staged_root, "staged native Rust root")
    within(staged_root, kernel_source, "staged native Rust root")
    commands = parse_named_paths(args.command, EXPECTED_CRATES, "--command")
    platform_path = regular_file(args.platform_evidence, "RS-001 platform evidence")
    platform_value = read_json(platform_path, "RS-001 platform evidence")
    selected_config, platform_rustc = validate_platform_evidence(platform_value, ledger)
    roots = {item["crate"]: item for item in ledger["crate_roots"]}
    sites_by_crate = {
        crate: [item["id"] for item in ledger["sites"] if crate in item["crate_roots"]]
        for crate in EXPECTED_CRATES
    }
    records = []
    compiler = None
    for crate in EXPECTED_CRATES:
        command_path = regular_file(commands[crate], crate + " compiler command")
        within(command_path, kernel_build, crate + " compiler command")
        command = parse_kbuild_command(command_path)
        current_compiler = compiler_provenance(command["command_argv"][0], platform_rustc)
        if compiler is None:
            compiler = current_compiler
        elif current_compiler != compiler:
            raise LedgerError("native crates were not built by one exact rustc")
        root = roots[crate]
        staged_source = regular_file(
            os.path.join(staged_root, root["destination"]), crate + " staged crate root"
        )
        declared = resolve_command_path(
            command["declared_source"], kernel_source, kernel_build, crate + " declared source"
        )
        if declared != staged_source:
            raise LedgerError("{0} compiler command names a different crate root".format(crate))
        source_occurrences = 0
        for word in command["command_argv"][1:]:
            if word.startswith("-"):
                continue
            try:
                candidate = resolve_command_path(word, kernel_source, kernel_build, "compiler input")
            except LedgerError:
                continue
            if candidate == staged_source:
                source_occurrences += 1
        if source_occurrences != 1:
            raise LedgerError("{0} rustc argv contains its root {1} times".format(crate, source_occurrences))
        dep_path = resolve_command_path(command["dep_info"], kernel_source, kernel_build, crate + " dep-info")
        object_path = resolve_command_path(command["object"], kernel_source, kernel_build, crate + " object")
        dependencies, dep_record = make_dependencies(dep_path)
        resolved_dependencies = [_resolve_dependency(value, kernel_source, kernel_build) for value in dependencies]
        project = []
        for dependency in resolved_dependencies:
            try:
                within(dependency, staged_root, "compiler project dependency")
            except LedgerError:
                continue
            relative_stage = os.path.relpath(dependency, staged_root).replace(os.sep, "/")
            if not relative_stage.endswith(".rs"):
                continue
            repository_path = NATIVE_SOURCE_ROOT + "/" + relative_stage
            project.append(
                {
                    "repository_path": repository_path,
                    "staged_path": relative_stage,
                    "sha256": sha256_file(dependency),
                }
            )
        project.sort(key=lambda item: item["repository_path"])
        if len(project) != len({item["repository_path"] for item in project}):
            raise LedgerError("{0} compiler project closure has duplicate inputs".format(crate))
        expected_paths = root["transitive_inputs"]
        if [item["repository_path"] for item in project] != expected_paths:
            raise LedgerError("{0} compiler project Rust closure differs from ledger".format(crate))
        input_lookup = {item["path"]: item for item in ledger["source_inputs"]}
        for item in project:
            if item["sha256"] != input_lookup[item["repository_path"]]["sha256"]:
                raise LedgerError("{0} staged Rust input bytes differ from ledger".format(item["repository_path"]))
        records.append(
            {
                "crate": crate,
                "root_repository_path": root["path"],
                "command_file": dict(command["file"], path=os.path.relpath(command_path, kernel_build).replace(os.sep, "/")),
                "command_argv_sha256": command["command_argv_sha256"],
                "environment_assignments_sha256": command["environment_assignments_sha256"],
                "post_compile_tokens_sha256": command["post_compile_tokens_sha256"],
                "dep_info": dict(dep_record, dependency_count=len(dependencies)),
                "object": {
                    "bytes": os.path.getsize(object_path),
                    "sha256": sha256_file(object_path),
                },
                "project_inputs": project,
                "project_inputs_sha256": sha256_bytes(canonical_bytes(project)),
                "source_site_ids": sites_by_crate[crate],
                "source_site_ids_sha256": sha256_bytes(canonical_bytes(sites_by_crate[crate])),
                "compiler_dependency_closure_match": True,
            }
        )
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "profile": COMPILER_PROFILE,
        "ledger_id": LEDGER_ID,
        "ledger_sha256": ledger["ledger_sha256"],
        "repository_commit": git_head(repo),
        "target": ledger["target"],
        "platform_evidence": {
            "bytes": os.path.getsize(platform_path),
            "sha256": sha256_file(platform_path),
            "evidence_sha256": platform_value["evidence_sha256"],
            "selected_config_sha256": selected_config,
        },
        "compiler": compiler,
        "crates": records,
        "cross_validation": {
            "source_closure_sha256": ledger["source_closure_sha256"],
            "site_ids_sha256": ledger["coverage"]["site_ids_sha256"],
            "compiler_dependency_closure_match": True,
            "compiler_expanded_site_capture": "missing",
        },
        "readiness": {
            "gate": "RS-011",
            "gate_status": "NOT_READY",
            "technical_complete": False,
            "credit_eligible": False,
            "review_required": True,
            "blockers": list(COMPILER_BLOCKERS),
        },
    }
    evidence["evidence_sha256"] = evidence_digest(evidence)
    validate_compiler_evidence(evidence, ledger)
    return evidence


def validate_compiler_evidence(value, ledger):
    require_keys(
        value,
        {
            "schema_version",
            "profile",
            "ledger_id",
            "ledger_sha256",
            "repository_commit",
            "target",
            "platform_evidence",
            "compiler",
            "crates",
            "cross_validation",
            "readiness",
            "evidence_sha256",
        },
        "RS-011 compiler evidence",
    )
    if value["schema_version"] != SCHEMA_VERSION or value["profile"] != COMPILER_PROFILE:
        raise LedgerError("compiler evidence schema/profile changed")
    if value["ledger_id"] != LEDGER_ID or value["ledger_sha256"] != ledger["ledger_sha256"]:
        raise LedgerError("compiler evidence is not bound to the exact ledger")
    if value["evidence_sha256"] != evidence_digest(value):
        raise LedgerError("compiler evidence digest is stale")
    if not isinstance(value["repository_commit"], str) or not HEX40.match(value["repository_commit"]):
        raise LedgerError("compiler evidence commit is not exact")
    if value["target"] != ledger["target"]:
        raise LedgerError("compiler evidence target changed")
    platform_record = require_keys(
        value["platform_evidence"],
        {"bytes", "sha256", "evidence_sha256", "selected_config_sha256"},
        "compiler platform evidence",
    )
    if any(not HEX64.match(str(platform_record[key])) for key in ("sha256", "evidence_sha256", "selected_config_sha256")):
        raise LedgerError("compiler platform evidence lacks immutable digests")
    compiler = require_keys(
        value["compiler"],
        {"path", "bytes", "sha256", "version_stdout_sha256", "version_stderr_sha256", "version_first_line"},
        "compiler provenance",
    )
    if any(not HEX64.match(str(compiler[key])) for key in ("sha256", "version_stdout_sha256", "version_stderr_sha256")):
        raise LedgerError("compiler provenance is not digest-bound")
    crates = value["crates"]
    if not isinstance(crates, list) or [item.get("crate") for item in crates if isinstance(item, dict)] != list(EXPECTED_CRATES):
        raise LedgerError("compiler evidence must contain exactly three ordered crates")
    roots = {item["crate"]: item for item in ledger["crate_roots"]}
    site_ids = {
        crate: [item["id"] for item in ledger["sites"] if crate in item["crate_roots"]]
        for crate in EXPECTED_CRATES
    }
    inputs = {item["path"]: item for item in ledger["source_inputs"]}
    for record in crates:
        require_keys(
            record,
            {
                "crate",
                "root_repository_path",
                "command_file",
                "command_argv_sha256",
                "environment_assignments_sha256",
                "post_compile_tokens_sha256",
                "dep_info",
                "object",
                "project_inputs",
                "project_inputs_sha256",
                "source_site_ids",
                "source_site_ids_sha256",
                "compiler_dependency_closure_match",
            },
            "compiler crate record",
        )
        crate = record["crate"]
        root = roots[crate]
        if record["root_repository_path"] != root["path"]:
            raise LedgerError("compiler root changed for {0}".format(crate))
        for field in ("command_file", "dep_info", "object"):
            item = record[field]
            if not isinstance(item, dict) or not HEX64.match(str(item.get("sha256"))) or not isinstance(item.get("bytes"), int) or item["bytes"] < 1:
                raise LedgerError("{0} evidence is malformed for {1}".format(field, crate))
        for field in ("command_argv_sha256", "environment_assignments_sha256", "post_compile_tokens_sha256", "project_inputs_sha256", "source_site_ids_sha256"):
            if not HEX64.match(str(record[field])):
                raise LedgerError("{0} digest is malformed for {1}".format(field, crate))
        project = record["project_inputs"]
        if not isinstance(project, list) or [item.get("repository_path") for item in project] != root["transitive_inputs"]:
            raise LedgerError("compiler project input closure is stale for {0}".format(crate))
        for item in project:
            require_keys(
                item,
                {"repository_path", "staged_path", "sha256"},
                "compiler project input",
            )
            expected_staged = item["repository_path"][len(NATIVE_SOURCE_ROOT) + 1 :]
            if item["staged_path"] != expected_staged:
                raise LedgerError("compiler staged path changed for {0}".format(crate))
            if item.get("sha256") != inputs[item["repository_path"]]["sha256"]:
                raise LedgerError("compiler project input digest changed for {0}".format(crate))
        if record["project_inputs_sha256"] != sha256_bytes(canonical_bytes(project)):
            raise LedgerError("compiler project input-set digest is stale for {0}".format(crate))
        if record["source_site_ids"] != site_ids[crate] or record["source_site_ids_sha256"] != sha256_bytes(canonical_bytes(site_ids[crate])):
            raise LedgerError("compiler source-site binding changed for {0}".format(crate))
        if record["compiler_dependency_closure_match"] is not True:
            raise LedgerError("compiler dependency closure is not exact for {0}".format(crate))
    if value["cross_validation"] != {
        "source_closure_sha256": ledger["source_closure_sha256"],
        "site_ids_sha256": ledger["coverage"]["site_ids_sha256"],
        "compiler_dependency_closure_match": True,
        "compiler_expanded_site_capture": "missing",
    }:
        raise LedgerError("compiler cross-validation result overclaims expanded-site coverage")
    if value["readiness"] != {
        "gate": "RS-011",
        "gate_status": "NOT_READY",
        "technical_complete": False,
        "credit_eligible": False,
        "review_required": True,
        "blockers": list(COMPILER_BLOCKERS),
    }:
        raise LedgerError("compiler evidence self-attests RS-011 readiness")


def atomic_write(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    descriptor, temporary = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=REPOSITORY_ROOT)
    subparsers = parser.add_subparsers(dest="mode")
    subparsers.add_parser("check")
    subparsers.add_parser("inventory")
    capture = subparsers.add_parser("capture-compiler")
    capture.add_argument("--platform-evidence", required=True)
    capture.add_argument("--kernel-source", required=True)
    capture.add_argument("--kernel-build", required=True)
    capture.add_argument("--staged-root", required=True)
    capture.add_argument("--command", action="append", default=[], required=True)
    capture.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify-compiler")
    verify.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    if args.mode is None:
        parser.error("one mode is required")
    return args


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo = os.path.realpath(args.repo)
    try:
        if args.mode == "inventory":
            print(pretty(discover(repo)), end="")
            return 0
        ledger_path = repository_file(repo, LEDGER_PATH, "RS-011 ledger")
        ledger = read_json(ledger_path, "RS-011 ledger")
        discovery = validate_ledger(ledger, repo)
        if args.mode == "check":
            print(
                "RS-011 source ledger verified: {0} inputs, {1} unsafe/FFI sites; gate_status=NOT_READY".format(
                    len(discovery["inputs"]), len(discovery["sites"])
                )
            )
            return 0
        if args.mode == "capture-compiler":
            evidence = build_compiler_evidence(args, repo, ledger)
            atomic_write(args.output, pretty(evidence))
            print(
                "captured exact compiler dependency closure for 3 crates; RS-011 remains NOT_READY; sha256={0}".format(
                    evidence["evidence_sha256"]
                )
            )
            return 0
        if args.mode == "verify-compiler":
            evidence_path = regular_file(args.evidence, "RS-011 compiler evidence")
            value = read_json(evidence_path, "RS-011 compiler evidence")
            validate_compiler_evidence(value, ledger)
            print(
                "verified RS-011 compiler closure evidence; expanded-site capture/review remain blocked; sha256={0}".format(
                    value["evidence_sha256"]
                )
            )
            return 0
        raise LedgerError("unsupported mode")
    except LedgerError as error:
        print("RS-011 unsafe/FFI ledger error: {0}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
