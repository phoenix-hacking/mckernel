// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Shared diagnostic PID and post-formatter count occupy one atomic word.
use core::sync::atomic::{AtomicU64, Ordering};

const F06_LOG_LIMIT: i32 = 64;
const F06_PID_MASK: u64 = 0xffff_ffff_0000_0000;
pub(super) static F06_SIGNAL_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

// Original entry observes every PID, even when its signal will not log.
pub(super) fn f06_log_observe_pid(state: &AtomicU64, pid: i32) {
    let pid_bits = (pid as u32 as u64) << 32;
    let mut seen = state.load(Ordering::Relaxed);
    loop {
        if seen & F06_PID_MASK == pid_bits { return; }
        match state.compare_exchange_weak(seen, pid_bits, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return,
            Err(next) => seen = next,
        }
    }
}

// Original C reads the signed int counter before the synchronous formatter.
// This is a check, not a reservation, and the borrow ends before the callback.
pub(super) fn f06_log_enabled(state: &AtomicU64) -> bool {
    (state.load(Ordering::Relaxed) as u32 as i32) < F06_LOG_LIMIT
}

// After the formatter returns, increment the then-current count while keeping
// its PID bits. A callback may have reset or incremented the budget meanwhile.
// The C signed-overflow domain remains outside the defined equivalence claim.
pub(super) fn f06_log_complete(state: &AtomicU64) {
    let mut seen = state.load(Ordering::Relaxed);
    loop {
        let next_count = (seen as u32).wrapping_add(1);
        let next = (seen & F06_PID_MASK) | u64::from(next_count);
        match state.compare_exchange_weak(seen, next, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return,
            Err(next_seen) => seen = next_seen,
        }
    }
}
