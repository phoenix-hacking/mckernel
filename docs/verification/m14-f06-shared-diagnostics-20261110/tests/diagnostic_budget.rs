// Pure diagnostic-sharing regression only. No signal/frame/GS/XSAVE/provider
// kernel function, fake ACK, process reset/release or native operation.
type CInt = i32;
use core::sync::atomic::{AtomicU64, Ordering};
static F06_SIGNAL_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

fn f06_signal_log_begin(pid: CInt) {
    let pid_bits = (pid as u32 as u64) << 32;
    let mut observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    while observed & 0xffff_ffff_0000_0000 != pid_bits {
        match F06_SIGNAL_LOG_STATE.compare_exchange_weak(
            observed, pid_bits, Ordering::Relaxed, Ordering::Relaxed,
        ) {
            Ok(_) => return,
            Err(actual) => observed = actual,
        }
    }
}

fn f06_signal_log_allowed() -> bool {
    (F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed) as u32 as CInt) < 64
}

fn f06_signal_log_after_print() {
    let mut observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    loop {
        let next = (observed & 0xffff_ffff_0000_0000)
            | u64::from((observed as u32).wrapping_add(1));
        match F06_SIGNAL_LOG_STATE.compare_exchange_weak(
            observed, next, Ordering::Relaxed, Ordering::Relaxed,
        ) {
            Ok(_) => return,
            Err(actual) => observed = actual,
        }
    }
}


fn main() {
    f06_signal_log_begin(41);
    for _ in 0..64 { assert!(f06_signal_log_allowed()); f06_signal_log_after_print(); }
    assert!(!f06_signal_log_allowed());
    f06_signal_log_begin(41);
    assert!(!f06_signal_log_allowed());
    f06_signal_log_begin(42);
    f06_signal_log_begin(41);
    assert!(f06_signal_log_allowed());
    f06_signal_log_begin(43);
    assert!(f06_signal_log_allowed());
    f06_signal_log_begin(44);
    f06_signal_log_after_print();
    let observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    assert_eq!((observed >> 32) as u32, 44);
    assert_eq!(observed as u32, 1);
    f06_signal_log_begin(45);
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(3));
    let mut handles = Vec::new();
    for _ in 0..2 {
        let gate = barrier.clone();
        handles.push(std::thread::spawn(move || {
            gate.wait();
            for _ in 0..1000 { f06_signal_log_after_print(); }
        }));
    }
    barrier.wait();
    for handle in handles { handle.join().expect("owned budget worker panicked"); }
    let observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    assert_eq!((observed >> 32) as u32, 45);
    assert_eq!(observed as u32, 2000);
    f06_signal_log_begin(-1);
    assert!(f06_signal_log_allowed());
    println!("{{\"status\":\"PASS\",\"scope\":\"actual-f06-diagnostic-atomics-only\",\"entry_reset\":true,\"post_formatter_reread\":true,\"joined_workers\":2,\"increments\":2000,\"kernel_runtime\":false}}");
}
