// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private nonoverlapping syscall_policy fragment: no existing helper/body/FFI edits.
unsafe extern "C" fn f03_exec_unmap_write_lock_v1(lock:*mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_write_lock_noirq(lock.cast());
}
unsafe extern "C" fn f03_exec_unmap_write_unlock_v1(lock:*mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_write_unlock_noirq(lock.cast());
}
unsafe extern "C" fn f03_exec_unmap_lookup_v1(
    vm:*mut c_void,start:CULong,end:CULong,
)->*mut c_void {
    crate::process_helpers::lookup_process_memory_range(vm.cast(),start,end).cast()
}
unsafe extern "C" fn f03_exec_unmap_next_v1(
    vm:*mut c_void,range:*mut c_void,
)->*mut c_void {
    crate::process_helpers::next_process_memory_range(vm.cast(),range.cast()).cast()
}
unsafe extern "C" fn f03_exec_unmap_free_ranges_v1(vm:*mut c_void) {
    crate::process_helpers::free_process_memory_ranges(vm.cast());
}
unsafe extern "C" fn f03_exec_unmap_log_v1(addr:CULong,len:SizeT,error:CInt) {
    kprintf(c"munmap_all():do_munmap(%p,%lx) failed. %d\n".as_ptr().cast(),
        addr as *mut c_void,len,error);
}
/// # Safety
/// Current CPU/thread/VM and their locks/ranges retain their original exec caller
/// lifetime. This consumes the old VM's ranges; caller may not recover user state.
/// The next range is obtained by the unchanged helper before do_munmap may free
/// the current range. Errors remain diagnostics; no new success/rollback claim.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_unmap_old_image_v1() {
    let thread=(*get_this_cpu_local_var()).current;
    let vm=(*thread).vm;
    munmap_all_body_result(
        vm.cast(),addr_of_mut!((*vm).memory_range_lock).cast(),
        addr_of_mut!((*vm).region).cast(),
        offset_of!(VmRange,start),offset_of!(VmRange,end),
        offset_of!(VmRegions,map_start),offset_of!(VmRegions,map_end),
        Some(f03_exec_unmap_write_lock_v1),Some(f03_exec_unmap_write_unlock_v1),
        Some(f03_exec_unmap_lookup_v1),Some(f03_exec_unmap_next_v1),
        Some(munmap_do_bridge),Some(f03_exec_unmap_free_ranges_v1),
        Some(f03_exec_unmap_log_v1),
    );
}
