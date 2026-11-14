// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// The caller keeps vm and returned range live under the qualified VM read-lock pair.
/// No ownership, allocation, retained reference or cache algorithm changes.
unsafe extern "C" fn f06_process_vm_rw_lookup(vm: *mut c_void, start: CULong, end: CULong) -> *mut c_void {
    unsafe { crate::process_helpers::lookup_process_memory_range(vm.cast(), start, end).cast() }
}

/// # Safety
/// vm is aligned/live; caller holds memory_range_lock through all returned-range uses.
#[no_mangle]
pub unsafe extern "C" fn arch_process_vm_rw_lookup_range_bridge(vm:*mut c_void,start:CULong,end:CULong)->*mut VmRange {
    unsafe { f06_process_vm_rw_lookup(vm,start,end).cast() }
}
