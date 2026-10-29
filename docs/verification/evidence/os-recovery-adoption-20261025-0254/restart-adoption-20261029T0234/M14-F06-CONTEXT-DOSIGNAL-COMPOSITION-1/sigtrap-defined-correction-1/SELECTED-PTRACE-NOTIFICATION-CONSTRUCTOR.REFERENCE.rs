    let mut info = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    let raw = info_ptr.cast::<u8>();
    let mut offset = 0;
    while offset < size_of::<SigInfo>() {
        raw.add(offset).write_volatile(0);
        offset += 1;
    }
    let info_ref = &mut *info_ptr;
    info_ref.si_signo = SIGCHLD;
    info_ref.si_code = CLD_TRAPPED;
    let sigchld = (&mut info_ref.sifields as *mut crate::abi::SigInfoFields).cast::<SigInfoChild>();
    write_volatile(core::ptr::addr_of_mut!((*sigchld).si_pid), tid);
    write_volatile(
        core::ptr::addr_of_mut!((*sigchld).si_status),
        read_volatile(field_ptr::<CInt>(
            thread_base,
            offsets.thread_exit_status_offset,
        )),
    );
