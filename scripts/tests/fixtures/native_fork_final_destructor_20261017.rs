// SPDX-License-Identifier: GPL-2.0
// Exact release bodies; kernel objects/callback plumbing are C test adapters.
#![allow(dead_code)]
use core::ffi::c_void;
type CInt = i32;
type CULong = u64;
const EINVAL: CInt = 22;
#[repr(C)]
struct RbRoot { head: *mut c_void }
@CALLBACK_TYPES@
unsafe fn field_ptr(object: *mut c_void, offset: CULong) -> *mut c_void {
    *object.cast::<u8>().add(offset as usize).cast::<*mut c_void>()
}
unsafe extern "C" {
    fn process_ref_dec_and_test_result(object: *mut c_void, offset: CULong,
        dec: Option<ProcessRefDecAndTestFn>) -> CInt;
    fn process_ref_release_should_destroy_result(result: CInt) -> CInt;
    fn process_thread_profile_result(thread: *mut c_void, proc: *mut c_void,
        profile: Option<ProcessThreadProfileFn>) -> CInt;
    fn process_thread_action_result(thread: *mut c_void, action: Option<ProcessThreadActionFn>) -> CInt;
    fn process_vm_action_result(vm: *mut c_void, action: Option<ProcessVmActionFn>) -> CInt;
    fn process_spin_lock_result(lock: CULong, action: Option<ProcessSpinLockFn>) -> CULong;
    fn process_spin_unlock_result(lock: CULong, state: CULong, action: Option<ProcessSpinUnlockFn>) -> CInt;
    fn process_mckfd_close_all_result(head: *mut c_void, next: CULong, close: CULong) -> CInt;
    fn process_release_vm_should_run_free_cb_result(address: CULong) -> CInt;
    fn process_vm_free_cb_result(vm: *mut c_void, opt: *mut c_void,
        action: Option<ProcessVmFreeCallback>) -> CInt;
    fn process_release_vm_detach_process_result(vm: *mut c_void, address_space: CULong,
        proc: CULong, pid: CULong, proc_vm: CULong, detach: Option<ProcessDetachAddressSpaceFn>,
        release: Option<ProcessReleaseProcessFn>) -> CInt;
    fn process_vm_policy_drain_free_result(root: *mut RbRoot, node: CULong,
        action: Option<ProcessPolicyFreeFn>) -> CInt;
    fn process_free_callback_result(object: *mut c_void, action: Option<ProcessFreeFn>) -> CInt;
    fn fork_final_destructor_suite(use_rust: CInt) -> *const core::ffi::c_char;
    fn fork_final_destructor_poison_controls() -> CInt;
}
@ACTUAL_RUST_BODIES@

#[test]
fn exact_rust_and_c_release_bodies_match_all_vectors() {
    let c_report = unsafe { std::ffi::CStr::from_ptr(fork_final_destructor_suite(0)) }.to_bytes().to_vec();
    let rust_report = unsafe { std::ffi::CStr::from_ptr(fork_final_destructor_suite(1)) }.to_bytes().to_vec();
    assert_eq!(c_report, rust_report);
    assert!(std::str::from_utf8(&c_report).unwrap().contains("checked-release-vectors="));
}

#[test]
fn inaccessible_destroyed_objects_reject_post_free_reads() {
    assert_eq!(unsafe { fork_final_destructor_poison_controls() }, 2);
}
