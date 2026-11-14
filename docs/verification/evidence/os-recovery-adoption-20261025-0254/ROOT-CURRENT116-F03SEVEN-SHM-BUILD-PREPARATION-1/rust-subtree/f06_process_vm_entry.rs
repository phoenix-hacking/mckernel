// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reuse the existing private entry/callbacks; canonical logger/offsets stay sole providers.
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::ptr::{addr_of, addr_of_mut, read_volatile};

use crate::abi::{CInt, CULong, Iovec, Process, ProcessVm, SizeT};
use crate::lock_helpers::McsRwlockNodeIrqsave;

use super::{
    arch_process_vm_read_writev_body_result, arch_process_vm_rw_log_bridge,
    McsRwlockNode, F06_PROCESS_VM_RW_OFFSETS,
};

unsafe extern "C" fn f06_process_vm_rw_read_lock(vm: *mut c_void) {
    unsafe {
        crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(
            addr_of_mut!((*vm.cast::<ProcessVm>()).memory_range_lock).cast(),
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_read_unlock(vm: *mut c_void) {
    unsafe {
        crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(
            addr_of_mut!((*vm.cast::<ProcessVm>()).memory_range_lock).cast(),
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_lookup(vm: *mut c_void, start: CULong, end: CULong) -> *mut c_void {
    unsafe { crate::process_helpers::lookup_process_memory_range(vm.cast(), start, end).cast() }
}
unsafe extern "C" fn f06_process_vm_rw_find(pid: CInt, node: *mut c_void) -> *mut c_void {
    unsafe { crate::process_helpers::find_process(pid, node.cast()).cast() }
}
unsafe extern "C" fn f06_process_vm_rw_process_unlock(proc: *mut c_void, node: *mut c_void) {
    unsafe { crate::process_helpers::process_unlock(proc.cast(), node.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_update_lock(proc: *mut c_void, node: *mut c_void) {
    unsafe {
        crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(
            addr_of_mut!((*proc.cast::<Process>()).update_lock).cast(), node,
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_update_unlock(proc: *mut c_void, node: *mut c_void) {
    unsafe {
        crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(
            addr_of_mut!((*proc.cast::<Process>()).update_lock).cast(), node,
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_hold(vm: *mut c_void) {
    unsafe { crate::process_helpers::hold_process_vm(vm.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_release(vm: *mut c_void) {
    unsafe { crate::process_helpers::release_process_vm(vm.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_vtop(
    pt: *mut c_void, virt: CULong, phys: *mut CULong, page_size: *mut CULong,
) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_virt_to_phys_size(pt, virt as *const c_void, phys, page_size) }
}
unsafe extern "C" fn f06_process_vm_rw_fault(vm: *mut c_void, addr: CULong, reason: CULong) -> CInt {
    unsafe { crate::process_helpers::page_fault_process_vm(vm.cast(), addr as *mut c_void, reason) }
}
unsafe extern "C" fn f06_process_vm_rw_phys(phys: CULong) -> *mut c_void {
    unsafe { crate::x86_memory_helpers::phys_to_virt(phys) }
}
unsafe extern "C" fn f06_process_vm_rw_copy(dst: *mut c_void, src: *const c_void, bytes: SizeT) {
    // Both selected Rust memcpy/fast_memcpy providers already share this exact
    // volatile byte-copy body. Keep its forward copy and zero-byte semantics.
    unsafe { let _ = crate::string::__inline_memcpy(dst, src, bytes); }
}

/// Reuse the exact validated process-VM read/write orchestration and its owners.
/// Current-thread, VM and process pointers are borrowed under the original call
/// contract. Both distinct stack lock nodes remain live until the body returns.
/// Existing callbacks alone own locks/remote-VM hold/release and fault/copy order;
/// this entry introduces no retained reference, rollback, retry or error policy.
///
/// # Safety
/// The caller supplies the same live process-VM operation and initialized iovecs
/// as the existing C entry. Current CPU/thread ownership remains valid through
/// this synchronous call. Existing providers retain process/VM/lock lifetimes,
/// user-copy validation and partial-copy/error cleanup. The two distinct stack
/// lock nodes must not escape the existing synchronous body or its callbacks.
#[no_mangle]
pub unsafe extern "C" fn do_process_vm_read_writev(
    pid: CInt, local_iov: *const c_void, liovcnt: CULong,
    remote_iov: *const c_void, riovcnt: CULong, flags: CULong, op: CInt,
) -> CInt {
    unsafe {
        let mut find_lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        let mut update_lock = MaybeUninit::<McsRwlockNode>::uninit();
        let current = read_volatile(addr_of!((*crate::cls::get_this_cpu_local_var()).current));
        arch_process_vm_read_writev_body_result(
            pid, local_iov.cast::<Iovec>(), liovcnt, remote_iov.cast::<Iovec>(), riovcnt, flags, op,
            current.cast(), find_lock.as_mut_ptr().cast(), update_lock.as_mut_ptr().cast(),
            &F06_PROCESS_VM_RW_OFFSETS,
            Some(f06_process_vm_rw_read_lock), Some(f06_process_vm_rw_read_unlock),
            Some(f06_process_vm_rw_lookup), Some(f06_process_vm_rw_find), Some(f06_process_vm_rw_process_unlock),
            Some(f06_process_vm_rw_update_lock), Some(f06_process_vm_rw_update_unlock),
            Some(f06_process_vm_rw_hold), Some(f06_process_vm_rw_release), Some(f06_process_vm_rw_vtop),
            Some(f06_process_vm_rw_fault), Some(f06_process_vm_rw_phys), Some(f06_process_vm_rw_copy),
            Some(arch_process_vm_rw_log_bridge),
        )
    }
}
