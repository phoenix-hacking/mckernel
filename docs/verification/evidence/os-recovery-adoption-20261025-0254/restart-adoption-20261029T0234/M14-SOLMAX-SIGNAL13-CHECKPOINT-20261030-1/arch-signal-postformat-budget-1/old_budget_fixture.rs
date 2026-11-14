// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private candidate: PID epoch and reserved diagnostic slots share one atomic word.
use core::sync::atomic::{AtomicU64, Ordering};

const F06_LOG_LIMIT: u32 = 64;
pub(super) static F06_SIGNAL_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

// Called once at the original do_signal entry reset point, even for signals that
// do not ultimately log. The high word contains the bit representation of pid.
pub(super) fn f06_log_observe_pid(state: &AtomicU64, pid: i32) {
    let pid_bits = (pid as u32 as u64) << 32;
    let mut seen = state.load(Ordering::Relaxed);
    loop {
        if seen & 0xffff_ffff_0000_0000 == pid_bits { return; }
        match state.compare_exchange_weak(seen, pid_bits, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return,
            Err(next) => seen = next,
        }
    }
}

// Claim against the CURRENT epoch at the original log site. A different PID can
// have entered since this invocation began; do not reset to this caller's PID.
// Claim precedes kprintf so simultaneous or reentrant calls cannot exceed 64.
pub(super) fn f06_log_claim(state: &AtomicU64) -> bool {
    let mut seen = state.load(Ordering::Relaxed);
    loop {
        let count = seen as u32;
        if count >= F06_LOG_LIMIT { return false; }
        match state.compare_exchange_weak(seen, seen + 1, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return true,
            Err(next) => seen = next,
        }
    }
}

