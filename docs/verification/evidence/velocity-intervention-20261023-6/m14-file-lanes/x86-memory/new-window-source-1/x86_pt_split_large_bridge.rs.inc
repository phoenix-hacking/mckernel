pub unsafe extern "C" fn x86_pt_split_large_bridge(
    ptep: *mut CULong, pgsize: SizeT,
) -> CInt {
    unsafe {
        x86_split_large_page_body_result(
            ptep, pgsize, IHK_MC_AP_NOWAIT,
            Some(x86_split_alloc_new_pt_bridge), Some(x86_pt_virt_to_phys_bridge),
            Some(x86_split_phys_to_page_bridge), Some(x86_split_page_map_bridge),
            Some(x86_split_rss_add_bridge), Some(x86_split_rss_sub_bridge),
            Some(x86_split_page_unmap_bridge), Some(x86_split_log_bridge),
            Some(x86_split_panic_bridge),
        )
    }
}
