// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: direct-target permission and early-return ownership orchestration only.
unsafe extern "C" {
    #[link_name = "interrupt_syscall"]
    fn f06_direct_target_interrupt_syscall(thread: *mut Thread, sig: CInt);
}

/// Return1 means the original do_kill caller must return `*return_value`.
/// Return0 continues to the caller's EXISTING pending writer lock/enqueue/wakeup.
/// caller_proc and target_proc are the original snapshots, borrowed at entry.
/// The caller already holds exactly one target-thread reference, when nonnull.
/// This body consumes it only on an original terminal branch; the continuing
/// path leaves it and IRQ-disabled state entirely with the C caller.
#[no_mangle]
pub unsafe extern "C" fn arch_do_kill_direct_target_gate_result(
    caller_proc: *mut Process, target_proc: *mut Process,
    target: *mut Thread, sig: CInt, irqstate: CULong,
    return_value: *mut CULong,
) -> CInt {
    // Same SIGCONT exemption and real/saved UID checks. No target EUID check,
    // session check or new null-pointer policy is added to this existing gate.
    if sig != SIGCONT && !caller_proc.is_null()
        && (*caller_proc).euid != 0
        && (*caller_proc).ruid != (*target_proc).ruid
        && (*caller_proc).euid != (*target_proc).ruid
        && (*caller_proc).ruid != (*target_proc).suid
        && (*caller_proc).euid != (*target_proc).suid
    {
        if !target.is_null() { crate::process_helpers::release_thread(target); }
        cpu_restore_interrupt(irqstate);
        *return_value = (-EPERM as CLong) as CULong;
        return 1;
    }
    if sig == 0 || target.is_null() || (*target).status == PS_EXITED {
        if !target.is_null() { crate::process_helpers::release_thread(target); }
        cpu_restore_interrupt(irqstate);
        *return_value = 0;
        return 1;
    }
    // The selected C branch releases the target and returns WITHOUT an explicit
    // cpu_restore_interrupt, including nohost. Preserve that baseline exactly;
    // do not infer or invent IRQ restoration in interrupt_syscall forwarding.
    if (*target).uti_state == 2 { // actual process.h UTI_STATE_RUNNING_IN_LINUX
        if (*(*target).proc).nohost == 0 {
            f06_direct_target_interrupt_syscall(target, sig);
        }
        crate::process_helpers::release_thread(target);
        *return_value = 0;
        return 1;
    }
    0
}
