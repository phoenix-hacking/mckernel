#![no_std]
use core::ffi::c_void;
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,X86UserContext};
type CUInt=u32;
unsafe extern "C" {
 fn kprintf(format:*const i8,...)->CInt;
 fn cpu_halt();
    // Existing selected providers; aliases introduce no new exported helper.
    #[link_name = "interrupt_from_user"]
    fn x86_gpe_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_gpe_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_gpe_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_gpe_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_gpe_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "panic"]
    fn x86_gpe_panic(message: *const i8) -> !;
    // Existing provider symbols; aliases add no new C implementation.
    #[link_name = "interrupt_from_user"]
    fn x86_int3_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_int3_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_int3_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_int3_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_int3_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "x86_int3_debug_print_enabled"]
    static X86_INT3_DEBUG_PRINT_ENABLED: CUInt;
    // Reuse existing provider symbols; no new C implementation or ABI header.
    #[link_name = "interrupt_from_user"]
    fn x86_debug_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_debug_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_debug_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_debug_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_debug_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "x86_debug_handler_debug_print_enabled"]
    static X86_DEBUG_HANDLER_DEBUG_PRINT_ENABLED: CUInt;
}
trait DebugRegisterReader {
    /// Caller provides the existing CPU-local privileged debug-state exclusion.
    unsafe fn read<const REG: u8>(&mut self) -> CULong;
}

struct HardwareDebugRegisterReader;

impl DebugRegisterReader for HardwareDebugRegisterReader {
    #[inline(always)]
    unsafe fn read<const REG: u8>(&mut self) -> CULong {
        let value: CULong;
        // Keep each read side-effecting and a compiler memory barrier, matching
        // statement order against the buffer stores. Never read DR4 or DR5.
        match REG {
            0 => unsafe { core::arch::asm!("mov {value}, dr0", value = out(reg) value, options(nostack)) },
            1 => unsafe { core::arch::asm!("mov {value}, dr1", value = out(reg) value, options(nostack)) },
            2 => unsafe { core::arch::asm!("mov {value}, dr2", value = out(reg) value, options(nostack)) },
            3 => unsafe { core::arch::asm!("mov {value}, dr3", value = out(reg) value, options(nostack)) },
            6 => unsafe { core::arch::asm!("mov {value}, dr6", value = out(reg) value, options(nostack)) },
            7 => unsafe { core::arch::asm!("mov {value}, dr7", value = out(reg) value, options(nostack)) },
            _ => unreachable!(),
        }
        value
    }
}


// Exact kernel/include/syscall.h enum values and x86 signal.h SIGSEGV.
// The supported GCC enum transport is checked by the real-header witness.
const X86_GPE_CPUTIME_K2U: CUInt = 0;
const X86_GPE_CPUTIME_U2K: CUInt = 1;
const X86_GPE_CPUTIME_K2K_IN: CUInt = 2;
const X86_GPE_CPUTIME_K2K_OUT: CUInt = 3;
const X86_GPE_SIGSEGV: CInt = 11;

/// Complete selected general-protection-fault orchestration.
///
/// The interrupt producer owns the same live context for this call. No Rust
/// reference crosses a provider call: CS is reloaded after context display,
/// and the existing classifier is called again after interrupt_exit. The
/// actual selected Rust panic provider does not return; no new recovery path,
/// pointer retention, lock, IRQ operation or signal ownership is introduced.
#[no_mangle]
pub unsafe extern "C" fn gpe_handler(regs: *mut X86UserContext) {
    unsafe {
        x86_gpe_set_cputime(if x86_gpe_from_user(regs.cast::<c_void>()) != 0 {
            X86_GPE_CPUTIME_U2K
        } else {
            X86_GPE_CPUTIME_K2K_IN
        });
        kprintf(
            b"General protection fault (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
            core::ptr::addr_of!((*regs).gpr.orig_rax).read(),
            core::ptr::addr_of!((*regs).gpr.cs).read(),
            core::ptr::addr_of!((*regs).gpr.rip).read(),
        );
        x86_gpe_show_context(regs.cast::<c_void>());
        if (core::ptr::addr_of!((*regs).gpr.cs).read() & 3) == 0 {
            x86_gpe_panic(b"gpe_handler\0".as_ptr().cast());
        }
        x86_gpe_set_signal(
            X86_GPE_SIGSEGV, regs.cast::<c_void>(), core::ptr::null_mut(),
        );
        x86_gpe_interrupt_exit(regs);
        x86_gpe_set_cputime(if x86_gpe_from_user(regs.cast::<c_void>()) != 0 {
            X86_GPE_CPUTIME_K2U
        } else {
            X86_GPE_CPUTIME_K2K_OUT
        });
        x86_gpe_panic(b"GPF\0".as_ptr().cast());
    }
}

