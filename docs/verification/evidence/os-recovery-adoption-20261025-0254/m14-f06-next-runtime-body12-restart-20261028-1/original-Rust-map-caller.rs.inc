unsafe fn arch_map_vdso_with_pages(
    vm: *mut ProcessVm,
    page_table: *mut c_void,
    vdso: *const ArchVdso,
    container_size: SizeT,
    vdso_offset: isize,
    add_range_fn: Option<ArchVdsoAddRangeFn>,
    set_range_fn: Option<ArchVdsoSetRangeFn>,
    log_fn: Option<ArchVdsoMapLogFn>,
    extra_pages: &[(isize, CULong)],
) -> CInt {
    if container_size == 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_MAP_LOG_NOT_AVAILABLE, 0, vm, 0, 0, 0, 0, 0);
        }
        return 0;
    }
    if vm.is_null() || vdso.is_null() {
        return -EFAULT;
    }

    let Some(add_range) = add_range_fn else {
        return -EFAULT;
    };
    let Some(set_range) = set_range_fn else {
        return -EFAULT;
    };
    let vdso_ref = &*vdso;
    let container = (*vm).region.map_end;
    // Additional pages are explicitly inside the native pre-text container.
    // Validate every address before changing the VM or calling its callbacks.
    if !extra_pages.is_empty() {
        if !(1..=2).contains(&vdso_ref.vdso_npages)
            || vdso_offset <= 0
            || (vdso_offset as usize)
                .checked_add(vdso_ref.vdso_npages as usize * PAGE_SIZE as usize)
                != Some(container_size)
            || container.checked_add(container_size as u64).is_none()
        {
            return -EINVAL;
        }
        for (index, &(offset, physical)) in extra_pages.iter().enumerate() {
            if physical == 0 {
                continue;
            }
            if offset >= 0
                || offset < -vdso_offset
                || offset % PAGE_SIZE as isize != 0
                || physical % PAGE_SIZE != 0
                || physical > (256_u64 << 30) - PAGE_SIZE
                || offset == vdso_ref.vvar_virt as isize
                || offset == vdso_ref.hpet_virt as isize
                || offset == vdso_ref.pvti_virt as isize
                || extra_pages[..index]
                    .iter()
                    .any(|&(old, pa)| pa != 0 && old == offset)
            {
                return -EINVAL;
            }
        }
    }
    (*vm).region.map_end = (*vm).region.map_end.wrapping_add(container_size as CULong);

    let vdso_addr = arch_vdso_addr_add(container, vdso_offset);
    let vdso_page_bytes = (vdso_ref.vdso_npages as CULong).wrapping_mul(PAGE_SIZE);
    let vdso_end = vdso_addr.wrapping_add(vdso_page_bytes);
    let mut vrflags = VR_REMOTE | VR_PROT_READ | VR_PROT_EXEC;
    vrflags |= arch_vdso_maxprot(vrflags);
    let mut range: *mut VmRange = null_mut();

    let mut error = add_range(vm, vdso_addr, vdso_end, vrflags, &mut range);
    if error != 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED, error, vm, 0, 0, 0, 0, 0);
        }
        return error;
    }
    (*vm).vdso_addr = vdso_addr as *mut c_void;
    if let Some(log) = log_fn {
        log(
            ARCH_VDSO_MAP_LOG_MAPPED,
            0,
            vm,
            container,
            vdso_addr,
            vdso_end,
            container_size as CULong,
            vdso_ref.vdso_npages,
        );
    }
