    // Root-approved defined notification; initialize complete caller-owned storage
    // before any reference or synchronous consumer. Never read the old pending.
    // SAFETY: info is aligned writable SigInfo storage kept live through do_kill.
    // Every byte, including union extent and padding, is initialized first. This
    // is the existing ptrace_report_signal_body_result writer/layout pattern.
    unsafe {
        let raw = info.cast::<u8>();
        let mut offset = 0;
        while offset < size_of::<SigInfo>() {
            raw.add(offset).write_volatile(0);
            offset += 1;
        }
        let info_ref = &mut *info;
        info_ref.si_signo = SIGCHLD;
        info_ref.si_code = CLD_TRAPPED;
        let sigchld = (&mut info_ref.sifields as *mut crate::abi::SigInfoFields)
            .cast::<crate::abi::SigInfoChild>();
        core::ptr::write_volatile(
            core::ptr::addr_of_mut!((*sigchld).si_pid), (*thread).tid,
        );
        core::ptr::write_volatile(
            core::ptr::addr_of_mut!((*sigchld).si_status),
            core::ptr::read_volatile(core::ptr::addr_of!((*thread).exit_status)),
        );
    }
