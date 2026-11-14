#[no_mangle]
pub unsafe extern "C" fn perf_mmap_body_result(
    addr0: CULong,
    len0: SizeT,
    prot: CInt,
    flags: CInt,
    fd: CInt,
    off0: CLong,
    map_anonymous: CInt,
    prot_write: CInt,
    data_head_offset: SizeT,
    capabilities_offset: SizeT,
    cap_user_rdpmc_mask: CULong,
    do_mmap_fn: Option<PerfDoMmapFn>,
) -> CLong {
    let Some(do_mmap) = do_mmap_fn else {
        return -EINVAL as CLong;
    };

    let rc = do_mmap(
        addr0,
        len0,
        prot | prot_write,
        flags | map_anonymous,
        fd,
        off0,
        0,
        core::ptr::null_mut(),
    );

    // Defined-error successor: the actual mapping error is not a page pointer.
    // Preserve its exact errno and perform no metadata access on this branch.
    if rc < 0 {
        return rc;
    }

    // SAFETY: The caller/provider must supply the original positive, writable,
    // aligned mapping spanning both real metadata fields. No ownership is added.
    let page = rc as CULong as *mut u8;
    write_volatile(field_ptr::<CULong>(page, data_head_offset), 16);
    let capabilities = field_ptr::<CULong>(page, capabilities_offset);
    write_volatile(
        capabilities,
        read_volatile(capabilities) | cap_user_rdpmc_mask,
    );

    rc
}
