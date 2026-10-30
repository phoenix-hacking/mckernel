// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// SOURCE ONLY: deterministic test inputs; no test has been run.
use std::cell::Cell;
use std::sync::atomic::{AtomicU64, Ordering};
#[path = "postimage/kernel/rust/f06_signal_log_budget.rs"]
mod actual;
#[path = "old_budget_fixture.rs"]
mod old_preclaim;

// Independent sequential/reentrant model of the C PID/reset and logging order.
struct CReference { pid: Cell<i32>, count: Cell<i32>, emitted: Cell<u32> }
impl CReference {
    fn new(pid: i32, count: i32) -> Self {
        Self { pid: Cell::new(pid), count: Cell::new(count), emitted: Cell::new(0) }
    }
    fn enter(&self, pid: i32) {
        if self.pid.get() != pid { self.pid.set(pid); self.count.set(0); }
    }
    fn log(&self, callback: impl FnOnce()) -> bool {
        if self.count.get() >= 64 { return false; }
        self.emitted.set(self.emitted.get() + 1);
        callback();
        self.count.set(self.count.get().checked_add(1).expect("C int overflow outside test domain"));
        true
    }
}

fn packed(pid: i32, count: u32) -> u64 { ((pid as u32 as u64) << 32) | u64::from(count) }

// Mirror the actual two call sites: each raw-pointer-to-reference conversion is
// used for one atomic helper call; none is kept across the fake formatter.
unsafe fn call_formatter(state: *const AtomicU64, formatter: impl FnOnce()) -> bool {
    if !actual::f06_log_enabled(unsafe { &*state }) { return false; }
    formatter();
    actual::f06_log_complete(unsafe { &*state });
    true
}

#[test]
fn nested_formatter_at_63_logs_twice_then_leaves_65() {
    let reference = CReference::new(7, 63);
    assert!(reference.log(|| { assert!(reference.log(|| {})); }));
    assert_eq!((reference.emitted.get(), reference.count.get()), (2, 65));
    assert!(!reference.log(|| panic!("suppressed formatter ran")));

    let state = AtomicU64::new(packed(7, 63));
    let pointer = &state as *const AtomicU64;
    let emitted = Cell::new(0);
    assert!(unsafe { call_formatter(pointer, || {
        emitted.set(emitted.get() + 1);
        assert!(unsafe { call_formatter(pointer, || emitted.set(emitted.get() + 1)) });
    }) });
    assert_eq!(emitted.get(), reference.emitted.get());
    assert_eq!(state.load(Ordering::Relaxed), packed(reference.pid.get(), reference.count.get() as u32));
    assert!(!unsafe { call_formatter(pointer, || panic!("suppressed formatter ran")) });

    // Exact retained preclaim helper suppresses the nested message at 63.
    let old = AtomicU64::new(packed(7, 63));
    assert!(old_preclaim::f06_log_claim(&old));
    assert!(!old_preclaim::f06_log_claim(&old));
    assert_eq!(old.load(Ordering::Relaxed), packed(7, 64));
}

#[test]
fn callback_pid_change_then_nested_log_charges_current_epoch_twice() {
    let reference = CReference::new(17, 63);
    assert!(reference.log(|| {
        reference.enter(18);
        assert!(reference.log(|| {}));
    }));
    assert_eq!((reference.pid.get(), reference.count.get(), reference.emitted.get()), (18, 2, 2));

    let state = AtomicU64::new(packed(17, 63));
    let pointer = &state as *const AtomicU64;
    let emitted = Cell::new(0);
    assert!(unsafe { call_formatter(pointer, || {
        emitted.set(emitted.get() + 1);
        actual::f06_log_observe_pid(&state, 18);
        assert!(unsafe { call_formatter(pointer, || emitted.set(emitted.get() + 1)) });
    }) });
    assert_eq!(emitted.get(), reference.emitted.get());
    assert_eq!(state.load(Ordering::Relaxed), packed(18, 2));

    let old = AtomicU64::new(packed(17, 63));
    assert!(old_preclaim::f06_log_claim(&old));
    old_preclaim::f06_log_observe_pid(&old, 18);
    assert!(old_preclaim::f06_log_claim(&old));
    assert_eq!(old.load(Ordering::Relaxed), packed(18, 1));
}

#[test]
fn nonlogging_entry_reset_during_formatter_still_receives_outer_increment() {
    let reference = CReference::new(3, 10);
    assert!(reference.log(|| reference.enter(-1)));
    assert_eq!((reference.pid.get(), reference.count.get()), (-1, 1));
    let state = AtomicU64::new(packed(3, 10));
    let pointer = &state as *const AtomicU64;
    assert!(unsafe { call_formatter(pointer, || actual::f06_log_observe_pid(&state, -1)) });
    assert_eq!(state.load(Ordering::Relaxed), packed(-1, 1));
    let old = AtomicU64::new(packed(3, 10));
    assert!(old_preclaim::f06_log_claim(&old));
    old_preclaim::f06_log_observe_pid(&old, -1);
    assert_eq!(old.load(Ordering::Relaxed), packed(-1, 0));
}

#[test]
fn serial_limit_and_entry_reset_follow_original_c_reference() {
    let reference = CReference::new(-1, 0);
    let state = AtomicU64::new(packed(-1, 0));
    let pointer = &state as *const AtomicU64;
    for (pid, logs) in [(1, false), (1, true), (2, false), (1, true), (-1, true)] {
        reference.enter(pid);
        actual::f06_log_observe_pid(&state, pid);
        if logs { assert_eq!(reference.log(|| {}), unsafe { call_formatter(pointer, || {}) }); }
        assert_eq!(state.load(Ordering::Relaxed), packed(reference.pid.get(), reference.count.get() as u32));
    }
    for _ in 0..70 {
        assert_eq!(reference.log(|| {}), unsafe { call_formatter(pointer, || {}) });
    }
    assert_eq!(reference.count.get(), 64);
    assert_eq!(state.load(Ordering::Relaxed), packed(-1, 64));
    actual::f06_log_observe_pid(&state, -1);
    assert!(!actual::f06_log_enabled(&state));
    actual::f06_log_observe_pid(&state, 99);
    assert!(actual::f06_log_enabled(&state));
}

#[test]
fn synthetic_low_word_wrap_never_carries_into_pid() {
    // This synthetic state is outside original C's defined signed-count domain.
    let state = AtomicU64::new(packed(42, u32::MAX));
    actual::f06_log_complete(&state);
    assert_eq!(state.load(Ordering::Relaxed), packed(42, 0));
}
