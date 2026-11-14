// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Host-only behavior fixture: mock layout and forwarding do not establish kernel ABI.
mod abi {
    pub type CInt = i32;
    pub type CULong = u64;
    #[repr(C)] pub struct Process { pub pid: CInt }
    #[repr(C)] pub struct Thread { pub proc: *mut Process, pub tid: CInt }
    #[repr(C)] pub struct Registers { pub rdi: u64, pub rsi: u64, pub rdx: u64, pub r10: u64, pub r8: u64, pub r9: u64 }
    #[repr(C)] pub struct X86UserContext { pub gpr: Registers }
}
mod debug {
    #[repr(C)] pub struct Ddebug { pub file: *const i8, pub func: *const i8, pub fmt: *const i8, pub line_flags: u32 }
}
use abi::*;
use std::ffi::c_char;
extern "C" { fn kprintf(fmt: *const c_char, ...); static mut log_count: i32; }
static mut SEEN: [u64; 7] = [0; 7];
static mut RESULT: i64 = 0;
unsafe fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> i64 {
    let g = unsafe { &raw const (*ctx).gpr };
    unsafe { SEEN = [n as u64, (*g).rdi, (*g).rsi, (*g).rdx, (*g).r10, (*g).r8, (*g).r9]; RESULT }
}
#[path = "../M14-REMAINING23-C-1/postimage/kernel/rust/syscall_interrupt_arity3.rs"]
mod leaf;
extern "C" { static mut f03_interrupt_syscall_debug_v1: [debug::Ddebug; 1]; }
fn main() {
    #[cfg(f03_interrupt_origin_dispatch)]
    let expected_line = 5662;
    #[cfg(not(f03_interrupt_origin_dispatch))]
    let expected_line = 5669;
    unsafe {
        let observed_line = (*(&raw const f03_interrupt_syscall_debug_v1[0])).line_flags;
        assert_eq!(observed_line, expected_line);
    }
    let mut process = Process { pid: -7 };
    let mut thread = Thread { proc: &mut process, tid: 12345 };
    for (debug_on, failure, sig) in [(false, 0, 9), (false, -5, 0), (true, 0, -1), (true, 17, 64)] {
        unsafe {
            (*(&raw mut f03_interrupt_syscall_debug_v1[0])).line_flags = if debug_on { 1 << 24 } else { 0 };
            RESULT = failure; log_count = 0; SEEN = [u64::MAX; 7];
            leaf::f03_interrupt_arity3_v1(&mut thread, sig);
            let observed = SEEN;
            assert_eq!(observed, [62, (-7i32) as u64, 12345, sig as u64, 0, 0, 0]);
            let observed_logs = log_count;
            assert_eq!(observed_logs, i32::from(debug_on) + i32::from(failure != 0));
        }
    }
    println!("PASS: four debug/error cases, exact kill number and six arguments");
}
