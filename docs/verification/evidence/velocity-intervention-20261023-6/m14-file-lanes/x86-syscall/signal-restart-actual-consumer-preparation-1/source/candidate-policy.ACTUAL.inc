// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete live signal restart policy; preserve the legacy/native config
// distinction at the existing C call sites through an explicit literal flag.
const F06_SIGNAL_RESTART_NEVER: [CInt; 16] = [
    34, // __NR_pause,
    130, // __NR_rt_sigsuspend,
    128, // __NR_rt_sigtimedwait,
    SYS_EPOLL_WAIT as CInt, // __NR_epoll_wait,
    281, // __NR_epoll_pwait,
    7, // __NR_poll,
    SYS_PPOLL, // __NR_ppoll,
    23, // __NR_select,
    SYS_PSELECT6, // __NR_pselect6,
    70, // __NR_msgrcv,
    69, // __NR_msgsnd,
    65, // __NR_semop,
    220, // __NR_semtimedop,
    230, // __NR_clock_nanosleep,
    SYS_NANOSLEEP, // __NR_nanosleep,
    208, // __NR_io_getevents
];

/// Pure policy only: no signal ownership, user-register or handler-state changes.
/// `rc` is the original unsigned-long return bits, not a narrowed signed errno.
/// The native flag is selected by the same MCKERNEL_NATIVE_SIGNAL_STACK C macro
/// as the original early-return guard; callers evaluate each argument once.
#[no_mangle]
pub extern "C" fn arch_signal_restart_result(
    num: CInt, rc: CULong, sig: CInt, restart: CInt, native_signal_stack: CInt,
) -> CInt {
    // A pending native handler observes an already-restored user continuation.
    if native_signal_stack != 0 && num == 15 { // __NR_rt_sigreturn
        return 0;
    }
    if sig == SIGKILL || sig == SIGSTOP {
        return 0;
    }
    if num < 0 || rc != (-(EINTR as CLong)) as CULong {
        return 0;
    }
    // Preserve this shortcut before the non-restarting syscall set.
    if sig == SIGCHLD {
        return 1;
    }
    if F06_SIGNAL_RESTART_NEVER.contains(&num) {
        return 0;
    }
    (restart != 0) as CInt
}
