"""Exact supported Rust1.95 diagnostic qualifier. Build metadata only.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The retained original remains FAIL. Only seven exact dead-code blocks, their
path-relocated source/line/column/category joins and the exact normal native
artifact note/summary/flag order are admitted; every other byte is rejected.
"""
from pathlib import Path
import hashlib
import posixpath
import re
import shlex

WARNING_SOURCES = [{'kind': 'function', 'name': 'abort', 'filename': 'accepted_host_root.assigned_memory_dependency_join.rs', 'line': 22, 'column': 8, 'source_sha256': 'f1b515fa9eceb75b2b912a9630641e663f21fa3ad06ab79b12d917492a9b22a2', 'origin_sha256': 'ccbf20b1a1a0d303b34e123adcbdf8e125773d26f2f9d8883c96d0a41ccc9f8b'}, {'kind': 'constant', 'name': 'EINVAL', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 5, 'column': 7, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}, {'kind': 'function', 'name': 'is', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 39, 'column': 11, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}, {'kind': 'function', 'name': 'strcmp', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 26, 'column': 5, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}, {'kind': 'function', 'name': 'strdup', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 27, 'column': 5, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}, {'kind': 'function', 'name': 'strsep', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 28, 'column': 5, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}, {'kind': 'function', 'name': 'strtol', 'filename': 'ihklib_mcstat_memory_shared_parser.rs', 'line': 29, 'column': 5, 'source_sha256': '3073d7d82836f0f131d6c34500d44d141d9bc313f6a3bd0a41523222b7d95d50', 'origin_sha256': '75d8fa2c77104a2f119aff0c5ee60da23089e06003b56f67b7fd79d2469e6601'}]
NATIVE_FLAGS = ['-lgcc_s', '-lutil', '-lrt', '-lpthread', '-lm', '-ldl', '-lc']
NORMALIZED_RETAINED_DIAGNOSTICS = 'warning: function `abort` is never used\n  --> @WARNING_SOURCE:accepted_host_root.assigned_memory_dependency_join.rs@:22:8\n   |\n22 |     fn abort() -> !;\n   |        ^^^^^\n   |\n   = note: `#[warn(dead_code)]` (part of `#[warn(unused)]`) on by default\n\nwarning: constant `EINVAL` is never used\n --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:5:7\n  |\n5 | const EINVAL:c_int=22;\n  |       ^^^^^^\n\nwarning: function `is` is never used\n  --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:39:11\n   |\n39 | unsafe fn is(a:*const c_char,b:*const c_char)->bool {unsafe {strcmp(a,b)==0}}\n   |           ^^\n\nwarning: function `strcmp` is never used\n  --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:26:5\n   |\n26 |  fn strcmp(a:*const c_char,b:*const c_char)->c_int;\n   |     ^^^^^^\n\nwarning: function `strdup` is never used\n  --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:27:5\n   |\n27 |  fn strdup(s:*const c_char)->*mut c_char;\n   |     ^^^^^^\n\nwarning: function `strsep` is never used\n  --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:28:5\n   |\n28 |  fn strsep(s:*mut *mut c_char,delimiters:*const c_char)->*mut c_char;\n   |     ^^^^^^\n\nwarning: function `strtol` is never used\n  --> @WARNING_SOURCE:ihklib_mcstat_memory_shared_parser.rs@:29:5\n   |\n29 |  fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;\n   |     ^^^^^^\n\nnote: link against the following native artifacts when linking against this static library. The order and any duplication can be significant on some platforms\n\nnote: native-static-libs: -lgcc_s -lutil -lrt -lpthread -lm -ldl -lc\n\nwarning: 7 warnings emitted\n\n'


def qualify_rust_diagnostics(raw, source):
    def need(ok, message):
        if not ok:
            raise ValueError(message)
    source = Path(source).resolve()
    text = raw.decode("utf-8")
    starts = list(re.finditer(r"^warning: (function|constant) `([^`]+)` is never used$",
                             text, re.M))
    need([(m.group(1), m.group(2)) for m in starts] ==
         [(r["kind"], r["name"]) for r in WARNING_SOURCES],
         "exact seven dead-code warning categories/names/order")
    replacements = []
    for index, (match, rule) in enumerate(zip(starts, WARNING_SOURCES)):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        locations = list(re.finditer(r"^\s*--> (.+):([0-9]+):([0-9]+)$",
                                    text[match.end():end], re.M))
        need(len(locations) == 1, "one exact warning source location")
        location = locations[0]
        expected = source / rule["filename"]
        need(posixpath.normpath(location.group(1)) == str(expected) and
             int(location.group(2)) == rule["line"] and
             int(location.group(3)) == rule["column"], "relocated exact source/line/column")
        need(hashlib.sha256(expected.read_bytes()).hexdigest() == rule["source_sha256"],
             "path-only canonical warning source pin")
        begin = match.end() + location.start(1)
        finish = match.end() + location.end(1)
        replacements.append((begin, finish, "@WARNING_SOURCE:" + rule["filename"] + "@"))
    flags = re.findall(r"^note: native-static-libs: (.+)$", text, re.M)
    need(len(flags) == 1 and shlex.split(flags[0]) == NATIVE_FLAGS,
         "one same-compile native flags record in accepted order")
    normalized = text
    for begin, finish, replacement in reversed(replacements):
        normalized = normalized[:begin] + replacement + normalized[finish:]
    need(normalized == NORMALIZED_RETAINED_DIAGNOSTICS,
         "exact dead-code snippets/category note/native artifact note/summary closure")
    return list(NATIVE_FLAGS)
