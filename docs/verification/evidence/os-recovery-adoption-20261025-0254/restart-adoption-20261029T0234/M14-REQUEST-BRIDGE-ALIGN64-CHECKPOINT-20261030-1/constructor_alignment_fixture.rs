// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source-only fixture. A reviewed profile and admission are required before running.
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    #[repr(C)]
    pub struct SyscallRequest {
        pub rtid: CInt,
        pub ttid: CInt,
        pub valid: CULong,
        pub number: CULong,
        pub args: [CULong; 6],
    }
}
#[path = "f03_request_constructors.rs"]
mod constructors;
use abi::{CInt, CLong, CULong, SyscallRequest};
use core::ptr::{addr_of, addr_of_mut};
use std::sync::Mutex;

struct Capture { calls: usize, pointer: usize, cpu: CInt, number: CULong, args: [CULong; 6], reply: CLong }
static CAPTURE: Mutex<Capture> = Mutex::new(Capture {
    calls: 0, pointer: 0, cpu: 0, number: 0, args: [0; 6], reply: 0,
});
unsafe fn ihk_mc_get_processor_id() -> CInt { 6 }
unsafe fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    // Model only the real ownership boundary: helper initializes IDs and valid.
    // All argument reads use raw field pointers, never a partial struct reference.
    unsafe {
        addr_of_mut!((*request).rtid).write(42);
        addr_of_mut!((*request).ttid).write(0);
        addr_of_mut!((*request).valid).write(0);
        let slots = addr_of!((*request).args).cast::<CULong>();
        let mut capture = CAPTURE.lock().unwrap();
        capture.calls += 1;
        capture.pointer = request as usize;
        capture.cpu = cpu;
        capture.number = addr_of!((*request).number).read();
        for i in 0..6 { capture.args[i] = slots.add(i).read(); }
        capture.reply
    }
}
fn begin(reply: CLong) {
    let mut c = CAPTURE.lock().unwrap();
    c.calls = 0; c.pointer = 0; c.cpu = 0; c.number = 0; c.args = [u64::MAX; 6]; c.reply = reply;
}
fn observe(number: u64, args: [u64; 6]) {
    let c = CAPTURE.lock().unwrap();
    assert_eq!(c.calls, 1);
    assert_ne!(c.pointer, 0);
    assert_eq!(c.pointer % 64, 0, "actual request address");
    assert_eq!(c.cpu, 6);
    assert_eq!(c.number, number);
    assert_eq!(c.args, args);
}
#[test]
fn five_actual_exports_use_aligned_defined_requests_and_preserve_returns() {
    assert_eq!(core::mem::size_of::<SyscallRequest>(), 72);
    assert_eq!(core::mem::align_of::<SyscallRequest>(), 8);
    begin(-1234);
    assert_eq!(unsafe { constructors::syscall_do_syscall2_bridge(201, 1, 2) }, -1234);
    observe(201, [1, 2, 0, 0, 0, 0]);
    begin(43);
    assert_eq!(unsafe { constructors::syscall_policy_do_syscall2_bridge(228, 3, 4) }, 43);
    observe(228, [3, 4, 0, 0, 0, 0]);
    begin(-44);
    assert_eq!(unsafe { constructors::syscall_do_syscall3_bridge(11, 5, 6, 7) }, -44);
    observe(11, [5, 6, 7, 0, 0, 0]);
    begin(45);
    assert_eq!(unsafe { constructors::syscall_policy_do_syscall3_bridge(38, 8, 9, 10) }, 45);
    observe(38, [8, 9, 10, 0, 0, 0]);
    begin(0x1_0000_0005);
    assert_eq!(unsafe { constructors::wait_host_wait4_bridge(-7, -2) }, 5);
    observe(61, [(-7_i32) as u64, 0, (-2_i32) as u64, 0, 0, 0]);
}
