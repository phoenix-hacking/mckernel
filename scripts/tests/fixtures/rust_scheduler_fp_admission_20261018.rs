//! Source-bound admission fixture. Callbacks model IRQ entry and FPU-save failure;
//! no privileged instruction or guest acceptance is claimed.
use std::alloc::{alloc_zeroed, Layout};
use std::ffi::{c_void, CStr};
use std::ptr::null_mut;
// REAL_SCHED_ABI
use abi::{CpuLocalVar, Thread};
extern "C" {
    fn selected_admit() -> u64;
    fn reference_admit() -> u64;
}
static mut CPU: *mut CpuLocalVar = null_mut();
static mut OWNER: *mut Thread = null_mut();
static mut IRQ_ENABLED: bool = true;
static mut ENTRY: u64 = 0;
static mut SAVES: usize = 0;
static mut PREPARES: usize = 0;
static mut FAILURE: bool = false;
static mut EXPECT_SAVE: bool = false;
static mut ADMITTED_CURRENT: *mut Thread = null_mut();
static mut ADMITTED_NO_PREEMPT: i32 = 0;
static mut ADMITTED_STATUS: i32 = 0;
static mut EVENTS: [u8; 8] = [0; 8];
static mut EVENT_COUNT: usize = 0;
unsafe fn event(value: u8) {
    let count = EVENT_COUNT;
    EVENTS[count] = value;
    EVENT_COUNT = count + 1;
}
#[no_mangle]
unsafe extern "C" fn process_sched_irq_save_bridge() -> u64 {
    assert_eq!(SAVES, 0);
    assert_eq!(PREPARES, 0);
    event(1);
    IRQ_ENABLED = false;
    // Poisoned fields become their actual values only at IRQ exclusion. Any
    // prematurely sampled no_preempt/current/status changes the required save.
    (*CPU).current = ADMITTED_CURRENT;
    (*CPU).no_preempt.counter = ADMITTED_NO_PREEMPT;
    (*OWNER).status = ADMITTED_STATUS;
    ENTRY
}
#[no_mangle]
unsafe extern "C" fn cpu_disable_interrupt_save() -> u64 {
    process_sched_irq_save_bridge()
}
#[no_mangle]
unsafe extern "C" fn ihk_mc_get_processor_id() -> i32 {
    assert!(!IRQ_ENABLED);
    3
}
#[no_mangle]
unsafe extern "C" fn process_sched_cpu_local_bridge(cpu: i32) -> usize {
    assert_eq!(cpu, 3);
    assert!(!IRQ_ENABLED);
    CPU as usize
}
#[no_mangle]
unsafe extern "C" fn get_this_cpu_local_var() -> *mut CpuLocalVar {
    assert!(!IRQ_ENABLED);
    CPU
}
#[no_mangle]
unsafe extern "C" fn save_fp_regs(thread: *mut c_void) -> i32 {
    assert!(!IRQ_ENABLED);
    assert_eq!(thread, OWNER.cast());
    assert_eq!(PREPARES, 0);
    assert_eq!((*CPU).runq_len, 23);
    assert_eq!((*CPU).flags, 0x1234);
    SAVES += 1;
    event(2);
    if FAILURE { -12 } else { 0 }
}
// Export the panic ABI under its actual symbol without shadowing Rust's macro.
#[export_name = "panic"]
unsafe extern "C" fn admission_panic(message: *const i8) -> ! {
    assert!(!IRQ_ENABLED);
    assert_eq!(CStr::from_ptr(message).to_bytes(), b"schedule: failed to save floating point state");
    assert_eq!(SAVES, 1);
    assert_eq!(PREPARES, 0);
    assert_eq!((*CPU).runq_len, 23);
    assert_eq!((*CPU).flags, 0x1234);
    assert_eq!(&EVENTS[..EVENT_COUNT], &[1, 2]);
    println!("PASS fail-stop: IRQ held, save failed, no prepare or queue mutation");
    std::process::exit(77)
}
#[no_mangle]
unsafe extern "C" fn observe_prepare() {
    assert!(!IRQ_ENABLED);
    assert_eq!(SAVES, usize::from(EXPECT_SAVE));
    assert_eq!((*CPU).runq_len, 23);
    assert_eq!((*CPU).flags, 0x1234);
    PREPARES += 1;
    event(3);
}
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let variant = &args[1];
    let case: u32 = args[2].parse().unwrap();
    let enabled = args[3] == "1";
    unsafe {
        CPU = alloc_zeroed(Layout::new::<CpuLocalVar>()).cast();
        OWNER = alloc_zeroed(Layout::new::<Thread>()).cast();
        assert!(!CPU.is_null() && !OWNER.is_null());
        assert_eq!(std::mem::offset_of!(Thread, status), 4184);
        assert_eq!(std::mem::offset_of!(CpuLocalVar, idle), 64);
        assert_eq!(std::mem::offset_of!(CpuLocalVar, current), 7848);
        assert_eq!(std::mem::offset_of!(CpuLocalVar, no_preempt), 7976);
        (*CPU).current = OWNER;
        (*CPU).runq_len = 23;
        (*CPU).flags = 0x1234;
        (*OWNER).status = 1;
        match case {
            0 => {}, // ordinary owner, successful save
            1 => (*CPU).no_preempt.counter = 1,
            2 => (*CPU).no_preempt.counter = -1,
            3 => (*CPU).current = null_mut(),
            4 => (*CPU).current = &raw mut (*CPU).idle,
            5 => (*OWNER).status = 0x10, // PS_EXITED supplied by extracted caller
            6 => FAILURE = true,
            7 => { (*CPU).no_preempt.counter = 1; FAILURE = true; },
            _ => unreachable!(),
        }
        EXPECT_SAVE = matches!(case, 0 | 6);
        ADMITTED_CURRENT = (*CPU).current;
        ADMITTED_NO_PREEMPT = (*CPU).no_preempt.counter;
        ADMITTED_STATUS = (*OWNER).status;
        (*CPU).current = null_mut();
        (*CPU).no_preempt.counter = if ADMITTED_NO_PREEMPT == 0 { 1 } else { 0 };
        (*OWNER).status = 0x10;
        ENTRY = if enabled { 0x246 } else { 0x46 };
        IRQ_ENABLED = enabled;
        let result = if variant == "rust" { selected_admit() } else { reference_admit() };
        assert_eq!(result, ENTRY);
        assert!(!IRQ_ENABLED);
        assert_eq!(PREPARES, 1);
        assert_eq!(&EVENTS[..EVENT_COUNT], if EXPECT_SAVE { &[1, 2, 3][..] } else { &[1, 3][..] });
        println!("PASS admission case={case} entry={result:#x} save={} prepare={}", SAVES, PREPARES);
    }
}
