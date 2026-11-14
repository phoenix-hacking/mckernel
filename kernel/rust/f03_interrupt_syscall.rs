// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::mem::MaybeUninit;
use core::ptr::{addr_of, read_volatile};
use crate::abi::{CInt, CLong, CULong, Thread, X86UserContext};

#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12)))]
compile_error!("interrupt_syscall requires the selected x86_64 Linux6.12 profile");

const SYS_KILL: CInt = 62;

// Preserve the original selected syscall.c debug identity. Existing conditional
// #line mappings give logical5666 for its dkprintf in OFFLOAD/POLICY/DISPATCH.
// The paired C guard restores both original mappings for C and later functions.
#[used]
#[link_section = "__verbose"]
static mut INTERRUPT_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(env!("MCKERNEL_INTERRUPT_SYSCALL_C_FILE"), "\0").as_ptr().cast(),
    func: b"interrupt_syscall\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: 5666, // Original DDEBUG_DEFAULT is DDEBUG_NONE (upper8 bits0).
};

unsafe extern "C" {
    fn syscall_generic_forwarding(number: CInt, context: *mut X86UserContext) -> CLong;
    fn kprintf(format: *const i8, ...) -> CInt;
}

/// Forward the original Linux-UTI signal through the genuine provider.
/// # Safety
/// Thread/Process and the actual CPU/offload context remain live through the
/// synchronous forwarding call. The local context remains valid until return.
/// This entry adds no reference, IRQ/preemption change or retained pointer.
#[no_mangle]
pub unsafe extern "C" fn interrupt_syscall(thread: *mut Thread, sig: CInt) {
    let mut context = MaybeUninit::<X86UserContext>::zeroed();
    if unsafe { read_volatile(addr_of!(INTERRUPT_DEBUG.line_flags)) } >> 24 != 0 {
        unsafe {
            kprintf(
                b"interrupt_syscall pid=%d tid=%d sig=%d\n\0".as_ptr().cast(),
                (*(*thread).proc).pid, (*thread).tid, sig,
            );
        }
    }
    // Re-read PID/TID after optional formatting, in the original C order.
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(
            context.as_mut_ptr(), (*(*thread).proc).pid as CULong,
        );
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(
            context.as_mut_ptr(), (*thread).tid as CULong,
        );
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg2(
            context.as_mut_ptr(), sig as CULong,
        );
    }
    let error = unsafe { syscall_generic_forwarding(SYS_KILL, context.as_mut_ptr()) };
    if error != 0 {
        unsafe { kprintf(b"interrupt_syscall failed. %ld\n\0".as_ptr().cast(), error); }
    }
}
