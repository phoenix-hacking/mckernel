#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_init_body_result(
    event: *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    ref_cpu_cycles_config: CULong,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if event.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(atomic_set) = atomic_set_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let attr_base = attr.cast::<u8>();
    let mut i = 0;
    while i < event_size {
        write_volatile(event_base.add(i), 0);
        i += 1;
    }

    i = 0;
    let attr_dst = event_base.add(event_attr_offset);
    while i < attr_size {
        write_volatile(attr_dst.add(i), read_volatile(attr_base.add(i)));
        i += 1;
    }

    let group_entry = field_ptr::<AbiListHead>(event_base, group_entry_offset);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).next), group_entry);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).prev), group_entry);
    let sibling_list = field_ptr::<AbiListHead>(event_base, sibling_list_offset);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).next), sibling_list);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).prev), sibling_list);

    write_volatile(
        field_ptr::<CULong>(event_base, sample_freq_offset),
        attr_sample_freq,
    );
    write_volatile(field_ptr::<CInt>(event_base, nr_siblings_offset), 0);
    atomic_set(event_base.add(count_offset).cast::<c_void>(), 0);
    write_volatile(field_ptr::<CULong>(event_base, child_count_total_offset), 0);
    write_volatile(
        field_ptr::<*mut c_void>(event_base, parent_offset),
        core::ptr::null_mut(),
    );

    let sample_period = if attr_freq != 0 && attr_sample_freq != 0 {
        1
    } else {
        attr_sample_period
    };
    write_volatile(
        field_ptr::<CULong>(event_base, hw_sample_period_offset),
        sample_period,
    );
    write_volatile(
        field_ptr::<CULong>(event_base, hw_last_period_offset),
        sample_period,
    );
    atomic_set(
        event_base.add(hw_period_left_offset).cast::<c_void>(),
        sample_period as CLong,
    );

    if attr_type == hardware_type && attr_config == ref_cpu_cycles_config {
        write_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset), 1);
        return 1;
    }

    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_map_body_result(
    event_out: *mut *mut c_void,
    event: *mut c_void,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(validate_event) = validate_event_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_id) = extra_reg_id_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_msr) = extra_reg_msr_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_idx) = extra_reg_idx_fn else {
        return -EINVAL as CLong;
    };
    let Some(hw_event_init) = hw_event_init_fn else {
        return -EINVAL as CLong;
    };

    let mut extra_config = 0;
    let val = if attr_type == hardware_type {
        let Some(hw_event_map) = hw_event_map_fn else {
            return -EINVAL as CLong;
        };
        hw_event_map(attr_config)
    } else if attr_type == hw_cache_type {
        let Some(hw_cache_event_map) = hw_cache_event_map_fn else {
            return -EINVAL as CLong;
        };
        let Some(hw_cache_extra_reg_map) = hw_cache_extra_reg_map_fn else {
            return -EINVAL as CLong;
        };
        extra_config = hw_cache_extra_reg_map(attr_config);
        hw_cache_event_map(attr_config)
    } else if attr_type == raw_type {
        let Some(raw_event_map) = raw_event_map_fn else {
            return -EINVAL as CLong;
        };
        raw_event_map(attr_config)
    } else {
        return -EINVAL as CLong;
    };

    if validate_event(val) == 0 {
        return -ENOENT as CLong;
    }

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CULong>(event_base, hw_config_offset), val);
    write_volatile(
        field_ptr::<CULong>(event_base, hw_config_ext_offset),
        extra_config,
    );

    let ereg_id = extra_reg_id(val, extra_config);
    if ereg_id >= 0 {
        write_volatile(
            field_ptr::<CULong>(event_base, extra_reg_config_offset),
            extra_config,
        );
        write_volatile(
            field_ptr::<u32>(event_base, extra_reg_reg_offset),
            extra_reg_msr(ereg_id),
        );
        write_volatile(
            field_ptr::<CInt>(event_base, extra_reg_idx_offset),
            extra_reg_idx(ereg_id),
        );
    }

    let ret = hw_event_init(event);
    if ret == 0 {
        write_volatile(event_out, event);
    }
    ret as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_body_result(
    event_out: *mut *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    alloc_flags: CULong,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    ref_cpu_cycles_config: CULong,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(alloc) = alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(free) = free_fn else {
        return -EINVAL as CLong;
    };

    let event = alloc(event_size, alloc_flags);
    if event.is_null() {
        return -ENOMEM as CLong;
    }

    let init = perf_event_alloc_init_body_result(
        event,
        attr,
        event_size,
        attr_size,
        event_attr_offset,
        group_entry_offset,
        sibling_list_offset,
        sample_freq_offset,
        nr_siblings_offset,
        count_offset,
        child_count_total_offset,
        parent_offset,
        hw_sample_period_offset,
        hw_last_period_offset,
        hw_period_left_offset,
        use_invariant_tsc_offset,
        attr_type,
        attr_config,
        attr_freq,
        attr_sample_freq,
        attr_sample_period,
        hardware_type,
        ref_cpu_cycles_config,
        atomic_set_fn,
    );
    if init < 0 {
        free(event);
        return init;
    }
    if init > 0 {
        write_volatile(event_out, event);
        return 0;
    }

    let ret = perf_event_alloc_map_body_result(
        event_out,
        event,
        hw_config_offset,
        hw_config_ext_offset,
        extra_reg_config_offset,
        extra_reg_reg_offset,
        extra_reg_idx_offset,
        attr_type,
        attr_config,
        hardware_type,
        hw_cache_type,
        raw_type,
        hw_event_map_fn,
        hw_cache_event_map_fn,
        hw_cache_extra_reg_map_fn,
        raw_event_map_fn,
        validate_event_fn,
        extra_reg_id_fn,
        extra_reg_msr_fn,
        extra_reg_idx_fn,
        hw_event_init_fn,
    );
    if ret != 0 {
        free(event);
    }
    ret
}
