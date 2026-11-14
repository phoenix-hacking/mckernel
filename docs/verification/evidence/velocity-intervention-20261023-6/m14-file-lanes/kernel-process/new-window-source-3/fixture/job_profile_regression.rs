// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual original/fixed function and production ABI types; controlled host effects.
use std::alloc::{alloc_zeroed, dealloc, Layout};
use std::cell::RefCell;
use std::ffi::{c_char, c_void, CStr};
use std::mem::size_of;
use std::ptr::null_mut;

#[path = "../source/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt, CULong, McsLockNode, Process, ProfileEvent};

include!("actual_constants.inc");
include!("actual_storage.inc");
include!("actual_helpers.inc");

#[derive(Default)]
struct Effects {
    held: bool,
    irq: u64,
    node: usize,
    fail_alloc: bool,
    alloc_calls: usize,
    trace: Vec<&'static str>,
    allocations: Vec<usize>,
    printed: Vec<(i32, u64, u64, u32)>,
}
thread_local! { static EFFECTS: RefCell<Effects> = RefCell::new(Effects::default()); }
const ORIGINAL_IRQ: u64 = 0x202;

unsafe fn mcs_lock_lock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    assert_eq!(lock, &raw mut job_profile_lock);
    EFFECTS.with(|slot| {
        let mut state = slot.borrow_mut();
        assert!(!state.held, "next operation encountered the prior retained lock");
        assert_eq!(state.irq, ORIGINAL_IRQ);
        unsafe { (*node).irqsave = state.irq };
        state.irq = 0;
        state.held = true;
        state.node = node as usize;
        state.trace.push("lock-save-irq");
    });
}

unsafe fn mcs_lock_unlock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    assert_eq!(lock, &raw mut job_profile_lock);
    EFFECTS.with(|slot| {
        let mut state = slot.borrow_mut();
        assert!(state.held);
        assert_eq!(state.node, node as usize, "unlock must use the same stack node");
        assert_eq!(state.irq, 0);
        assert_eq!(unsafe { (*node).irqsave }, ORIGINAL_IRQ);
        state.irq = unsafe { (*node).irqsave };
        state.held = false;
        state.node = 0;
        state.trace.push("unlock-restore-irq");
    });
}

unsafe fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void {
    assert_eq!(size as usize, size_of::<ProfileEvent>() * PROFILE_EVENT_MAX);
    assert_eq!(flags, IHK_MC_AP_NOWAIT);
    assert_eq!(unsafe { CStr::from_ptr(file) }.to_bytes_with_nul(), PROFILE_FILE);
    assert!(line > 0);
    EFFECTS.with(|slot| {
        let mut state = slot.borrow_mut();
        assert!(state.held);
        state.alloc_calls += 1;
        if state.fail_alloc {
            state.trace.push("allocation-failed");
            null_mut()
        } else {
            state.trace.push("allocation-succeeded");
            let pointer = unsafe { alloc_zeroed(Layout::array::<ProfileEvent>(PROFILE_EVENT_MAX).unwrap()) };
            assert!(!pointer.is_null());
            unsafe { std::ptr::write_bytes(pointer, 0xcd, size as usize) };
            state.allocations.push(pointer as usize);
            pointer.cast()
        }
    })
}

unsafe fn kprintf(format: *const c_char, name: *const u8) -> CInt {
    assert_eq!(unsafe { CStr::from_ptr(format) }.to_bytes_with_nul(), JOB_ALLOC_ERR_FMT);
    assert_eq!(unsafe { CStr::from_ptr(name.cast()) }.to_bytes_with_nul(), PROFILE_ACC_JOB_NAME);
    EFFECTS.with(|slot| {
        let mut state = slot.borrow_mut();
        assert!(state.held, "original error report remains inside the acquisition");
        state.trace.push("original-allocation-error-report");
    });
    0
}

unsafe fn print_profile_events(
    events: *mut ProfileEvent,
    format: *const c_char,
    label: *const u8,
    count: CInt,
    elapsed: CULong,
) {
    assert_eq!(unsafe { CStr::from_ptr(format) }.to_bytes_with_nul(), JOB_HDR_FMT);
    assert_eq!(unsafe { CStr::from_ptr(label.cast()) }.to_bytes_with_nul(), JOB_LABEL);
    EFFECTS.with(|slot| {
        let mut state = slot.borrow_mut();
        assert!(state.held);
        state.trace.push("print-job-profile");
        state.printed.push((count, elapsed, unsafe { (*events).tsc }, unsafe { (*events).cnt }));
    });
}

include!("original_job_profile.TEST-NAME-ONLY.inc");
include!("fixed_job_profile.ACTUAL-RUST.inc");

struct FixtureProcess {
    proc: *mut Process,
    events: *mut ProfileEvent,
}
impl FixtureProcess {
    fn new(count: i32, elapsed: u64, tsc: u64, events: u32) -> Self {
        // No whole Process value/reference is formed: the exact ABI fields used
        // by the actual body are initialized in aligned, owned zeroed storage.
        unsafe {
            let proc = alloc_zeroed(Layout::new::<Process>()).cast::<Process>();
            let array = alloc_zeroed(Layout::array::<ProfileEvent>(PROFILE_EVENT_MAX).unwrap())
                .cast::<ProfileEvent>();
            assert!(!proc.is_null() && !array.is_null());
            (*proc).nr_processes = count;
            (*proc).profile_elapsed_ts = elapsed;
            (*proc).profile_events = array.cast();
            (*array).tsc = tsc;
            (*array).cnt = events;
            Self { proc, events: array }
        }
    }
}
impl Drop for FixtureProcess {
    fn drop(&mut self) {
        unsafe {
            dealloc(self.events.cast(), Layout::array::<ProfileEvent>(PROFILE_EVENT_MAX).unwrap());
            dealloc(self.proc.cast(), Layout::new::<Process>());
        }
    }
}

