    // Existing public providers; opaque VM/PT pointers preserve the C pointer ABI.
    fn ihk_mc_pt_lookup_pte(
        pt: *mut c_void, virt: *mut c_void, pgshift: CInt,
        basep: *mut *mut c_void, sizep: *mut usize, p2alignp: *mut CInt,
    ) -> *mut CULong;
    fn page_fault_process_vm(vm: *mut c_void, virt: *mut c_void, reason: CULong) -> CInt;

/// Preserve the complete default VM fault/PTE/NUMA lookup entry.
///
/// # Safety
/// The caller retains the original VM/address-space/page-table lifetime and the
/// original mapping synchronization. This entry adds no reference or lock. The
/// same helper faults first, propagates the exact error, then resolves an active
/// PTE and its physical NUMA node; the default helper's null behavior is unchanged.
#[no_mangle]
pub unsafe extern "C" fn lookup_node(vm: *mut ProcessVm, addr: *mut c_void) -> CInt {
    unsafe {
        mem_lookup_node_body_result(
            vm.cast(), addr,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm), Some(phys_to_nid),
        )
    }
}

