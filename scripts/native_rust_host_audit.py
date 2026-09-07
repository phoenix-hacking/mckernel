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
            "IHK SMP provider open ABI",
            '''#[export_name = "ihk_smp_provider_open_v1"]
// SAFETY: This exported C ABI carries only a u32 argument and i64 result;
// every expected failure becomes a negative errno and no unwind may cross it.
pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {''',
        ),
        (
            "IHK SMP provider open export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_open_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_OPEN_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_open_v1 as *const () as *const u8,
};''',
        ),
        (
            "IHK SMP provider close ABI",
            '''#[export_name = "ihk_smp_provider_close_v1"]
// SAFETY: This exported C ABI carries only an i64 receipt; detectable ownership
// faults fail stop inside the kernel and no unwind may cross the module boundary.
pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {''',
        ),
        (
            "IHK SMP provider close export record",
            '''#[export_name = "__export_symbol_ihk_smp_provider_close_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_CLOSE_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0",
    namespace: *b"MCKERNEL_IHK_V1\\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_close_v1 as *const () as *const u8,
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
    "host-kernel/native-rust/ihk_smp_x86_64.rs": (('IHK exact generated compatibility build identity',
  'const IHK_COMPAT_BUILD_ID: &[u8] = include_bytes!("ihk-compat-build-id.bin");'),
 ('IHK SMP init callback type', 'type IhkSmpProviderInitV2 = extern "C" fn() -> i32;'),
 ('IHK SMP exit callback type', 'type IhkSmpProviderExitV2 = extern "C" fn();'),
 ('IHK SMP OS ioctl callback type',
  'type IhkSmpOsIoctlV2 = unsafe extern "C" fn(u32, u64, u32, u64, u32) -> i64;'),
 ('IHK SMP OS release callback type',
  'type IhkSmpOsReleaseV2 = unsafe extern "C" fn(u32, u64) -> i32;'),
 ('IHK SMP provider and OS import',
  'extern "C" {\n'
  '    #[link_name = "ihk_provider_lifecycle_v1"]\n'
  '    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n'
  '    #[link_name = "ihk_smp_provider_attach_v2"]\n'
  '    fn ihk_smp_provider_attach_v2(\n'
  '        callback_abi: u32,\n'
  '        flags: u32,\n'
  '        init: Option<IhkSmpProviderInitV2>,\n'
  '        exit: Option<IhkSmpProviderExitV2>,\n'
  '    ) -> i64;\n'
  '    #[link_name = "ihk_smp_provider_detach_v2"]\n'
  '    fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);\n'
  '    #[link_name = "ihk_smp_provider_open_v1"]\n'
  '    fn ihk_smp_provider_open_v1(minor: u32) -> i64;\n'
  '    #[link_name = "ihk_smp_provider_close_v1"]\n'
  '    fn ihk_smp_provider_close_v1(receipt: i64);\n'
  '    #[link_name = "ihk_os_create_unbooted_v2"]\n'
  '    fn ihk_os_create_unbooted_v2(\n'
  '        provider_minor: u32,\n'
  '        owner: *mut core::ffi::c_void,\n'
  '        argument: u64,\n'
  '        callback_abi: u32,\n'
  '        ioctl: Option<IhkSmpOsIoctlV2>,\n'
  '        release: Option<IhkSmpOsReleaseV2>,\n'
  '    ) -> i64;\n'
  '    #[link_name = "ihk_os_destroy_unbooted_v1"]\n'
  '    fn ihk_os_destroy_unbooted_v1(provider_minor: u32, minor: u64) -> i64;\n'
  '}'),
 ('IHK SMP OS ioctl callback ABI',
  'unsafe extern "C" fn ihk_smp_os_ioctl_v2(\n'
  '    slot: u32,\n'
  '    generation: u64,\n'
  '    command: u32,\n'
  '    argument: u64,\n'
  '    compat: u32,\n'
  ') -> i64 {'),
 ('IHK SMP OS release callback ABI',
  'unsafe extern "C" fn ihk_smp_os_release_v2(slot: u32, generation: u64) -> i32 {'),
 ('IHK SMP init callback ABI', 'extern "C" fn ihk_smp_provider_init_v2() -> i32 {'),
 ('IHK SMP exit callback ABI', 'extern "C" fn ihk_smp_provider_exit_v2() {'),
 ('IHK SMP parameter descriptor section',
  '#[link_section = "__param"]\n'
  '        #[used(compiler)]\n'
  '        static $descriptor: KernelParameter = KernelParameter {'),
 ('IHK SMP loadable parameter metadata',
  '#[link_section = ".modinfo"]\n'
  '        #[used(compiler)]\n'
  '        static $loadable_name: [u8; $loadable.len()] = *$loadable;'),
 ('IHK SMP built-in parameter metadata',
  '#[link_section = ".modinfo"]\n'
  '        #[used(compiler)]\n'
  '        static $builtin_name: [u8; $builtin.len()] = *$builtin;')),
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

REVIEWED_RUST_ESCAPE_BLOCKS['host-kernel/native-rust/smp_cpu.rs'] = (
    ('CPU adapter shared ABI', '#[path = "abi/x86_64.rs"]\nmod abi;'),
    ('CPU adapter APIC import', '''extern "C" {
    fn default_cpu_present_to_apicid(cpu: i32) -> u32;
}'''),
    ('CPU adapter online callback', 'unsafe extern "C" fn allow_cpu_online(cpu: u32) -> i32 {'),
)

REVIEWED_RUST_ESCAPE_BLOCKS['host-kernel/native-rust/smp_memory.rs'] = (
    ('Memory adapter shared ABI', '#[path = "abi/x86_64.rs"]\nmod abi;'),
)

REVIEWED_RUST_ESCAPE_BLOCKS['host-kernel/native-rust/os_runtime.rs'] = (('OS Linux kernel exports',
  'extern "C" {\n'
  '    fn __register_chrdev(\n'
  '        major: u32,\n'
  '        base: u32,\n'
  '        count: u32,\n'
  '        name: *const i8,\n'
  '        operations: *const c_void,\n'
  '    ) -> i32;\n'
  '    fn __unregister_chrdev(major: u32, base: u32, count: u32, name: *const i8);\n'
  '    fn class_create(name: *const i8) -> *mut bindings::class;\n'
  '    fn class_destroy(class: *const bindings::class);\n'
  '    fn device_create(\n'
  '        class: *const bindings::class,\n'
  '        parent: *mut c_void,\n'
  '        dev: u32,\n'
  '        data: *mut c_void,\n'
  '        format: *const i8,\n'
  '        ...\n'
  '    ) -> *mut c_void;\n'
  '    fn device_destroy(class: *const bindings::class, dev: u32);\n'
  '    fn get_free_pages_noprof(flags: u32, order: u32) -> usize;\n'
  '    fn free_pages(address: usize, order: u32);\n'
  '    fn try_module_get(module: *mut c_void) -> bool;\n'
  '    fn module_put(module: *mut c_void);\n'
  '}'),
 ('OS backend ioctl callback type',
  'type OsBackendIoctlV2 = unsafe extern "C" fn(u32, u64, u32, u64, u32) -> i64;'),
 ('OS backend release callback type',
  'type OsBackendReleaseV2 = unsafe extern "C" fn(u32, u64) -> i32;'),
 ('OS create ABI',
  '#[export_name = "ihk_os_create_unbooted_v1"]\n'
  '// SAFETY: The C caller supplies its already pinned Linux module pointer; this\n'
  '// adapter acquires a separate module reference before publishing any OS node.\n'
  'pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v1(\n'
  '    provider_minor: u32,\n'
  '    owner: *mut c_void,\n'
  '    argument: u64,\n'
  ') -> i64 {'),
 ('OS create v2 ABI',
  '#[export_name = "ihk_os_create_unbooted_v2"]\n// SAFETY: This C ABI accepts a pinned Linux module pointer and trusted callback\n// identities with the exact scalar signature; no unwind may cross the boundary.\npub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v2(\n    provider_minor: u32,\n    owner: *mut c_void,\n    argument: u64,\n    callback_abi: u32,\n    ioctl: Option<OsBackendIoctlV2>,\n    release: Option<OsBackendReleaseV2>,\n) -> i64 {'),
 ('OS destroy ABI',
  '#[export_name = "ihk_os_destroy_unbooted_v1"]\n'
  '// SAFETY: Only scalar identities cross this C ABI. Registry guards validate\n'
  '// ownership and exclude live open files before any allocation is reclaimed.\n'
  'pub(crate) extern "C" fn ihk_os_destroy_unbooted_v1(provider_minor: u32, minor: u64) -> i64 {'),
 ('OS open ABI',
  'unsafe extern "C" fn os_open(inode: *mut bindings::inode, file: *mut bindings::file) -> i32 {'),
 ('OS release ABI',
  'unsafe extern "C" fn os_release(_inode: *mut bindings::inode, file: *mut bindings::file) -> i32 '
  '{'),
 ('OS ioctl ABI',
  'unsafe extern "C" fn os_ioctl(\n'
  '    file: *mut bindings::file,\n'
  '    command: u32,\n'
  '    argument: core::ffi::c_ulong,\n'
  ') -> core::ffi::c_long {'),
 ('OS compat ioctl ABI',
  '#[cfg(CONFIG_COMPAT)]\n'
  'unsafe extern "C" fn os_compat_ioctl(\n'
  '    file: *mut bindings::file,\n'
  '    command: u32,\n'
  '    argument: core::ffi::c_ulong,\n'
  ') -> core::ffi::c_long {'),
 ('OS create export record',
  '#[export_name = "__export_symbol_ihk_os_create_unbooted_v1"]\n'
  '#[link_section = ".export_symbol"]\n'
  '#[used(compiler)]\n'
  'pub(crate) static IHK_OS_CREATE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {\n'
  '    license: *b"GPL\\0",\n'
  '    namespace: *b"MCKERNEL_IHK_V1\\0",\n'
  '    padding: [0; 4],\n'
  '    symbol: ihk_os_create_unbooted_v1 as *const () as *const u8,\n'
  '};'),
 ('OS create v2 export record',
  '#[export_name = "__export_symbol_ihk_os_create_unbooted_v2"]\n'
  '#[link_section = ".export_symbol"]\n'
  '#[used(compiler)]\n'
  'pub(crate) static IHK_OS_CREATE_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {\n'
  '    license: *b"GPL\\0",\n'
  '    namespace: *b"MCKERNEL_IHK_V1\\0",\n'
  '    padding: [0; 4],\n'
  '    symbol: ihk_os_create_unbooted_v2 as *const () as *const u8,\n'
  '};'),
 ('OS destroy export record',
  '#[export_name = "__export_symbol_ihk_os_destroy_unbooted_v1"]\n'
  '#[link_section = ".export_symbol"]\n'
  '#[used(compiler)]\n'
  'pub(crate) static IHK_OS_DESTROY_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {\n'
  '    license: *b"GPL\\0",\n'
  '    namespace: *b"MCKERNEL_IHK_V1\\0",\n'
  '    padding: [0; 4],\n'
  '    symbol: ihk_os_destroy_unbooted_v1 as *const () as *const u8,\n'
  '};'))

REVIEWED_RUST_BLOCK_PREFIXES = {
    "CPU adapter shared ABI": "#[allow(dead_code, unreachable_pub)]\n",
    "Memory adapter shared ABI": "#[allow(dead_code, unreachable_pub)]\n",
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
    "IHK SMP provider open ABI": '''#[doc(hidden)]
// SAFETY: This C-ABI boundary accepts only the scalar device minor and returns
// either a positive opaque provider-generation receipt or a negative errno.
// The receipt does not encode a pointer or Rust layout.  Its open reference is
// owned exactly once by the caller's non-Copy per-file wrapper.
''',
    "IHK SMP provider open export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar open function in MCKERNEL_IHK_V1 for the provider lifetime.
''',
    "IHK SMP provider close ABI": '''#[doc(hidden)]
// SAFETY: This C-ABI boundary accepts only a positive scalar generation token
// returned by open.  Shared opens intentionally receive the same scalar, so
// the trusted caller's non-Copy per-file owners must keep calls count-balanced;
// malformed, stale, and zero-reference closes fail stop.
''',
    "IHK SMP provider close export record": '''#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar close function in MCKERNEL_IHK_V1 for the provider lifetime.
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
        "CPU adapter shared ABI",
        "CPU adapter APIC import",
        "CPU adapter online callback",
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
        "IHK SMP provider open ABI",
        "IHK SMP provider open export record",
        "IHK SMP provider close ABI",
        "IHK SMP provider close export record",
        "IHK loadable version metadata",
        "IHK built-in version metadata",
        "IHK SMP init callback type",
        "IHK SMP exit callback type",
        "IHK SMP provider and OS import",
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

REVIEWED_RUST_BLOCK_PREFIXES.update({'OS Linux kernel exports': '// SAFETY: These are Linux 6.12 kernel exports with their C header ABI.\n// Calls below supply only module-resident operations, registered device IDs,\n// valid kernel module pointers or allocation addresses owned by this adapter.\n', 'OS create ABI': "// SAFETY: Called only by the pinned native SMP control-file ioctl. The owner\n// is the caller's Linux module pointer, never a user argument or Rust object.\n// No callback or caller data is retained; a Linux module reference is acquired.\n", 'OS destroy ABI': '// SAFETY: This C ABI accepts scalar minor numbers only. It tears down solely an\n// unbooted OS belonging to the given live provider and propagates busy errors.\n', 'OS open ABI': '// SAFETY: Linux calls this only with a live inode/file and ihk.ko pinned by\n// .owner. Successful open installs exactly one owned lease in private_data.\n', 'OS release ABI': '// SAFETY: Linux calls release once after the final file reference. No ioctl\n// can still borrow the private lease, and .owner keeps this module resident.\n', 'OS ioctl ABI': '// SAFETY: Linux pins the file for the callback; its immutable private lease\n// keeps the exact OS generation live until this callback and all peers finish.\n', 'OS create export record': '// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.\n', 'OS destroy export record': '// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.\n'})
REVIEWED_RUST_OUTER_BLOCKS = REVIEWED_RUST_OUTER_BLOCKS | frozenset(('OS Linux kernel exports', 'OS create ABI', 'OS destroy ABI', 'OS open ABI', 'OS release ABI', 'OS ioctl ABI', 'OS create export record', 'OS destroy export record'))

REVIEWED_RUST_BLOCK_PREFIXES.update({'IHK SMP OS ioctl callback ABI': "// SAFETY: Only IHK's versioned OS object invokes this "
                                  'registered callback. It\n'
                                  '// holds an OsLease for the exact slot/generation, its '
                                  'sleepable operation lock,\n'
                                  '// and the owning SMP module reference. User pointers live only '
                                  'for this call.\n',
 'IHK SMP OS ioctl callback type': '// SAFETY: IHK holds the exact OS lease, operation lock and '
                                   'SMP module owner.\n'
                                   '// The address and compat flag are borrowed only during the '
                                   'synchronous call.\n',
 'IHK SMP OS release callback ABI': '// SAFETY: IHK invokes this only with the exclusive '
                                    'initial-state DestroyGuard\n'
                                    '// and the retained SMP module owner. No OS file, boot, or '
                                    'other resource call\n'
                                    '// can overlap cleanup for this generation. Errors leave its '
                                    'resources intact.\n',
 'IHK SMP OS release callback type': '// SAFETY: IHK holds the exclusive initial-state destruction '
                                     'guard and module\n'
                                     '// owner until this callback returns all resources or leaves '
                                     'them unchanged.\n',
 'OS backend ioctl callback type': '// SAFETY: Only IHK invokes these callbacks with a live '
                                   'OsLease or an exclusive\n'
                                   '// DestroyGuard, respectively. The owning SMP module must keep '
                                   'the callbacks\n'
                                   '// resident, accept the exact scalar ABI and borrow user '
                                   'addresses only during\n'
                                   '// ioctl. The release callback must finish all resource '
                                   'cleanup before success,\n'
                                   '// and leave the OS usable on failure. Neither callback may '
                                   'reenter OS ioctls\n'
                                   '// or destruction while the per-OS operation lock is held.\n',
 'OS backend release callback type': '// SAFETY: The exclusive destruction guard proves this exact '
                                     'slot/generation\n'
                                     '// has no open references. Success returns its resources '
                                     'before minor reuse.\n',
 'OS compat ioctl ABI': "// SAFETY: Linux's compat callback has the same file lifetime as native "
                        'ioctl.\n'
                        '// Zero-extend the top-level user address once before any backend can '
                        'parse it.\n',
 'OS create v2 ABI': '/// Create an unbooted OS with callbacks pinned by its provider module '
                     'owner.\n'
                     '/// ABI version 1 uses (slot, generation, command, user address, '
                     'compat=0/1)\n'
                     '/// for ioctl and (slot, generation) for exclusive resource cleanup.\n'
                     '///\n'
                     '/// # Safety\n'
                     '/// The caller pins `owner`, and both callbacks reside in that module and '
                     'obey\n'
                     '/// the contracts above. These are trusted code pointers, never userspace '
                     'data.\n'
                     '// SAFETY: The boundary validates the callback version and complete '
                     'callback\n'
                     '// pair before acquiring owners or publishing anything. The existing create\n'
                     '// transaction retains the module before storing either function pointer.\n',
 'OS create v2 export record': '// SAFETY: Linux modpost reads this immutable relocation for the '
                               'module lifetime.\n'})
REVIEWED_RUST_OUTER_BLOCKS = REVIEWED_RUST_OUTER_BLOCKS | frozenset(('IHK SMP OS ioctl callback type', 'IHK SMP OS release callback type', 'IHK SMP OS ioctl callback ABI', 'IHK SMP OS release callback ABI', 'OS backend ioctl callback type', 'OS backend release callback type', 'OS create v2 ABI', 'OS compat ioctl ABI', 'OS create v2 export record'))

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
        "smp_cpu.rs",
        "smp_memory.rs",
        "os_runtime.rs",
        "ihk_mapping.rs",
        "smp_image.rs",
        "smp_loader.rs",
        "smp_startup.rs",
    ]:
        die(
            "Rust support input closure differs from the locked ABI, queue, "
            "OS registry, device registry, IKC master, IHK ioctl dispatcher, page allocator, "
            "page-owner registry, SMP resource policy, unbooted OS runtime, "
            "mapping geometry, image policy and bounded file loader"
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
