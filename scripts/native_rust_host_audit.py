#!/usr/bin/env python3
"""Fail closed unless native Rust host-module staging has only locked Rust inputs."""

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "host-kernel", "kbuild", "stage-manifest.json")
FORBIDDEN_SUFFIXES = (".c", ".cc", ".cpp", ".o", ".a", ".so")
FORBIDDEN_RUST_IDENTIFIERS = frozenset(
    (
        "asm",
        "export_name",
        "extern",
        "global_asm",
        "include",
        "include_bytes",
        "include_str",
        "link",
        "link_name",
        "link_ordinal",
        "link_section",
        "linkage",
        "llvm_asm",
        "naked_asm",
        "no_mangle",
        "path",
    )
)


# These are the complete reviewed escape surfaces in the three locked crate
# roots.  Each block must occur exactly once and is removed before the generic
# escape scan.  Consequently a renamed, duplicated, reordered, or additional
# ABI/linkage construct fails closed even when an attacker also refreshes the
# source digest in the staging manifest.
REVIEWED_RUST_ESCAPE_BLOCKS = {
    "host-kernel/native-rust/ihk.rs": (
        (
            "IHK locked x86_64 ABI module path",
            '''#[path = "abi/x86_64.rs"]
mod abi;''',
        ),
        (
            "IHK SMP provider init callback type",
            '''type IhkSmpProviderInitV2 = extern "C" fn() -> i32;''',
        ),
        (
            "IHK SMP provider exit callback type",
            '''type IhkSmpProviderExitV2 = extern "C" fn();''',
        ),
        (
            "IHK lifecycle value export",
            '''#[export_name = "ihk_provider_lifecycle_v1"]
pub static IHK_PROVIDER_LIFECYCLE_V1: u8 = 1;''',
        ),
        (
            "IHK lifecycle export record",
            '''#[export_name = "__export_symbol_ihk_provider_lifecycle_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_PROVIDER_LIFECYCLE_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1),
};''',
        ),
        (
            "IHK SMP provider attach ABI",
            '''#[export_name = "ihk_smp_provider_attach_v1"]
// SAFETY: This exported C ABI accepts no caller-owned state and returns only
// the registry-owned scalar token or a negative errno.
pub extern "C" fn ihk_smp_provider_attach_v1() -> i64 {''',
        ),
        (
            "IHK SMP provider attach export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_attach_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_ATTACH_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_attach_v1 as *const () as *const u8,
};''',
        ),
        (
            "IHK SMP provider detach ABI",
            '''#[export_name = "ihk_smp_provider_detach_v1"]
// SAFETY: This exported C ABI accepts only the opaque scalar issued by attach
// and cannot return while the owned provider entry remains live.
pub extern "C" fn ihk_smp_provider_detach_v1(token: i64) {''',
        ),
        (
            "IHK SMP provider detach export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_detach_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_DETACH_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_detach_v1 as *const () as *const u8,
};''',
        ),
        (
            "IHK SMP provider attach v2 ABI",
            '''#[export_name = "ihk_smp_provider_attach_v2"]
// SAFETY: The exact nullable function-pointer ABI is validated before either
// callback is invoked; no Rust object or caller-owned data crosses the export.
pub extern "C" fn ihk_smp_provider_attach_v2(
    callback_abi: u32,
    flags: u32,
    init: Option<IhkSmpProviderInitV2>,
    exit: Option<IhkSmpProviderExitV2>,
) -> i64 {''',
        ),
        (
            "IHK SMP provider attach v2 export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_attach_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_ATTACH_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_attach_v2 as *const () as *const u8,
};''',
        ),
        (
            "IHK SMP provider detach v2 ABI",
            '''#[export_name = "ihk_smp_provider_detach_v2"]
// SAFETY: The token and exact retained exit identity name the sole live v2
// lease; invariant violations fail stop before provider retirement can return.
pub extern "C" fn ihk_smp_provider_detach_v2(
    token: i64,
    exit: Option<IhkSmpProviderExitV2>,
) {''',
        ),
        (
            "IHK SMP provider detach v2 export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_detach_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_DETACH_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_detach_v2 as *const () as *const u8,
};''',
        ),
        (
            "IHK loadable version metadata",
            '''#[link_section = ".modinfo"]
#[used(compiler)]
static IHK_VERSION_MODINFO: [u8; 17] = *b"version=1.7.0rc4\\0";''',
        ),
        (
            "IHK built-in version metadata",
            '''#[link_section = ".modinfo"]
#[used(compiler)]
static IHK_BUILTIN_VERSION_MODINFO: [u8; 21] = *b"ihk.version=1.7.0rc4\\0";''',
        ),
    ),
    "host-kernel/native-rust/ihk_smp_x86_64.rs": (
        (
            "IHK SMP init callback type",
            '''type IhkSmpProviderInitV2 = extern "C" fn() -> i32;''',
        ),
        (
            "IHK SMP exit callback type",
            '''type IhkSmpProviderExitV2 = extern "C" fn();''',
        ),
        (
            "IHK SMP three-symbol provider import",
            '''extern "C" {
    #[link_name = "ihk_provider_lifecycle_v1"]
    static IHK_PROVIDER_LIFECYCLE_V1: u8;
    #[link_name = "ihk_smp_provider_attach_v2"]
    fn ihk_smp_provider_attach_v2(
        callback_abi: u32,
        flags: u32,
        init: Option<IhkSmpProviderInitV2>,
        exit: Option<IhkSmpProviderExitV2>,
    ) -> i64;
    #[link_name = "ihk_smp_provider_detach_v2"]
    fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);
}''',
        ),
        (
            "IHK SMP init callback ABI",
            '''extern "C" fn ihk_smp_provider_init_v2() -> i32 {''',
        ),
        (
            "IHK SMP exit callback ABI",
            '''extern "C" fn ihk_smp_provider_exit_v2() {''',
        ),
        (
            "IHK SMP parameter descriptor section",
            '''#[link_section = "__param"]
        #[used(compiler)]
        static $descriptor: KernelParameter = KernelParameter {''',
        ),
        (
            "IHK SMP loadable parameter metadata",
            '''#[link_section = ".modinfo"]
        #[used(compiler)]
        static $loadable_name: [u8; $loadable.len()] = *$loadable;''',
        ),
        (
            "IHK SMP built-in parameter metadata",
            '''#[link_section = ".modinfo"]
        #[used(compiler)]
        static $builtin_name: [u8; $builtin.len()] = *$builtin;''',
        ),
    ),
    "host-kernel/native-rust/mcctrl.rs": (
        (
            "mcctrl lifecycle provider import",
            '''extern "Rust" {
    #[link_name = "ihk_provider_lifecycle_v1"]
    static IHK_PROVIDER_LIFECYCLE_V1: u8;
}''',
        ),
        (
            "mcctrl loadable namespace metadata",
            '''#[link_section = ".modinfo"]
#[used(compiler)]
static MCCTRL_IHK_IMPORT_NAMESPACE: [u8; 26] = *b"import_ns=MCKERNEL_IHK_V1\\0";''',
        ),
        (
            "mcctrl built-in namespace metadata",
            '''#[link_section = ".modinfo"]
#[used(compiler)]
static MCCTRL_BUILTIN_IHK_IMPORT_NAMESPACE: [u8; 33] =
    *b"mcctrl.import_ns=MCKERNEL_IHK_V1\\0";''',
        ),
    ),
}

