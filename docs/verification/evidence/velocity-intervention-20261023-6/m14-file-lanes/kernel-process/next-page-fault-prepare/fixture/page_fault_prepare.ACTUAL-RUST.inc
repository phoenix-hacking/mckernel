#[no_mangle]
pub unsafe extern "C" fn process_page_fault_prepare_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep_out: *mut *mut CULong,
    pgaddr_out: *mut *mut c_void,
    pgsize_out: *mut SizeT,
    p2align_out: *mut CInt,
    error_out: *mut CInt,
) -> CInt {
    // Match the original valid borrowed inputs; add no NULL/error policy.
    crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
        &raw mut (*vm).page_table_lock,
    );
    *ptep_out = ihk_mc_pt_lookup_pte(
        (*(*vm).address_space).page_table,
        fault_addr as *mut c_void,
        (*range).pgshift,
        pgaddr_out, pgsize_out, p2align_out,
    );
    if reason & (1 | PF_PATCH) == 0 && !(*ptep_out).is_null()
        && crate::pte_helpers::pte_is_null(*ptep_out) == 0
        && crate::pte_helpers::pte_is_fileoff(*ptep_out, *pgsize_out) == 0
    {
        if crate::pte_helpers::pte_is_present(*ptep_out) == 0 {
            *error_out = -EFAULT;
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *error_out = 0;
        return 1;
    }
    if reason & 1 != 0 && ((*ptep_out).is_null()
        || crate::pte_helpers::pte_is_present(*ptep_out) == 0)
    {
        crate::x86_memory_helpers::flush_tlb_single(fault_addr);
        *error_out = 0;
        return 1;
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_page_fault_prepare_bounds_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\n\0".as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
            *pgaddr_out, (*range).start, (*range).end,
            (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong) as *mut c_void,
        );
    }
    while (*pgaddr_out as CULong) < (*range).start
        || (*range).end < (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong)
    {
        *ptep_out = null_mut();
        *error_out = crate::x86_memory_helpers::arch_get_smaller_page_size(
            null_mut(), *pgsize_out, pgsize_out, p2align_out,
        );
        if *error_out != 0 {
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *pgaddr_out = (fault_addr & !((*pgsize_out as CULong).wrapping_sub(1))) as *mut c_void;
    }
    crate::pte_helpers::arch_adjust_allocate_page_size(
        (*(*vm).address_space).page_table, fault_addr, *ptep_out,
        pgaddr_out, pgsize_out,
    );
    0
}
