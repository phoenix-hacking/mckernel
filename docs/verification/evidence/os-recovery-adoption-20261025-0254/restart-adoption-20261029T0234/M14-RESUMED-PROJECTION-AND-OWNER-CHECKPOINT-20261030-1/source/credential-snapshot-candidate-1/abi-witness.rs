// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Include in a selected-source witness build; not compiled by this assignment.
use crate::abi::Process;
use core::mem::offset_of;
#[no_mangle]
pub static f03_cred_rust_process_offsets_v1: [usize; 9] = [
    offset_of!(Process, update_lock),
    offset_of!(Process, ruid), offset_of!(Process, euid),
    offset_of!(Process, suid), offset_of!(Process, fsuid),
    offset_of!(Process, rgid), offset_of!(Process, egid),
    offset_of!(Process, sgid), offset_of!(Process, fsgid),
];