REVIEWED_RUST_BLOCK_PREFIXES = {
    "IHK locked x86_64 ABI module path": '''#[allow(dead_code, unreachable_pub)]
''',
    "IHK SMP provider init callback type": '''// SAFETY: This C-ABI callback has no arguments, borrows no caller memory, and
// returns only a scalar status consumed before provider publication.
''',
    "IHK SMP provider exit callback type": '''// SAFETY: This C-ABI callback has no arguments, borrows no caller memory, and
// returns only after the dependent has completed its scalar lifecycle exit.
''',
    "IHK lifecycle value export": '''#[doc(hidden)]
// SAFETY: This immutable byte is the provider's read-only ABI anchor. Consumers
// must import it through MCKERNEL_IHK_V1 and may not treat its value as state.
''',
    "IHK lifecycle export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the namespaced anchor; neither the record nor its target is mutated in Rust.
''',
    "IHK SMP provider attach ABI": '''#[doc(hidden)]
// SAFETY: This C-ABI scalar boundary owns no caller memory.  A positive return
// is a versioned opaque token for the single published minor-zero provider;
// every failure is a negative errno and leaves no live reservation behind.
''',
    "IHK SMP provider attach export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar attach function in MCKERNEL_IHK_V1 for the provider lifetime.
''',
    "IHK SMP provider detach ABI": '''#[doc(hidden)]
// SAFETY: This C-ABI scalar boundary consumes the exact v1 token owned by the
// reviewed namespaced SMP dependent.  The token is an ownership receipt, not
// a security boundary against other privileged in-kernel code.  Any malformed,
// stale, duplicated, busy, or corrupt state fails stop before unload succeeds.
''',
    "IHK SMP provider detach export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar detach function in MCKERNEL_IHK_V1 for the provider lifetime.
''',
    "IHK SMP provider attach v2 ABI": '''#[doc(hidden)]
// SAFETY: This C ABI accepts only scalars and nullable C-ABI function pointers.
// The reviewed SMP dependent owns both callback targets for the full returned
// lease lifetime.  Initialization runs while the registry slot is Publishing;
// only a zero result permits publication.  Every failed path aborts or retires
// its reservation and leaves no retained callback identity.
''',
    "IHK SMP provider attach v2 export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the callback-bound attach function in MCKERNEL_IHK_V1 for the provider lifetime.
''',
    "IHK SMP provider detach v2 ABI": '''#[doc(hidden)]
// SAFETY: The exact callback identity was retained before the named token was
// published.  The unregister guard first makes the provider Unpublishing and
// rejects new references.  The callback executes only after all existing open
// and OS references have drained, remains bound throughout the call, and is
// cleared only after exit completes and the slot commits to Vacant.
''',
    "IHK SMP provider detach v2 export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the callback-bound detach function in MCKERNEL_IHK_V1 for the provider lifetime.
''',
    "IHK loadable version metadata": '''#[cfg(MODULE)]
#[doc(hidden)]
''',
    "IHK built-in version metadata": '''#[cfg(not(MODULE))]
#[doc(hidden)]
''',
    "IHK SMP init callback type": '''// SAFETY: This scalar C-ABI callback borrows no provider or caller memory.
''',
    "IHK SMP exit callback type": '''// SAFETY: This scalar C-ABI callback borrows no provider or caller memory.
''',
    "IHK SMP init callback ABI": '''// These callbacks deliberately own lifecycle only.  Returning success from
// init does not advertise any device operation, OS lease, CPU, memory, IKC, or
// McKernel behavior.  The IHK provider invokes them before publication and
// while holding an unpublishing guard respectively.
// SAFETY: The callback owns no foreign state and returns only a literal errno
// status through the exact v2 function-pointer ABI.
''',
    "IHK SMP exit callback ABI": '''// SAFETY: The callback owns no foreign state and returns only after its local
// lifecycle diagnostic completes through the exact v2 function-pointer ABI.
''',
    "IHK SMP parameter descriptor section": '''#[doc(hidden)]
        ''',
    "IHK SMP loadable parameter metadata": '''#[cfg(MODULE)]
        #[doc(hidden)]
        ''',
    "IHK SMP built-in parameter metadata": '''#[cfg(not(MODULE))]
        #[doc(hidden)]
        ''',
    "mcctrl loadable namespace metadata": '''#[cfg(MODULE)]
#[doc(hidden)]
''',
    "mcctrl built-in namespace metadata": '''#[cfg(not(MODULE))]
#[doc(hidden)]
''',
}

REVIEWED_RUST_OUTER_BLOCKS = frozenset(
    (
        "IHK locked x86_64 ABI module path",
        "IHK SMP provider init callback type",
        "IHK SMP provider exit callback type",
        "IHK lifecycle value export",
        "IHK lifecycle export record",
        "IHK SMP provider attach ABI",
        "IHK SMP provider attach export record",
        "IHK SMP provider detach ABI",
        "IHK SMP provider detach export record",
        "IHK SMP provider attach v2 ABI",
        "IHK SMP provider attach v2 export record",
        "IHK SMP provider detach v2 ABI",
        "IHK SMP provider detach v2 export record",
        "IHK loadable version metadata",
        "IHK built-in version metadata",
        "IHK SMP init callback type",
        "IHK SMP exit callback type",
        "IHK SMP three-symbol provider import",
        "IHK SMP init callback ABI",
        "IHK SMP exit callback ABI",
        "IHK SMP parameter descriptor section",
        "IHK SMP loadable parameter metadata",
        "IHK SMP built-in parameter metadata",
        "mcctrl lifecycle provider import",
        "mcctrl loadable namespace metadata",
        "mcctrl built-in namespace metadata",
    )
)

REVIEWED_RUST_BRACED_BLOCKS = frozenset(
    ("IHK SMP loadable parameter metadata",)
)

REVIEWED_RUST_BLOCK_DEPTHS = dict(
    (label, 0) for label in REVIEWED_RUST_OUTER_BLOCKS
)
REVIEWED_RUST_BLOCK_DEPTHS.update(
    {
        "IHK SMP parameter descriptor section": 2,
        "IHK SMP loadable parameter metadata": 2,
        "IHK SMP built-in parameter metadata": 2,
    }
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8") as stream:
        return stream.read()


def die(message):
    raise SystemExit("native Rust host audit failed: " + message)


def regular_repo_file(relative):
    if not relative or relative.startswith("/") or ".." in relative.split("/"):
        die("unsafe repository path: {0}".format(relative))
    path = os.path.join(ROOT, relative)
    try:
        st = os.lstat(path)
    except OSError as error:
        die("missing locked file {0}: {1}".format(relative, error))
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        die("locked input is not a regular file: {0}".format(relative))
    if os.path.realpath(path) != path:
        die("locked input traverses a symlink: {0}".format(relative))
    return path


def _blank_rust_span(masked, text, start, end, preserved=()):
    preserved = set(preserved)
    for offset in range(start, end):
        if offset not in preserved and text[offset] not in "\r\n":
            masked[offset] = " "


def _rust_char_literal_end(text, start):
    cursor = start + 1
    if cursor >= len(text) or text[cursor] in "\r\n'":
        return None
    if text[cursor] == "\\":
        cursor += 1
        if cursor >= len(text) or text[cursor] in "\r\n":
            return None
        if text[cursor] == "u" and cursor + 1 < len(text) and text[cursor + 1] == "{":
            closing = text.find("}", cursor + 2)
            if closing < 0:
                return None
            cursor = closing + 1
        elif text[cursor] == "x":
            cursor += 3
        else:
            cursor += 1
    else:
        cursor += 1
    if cursor < len(text) and text[cursor] == "'":
        return cursor + 1
    return None


def _mask_rust_comments_and_literals(text, relative):
    """Mask inert Rust text while preserving active identifiers and offsets."""

    masked = list(text)
    cursor = 0
    length = len(text)
    while cursor < length:
        if text.startswith("//", cursor):
            end = text.find("\n", cursor + 2)
            if end < 0:
                end = length
            _blank_rust_span(masked, text, cursor, end)
            cursor = end
            continue
        if text.startswith("/*", cursor):
            depth = 1
            end = cursor + 2
            while end < length and depth:
                if text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            if depth:
                die("unterminated Rust block comment in {0}".format(relative))
            _blank_rust_span(masked, text, cursor, end)
            cursor = end
            continue

        raw_prefix_length = None
        if cursor == 0 or not (text[cursor - 1].isalnum() or text[cursor - 1] == "_"):
            for prefix in ("br", "cr", "r"):
                if text.startswith(prefix, cursor):
                    probe = cursor + len(prefix)
                    while probe < length and text[probe] == "#":
                        probe += 1
                    if probe < length and text[probe] == '"':
                        raw_prefix_length = len(prefix)
                        break
        if raw_prefix_length is not None:
            quote = cursor + raw_prefix_length
            while quote < length and text[quote] == "#":
                quote += 1
            hashes = text[cursor + raw_prefix_length : quote]
            closing = text.find('"' + hashes, quote + 1)
            if closing < 0:
                die("unterminated Rust raw string literal in {0}".format(relative))
            end = closing + 1 + len(hashes)
            _blank_rust_span(masked, text, quote + 1, closing)
            cursor = end
            continue

        if text[cursor] == '"':
            end = cursor + 1
            closed = False
            while end < length:
                if text[end] == "\\":
                    end += 2
                elif text[end] == '"':
                    end += 1
                    closed = True
                    break
                else:
                    end += 1
            if not closed:
                die("unterminated Rust string literal in {0}".format(relative))
            _blank_rust_span(masked, text, cursor, end, (cursor, end - 1))
            cursor = end
            continue

        char_start = cursor
        if (
            text[cursor] == "b"
            and cursor + 1 < length
            and text[cursor + 1] == "'"
            and (cursor == 0 or not (text[cursor - 1].isalnum() or text[cursor - 1] == "_"))
        ):
            char_start = cursor + 1
        if text[char_start] == "'":
            end = _rust_char_literal_end(text, char_start)
            if end is not None:
                _blank_rust_span(masked, text, char_start, end)
                cursor = end
                continue
        cursor += 1
    return "".join(masked)


def _rust_identifier_start(character):
    return character == "_" or character.isidentifier()


def _rust_identifier_continue(character):
    return character == "_" or ("a" + character).isidentifier()


def _rust_identifiers(text):
    cursor = 0
    length = len(text)
    while cursor < length:
        raw = False
        name_start = cursor
        if (
            text.startswith("r#", cursor)
            and cursor + 2 < length
            and _rust_identifier_start(text[cursor + 2])
        ):
            raw = True
            name_start = cursor + 2
        elif not _rust_identifier_start(text[cursor]):
            cursor += 1
            continue
        end = name_start + 1
        while end < length and _rust_identifier_continue(text[end]):
            end += 1
        yield text[name_start:end], cursor, end, raw
        cursor = end


def _validate_reviewed_outer_boundary(masked, start, relative, label):
    line_start = masked.rfind("\n", 0, start) + 1
    if masked[line_start:start].strip():
        die(
            "reviewed Rust escape block has an outer modifier in {0}: {1}".format(
                relative, label
            )
        )
    prefix = masked[:start].rstrip()
    allowed_previous = ";}"
    if label in REVIEWED_RUST_BRACED_BLOCKS:
        allowed_previous += "{"
    if prefix and prefix[-1] not in allowed_previous:
        die(
            "reviewed Rust escape block has an outer attribute in {0}: {1}".format(
                relative, label
            )
        )


def _rust_brace_depth(masked, end, relative):
    depth = 0
    for character in masked[:end]:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                die("unbalanced Rust braces in {0}".format(relative))
    return depth


def reject_unreviewed_rust_escapes(relative, text):
    original_masked = _mask_rust_comments_and_literals(text, relative)
    masked = list(original_masked)
    previous_end = 0
    for label, block in REVIEWED_RUST_ESCAPE_BLOCKS.get(relative, ()):
        count = text.count(block)
        if count != 1:
            die(
                "reviewed Rust escape block differs in {0}: {1} count={2}".format(
                    relative, label, count
                )
            )
        start = text.find(block)
        prefix = REVIEWED_RUST_BLOCK_PREFIXES.get(label, "")
        full_start = start - len(prefix)
        if full_start < 0 or text[full_start:start] != prefix:
            die(
                "reviewed Rust escape block prefix differs in {0}: {1}".format(
                    relative, label
                )
            )
        reviewed = prefix + block
        reviewed_masked = _mask_rust_comments_and_literals(reviewed, relative)
        end = start + len(block)
        if full_start < previous_end:
            die(
                "reviewed Rust escape block order differs in {0}: {1}".format(
                    relative, label
                )
            )
        if original_masked[full_start:end] != reviewed_masked:
            die(
                "reviewed Rust escape block is not active in {0}: {1}".format(
                    relative, label
                )
            )
        expected_depth = REVIEWED_RUST_BLOCK_DEPTHS.get(label)
        if expected_depth is not None:
            actual_depth = _rust_brace_depth(
                original_masked, full_start, relative
            )
            if actual_depth != expected_depth:
                die(
                    "reviewed Rust escape block depth differs in {0}: "
                    "{1} actual={2} expected={3}".format(
                        relative, label, actual_depth, expected_depth
                    )
                )
        if label in REVIEWED_RUST_OUTER_BLOCKS:
            _validate_reviewed_outer_boundary(
                original_masked, full_start, relative, label
            )
        _blank_rust_span(masked, text, start, end)
        previous_end = end
    masked = "".join(masked)
    forbidden = next(
        (
            name for name, _start, _end, raw in _rust_identifiers(masked)
            if name in FORBIDDEN_RUST_IDENTIFIERS
            and not (raw and name == "extern")
        ),
        None,
    )
    if forbidden is not None:
        die(
            "unreviewed Rust escape hatch in {0}: {1}".format(
                relative, forbidden
            )
        )


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    contract = manifest["build_contract"]
    if contract.get("project_c_link_objects") != 0:
        die("project_c_link_objects must be zero")
    if contract.get("manual_rustc_invocation_forbidden") is not True:
        die("manual rustc invocation must be forbidden")
    if contract.get("prebuilt_project_objects_forbidden") is not True:
        die("prebuilt project objects must be forbidden")

    destinations = set()
    modules = manifest.get("modules", [])
    if len(modules) != 3:
        die("expected exactly three native host modules")
    for module in modules:
        source = module["source"]
        relative = source["repository_path"]
        if not relative.endswith(".rs"):
            die("non-Rust crate root: {0}".format(relative))
        if any(relative.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            die("forbidden project input: {0}".format(relative))
        path = regular_repo_file(relative)
        if sha256(path) != source["sha256"]:
            die("crate root digest drift: {0}".format(relative))
        text = read_text(path)
        if "module!" not in text or "impl kernel::Module" not in text:
            die("missing Rust-for-Linux module entry point: {0}".format(relative))
        reject_unreviewed_rust_escapes(relative, text)
        destination = source["destination"]
        if destination in destinations:
            die("duplicate staged destination: {0}".format(destination))
        destinations.add(destination)

    support = [
        item for item in manifest.get("inputs", [])
        if item.get("kind") in (
            "shared_rust_abi", "rust_ioctl_dispatch", "rust_module",
            "rust_support_module"
        )
    ]
    if [item.get("destination") for item in support] != [
        "abi/x86_64.rs",
        "ikc_queue.rs",
        "os_registry.rs",
        "device_registry.rs",
        "ikc_master.rs",
        "ihk_ioctl.rs",
        "page_allocator.rs",
        "page_owner_registry.rs",
        "smp_resource.rs",
    ]:
        die(
            "Rust support input closure differs from the locked ABI, queue, "
            "OS registry, device registry, IKC master, IHK ioctl dispatcher, page allocator, "
            "page-owner registry, and SMP resource policy"
        )
    for item in support:
        relative = item.get("repository_path")
        if not isinstance(relative, str) or not relative.endswith(".rs"):
            die("non-Rust support input: {0}".format(relative))
        path = regular_repo_file(relative)
        if sha256(path) != item.get("sha256"):
            die("support input digest drift: {0}".format(relative))
        text = read_text(path)
        reject_unreviewed_rust_escapes(relative, text)
        destination = item.get("destination")
        if destination in destinations:
            die("duplicate staged destination: {0}".format(destination))
        destinations.add(destination)

    kbuild = regular_repo_file("host-kernel/kbuild/Kbuild.in")
    ktext = read_text(kbuild).lower()
    for token in ("rustc", "$(shell", ".c ", ".o ", ".a ", ".so "):
        if token in ktext:
            die("forbidden Kbuild construct: {0}".format(token))

    print("native-rust-host-audit: PASS modules=3 project_c_link_objects=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
