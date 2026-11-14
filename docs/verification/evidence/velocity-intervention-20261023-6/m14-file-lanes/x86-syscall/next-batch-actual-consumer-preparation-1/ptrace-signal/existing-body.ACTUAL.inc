#[no_mangle]
pub unsafe extern "C" fn ptrace_report_signal_body_result(
    thread: *mut c_void,
    sig: CInt,
    current_thread: *mut c_void,
    offsets: *const PtraceReportSignalOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<PtraceSignalLockFn>,
    unlock_fn: Option<PtraceSignalLockFn>,
    save_debugreg_fn: Option<PtraceSaveDebugregFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    schedule_fn: Option<PtraceVoidFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CInt {
    if thread.is_null() || current_thread.is_null() || offsets.is_null() || lock_node.is_null() {
        return -EINVAL;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(save_debugreg) = save_debugreg_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };
    let Some(do_kill) = do_kill_fn else {
        return -EINVAL;
    };
    let Some(schedule) = schedule_fn else {
        return -EINVAL;
    };

    let offsets = &*offsets;
    let thread_base = thread.cast::<u8>();
    let proc = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_proc_offset,
    ));
    if proc.is_null() {
        return -EINVAL;
    }
    let proc_base = proc.cast::<u8>();
    let tid = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_tid_offset));
    let proc_pid = read_volatile(field_ptr::<CInt>(proc_base, offsets.proc_pid_offset));
    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_ENTER, tid, proc_pid);
    }

    let parent_pid;
    let parent_waitq;
    let wake_parent;
    let update_lock = field_ptr::<c_void>(proc_base, offsets.proc_update_lock_offset);
    lock(update_lock, lock_node);
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset));
    if (ptrace & PT_TRACED) == 0 {
        unlock(update_lock, lock_node);
        return 0;
    }

    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_exit_status_offset),
        sig,
    );
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_status_offset),
        PS_TRACED,
    );
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset),
        ptrace & !PT_TRACE_SYSCALL,
    );
    let debugreg = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_ptrace_debugreg_offset,
    ));
    save_debugreg(debugreg);

    let signal_flags_ptr = field_ptr::<CInt>(thread_base, offsets.thread_signal_flags_offset);
    let mut signal_flags = read_volatile(signal_flags_ptr);
    if sig == SIGSTOP || sig == SIGTSTP || sig == SIGTTIN || sig == SIGTTOU {
        signal_flags |= SIGNAL_STOP_STOPPED;
    } else {
        signal_flags &= !SIGNAL_STOP_STOPPED;
    }
    write_volatile(signal_flags_ptr, signal_flags);

    let main_thread = read_volatile(field_ptr::<*mut c_void>(
        proc_base,
        offsets.proc_main_thread_offset,
    ));
    if thread == main_thread {
        let parent = read_volatile(field_ptr::<*mut c_void>(
            proc_base,
            offsets.proc_parent_offset,
        ));
        if parent.is_null() {
            unlock(update_lock, lock_node);
            return -EINVAL;
        }
        let parent_base = parent.cast::<u8>();
        write_volatile(
            field_ptr::<CInt>(proc_base, offsets.proc_status_offset),
            PS_TRACED,
        );
        wake_parent = true;
        parent_pid = read_volatile(field_ptr::<CInt>(parent_base, offsets.proc_pid_offset));
        parent_waitq = field_ptr::<c_void>(parent_base, offsets.proc_waitpid_q_offset);
    } else {
        let report_proc = read_volatile(field_ptr::<*mut c_void>(
            thread_base,
            offsets.thread_report_proc_offset,
        ));
        if report_proc.is_null() {
            unlock(update_lock, lock_node);
            return -EINVAL;
        }
        let report_base = report_proc.cast::<u8>();
        parent_pid = read_volatile(field_ptr::<CInt>(report_base, offsets.proc_pid_offset));
        parent_waitq = core::ptr::null_mut::<c_void>();
        wake_parent = false;
        wake(field_ptr::<c_void>(
            report_base,
            offsets.proc_waitpid_q_offset,
        ));
    }
    unlock(update_lock, lock_node);

    if wake_parent {
        wake(parent_waitq);
    }

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
    do_kill(
        current_thread,
        parent_pid,
        -1,
        SIGCHLD,
        info_ref as *const SigInfo,
        0,
    );

    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_SLEEPING, tid, sig);
    }
    schedule();
    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_WAKE, tid, sig);
    }
    0
}