// Exact existing syscall.h and x86 signal.h constants; real-header witness
// must confirm the supported unsigned32-bit enum transport before acceptance.
const X86_INT3_CPUTIME_K2U: CUInt = 0;
const X86_INT3_CPUTIME_U2K: CUInt = 1;
const X86_INT3_CPUTIME_K2K_IN: CUInt = 2;
const X86_INT3_CPUTIME_K2K_OUT: CUInt = 3;
const X86_INT3_SIGTRAP: CInt = 5;
const X86_INT3_TRAP_BRKPT: CInt = 1;

/// Complete breakpoint-exception orchestration using existing selected providers.
///
/// C owns the live interrupt context. The stack-local real SigInfo storage is
/// zeroed byte-for-byte (including padding) and borrowed only for set_signal.
/// No Rust reference crosses a provider, no frame/signal pointer is retained,
/// and the second classification is performed after interrupt_exit as in C.
#[no_mangle]
pub unsafe extern "C" fn int3_handler(regs: *mut X86UserContext) {
    let mut info = core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
    unsafe {
        x86_int3_set_cputime(if x86_int3_from_user(regs.cast::<c_void>()) != 0 {
            X86_INT3_CPUTIME_U2K
        } else {
            X86_INT3_CPUTIME_K2K_IN
        });
        // #ifdef DEBUG_PRINT_CPU, including a definition with value 0, is
        // captured by the immutable data from the actual C translation unit.
        if X86_INT3_DEBUG_PRINT_ENABLED != 0 {
            kprintf(
                b"int3 exception (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
                core::ptr::addr_of!((*regs).gpr.orig_rax).read(),
                core::ptr::addr_of!((*regs).gpr.cs).read(),
                core::ptr::addr_of!((*regs).gpr.rip).read(),
            );
            x86_int3_show_context(regs.cast::<c_void>());
        }
        core::ptr::write_bytes(
            info.as_mut_ptr().cast::<u8>(), 0, core::mem::size_of::<crate::abi::SigInfo>(),
        );
        core::ptr::addr_of_mut!((*info.as_mut_ptr()).si_code).write(X86_INT3_TRAP_BRKPT);
        x86_int3_set_signal(X86_INT3_SIGTRAP, regs.cast::<c_void>(), info.as_mut_ptr());
        x86_int3_interrupt_exit(regs);
        x86_int3_set_cputime(if x86_int3_from_user(regs.cast::<c_void>()) != 0 {
            X86_INT3_CPUTIME_K2U
        } else {
            X86_INT3_CPUTIME_K2K_OUT
        });
    }
}

// Exact existing syscall.h/registers.h/x86 signal.h constants.
// The future real-header witness must confirm each value and enum transport.
const X86_DEBUG_CPUTIME_K2U: CUInt = 0;
const X86_DEBUG_CPUTIME_U2K: CUInt = 1;
const X86_DEBUG_CPUTIME_K2K_IN: CUInt = 2;
const X86_DEBUG_CPUTIME_K2K_OUT: CUInt = 3;
const X86_DEBUG_DB6_BS: CULong = 1 << 14;
const X86_DEBUG_DB6_BREAKPOINT_MASK: CULong = 0xf;
const X86_DEBUG_RFLAGS_TF: CULong = 1 << 8;
const X86_DEBUG_SIGTRAP: CInt = 5;
const X86_DEBUG_TRAP_TRACE: CInt = 2;
const X86_DEBUG_TRAP_HWBKPT: CInt = 4;

