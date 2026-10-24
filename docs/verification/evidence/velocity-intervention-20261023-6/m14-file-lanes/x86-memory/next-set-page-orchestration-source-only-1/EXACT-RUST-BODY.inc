// Complete original __set_pt_page orchestration. Use the existing IRQ-saving
// spinlock implementation and raw lock address; never borrow across callbacks.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_page_bridge(
    pt: *mut c_void, virt: CULong, phys: CULong, attr: CULong,
) -> CInt {
    unsafe {
        let in_kernel = x86_pt_kernel_lock_needed_result(virt) != 0;
        let mut lock: *mut crate::abi::IhkSpinlock = core::ptr::null_mut();
        let mut flags: CULong = 0;
        if in_kernel {
            lock = x86_init_page_table_lock_bridge().cast();
            flags = crate::spinlock_helpers::__ihk_mc_spinlock_lock(lock);
        }
        // Read init_pt after acquisition, exactly as the original C body did.
        let ret = x86_pt_set_page_body_result(
            pt, x86_page_table_init_pt_bridge(), virt, phys, attr,
            x86_attr_mask_bridge(), Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge), Some(x86_pt_phys_to_virt_bridge),
            Some(x86_pt_set_page_log_bridge),
        );
        if in_kernel {
            crate::spinlock_helpers::__ihk_mc_spinlock_unlock(lock, flags);
        }
        ret
    }
}
