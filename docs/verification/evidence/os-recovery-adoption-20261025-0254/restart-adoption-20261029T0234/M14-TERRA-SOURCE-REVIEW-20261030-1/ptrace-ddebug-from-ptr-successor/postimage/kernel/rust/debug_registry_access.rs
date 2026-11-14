use super::Ddebug;

#[inline(always)]
unsafe fn ddebug_word(dbg: *const Ddebug) -> u32 {
    #[cfg(all(f03_leaf_callbacks_candidate, f03_ptrace_wakeup_log_candidate, target_arch = "x86_64"))]
    if let Some(value) = crate::syscall_policy::syscall_ptrace_wakeup_logger::special_load(dbg) {
        return value;
    }
    (*dbg).line_flags
}

#[inline(always)]
pub(super) fn ddebug_line(dbg: *const Ddebug) -> i32 {
    unsafe { (ddebug_word(dbg) & 0x00ff_ffff) as i32 }
}

#[inline(always)]
pub(super) unsafe fn ddebug_flags(dbg: *const Ddebug) -> u32 {
    ddebug_word(dbg) >> 24
}

#[inline(always)]
pub(super) unsafe fn set_ddebug_flags(dbg: *mut Ddebug, flags: u32) {
    #[cfg(all(f03_leaf_callbacks_candidate, f03_ptrace_wakeup_log_candidate, target_arch = "x86_64"))]
    if crate::syscall_policy::syscall_ptrace_wakeup_logger::special_set_flags(dbg, flags) {
        return;
    }
    (*dbg).line_flags = ((*dbg).line_flags & 0x00ff_ffff) | (flags << 24);
}
