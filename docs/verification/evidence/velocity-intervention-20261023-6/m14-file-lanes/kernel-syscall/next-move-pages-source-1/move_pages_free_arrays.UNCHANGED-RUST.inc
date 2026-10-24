unsafe fn move_pages_free_arrays(
    free_fn: Option<SyscallMckfdFreeFn>,
    virt_addr: *mut c_void,
    nr_pages: *mut c_void,
    nodes: *mut c_void,
    status: *mut c_void,
    ptep: *mut c_void,
    dst_phys: *mut c_void,
) {
    if let Some(free) = free_fn {
        free(virt_addr);
        free(nr_pages);
        free(nodes);
        free(status);
        free(ptep);
        free(dst_phys);
    }
}
