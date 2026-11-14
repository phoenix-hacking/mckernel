#[no_mangle]
pub unsafe extern "C" fn move_pages_smp_req_prepare_result(
    req: *mut MovePagesSmpReq,
    count: CULong,
    user_virt_addr: *mut *const c_void,
    user_status: *mut CInt,
    user_nodes: *const CInt,
    virt_addr: *mut *mut c_void,
    status: *mut CInt,
    ptep: *mut *mut c_void,
    nodes: *mut CInt,
    nr_pages: *mut CInt,
    dst_phys: *mut CULong,
    proc: *mut c_void,
) -> CInt {
    if req.is_null() {
        return -EINVAL;
    }

    (*req).count = count;
    (*req).user_virt_addr = user_virt_addr;
    (*req).user_status = user_status;
    (*req).user_nodes = user_nodes;
    (*req).virt_addr = virt_addr;
    (*req).status = status;
    (*req).ptep = ptep;
    (*req).nodes = nodes;
    (*req).nodes_ready = 0;
    (*req).nr_pages = nr_pages;
    (*req).dst_phys = dst_phys;
    (*req).proc = proc;
    (*req).phase_done.counter = 0;
    (*req).phase_ret = 0;
    0
}
