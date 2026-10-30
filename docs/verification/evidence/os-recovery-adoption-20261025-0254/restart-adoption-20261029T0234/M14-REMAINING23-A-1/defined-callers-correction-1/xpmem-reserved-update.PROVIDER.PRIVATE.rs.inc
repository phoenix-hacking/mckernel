// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Append inside xpmem_helpers.rs. This is unselected private implementation.
#[cfg(f03_mmap_range_reservation_candidate)]
mod f03_reserved_xpmem_update_v1 {
    use super::*;
    use core::ptr::null_mut;

    // Passing a deliberately non-matching NULL current_vm makes the EXISTING pin
    // body take/release the source-VM reader even for a same-VM source. In its
    // missing-stack path it releases that reader before page_fault_process_vm,
    // avoiding holding the reader while the stack fault acquires a writer.
    unsafe extern "C" fn pin_page(tg: *mut c_void, thread: *mut c_void,
        src_vm: *mut c_void, vaddr: CULong, page_in: CInt) -> CInt {
        xpmem_pin_page_body_result(tg, thread, src_vm, null_mut(), vaddr, page_in,
            &XPMEM_PIN_PAGE_OFFSETS, Some(xpmem_rwspin_read_lock_noirq_bridge),
            Some(xpmem_rwspin_read_unlock_noirq_bridge), Some(xpmem_lookup_range_bridge),
            Some(xpmem_page_fault_vm_bridge), Some(xpmem_page_fault_range_bridge),
            Some(xpmem_atomic_inc_bridge))
    }
    unsafe extern "C" fn ensure_valid(seg: *mut c_void, vaddr: CULong, page_in: CInt) -> CInt {
        xpmem_ensure_valid_page_body_result(seg, vaddr, page_in,
            &XPMEM_ENSURE_VALID_PAGE_OFFSETS, Some(pin_page))
    }
    static OPS: XpmemFaultProcessRangeOps = XpmemFaultProcessRangeOps {
        att_ref_fn: Some(xpmem_att_ref), att_deref_fn: Some(xpmem_att_deref_bridge),
        ap_ref_fn: Some(xpmem_ap_ref), ap_deref_fn: Some(xpmem_ap_deref_bridge),
        tg_ref_fn: Some(xpmem_tg_ref_bridge), tg_deref_fn: Some(xpmem_tg_deref_bridge),
        seg_ref_fn: Some(xpmem_seg_ref), seg_deref_fn: Some(xpmem_seg_deref_bridge),
        bug_on_fn: Some(xpmem_bug_on_bridge), ensure_valid_fn: Some(ensure_valid),
        read_lock_noirq_fn: Some(xpmem_rwspin_read_lock_noirq_bridge),
        read_unlock_noirq_fn: Some(xpmem_rwspin_read_unlock_noirq_bridge),
        vaddr_to_pte_fn: Some(xpmem_vaddr_to_pte_bridge),
        pte_present_fn: Some(xpmem_pte_present_bridge), pte_phys_fn: Some(xpmem_pte_phys_bridge),
        pt_lookup_pte_fn: Some(xpmem_pt_lookup_pte_bridge),
        smaller_page_fn: Some(xpmem_get_smaller_page_size_bridge),
        adjust_page_fn: Some(xpmem_adjust_page_size_bridge),
        vrflag_to_ptattr_fn: Some(xpmem_vrflag_to_ptattr_bridge),
        pgsize_contiguous_fn: Some(xpmem_pgsize_contiguous_bridge),
        pt_set_pte_fn: Some(xpmem_pt_set_pte_bridge), pt_set_range_fn: Some(xpmem_pt_set_range_bridge),
        atomic_dec_fn: Some(xpmem_atomic_dec_bridge),
        flush_tlb_single_fn: Some(xpmem_flush_tlb_single_bridge), log_fn: Some(xpmem_fault_log_bridge),
    };
    unsafe extern "C" fn fault(vm: *mut c_void, range: *mut c_void,
        vaddr: CULong, reason: CULong, page_in: CInt) -> CInt {
        let process = xpmem_current_process();
        if process.is_null() { return -EINVAL; }
        // As in pin_page, a NULL comparison sentinel forces the existing fault
        // body to lock its source VM before lookups, including same-VM sources.
        xpmem_fault_process_memory_range_body_result(vm, range, vaddr, reason, page_in,
            (*process).pid, null_mut(), &XPMEM_FAULT_PROCESS_RANGE_OFFSETS, &OPS)
    }
    /// # Safety
    /// `vm`/`range` are the exact active reservation protected by ALL relevant
    /// range mutations, teardown and XPMEM detach paths. Provider verifies token
    /// identity but does not create ownership. Token and caller VM remain live until this
    /// synchronous call returns. The reserved node and its private-data graph are
    /// stable; page-table and attachment providers retain their own lock/ref rules.
    /// This is not selectable until mutator participation and all nested lock
    /// orders, page faults and graph lifetime have independent review.
    #[no_mangle]
    pub unsafe extern "C" fn f03_mmap_xpmem_update_reserved_v1(
        vm: *mut ProcessVm, range: *mut VmRange, token: *mut c_void,
    ) -> CInt {
        // Invalid token is an internal ownership failure, never an invented ACK.
        assert!(crate::syscall_policy::f03_mmap_range_reservation_v1::is_registered(
            vm, range, token.cast()));
        let process = xpmem_current_process();
        if process.is_null() { return -EINVAL; }
        xpmem_update_process_page_table_body_result(vm.cast(), range.cast(), (*process).pid,
            xpmem_page_in_remote_on_attach, &XPMEM_UPDATE_PAGE_TABLE_OFFSETS,
            Some(xpmem_att_ref), Some(xpmem_att_deref_bridge), Some(xpmem_ap_ref),
            Some(xpmem_ap_deref_bridge), Some(xpmem_tg_ref_bridge), Some(xpmem_tg_deref_bridge),
            Some(xpmem_seg_ref), Some(xpmem_seg_deref_bridge), Some(xpmem_bug_on_bridge),
            Some(fault), Some(xpmem_pt_lookup_pte_bridge), Some(xpmem_pte_present_bridge),
            Some(xpmem_update_page_table_log_bridge))
    }
}
