pub unsafe extern "C" fn ihk_mc_pt_split(
    pt: *mut c_void, vm: *mut ProcessVm,
    range: *mut crate::abi::VmRange, addr: *mut c_void,
) -> CInt {
    unsafe {
        let memobj = (*range).memobj.cast::<Memobj>();
        let memobj_flags = if memobj.is_null() { 0 } else { (*memobj).flags };
        let cpu_id = ihk_mc_get_processor_id();
        x86_pt_split_body_result(
            pt, vm.cast(), addr as CULong, memobj_flags, cpu_id,
            Some(x86_pt_split_lookup_bridge), Some(x86_split_phys_to_page_bridge),
            Some(x86_pt_splitable_bridge), Some(x86_pt_split_large_bridge),
            Some(x86_pt_split_flush_bridge), Some(x86_pt_split_log_bridge),
        )
    }
}
