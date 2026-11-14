// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Contract candidate only: kill's unused arguments 3-5 are zero. This proposed
// defined-input policy does not change UTI decisions or request ID/valid logic.
use core::mem::MaybeUninit;
use core::ptr::{addr_of, addr_of_mut, write_volatile};
use crate::abi::{CInt, CULong, Thread, X86UserContext};
use crate::debug::Ddebug;

const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\0";
#[cfg(f03_interrupt_origin_dispatch)]
const DEBUG_LINE: u32 = 5662;
#[cfg(not(f03_interrupt_origin_dispatch))]
const DEBUG_LINE: u32 = 5669;
#[used]
#[no_mangle]
#[link_section = "__verbose"]
static mut f03_interrupt_syscall_debug_v1: [Ddebug; 1] = [Ddebug {
    file: SOURCE_FILE.as_ptr().cast(), func: b"interrupt_syscall\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: DEBUG_LINE,
}];

/// Invoke the original three-argument kill forwarding route on a defined context.
///
/// # Safety
/// `thread` and its process are live for all field reads and forwarding, as in
/// the original entry. Current execution and forwarding retain their original
/// locks and lifetime; this does not acquire a reference or alter UTI state.
#[export_name = "interrupt_syscall"]
pub unsafe extern "C" fn f03_interrupt_arity3_v1(thread: *mut Thread, sig: CInt) {
    // Only the six argument fields are initialized; never create a reference
    // to an incompletely initialized context or initialize unrelated UTI state.
    let mut ctx = MaybeUninit::<X86UserContext>::uninit();
    let ctx_ptr = ctx.as_mut_ptr();
    unsafe {
        if core::ptr::read_volatile(addr_of!(f03_interrupt_syscall_debug_v1[0].line_flags)) >> 24 != 0 {
            super::kprintf(c"interrupt_syscall pid=%d tid=%d sig=%d\n".as_ptr(),
                (*(*thread).proc).pid, (*thread).tid, sig);
        }
        // SAFETY: These six distinct integer fields match the x86 syscall
        // selectors; raw field writes avoid references to uninitialized storage.
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rdi), (*(*thread).proc).pid as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rsi), (*thread).tid as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rdx), sig as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r10), 0);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r8), 0);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r9), 0);
        let error = super::syscall_generic_forwarding(62, ctx_ptr);
        if error != 0 {
            super::kprintf(c"interrupt_syscall failed. %ld\n".as_ptr(), error);
        }
    }
}
