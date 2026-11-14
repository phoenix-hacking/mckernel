#[no_mangle]
pub unsafe extern "C" fn do_munmap_body_result(
    vm: *mut c_void,
    proc: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    proc_straight_va_offset: SizeT,
    proc_straight_len_offset: SizeT,
    begin_fn: Option<DoMunmapVoidFn>,
    remove_range_fn: Option<DoMunmapRemoveRangeFn>,
    clear_host_pte_fn: Option<DoMunmapClearHostFn>,
    set_host_vma_fn: Option<MprotectSetHostVmaFn>,
    finish_fn: Option<DoMunmapVoidFn>,
    log_fn: Option<DoMunmapLogFn>,
) -> CInt {
    if let Some(begin) = begin_fn {
        begin();
    }

    let mut ro_freed = 0;
    let mut error = if let Some(remove_range) = remove_range_fn {
        remove_range(vm, addr, addr.wrapping_add(len as CULong), &mut ro_freed)
    } else {
        -EINVAL
    };

    let straight_va = *field_ptr::<CULong>(proc.cast::<u8>(), proc_straight_va_offset);
    let straight_len = *field_ptr::<SizeT>(proc.cast::<u8>(), proc_straight_len_offset);
    if straight_va == 0
        || addr < straight_va
        || addr.wrapping_add(len as CULong) > straight_va.wrapping_add(straight_len as CULong)
    {
        if error != 0 || ro_freed == 0 {
            if let Some(clear_host_pte) = clear_host_pte_fn {
                let clear_error = clear_host_pte(addr, len, holding_memory_range_lock);
                if error == 0 {
                    error = clear_error as CInt;
                }
            }
        } else {
            error = if let Some(set_host_vma) = set_host_vma_fn {
                set_host_vma(
                    addr,
                    len,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    holding_memory_range_lock,
                )
            } else {
                -EINVAL
            };
        }
    }

    if let Some(finish) = finish_fn {
        finish();
    }
    if let Some(log) = log_fn {
        log(addr, len, error);
    }
    error
}
