// Functional McKernel executor cleanup fixture; no device/native execution.
// @ACTUAL_ITEMS@ is replaced with verbatim declarations and the production body.
#![allow(dead_code)]
use core::ffi::{c_int, c_long, c_ulong, c_void};
use std::alloc::{alloc, dealloc, Layout};
use std::sync::Mutex;

@ACTUAL_ITEMS@

const FD: c_int = 19;
const CPU: c_int = 4;
const BYTES: usize = 96;
const RPHYS: c_ulong = 0x1234_5000;

#[derive(Clone, Copy, Default)]
struct Faults {
    allocation: bool,
    descriptor_transfer: c_int,
    image_transfer: c_int,
    close_exec: c_int,
    close_cloexec: c_int,
}

struct State {
    faults: Faults,
    live: usize,
    allocations: usize,
    frees: usize,
    events: Vec<&'static str>,
}

static SERIAL: Mutex<()> = Mutex::new(());
static STATE: Mutex<State> = Mutex::new(State {
    faults: Faults {
        allocation: false, descriptor_transfer: 0, image_transfer: 0,
        close_exec: 0, close_cloexec: 0,
    },
    live: 0, allocations: 0, frees: 0, events: Vec::new(),
});

fn event(value: &'static str) { STATE.lock().unwrap().events.push(value); }

unsafe fn malloc(size: usize) -> *mut u8 {
    assert_eq!(size, BYTES);
    let mut state = STATE.lock().unwrap();
    assert_eq!(state.live, 0, "previous descriptor was retained");
    state.events.push("allocate");
    if state.faults.allocation { return core::ptr::null_mut(); }
    let buffer = unsafe { alloc(Layout::from_size_align(size, 16).unwrap()) };
    assert!(!buffer.is_null());
    // Nonzero allocation contents make the actual production zero_bytes call
    // observable to the first transfer provider.
    unsafe { core::ptr::write_bytes(buffer, 0xa5, size) };
    state.live = buffer as usize;
    state.allocations += 1;
    buffer
}

unsafe fn free(buffer: *mut u8) {
    let mut state = STATE.lock().unwrap();
    assert_ne!(state.live, 0, "descriptor freed without a live allocation");
    assert_eq!(buffer as usize, state.live, "wrong descriptor freed");
    state.events.push("free descriptor");
    state.live = 0;
    state.frees += 1;
    unsafe { dealloc(buffer, Layout::from_size_align(BYTES, 16).unwrap()) };
}

unsafe fn ioctl(fd: c_int, request: c_ulong, arg: c_ulong) -> c_int {
    assert_eq!(fd, FD);
    let mut state = STATE.lock().unwrap();
    match request {
        MCEXEC_UP_TRANSFER => {
            state.events.push("descriptor transfer");
            let transfer = unsafe { &*(arg as *const RemoteTransfer) };
            assert_ne!(state.live, 0);
            assert_eq!(transfer.userp as usize, state.live);
            assert_eq!((transfer.rphys, transfer.size, transfer.direction),
                       (RPHYS, BYTES as c_ulong, MCEXEC_UP_TRANSFER_FROM_REMOTE));
            assert!(unsafe { std::slice::from_raw_parts(transfer.userp.cast::<u8>(), BYTES) }
                    .iter().all(|byte| *byte == 0));
            if state.faults.descriptor_transfer == 0 {
                unsafe { core::ptr::write_bytes(transfer.userp.cast::<u8>(), 0x5a, BYTES) };
            }
            state.faults.descriptor_transfer
        }
        MCEXEC_UP_CLOSE_EXEC => {
            assert_eq!(arg, 0);
            assert_eq!(state.live, 0, "CLOSE_EXEC must run after the last descriptor borrow/free");
            state.events.push("close exec");
            state.faults.close_exec
        }
        _ => panic!("unexpected device request; this fixture never calls a real ioctl"),
    }
}

unsafe fn transfer_image(fd: c_int, desc: *mut c_void) -> c_int {
    assert_eq!(fd, FD);
    let (address, result) = {
        let mut state = STATE.lock().unwrap();
        assert_ne!(state.live, 0);
        assert_eq!(desc as usize, state.live);
        state.events.push("image transfer");
        (state.live, state.faults.image_transfer)
    };
    // The provider synchronously joins its final reader. This checks that the
    // real caller keeps the buffer live through the complete callback return.
    std::thread::spawn(move || {
        std::thread::yield_now();
        assert_eq!(STATE.lock().unwrap().live, address);
        let bytes = unsafe { std::slice::from_raw_parts(address as *const u8, BYTES) };
        assert!(bytes.iter().all(|byte| *byte == 0x5a));
    }).join().unwrap();
    result
}

unsafe fn close_cloexec_fds(fd: c_int) -> c_int {
    assert_eq!(fd, FD);
    let mut state = STATE.lock().unwrap();
    assert_eq!(state.live, 0);
    state.events.push("close cloexec");
    state.faults.close_cloexec
}

unsafe fn do_syscall_return(fd: c_int, cpu: c_int, ret: c_long, n: c_int,
                            src: c_ulong, dest: c_ulong, size: c_ulong) {
    assert_eq!((fd, cpu, ret, n, src, dest, size), (FD, CPU, 0, 0, 0, 0, 0));
    assert_eq!(STATE.lock().unwrap().live, 0);
    event("guest return");
}

unsafe fn mcexec_execve2_alloc_desc_failed_bridge() { event("allocation failed"); }
unsafe fn mcexec_execve2_transfer_desc_failed_bridge() { event("descriptor transfer failed"); }
unsafe fn mcexec_execve2_transfer_desc_ok_bridge() { event("descriptor transfer ok"); }
unsafe fn mcexec_execve2_transfer_image_failed_bridge() { event("image transfer failed"); }
unsafe fn mcexec_execve2_image_transferred_bridge() { event("image transferred"); }
unsafe fn mcexec_execve2_close_exec_failed_bridge(result: c_int) {
    assert_ne!(result, 0);
    event("close exec failed");
}

fn run(faults: Faults, expected_return: c_long, expected_events: &[&'static str]) {
    {
        let mut state = STATE.lock().unwrap();
        assert_eq!(state.live, 0);
        state.faults = faults;
        state.allocations = 0; state.frees = 0; state.events.clear();
    }
    let mut wait: McexecSyscallWaitDesc = unsafe { core::mem::zeroed() };
    wait.sr.args[1] = RPHYS;
    wait.sr.args[2] = BYTES as c_ulong;
    assert_eq!(unsafe { act_execve_phase2(&wait, FD, CPU) }, expected_return);
    let state = STATE.lock().unwrap();
    assert_eq!(state.live, 0, "replacement image retained its copied descriptor");
    let expected_count = usize::from(!faults.allocation);
    assert_eq!((state.allocations, state.frees), (expected_count, expected_count));
    assert_eq!(state.events, expected_events);
}

const THROUGH_IMAGE: &[&str] = &[
    "allocate", "descriptor transfer", "descriptor transfer ok", "image transfer", "free descriptor",
];

#[test]
fn allocation_failure_never_frees_or_enters_a_provider() {
    let _serial = SERIAL.lock().unwrap();
    run(Faults { allocation: true, ..Faults::default() }, -1, &["allocate", "allocation failed"]);
}

#[test]
fn descriptor_transfer_failure_releases_the_only_allocation() {
    let _serial = SERIAL.lock().unwrap();
    for result in [-1, 7] {
        run(Faults { descriptor_transfer: result, ..Faults::default() }, -1,
            &["allocate", "descriptor transfer", "descriptor transfer failed", "free descriptor"]);
    }
}

#[test]
fn image_transfer_failure_releases_after_the_final_synchronous_borrow() {
    let _serial = SERIAL.lock().unwrap();
    let mut expected = THROUGH_IMAGE.to_vec(); expected.push("image transfer failed");
    for result in [-1, -22, 1] {
        run(Faults { image_transfer: result, ..Faults::default() }, -1, &expected);
    }
}

#[test]
fn close_exec_failure_keeps_its_original_fatal_return_without_guest_return() {
    let _serial = SERIAL.lock().unwrap();
    let mut expected = THROUGH_IMAGE.to_vec();
    expected.extend(["image transferred", "close exec", "close exec failed"]);
    for result in [-1, 5] {
        run(Faults { close_exec: result, ..Faults::default() }, 1, &expected);
    }
}

#[test]
fn close_cloexec_failure_does_not_send_a_guest_return() {
    let _serial = SERIAL.lock().unwrap();
    let mut expected = THROUGH_IMAGE.to_vec();
    expected.extend(["image transferred", "close exec", "close cloexec"]);
    run(Faults { close_cloexec: -1, ..Faults::default() }, -1, &expected);
}

#[test]
fn repeated_successful_replacements_retain_no_descriptor() {
    let _serial = SERIAL.lock().unwrap();
    let mut expected = THROUGH_IMAGE.to_vec();
    expected.extend(["image transferred", "close exec", "close cloexec", "guest return"]);
    for _ in 0..32 { run(Faults::default(), 0, &expected); }
}
