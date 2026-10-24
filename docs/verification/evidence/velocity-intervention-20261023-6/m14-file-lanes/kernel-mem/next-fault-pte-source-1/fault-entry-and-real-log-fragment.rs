/// Exact former C diagnostic callback; preserve format bytes and varargs types.
unsafe extern "C" fn mem_lookup_fault_log_bridge(virt: *mut c_void) {
    unsafe {
        kprintf(
            b"%s: successfully faulted 0x%lx\n\0".as_ptr().cast(),
            b"ihk_mc_pt_lookup_fault_pte\0".as_ptr().cast::<i8>(),
            virt as CULong,
        );
    }
}

/// Complete default public fault/PTE lookup; reuse the unchanged production body.
///
/// # Safety
/// Caller retains the VM/address-space/PT and output-pointer lifetimes and the
/// same mapping synchronization as before. No new lock/reference or ownership
/// transfer is introduced. The existing body retries once after fault, ignores
/// the same fault return, and logs only an active post-fault PTE.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_lookup_fault_pte(
    vm: *mut ProcessVm, virt: *mut c_void, pgshift: CInt,
    basep: *mut *mut c_void, sizep: *mut usize, p2alignp: *mut CInt,
) -> *mut CULong {
    unsafe {
        mem_pt_lookup_fault_pte_body_result(
            vm.cast(), virt, pgshift, basep, sizep, p2alignp,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm),
            Some(mem_lookup_fault_log_bridge),
        )
    }
}

