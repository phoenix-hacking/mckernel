//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Current LP64 Linux>=4.6 exported data, without namespace operations or new policy.

use core::ffi::{c_char, c_int};
use core::ptr::null_mut;

#[repr(C)]
pub struct NamespaceFile {
    pub nstype: c_int,
    pub name: *const c_char,
    pub fd: c_int,
}

const _: () = {
    assert!(core::mem::size_of::<NamespaceFile>() == 24);
    assert!(core::mem::offset_of!(NamespaceFile, name) == 8);
    assert!(core::mem::offset_of!(NamespaceFile, fd) == 16);
};

// Existing externally writable, non-atomic ABI storage requires the original
// caller serialization. Immutable pointed-to string bytes remain borrowed forever.
#[no_mangle]
pub static mut namespace_files: [NamespaceFile; 8] = [
    NamespaceFile { nstype: 0x10000000, name: b"ns/user\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x02000000, name: b"ns/cgroup\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x08000000, name: b"ns/ipc\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x04000000, name: b"ns/uts\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x40000000, name: b"ns/net\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x20000000, name: b"ns/pid\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0x00020000, name: b"ns/mnt\0".as_ptr().cast(), fd: -1 },
    NamespaceFile { nstype: 0, name: core::ptr::null(), fd: -1 },
];

#[no_mangle]
pub static mut __argc: c_int = 0;

#[no_mangle]
pub static mut __argv: *mut *mut c_char = null_mut();

// Genuine private-header initialized data formerly supplied by the C TU. Keep
// its writable pointer-array ABI, despite each pointed-to C string being const.
#[no_mangle]
pub static mut ihklib_os_query_mem_type_str: [*const c_char; 2] = [
    b"MemTotal\0".as_ptr().cast(),
    b"MemFree\0".as_ptr().cast(),
];
