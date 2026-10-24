pub unsafe extern "C" fn process_invalidate_one_page_body_result(
    arg: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
    pte_null_fn: Option<ProcessPteTestFn>,
    pte_fileoff_fn: Option<ProcessPtePgsizeTestFn>,
    pte_get_phys_fn: Option<ProcessPteGetPhysFn>,
    phys_to_page_fn: Option<ProcessPhysToPageFn>,
    page_offset_fn: Option<ProcessPageOffsetFn>,
    pte_make_fileoff_fn: Option<ProcessPteMakeFileoffFn>,
    pte_xchg_fn: Option<ProcessPteXchgFn>,
    flush_tlb_single_fn: Option<ProcessFlushTlbSingleFn>,
    pte_contiguous_fn: Option<ProcessPteTestFn>,
    pte_head_fn: Option<ProcessPtePgsizeTestFn>,
    pgsize_to_tbllv_fn: Option<ProcessPgsizeToTbllvFn>,
    tbllv_to_contpgsize_fn: Option<ProcessTbllvToContpgsizeFn>,
    page_unmap_fn: Option<ProcessPageUnmapFn>,
    panic_fn: Option<ProcessPanicFn>,
    memobj_invalidate_page_fn: Option<ProcessMemobjInvalidatePageFn>,
    log_fn: Option<ProcessInvalidateOnePageLogFn>,
) -> CInt {
    if arg.is_null() || ptep.is_null() || pgshift < 0 || pgshift as usize >= SizeT::BITS as usize {
        return -EINVAL;
    }
    let Some(pte_null) = pte_null_fn else {
        return -EINVAL;
    };
    let Some(pte_fileoff) = pte_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_get_phys) = pte_get_phys_fn else {
        return -EINVAL;
    };
    let Some(phys_to_page) = phys_to_page_fn else {
        return -EINVAL;
    };
    let Some(page_offset) = page_offset_fn else {
        return -EINVAL;
    };
    let Some(pte_make_fileoff) = pte_make_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_xchg) = pte_xchg_fn else {
        return -EINVAL;
    };
    let Some(flush_tlb_single) = flush_tlb_single_fn else {
        return -EINVAL;
    };
    let Some(pte_contiguous) = pte_contiguous_fn else {
        return -EINVAL;
    };
    let Some(pte_head) = pte_head_fn else {
        return -EINVAL;
    };
    let Some(pgsize_to_tbllv) = pgsize_to_tbllv_fn else {
        return -EINVAL;
    };
    let Some(tbllv_to_contpgsize) = tbllv_to_contpgsize_fn else {
        return -EINVAL;
    };
    let Some(page_unmap) = page_unmap_fn else {
        return -EINVAL;
    };
    let Some(panic_call) = panic_fn else {
        return -EINVAL;
    };
    let Some(memobj_invalidate_page) = memobj_invalidate_page_fn else {
        return -EINVAL;
    };

    let range = *(arg.cast::<*mut VmRange>());
    if range.is_null() || (*range).memobj.is_null() {
        return -EINVAL;
    }

    let pgsize = 1usize << (pgshift as usize);
    if pte_null(ptep) != 0 || pte_fileoff(ptep, pgsize) != 0 {
        return 0;
    }

    let phys = pte_get_phys(ptep);
    let page = phys_to_page(phys);
    let linear_off = (*range)
        .objoff
        .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start) as OffT);
    let mut apte: CULong = 0;

    if !page.is_null() {
        let page_off = page_offset(page);

        if page_off != linear_off {
            pte_make_fileoff(page_off, pgsize, (&raw mut apte).cast::<c_void>());
        }
    }

    pte_xchg(ptep, (&raw mut apte).cast::<c_void>());
    flush_tlb_single(pgaddr as CULong);

    let memobj_pgsize = if pte_contiguous((&raw mut apte).cast::<c_void>()) != 0 {
        if pte_head(ptep, pgsize) != 0 {
            tbllv_to_contpgsize(pgsize_to_tbllv(pgsize))
        } else {
            return 0;
        }
    } else {
        pgsize
    };

    if !page.is_null() && page_unmap(page) != 0 {
        panic_call(b"invalidate_one_page\0".as_ptr().cast::<i8>());
    }

    let error = memobj_invalidate_page((*range).memobj.cast::<Memobj>(), phys, memobj_pgsize);
    if error != 0 {
        if let Some(log) = log_fn {
            log(
                arg,
                page_table,
                ptep,
                *(ptep.cast::<CULong>()),
                pgaddr,
                pgshift,
                error,
            );
        }
    }

    error
}