/// Complete debug-exception orchestration. The generic reader is the existing
/// privileged debug-register boundary, not a new C getter or public helper.
/// The caller retains the original live frame and CPU-local debug-state
/// exclusion. No frame or stack-local signal-info pointer escapes.
#[inline(always)]
unsafe fn x86_debug_handler_body<R: DebugRegisterReader>(
    regs: *mut X86UserContext,
    reader: &mut R,
) {
    let mut info = core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
    let mut si_code: CInt = 0;
    unsafe {
        x86_debug_set_cputime(if x86_debug_from_user(regs.cast::<c_void>()) != 0 {
            X86_DEBUG_CPUTIME_U2K
        } else {
            X86_DEBUG_CPUTIME_K2K_IN
        });
        if X86_DEBUG_HANDLER_DEBUG_PRINT_ENABLED != 0 {
            kprintf(
                b"debug exception (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
                core::ptr::addr_of!((*regs).gpr.orig_rax).read(),
                core::ptr::addr_of!((*regs).gpr.cs).read(),
                core::ptr::addr_of!((*regs).gpr.rip).read(),
            );
            x86_debug_show_context(regs.cast::<c_void>());
        }
        // Reuse the exact existing DR6 instruction/provider; only register6
        // is requested, once, after the optional context callback.
        let db6 = reader.read::<6>();
        if db6 & X86_DEBUG_DB6_BS != 0 {
            let flags = core::ptr::addr_of_mut!((*regs).gpr.rflags);
            flags.write(flags.read() & !X86_DEBUG_RFLAGS_TF);
            si_code = X86_DEBUG_TRAP_TRACE;
        } else if db6 & X86_DEBUG_DB6_BREAKPOINT_MASK != 0 {
            si_code = X86_DEBUG_TRAP_HWBKPT;
        }
        core::ptr::write_bytes(
            info.as_mut_ptr().cast::<u8>(), 0, core::mem::size_of::<crate::abi::SigInfo>(),
        );
        core::ptr::addr_of_mut!((*info.as_mut_ptr()).si_code).write(si_code);
        x86_debug_set_signal(X86_DEBUG_SIGTRAP, regs.cast::<c_void>(), info.as_mut_ptr());
        x86_debug_interrupt_exit(regs);
        x86_debug_set_cputime(if x86_debug_from_user(regs.cast::<c_void>()) != 0 {
            X86_DEBUG_CPUTIME_K2U
        } else {
            X86_DEBUG_CPUTIME_K2K_OUT
        });
    }
}

#[no_mangle]
pub unsafe extern "C" fn debug_handler(regs: *mut X86UserContext) {
    unsafe { x86_debug_handler_body(regs, &mut HardwareDebugRegisterReader); }
}

/// Complete nonreturning stop loop, using the existing architecture halt body.
/// Each wakeup returns to the next halt; no IRQ state, return policy or counter
/// is introduced. The C ABI remains void(void), as in the actual panic caller.
#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn arch_cpu_stop() {
    loop {
        unsafe { cpu_halt(); }
    }
}

// SOURCE FRAGMENT ONLY, include alongside actual candidate body and existing
// DebugRegisterReader trait. No hardware export is called by this entry.
extern "C" { fn fixture_debug_register_read(reg: CInt) -> CULong; }
struct ControlledDebugReader;
impl DebugRegisterReader for ControlledDebugReader {
    unsafe fn read<const REG: u8>(&mut self) -> CULong {
        unsafe { fixture_debug_register_read(REG as CInt) }
    }
}
#[no_mangle]
pub unsafe extern "C" fn actual_debug_controlled(regs: *mut X86UserContext) {
    unsafe { x86_debug_handler_body(regs, &mut ControlledDebugReader); }
}

include!("gpe-actual-Rust-ABI.inc");

include!("int3-actual-Rust-ABI.inc");

include!("debug-actual-Rust-ABI.inc");