unsafe fn reset() {
    EFFECTS.with(|slot| {
        for pointer in slot.borrow_mut().allocations.drain(..) {
            unsafe { dealloc(pointer as *mut u8, Layout::array::<ProfileEvent>(PROFILE_EVENT_MAX).unwrap()) };
        }
        *slot.borrow_mut() = Effects { irq: ORIGINAL_IRQ, ..Effects::default() };
    });
    unsafe {
        job_profile_events = null_mut();
        job_nr_processes = -1;
        job_nr_processes_left = -1;
        job_elapsed_ts = 0;
    }
}

fn released(label: &str) {
    EFFECTS.with(|slot| {
        let state = slot.borrow();
        assert!(!state.held, "{label}: lock still held");
        assert_eq!(state.irq, ORIGINAL_IRQ, "{label}: IRQ state not restored");
        println!("{label}: {:?}", state.trace);
    });
}

fn main() {
    unsafe {
        reset();
        let failed = FixtureProcess::new(2, 7, 10, 2);
        EFFECTS.with(|slot| slot.borrow_mut().fail_alloc = true);
        assert_eq!(original_profile_accumulate_and_print_job_events(failed.proc), -ENOMEM);
        EFFECTS.with(|slot| {
            let state = slot.borrow();
            assert!(state.held, "original retained defect must be reproduced");
            assert_eq!(state.irq, 0);
            assert_eq!(state.trace, ["lock-save-irq", "allocation-failed", "original-allocation-error-report"]);
            println!("ORIGINAL_DEFECT_REPRODUCED: {:?}", state.trace);
        });

        // Reset only controlled fixture effects after preserving the original
        // defect; this is not cleanup or forced release of a real kernel lock.
        reset();
        EFFECTS.with(|slot| slot.borrow_mut().fail_alloc = true);
        assert_eq!(profile_accumulate_and_print_job_events(failed.proc), -ENOMEM);
        released("FIXED_FAILURE");
        assert!(job_profile_events.is_null());
        assert_eq!(*(&raw const job_nr_processes_left), 1);
        assert_eq!((*failed.events).tsc, 10, "error path must not consume source counters");
        EFFECTS.with(|slot| slot.borrow_mut().fail_alloc = false);
        assert_eq!(profile_accumulate_and_print_job_events(failed.proc), 0);
        released("NEXT_OPERATION_ACQUIRED_AND_FINISHED");
        EFFECTS.with(|slot| assert_eq!(slot.borrow().printed, [(2, 7, 10, 2)]));
        assert_eq!(*(&raw const job_nr_processes), -1);
        assert_eq!((*failed.events).tsc, 0);
        assert_eq!((*job_profile_events).tsc, 0);

        reset();
        let first = FixtureProcess::new(2, 7, 10, 2);
        let second = FixtureProcess::new(2, 3, 5, 1);
        assert_eq!(profile_accumulate_and_print_job_events(first.proc), 0);
        released("NORMAL_FIRST_PROCESS");
        assert_eq!((*job_profile_events).tsc, 10);
        assert_eq!((*job_profile_events).cnt, 2);
        assert_eq!((*job_profile_events.add(PROFILE_EVENT_MAX - 1)).tsc, 0);
        assert_eq!(profile_accumulate_and_print_job_events(second.proc), 0);
        released("NORMAL_LAST_PROCESS");
        EFFECTS.with(|slot| {
            let state = slot.borrow();
            assert_eq!(state.alloc_calls, 1);
            assert_eq!(state.printed, [(2, 10, 15, 3)]);
        });

        reset();
        job_profile_events = _kmalloc_for_existing_control();
        job_nr_processes = 4;
        job_nr_processes_left = 3;
        job_elapsed_ts = 1;
        let existing = FixtureProcess::new(99, 2, 8, 4);
        EFFECTS.with(|slot| slot.borrow_mut().fail_alloc = true);
        assert_eq!(profile_accumulate_and_print_job_events(existing.proc), 0);
        released("EXISTING_JOB_NO_ALLOCATION");
        assert_eq!(*(&raw const job_nr_processes), 4);
        assert_eq!(*(&raw const job_nr_processes_left), 2);
        assert_eq!(*(&raw const job_elapsed_ts), 3);
        assert_eq!((*job_profile_events).tsc, 8);
        EFFECTS.with(|slot| {
            assert_eq!(slot.borrow().alloc_calls, 0);
            assert!(slot.borrow().printed.is_empty());
        });
        reset();
    }
    println!("PASS actual job-profile lock regression: original defect, failure/reacquire, new-job success, existing-job control; IRQ and node identity preserved");
}

unsafe fn _kmalloc_for_existing_control() -> *mut ProfileEvent {
    let pointer = unsafe { alloc_zeroed(Layout::array::<ProfileEvent>(PROFILE_EVENT_MAX).unwrap()) };
    assert!(!pointer.is_null());
    EFFECTS.with(|slot| slot.borrow_mut().allocations.push(pointer as usize));
    pointer.cast()
}
