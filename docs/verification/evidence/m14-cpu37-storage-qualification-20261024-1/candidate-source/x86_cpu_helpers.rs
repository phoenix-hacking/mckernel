use core::ffi::c_void;
use core::mem::{offset_of, size_of};
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{
    CInt, CLong, CULong, IhkOsCpuRegister, Thread, X86BasicRegs, X86KernelContext, X86UserContext,
};

type CUInt = u32;

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const LAPIC_TIMER: CInt = 0x320;
const LAPIC_LVTPC: CInt = 0x340;
const LAPIC_TIMER_INITIAL: CInt = 0x380;
const LAPIC_TIMER_DIVIDE: CInt = 0x3e0;
const LAPIC_SPURIOUS: CInt = 0x0f0;
const LAPIC_EOI: CInt = 0x0b0;
const MSR_IA32_APIC_BASE: CInt = 0x1b;
const MSR_PLATFORM_INFO: CInt = 0xce;
const MSR_NHM_TURBO_RATIO_LIMIT: CInt = 0x1ad;
const MSR_IA32_PERF_CTL: CInt = 0x199;
const MSR_IA32_ENERGY_PERF_BIAS: CInt = 0x1b0;
const X2APIC_ENABLE: CULong = 1 << 10;
const LOCAL_TIMER_VECTOR: CUInt = 0xef;
const LOCAL_PERF_VECTOR: CUInt = 0xf0;
const LOCAL_SMP_FUNC_CALL_VECTOR: CInt = 0xf1;
const ARCH_SET_FS: CULong = 0x1002;
const IHK_UCR_STACK_POINTER: CInt = 1;
const IHK_UCR_PROGRAM_COUNTER: CInt = 2;
const IHK_ASR_X86_FS: CInt = 0;
const MSR_FS_BASE: CUInt = 0xc000_0100;
const MCCTRL_OS_CPU_READ_REGISTER: CInt = 0;
const MCCTRL_OS_CPU_WRITE_REGISTER: CInt = 1;
const APIC_DIVISOR: CUInt = 16;
const APIC_LVT_TIMER_PERIODIC: CUInt = 1 << 17;
const KVM_SYSTEM_TIME_ENABLE: CULong = 0x1;
const PAGE_SIZE: CULong = 4096;
const PAGE_P2ALIGN: CInt = 0;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_KERNEL: CInt = 0;
const KVM_CPUID_SIGNATURE: CULong = 0x4000_0000;
const KVM_CPUID_FEATURES: CULong = 0x4000_0001;
const KVM_FEATURE_CLOCKSOURCE2: CInt = 3;
const KVM_FEATURE_CLOCKSOURCE: CInt = 0;
const MSR_KVM_SYSTEM_TIME_NEW: CLong = 0x4b56_4d01;
const MSR_KVM_SYSTEM_TIME: CLong = 0x12;
const PF_USER: CULong = 1 << 2;
const PRE_INTERRUPT_STACK_SCAN_WINDOW: CULong = 0x10000;
const STACK_LOWER_BOUND: CULong = 0xffff_8000_0000_0000;
const STACK_UPPER_BOUND: CULong = 0xffff_ffff_8000_0000;
static CPU_FILE: &[u8] = b"arch/x86_64/kernel/cpu.c\0";

#[repr(C)]
struct PvclockVsyscallTimeInfo {
    contents: [CLong; 64 / size_of::<CLong>()],
}

type X86StackFn = unsafe extern "C" fn() -> *mut c_void;
type X86MsrReadFn = unsafe extern "C" fn() -> CULong;
type X86MsrWriteFn = unsafe extern "C" fn(CULong);
type X86CpuLocalFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type X86IssueIpiFn = unsafe extern "C" fn(CULong, CInt);
type X86InterruptLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type X86VoidFn = unsafe extern "C" fn();
type X86DisableSaveFn = unsafe extern "C" fn() -> CULong;
type X86RestoreFn = unsafe extern "C" fn(CULong);
type X86IcrWriteFn = unsafe extern "C" fn(CUInt, CUInt);
type X86LapicWriteFn = unsafe extern "C" fn(CInt, CUInt);
type X86SelectLapicModeFn = unsafe extern "C" fn(CInt);
type X86ReadMsrRegFn = unsafe extern "C" fn(CInt) -> CULong;
type X86WriteMsrRegFn = unsafe extern "C" fn(CInt, CULong);
type X86MapFixedFn = unsafe extern "C" fn(CULong, CULong, CInt) -> *mut c_void;
type X86RunningOnKvmFn = unsafe extern "C" fn() -> CInt;
type X86Cpuid6Fn = unsafe extern "C" fn(*mut CULong, *mut CULong);
type X86CpuidEdxFn = unsafe extern "C" fn(CULong, *mut CULong);
type X86CpuidLeafFn =
    unsafe extern "C" fn(CULong, *mut CULong, *mut CULong, *mut CULong, *mut CULong);
type X86CpuLogFn = unsafe extern "C" fn(CInt);
type X86CpuValueLogFn = unsafe extern "C" fn(CInt, CInt);
type X86CpuULongLogFn = unsafe extern "C" fn(CInt, CULong);
type X86ContextLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong, CULong);
type X86KprintfLockFn = unsafe extern "C" fn() -> CULong;
type X86KprintfUnlockFn = unsafe extern "C" fn(CULong);
type X86TraceEnterUserLogFn =
    unsafe extern "C" fn(CInt, CInt, CInt, CULong, CULong, CULong, CULong, CULong, CInt);
type X86RunqUnlockFn = unsafe extern "C" fn(*mut c_void, CULong);
type X86GetULongFn = unsafe extern "C" fn() -> CULong;
type X86GetCpuULongFn = unsafe extern "C" fn(CInt) -> CULong;
type X86WakeupFn = unsafe extern "C" fn(CInt, CULong);
type X86GetIntFn = unsafe extern "C" fn() -> CInt;
type X86InitProcessorsFn = unsafe extern "C" fn(CInt);
type X86DelayFn = unsafe extern "C" fn(CInt);
type X86AllocAlignedPagesNodeFn =
    unsafe extern "C" fn(CInt, CInt, CULong, CInt, CInt, CULong, *mut i8, CInt) -> *mut c_void;
type X86VirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type X86StackFrameLogFn = unsafe extern "C" fn(CULong, CULong, CULong);
type X86PrintStackFn = unsafe extern "C" fn(*mut c_void, CULong);

extern "C" {
    #[link_name = "no_turbo"]
    static mut X86_NO_TURBO: CInt;
    fn x86_running_on_kvm_bridge() -> CInt;
    fn x86_cpuid6_bridge(eaxp: *mut CULong, ecxp: *mut CULong);
    fn kprintf(format: *const i8, ...) -> CInt;
    // Existing providers; the Rust-local alias adds no exported C helper.
    fn interrupt_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "cpu_enable_interrupt"]
    fn x86_interrupt_exit_enable_interrupt();
    fn check_sig_pending();
    fn check_need_resched();
    fn check_signal(rc: CULong, regs: *mut c_void, num: CInt);
    fn __kprintf(format: *const i8, ...) -> CInt;
    fn snprintf(buf: *mut i8, size: usize, format: *const i8, ...) -> CInt;
    fn arch_delay(us: CInt);
    fn do_arch_prctl(code: CULong, address: CULong) -> CLong;
    fn x86_lapic_write_bridge(reg: CInt, value: CUInt);
    fn x86_read_msr_bridge(reg: CInt) -> CULong;
    fn x86_issue_ipi_bridge(apic_id: CULong, vector: CInt);
    fn x86_cpuid_leaf_bridge(
        op: CULong,
        eaxp: *mut CULong,
        ebxp: *mut CULong,
        ecxp: *mut CULong,
        edxp: *mut CULong,
    );
    fn x86_xsave_size_bridge() -> CInt;
    fn x86_xsave_mask_bridge() -> CULong;
    fn x86_alloc_aligned_pages_node_bridge(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void;
    fn x86_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn x86_write_msr_bridge(reg: CInt, value: CULong);
    fn x86_current_cpu_bridge() -> CInt;
    fn x86_kprintf_lock_bridge() -> CULong;
    fn x86_kprintf_unlock_bridge(flags: CULong);
    fn x86_stack_frame_log_bridge(ip: CULong, sp: CULong, fp: CULong);
    fn x86_cpu_boot_status_slot_bridge() -> *mut CInt;
    fn x86_boot_trampoline_va_bridge() -> *mut c_void;
    fn x86_boot_trampoline_code_data_bridge() -> *const u8;
    fn x86_boot_trampoline_code_size_bridge() -> CULong;
    fn x86_boot_ap_trampoline_bridge() -> CULong;
    fn x86_boot_setup_ap_bridge() -> *mut c_void;
    fn x86_boot_page_table_phys_bridge() -> CULong;
    fn x86_cpu_kstack_bridge(cpu: CInt) -> CULong;
    fn x86_transit_page_table_bridge() -> CULong;
    fn x86_wakeup_bridge(cpu: CInt, trampoline: CULong);
    fn x86_cpu_pause_bridge();
    fn x86_current_thread_bridge() -> *mut c_void;
    fn x86_trace_enter_user_offsets_bridge() -> *const X86TraceEnterUserOffsets;
    fn x86_mcexec_v10_trace_log_bridge(
        cpu: CInt,
        pid: CInt,
        tid: CInt,
        rip: CULong,
        sp: CULong,
        cs: CULong,
        ss: CULong,
        rflags: CULong,
        status: CInt,
    );
    fn x86_this_cpu_local_var_bridge() -> *mut c_void;
    fn x86_runq_lock_offset_bridge() -> CULong;
    fn x86_runq_irqstate_offset_bridge() -> CULong;
    fn x86_runq_unlock_bridge(lock: *mut c_void, irqstate: CULong);
    static mut __x86_syscall_handler: CULong;
    static mut __page_fault_handler_address: CULong;
    #[link_name = "pvti"]
    static mut X86_PVTI: *mut PvclockVsyscallTimeInfo;
    #[link_name = "pvti_npages"]
    static mut X86_PVTI_NPAGES: CInt;
    #[link_name = "pvti_msr"]
    static mut X86_PVTI_MSR: CLong;
}

#[no_mangle]
pub unsafe extern "C" fn rdtsc() -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "rdtsc",
        lateout("edx") high,
        lateout("eax") low,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}

#[no_mangle]
pub unsafe extern "C" fn read_tsc() -> CULong {
    rdtsc()
}

#[no_mangle]
pub unsafe extern "C" fn get_xsave_size() -> CInt {
    unsafe { x86_xsave_size_bridge() }
}

/// Save the current CPU's extended state into the exclusively owned thread slot.
///
/// The caller pins execution to the CPU whose state is being saved and owns the
/// thread and its buffer exclusively until the save completes. XSAVE setup is
/// boot-stable: a nonzero `available` requires CR4.OSXSAVE, an XCR0-compatible
/// mask, and a 64-byte-aligned buffer covering the CPUID-reported standard extent.
/// The kernel compiler and all callees must preserve the no-FP/SIMD profile.
/// Allocation failure returns before XSAVE; the scheduler must not restore an
/// unsaved state or progress the context switch after this error.
///
/// Preserve the original C gates: nonpositive `size` prevents allocation but
/// does not disable XSAVE when `available` is nonzero. Such a configuration with
/// an absent/undersized buffer violates the hardware precondition; this function
/// does not reinterpret it as a successful skip or silently change the ABI.
#[no_mangle]
pub unsafe extern "C" fn rust_x86_save_fp_regs(
    thread: *mut Thread,
    available: CInt,
    size: CInt,
    mask: CULong,
) -> CInt {
    if available != 0 && size > 0 && unsafe { (*thread).fp_regs.is_null() } {
        let pages = (size as usize + PAGE_SIZE as usize - 1) / PAGE_SIZE as usize;
        let state = unsafe {
            x86_alloc_aligned_pages_node_bridge(
                pages as CInt,
                PAGE_P2ALIGN,
                IHK_MC_AP_NOWAIT,
                -1,
                IHK_MC_PG_KERNEL,
                CULong::MAX,
                CPU_FILE.as_ptr().cast::<i8>() as *mut i8,
                line!() as CInt,
            )
        };
        if state.is_null() {
            unsafe { kprintf(b"error: allocating fp_regs pages\n\0".as_ptr().cast()) };
            return -ENOMEM;
        }
        unsafe {
            core::ptr::write_bytes(state.cast::<u8>(), 0, pages * PAGE_SIZE as usize);
            (*thread).fp_regs = state;
        }
    }
    if available != 0 {
        unsafe { x86_save_xstate((*thread).fp_regs, mask) };
    }
    0
}

/// XSAVE writes memory and leaves arithmetic flags unchanged. The full 64-bit
/// requested mask is split exactly across EDX:EAX; no vector operands are used.
#[inline(always)]
unsafe fn x86_save_xstate(state: *mut c_void, mask: CULong) {
    unsafe {
        core::arch::asm!(
            "xsave [{state}]",
            state = in(reg) state,
            in("eax") mask as u32,
            in("edx") (mask >> 32) as u32,
            options(nostack, preserves_flags),
        );
    }
}

// The old diagnostic counter was a racy C static. A relaxed saturating atomic
// gives each of the first sixteen calls one ticket without introducing a lock,
// IRQ changes, allocation, or unbounded logging. It orders no FP/thread memory.
static X86_FP_DEFAULT_LOGS: core::sync::atomic::AtomicU32 =
    core::sync::atomic::AtomicU32::new(0);

/// Restore the boot-captured default state, or initialize x87 and optional SSE.
///
/// Callers retain CPU/IRQ exclusion and any supplied thread/process lifetimes.
/// `initial_available != 0` with XSAVE enabled promises a readable, 64-byte
/// aligned boot image covering the CPUID extent, valid for the stable XCR0 mask.
/// The pointer is deliberately not used as a new availability gate: malformed
/// geometry is a caller error, just as for the original C. All callees, including
/// the diagnostic formatter, must obey the kernel no-FP/SIMD compiler profile.
#[no_mangle]
pub unsafe extern "C" fn rust_x86_restore_default_fp_regs(
    thread: *mut Thread,
    available: CInt,
    initial_available: CInt,
    initial: *const c_void,
    mask: CULong,
    sse_enabled: CInt,
) {
    use core::sync::atomic::Ordering;
    if X86_FP_DEFAULT_LOGS
        .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |count| {
            if count < 16 { Some(count + 1) } else { None }
        })
        .is_ok()
    {
        let (pid, tid) = if thread.is_null() {
            (-1, -1)
        } else {
            let process = unsafe { (*thread).proc };
            let pid = if process.is_null() { -1 } else { unsafe { (*process).pid } };
            (pid, unsafe { (*thread).tid })
        };
        unsafe {
            kprintf(
                b"mcexec_v10: fp_default cpu=%d pid=%d tid=%d xsave=%d initial=%d\n\0".as_ptr().cast(),
                x86_current_cpu_bridge(), pid, tid, available, initial_available,
            );
        }
    }
    if available != 0 && initial_available != 0 {
        unsafe { x86_restore_xstate(initial, mask) };
    } else {
        unsafe { x86_initialize_fp_state(sse_enabled) };
    }
}

/// Restore the exclusively owned thread state, retaining the NULL/no-buffer
/// default path and the original no-op for a buffered thread without XSAVE.
/// Never frees, changes, allocates or copies a thread state buffer. In addition
/// to the default-path requirements, a present buffer covers the boot-stable
/// CPUID extent and uses the supported standard XSAVE layout and XCR0 mask.
/// Execution stays on the intended CPU with exclusion held across the restore;
/// all generated code and callees obey the kernel no-FP/SIMD compiler profile.
#[no_mangle]
pub unsafe extern "C" fn rust_x86_restore_fp_regs(
    thread: *mut Thread,
    available: CInt,
    initial_available: CInt,
    initial: *const c_void,
    mask: CULong,
    sse_enabled: CInt,
) {
    if thread.is_null() || unsafe { (*thread).fp_regs.is_null() } {
        unsafe {
            rust_x86_restore_default_fp_regs(
                thread, available, initial_available, initial, mask, sse_enabled,
            );
        }
        return;
    }
    if available != 0 {
        unsafe { x86_restore_xstate((*thread).fp_regs, mask) };
    }
}

/// XRSTOR consumes the complete EDX:EAX request mask. The ordinary asm memory
/// effect prevents memory reordering across restore. FP/SIMD registers are not
/// Rust operands: the entire kernel build excludes their compiler-generated use.
#[inline(always)]
unsafe fn x86_restore_xstate(state: *const c_void, mask: CULong) {
    unsafe {
        core::arch::asm!(
            "xrstor [{state}]",
            state = in(reg) state,
            in("eax") mask as u32,
            in("edx") (mask >> 32) as u32,
            options(nostack, preserves_flags),
        );
    }
}

#[inline(always)]
unsafe fn x86_initialize_fp_state(sse_enabled: CInt) {
    unsafe { core::arch::asm!("finit", options(nostack, preserves_flags)); }
    if sse_enabled != 0 {
        let default_mxcsr: u32 = 0x1f80;
        unsafe {
            core::arch::asm!(
                "ldmxcsr [{mxcsr}]",
                mxcsr = in(reg) &default_mxcsr,
                options(nostack, preserves_flags),
            );
        }
    }
}

/// Reset the local idle context using its saved state when present.
///
/// The caller supplies the actual CPU-local idle thread, pins execution and
/// retains the same CPU/IRQ exclusion and boot-image lifetimes required by the
/// existing restore helpers. No allocation or thread-slot mutation occurs.
#[no_mangle]
pub unsafe extern "C" fn rust_x86_clear_fp_regs(
    idle: *mut Thread,
    available: CInt,
    initial_available: CInt,
    initial: *const c_void,
    mask: CULong,
    sse_enabled: CInt,
) {
    if unsafe { !(*idle).fp_regs.is_null() } {
        unsafe {
            rust_x86_restore_fp_regs(
                idle, available, initial_available, initial, mask, sse_enabled,
            );
        }
    } else {
        unsafe {
            rust_x86_restore_default_fp_regs(
                idle, available, initial_available, initial, mask, sse_enabled,
            );
        }
    }
}

#[cfg(native_linux_irq_work_v6_12)]
extern "C" {
    fn native_xrstor_checked(buffer: *const u8, mask: CULong) -> CLong;
}

/// Preserve the signal reset's checked-XRSTOR fault recovery and exact status.
/// The existing current-thread bridge is called only for the no-XSAVE default
/// restoration path, matching the C selection and retaining lazy lookup. All
/// CPU exclusion, boot-image extent/alignment and no-FP compiler requirements
/// of the existing restore helpers and native fault bridge remain in force.
#[cfg(native_linux_irq_work_v6_12)]
#[no_mangle]
pub unsafe extern "C" fn rust_x86_native_signal_reset_fp(
    available: CInt,
    initial_available: CInt,
    initial: *const c_void,
    mask: CULong,
    sse_enabled: CInt,
) -> CLong {
    if available != 0 {
        if initial_available == 0 {
            return -95; // EOPNOTSUPP, matching the existing x86/Linux ABI.
        }
        return unsafe { native_xrstor_checked(initial.cast(), mask) };
    }
    unsafe {
        rust_x86_restore_default_fp_regs(
            x86_current_thread_bridge().cast(), available, initial_available, initial, mask, sse_enabled,
        );
    }
    0
}

/// Query the hardware MXCSR mask without changing the live FP state. Disabled
/// SSE and the architectural zero-mask result both retain the 0xffbf fallback.
#[cfg(native_linux_irq_work_v6_12)]
#[no_mangle]
pub unsafe extern "C" fn rust_x86_native_signal_mxcsr_mask(sse_enabled: CInt) -> CUInt {
    if sse_enabled == 0 {
        return 0xffbf;
    }
    let mask = unsafe { x86_read_mxcsr_mask() };
    if mask != 0 { mask } else { 0xffbf }
}

#[cfg(native_linux_irq_work_v6_12)]
#[inline(always)]
unsafe fn x86_read_mxcsr_mask() -> CUInt {
    use crate::abi::I387FxsaveStruct;
    // Use the production ABI, not a replica. FXSAVE writes mxcsr_mask at byte28
    // but need not initialize every reserved byte: read only this written u32.
    const _: () = assert!(size_of::<I387FxsaveStruct>() == 512);
    const _: () = assert!(core::mem::align_of::<I387FxsaveStruct>() == 16);
    const _: () = assert!(offset_of!(I387FxsaveStruct, mxcsr_mask) == 28);
    let mut saved = core::mem::MaybeUninit::<I387FxsaveStruct>::uninit();
    let pointer = saved.as_mut_ptr();
    unsafe {
        core::arch::asm!(
            "fxsave [{state}]",
            state = in(reg) pointer,
            options(nostack, preserves_flags),
        );
        core::ptr::addr_of!((*pointer).mxcsr_mask).read()
    }
}

/// Copy the saved state owned by `from` into the independently owned `to` state.
///
/// The caller holds both thread lifetimes and exclusive access to the destination
/// slot/buffer. A nonnull source covers `size` initialized bytes; an existing
/// destination covers the same extent. Source and destination buffers must not
/// overlap, as for the original memcpy. XSAVE configuration is boot-stable.
/// New allocations cover whole pages and are zeroed before copying so reserved
/// state and the page tail never inherit allocator contents. No allocation or
/// destination change occurs for an absent source. This function never executes
/// XSAVE/XRSTOR and requires the kernel's no-FP/SIMD compiler profile.
#[no_mangle]
pub unsafe extern "C" fn rust_x86_copy_fp_regs(
    from: *const Thread,
    to: *mut Thread,
    available: CInt,
    size: CInt,
) -> CInt {
    if from.is_null() || to.is_null() {
        return -EINVAL;
    }
    let source = unsafe { (*from).fp_regs };
    if source.is_null() {
        return 0;
    }
    // A saved source cannot exist without a valid XSAVE configuration. Unlike
    // the C fallback, reject this invalid lifecycle state before any copy.
    if available == 0 || size <= 0 {
        return -EINVAL;
    }
    let length = size as usize;
    let pages = (length + PAGE_SIZE as usize - 1) / PAGE_SIZE as usize;
    let mut destination = unsafe { (*to).fp_regs };
    if destination.is_null() {
        destination = unsafe {
            x86_alloc_aligned_pages_node_bridge(
                pages as CInt,
                PAGE_P2ALIGN,
                IHK_MC_AP_NOWAIT,
                -1,
                IHK_MC_PG_KERNEL,
                CULong::MAX,
                CPU_FILE.as_ptr().cast::<i8>() as *mut i8,
                line!() as CInt,
            )
        };
        if destination.is_null() {
            return -ENOMEM;
        }
        unsafe {
            core::ptr::write_bytes(destination.cast::<u8>(), 0, pages * PAGE_SIZE as usize);
            (*to).fp_regs = destination;
        }
    }
    unsafe {
        core::ptr::copy_nonoverlapping(source.cast::<u8>(), destination.cast::<u8>(), length);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn get_xsave_mask() -> CULong {
    unsafe { x86_xsave_mask_bridge() }
}

#[no_mangle]
pub unsafe extern "C" fn x86_call_ap_func_body_result(
    cpu_boot_status_slot: *mut CInt,
    next_func: Option<X86VoidFn>,
) -> CInt {
    if cpu_boot_status_slot.is_null() {
        return -EINVAL;
    }
    let Some(next) = next_func else {
        return -EINVAL;
    };

    unsafe {
        write_volatile(cpu_boot_status_slot, 1);
        next();
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn call_ap_func(next_func: Option<X86VoidFn>) {
    unsafe {
        x86_call_ap_func_body_result(x86_cpu_boot_status_slot_bridge(), next_func);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __show_stack(sp: *mut CULong) {
    unsafe {
        x86_show_stack_body_result(
            sp,
            STACK_LOWER_BOUND,
            STACK_UPPER_BOUND,
            Some(x86_stack_frame_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn show_context_stack(rbp: *mut CULong) {
    unsafe {
        x86_show_stack_body_result(
            rbp,
            STACK_LOWER_BOUND,
            STACK_UPPER_BOUND,
            Some(x86_stack_frame_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_boot_cpu(cpuid: CInt, pc: CULong) {
    unsafe {
        x86_boot_cpu_body_result(
            x86_boot_trampoline_va_bridge(),
            x86_boot_trampoline_code_data_bridge(),
            x86_boot_trampoline_code_size_bridge(),
            cpuid,
            pc,
            x86_boot_ap_trampoline_bridge(),
            x86_cpu_boot_status_slot_bridge(),
            x86_boot_setup_ap_bridge(),
            Some(x86_boot_page_table_phys_bridge),
            Some(x86_cpu_kstack_bridge),
            Some(x86_transit_page_table_bridge),
            Some(x86_wakeup_bridge),
            Some(x86_cpu_pause_bridge),
        );
    }
}

static mut X86_MEXEC_V10_ENTER_USER_LOGS: CInt = 0;

#[no_mangle]
pub unsafe extern "C" fn mcexec_v10_trace_enter_user(regs: *const X86UserContext) {
    unsafe {
        x86_mcexec_v10_trace_enter_user_body_result(
            regs,
            x86_current_thread_bridge(),
            &raw mut X86_MEXEC_V10_ENTER_USER_LOGS,
            32,
            x86_current_cpu_bridge(),
            x86_trace_enter_user_offsets_bridge(),
            Some(x86_mcexec_v10_trace_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn release_runq_lock() {
    unsafe {
        x86_release_runq_lock_body_result(
            x86_this_cpu_local_var_bridge(),
            x86_runq_lock_offset_bridge(),
            x86_runq_irqstate_offset_bridge(),
            Some(x86_runq_unlock_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn mb() {
    core::arch::asm!("mfence", options(nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn rmb() {
    core::arch::asm!("lfence", options(nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn wmb() {
    core::arch::asm!("sfence", options(nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn smp_mb() {
    unsafe { mb() };
}

#[no_mangle]
pub unsafe extern "C" fn smp_rmb() {
    unsafe { rmb() };
}

#[no_mangle]
pub unsafe extern "C" fn smp_wmb() {
    core::arch::asm!("", options(nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn arch_barrier() {
    core::arch::asm!("", options(nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn smp_load_acquire_ulong(p: *const CULong) -> CULong {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}

#[no_mangle]
pub unsafe extern "C" fn smp_load_acquire_uint(p: *const CUInt) -> CUInt {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}

#[no_mangle]
pub unsafe extern "C" fn smp_load_acquire_int(p: *const CInt) -> CInt {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}

#[no_mangle]
pub unsafe extern "C" fn smp_load_acquire_ptr(p: *const *mut c_void) -> *mut c_void {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}

#[no_mangle]
pub unsafe extern "C" fn smp_store_release_ulong(p: *mut CULong, value: CULong) {
    unsafe { arch_barrier() };
    unsafe { write_volatile(p, value) };
}

#[no_mangle]
pub unsafe extern "C" fn smp_store_release_uint(p: *mut CUInt, value: CUInt) {
    unsafe { arch_barrier() };
    unsafe { write_volatile(p, value) };
}

#[no_mangle]
pub unsafe extern "C" fn smp_store_release_int(p: *mut CInt, value: CInt) {
    unsafe { arch_barrier() };
    unsafe { write_volatile(p, value) };
}

#[no_mangle]
pub extern "C" fn CVAL(event: CUInt, mask: CUInt) -> CULong {
    (((event & 0xf00) as CULong) << 24) | ((mask as CULong) << 8) | ((event & 0xff) as CULong)
}

#[no_mangle]
pub extern "C" fn CVAL2(event: CUInt, mask: CUInt, inv: CUInt, count: CUInt) -> CULong {
    CVAL(event, mask) | (((inv & 1) as CULong) << 23) | (((count & 0xff) as CULong) << 24)
}

#[no_mangle]
pub unsafe extern "C" fn xgetbv(index: CUInt) -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "xgetbv",
        lateout("edx") high,
        lateout("eax") low,
        in("ecx") index,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}

#[no_mangle]
pub unsafe extern "C" fn xsetbv(index: CUInt, value: CULong) {
    let low = value as u32;
    let high = (value >> 32) as u32;

    core::arch::asm!(
        "xsetbv",
        in("eax") low,
        in("edx") high,
        in("ecx") index,
        options(nomem, nostack, preserves_flags),
    );
}

#[no_mangle]
pub unsafe extern "C" fn wrmsr(index: CUInt, value: CULong) {
    let low = value as u32;
    let high = (value >> 32) as u32;

    core::arch::asm!(
        "wrmsr",
        in("ecx") index,
        in("eax") low,
        in("edx") high,
        options(nostack, preserves_flags),
    );
}

#[no_mangle]
pub unsafe extern "C" fn rdpmc(counter: CUInt) -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "rdpmc",
        lateout("edx") high,
        lateout("eax") low,
        in("ecx") counter,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}

#[no_mangle]
pub unsafe extern "C" fn rdmsr(index: CUInt) -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "rdmsr",
        lateout("edx") high,
        lateout("eax") low,
        in("ecx") index,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_mb() {
    core::arch::asm!("mfence", options(nostack, preserves_flags));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_halt() {
    core::arch::asm!("hlt", options(nomem, nostack));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_safe_halt() {
    core::arch::asm!("sti; hlt", options(nomem, nostack));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_enable_interrupt() {
    core::arch::asm!("sti", options(nomem, nostack));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_disable_interrupt() {
    core::arch::asm!("cli", options(nomem, nostack));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_restore_interrupt(flags: CULong) {
    core::arch::asm!("push {flags}", "popfq", flags = in(reg) flags);
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_disable_interrupt_save() -> CULong {
    let flags: CULong;

    core::arch::asm!("pushfq", "pop {flags}", "cli", flags = lateout(reg) flags);

    flags
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_enable_interrupt_save() -> CULong {
    let flags: CULong;

    core::arch::asm!("pushfq", "pop {flags}", "sti", flags = lateout(reg) flags);

    flags
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_interrupt_disabled() -> CInt {
    let flags: CULong;

    core::arch::asm!(
        "pushfq",
        "pop {flags}",
        flags = lateout(reg) flags,
        options(preserves_flags),
    );

    if flags & 0x200 == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ihk_mc_get_smp_handler_irq() -> CInt {
    LOCAL_SMP_FUNC_CALL_VECTOR
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_interrupt_id(cpu: CInt) -> CInt {
    unsafe {
        let local = crate::x86_local::get_x86_cpu_local_variable(cpu);
        read_volatile(core::ptr::addr_of!((*local).apic_id)) as CInt
    }
}

unsafe extern "C" fn x86_cpu_local_native(cpu: CInt) -> *mut c_void {
    unsafe { crate::x86_local::get_x86_cpu_local_variable(cpu).cast::<c_void>() }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt {
    unsafe {
        x86_interrupt_cpu_result(
            cpu,
            vector,
            crate::ap::num_processors,
            Some(x86_cpu_local_native),
            size_of::<CULong>() as CULong,
            Some(x86_issue_ipi_bridge),
            Some(x86_interrupt_log_bridge),
        )
    }
}

#[no_mangle]
pub extern "C" fn arch_clone_thread(
    _othread: *mut c_void,
    _pc: CULong,
    _sp: CULong,
    _nthread: *mut c_void,
) {
}

#[no_mangle]
pub extern "C" fn arch_flush_icache_all() {}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_init_user_tlsbase(
    _ctx: *mut X86UserContext,
    tls_base_addr: CULong,
) {
    unsafe {
        do_arch_prctl(ARCH_SET_FS, tls_base_addr);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_set_page_fault_handler(handler: *mut c_void) {
    unsafe {
        write_volatile(
            core::ptr::addr_of_mut!(__page_fault_handler_address),
            handler as CULong,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_set_syscall_handler(handler: *mut c_void) {
    unsafe {
        write_volatile(
            core::ptr::addr_of_mut!(__x86_syscall_handler),
            handler as CULong,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_delay_us(us: CInt) {
    unsafe {
        arch_delay(us);
    }
}

#[no_mangle]
pub unsafe extern "C" fn REGS_GET_STACK_POINTER(regs: *const X86UserContext) -> CULong {
    if regs.is_null() {
        return 0;
    }

    unsafe { read_volatile(&(*regs).gpr.rsp) }
}

#[inline(always)]
unsafe fn x86_syscall_read(uctx: *const X86UserContext, selector: CInt) -> CULong {
    if uctx.is_null() {
        return 0;
    }

    unsafe {
        match selector {
            0 => read_volatile(&(*uctx).gpr.rdi),
            1 => read_volatile(&(*uctx).gpr.rsi),
            2 => read_volatile(&(*uctx).gpr.rdx),
            3 => read_volatile(&(*uctx).gpr.r10),
            4 => read_volatile(&(*uctx).gpr.r8),
            5 => read_volatile(&(*uctx).gpr.r9),
            6 => read_volatile(&(*uctx).gpr.rax),
            7 => read_volatile(&(*uctx).gpr.orig_rax),
            8 => read_volatile(&(*uctx).gpr.rip),
            9 => read_volatile(&(*uctx).gpr.rsp),
            _ => 0,
        }
    }
}

#[inline(always)]
unsafe fn x86_syscall_write(uctx: *mut X86UserContext, selector: CInt, value: CULong) {
    if uctx.is_null() {
        return;
    }

    unsafe {
        match selector {
            0 => write_volatile(&mut (*uctx).gpr.rdi, value),
            1 => write_volatile(&mut (*uctx).gpr.rsi, value),
            2 => write_volatile(&mut (*uctx).gpr.rdx, value),
            3 => write_volatile(&mut (*uctx).gpr.r10, value),
            4 => write_volatile(&mut (*uctx).gpr.r8, value),
            5 => write_volatile(&mut (*uctx).gpr.r9, value),
            6 => write_volatile(&mut (*uctx).gpr.rax, value),
            _ => {}
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg0(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 0) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg1(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 1) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg2(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 2) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg3(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 3) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg4(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 4) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg5(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 5) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg0(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 0, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg1(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 1, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg2(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 2, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg3(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 3, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg4(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 4, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg5(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 5, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_ret(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 6) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_ret(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 6, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_number(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 7) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_pc(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 8) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_sp(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 9) }
}

#[repr(C)]
pub struct X86ThreadContextOffsets {
    pub thread_status_offset: CULong,
    pub thread_uctx_offset: CULong,
    pub thread_tlsblock_base_offset: CULong,
}

#[repr(C)]
pub struct X86TraceEnterUserOffsets {
    pub thread_tid_offset: CULong,
    pub thread_status_offset: CULong,
    pub thread_proc_offset: CULong,
    pub process_pid_offset: CULong,
}

#[no_mangle]
pub unsafe extern "C" fn x86_boot_cpu_body_result(
    trampoline_va: *mut c_void,
    trampoline_code_data: *const u8,
    trampoline_code_size: CULong,
    cpuid: CInt,
    pc: CULong,
    ap_trampoline: CULong,
    boot_status_slot: *mut CInt,
    setup_x86_ap_addr: *mut c_void,
    boot_page_table_phys_fn: Option<X86GetULongFn>,
    cpu_kstack_fn: Option<X86GetCpuULongFn>,
    transit_page_table_fn: Option<X86GetULongFn>,
    wakeup_fn: Option<X86WakeupFn>,
    pause_fn: Option<X86VoidFn>,
) -> CInt {
    if trampoline_va.is_null()
        || trampoline_code_data.is_null()
        || boot_status_slot.is_null()
        || setup_x86_ap_addr.is_null()
    {
        return -EINVAL;
    }
    let (Some(boot_pt_phys), Some(cpu_kstack), Some(transit_pt), Some(wakeup), Some(pause)) = (
        boot_page_table_phys_fn,
        cpu_kstack_fn,
        transit_page_table_fn,
        wakeup_fn,
        pause_fn,
    ) else {
        return -EINVAL;
    };

    unsafe {
        core::ptr::copy_nonoverlapping(
            trampoline_code_data,
            trampoline_va.cast::<u8>(),
            trampoline_code_size as usize,
        );
        let p = trampoline_va.cast::<CULong>();
        let boot_pt = boot_pt_phys();
        write_volatile(p.add(1), boot_pt);
        write_volatile(p.add(2), setup_x86_ap_addr as CULong);
        write_volatile(p.add(3), pc);
        write_volatile(p.add(4), cpu_kstack(cpuid));
        let transit = transit_pt();
        write_volatile(p.add(6), if transit == 0 { boot_pt } else { transit });
        write_volatile(boot_status_slot, 0);
        wakeup(cpuid, ap_trampoline);
        while read_volatile(boot_status_slot) == 0 {
            pause();
        }
    }
    0
}

#[inline(always)]
unsafe fn zero_bytes(addr: *mut u8, len: usize) {
    let mut i = 0usize;
    while i < len {
        unsafe {
            write_volatile(addr.add(i), 0);
        }
        i += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_context_body_result(
    ctx: *mut X86KernelContext,
    mut stack_pointer: *mut c_void,
    next_function: *mut c_void,
    stack_fn: Option<X86StackFn>,
) -> CInt {
    if ctx.is_null() || next_function.is_null() {
        return -EINVAL;
    }
    if stack_pointer.is_null() {
        let Some(stack) = stack_fn else {
            return -EINVAL;
        };
        stack_pointer = unsafe { stack() };
        if stack_pointer.is_null() {
            return -EINVAL;
        }
    }

    unsafe {
        zero_bytes(ctx.cast::<u8>(), size_of::<X86KernelContext>());
        let sp = stack_pointer.cast::<CULong>();
        let ret_slot = sp.sub(1);
        write_volatile(ret_slot, next_function as CULong);
        write_volatile(&mut (*ctx).rsp, ret_slot as CULong);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_user_process_body_result(
    ctx: *mut X86KernelContext,
    puctx: *mut *mut X86UserContext,
    stack_pointer: *mut c_void,
    new_pc: CULong,
    user_sp: CULong,
    user_cs: CULong,
    user_ds: CULong,
    rflags_if: CULong,
    enter_user_mode_addr: *mut c_void,
) -> CInt {
    if ctx.is_null() || puctx.is_null() || stack_pointer.is_null() || enter_user_mode_addr.is_null()
    {
        return -EINVAL;
    }

    let uctx_addr = (stack_pointer as usize).wrapping_sub(size_of::<X86UserContext>());
    let uctx = uctx_addr as *mut X86UserContext;
    unsafe {
        write_volatile(puctx, uctx);
        zero_bytes(uctx.cast::<u8>(), size_of::<X86UserContext>());
        write_volatile(&mut (*uctx).gpr.cs, user_cs);
        write_volatile(&mut (*uctx).gpr.rip, new_pc);
        write_volatile(&mut (*uctx).gpr.ss, user_ds);
        write_volatile(&mut (*uctx).gpr.rsp, user_sp);
        write_volatile(&mut (*uctx).gpr.rflags, rflags_if);
        write_volatile(&mut (*uctx).is_gpr_valid, 1);

        zero_bytes(ctx.cast::<u8>(), size_of::<X86KernelContext>());
        let ret_slot = (uctx_addr as *mut CULong).sub(1);
        write_volatile(ret_slot, enter_user_mode_addr as CULong);
        write_volatile(&mut (*ctx).rsp, ret_slot as CULong);
        write_volatile(&mut (*ctx).rsp0, stack_pointer as CULong);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_modify_user_context_result(
    uctx: *mut X86UserContext,
    reg: CInt,
    value: CULong,
    stack_pointer_reg: CInt,
    program_counter_reg: CInt,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }

    unsafe {
        if reg == stack_pointer_reg {
            write_volatile(&mut (*uctx).gpr.rsp, value);
            return 1;
        }
        if reg == program_counter_reg {
            write_volatile(&mut (*uctx).gpr.rip, value);
            return 1;
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_modify_user_context(
    uctx: *mut X86UserContext,
    reg: CInt,
    value: CULong,
) {
    let _ = unsafe {
        x86_modify_user_context_result(
            uctx,
            reg,
            value,
            IHK_UCR_STACK_POINTER,
            IHK_UCR_PROGRAM_COUNTER,
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn x86_lookup_user_context_body_result(
    thread_addr: *mut c_void,
    current_thread_addr: *mut c_void,
    sleep_status_mask: CInt,
    offsets: *const X86ThreadContextOffsets,
) -> *mut X86UserContext {
    if thread_addr.is_null() || offsets.is_null() {
        return null_mut();
    }

    let offsets = unsafe { &*offsets };
    let base = thread_addr as usize;
    let status = unsafe {
        read_volatile(base.wrapping_add(offsets.thread_status_offset as usize) as *const CInt)
    };
    let uctx = unsafe {
        read_volatile(
            base.wrapping_add(offsets.thread_uctx_offset as usize) as *const *mut X86UserContext
        )
    };
    if uctx.is_null() {
        return null_mut();
    }

    let gpr_valid = unsafe { read_volatile(&(*uctx).is_gpr_valid) };
    if ((status & sleep_status_mask) == 0 && thread_addr != current_thread_addr) || gpr_valid == 0 {
        return null_mut();
    }

    let sr_valid = unsafe { read_volatile(&(*uctx).is_sr_valid) };
    if sr_valid == 0 {
        let tlsblock_base = unsafe {
            read_volatile(
                base.wrapping_add(offsets.thread_tlsblock_base_offset as usize) as *const CULong,
            )
        };
        unsafe {
            write_volatile(&mut (*uctx).sr.fs_base, tlsblock_base);
            write_volatile(&mut (*uctx).sr.gs_base, 0);
            write_volatile(&mut (*uctx).sr.ds, 0);
            write_volatile(&mut (*uctx).sr.es, 0);
            write_volatile(&mut (*uctx).sr.fs, 0);
            write_volatile(&mut (*uctx).sr.gs, 0);
            write_volatile(&mut (*uctx).is_sr_valid, 1);
        }
    }

    uctx
}

#[no_mangle]
pub unsafe extern "C" fn x86_syscall_handler_publish_result(
    slot: *mut CULong,
    handler: *mut c_void,
) -> CInt {
    if slot.is_null() {
        return -EINVAL;
    }

    unsafe {
        write_volatile(slot, handler as CULong);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_page_fault_handler_publish_result(
    slot: *mut CULong,
    handler: *mut c_void,
) -> CInt {
    unsafe { x86_syscall_handler_publish_result(slot, handler) }
}

#[no_mangle]
pub extern "C" fn x86_arch_noop_body_result() -> CInt {
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_print_user_context_body_result(
    uctx: *const X86UserContext,
    log_fn: Option<X86ContextLogFn>,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    unsafe {
        let regs = &(*uctx).gpr;
        log(20, regs.cs, regs.rip, 0, 0);
        log(21, regs.rax, regs.rbx, regs.rcx, regs.rdx);
        log(22, regs.rsi, regs.rdi, regs.rsp, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_show_interrupt_context_body_result(
    uctx: *const X86UserContext,
    lock_fn: Option<X86KprintfLockFn>,
    unlock_fn: Option<X86KprintfUnlockFn>,
    log_fn: Option<X86ContextLogFn>,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(log)) = (lock_fn, unlock_fn, log_fn) else {
        return -EINVAL;
    };

    unsafe {
        let flags = lock();
        let regs = &(*uctx).gpr;
        log(1, regs.cs, regs.rip, 0, 0);
        log(2, regs.rax, regs.rbx, regs.rcx, regs.rdx);
        log(3, regs.rsi, regs.rdi, regs.rsp, regs.rbp);
        log(4, regs.r8, regs.r9, regs.r10, regs.r11);
        log(5, regs.r12, regs.r13, regs.r14, regs.r15);
        log(6, regs.cs, regs.ss, regs.rflags, regs.orig_rax);
        unlock(flags);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_show_interrupt_context(reg: *const c_void) {
    unsafe {
        x86_arch_show_interrupt_context_body_result(
            reg.cast::<X86UserContext>(),
            Some(x86_kprintf_lock_bridge),
            Some(x86_kprintf_unlock_bridge),
            Some(x86_context_line_log_bridge),
        );
    }
}

unsafe fn x86_write_panic_segment_regs(regs: *const X86UserContext, panic_regs: *mut CULong) {
    let sregs = unsafe { panic_regs.add(17).cast::<CUInt>() };
    unsafe {
        write_volatile(sregs.add(0), read_volatile(&(*regs).gpr.rflags) as CUInt);
        write_volatile(sregs.add(1), read_volatile(&(*regs).gpr.cs) as CUInt);
        write_volatile(sregs.add(2), read_volatile(&(*regs).gpr.ss) as CUInt);
        write_volatile(sregs.add(3), read_volatile(&(*regs).sr.ds) as CUInt);
        write_volatile(sregs.add(4), read_volatile(&(*regs).sr.es) as CUInt);
        write_volatile(sregs.add(5), read_volatile(&(*regs).sr.fs) as CUInt);
        write_volatile(sregs.add(6), read_volatile(&(*regs).sr.gs) as CUInt);
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_save_panic_regs_body_result(
    regs: *const X86UserContext,
    current_ctx: *const X86KernelContext,
    panic_regs: *mut CULong,
    paniced_slot: *mut CULong,
    user_end: CULong,
    enter_user_mode_addr: CULong,
    log_fn: Option<X86CpuULongLogFn>,
) -> CInt {
    if regs.is_null() || panic_regs.is_null() || paniced_slot.is_null() {
        return -EINVAL;
    }

    let rip = unsafe { read_volatile(&(*regs).gpr.rip) };
    if rip > user_end {
        unsafe {
            write_volatile(panic_regs.add(0), read_volatile(&(*regs).gpr.rax));
            write_volatile(panic_regs.add(1), read_volatile(&(*regs).gpr.rbx));
            write_volatile(panic_regs.add(2), read_volatile(&(*regs).gpr.rcx));
            write_volatile(panic_regs.add(3), read_volatile(&(*regs).gpr.rdx));
            write_volatile(panic_regs.add(4), read_volatile(&(*regs).gpr.rsi));
            write_volatile(panic_regs.add(5), read_volatile(&(*regs).gpr.rdi));
            write_volatile(panic_regs.add(6), read_volatile(&(*regs).gpr.rbp));
            write_volatile(panic_regs.add(7), read_volatile(&(*regs).gpr.rsp));
            write_volatile(panic_regs.add(8), read_volatile(&(*regs).gpr.r8));
            write_volatile(panic_regs.add(9), read_volatile(&(*regs).gpr.r9));
            write_volatile(panic_regs.add(10), read_volatile(&(*regs).gpr.r10));
            write_volatile(panic_regs.add(11), read_volatile(&(*regs).gpr.r11));
            write_volatile(panic_regs.add(12), read_volatile(&(*regs).gpr.r12));
            write_volatile(panic_regs.add(13), read_volatile(&(*regs).gpr.r13));
            write_volatile(panic_regs.add(14), read_volatile(&(*regs).gpr.r14));
            write_volatile(panic_regs.add(15), read_volatile(&(*regs).gpr.r15));
            write_volatile(panic_regs.add(16), rip);
            x86_write_panic_segment_regs(regs, panic_regs);
            write_volatile(paniced_slot, 1);
        }
        return 0;
    }

    if current_ctx.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    unsafe {
        log(15, rip);
        write_volatile(panic_regs.add(0), 0);
        write_volatile(panic_regs.add(1), read_volatile(&(*current_ctx).rbx));
        write_volatile(panic_regs.add(2), 0);
        write_volatile(panic_regs.add(3), 0);
        write_volatile(panic_regs.add(4), read_volatile(&(*current_ctx).rsi));
        write_volatile(panic_regs.add(5), read_volatile(&(*current_ctx).rdi));
        write_volatile(panic_regs.add(6), read_volatile(&(*current_ctx).rbp));
        write_volatile(panic_regs.add(7), read_volatile(&(*current_ctx).rsp));
        write_volatile(panic_regs.add(8), 0);
        write_volatile(panic_regs.add(9), 0);
        write_volatile(panic_regs.add(10), 0);
        write_volatile(panic_regs.add(11), 0);
        write_volatile(panic_regs.add(12), read_volatile(&(*regs).gpr.r12));
        write_volatile(panic_regs.add(13), read_volatile(&(*regs).gpr.r13));
        write_volatile(panic_regs.add(14), read_volatile(&(*regs).gpr.r14));
        write_volatile(panic_regs.add(15), read_volatile(&(*regs).gpr.r15));
        write_volatile(panic_regs.add(16), enter_user_mode_addr);
        x86_write_panic_segment_regs(regs, panic_regs);
        write_volatile(paniced_slot, 1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_clear_panic_body_result(paniced_slot: *mut CULong) -> CInt {
    if paniced_slot.is_null() {
        return -EINVAL;
    }

    unsafe {
        write_volatile(paniced_slot, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_clear_panic() {
    unsafe {
        let cpu = crate::x86_local::ihk_mc_get_processor_id();
        let local = crate::x86_local::get_x86_cpu_local_variable(cpu);
        write_volatile(core::ptr::addr_of_mut!((*local).paniced), 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_mcexec_v10_trace_enter_user_body_result(
    regs: *const X86UserContext,
    thread: *const c_void,
    counter: *mut CInt,
    limit: CInt,
    cpu: CInt,
    offsets: *const X86TraceEnterUserOffsets,
    log_fn: Option<X86TraceEnterUserLogFn>,
) -> CInt {
    if counter.is_null() || offsets.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };
    if unsafe { read_volatile(counter) } >= limit {
        return 0;
    }

    let mut pid = -1;
    let mut tid = -1;
    let mut status = -1;
    let offsets = unsafe { &*offsets };
    if !thread.is_null() {
        let base = thread as usize;
        unsafe {
            tid =
                read_volatile(base.wrapping_add(offsets.thread_tid_offset as usize) as *const CInt);
            status = read_volatile(
                base.wrapping_add(offsets.thread_status_offset as usize) as *const CInt
            );
            let proc = read_volatile(
                base.wrapping_add(offsets.thread_proc_offset as usize) as *const *const c_void
            );
            if !proc.is_null() {
                pid = read_volatile(
                    (proc as usize).wrapping_add(offsets.process_pid_offset as usize)
                        as *const CInt,
                );
            }
        }
    }

    let (rip, rsp, cs, ss, rflags) = if regs.is_null() {
        (0, 0, 0, 0, 0)
    } else {
        unsafe {
            (
                read_volatile(&(*regs).gpr.rip),
                read_volatile(&(*regs).gpr.rsp),
                read_volatile(&(*regs).gpr.cs),
                read_volatile(&(*regs).gpr.ss),
                read_volatile(&(*regs).gpr.rflags),
            )
        }
    };

    unsafe {
        log(cpu, pid, tid, rip, rsp, cs, ss, rflags, status);
        write_volatile(counter, read_volatile(counter) + 1);
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn x86_release_runq_lock_body_result(
    cpu_local: *mut c_void,
    runq_lock_offset: CULong,
    runq_irqstate_offset: CULong,
    unlock_fn: Option<X86RunqUnlockFn>,
) -> CInt {
    if cpu_local.is_null() {
        return -EINVAL;
    }
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    let base = cpu_local as usize;
    let lock = base.wrapping_add(runq_lock_offset as usize) as *mut c_void;
    let irqstate =
        unsafe { read_volatile(base.wrapping_add(runq_irqstate_offset as usize) as *const CULong) };
    unsafe {
        unlock(lock, irqstate);
    }
    0
}

/// Publish the kernel stack before the packed TSS RSP0 using two x86 stores.
///
/// # Safety
/// Each supplied offset must name writable eight-byte storage within the live
/// CPU-local allocation. The caller excludes concurrent stack/TSS modification
/// and retains the existing hardware/publication contract through both stores.
#[no_mangle]
pub unsafe extern "C" fn x86_set_kstack_body_result(
    cpu_local: *mut c_void,
    kernel_stack_offset: CULong,
    tss_rsp0_offset: CULong,
    stack_pointer: CULong,
) -> CInt {
    if cpu_local.is_null() {
        return -EINVAL;
    }

    let base = cpu_local as usize;
    let kernel = base.wrapping_add(kernel_stack_offset as usize);
    let tss = base.wrapping_add(tss_rsp0_offset as usize);
    // SAFETY: The caller supplies two writable eight-byte field spans. Actual
    // packed CPU-local/TSS fields need not be aligned for a Rust u64 access.
    // These x86 memory operands allow byte alignment, form no references, and
    // retain one ordered 64-bit store per field with default asm memory effects.
    // There is no additional fence, LOCK, atomicity or interrupt-state guarantee.
    unsafe {
        core::arch::asm!(
            "mov qword ptr [{kernel}], {value}",
            "mov qword ptr [{tss}], {value}",
            kernel = in(reg) kernel,
            tss = in(reg) tss,
            value = in(reg) stack_pointer,
            options(nostack, preserves_flags),
        );
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_delay_us_body_result(us: CInt, delay_fn: Option<X86DelayFn>) -> CInt {
    let Some(delay) = delay_fn else {
        return -EINVAL;
    };

    unsafe {
        delay(us);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_tick_log_body_result(
    event: CInt,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if event < 1 || event > 3 {
        return -EINVAL;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(event);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn init_tick() {
    unsafe {
        x86_tick_log_body_result(1, Some(x86_tick_log_bridge));
    }
}

#[no_mangle]
pub unsafe extern "C" fn init_delay() {
    unsafe {
        x86_tick_log_body_result(2, Some(x86_tick_log_bridge));
    }
}

#[no_mangle]
pub unsafe extern "C" fn sync_tick() {
    unsafe {
        x86_tick_log_body_result(3, Some(x86_tick_log_bridge));
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_set_special_register_result(
    reg_type: CInt,
    fs_type: CInt,
    value: CULong,
    write_fn: Option<X86MsrWriteFn>,
) -> CInt {
    if reg_type != fs_type {
        return -EINVAL;
    }
    let Some(write_msr) = write_fn else {
        return -EINVAL;
    };

    unsafe {
        write_msr(value);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_get_special_register_result(
    reg_type: CInt,
    fs_type: CInt,
    valuep: *mut CULong,
    read_fn: Option<X86MsrReadFn>,
) -> CInt {
    if reg_type != fs_type || valuep.is_null() {
        return -EINVAL;
    }
    let Some(read_msr) = read_fn else {
        return -EINVAL;
    };

    unsafe {
        write_volatile(valuep, read_msr());
    }
    0
}

unsafe extern "C" fn x86_fs_write_native(value: CULong) {
    unsafe {
        wrmsr(MSR_FS_BASE, value);
    }
}

unsafe extern "C" fn x86_fs_read_native() -> CULong {
    unsafe { rdmsr(MSR_FS_BASE) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_arch_set_special_register(reg_type: CInt, value: CULong) -> CInt {
    unsafe {
        x86_arch_set_special_register_result(
            reg_type,
            IHK_ASR_X86_FS,
            value,
            Some(x86_fs_write_native),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_arch_get_special_register(
    reg_type: CInt,
    valuep: *mut CULong,
) -> CInt {
    unsafe {
        x86_arch_get_special_register_result(
            reg_type,
            IHK_ASR_X86_FS,
            valuep,
            Some(x86_fs_read_native),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_get_interrupt_id_result(
    cpu: CInt,
    cpu_local_fn: Option<X86CpuLocalFn>,
    apic_id_offset: CULong,
) -> CInt {
    let Some(cpu_local) = cpu_local_fn else {
        return -1;
    };
    let cpu_local_addr = unsafe { cpu_local(cpu) };
    if cpu_local_addr.is_null() {
        return -1;
    }

    unsafe {
        read_volatile(
            (cpu_local_addr as usize).wrapping_add(apic_id_offset as usize) as *const CULong,
        ) as CInt
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_interrupt_cpu_result(
    cpu: CInt,
    vector: CInt,
    num_processors: CInt,
    cpu_local_fn: Option<X86CpuLocalFn>,
    apic_id_offset: CULong,
    issue_ipi_fn: Option<X86IssueIpiFn>,
    log_fn: Option<X86InterruptLogFn>,
) -> CInt {
    if cpu < 0 || cpu >= num_processors {
        if let Some(log) = log_fn {
            unsafe {
                log(1, cpu, vector);
            }
        }
        return -1;
    }
    let Some(issue_ipi) = issue_ipi_fn else {
        return -1;
    };
    let apic_id = unsafe { x86_get_interrupt_id_result(cpu, cpu_local_fn, apic_id_offset) };
    if apic_id < 0 {
        return -1;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(2, cpu, vector);
        }
    }
    unsafe {
        issue_ipi(apic_id as CULong, vector);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_lapic_timer_enable_body_result(
    clocks: CUInt,
    write_fn: Option<X86LapicWriteFn>,
) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_TIMER_INITIAL, clocks / APIC_DIVISOR);
    write(LAPIC_TIMER_DIVIDE, 3);
    write(LAPIC_TIMER, LOCAL_TIMER_VECTOR | APIC_LVT_TIMER_PERIODIC);
    0
}

#[no_mangle]
pub unsafe extern "C" fn lapic_timer_enable(clocks: CUInt) {
    let _ = x86_lapic_timer_enable_body_result(clocks, Some(x86_lapic_write_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn x86_lapic_timer_disable_body_result(
    write_fn: Option<X86LapicWriteFn>,
) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_TIMER_INITIAL, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn lapic_timer_disable() {
    let _ = x86_lapic_timer_disable_body_result(Some(x86_lapic_write_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn x86_lapic_ack_body_result(write_fn: Option<X86LapicWriteFn>) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_EOI, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn lapic_ack() {
    let _ = x86_lapic_ack_body_result(Some(x86_lapic_write_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn x86_x2apic_issue_ipi_body_result(
    apicid: CUInt,
    low: CUInt,
    mb_fn: Option<X86VoidFn>,
    disable_save_fn: Option<X86DisableSaveFn>,
    icr_write_fn: Option<X86IcrWriteFn>,
    restore_fn: Option<X86RestoreFn>,
) -> CInt {
    let (Some(mb), Some(disable_save), Some(icr_write), Some(restore)) =
        (mb_fn, disable_save_fn, icr_write_fn, restore_fn)
    else {
        return -EINVAL;
    };

    mb();
    let flags = disable_save();
    icr_write(low, apicid);
    restore(flags);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_apic_issue_ipi_body_result(
    apicid: CUInt,
    low: CUInt,
    lapic_icr_id_shift: CInt,
    disable_save_fn: Option<X86DisableSaveFn>,
    wait_idle_fn: Option<X86VoidFn>,
    icr_write_fn: Option<X86IcrWriteFn>,
    restore_fn: Option<X86RestoreFn>,
) -> CInt {
    if lapic_icr_id_shift < 0 || lapic_icr_id_shift >= 32 {
        return -EINVAL;
    }
    let (Some(disable_save), Some(wait_idle), Some(icr_write), Some(restore)) =
        (disable_save_fn, wait_idle_fn, icr_write_fn, restore_fn)
    else {
        return -EINVAL;
    };

    let flags = disable_save();
    wait_idle();
    icr_write(apicid << (lapic_icr_id_shift as u32), low);
    restore(flags);
    0
}

#[no_mangle]
pub extern "C" fn x86_x2apic_enabled_result(msr: CULong, enable_bit: CULong) -> CULong {
    msr & enable_bit
}

#[no_mangle]
pub unsafe extern "C" fn x2apic_is_enabled() -> CULong {
    x86_x2apic_enabled_result(x86_read_msr_bridge(MSR_IA32_APIC_BASE), X2APIC_ENABLE)
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_lapic_bsp_body_result(
    enabled: CULong,
    select_fn: Option<X86SelectLapicModeFn>,
) -> CInt {
    let Some(select) = select_fn else {
        return -EINVAL;
    };

    let mode = (enabled != 0) as CInt;
    select(mode);
    mode
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_lapic_body_result(
    x2apic_enabled: CInt,
    lapic_vp_slot: *mut *mut c_void,
    apic_base_msr: CInt,
    page_mask: CULong,
    page_size: CULong,
    apic_enable_bit: CULong,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
    map_fixed_fn: Option<X86MapFixedFn>,
    write_fn: Option<X86LapicWriteFn>,
) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    if x2apic_enabled == 0 {
        if lapic_vp_slot.is_null() {
            return -EINVAL;
        }
        let (Some(read_msr), Some(write_msr), Some(map_fixed)) =
            (read_msr_fn, write_msr_fn, map_fixed_fn)
        else {
            return -EINVAL;
        };

        let mut base = read_msr(apic_base_msr);
        if (*lapic_vp_slot).is_null() {
            *lapic_vp_slot = map_fixed(base & page_mask, page_size, 1);
        }
        base |= apic_enable_bit;
        write_msr(apic_base_msr, base);
    }

    write(LAPIC_SPURIOUS, 0x1ff);
    write(LAPIC_LVTPC, LOCAL_PERF_VECTOR);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_pstate_turbo_body_result(
    no_turbo: CInt,
    platform_info_msr: CInt,
    turbo_ratio_msr: CInt,
    perf_ctl_msr: CInt,
    energy_perf_bias_msr: CInt,
    running_on_kvm_fn: Option<X86RunningOnKvmFn>,
    cpuid6_fn: Option<X86Cpuid6Fn>,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
) -> CInt {
    let (Some(running_on_kvm), Some(cpuid6), Some(read_msr), Some(write_msr)) =
        (running_on_kvm_fn, cpuid6_fn, read_msr_fn, write_msr_fn)
    else {
        return -EINVAL;
    };

    if running_on_kvm() != 0 {
        return 0;
    }

    let mut eax = 0;
    let mut ecx = 0;
    cpuid6(&mut eax, &mut ecx);
    if (ecx & 0x01) == 0 {
        return 0;
    }

    let mut value = read_msr(platform_info_msr) & 0xff00;
    if (eax & (1 << 1)) != 0 {
        if no_turbo == 0 {
            value = (read_msr(turbo_ratio_msr) & 0xff) << 8;
            value &= !(1 << 32);
        } else {
            value |= 1 << 32;
        }
    }

    write_msr(perf_ctl_msr, value);
    if (ecx & (1 << 3)) != 0 {
        write_msr(energy_perf_bias_msr, 0);
    }
    0
}

/// Preserve the selected x86 CPU initialization entry and its ordered MSR callbacks.
/// The boot CPU initializes `no_turbo` before entering this serialized setup path.
#[no_mangle]
pub unsafe extern "C" fn init_pstate_and_turbo() {
    let _ = unsafe {
        x86_init_pstate_turbo_body_result(
            read_volatile(core::ptr::addr_of!(X86_NO_TURBO)),
            MSR_PLATFORM_INFO,
            MSR_NHM_TURBO_RATIO_LIMIT,
            MSR_IA32_PERF_CTL,
            MSR_IA32_ENERGY_PERF_BIAS,
            Some(x86_running_on_kvm_bridge),
            Some(x86_cpuid6_bridge),
            Some(x86_read_msr_bridge),
            Some(x86_write_msr_bridge),
        )
    };
}


#[no_mangle]
pub unsafe extern "C" fn x86_init_pat_body_result(
    boot_pat_state: *mut CULong,
    cr_pat_msr: CInt,
    cpuid_edx_fn: Option<X86CpuidEdxFn>,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if boot_pat_state.is_null() {
        return -EINVAL;
    }
    let (Some(cpuid_edx), Some(read_msr), Some(write_msr)) =
        (cpuid_edx_fn, read_msr_fn, write_msr_fn)
    else {
        return -EINVAL;
    };

    let mut edx = 0;
    cpuid_edx(1, &mut edx);
    if (edx & (1 << 16)) == 0 {
        if let Some(log) = log_fn {
            log(1);
        }
        return 0;
    }

    let pat =
        (6 << 0) | (1 << 8) | (7 << 16) | (0 << 24) | (6 << 32) | (1 << 40) | (7 << 48) | (0 << 56);

    if read_volatile(boot_pat_state) == 0 {
        write_volatile(boot_pat_state, read_msr(cr_pat_msr));
    }
    write_msr(cr_pat_msr, pat);
    if let Some(log) = log_fn {
        log(2);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_syscall_body_result(
    efer_msr: CInt,
    star_msr: CInt,
    lstar_msr: CInt,
    kernel_cs: CULong,
    user_cs: CULong,
    syscall_addr: CULong,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
) -> CInt {
    let (Some(read_msr), Some(write_msr)) = (read_msr_fn, write_msr_fn) else {
        return -EINVAL;
    };

    let efer = read_msr(efer_msr) | 1;
    write_msr(efer_msr, efer);
    write_msr(star_msr, (kernel_cs << 32) | (user_cs << 48));
    write_msr(lstar_msr, syscall_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_enable_no_execute_body_result(
    no_execute_available: CInt,
    efer_msr: CInt,
    nxe_bit: CULong,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
) -> CInt {
    if no_execute_available == 0 {
        return 0;
    }
    let (Some(read_msr), Some(write_msr)) = (read_msr_fn, write_msr_fn) else {
        return -EINVAL;
    };

    write_msr(efer_msr, read_msr(efer_msr) | nxe_bit);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_check_no_execute_body_result(
    no_execute_available_slot: *mut CInt,
    cpuid_edx_fn: Option<X86CpuidEdxFn>,
    log_fn: Option<X86CpuValueLogFn>,
    enable_ptattr_fn: Option<X86VoidFn>,
) -> CInt {
    if no_execute_available_slot.is_null() {
        return -EINVAL;
    }
    let Some(cpuid_edx) = cpuid_edx_fn else {
        return -EINVAL;
    };

    let mut edx = 0;
    cpuid_edx(0x80000001, &mut edx);
    let available = ((edx & (1 << 20)) != 0) as CInt;
    write_volatile(no_execute_available_slot, available);
    if let Some(log) = log_fn {
        log(1, available);
    }
    if available != 0 {
        let Some(enable_ptattr) = enable_ptattr_fn else {
            return -EINVAL;
        };
        enable_ptattr();
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_gettime_support_body_result(
    gettime_local_support_slot: *mut CInt,
    cpuid_edx_fn: Option<X86CpuidEdxFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if gettime_local_support_slot.is_null() {
        return -EINVAL;
    }
    let Some(cpuid_edx) = cpuid_edx_fn else {
        return -EINVAL;
    };

    let mut edx = 0;
    cpuid_edx(0x80000007, &mut edx);
    if (edx & (1 << 8)) != 0 {
        write_volatile(gettime_local_support_slot, 1);
        if let Some(log) = log_fn {
            log(3);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_cpu_body_result(
    enable_page_protection_fault_fn: Option<X86VoidFn>,
    enable_no_execute_fn: Option<X86VoidFn>,
    init_fpu_fn: Option<X86VoidFn>,
    init_lapic_fn: Option<X86VoidFn>,
    init_syscall_fn: Option<X86VoidFn>,
    init_perfctr_fn: Option<X86VoidFn>,
    init_pstate_turbo_fn: Option<X86VoidFn>,
    init_pat_fn: Option<X86VoidFn>,
) -> CInt {
    let (
        Some(enable_page_protection_fault),
        Some(enable_no_execute),
        Some(init_fpu),
        Some(init_lapic),
        Some(init_syscall),
        Some(init_perfctr),
        Some(init_pstate_turbo),
        Some(init_pat),
    ) = (
        enable_page_protection_fault_fn,
        enable_no_execute_fn,
        init_fpu_fn,
        init_lapic_fn,
        init_syscall_fn,
        init_perfctr_fn,
        init_pstate_turbo_fn,
        init_pat_fn,
    )
    else {
        return -EINVAL;
    };

    enable_page_protection_fault();
    enable_no_execute();
    init_fpu();
    init_lapic();
    init_syscall();
    init_perfctr();
    init_pstate_turbo();
    init_pat();
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_setup_phase1_body_result(
    disable_interrupt_fn: Option<X86VoidFn>,
    init_idt_fn: Option<X86VoidFn>,
    init_gdt_fn: Option<X86VoidFn>,
    init_page_table_fn: Option<X86VoidFn>,
) -> CInt {
    let (Some(disable_interrupt), Some(init_idt), Some(init_gdt), Some(init_page_table)) = (
        disable_interrupt_fn,
        init_idt_fn,
        init_gdt_fn,
        init_page_table_fn,
    ) else {
        return -EINVAL;
    };

    crate::x86_setup::early_phase(b'1');
    disable_interrupt();
    crate::x86_setup::early_phase(b'2');
    init_idt();
    crate::x86_setup::early_phase(b'3');
    init_gdt();
    crate::x86_setup::early_phase(b'4');
    init_page_table();
    crate::x86_setup::early_phase(b'5');
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_setup_phase2_body_result(
    check_no_execute_fn: Option<X86VoidFn>,
    init_lapic_bsp_fn: Option<X86VoidFn>,
    init_cpu_fn: Option<X86VoidFn>,
    init_gettime_support_fn: Option<X86VoidFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    let (Some(check_no_execute), Some(init_lapic_bsp), Some(init_cpu), Some(init_gettime_support)) = (
        check_no_execute_fn,
        init_lapic_bsp_fn,
        init_cpu_fn,
        init_gettime_support_fn,
    ) else {
        return -EINVAL;
    };

    check_no_execute();
    init_lapic_bsp();
    init_cpu();
    init_gettime_support();
    if let Some(log) = log_fn {
        log(4);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_ihk_mc_init_ap_body_result(
    trampoline_va_slot: *mut *mut c_void,
    first_page_va_slot: *mut *mut c_void,
    ap_trampoline: CULong,
    ap_trampoline_size: CULong,
    page_size: CULong,
    map_fixed_fn: Option<X86MapFixedFn>,
    get_ncpus_fn: Option<X86GetIntFn>,
    init_processors_fn: Option<X86InitProcessorsFn>,
    assign_processor_id_fn: Option<X86VoidFn>,
    init_smp_processor_fn: Option<X86VoidFn>,
    log_fn: Option<X86CpuULongLogFn>,
) -> CInt {
    if trampoline_va_slot.is_null() || first_page_va_slot.is_null() {
        return -EINVAL;
    }
    let (
        Some(map_fixed),
        Some(get_ncpus),
        Some(init_processors),
        Some(assign_processor_id),
        Some(init_smp_processor),
    ) = (
        map_fixed_fn,
        get_ncpus_fn,
        init_processors_fn,
        assign_processor_id_fn,
        init_smp_processor_fn,
    )
    else {
        return -EINVAL;
    };

    write_volatile(
        trampoline_va_slot,
        map_fixed(ap_trampoline, ap_trampoline_size, 0),
    );
    if let Some(log) = log_fn {
        log(1, ap_trampoline);
    }
    write_volatile(first_page_va_slot, map_fixed(0, page_size, 0));
    let ncpus = get_ncpus();
    if let Some(log) = log_fn {
        log(2, ncpus as CULong);
    }
    init_processors(ncpus);
    assign_processor_id();
    init_smp_processor();
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_running_on_kvm_body_result(
    signature_leaf: CULong,
    cpuid_fn: Option<X86CpuidLeafFn>,
) -> CInt {
    let Some(cpuid) = cpuid_fn else {
        return 0;
    };

    let mut eax = 0;
    let mut ebx = 0;
    let mut ecx = 0;
    let mut edx = 0;
    unsafe {
        cpuid(signature_leaf, &mut eax, &mut ebx, &mut ecx, &mut edx);
    }

    let kvm0 = u32::from_le_bytes(*b"KVMK") as CULong;
    let kvm1 = u32::from_le_bytes(*b"VMKV") as CULong;
    let kvm2 = u32::from_le_bytes(*b"M\0\0\0") as CULong;
    ((ebx == kvm0) && (ecx == kvm1) && (edx == kvm2)) as CInt
}

unsafe extern "C" fn x86_native_cpuid_leaf(
    leaf: CULong,
    eaxp: *mut CULong,
    ebxp: *mut CULong,
    ecxp: *mut CULong,
    edxp: *mut CULong,
) {
    let cpuid = core::arch::x86_64::__cpuid(leaf as u32);

    unsafe {
        if !eaxp.is_null() {
            write_volatile(eaxp, cpuid.eax as CULong);
        }
        if !ebxp.is_null() {
            write_volatile(ebxp, cpuid.ebx as CULong);
        }
        if !ecxp.is_null() {
            write_volatile(ecxp, cpuid.ecx as CULong);
        }
        if !edxp.is_null() {
            write_volatile(edxp, cpuid.edx as CULong);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn running_on_kvm() -> CInt {
    unsafe { x86_running_on_kvm_body_result(0x40000000, Some(x86_native_cpuid_leaf)) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pvclock_available_body_result(
    pvti_msr_slot: *mut CLong,
    signature_leaf: CULong,
    features_leaf: CULong,
    feature_new_bit: CInt,
    feature_old_bit: CInt,
    msr_new: CLong,
    msr_old: CLong,
    cpuid_fn: Option<X86CpuidLeafFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if pvti_msr_slot.is_null()
        || feature_new_bit < 0
        || feature_new_bit >= 63
        || feature_old_bit < 0
        || feature_old_bit >= 63
    {
        return 0;
    }
    let Some(cpuid) = cpuid_fn else {
        return 0;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(1);
        }
    }

    let mut eax = 0;
    let mut ebx = 0;
    let mut ecx = 0;
    let mut edx = 0;
    unsafe {
        cpuid(signature_leaf, &mut eax, &mut ebx, &mut ecx, &mut edx);
    }

    let kvm0 = u32::from_le_bytes(*b"KVMK") as CULong;
    let kvm1 = u32::from_le_bytes(*b"VMKV") as CULong;
    let kvm2 = u32::from_le_bytes(*b"M\0\0\0") as CULong;
    if (eax != 0 && eax < features_leaf) || ebx != kvm0 || ecx != kvm1 || edx != kvm2 {
        if let Some(log) = log_fn {
            unsafe {
                log(2);
            }
        }
        return 0;
    }

    unsafe {
        cpuid(features_leaf, &mut eax, &mut ebx, &mut ecx, &mut edx);
    }

    if (eax & (1 << (feature_new_bit as u32))) != 0 {
        unsafe {
            write_volatile(pvti_msr_slot, msr_new);
        }
        if let Some(log) = log_fn {
            unsafe {
                log(3);
            }
        }
        return 1;
    }

    if (eax & (1 << (feature_old_bit as u32))) != 0 {
        unsafe {
            write_volatile(pvti_msr_slot, msr_old);
        }
        if let Some(log) = log_fn {
            unsafe {
                log(4);
            }
        }
        return 1;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(5);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_setup_pvclock_body_result(
    pvti_slot: *mut *mut c_void,
    pvti_npages_slot: *mut CInt,
    num_processors: CInt,
    pvti_entry_size: usize,
    page_size: CULong,
    page_p2align: CInt,
    alloc_flag: CULong,
    pg_kernel: CInt,
    file: *mut i8,
    line: CInt,
    available_fn: Option<X86GetIntFn>,
    alloc_fn: Option<X86AllocAlignedPagesNodeFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if pvti_slot.is_null()
        || pvti_npages_slot.is_null()
        || num_processors < 0
        || pvti_entry_size == 0
        || page_size == 0
    {
        return -EINVAL;
    }
    let Some(available) = available_fn else {
        return -EINVAL;
    };
    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(6);
        }
    }
    if unsafe { available() } == 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(7);
            }
        }
        return 0;
    }

    let page_size_usize = page_size as usize;
    if page_size_usize as CULong != page_size {
        return -EINVAL;
    }
    let size = match (num_processors as usize).checked_mul(pvti_entry_size) {
        Some(size) => size,
        None => return -EINVAL,
    };
    let rounded = match size.checked_add(page_size_usize - 1) {
        Some(value) => value,
        None => return -EINVAL,
    };
    let npages = rounded / page_size_usize;
    if npages > CInt::MAX as usize {
        return -EINVAL;
    }
    unsafe {
        write_volatile(pvti_npages_slot, npages as CInt);
    }

    let pages = unsafe {
        alloc(
            npages as CInt,
            page_p2align,
            alloc_flag,
            -1,
            pg_kernel,
            CULong::MAX,
            file,
            line,
        )
    };
    unsafe {
        write_volatile(pvti_slot, pages);
    }
    if pages.is_null() {
        if let Some(log) = log_fn {
            unsafe {
                log(8);
            }
        }
        return -ENOMEM;
    }

    if let Some(zero_len) = page_size_usize.checked_mul(npages) {
        unsafe {
            core::ptr::write_bytes(pages.cast::<u8>(), 0, zero_len);
        }
    } else {
        return -EINVAL;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(9);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_start_pvclock_body_result(
    pvti: *mut c_void,
    pvti_msr: CLong,
    pvti_entry_size: usize,
    enable_bit: CULong,
    current_cpu_fn: Option<X86GetIntFn>,
    virt_to_phys_fn: Option<X86VirtToPhysFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if let Some(log) = log_fn {
        unsafe {
            log(10);
        }
    }
    if pvti.is_null() {
        if let Some(log) = log_fn {
            unsafe {
                log(11);
            }
        }
        return 0;
    }
    if pvti_entry_size == 0 {
        return -EINVAL;
    }
    let Some(current_cpu) = current_cpu_fn else {
        return -EINVAL;
    };
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return -EINVAL;
    };
    let Some(write_msr) = write_msr_fn else {
        return -EINVAL;
    };

    let cpu = unsafe { current_cpu() };
    if cpu < 0 {
        return -EINVAL;
    }
    let Some(offset) = (cpu as usize).checked_mul(pvti_entry_size) else {
        return -EINVAL;
    };
    let entry = unsafe { pvti.cast::<u8>().add(offset).cast::<c_void>() };
    let phys = unsafe { virt_to_phys(entry) };
    unsafe {
        write_msr(pvti_msr as CInt, phys | enable_bit);
    }

    if let Some(log) = log_fn {
        unsafe {
            log(12);
        }
    }
    0
}

unsafe extern "C" fn x86_pvclock_available_bridge() -> CInt {
    unsafe {
        x86_pvclock_available_body_result(
            core::ptr::addr_of_mut!(X86_PVTI_MSR),
            KVM_CPUID_SIGNATURE,
            KVM_CPUID_FEATURES,
            KVM_FEATURE_CLOCKSOURCE2,
            KVM_FEATURE_CLOCKSOURCE,
            MSR_KVM_SYSTEM_TIME_NEW,
            MSR_KVM_SYSTEM_TIME,
            Some(x86_cpuid_leaf_bridge),
            Some(x86_pvclock_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_setup_pvclock() -> CInt {
    unsafe {
        x86_arch_setup_pvclock_body_result(
            core::ptr::addr_of_mut!(X86_PVTI).cast::<*mut c_void>(),
            core::ptr::addr_of_mut!(X86_PVTI_NPAGES),
            crate::ap::num_processors,
            size_of::<PvclockVsyscallTimeInfo>(),
            PAGE_SIZE,
            PAGE_P2ALIGN,
            IHK_MC_AP_NOWAIT,
            IHK_MC_PG_KERNEL,
            CPU_FILE.as_ptr().cast::<i8>() as *mut i8,
            0,
            Some(x86_pvclock_available_bridge),
            Some(x86_alloc_aligned_pages_node_bridge),
            Some(x86_pvclock_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_start_pvclock() {
    unsafe {
        x86_arch_start_pvclock_body_result(
            X86_PVTI.cast::<c_void>(),
            X86_PVTI_MSR,
            size_of::<PvclockVsyscallTimeInfo>(),
            KVM_SYSTEM_TIME_ENABLE,
            Some(x86_current_cpu_bridge),
            Some(x86_virt_to_phys_bridge),
            Some(x86_write_msr_bridge),
            Some(x86_pvclock_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_show_stack_body_result(
    mut sp: *mut CULong,
    lower_bound: CULong,
    upper_bound: CULong,
    log_fn: Option<X86StackFrameLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    loop {
        let sp_addr = sp as CULong;
        if sp_addr < lower_bound || sp_addr >= upper_bound {
            break;
        }

        let fp = unsafe { *sp };
        let ip = unsafe { *sp.add(1) };
        unsafe {
            log(ip, sp_addr, fp);
        }
        sp = fp as *mut CULong;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_print_pre_interrupt_stack_body_result(
    regs: *const u8,
    error_offset: CULong,
    rsp_offset: CULong,
    rip_offset: CULong,
    pf_user: CULong,
    scan_window: CULong,
    log_fn: Option<X86CpuLogFn>,
    print_stack_fn: Option<X86PrintStackFn>,
) -> CInt {
    if regs.is_null() {
        return -EINVAL;
    }
    let Some(print_stack) = print_stack_fn else {
        return -EINVAL;
    };

    let error = unsafe { *(regs.wrapping_add(error_offset as usize).cast::<CULong>()) };
    if (error & pf_user) != 0 {
        return 0;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(13);
        }
    }

    let mut rbp =
        unsafe { *(regs.wrapping_add(rsp_offset as usize).cast::<CULong>()) } as *mut CULong;
    loop {
        let rbp_addr = rbp as CULong;
        let next = unsafe { *rbp };
        if rbp_addr <= next && rbp_addr.wrapping_add(scan_window) >= next {
            break;
        }
        rbp = rbp.wrapping_add(1);
    }

    let first = unsafe { *(regs.wrapping_add(rip_offset as usize).cast::<CULong>()) };
    unsafe {
        print_stack(rbp.cast::<c_void>(), first);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_print_pre_interrupt_stack(regs: *const X86BasicRegs) {
    unsafe {
        x86_arch_print_pre_interrupt_stack_body_result(
            regs.cast::<u8>(),
            offset_of!(X86BasicRegs, orig_rax) as CULong,
            offset_of!(X86BasicRegs, rsp) as CULong,
            offset_of!(X86BasicRegs, rip) as CULong,
            PF_USER,
            PRE_INTERRUPT_STACK_SCAN_WINDOW,
            Some(x86_pvclock_log_bridge),
            Some(x86_print_stack_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_print_stack_body_result(
    rbp: *mut c_void,
    log_fn: Option<X86CpuLogFn>,
    print_stack_fn: Option<X86PrintStackFn>,
) -> CInt {
    let Some(print_stack) = print_stack_fn else {
        return -EINVAL;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(14);
        }
    }
    unsafe {
        print_stack(rbp, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_print_stack() {
    let rbp: *mut c_void;
    unsafe {
        core::arch::asm!("mov {}, rbp", out(reg) rbp, options(nomem, nostack, preserves_flags));
        x86_arch_print_stack_body_result(
            rbp,
            Some(x86_pvclock_log_bridge),
            Some(x86_print_stack_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_arch_cpu_read_write_register_body_result(
    desc: *mut u8,
    op: CInt,
    read_op: CInt,
    write_op: CInt,
    addr_offset: usize,
    val_offset: usize,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
) -> CInt {
    if op == read_op {
        if desc.is_null() {
            return -EINVAL;
        }
        let Some(read_msr) = read_msr_fn else {
            return -EINVAL;
        };
        let addr = read_volatile(desc.add(addr_offset).cast::<CULong>());
        write_volatile(
            desc.add(val_offset).cast::<CULong>(),
            read_msr(addr as CInt),
        );
        return 0;
    }

    if op == write_op {
        if desc.is_null() {
            return -EINVAL;
        }
        let Some(write_msr) = write_msr_fn else {
            return -EINVAL;
        };
        let addr = read_volatile(desc.add(addr_offset).cast::<CULong>());
        let value = read_volatile(desc.add(val_offset).cast::<CULong>());
        write_msr(addr as CInt, value);
        return 0;
    }

    -1
}

unsafe extern "C" fn x86_read_msr_reg_native(index: CInt) -> CULong {
    unsafe { rdmsr(index as CUInt) }
}

unsafe extern "C" fn x86_write_msr_reg_native(index: CInt, value: CULong) {
    unsafe {
        wrmsr(index as CUInt, value);
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_cpu_read_write_register(
    desc: *mut IhkOsCpuRegister,
    op: CInt,
) -> CInt {
    unsafe {
        x86_arch_cpu_read_write_register_body_result(
            desc.cast::<u8>(),
            op,
            MCCTRL_OS_CPU_READ_REGISTER,
            MCCTRL_OS_CPU_WRITE_REGISTER,
            0,
            size_of::<CULong>(),
            Some(x86_read_msr_reg_native),
            Some(x86_write_msr_reg_native),
        )
    }
}

// Matches arch/x86_64/kernel/syscall.c's DB6/DB7 reserved-set constants.
const DB6_RESERVED_SET: CULong = 0xffff_0ff0;
const DB7_RESERVED_SET: CULong = 0x400;

trait DebugRegisterWriter {
    /// Caller provides CPU-local privileged execution with debug traps disabled.
    unsafe fn write<const REG: u8>(&mut self, value: CULong);
}

struct HardwareDebugRegisterWriter;

impl DebugRegisterWriter for HardwareDebugRegisterWriter {
    #[inline(always)]
    unsafe fn write<const REG: u8>(&mut self, value: CULong) {
        // Side-effecting asm, with a compiler memory barrier and no flag promise.
        // Each monomorphized call writes only its named register. Never DR4/DR5.
        match REG {
            0 => unsafe { core::arch::asm!("mov dr0, {value}", value = in(reg) value, options(nostack)) },
            1 => unsafe { core::arch::asm!("mov dr1, {value}", value = in(reg) value, options(nostack)) },
            2 => unsafe { core::arch::asm!("mov dr2, {value}", value = in(reg) value, options(nostack)) },
            3 => unsafe { core::arch::asm!("mov dr3, {value}", value = in(reg) value, options(nostack)) },
            6 => unsafe { core::arch::asm!("mov dr6, {value}", value = in(reg) value, options(nostack)) },
            7 => unsafe { core::arch::asm!("mov dr7, {value}", value = in(reg) value, options(nostack)) },
            _ => unreachable!(),
        }
    }
}

#[inline(always)]
unsafe fn clear_debugreg_body<W: DebugRegisterWriter>(writer: &mut W) {
    unsafe {
        writer.write::<0>(0);
        writer.write::<1>(0);
        writer.write::<2>(0);
        writer.write::<3>(0);
        writer.write::<6>(DB6_RESERVED_SET);
        writer.write::<7>(DB7_RESERVED_SET);
    }
}

/// Clear this CPU's debug state using the existing scheduler/ptrace contract.
/// The caller must run at kernel privilege on the pinned CPU, with the existing
/// debug exception and scheduler exclusion preconditions. This preserves the
/// original register order and values; it does not change DR7.GD handling.
#[no_mangle]
pub unsafe extern "C" fn clear_debugreg() {
    unsafe { clear_debugreg_body(&mut HardwareDebugRegisterWriter) };
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

#[inline(always)]
unsafe fn save_debugreg_body<R: DebugRegisterReader>(debugreg: *mut CULong, reader: &mut R) {
    unsafe {
        debugreg.add(0).write(reader.read::<0>());
        debugreg.add(1).write(reader.read::<1>());
        debugreg.add(2).write(reader.read::<2>());
        debugreg.add(3).write(reader.read::<3>());
        // The C chained assignment stores slot 5 then slot 4, both before DR6.
        debugreg.add(5).write(0);
        debugreg.add(4).write(0);
        debugreg.add(6).write(reader.read::<6>());
        debugreg.add(7).write(reader.read::<7>());
    }
}

/// Save this CPU's debug state through the existing scheduler/ptrace ABI.
/// debugreg must be aligned, writable and live for eight CULong elements under
/// the caller's existing exclusion; no Rust reference or ownership is created.
/// Kernel privilege, CPU pinning and debug exception preconditions are unchanged.
/// Slots 4 and 5 are zeroed without touching DR4/DR5. DR7.GD handling is unchanged.
#[no_mangle]
pub unsafe extern "C" fn save_debugreg(debugreg: *mut CULong) {
    unsafe { save_debugreg_body(debugreg, &mut HardwareDebugRegisterReader) };
}

#[inline(always)]
unsafe fn restore_debugreg_body<W: DebugRegisterWriter>(debugreg: *mut CULong, writer: &mut W) {
    unsafe {
        writer.write::<0>(debugreg.add(0).read());
        writer.write::<1>(debugreg.add(1).read());
        writer.write::<2>(debugreg.add(2).read());
        writer.write::<3>(debugreg.add(3).read());
        writer.write::<6>(debugreg.add(6).read());
        writer.write::<7>(debugreg.add(7).read());
    }
}

/// Restore this CPU's debug state using the existing scheduler contract.
/// The caller supplies a live aligned eight-element unsigned-long buffer and
/// kernel privilege on the pinned CPU with existing debug/scheduler exclusion.
/// Slots 4/5 are ignored; this preserves DR order and existing DR7.GD handling.
#[no_mangle]
pub unsafe extern "C" fn restore_debugreg(debugreg: *mut CULong) {
    unsafe { restore_debugreg_body(debugreg, &mut HardwareDebugRegisterWriter) };
}

// Use the existing dynamic-debug descriptor ABI; flags start disabled as in C.
#[used]
#[link_section = "__verbose"]
static mut RELEASE_FP_REGS_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"release_fp_regs\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

extern "C" {
    fn _ihk_mc_free_pages(
        ptr: *mut c_void, npages: CInt, is_user: CInt, file: *mut i8, line: CInt,
    );
}

// This field is consumed directly. The production C assertion is also required.
const _: () = assert!(offset_of!(Thread, fp_regs) == 4784);

/// Release an exclusively owned thread's extended-state allocation.
///
/// `thread` must be valid, writable and exclusively owned through the call,
/// including the allocator/debug callbacks. Its non-null state buffer must be
/// the matching allocation for the boot-stable XSAVE size and kernel class.
/// Free must finish before the slot is cleared; no reentrant release is allowed.
/// A null buffer is already released. A null thread violates the original ABI.
#[no_mangle]
pub unsafe extern "C" fn release_fp_regs(thread: *mut Thread) {
    if unsafe { (*thread).fp_regs.is_null() } {
        return;
    }
    let size = unsafe { x86_xsave_size_bridge() };
    // PAGE_SIZE is unsigned long in C: preserve its unsigned addition/shift.
    let pages = ((size as CULong).wrapping_add(PAGE_SIZE - 1) >> 12) as CInt;
    let flags = unsafe {
        read_volatile(core::ptr::addr_of!(RELEASE_FP_REGS_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe { kprintf(b"release_fp_regs: pages=%d\n\0".as_ptr().cast(), pages) };
    }
    unsafe {
        _ihk_mc_free_pages(
            (*thread).fp_regs, pages, IHK_MC_PG_KERNEL,
            concat!(file!(), "\0").as_ptr().cast::<i8>() as *mut i8,
            line!() as CInt,
        );
        (*thread).fp_regs = null_mut();
    }
}


/// Preserve the existing three unsigned-long CPU diagnostics through Rust kprintf.
/// Values are forwarded by value; case 15 is a pointer-format argument only and
/// is never dereferenced. Unknown events perform no call; kprintf results remain
/// ignored exactly as in the C callback.
#[no_mangle]
pub unsafe extern "C" fn x86_cpu_ulong_log_bridge(event: CInt, value: CULong) {
    match event {
        1 => unsafe {
            kprintf(b"Trampoline area: 0x%lx \n\0".as_ptr().cast(), value);
        },
        2 => unsafe {
            kprintf(b"# of cpus : %lu\n\0".as_ptr().cast(), value);
        },
        15 => unsafe {
            kprintf(
                b"arch_save_panic_regs: in user-space: %p\n\0".as_ptr().cast(),
                value as *mut c_void,
            );
        },
        _ => {},
    }
}

/// Preserve complete context diagnostics using the existing Rust print providers.
/// The caller owns any outer print lock. Events 1..6 use __kprintf without
/// acquiring that lock again; 20..22 retain the original kprintf calls. All
/// arguments are integer values, no context pointer or callback is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_context_line_log_bridge(
    event: CInt, a: CULong, b: CULong, c: CULong, d: CULong,
) {
    match event {
        1 => unsafe {
            __kprintf(b"CS:RIP = %4lx:%16lx\n\0".as_ptr().cast(), a, b);
        },
        2 => unsafe {
            __kprintf(b"             RAX              RBX              RCX              RDX\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        3 => unsafe {
            __kprintf(b"             RSI              RDI              RSP              RBP\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        4 => unsafe {
            __kprintf(b"              R8               R9              R10              R11\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        5 => unsafe {
            __kprintf(b"             R12              R13              R14              R15\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        6 => unsafe {
            __kprintf(b"              CS               SS           RFLAGS            ERROR\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        20 => unsafe {
            kprintf(b"CS:RIP = %04lx:%16lx\n\0".as_ptr().cast(), a, b);
        },
        21 => unsafe {
            kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        22 => unsafe {
            kprintf(b"%16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c);
        },
        _ => {},
    }
}


/// Build the existing single addr2line stack diagnostic with existing Rust
/// snprintf and unlocked-print providers. The caller supplies the same live
/// two-word C stack frames; no frame/context or local-buffer pointer is retained.
/// Frame reads stay separated by snprintf as in C so a provider may affect the
/// next-link word before that word is read.
#[no_mangle]
pub unsafe extern "C" fn __print_stack(mut rbp: *mut CULong, first: CULong) {
    // Exact existing C STACK_BUF_LEN: 1024-sizeof("[  0]: ").
    const BUF_LEN: usize = 1024 - b"[  0]: \0".len();
    let mut buf = [0i8; BUF_LEN];
    let out = buf.as_mut_ptr();
    let mut len = unsafe {
        snprintf(
            out, BUF_LEN,
            b"addr2line -e smp-x86/kernel/mckernel.img -fpia\0".as_ptr().cast(),
        )
    } as usize;
    if first != 0 {
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), first,
            )
        } as usize);
    }
    while (rbp as CULong) > 0xffff880000000000
        && BUF_LEN.wrapping_sub(len) > b" 0x0123456789abcdef\0".len()
    {
        let ip = unsafe { rbp.add(1).read() };
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), ip,
            )
        } as usize);
        rbp = unsafe { rbp.read() } as *mut CULong;
    }
    unsafe { __kprintf(b"%s\n\0".as_ptr().cast(), out); }
}


/// Preserve the complete existing NMI frame rewrite. The caller owns a live,
/// aligned writable span of at least 27 C unsigned-long words. This forward
/// overlapping copy and the final five fields exactly match the C producer;
/// the supplied function is stored as a return address and is never invoked.
#[no_mangle]
pub unsafe extern "C" fn mod_nmi_ctx(
    nmi_ctx: *mut c_void,
    func: Option<unsafe extern "C" fn()>,
) {
    let flags: CULong;
    // Same pushfq/pop read used by existing cpu_interrupt_disabled. Default
    // memory/flags clobbers retain the original C "memory","cc" barrier.
    unsafe { core::arch::asm!("pushfq", "pop {flags}", flags = lateout(reg) flags); }
    let words = nmi_ctx.cast::<CULong>();
    let mut i = 0usize;
    while i < 22 {
        let value = unsafe { core::ptr::read_volatile(words.add(i + 5)) };
        unsafe { core::ptr::write_volatile(words.add(i), value); }
        i += 1;
    }
    let return_address = func.map_or(0, |entry| entry as CULong);
    unsafe {
        words.add(22).write(return_address);
        words.add(23).write(0x20);
        // Actual registers.h RFLAGS_IF=(1<<9); same mask is already used by
        // existing Rust cpu_interrupt_disabled. No IRQ state is changed here.
        words.add(24).write(flags & !(1 << 9));
        words.add(25).write(words.add(27) as CULong);
        words.add(26).write(0x28);
    }
}

/// Complete interrupt-return orchestration for the caller-owned context.
///
/// The classifier and callbacks retain their original contract. In particular,
/// interrupt enable precedes pending-signal and reschedule handling. No context
/// pointer or callback state is retained, and no new null/error policy is added.
#[no_mangle]
pub unsafe extern "C" fn interrupt_exit(regs: *mut X86UserContext) {
    unsafe {
        if interrupt_from_user(regs.cast::<c_void>()) != 0 {
            x86_interrupt_exit_enable_interrupt();
            check_sig_pending();
            check_need_resched();
            check_signal(0, regs.cast::<c_void>(), -1);
        }
    }
}

unsafe extern "C" {
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

unsafe extern "C" {
    // Existing providers and actual selected C data, no new runtime C getter.
    #[link_name = "x86_set_warm_reset"]
    fn x86_wakeup_set_warm_reset(ip: CULong, first_page: *mut i8);
    #[link_name = "x86_issue_ipi"]
    static mut X86_WAKEUP_ISSUE_IPI: unsafe extern "C" fn(CUInt, CUInt);
    #[link_name = "x86_wakeup_lapic_write_slot"]
    static X86_WAKEUP_LAPIC_WRITE_SLOT: *const unsafe extern "C" fn(CInt, CUInt);
    #[link_name = "x86_wakeup_lapic_read_slot"]
    static X86_WAKEUP_LAPIC_READ_SLOT: *const unsafe extern "C" fn(CInt) -> CUInt;
    #[link_name = "x86_wakeup_wait_slot"]
    static X86_WAKEUP_WAIT_SLOT: *const unsafe extern "C" fn();
    #[link_name = "x86_wakeup_first_page_slot"]
    static X86_WAKEUP_FIRST_PAGE_SLOT: *const *mut i8;
    #[link_name = "x86_wakeup_boot_status_slot"]
    static X86_WAKEUP_BOOT_STATUS_SLOT: *const CInt;
    #[link_name = "x86_wakeup_constants"]
    static X86_WAKEUP_CONSTANTS: [CUInt; 5];
}

// Complete existing INIT/SIPI orchestration; no new AP startup or error policy.
// Existing C macro values come from the typed immutable data witness. Existing
// callback slots remain owned/configured by APIC initialization. Each indirect
// call reloads its slot, preserving the original expression/callback order.
#[export_name = "__x86_wakeup"]
pub unsafe extern "C" fn x86_wakeup(apicid: CInt, ip: CULong) {
    unsafe {
        let esr = X86_WAKEUP_CONSTANTS[0] as CInt;
        let level = X86_WAKEUP_CONSTANTS[1];
        let assert = X86_WAKEUP_CONSTANTS[2];
        let init = X86_WAKEUP_CONSTANTS[3];
        let startup = X86_WAKEUP_CONSTANTS[4];

        let first_page = core::ptr::read_volatile(X86_WAKEUP_FIRST_PAGE_SLOT);
        x86_wakeup_set_warm_reset(ip, first_page);

        core::ptr::read_volatile(X86_WAKEUP_LAPIC_WRITE_SLOT)(esr, 0);
        let _ = core::ptr::read_volatile(X86_WAKEUP_LAPIC_READ_SLOT)(esr);
        core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
            apicid as CUInt, level | assert | init,
        );
        core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
            apicid as CUInt, level | init,
        );
        core::ptr::read_volatile(X86_WAKEUP_WAIT_SLOT)();

        for _ in 0..3 {
            let _ = core::ptr::read_volatile(X86_WAKEUP_LAPIC_READ_SLOT)(esr);
            // In C, ip promotes the OR to unsigned long, then the existing
            // callback's unsigned-int parameter truncates it to 32 bits.
            core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
                apicid as CUInt, ((startup as CULong) | (ip >> 12)) as CUInt,
            );
            core::ptr::read_volatile(X86_WAKEUP_WAIT_SLOT)();
            arch_delay(200);
            if core::ptr::read_volatile(X86_WAKEUP_BOOT_STATUS_SLOT) != 0 {
                break;
            }
        }
    }
}

// Complete main IRQ port. All imports name EXISTING selected providers. No new
// C wrapper/getter or generic platform behavior is introduced.
unsafe extern "C" {
    #[link_name="get_this_cpu_local_var"]
    fn x86_main_local() -> *mut crate::abi::CpuLocalVar;
    #[link_name="interrupt_from_user"]
    fn x86_main_from_user(regs:*mut c_void) -> CInt;
    #[link_name="lapic_ack"] fn x86_main_ack();
    #[link_name="set_cputime"] fn x86_main_cputime(mode:CUInt);
    #[link_name="ihk_mc_get_processor_id"] fn x86_main_cpu() -> CInt;
    #[link_name="set_signal"]
    fn x86_main_signal(sig:CInt,regs:*mut c_void,info:*mut crate::abi::SigInfo);
    #[link_name="arch_show_interrupt_context"] fn x86_main_context(regs:*const c_void);
    #[link_name="panic"] fn x86_main_panic(message:*const i8) -> !;
    #[link_name="__ihk_mc_spinlock_lock"]
    fn x86_main_lock(lock:*mut crate::abi::IhkSpinlock) -> CULong;
    #[link_name="__ihk_mc_spinlock_unlock"]
    fn x86_main_unlock(lock:*mut crate::abi::IhkSpinlock,flags:CULong);
    #[link_name="rdtsc"] fn x86_main_rdtsc() -> CULong;
    #[link_name="do_backlog"] fn x86_main_backlog();
    #[link_name="rdmsr"] fn x86_main_rdmsr(index:CUInt) -> CULong;
    #[link_name="wrmsr"] fn x86_main_wrmsr(index:CUInt,value:CULong);
    #[link_name="tlb_flush_handler"] fn x86_main_tlb(vector:CInt);
    #[link_name="smp_func_call_handler"] fn x86_main_smp();
    #[link_name="show_context_stack"] fn x86_main_stack(rbp:*mut CULong);
    #[link_name="interrupt_exit"] fn x86_main_exit(regs:*mut X86UserContext);
    #[link_name="schedule"] fn x86_main_schedule();
    static mut x86_main_irq_debug:[crate::debug::Ddebug;2];
    static x86_main_irq_constants:[CULong;23];
    static x86_main_irq_handler_layout:[CULong;9];
    static mut handlers:[crate::abi::AbiListHead;224];
}

// Original function-local C int, initial zero and same bounded publication point.
// This deliberately adds no atomic protocol or cross-CPU ownership policy.
static mut X86_MAIN_EXCEPTION_LOGS:CInt=0;

/// Complete original IRQ transaction over the caller-owned live frame/current
/// CPU. Existing entry IRQ/preemption exclusion and handler/fd lifetimes remain
/// caller obligations. In particular a selected mckfd must remain live after
/// its lock is released, through all later field reads/set_signal; this is the
/// original C contract, not a new reference acquisition or lifetime proof.
///
/// Handler layout is data from the REAL C type. No Rust repr(C) model is added.
/// The private source cannot be integrated before real C/Rust size/alignment/
/// callback/field ABI witnesses and independent lifetime/order review pass.
#[no_mangle]
pub unsafe extern "C" fn handle_interrupt(vector:CInt,regs:*mut X86UserContext) {
    unsafe {
        let v=x86_main_local();
        let from_user=x86_main_from_user(regs.cast());
        x86_main_ack();
        let nesting=core::ptr::addr_of_mut!((*v).in_interrupt);
        nesting.write(nesting.read().wrapping_add(1));
        x86_main_cputime(x86_main_irq_constants[if from_user!=0 {0}else{1}] as CUInt);
        if (read_volatile(core::ptr::addr_of!(x86_main_irq_debug[0].line_flags))>>24)!=0 {
            let rip=core::ptr::addr_of!((*regs).gpr.rip).read();
            let cpu=x86_main_cpu();
            kprintf(b"CPU[%d] got interrupt, vector: %d, RIP: 0x%lX\n\0".as_ptr().cast(),cpu,vector,rip);
        }
        if vector<0 || vector>255 {
            x86_main_panic(b"Invalid interrupt vector.\0".as_ptr().cast());
        } else if vector<32 {
            if from_user!=0 && read_volatile(core::ptr::addr_of!(X86_MAIN_EXCEPTION_LOGS))<32 {
                let thread=core::ptr::addr_of!((*x86_main_local()).current).read();
                let (pid,tid)=if thread.is_null(){(-1,-1)}else{
                    let proc=core::ptr::addr_of!((*thread).proc).read();
                    (if proc.is_null(){-1}else{core::ptr::addr_of!((*proc).pid).read()},
                     core::ptr::addr_of!((*thread).tid).read())
                };
                let rip=core::ptr::addr_of!((*regs).gpr.rip).read();
                let rsp=core::ptr::addr_of!((*regs).gpr.rsp).read();
                let error=core::ptr::addr_of!((*regs).gpr.orig_rax).read();
                let flags=core::ptr::addr_of!((*regs).gpr.rflags).read();
                let cpu=x86_main_cpu();
                kprintf(b"mcexec_v10: exception cpu=%d vector=%d pid=%d tid=%d rip=0x%lx sp=0x%lx error=0x%lx rflags=0x%lx\n\0".as_ptr().cast(),cpu,vector,pid,tid,rip,rsp,error,flags);
                let count=read_volatile(core::ptr::addr_of!(X86_MAIN_EXCEPTION_LOGS));
                write_volatile(core::ptr::addr_of_mut!(X86_MAIN_EXCEPTION_LOGS),count.wrapping_add(1));
            }
            let mut storage=core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
            let info=storage.as_mut_ptr();
            match vector {
                0|6|17 => {
                    core::ptr::write_bytes(info.cast::<u8>(),0,size_of::<crate::abi::SigInfo>());
                    let (signal,code)=match vector {
                        0=>(x86_main_irq_constants[14],x86_main_irq_constants[15]),
                        6=>(x86_main_irq_constants[17],x86_main_irq_constants[18]),
                        _=>(x86_main_irq_constants[19],x86_main_irq_constants[20]),
                    };
                    core::ptr::addr_of_mut!((*info).si_signo).write(signal as CInt);
                    core::ptr::addr_of_mut!((*info).si_code).write(code as CInt);
                    if vector!=17 {
                        let fault=core::ptr::addr_of_mut!((*info).sifields.sigfault).cast::<crate::abi::SigInfoFault>();
                        core::ptr::addr_of_mut!((*fault).si_addr).write(core::ptr::addr_of!((*regs).gpr.rip).read() as *mut c_void);
                    }
                    x86_main_signal(signal as CInt,regs.cast(),info);
                },
                9|16|19=>x86_main_signal(x86_main_irq_constants[14] as CInt,regs.cast(),core::ptr::null_mut()),
                4|5|10=>x86_main_signal(x86_main_irq_constants[16] as CInt,regs.cast(),core::ptr::null_mut()),
                11|12=>x86_main_signal(x86_main_irq_constants[19] as CInt,regs.cast(),core::ptr::null_mut()),
                _=>{
                    let flags=core::ptr::addr_of!((*regs).gpr.rflags).read();
                    let cs=core::ptr::addr_of!((*regs).gpr.cs).read();
                    let rip=core::ptr::addr_of!((*regs).gpr.rip).read();
                    kprintf(b"Exception %d, rflags: 0x%lX CS: 0x%lX, RIP: 0x%lX\n\0".as_ptr().cast(),vector,flags,cs,rip);
                    x86_main_context(regs.cast());
                    x86_main_panic(b"Unhandled exception\0".as_ptr().cast());
                },
            }
        } else if vector==x86_main_irq_constants[6] as CInt {
            let lock=core::ptr::addr_of_mut!((*v).runq_lock);
            let irq=x86_main_lock(lock);
            let flags=core::ptr::addr_of_mut!((*v).flags);
            flags.write(flags.read()|(x86_main_irq_constants[4] as u32));
            x86_main_unlock(lock,irq);
            if (read_volatile(core::ptr::addr_of!(x86_main_irq_debug[1].line_flags))>>24)!=0 {
                let tick=x86_main_rdtsc();
                kprintf(b"timer[%lu]: CPU_FLAG_NEED_RESCHED \n\0".as_ptr().cast(),tick);
            }
            x86_main_backlog();
        } else if vector==x86_main_irq_constants[7] as CInt {
            let thread=core::ptr::addr_of!((*x86_main_local()).current).read();
            let proc=core::ptr::addr_of!((*thread).proc).read();
            x86_lapic_write_bridge(x86_main_irq_constants[8] as CInt,x86_main_irq_constants[7] as CUInt);
            let value=x86_main_rdmsr(x86_main_irq_constants[9] as CUInt);
            x86_main_wrmsr(x86_main_irq_constants[10] as CUInt,value);
            x86_main_wrmsr(x86_main_irq_constants[10] as CUInt,0);
            let lock=core::ptr::addr_of_mut!((*proc).mckfd_lock);
            let irq=x86_main_lock(lock);
            let mut fd=core::ptr::addr_of!((*proc).mckfd).read().cast::<crate::abi::Mckfd>();
            while !fd.is_null() {
                // Actual GCC9 C sig_no is this existing signed32 slot12.
                // Real C/Rust equality witness is REQUIRED; no new ABI field.
                if core::ptr::addr_of!((*fd).padding).read()>0 {break;}
                fd=core::ptr::addr_of!((*fd).next).read();
            }
            x86_main_unlock(lock,irq);
            if !fd.is_null() {
                // Preserve original post-unlock pointer lifetime; do not invent
                // a hold/ACK or silently move these reads under the lock.
                let mut storage=core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
                let info=storage.as_mut_ptr();
                core::ptr::write_bytes(info.cast::<u8>(),0,size_of::<crate::abi::SigInfo>());
                core::ptr::addr_of_mut!((*info).si_signo).write(core::ptr::addr_of!((*fd).padding).read());
                let fault=core::ptr::addr_of_mut!((*info).sifields.sigfault).cast::<crate::abi::SigInfoFault>();
                core::ptr::addr_of_mut!((*fault).si_addr).write(core::ptr::addr_of!((*regs).gpr.rip).read() as *mut c_void);
                let poll=core::ptr::addr_of_mut!((*info).sifields.sigpoll).cast::<crate::abi::SigInfoPoll>();
                core::ptr::addr_of_mut!((*poll).si_fd).write(core::ptr::addr_of!((*fd).fd).read());
                x86_main_signal(core::ptr::addr_of!((*fd).padding).read(),regs.cast(),info);
            } else {
                x86_main_signal(x86_main_irq_constants[21] as CInt,regs.cast(),core::ptr::null_mut());
            }
        } else if vector>=x86_main_irq_constants[11] as CInt && vector<x86_main_irq_constants[12] as CInt {
            x86_main_tlb(vector);
        } else if vector==x86_main_irq_constants[13] as CInt {
            x86_main_smp();
        } else if vector==133 {
            x86_main_stack(core::ptr::addr_of!((*regs).gpr.rbp).read() as *mut CULong);
        } else {
            let head=core::ptr::addr_of_mut!(handlers).cast::<crate::abi::AbiListHead>().add((vector-32) as usize);
            let list_offset=x86_main_irq_handler_layout[2] as usize;
            let func_offset=x86_main_irq_handler_layout[3] as usize;
            let priv_offset=x86_main_irq_handler_layout[4] as usize;
            let mut node=core::ptr::addr_of!((*head).next).read().cast::<u8>().wrapping_sub(list_offset);
            while node.wrapping_add(list_offset).cast::<crate::abi::AbiListHead>()!=head {
                type Handler=unsafe extern "C" fn(*mut c_void);
                // No guessed handler repr or alignment. Exact callback ABI,
                // C offsets/alignment and actual record lifetime need witness.
                let callback=node.wrapping_add(func_offset).cast::<Option<Handler>>();
                if callback.read_unaligned().is_some() {
                    let function=callback.read_unaligned().unwrap_unchecked();
                    let private=node.wrapping_add(priv_offset).cast::<*mut c_void>().read_unaligned();
                    function(private);
                }
                // Original for-loop reloads current entry's next AFTER callback.
                let list=node.wrapping_add(list_offset).cast::<crate::abi::AbiListHead>();
                node=core::ptr::addr_of!((*list).next).read().cast::<u8>().wrapping_sub(list_offset);
            }
        }
        x86_main_exit(regs);
        x86_main_cputime(x86_main_irq_constants[if from_user!=0 {2}else{3}] as CUInt);
        nesting.write(nesting.read().wrapping_sub(1));
        if (core::ptr::addr_of!((*v).flags).read() & x86_main_irq_constants[5] as u32)!=0 && from_user!=0 {
            x86_main_schedule();
            check_signal(0,regs.cast(),0);
        }
    }
}

unsafe extern "C" {
    #[link_name="list_add_tail"]
    fn x86_irq_registration_add_tail(new:*mut crate::abi::AbiListHead,head:*mut crate::abi::AbiListHead);
    #[link_name="list_del"]
    fn x86_irq_registration_del(entry:*mut crate::abi::AbiListHead);
}

/// Register the caller-owned handler at the same tail, using the already
/// selected Rust list core. Invalid vector returns before handler/state access.
/// The caller retains original list exclusion and detached/live record rules.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_register_interrupt_handler(
    vector:CInt,handler:*mut c_void,
) -> CInt {
    if vector<32 || vector>255 {return -EINVAL;}
    unsafe {
        let list=handler.cast::<u8>().wrapping_add(x86_main_irq_handler_layout[2] as usize)
            .cast::<crate::abi::AbiListHead>();
        let head=core::ptr::addr_of_mut!(handlers).cast::<crate::abi::AbiListHead>()
            .add((vector-32) as usize);
        x86_irq_registration_add_tail(list,head);
    }
    0
}

/// Preserve the complete unregister operation. Its vector is intentionally
/// ignored as in C; no new range/NULL/membership/IRQ/lock policy is introduced.
/// The live linked record remains caller-owned, and existing list_del retains
/// its exact unlink/poison behavior through the same Rust implementation.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_unregister_interrupt_handler(
    _vector:CInt,handler:*mut c_void,
) -> CInt {
    unsafe {
        let list=handler.cast::<u8>().wrapping_add(x86_main_irq_handler_layout[2] as usize)
            .cast::<crate::abi::AbiListHead>();
        x86_irq_registration_del(list);
    }
    0
}

// Complete existing IDT initialization port. Existing setup-phase1 supplies the
// same init_idt callback. C state and selector/layout witnesses remain explicit
// data debt; the existing C reload_idt is still the sole privileged boundary.
unsafe extern "C" {
    static mut x86_cpu_idt: [[u32; 4]; 256];
    // Address-only byte alias, never a Rust model of the packed C descriptor.
    static mut x86_cpu_idt_desc: u8;
    static x86_idt_geometry: [CULong; 9];
    #[link_name = "handlers"]
    static mut x86_idt_handlers: [crate::abi::AbiListHead; 224];
    #[link_name = "generic_common_handlers"]
    static x86_idt_generic_handlers: [CULong; 256];
    #[link_name = "nmi_handler"] static x86_idt_nmi: u8;
    #[link_name = "general_protection_exception"] static x86_idt_gpe: u8;
    #[link_name = "page_fault"] static x86_idt_page_fault: u8;
    #[link_name = "debug_exception"] static x86_idt_debug: u8;
    #[link_name = "int3_exception"] static x86_idt_int3: u8;
    #[link_name = "INIT_LIST_HEAD"]
    fn x86_idt_list_init(list: *mut crate::abi::AbiListHead);
    #[link_name = "reload_idt"] fn x86_idt_reload();
}

/// Same four u32 stores as the complete C setter. Callers retain the original
/// valid-index requirement; no new range check, architecture constant or IDT
/// lifetime is introduced. Real C/Rust array/packed-descriptor witnesses must
/// pass before integration. Original initialization order/exclusion is required.
#[no_mangle]
pub unsafe extern "C" fn set_idt_entry(idx: CInt, addr: CULong) {
    unsafe {
        let entry = core::ptr::addr_of_mut!(x86_cpu_idt)
            .cast::<[u32; 4]>().offset(idx as isize).cast::<u32>();
        entry.write(((addr & 0xffff) | (x86_idt_geometry[8] << 16)) as u32);
        entry.add(1).write(((addr & 0xffff0000) | 0x8e00) as u32);
        entry.add(2).write((addr >> 32) as u32);
        entry.add(3).write(0);
    }
}

/// Preserve the trap gate's only difference, the exact existing 0xef00 field.
#[no_mangle]
pub unsafe extern "C" fn set_idt_entry_trap_gate(idx: CInt, addr: CULong) {
    unsafe {
        let entry = core::ptr::addr_of_mut!(x86_cpu_idt)
            .cast::<[u32; 4]>().offset(idx as isize).cast::<u32>();
        entry.write(((addr & 0xffff) | (x86_idt_geometry[8] << 16)) as u32);
        entry.add(1).write(((addr & 0xffff0000) | 0xef00) as u32);
        entry.add(2).write((addr >> 32) as u32);
        entry.add(3).write(0);
    }
}

/// Preserve descriptor publication, each list-before-gate initialization, the
/// five ordered special-gate overwrites, and the single final reload callback.
/// This does not execute LIDT in a HOST fixture or establish AP/native readiness.
#[no_mangle]
pub unsafe extern "C" fn init_idt() {
    unsafe {
        let descriptor = core::ptr::addr_of_mut!(x86_cpu_idt_desc);
        descriptor.add(x86_idt_geometry[4] as usize).cast::<u16>()
            .write_unaligned(x86_idt_geometry[0].wrapping_sub(1) as u16);
        descriptor.add(x86_idt_geometry[5] as usize).cast::<CULong>()
            .write_unaligned(core::ptr::addr_of_mut!(x86_cpu_idt) as CULong);
        for i in 0..256 {
            if i >= 32 {
                let head = core::ptr::addr_of_mut!(x86_idt_handlers)
                    .cast::<crate::abi::AbiListHead>().add(i - 32);
                x86_idt_list_init(head);
            }
            set_idt_entry(i as CInt, x86_idt_generic_handlers[i]);
        }
        set_idt_entry(2, core::ptr::addr_of!(x86_idt_nmi) as CULong);
        set_idt_entry(13, core::ptr::addr_of!(x86_idt_gpe) as CULong);
        set_idt_entry(14, core::ptr::addr_of!(x86_idt_page_fault) as CULong);
        set_idt_entry_trap_gate(1, core::ptr::addr_of!(x86_idt_debug) as CULong);
        set_idt_entry_trap_gate(3, core::ptr::addr_of!(x86_idt_int3) as CULong);
        x86_idt_reload();
    }
}

// Existing real TSS/descriptor types keep this port independent of a new ABI model.
mod initial_gdt {
    use core::arch::asm;
    use core::mem::size_of;
    use core::ptr::{addr_of_mut, write_bytes, write_unaligned};

    use crate::abi::{CULong, Tss64, X86DescPtr};

    unsafe extern "C" {
        #[link_name = "tss"]
        static mut initial_tss: Tss64;
        #[link_name = "gdt"]
        static mut initial_table: [CULong; 16];
        #[link_name = "gdt_desc"]
        static mut initial_descriptor: X86DescPtr;
        static x86_gdt_geometry: [CULong; 2];
        #[link_name = "reload_gdt"]
        fn load_existing_gdt(descriptor: *mut X86DescPtr);
    }

    // Caller owns the same boot-time exclusion as init_gdt. The real C TSS and
    // GDT storage remain writable/live across the final existing reload callback.
    // ABI equality must prove Tss64, X86DescPtr and the 16-entry C array first.
    unsafe fn publish_initial_gdt(stack_pointer: CULong) {
        // SAFETY: Boot owns these unique static objects; no reference is formed
        // to packed fields. Typed sizes/offsets come from the actual shared ABI.
        // The C geometry supplies the real selector slot and table byte count.
        unsafe {
            let tss = addr_of_mut!(initial_tss);
            let table = addr_of_mut!(initial_table).cast::<CULong>();
            let descriptor = addr_of_mut!(initial_descriptor);
            let tss_address = tss as CULong;
            let slot = x86_gdt_geometry[1] as usize;

            write_bytes(tss.cast::<u8>(), 0, size_of::<Tss64>());
            write_unaligned(addr_of_mut!((*tss).rsp0), stack_pointer);

            table.add(slot).write(
                (size_of::<Tss64>() as CULong - 1)
                    | ((tss_address & 0xffffff) << 16)
                    | (0x89u64 << 40)
                    | ((tss_address & 0xff000000) << 32),
            );
            table.add(slot + 1).write(tss_address >> 32);
            write_unaligned(
                addr_of_mut!((*descriptor).size),
                x86_gdt_geometry[0].wrapping_sub(1) as u16,
            );
            write_unaligned(addr_of_mut!((*descriptor).address), table as CULong);
            load_existing_gdt(descriptor);
        }
    }

    /// Initialize the same boot GDT and TSS, then invoke the existing reload body.
    ///
    /// # Safety
    /// The caller must own boot-time exclusion for the live initial TSS/GDT and
    /// execute on the intended writable kernel stack. Their actual C layouts and
    /// selector index must match the shared ABI and C geometry witness. The
    /// existing reload callback performs privileged segment/task-state changes.
    #[no_mangle]
    pub unsafe extern "C" fn init_gdt() {
        let stack_pointer: CULong;

        // SAFETY: Reading the current RSP does not dereference it or change stack
        // contents, flags or control state. This is the original live-RSP input,
        // not a fabricated interrupt frame or a native equivalence observation.
        unsafe {
            asm!(
                "mov {stack_pointer}, rsp",
                stack_pointer = lateout(reg) stack_pointer,
                options(nomem, nostack, preserves_flags),
            );
        }

        // SAFETY: Caller-owned boot exclusion and real-data lifetime cover this
        // publication transaction and the existing final reload callback.
        unsafe { publish_initial_gdt(stack_pointer) };
    }
}

// Complete existing low-level local APIC providers, selected by the unchanged C
// dispatch-pointer assignment. No new mapping, IRQ or device ownership policy.
mod local_apic_io {
    use core::ffi::c_void;
    use core::ptr::{addr_of, read_volatile, write_volatile};

    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        #[link_name = "lapic_vp"]
        static mut mapped_local_apic: *mut c_void;
        static x86_local_apic_base_msr: u32;
    }

    /// Perform the same single volatile 32-bit mapped local APIC store.
    ///
    /// # Safety
    /// The existing dispatch selection and caller must ensure the mapped device
    /// remains live, writable and excluded as required. `reg` must select an
    /// aligned accessible 32-bit register relative to the existing mapped base.
    #[no_mangle]
    pub unsafe extern "C" fn apic_write(reg: CInt, value: u32) {
        // SAFETY: The caller owns the same mapping/exclusion contract as the C
        // provider. The slot contains a live device base; no reference is formed
        // to MMIO. Signed byte offset and access width are preserved exactly.
        unsafe {
            let base = addr_of!(mapped_local_apic).read().cast::<u8>();
            let register = base.offset(reg as isize).cast::<u32>();
            write_volatile(register, value);
        }
    }

    /// Perform the same single volatile 32-bit mapped local APIC load.
    ///
    /// # Safety
    /// The caller must satisfy the live mapping, alignment and device access
    /// exclusion contract documented by `apic_write`, with a readable register.
    #[no_mangle]
    pub unsafe extern "C" fn apic_read(reg: CInt) -> u32 {
        // SAFETY: The caller supplies a live, aligned readable device register.
        // The load remains volatile; no caching, retry or additional read occurs.
        unsafe {
            let base = addr_of!(mapped_local_apic).read().cast::<u8>();
            read_volatile(base.offset(reg as isize).cast::<u32>())
        }
    }

    /// Preserve the signed register conversion and existing Rust MSR write.
    ///
    /// # Safety
    /// The caller must execute on the intended CPU with x2APIC enabled and a
    /// valid register/value for the existing dispatch selection and IRQ context.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_write(mut reg: CInt, value: u32) {
        // SAFETY: The real C macro supplies the same index base; arithmetic
        // right shift preserves GCC's signed int mapping. The existing Rust
        // wrmsr provider retains the privileged instruction and ordering contract.
        unsafe {
            reg >>= 4;
            reg |= x86_local_apic_base_msr as CInt;
            super::wrmsr(reg as u32, value as CULong);
        }
    }

    /// Preserve the signed index mapping and low-32-bit unsigned return.
    ///
    /// # Safety
    /// The caller must meet the x2APIC CPU/register/exclusion contract described
    /// by `x2apic_write`. The existing Rust MSR read may access device state.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_read(mut reg: CInt) -> u32 {
        // SAFETY: The caller selected a valid x2APIC provider/register. The same
        // single existing Rust rdmsr call occurs; C's int-to-unsigned return
        // conversion keeps the same low32 bits of the 64-bit MSR value.
        unsafe {
            reg >>= 4;
            reg |= x86_local_apic_base_msr as CInt;
            super::rdmsr(reg as u32) as u32
        }
    }
}

// Complete existing IPI entry wrappers. The already selected Rust transaction
// cores retain barrier, IRQ flags, idle wait, ICR argument order and restoration.
mod ipi_entries {
    use crate::abi::CInt;

    unsafe extern "C" {
        fn x2apic_icr_write(low: u32, apicid: u32);
        fn apic_icr_write(high: u32, low: u32);
        fn apic_wait_icr_idle();
        static x86_ipi_icr_id_shift: CInt;
    }

    /// Execute the same complete x2APIC IPI transaction using existing providers.
    ///
    /// # Safety
    /// The caller must run on the selected CPU in valid x2APIC/device context,
    /// with the same interrupt-controller exclusion and live ICR provider state
    /// required by the original wrapper. This invokes privileged IRQ/MSR effects.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_x86_issue_ipi(apicid: u32, low: u32) {
        // SAFETY: The caller supplies the existing device/exclusion contract.
        // These are the same Rust primitives reached through the old C thunks;
        // the existing transaction core preserves all callback order/flag data.
        unsafe {
            let _ = super::x86_x2apic_issue_ipi_body_result(
                apicid,
                low,
                Some(super::ihk_mc_mb),
                Some(super::cpu_disable_interrupt_save),
                Some(x2apic_icr_write),
                Some(super::cpu_restore_interrupt),
            );
        }
    }

    /// Execute the same complete mapped-APIC IPI transaction.
    ///
    /// # Safety
    /// The caller must provide the selected CPU/device/exclusion context and
    /// live mapped-APIC callbacks. The unchanged idle loop may wait for hardware;
    /// the same IRQ flags must remain owned through the final restore operation.
    #[no_mangle]
    pub unsafe extern "C" fn apic_x86_issue_ipi(apicid: u32, low: u32) {
        // SAFETY: Existing device/mapping lifetime and IRQ exclusion cover the
        // callback sequence. The real C macro supplies the unchanged bit shift;
        // no new mask, bound, fallback, error suppression or return is added.
        unsafe {
            let _ = super::x86_apic_issue_ipi_body_result(
                apicid,
                low,
                x86_ipi_icr_id_shift,
                Some(super::cpu_disable_interrupt_save),
                Some(apic_wait_icr_idle),
                Some(apic_icr_write),
                Some(super::cpu_restore_interrupt),
            );
        }
    }
}

// Complete existing ICR providers and idle wait. Existing selected data supplies
// register indices; no new getter, mapping, retry or hardware ordering policy.
mod icr_callbacks {
    use core::ptr::addr_of;

    use crate::abi::{CInt, CULong};

    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;

    unsafe extern "C" {
        #[link_name = "lapic_read"]
        static mut selected_read: Option<ReadRegister>;
        static x86_icr_geometry: [CULong; 4];
    }

    /// Write the same combined low-word/destination value to the existing MSR.
    ///
    /// # Safety
    /// The caller must own the selected CPU/x2APIC context and controller
    /// exclusion required by the original C callback. The MSR bridge performs
    /// the existing privileged write and must remain available for this call.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_icr_write(low: u32, apicid: u32) {
        // SAFETY: The caller provides the live device/CPU context. The real C
        // macro supplies the same index. Keep the existing external MSR bridge
        // boundary instead of changing its compiler-visible memory effects.
        unsafe {
            let value = ((apicid as CULong) << 32) | low as CULong;
            super::x86_write_msr_bridge(x86_icr_geometry[0] as CInt, value);
        }
    }

    /// Preserve the high-register write followed by the low-register write.
    ///
    /// # Safety
    /// The caller must retain the existing selected mapped-APIC provider and
    /// its mapping/device exclusion across both operations. The high/low inputs
    /// and register selection have the same validity contract as the C callback.
    #[no_mangle]
    pub unsafe extern "C" fn apic_icr_write(high: u32, low: u32) {
        // SAFETY: Existing dispatch and mapping lifetime cover both writes.
        // Both calls reuse the original LAPIC bridge; no fence, read or reordering
        // is inserted between the two device operations.
        unsafe {
            super::x86_lapic_write_bridge(x86_icr_geometry[1] as CInt, high);
            super::x86_lapic_write_bridge(x86_icr_geometry[2] as CInt, low);
        }
    }

    /// Repeat the same busy-register read and pause until the busy bit clears.
    ///
    /// # Safety
    /// The selected read callback must be non-NULL, retain its actual C
    /// unsigned-int(int) ABI, and remain callable with live device state under
    /// the caller's controller exclusion. The original operation has no timeout.
    #[no_mangle]
    pub unsafe extern "C" fn apic_wait_icr_idle() {
        // SAFETY: The caller owns the same non-NULL dispatch/device contract as
        // C. Reload the function pointer each iteration without forming a Rust
        // reference to the mutable C slot. Do not add a NULL fallback or timeout.
        unsafe {
            loop {
                let read = addr_of!(selected_read).read().unwrap_unchecked();
                let value = read(x86_icr_geometry[2] as CInt);
                if value & x86_icr_geometry[3] as u32 == 0 {
                    break;
                }
                super::x86_cpu_pause_bridge();
            }
        }
    }
}

// Complete existing context entry bodies reuse the already selected Rust cores.
// Actual shared types/offsets replace no ABI layout and acquire no new lifetime.
mod context_entries {
    use core::ffi::c_void;
    use core::mem::offset_of;
    use core::ptr::{addr_of, null_mut};

    use crate::abi::{CInt, CULong, CpuLocalVar, Thread, X86KernelContext, X86UserContext};

    unsafe extern "C" {
        #[link_name = "get_x86_this_cpu_kstack"]
        fn current_kernel_stack() -> *mut c_void;
        #[link_name = "get_this_cpu_local_var"]
        fn current_local() -> *mut CpuLocalVar;
        static enter_user_mode: u8;
        static x86_lookup_sleep_mask: CInt;
        static x86_user_start_geometry: [CULong; 3];
    }

    static THREAD_CONTEXT_OFFSETS: super::X86ThreadContextOffsets =
        super::X86ThreadContextOffsets {
            thread_status_offset: offset_of!(Thread, status) as CULong,
            thread_uctx_offset: offset_of!(Thread, uctx) as CULong,
            thread_tlsblock_base_offset: offset_of!(Thread, tlsblock_base) as CULong,
        };

    /// Initialize the existing kernel context and return slot with the Rust core.
    ///
    /// # Safety
    /// Non-NULL arguments must satisfy the existing core's actual typed context
    /// and writable stack-slot contract. A NULL stack selects the live current
    /// CPU stack accessor. The caller excludes concurrent writes to those spans;
    /// no new allocation, reference, ownership transfer or callable-frame proof
    /// is supplied here. Existing core errors remain ignored by this void ABI.
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_init_context(
        context: *mut X86KernelContext,
        stack_pointer: *mut c_void,
        next_function: Option<unsafe extern "C" fn()>,
    ) {
        let next = match next_function {
            Some(function) => function as *mut c_void,
            None => null_mut(),
        };

        // SAFETY: Caller-owned spans remain live and writable through the same
        // selected core. The accessor is the actual provider called by the old
        // C thunk, with the identical void*(void) ABI and conditional invocation.
        unsafe {
            let _ = super::x86_init_context_body_result(
                context,
                stack_pointer,
                next,
                Some(current_kernel_stack),
            );
        }
    }

    /// Build the same initial user frame and kernel return slot via the Rust core.
    ///
    /// # Safety
    /// The caller must provide the existing live writable kernel context, output
    /// pointer and stack region covering the user context plus preceding return
    /// word. Geometry/symbol bindings must match the real selected C headers and
    /// enter_user_mode provider. This stores code/user addresses without running
    /// them, and does not establish a valid native user transition by itself.
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_init_user_process(
        context: *mut X86KernelContext,
        user_context: *mut *mut X86UserContext,
        stack_pointer: *mut c_void,
        new_pc: CULong,
        user_sp: CULong,
    ) {
        // SAFETY: Existing caller-owned storage/exclusion covers each write by
        // the unchanged core. Read only real C selector/flag data and take the
        // existing ASM entry address; do not execute it or invent a valid frame.
        unsafe {
            let _ = super::x86_init_user_process_body_result(
                context,
                user_context,
                stack_pointer,
                new_pc,
                user_sp,
                x86_user_start_geometry[0],
                x86_user_start_geometry[1],
                x86_user_start_geometry[2],
                addr_of!(enter_user_mode) as *mut c_void,
            );
        }
    }

    /// Return/update the same existing thread user-context view via the Rust core.
    ///
    /// # Safety
    /// The current CPU-local object must be live and readable. Non-NULL thread
    /// and context pointers must retain their real layout and caller-owned
    /// lifetime/exclusion through the call and subsequent use of the raw return
    /// pointer. This adds no pin, lock, reference or lifetime extension.
    #[no_mangle]
    pub unsafe extern "C" fn lookup_user_context(thread: *mut Thread) -> *mut X86UserContext {
        // SAFETY: The caller retains the same current/thread/context lifetimes.
        // Read current once before the existing core, matching the selected C
        // wrapper. Immutable offsets derive from actual Thread, not a model.
        unsafe {
            let current = addr_of!((*current_local()).current).read();
            super::x86_lookup_user_context_body_result(
                thread.cast(),
                current.cast(),
                x86_lookup_sleep_mask,
                addr_of!(THREAD_CONTEXT_OFFSETS),
            )
        }
    }
}

// Complete existing FP entry wrappers. Existing Rust cores retain allocation,
// byte-copy, error and actual FP-ISA behavior; no new FP algorithm is introduced.
mod fp_state_entries {
    use core::ffi::c_void;
    use core::ptr::{addr_of, addr_of_mut};

    use crate::abi::{CInt, CULong, CpuLocalVar, Thread};

    unsafe extern "C" {
        #[link_name = "x86_cpu_xsave_available"]
        static mut available: CInt;
        #[link_name = "x86_cpu_xsave_size"]
        static mut extent: CInt;
        #[link_name = "x86_cpu_xsave_mask"]
        static mut request_mask: CULong;
        #[link_name = "x86_cpu_initial_fp_regs"]
        static mut initial_state: u8;
        #[link_name = "x86_cpu_initial_fp_regs_available"]
        static mut initial_available: CInt;
        static x86_cpu_fp_sse_enabled: CInt;
        #[link_name = "get_this_cpu_local_var"]
        fn current_local() -> *mut CpuLocalVar;
    }

    /// Preserve the selected Rust save result, including allocation failure.
    ///
    /// # Safety
    /// The caller must pin execution, retain the live thread/buffer and exclusive
    /// state access required by rust_x86_save_fp_regs. Boot configuration must be
    /// stable, with valid OSXSAVE/XCR0/mask/aligned extent when XSAVE is enabled.
    /// The entire kernel and callees must retain the no-FP/SIMD compiler profile;
    /// the scheduler must not advance a switch after an unsuccessful save.
    #[no_mangle]
    pub unsafe extern "C" fn save_fp_regs(thread: *mut Thread) -> CInt {
        // SAFETY: The unchanged caller-owned lifecycle/profile covers the same
        // thread and boot-stable scalar state read by the old C wrapper.
        unsafe { super::rust_x86_save_fp_regs(thread, available, extent, request_mask) }
    }

    /// Preserve exact selected copy behavior and return its existing error code.
    ///
    /// # Safety
    /// The caller retains both thread lifetimes and exclusive destination access.
    /// Present buffers cover the boot-stable XSAVE extent and do not overlap, as
    /// required by the existing Rust copy core. Do not reinterpret an invalid
    /// lifecycle as a successful copy or change allocation/publication ownership.
    #[no_mangle]
    pub unsafe extern "C" fn copy_fp_regs(from: *mut Thread, to: *mut Thread) -> CInt {
        // SAFETY: All storage/lifecycle obligations are unchanged from the
        // already selected core. This wrapper performs no additional allocation.
        unsafe { super::rust_x86_copy_fp_regs(from, to, available, extent) }
    }

    /// Restore the same present/default state using the already selected core.
    ///
    /// # Safety
    /// Execution must remain pinned/excluded on the intended CPU. The existing
    /// core's thread, aligned buffer, boot mask and initial-state lifetimes must
    /// hold. NULL still selects its existing default-state path; it does not
    /// establish the separate NMI(NULL) frame contract. No-FP/SIMD code generation
    /// and the actual supported hardware configuration remain required.
    #[no_mangle]
    pub unsafe extern "C" fn restore_fp_regs(thread: *mut Thread) {
        // SAFETY: The caller owns the same restore preconditions. Take only the
        // first byte address of real C initial storage, never a guessed model or
        // a reference whose lifetime outlives the original borrowed buffer.
        unsafe {
            super::rust_x86_restore_fp_regs(
                thread,
                available,
                initial_available,
                addr_of!(initial_state).cast::<c_void>(),
                request_mask,
                x86_cpu_fp_sse_enabled,
            );
        }
    }

    /// Reset the same actual current CPU-local idle thread via the Rust core.
    ///
    /// # Safety
    /// The current CPU-local object and idle thread must remain live and excluded
    /// on the intended CPU. The save/default state, boot mask and no-FP/SIMD
    /// profile have the same obligations documented by restore_fp_regs.
    #[no_mangle]
    pub unsafe extern "C" fn clear_fp_regs() {
        // SAFETY: CPU-local lifetime/exclusion covers the exact idle field and
        // unchanged restore core. Raw field addressing creates no new reference
        // or ownership hold and performs no new thread-slot publication.
        unsafe {
            let idle = addr_of_mut!((*current_local()).idle);
            super::rust_x86_clear_fp_regs(
                idle,
                available,
                initial_available,
                addr_of!(initial_state).cast::<c_void>(),
                request_mask,
                x86_cpu_fp_sse_enabled,
            );
        }
    }
}

unsafe extern "C" {
    static mut x86_cpu_setup_log_debug: crate::debug::Ddebug;
}

/// Preserve the complete selected PAT/TSC/setup diagnostic callback. This
/// replaces its existing C function-pointer target, not its caller or MSR/CPUID
/// behavior. Event2 retains its original dynamic selector; all returns ignored.
#[no_mangle]
pub unsafe extern "C" fn x86_cpu_log_bridge(event: CInt) {
    match event {
        1 => unsafe { kprintf(b"PAT not supported.\n\0".as_ptr().cast()); },
        2 => unsafe {
            let flags = read_volatile(
                core::ptr::addr_of!(x86_cpu_setup_log_debug.line_flags),
            ) >> 24;
            if flags != 0 {
                kprintf(b"PAT support detected and reconfigured.\n\0".as_ptr().cast());
            }
        },
        3 => unsafe { kprintf(b"Invariant TSC supported.\n\0".as_ptr().cast()); },
        4 => unsafe { kprintf(b"setup_x86 done.\n\0".as_ptr().cast()); },
        _ => {},
    }
}

unsafe extern "C" {
    // The exact existing CPU C dynamic-debug selector remains declarative data.
    static mut x86_interrupt_log_debug: crate::debug::Ddebug;
}

/// Preserve complete interrupt diagnostics and dynamic-debug argument evaluation.
/// Event1 always reports the supplied CPU; event2 obtains the current CPU only
/// after the original selector is enabled. The vector remains ignored, logger
/// results remain ignored, and no CPU/context pointer or lock is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_interrupt_log_bridge(
    event: CInt, cpu: CInt, _vector: CInt,
) {
    match event {
        1 => unsafe {
            kprintf(
                b"%s: invalid CPU id: %d\n\0".as_ptr().cast(),
                b"ihk_mc_interrupt_cpu\0".as_ptr().cast::<i8>(), cpu,
            );
        },
        2 => unsafe {
            let flags = read_volatile(
                core::ptr::addr_of!(x86_interrupt_log_debug.line_flags),
            ) >> 24;
            if flags != 0 {
                let current = crate::x86_local::ihk_mc_get_processor_id();
                kprintf(
                    b"[%d] ihk_mc_interrupt_cpu: %d\n\0".as_ptr().cast(),
                    current, cpu,
                );
            }
        },
        _ => {},
    }
}

unsafe extern "C" {
    // The same three original C file/function/line dynamic-debug records.
    static mut x86_tick_log_debug: [crate::debug::Ddebug; 3];
}

/// Preserve the complete selected tick-initialization diagnostics. Each event
/// reads only its original selector; unknown events touch no record or logger.
/// No timer, IRQ, current-CPU operation or provider result policy is introduced.
#[no_mangle]
pub unsafe extern "C" fn x86_tick_log_bridge(event: CInt) {
    let (index, format): (usize, &[u8]) = match event {
        1 => (0, b"init_tick():\n\0"),
        2 => (1, b"init_delay():\n\0"),
        3 => (2, b"sync_tick():\n\0"),
        _ => return,
    };
    unsafe {
        let row = core::ptr::addr_of!(x86_tick_log_debug)
            .cast::<crate::debug::Ddebug>().add(index);
        let flags = read_volatile(core::ptr::addr_of!((*row).line_flags)) >> 24;
        if flags != 0 {
            kprintf(format.as_ptr().cast());
        }
    }
}

unsafe extern "C" {
    // Same actual C __verbose per-line selectors, with existing Ddebug ABI.
    static mut x86_pvclock_log_debug: [crate::debug::Ddebug; 11];
}

/// Complete14-event pvclock/stack diagnostics using existing Rust providers.
/// Dynamic events read only their own existing selector. The allocation error
/// remains unconditional kprintf; stack headings remain unlocked __kprintf.
/// Unknown events touch no provider; results and all pointer lifetimes unchanged.
#[no_mangle]
pub unsafe extern "C" fn x86_pvclock_log_bridge(event: CInt) {
    match event {
        8 => { unsafe { kprintf(b"arch_setup_pvclock: allocate_pages failed.\n\0".as_ptr().cast()); } return; },
        13 => { unsafe { __kprintf(b"Pre-interrupt stack trace:\n\0".as_ptr().cast()); } return; },
        14 => { unsafe { __kprintf(b"Approximative stack trace:\n\0".as_ptr().cast()); } return; },
        _ => {},
    }
    let (index, format): (usize, &[u8]) = match event {
        1 => (0, b"is_pvclock_available()\n\0"),
        2 => (1, b"is_pvclock_available(): false (not kvm)\n\0"),
        3 => (2, b"is_pvclock_available(): true (new)\n\0"),
        4 => (3, b"is_pvclock_available(): true (old)\n\0"),
        5 => (4, b"is_pvclock_available(): false (not supported)\n\0"),
        6 => (5, b"arch_setup_pvclock()\n\0"),
        7 => (6, b"arch_setup_pvclock(): not supported\n\0"),
        9 => (7, b"arch_setup_pvclock(): ok\n\0"),
        10 => (8, b"arch_start_pvclock()\n\0"),
        11 => (9, b"arch_start_pvclock(): not supported\n\0"),
        12 => (10, b"arch_start_pvclock(): ok\n\0"),
        _ => return,
    };
    unsafe {
        let row = core::ptr::addr_of!(x86_pvclock_log_debug)
            .cast::<crate::debug::Ddebug>().add(index);
        let flags = read_volatile(core::ptr::addr_of!((*row).line_flags)) >> 24;
        if flags != 0 {
            kprintf(format.as_ptr().cast());
        }
    }
}

// Whole initialization entry providers reuse the existing selected Rust cores.
// Existing callbacks preserve CPUID/MSR/logging/device effects and their ordering.
mod initialization_entries {
    use core::ffi::c_void;
    use core::ptr::addr_of_mut;

    use crate::abi::{CInt, CULong};

    // Storage ownership only; mapping, feature publication and all device
    // accesses remain in the unchanged selected provider bodies.
    #[no_mangle]
    pub(crate) static mut lapic_vp: *mut c_void = core::ptr::null_mut();
    #[export_name = "x86_cpu_no_execute_available"]
    static mut no_execute: CInt = 0;

    unsafe extern "C" {
        #[link_name = "x86_cpu_x2apic_mode"]
        static mut x2apic_mode: CInt;
        static mut boot_pat_state: CULong;
        static mut gettime_local_support: CInt;
        static x86_init_geometry: [CULong; 11];
        static x86_syscall: u8;
        fn x86_lapic_bsp_select_bridge(mode: CInt);
        fn x86_cpuid_edx_bridge(leaf: CULong, value: *mut CULong);
        fn x86_enable_ptattr_no_execute_bridge();
        fn x86_map_fixed_area_bridge(phys: CULong, size: CULong, uncached: CInt)
            -> *mut c_void;
        fn x86_cpu_value_log_bridge(event: CInt, value: CInt);
        fn enable_page_protection_fault();
        fn init_fpu();
        fn x86_init_perfctr();
        fn init_page_table();
        fn init_idt();
        fn init_gdt();
    }

    /// Select the same boot local-APIC mode and provider callbacks.
    ///
    /// # Safety
    /// The caller owns serialized boot/device selection and the live C dispatch
    /// state. Existing MSR/selection callbacks retain their privileged contracts.
    #[no_mangle]
    pub unsafe extern "C" fn init_lapic_bsp() {
        // SAFETY: Caller-owned boot exclusion covers the same mode query and
        // selection callback, including the ignored existing CInt core result.
        unsafe {
            let _ = super::x86_init_lapic_bsp_body_result(
                super::x2apic_is_enabled(),
                Some(x86_lapic_bsp_select_bridge),
            );
        }
    }

    /// Initialize the same mapped/x2APIC device through the existing Rust core.
    ///
    /// # Safety
    /// Boot owns the selected mode, mapping slot, CPU and controller state. All
    /// existing provider lifetime/IRQ contracts hold through the complete call.
    #[no_mangle]
    pub unsafe extern "C" fn init_lapic() {
        // SAFETY: The real mutable slot remains live under boot exclusion. Real
        // C macro data and existing providers are passed in the original order.
        unsafe {
            let _ = super::x86_init_lapic_body_result(
                x2apic_mode,
                addr_of_mut!(lapic_vp),
                x86_init_geometry[0] as CInt,
                x86_init_geometry[1],
                x86_init_geometry[2],
                x86_init_geometry[3],
                Some(super::x86_read_msr_bridge),
                Some(super::x86_write_msr_bridge),
                Some(x86_map_fixed_area_bridge),
                Some(super::x86_lapic_write_bridge),
            );
        }
    }

    /// Preserve PAT capability/publication/MSR/logging using the existing core.
    ///
    /// # Safety
    /// The caller owns boot PAT state and the same CPUID/MSR/device context.
    #[no_mangle]
    pub unsafe extern "C" fn init_pat() {
        // SAFETY: The unique live PAT slot and all original callbacks remain
        // covered by boot exclusion; no new mapping or error handling is added.
        unsafe {
            let _ = super::x86_init_pat_body_result(
                addr_of_mut!(boot_pat_state),
                x86_init_geometry[4] as CInt,
                Some(x86_cpuid_edx_bridge),
                Some(super::x86_read_msr_bridge),
                Some(super::x86_write_msr_bridge),
                Some(super::x86_cpu_log_bridge),
            );
        }
    }

    /// Preserve the existing EFER/STAR/LSTAR setup and entry-address publication.
    ///
    /// # Safety
    /// The caller owns serialized CPU setup and the live syscall ASM provider.
    #[no_mangle]
    pub unsafe extern "C" fn init_syscall() {
        // SAFETY: All real C selector/MSR values and the actual ASM address are
        // consumed by the same core. The address is stored, never invoked here.
        unsafe {
            let _ = super::x86_init_syscall_body_result(
                x86_init_geometry[5] as CInt,
                x86_init_geometry[6] as CInt,
                x86_init_geometry[7] as CInt,
                x86_init_geometry[8],
                x86_init_geometry[9],
                core::ptr::addr_of!(x86_syscall) as CULong,
                Some(super::x86_read_msr_bridge),
                Some(super::x86_write_msr_bridge),
            );
        }
    }

    /// Preserve the existing boot NX check and selected page-attribute update.
    ///
    /// # Safety
    /// The caller owns the boot capability slot and real CPUID/attribute context.
    #[no_mangle]
    pub unsafe extern "C" fn check_no_execute() {
        // SAFETY: The same actual slot and callbacks remain live under boot
        // exclusion. The foreground logger export must be linked before use.
        unsafe {
            let _ = super::x86_check_no_execute_body_result(
                addr_of_mut!(no_execute),
                Some(x86_cpuid_edx_bridge),
                Some(x86_cpu_value_log_bridge),
                Some(x86_enable_ptattr_no_execute_bridge),
            );
        }
    }

    /// Preserve the boot-gated EFER NX enable operation through the Rust core.
    ///
    /// # Safety
    /// The boot capability data and privileged MSR context must remain stable.
    #[no_mangle]
    pub unsafe extern "C" fn enable_no_execute() {
        // SAFETY: Read the original boot slot and retain the exact existing
        // read/write callbacks and enable bit; no new capability inference.
        unsafe {
            let _ = super::x86_enable_no_execute_body_result(
                no_execute,
                x86_init_geometry[5] as CInt,
                x86_init_geometry[10],
                Some(super::x86_read_msr_bridge),
                Some(super::x86_write_msr_bridge),
            );
        }
    }

    /// Preserve the same invariant-TSC support slot and diagnostic callback.
    ///
    /// # Safety
    /// The caller owns serialized capability publication and the CPUID context.
    #[no_mangle]
    pub unsafe extern "C" fn init_gettime_support() {
        // SAFETY: The real writable slot and existing callbacks stay live.
        unsafe {
            let _ = super::x86_init_gettime_support_body_result(
                addr_of_mut!(gettime_local_support),
                Some(x86_cpuid_edx_bridge),
                Some(super::x86_cpu_log_bridge),
            );
        }
    }

    /// Invoke the same complete ordered CPU initialization transaction core.
    ///
    /// # Safety
    /// The caller owns the boot CPU, live tables/device state and each existing
    /// privileged provider contract. This adds no new initialization or rollback.
    #[no_mangle]
    pub unsafe extern "C" fn init_cpu() {
        // SAFETY: All callbacks are the same selected providers, in the same
        // order, with their previous boot/frame/device lifetimes retained.
        unsafe {
            let _ = super::x86_init_cpu_body_result(
                Some(enable_page_protection_fault),
                Some(enable_no_execute),
                Some(init_fpu),
                Some(init_lapic),
                Some(init_syscall),
                Some(x86_init_perfctr),
                Some(super::init_pstate_and_turbo),
                Some(init_pat),
            );
        }
    }

    /// Preserve early phase ordering and the already selected Rust phase markers.
    ///
    /// # Safety
    /// The caller owns early boot CPU, IRQ state, IDT/GDT and page-table lifetimes.
    #[no_mangle]
    pub unsafe extern "C" fn setup_x86_phase1() {
        // SAFETY: The existing core retains the exact marker/callback order.
        unsafe {
            let _ = super::x86_setup_phase1_body_result(
                Some(super::cpu_disable_interrupt),
                Some(init_idt),
                Some(init_gdt),
                Some(init_page_table),
            );
        }
    }

    /// Preserve phase-two capability/device/CPU/time setup and final diagnostic.
    ///
    /// # Safety
    /// The caller retains all boot, IRQ, device and state lifetimes required by
    /// the same providers passed to the existing ordered transaction core.
    #[no_mangle]
    pub unsafe extern "C" fn setup_x86_phase2() {
        // SAFETY: Caller-owned boot exclusion covers the unchanged provider
        // sequence. Core errors and callback results remain ignored as in C.
        unsafe {
            let _ = super::x86_setup_phase2_body_result(
                Some(check_no_execute),
                Some(init_lapic_bsp),
                Some(init_cpu),
                Some(init_gettime_support),
                Some(super::x86_cpu_log_bridge),
            );
        }
    }
}

// Complete existing control-state operations. No new access policy, saved-frame
// interpretation or hardware capability inference is introduced.
mod control_state_entries {
    use core::arch::asm;
    use core::ptr::addr_of;

    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        #[link_name = "x86_cpu_xsave_available"]
        static mut xsave_available: CInt;
        static x86_init_geometry: [CULong; 11];
    }

    /// Enable the same CR0 write-protection bit with original IRQ flag restore.
    ///
    /// # Safety
    /// The caller must execute in the existing privileged boot context on a live
    /// writable kernel stack, with the original CPU/IRQ ownership. The complete
    /// push/CLI/control-register/pop sequence must execute without interruption
    /// by unsupported context handling. This is never a HOST fixture operation.
    #[no_mangle]
    pub unsafe extern "C" fn enable_page_protection_fault() {
        // SAFETY: Caller-owned kernel stack/execution context covers the balanced
        // stack use and privileged instructions. Preserve the original sequence
        // and RAX clobber. The block restores flags and does not claim nostack.
        unsafe {
            asm!(
                "pushfq",
                "cli",
                "mov rax, cr0",
                "or rax, 0x10000",
                "mov cr0, rax",
                "popfq",
                lateout("rax") _,
                options(preserves_flags),
            );
        }
    }

    /// Print the same CR0/CR4/EFER and conditional XCR0 diagnostics.
    ///
    /// # Safety
    /// The caller must own the existing privileged CPU diagnostic context and
    /// logger lock span. Boot XSAVE availability must remain coherent with actual
    /// XGETBV eligibility. The logger/output buffers retain their existing lives;
    /// this does not create an IRQ frame or prove the separate NMI(NULL) contract.
    #[no_mangle]
    pub unsafe extern "C" fn arch_show_extended_context() {
        let cr0: CULong;
        let cr4: CULong;
        let mut xcr0 = 0;

        // SAFETY: Existing caller privilege/CPU ownership permits the two reads.
        // Neither operation accesses memory or changes flags/stack contents.
        unsafe {
            asm!("mov {value}, cr0", value = lateout(reg) cr0,
                options(nomem, nostack, preserves_flags));
            asm!("mov {value}, cr4", value = lateout(reg) cr4,
                options(nomem, nostack, preserves_flags));
        }

        // SAFETY: The original selected MSR helper and existing Rust XGETBV
        // provider retain their device/eligibility contracts. Re-read the same
        // availability slot at the second original gate rather than inventing
        // one cached snapshot. Format bytes/argument widths/order are exact.
        unsafe {
            let efer = super::x86_read_msr_bridge(x86_init_geometry[5] as CInt);
            if addr_of!(xsave_available).read() != 0 {
                xcr0 = super::xgetbv(0);
            }
            super::__kprintf(b"\n             CR0              CR4\n\0".as_ptr().cast());
            super::__kprintf(b"%016lX %016lX\n\0".as_ptr().cast(), cr0, cr4);
            super::__kprintf(b"             MSR_EFER\n\0".as_ptr().cast());
            super::__kprintf(b"%016lX\n\0".as_ptr().cast(), efer);
            if addr_of!(xsave_available).read() != 0 {
                super::__kprintf(b"             XCR0\n\0".as_ptr().cast());
                super::__kprintf(b"%016lX\n\0".as_ptr().cast(), xcr0);
            }
        }
    }
}

// Existing state bridge exports and kernel-stack publication, no new ABI model.
mod state_bridge_entries {
    use core::ffi::c_void;
    use core::mem::offset_of;
    use core::ptr::{addr_of, addr_of_mut};

    use crate::abi::{CInt, CLong, CULong, X86CpuLocalVariables};

    unsafe extern "C" {
        #[link_name = "x86_cpu_xsave_available"]
        static mut available: CInt;
        #[link_name = "x86_cpu_xsave_size"]
        static mut extent: CInt;
        #[link_name = "x86_cpu_xsave_mask"]
        static mut request_mask: CULong;
        #[link_name = "x86_cpu_initial_fp_regs"]
        static mut initial_state: u8;
        #[link_name = "x86_cpu_initial_fp_regs_available"]
        static mut initial_available: CInt;
        static x86_cpu_fp_sse_enabled: CInt;
        #[link_name = "get_x86_this_cpu_local"]
        fn current_arch_local() -> *mut X86CpuLocalVariables;
    }

    /// Return the same boot-published XSAVE byte extent.
    ///
    /// # Safety
    /// The caller must retain the original boot-publication synchronization.
    #[no_mangle]
    pub unsafe extern "C" fn x86_xsave_size_bridge() -> CInt {
        // SAFETY: The live boot state has the same synchronization as the C
        // getter; no capability inference, default or validation is introduced.
        unsafe { addr_of!(extent).read() }
    }

    /// Return the same boot-published complete XSAVE request mask.
    ///
    /// # Safety
    /// The caller must retain the original boot-publication synchronization.
    #[no_mangle]
    pub unsafe extern "C" fn x86_xsave_mask_bridge() -> CULong {
        // SAFETY: Read the same live actual u64 state with the caller's original
        // publication contract; do not truncate, reinterpret or change its bits.
        unsafe { addr_of!(request_mask).read() }
    }

    /// Return the same native-signal MXCSR mask through the existing Rust core.
    ///
    /// # Safety
    /// The supported native-signal CPU/SSE and no-FP/SIMD compiler contracts of
    /// the existing core must hold. This is not a HOST register-state operation.
    #[no_mangle]
    pub unsafe extern "C" fn arch_native_signal_mxcsr_mask_bridge() -> u32 {
        // SAFETY: The actual C SSE selection is unchanged; the existing core
        // retains its own instruction/data eligibility and fallback semantics.
        unsafe { super::rust_x86_native_signal_mxcsr_mask(x86_cpu_fp_sse_enabled) }
    }

    /// Reset the same native-signal FP state and return its original long result.
    ///
    /// # Safety
    /// The caller must retain the existing pinned CPU/IRQ, initial-image,
    /// OSXSAVE/XCR0/mask and no-FP/SIMD profile contracts through the reset.
    #[no_mangle]
    pub unsafe extern "C" fn arch_native_signal_reset_fp_bridge() -> CLong {
        // SAFETY: The same boot-stable real state/buffer and actual C config are
        // passed to the existing core; no error suppression or new state path.
        unsafe {
            super::rust_x86_native_signal_reset_fp(
                available,
                initial_available,
                addr_of!(initial_state).cast::<c_void>(),
                request_mask,
                x86_cpu_fp_sse_enabled,
            )
        }
    }

    /// Publish the same actual CPU-local kernel stack and packed TSS RSP0.
    ///
    /// # Safety
    /// The caller owns the current architecture CPU-local object and excludes
    /// concurrent stack/TSS mutation. `pointer` has the original valid kernel
    /// stack contract; the actual packed C/Rust field layouts must match.
    #[no_mangle]
    pub unsafe extern "C" fn set_kstack(pointer: CULong) {
        // SAFETY: The existing accessor returns the same live object used by C.
        // Actual shared-type offsets feed the unchanged selected Rust core;
        // no Rust reference is formed to packed storage or lifetime extended.
        unsafe {
            let local = current_arch_local();
            let _ = super::x86_set_kstack_body_result(
                local.cast(),
                offset_of!(X86CpuLocalVariables, kernel_stack) as CULong,
                offset_of!(X86CpuLocalVariables, tss.rsp0) as CULong,
                pointer,
            );
        }
    }
}

// Complete AP per-CPU initialization, using the actual packed shared types.
mod smp_initialization_entry {
    use core::ffi::c_void;
    use core::mem::size_of;
    use core::ptr::{addr_of, addr_of_mut, copy_nonoverlapping, write_bytes};

    use crate::abi::{CInt, CULong, Tss64, X86CpuLocalVariables, X86DescPtr};

    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;

    unsafe extern "C" {
        #[link_name = "get_x86_this_cpu_local"]
        fn current_arch_local() -> *mut X86CpuLocalVariables;
        #[link_name = "get_x86_this_cpu_kstack"]
        fn current_arch_stack() -> *mut c_void;
        static gdt: [u64; 16];
        #[link_name = "lapic_read"]
        static mut selected_read: Option<ReadRegister>;
        static x86_smp_init_geometry: [CULong; 6];
        fn reload_gdt(pointer: *mut X86DescPtr);
    }

    /// Install this CPU's GDT/TSS, publish its stack, and retain the KVM MSR skip.
    ///
    /// # Safety
    /// The caller owns a live current CPU-local object and AP initialization
    /// exclusion. The selected controller, global GDT template and actual macro
    /// geometry are valid through the operation. The existing reload/stack/MSR
    /// providers retain their real hardware and pinned-CPU contracts.
    #[no_mangle]
    pub unsafe extern "C" fn init_smp_processor() {
        // SAFETY: All addresses belong to the caller-owned real packed object.
        // Raw field accesses do not form references to packed storage. The GDT
        // template and destination are distinct, as required by the original
        // memcpy. The selected callback is nonnull under the original setup
        // precondition; no fallback, validation or hardware ordering is added.
        unsafe {
            let local = current_arch_local();
            let tss = addr_of_mut!((*local).tss);
            let tss_address = tss as CULong;
            let apic_id = if super::x2apic_is_enabled() != 0 {
                super::rdmsr(x86_smp_init_geometry[0] as u32)
            } else {
                let read = addr_of!(selected_read).read().unwrap_unchecked();
                (read(x86_smp_init_geometry[1] as CInt)
                    >> x86_smp_init_geometry[2]) as CULong
            };
            addr_of_mut!((*local).apic_id).write_unaligned(apic_id);

            let local_gdt = addr_of_mut!((*local).gdt).cast::<u8>();
            copy_nonoverlapping(addr_of!(gdt).cast::<u8>(), local_gdt, 16 * 8);
            write_bytes(tss.cast::<u8>(), 0, size_of::<Tss64>());
            let slots = local_gdt.cast::<u64>();
            let tss_slot = x86_smp_init_geometry[3] as usize;
            slots.add(tss_slot).write_unaligned(
                ((size_of::<Tss64>() - 1) as CULong)
                    | ((tss_address & 0xffffff) << 16)
                    | (0x89_u64 << 40)
                    | ((tss_address & 0xff000000) << 32),
            );
            slots.add(tss_slot + 1).write_unaligned(tss_address >> 32);

            // The C unsigned node_cpu truncates processor_id before either use.
            let node_cpu = addr_of!((*local).processor_id).read_unaligned() as u32;
            let getcpu = slots.add(x86_smp_init_geometry[4] as usize);
            getcpu.write_unaligned(getcpu.read_unaligned() | node_cpu as CULong);
            let descriptor = addr_of_mut!((*local).gdt_ptr);
            addr_of_mut!((*descriptor).size).write_unaligned((16 * 8 - 1) as u16);
            addr_of_mut!((*descriptor).address).write_unaligned(local_gdt as CULong);
            reload_gdt(descriptor);
            super::state_bridge_entries::set_kstack(current_arch_stack() as CULong);
            if super::running_on_kvm() != 0 {
                return;
            }
            super::wrmsr(x86_smp_init_geometry[5] as u32, node_cpu as CULong);
        }
    }
}

// Full FPU initialization entry, preserving original state/CPUID/CR/XCR sequence.
mod fpu_initialization_entry {
    use core::arch::{asm, x86_64::__cpuid_count};
    use core::ptr::{addr_of, addr_of_mut, read_volatile, write_bytes};

    use crate::abi::{CInt, CULong};
    use crate::debug::{kprintf, Ddebug};

    unsafe extern "C" {
        #[link_name = "x86_cpu_xsave_available"]
        static mut available: CInt;
        #[link_name = "x86_cpu_xsave_size"]
        static mut extent: CInt;
        #[link_name = "x86_cpu_xsave_mask"]
        static mut mask: CULong;
        #[link_name = "x86_cpu_initial_fp_regs"]
        static mut initial: u8;
        #[link_name = "x86_cpu_initial_fp_regs_available"]
        static mut initial_available: CInt;
        static x86_cpu_fp_sse_enabled: CInt;
        static x86_initial_fp_regs_extent: CULong;
        static mut x86_init_fpu_debug: [Ddebug; 6];
    }

    unsafe fn enabled(index: usize) -> bool {
        // SAFETY: The six real C records retain their original boot lifetime and
        // dynamic-debug ownership. Read only the existing flags word.
        unsafe {
            read_volatile(addr_of!(x86_init_fpu_debug[index].line_flags)) >> 24 != 0
        }
    }

    /// Initialize the original CPU-local FP control state and boot XSAVE image.
    ///
    /// # Safety
    /// This is privileged boot initialization on the owned CPU, under the
    /// original SSE/CPUID/XCR/XSAVE and no-FP/SIMD compiler contracts. The shared
    /// initial image is the real aligned C allocation, exclusively boot-owned;
    /// caller synchronization covers all boot variables and debug metadata.
    #[no_mangle]
    pub unsafe extern "C" fn init_fpu() {
        // SAFETY: These are the original privileged instruction operations, not
        // HOST-safe probes. All state/image spans and feature preconditions are
        // retained from the existing C initializer. Default asm memory effects
        // keep state operations ordered; no new capability or fallback is added.
        unsafe {
            let mut register: CULong;
            asm!("mov {value}, cr0", value = out(reg) register,
                options(nostack, preserves_flags));
            register &= !((1 << 2) | (1 << 3));
            register |= 1 << 1;
            asm!("mov cr0, {value}", value = in(reg) register,
                options(nostack, preserves_flags));

            if x86_cpu_fp_sse_enabled != 0 {
                let cpuid01 = __cpuid_count(1, 0);
                asm!("mov {value}, cr4", value = out(reg) register,
                    options(nostack, preserves_flags));
                register |= (1 << 9) | (1 << 10);
                if cpuid01.ecx & (1 << 26) != 0 {
                    if enabled(0) {
                        kprintf(b"init_fpu(): XSAVE available\n\0".as_ptr().cast());
                    }
                    available = 1;
                    register |= 1 << 18;
                }
                asm!("mov cr4, {value}", value = in(reg) register,
                    options(nostack, preserves_flags));
                if enabled(1) {
                    kprintf(b"init_fpu(): SSE init: CR4 = 0x%016lX\n\0".as_ptr().cast(),
                        register);
                }
                if available != 0 {
                    let cpuid0d = __cpuid_count(0x0d, 0);
                    extent = cpuid0d.ecx as CInt;
                    if enabled(2) {
                        kprintf(b"init_fpu(): xsave_size = %d\n\0".as_ptr().cast(), extent);
                    }
                    if cpuid0d.eax & ((1 << 5) | (1 << 6) | (1 << 7))
                        == ((1 << 5) | (1 << 6) | (1 << 7))
                    {
                        register = super::xgetbv(0) | 0xe6;
                        super::xsetbv(0, register);
                        if enabled(3) {
                            kprintf(
                                b"init_fpu(): AVX-512 init: XCR0 = 0x%016lX\n\0"
                                    .as_ptr().cast(),
                                register,
                            );
                        }
                    } else {
                        register = super::xgetbv(0) | 0x6;
                        super::xsetbv(0, register);
                        if enabled(4) {
                            kprintf(b"init_fpu(): AVX init: XCR0 = 0x%016lX\n\0"
                                .as_ptr().cast(), register);
                        }
                    }
                    mask = super::xgetbv(0);
                    if enabled(5) {
                        kprintf(b"init_fpu(): xsave_mask = 0x%016lX\n\0".as_ptr().cast(),
                            mask);
                    }
                }
            } else {
                kprintf(b"init_fpu(): SSE not enabled\n\0".as_ptr().cast());
            }
            asm!("finit", options(nostack, preserves_flags));
            // C compares signed int with sizeof's unsigned long: negative int
            // values convert to huge unsigned values and must not pass this gate.
            if available != 0 && (extent as CULong) <= x86_initial_fp_regs_extent {
                let low = mask as u32;
                let high = (mask >> 32) as u32;
                let image = addr_of_mut!(initial);
                write_bytes(image, 0, x86_initial_fp_regs_extent as usize);
                asm!("xsave [{image}]", image = in(reg) image,
                    in("eax") low, in("edx") high,
                    options(nostack, preserves_flags));
                initial_available = 1;
            }
        }
    }
}

// Whole panic snapshot wrapper and NMI mode orchestration. Inherited NULL freeze
// behavior is retained exactly; source readiness does not clear its native HOLD.
mod panic_nmi_entries {
    use core::ffi::c_void;
    use core::ptr::{addr_of, addr_of_mut, null, null_mut, read_volatile};

    use crate::abi::{CInt, CULong, CpuLocalVar, X86CpuLocalVariables, X86UserContext};
    use crate::debug::{kprintf, Ddebug};

    unsafe extern "C" {
        #[link_name = "get_this_cpu_local_var"]
        fn current_local() -> *mut CpuLocalVar;
        fn get_x86_cpu_local_variable(cpu: CInt) -> *mut X86CpuLocalVariables;
        static enter_user_mode: u8;
        static x86_panic_user_end: CULong;
        static mut nmi_mode: CInt;
        static mut x86_multi_nmi_debug: [Ddebug; 2];
        fn ihk_mc_query_mem_areas();
        fn ihk_mc_clear_dump_page_completion();
    }

    /// Save the same interrupted/kernel continuation snapshot and publish panic.
    ///
    /// # Safety
    /// The real IRQ frame, current thread and architecture CPU-local allocation
    /// remain valid under the existing panic/NMI ownership. The selected core's
    /// volatile typed spans must satisfy its original alignment contract. No
    /// frame or thread reference is retained or fabricated for NULL callers.
    #[no_mangle]
    pub unsafe extern "C" fn arch_save_panic_regs(irq_regs: *mut c_void) {
        // SAFETY: Exact existing accessors and source-owned live allocations
        // feed the selected core. Retain its original early-return/error path;
        // if it declines, execute the same complete original C fallback below.
        unsafe {
            let current = (*current_local()).current;
            let regs = irq_regs.cast::<X86UserContext>();
            let local = get_x86_cpu_local_variable(crate::x86_local::ihk_mc_get_processor_id());
            let saved = addr_of_mut!((*local).panic_regs).cast::<CULong>();
            let paniced = addr_of_mut!((*local).paniced);
            let context = if current.is_null() { null() } else { addr_of!((*current).ctx) };
            let resume = addr_of!(enter_user_mode) as CULong;
            if super::x86_arch_save_panic_regs_body_result(
                regs, context, saved, paniced, x86_panic_user_end, resume,
                Some(super::x86_cpu_ulong_log_bridge),
            ) == 0 {
                return;
            }
            // The original fallback assumes a valid frame and a current thread
            // for user-space snapshots; preserve that precondition rather than
            // turn an invalid NULL caller into a claimed successful snapshot.
            let rip = addr_of!((*regs).gpr.rip).read();
            if rip > x86_panic_user_end {
                saved.add(0).write_unaligned(addr_of!((*regs).gpr.rax).read());
                saved.add(1).write_unaligned(addr_of!((*regs).gpr.rbx).read());
                saved.add(2).write_unaligned(addr_of!((*regs).gpr.rcx).read());
                saved.add(3).write_unaligned(addr_of!((*regs).gpr.rdx).read());
                saved.add(4).write_unaligned(addr_of!((*regs).gpr.rsi).read());
                saved.add(5).write_unaligned(addr_of!((*regs).gpr.rdi).read());
                saved.add(6).write_unaligned(addr_of!((*regs).gpr.rbp).read());
                saved.add(7).write_unaligned(addr_of!((*regs).gpr.rsp).read());
                saved.add(8).write_unaligned(addr_of!((*regs).gpr.r8).read());
                saved.add(9).write_unaligned(addr_of!((*regs).gpr.r9).read());
                saved.add(10).write_unaligned(addr_of!((*regs).gpr.r10).read());
                saved.add(11).write_unaligned(addr_of!((*regs).gpr.r11).read());
                saved.add(12).write_unaligned(addr_of!((*regs).gpr.r12).read());
                saved.add(13).write_unaligned(addr_of!((*regs).gpr.r13).read());
                saved.add(14).write_unaligned(addr_of!((*regs).gpr.r14).read());
                saved.add(15).write_unaligned(addr_of!((*regs).gpr.r15).read());
                saved.add(16).write_unaligned(addr_of!((*regs).gpr.rip).read());
            } else {
                kprintf(b"%s: in user-space: %p\n\0".as_ptr().cast(),
                    b"arch_save_panic_regs\0".as_ptr().cast::<i8>(), rip as *const c_void);
                saved.add(0).write_unaligned(0);
                saved.add(1).write_unaligned(addr_of!((*current).ctx.rbx).read());
                saved.add(2).write_unaligned(0);
                saved.add(3).write_unaligned(0);
                saved.add(4).write_unaligned(addr_of!((*current).ctx.rsi).read());
                saved.add(5).write_unaligned(addr_of!((*current).ctx.rdi).read());
                saved.add(6).write_unaligned(addr_of!((*current).ctx.rbp).read());
                saved.add(7).write_unaligned(addr_of!((*current).ctx.rsp).read());
                saved.add(8).write_unaligned(0);
                saved.add(9).write_unaligned(0);
                saved.add(10).write_unaligned(0);
                saved.add(11).write_unaligned(0);
                saved.add(12).write_unaligned(addr_of!((*regs).gpr.r12).read());
                saved.add(13).write_unaligned(addr_of!((*regs).gpr.r13).read());
                saved.add(14).write_unaligned(addr_of!((*regs).gpr.r14).read());
                saved.add(15).write_unaligned(addr_of!((*regs).gpr.r15).read());
                saved.add(16).write_unaligned(resume);
            }
            let segments = saved.add(17).cast::<u32>();
            segments.add(0).write_unaligned(addr_of!((*regs).gpr.rflags).read() as u32);
            segments.add(1).write_unaligned(addr_of!((*regs).gpr.cs).read() as u32);
            segments.add(2).write_unaligned(addr_of!((*regs).gpr.ss).read() as u32);
            segments.add(3).write_unaligned(addr_of!((*regs).sr.ds).read() as u32);
            segments.add(4).write_unaligned(addr_of!((*regs).sr.es).read() as u32);
            segments.add(5).write_unaligned(addr_of!((*regs).sr.fs).read() as u32);
            segments.add(6).write_unaligned(addr_of!((*regs).sr.gs).read() as u32);
            paniced.write_unaligned(1);
        }
    }

    unsafe fn enabled(index: usize) -> bool {
        // SAFETY: Read only the existing flags word in the real C metadata.
        unsafe { read_volatile(addr_of!(x86_multi_nmi_debug[index].line_flags)) >> 24 != 0 }
    }

    /// Execute the same selected NMI modes, including the inherited NULL call.
    ///
    /// # Safety
    /// Caller owns the original interrupt/panic context and runtime mode state.
    /// Mode0 requires the real valid frame for arch_save_panic_regs. Modes1/2
    /// preserve freeze_thaw(NULL) and remain on the separate inherited NULL-freeze
    /// HOLD; no fabricated frame, no success guard and no IRQ/NMI safety claim.
    #[no_mangle]
    pub unsafe extern "C" fn multi_nm_interrupt_handler(irq_regs: *mut c_void) {
        // SAFETY: Existing providers and mode ownership retain their original
        // contracts. Ordinary nmi_mode loads preserve C's nonvolatile source
        // semantics; opaque halt/provider calls can still change shared state.
        unsafe {
            let function = b"multi_nm_interrupt_handler\0".as_ptr().cast::<i8>();
            if enabled(0) {
                kprintf(b"%s: ...\n\0".as_ptr().cast(), function);
            }
            let selected_mode = addr_of!(nmi_mode).read();
            match selected_mode {
                1 | 2 => {
                    if enabled(1) {
                        kprintf(b"%s: freeze mode NMI catch. (nmi_mode=%d)\n\0"
                            .as_ptr().cast(), function, addr_of!(nmi_mode).read());
                    }
                    let _ = crate::freeze::freeze_thaw(null_mut());
                }
                0 | 3 => {
                    if selected_mode == 0 {
                        arch_save_panic_regs(irq_regs);
                        ihk_mc_query_mem_areas();
                    }
                    kprintf(b"%s: STOP\n\0".as_ptr().cast(), function);
                    while addr_of!(nmi_mode).read() != 4 {
                        super::cpu_halt();
                    }
                }
                4 => {
                    super::arch_clear_panic();
                    if crate::x86_local::ihk_mc_get_processor_id() == 0 {
                        ihk_mc_clear_dump_page_completion();
                    }
                    kprintf(b"%s: RESUME, nmi_mode: %d\n\0".as_ptr().cast(),
                        function, addr_of!(nmi_mode).read());
                }
                _ => {
                    kprintf(b"%s: Unknown nmi-mode(%d) detected.\n\0".as_ptr().cast(),
                        function, addr_of!(nmi_mode).read());
                }
            }
        }
    }
}

// Complete existing dispatch selection and diagnostic MSR printer, using the
// already ported concrete providers rather than introducing a C selector/getter.
mod dispatch_and_msr_entries {
    use core::ptr::addr_of_mut;

    use crate::abi::CInt;
    use crate::debug::__kprintf;

    type WriteRegister = unsafe extern "C" fn(CInt, u32);
    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;
    type WriteIcr = unsafe extern "C" fn(u32, u32);
    type WaitIcr = unsafe extern "C" fn();
    type IssueIpi = unsafe extern "C" fn(u32, u32);

    // The existing nullable C-function-pointer aliases retain their exact
    // ABI. Initial NULL state and all selector publication order are unchanged.
    #[export_name = "x86_cpu_x2apic_mode"]
    static mut selected_mode: CInt = 0;
    #[no_mangle]
    pub(crate) static mut lapic_write: Option<WriteRegister> = None;
    #[no_mangle]
    pub(crate) static mut lapic_read: Option<ReadRegister> = None;
    #[no_mangle]
    pub(crate) static mut lapic_icr_write: Option<WriteIcr> = None;
    #[no_mangle]
    pub(crate) static mut lapic_wait_icr_idle: Option<WaitIcr> = None;
    #[no_mangle]
    pub(crate) static mut x86_issue_ipi: Option<IssueIpi> = None;

    const _: () = {
        assert!(core::mem::size_of::<Option<WriteRegister>>() == 8);
        assert!(core::mem::align_of::<Option<WriteRegister>>() == 8);
        assert!(core::mem::size_of::<Option<ReadRegister>>() == 8);
        assert!(core::mem::align_of::<Option<ReadRegister>>() == 8);
        assert!(core::mem::size_of::<Option<WriteIcr>>() == 8);
        assert!(core::mem::align_of::<Option<WriteIcr>>() == 8);
        assert!(core::mem::size_of::<Option<WaitIcr>>() == 8);
        assert!(core::mem::align_of::<Option<WaitIcr>>() == 8);
        assert!(core::mem::size_of::<Option<IssueIpi>>() == 8);
        assert!(core::mem::align_of::<Option<IssueIpi>>() == 8);
    };

    /// Retain the existing x2APIC mode's intentionally empty wait callback.
    ///
    /// # Safety
    /// The caller retains the original x2APIC dispatch/CPU ownership contract.
    /// No timeout, polling, barrier or controller access is introduced.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_wait_icr_idle() {}

    /// Publish the original mode and five dispatch targets in the same order.
    ///
    /// # Safety
    /// Boot owns all six existing C slots and excludes concurrent consumers or
    /// updates through the entire publication. This preserves the original
    /// unsynchronized C contract; it does not add atomicity or a readiness flag.
    #[no_mangle]
    pub unsafe extern "C" fn x86_lapic_bsp_select_bridge(use_x2apic: CInt) {
        // SAFETY: Each actual selected C slot has the exact original function
        // pointer ABI. All concrete targets are the existing private Rust body
        // exports, including the empty wait. No slot lifetime is extended.
        unsafe {
            if use_x2apic != 0 {
                addr_of_mut!(selected_mode).write(1);
                addr_of_mut!(lapic_write).write(Some(super::local_apic_io::x2apic_write));
                addr_of_mut!(lapic_read).write(Some(super::local_apic_io::x2apic_read));
                addr_of_mut!(lapic_icr_write).write(Some(super::icr_callbacks::x2apic_icr_write));
                addr_of_mut!(lapic_wait_icr_idle).write(Some(x2apic_wait_icr_idle));
                addr_of_mut!(x86_issue_ipi).write(Some(super::ipi_entries::x2apic_x86_issue_ipi));
            } else {
                addr_of_mut!(selected_mode).write(0);
                addr_of_mut!(lapic_write).write(Some(super::local_apic_io::apic_write));
                addr_of_mut!(lapic_read).write(Some(super::local_apic_io::apic_read));
                addr_of_mut!(lapic_icr_write).write(Some(super::icr_callbacks::apic_icr_write));
                addr_of_mut!(lapic_wait_icr_idle)
                    .write(Some(super::icr_callbacks::apic_wait_icr_idle));
                addr_of_mut!(x86_issue_ipi).write(Some(super::ipi_entries::apic_x86_issue_ipi));
            }
        }
    }

    /// Print the same decimal, hexadecimal and two complete 64-column bit lines.
    ///
    /// # Safety
    /// The caller supplies a legal MSR index and owns the original privileged CPU
    /// access and logger contract. The existing rdmsr provider is not HOST-safe.
    #[no_mangle]
    pub unsafe extern "C" fn print_msr(index: CInt) {
        // SAFETY: Same existing provider, formats, C int/u64 varargs, descending
        // bit order and ignored formatter results; no log lock is introduced.
        unsafe {
            let value = super::rdmsr(index as u32);
            __kprintf(b"MSR 0x%x val (dec): %llu\n\0".as_ptr().cast(), index, value);
            __kprintf(b"MSR 0x%x val (hex): 0x%llx\n\0".as_ptr().cast(), index, value);
            __kprintf(b"                    \0".as_ptr().cast());
            for bit in (0..64_i32).rev() {
                __kprintf(b"%3d\0".as_ptr().cast(), bit);
            }
            __kprintf(b"\n\0".as_ptr().cast());
            __kprintf(b"MSR 0x%x val (bin):\0".as_ptr().cast(), index);
            for bit in (0..64_i32).rev() {
                __kprintf(b"%3d\0".as_ptr().cast(), ((value >> bit) & 1) as CInt);
            }
            __kprintf(b"\n\0".as_ptr().cast());
        }
    }
}

// Complete TLS/perf/profile/delayed-stop context-switch transaction. This private
// local type is an exact port of the current real arch-lock.h definition, not a
// replacement shared ABI or a fabricated model for the future layout witness.
mod context_switch_entry {
    use core::ffi::c_void;
    use core::mem::MaybeUninit;
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};

    use crate::abi::{CInt, CULong, McsRwlockLock, Thread, X86KernelContext};
    use crate::debug::{kprintf, Ddebug};

    // The parent field is abi::Waitq; the genuine existing provider accepts
    // waitq::Waitq. Both repr(C) definitions mirror actual waitq.h. The provider
    // module independently asserts its private lock/list offsets to be 0/8.
    const _: () = {
        assert!(core::mem::size_of::<crate::abi::Waitq>() == 24);
        assert!(core::mem::align_of::<crate::abi::Waitq>() == 8);
        assert!(core::mem::size_of::<crate::waitq::Waitq>() == 24);
        assert!(core::mem::align_of::<crate::waitq::Waitq>() == 8);
        assert!(core::mem::offset_of!(crate::abi::Waitq, lock) == 0);
        assert!(core::mem::offset_of!(crate::abi::Waitq, waitq) == 8);
        assert!(core::mem::size_of::<crate::abi::IhkSpinlock>() == 4);
        assert!(core::mem::align_of::<crate::abi::IhkSpinlock>() == 4);
        assert!(core::mem::size_of::<crate::abi::AbiListHead>() == 16);
        assert!(core::mem::align_of::<crate::abi::AbiListHead>() == 8);
        assert!(core::mem::offset_of!(crate::abi::AbiListHead, next) == 0);
        assert!(core::mem::offset_of!(crate::abi::AbiListHead, prev) == 8);
        assert!(core::mem::offset_of!(crate::abi::Process, waitpid_q) == 432);
    };

    // arch-lock.h unconditionally selects SPINLOCK_IN_MCS_RWLOCK; current
    // supported build has ENABLE_UBSAN disabled. Only irqsave is present, with
    // the real C align64 tail padding. C/Rust size/align/field proof is pending.
    #[repr(C, align(64))]
    struct SwitchLockNode {
        irqsave: CULong,
    }

    unsafe extern "C" {
        static x86_switch_context_geometry: [CULong; 6];
        static x86_switch_context_perf_enabled: CInt;
        static x86_switch_context_profile_enabled: CInt;
        static mut x86_switch_context_debug: Ddebug;
        #[link_name = "__mcs_rwlock_writer_lock"]
        fn writer_lock(lock: *mut McsRwlockLock, node: *mut SwitchLockNode);
        #[link_name = "__mcs_rwlock_writer_unlock"]
        fn writer_unlock(lock: *mut McsRwlockLock, node: *mut SwitchLockNode);
        fn perf_reset(event: *mut c_void);
        fn perf_start(event: *mut c_void);
        fn ihk_mc_switch_context(
            old: *mut X86KernelContext,
            new: *mut X86KernelContext,
            previous: *mut c_void,
        ) -> *mut c_void;
    }

    /// Run the original complete scheduler context handoff and return last.
    ///
    /// # Safety
    /// The scheduler owns next and optional previous plus their process/parent,
    /// contexts, queues and monitoring event until the corresponding original
    /// use finishes. Its existing IRQ/runqueue and delayed-stop lock contracts
    /// remain required. The assembly context switch must satisfy its genuine C
    /// callee-save/resume ABI. No lock-node or thread reference is retained here.
    #[no_mangle]
    pub unsafe extern "C" fn arch_switch_context(
        previous: *mut Thread,
        next: *mut Thread,
    ) -> *mut Thread {
        let mut lock = MaybeUninit::<SwitchLockNode>::uninit();
        // SAFETY: Exact real shared types address the same caller-owned state.
        // Lock and unlock bracket only previous process delayed-status mutation;
        // parent wakeup remains after unlock. The node is stack-owned through
        // both callbacks, never initialized with invented field values.
        unsafe {
            if read_volatile(addr_of!(x86_switch_context_debug.line_flags)) >> 24 != 0 {
                kprintf(b"[%d] schedule: tlsblock_base: 0x%lX\n\0".as_ptr().cast(),
                    crate::x86_local::ihk_mc_get_processor_id(), (*next).tlsblock_base);
            }
            super::ihk_mc_init_user_tlsbase((*next).uctx, (*next).tlsblock_base);
            if x86_switch_context_perf_enabled != 0 {
                let process = (*next).proc;
                if !(*process).monitoring_event.is_null() {
                    if (*process).perf_status == x86_switch_context_geometry[4] as CInt {
                        perf_reset((*process).monitoring_event);
                    }
                    if (*process).perf_status != x86_switch_context_geometry[5] as CInt {
                        perf_reset((*process).monitoring_event);
                        perf_start((*process).monitoring_event);
                    }
                }
            }
            if x86_switch_context_profile_enabled != 0 {
                if !previous.is_null() && (*previous).profile != 0
                    && (*previous).profile_start_ts != 0
                {
                    let delta = super::rdtsc().wrapping_sub((*previous).profile_start_ts);
                    (*previous).profile_elapsed_ts =
                        (*previous).profile_elapsed_ts.wrapping_add(delta);
                    (*previous).profile_start_ts = 0;
                }
                if (*next).profile != 0 && (*next).profile_start_ts == 0 {
                    (*next).profile_start_ts = super::rdtsc();
                }
            }
            let old = if previous.is_null() {
                null_mut()
            } else {
                let process = (*previous).proc;
                let update = addr_of_mut!((*process).update_lock);
                writer_lock(update, lock.as_mut_ptr());
                let delayed_stopped = x86_switch_context_geometry[0] as CInt;
                let delayed_traced = x86_switch_context_geometry[1] as CInt;
                if (*process).status & (delayed_stopped | delayed_traced) != 0 {
                    if (*process).status == delayed_stopped {
                        (*process).status = x86_switch_context_geometry[2] as CInt;
                    } else if (*process).status == delayed_traced {
                        (*process).status = x86_switch_context_geometry[3] as CInt;
                    }
                    writer_unlock(update, lock.as_mut_ptr());
                    // SAFETY: Both actual Rust waitq definitions use the same
                    // C waitq_t storage, checked below and by the real C witness.
                    // The scheduler retains the parent queue through this call;
                    // this conversion creates no reference or lifetime hold.
                    let queue = addr_of_mut!((*(*process).parent).waitpid_q);
                    crate::waitq::waitq_wakeup(queue.cast::<crate::waitq::Waitq>());
                } else {
                    writer_unlock(update, lock.as_mut_ptr());
                }
                addr_of_mut!((*previous).ctx)
            };
            ihk_mc_switch_context(old, addr_of_mut!((*next).ctx), previous.cast()).cast()
        }
    }
}

// Complete descriptor loads and AP stack handoff. This source-only batch keeps
// privileged instruction execution and assembly/caller-stack review separate.
mod descriptor_load_and_ap_handoff_entries {
    use core::arch::asm;
    use core::ffi::c_void;
    use core::ptr::addr_of;

    use crate::abi::{CULong, X86DescPtr};

    type Continuation = unsafe extern "C" fn();

    unsafe extern "C" {
        static x86_cpu_idt_desc: X86DescPtr;
        static x86_gdt_reload_geometry: [CULong; 3];
        fn get_init_page_table() -> *mut c_void;
        fn ihk_mc_load_page_table(table: *mut c_void);
        fn assign_processor_id();
        #[link_name = "get_x86_this_cpu_kstack"]
        fn current_arch_stack() -> *mut c_void;
    }

    /// Load the same live ten-byte packed IDT descriptor.
    ///
    /// # Safety
    /// The caller owns the privileged CPU and a fully initialized, valid actual
    /// descriptor/table; publication and interrupt exclusion are unchanged.
    #[no_mangle]
    pub unsafe extern "C" fn reload_idt() {
        // SAFETY: LIDT reads the original complete packed descriptor without a
        // Rust reference or alignment assumption. Default asm memory effects
        // retain the original C memory clobber; no HOST execution is allowed.
        unsafe {
            asm!("lidt [{descriptor}]", descriptor = in(reg) addr_of!(x86_cpu_idt_desc),
                options(nostack, preserves_flags));
        }
    }

    /// Reload GDT and the original CS/DS/SS/TSS selectors in source order.
    ///
    /// # Safety
    /// The descriptor/GDT/TSS and all actual C selectors must be valid for the
    /// current privileged CPU and stack. The balanced far-return sequence must
    /// satisfy its real instruction ABI and exception/interrupt contract.
    #[no_mangle]
    pub unsafe extern "C" fn reload_gdt(descriptor: *mut X86DescPtr) {
        // SAFETY: This is the same push-CS/push-resume/LGDT/far-return operation.
        // A non-overlapping early output register replaces C's compiler-managed
        // RBX scratch: the descriptor input remains live until LGDT. The two
        // pushes are balanced by RETFQ; do not mark this block nostack/nomem.
        unsafe {
            asm!(
                "push {code}",
                "lea {scratch}, [rip + 2f]",
                "push {scratch}",
                "lgdt [{descriptor}]",
                "retfq",
                "2:",
                code = in(reg) x86_gdt_reload_geometry[0],
                descriptor = in(reg) descriptor,
                scratch = out(reg) _,
                options(preserves_flags),
            );
            // Separate blocks retain the original source's three ordered
            // segment/TSS operations, with default compiler memory effects.
            asm!("mov ds, {selector:x}", selector = in(reg) x86_gdt_reload_geometry[1],
                options(nostack, preserves_flags));
            asm!("mov ss, {selector:x}", selector = in(reg) x86_gdt_reload_geometry[1],
                options(nostack, preserves_flags));
            asm!("ltr {selector:x}", selector = in(reg) x86_gdt_reload_geometry[2],
                options(nostack, preserves_flags));
        }
    }

    /// Initialize an AP and transfer to its original continuation on its stack.
    ///
    /// # Safety
    /// AP boot owns the current CPU/page tables, local objects, descriptor state
    /// and kernel-stack allocation through the nonreturning handoff. The stack
    /// top and call_ap_func continuation obey the original x86 C call ABI. A
    /// nullable next function retains the existing call_ap_func error behavior.
    #[no_mangle]
    pub unsafe extern "C" fn setup_x86_ap(next_function: Option<Continuation>) {
        // SAFETY: Exact existing setup providers retain their source ordering
        // and hardware contracts. Once RSP changes, no Rust frame or local is
        // accessed again: the asm never returns. An unexpectedly returning
        // call_ap_func reaches the same endless-spin behavior as the C body.
        unsafe {
            super::cpu_disable_interrupt();
            ihk_mc_load_page_table(get_init_page_table());
            assign_processor_id();
            super::smp_initialization_entry::init_smp_processor();
            reload_idt();
            super::initialization_entries::init_cpu();
            let stack = current_arch_stack();
            let next = match next_function {
                Some(function) => function as usize,
                None => 0,
            };
            asm!(
                "mov rsp, {stack}",
                "call {entry}",
                "2:",
                "jmp 2b",
                stack = in(reg) stack,
                entry = in(reg) super::call_ap_func as *const (),
                in("rdi") next,
                clobber_abi("C"),
                options(noreturn),
            );
        }
    }
}

// Complete remaining public entry wrapper; same already selected Rust core.
mod ap_initialization_entry {
    use core::ffi::c_void;
    use core::ptr::addr_of_mut;

    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        #[link_name = "x86_cpu_trampoline_va"]
        static mut trampoline: *mut c_void;
        #[link_name = "x86_cpu_first_page_va"]
        static mut first_page: *mut c_void;
        static ap_trampoline: CULong;
        static x86_ap_init_geometry: [CULong; 2];
        fn x86_cpu_info_ncpus_bridge() -> CInt;
        fn x86_map_fixed_area_bridge(physical: CULong, size: CULong, uncached: CInt)
            -> *mut c_void;
    }

    /// Retire the C AP initializer wrapper without changing its selected core.
    ///
    /// # Safety
    /// Boot owns both mapping slots, actual trampoline extent, processor-local
    /// allocation/identity and current AP architecture state. All existing map,
    /// CPU-info, initialization/logging providers retain their lifetime/IRQ and
    /// hardware contracts. The original core result remains intentionally ignored.
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_init_ap() {
        // SAFETY: Both slots keep their original C ABI names and lifetimes;
        // Rust owns the zero storage without adding an accessor or C getter.
        // Same existing Rust init_processors_local/assign_processor_id bodies
        // replace their otherwise trivial C forwarding callback boundary.
        unsafe {
            let _ = super::x86_ihk_mc_init_ap_body_result(
                addr_of_mut!(trampoline),
                addr_of_mut!(first_page),
                ap_trampoline,
                x86_ap_init_geometry[0],
                x86_ap_init_geometry[1],
                Some(x86_map_fixed_area_bridge),
                Some(x86_cpu_info_ncpus_bridge),
                Some(crate::x86_local::init_processors_local),
                Some(crate::x86_local::assign_processor_id),
                Some(super::smp_initialization_entry::init_smp_processor),
                Some(super::x86_cpu_ulong_log_bridge),
            );
        }
    }
}

// Byte-exact previously frozen user-context entry reused below.
/// Retire the selected C entry while reusing its exact existing Rust core.
/// The original selected entry discarded the core result. In particular, a
/// null context retains the existing core's -EINVAL/no-log behavior; no new
/// frame or freeze/null policy is introduced. Context/log pointers do not escape.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_print_user_context(uctx: *mut X86UserContext) {
    unsafe {
        let _ = x86_print_user_context_body_result(
            uctx,
            Some(x86_context_line_log_bridge),
        );
    }
}

// Byte-exact existing stack forwarder only; foreground owns stack-frame logger.
#[no_mangle]
pub unsafe extern "C" fn x86_print_stack_bridge(rbp: *mut c_void, first: CULong) {
    unsafe { __print_stack(rbp.cast::<CULong>(), first); }
}

// Remaining exact existing callback bodies. No new C getter, subsystem, pointer
// ownership, acknowledgement or controller behavior is introduced.
mod remaining_cpu_callbacks {
    use core::ffi::c_void;
    use core::ptr::{addr_of, addr_of_mut};

    use crate::abi::{CInt, CULong, CpuLocalVar, IhkSpinlock};

    unsafe extern "C" {
        static mut lapic_write: Option<unsafe extern "C" fn(CInt, u32)>;
        static mut x86_issue_ipi: Option<unsafe extern "C" fn(u32, u32)>;
        fn ihk_mc_mb();
        #[link_name = "map_fixed_area"]
        fn c_map_fixed_area(physical: CULong, size: CULong, uncached: CInt) -> *mut c_void;
        #[link_name = "_ihk_mc_alloc_aligned_pages_node"]
        fn allocate_node(
            pages: CInt, alignment: CInt, flags: CULong, node: CInt, user: CInt,
            virtual_address: CULong, file: *mut i8, line: CInt,
        ) -> *mut c_void;
        #[link_name = "virt_to_phys"]
        fn c_virt_to_phys(address: *mut c_void) -> CULong;
        fn enable_ptattr_no_execute();
        #[link_name = "ihk_mc_get_cpu_info"]
        fn c_cpu_info() -> *mut c_void;
        static x86_cpu_info_ncpus_offset: CULong;
        #[link_name = "get_x86_this_cpu_kstack"]
        fn c_current_stack() -> *mut c_void;
        #[link_name = "get_this_cpu_local_var"]
        fn c_current_local() -> *mut CpuLocalVar;
        #[link_name = "x86_cpu_boot_status"]
        static mut boot_status: CInt;
        #[link_name = "x86_cpu_trampoline_va"]
        static mut trampoline: *mut c_void;
        static trampoline_code_data: u8;
        static trampoline_code_data_end: u8;
        static ap_trampoline: CULong;
        fn get_boot_page_table() -> *mut c_void;
        fn get_x86_cpu_local_kstack(cpu: CInt) -> *mut c_void;
        fn get_transit_page_table() -> CULong;
        #[link_name = "x86_trace_enter_user_offsets"]
        static trace_offsets: super::X86TraceEnterUserOffsets;
        #[link_name = "__ihk_mc_spinlock_unlock"]
        fn c_spin_unlock(lock: *mut IhkSpinlock, flags: CULong);
    }

    /// Call the same selected LAPIC write target.
    ///
    /// # Safety
    /// The live boot-selected callback and mapped controller must remain owned
    /// through the call; preserve its original MMIO/MSR and interrupt contract.
    #[no_mangle]
    pub unsafe extern "C" fn x86_lapic_write_bridge(register: CInt, value: u32) {
    unsafe { addr_of!(lapic_write).read().unwrap_unchecked()(register, value); }
    }

    /// Call the same existing architecture memory barrier.
    ///
    /// # Safety
    /// The original barrier caller and memory-publication contract must hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_mb_bridge() {
    unsafe { ihk_mc_mb(); }
    }

    /// Call the same save-and-disable interrupt body.
    ///
    /// # Safety
    /// The caller owns the current privileged CPU and saved-flag lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_disable_interrupt_save_bridge() -> CULong {
    unsafe { super::cpu_disable_interrupt_save() }
    }

    /// Restore the same caller-supplied interrupt flags.
    ///
    /// # Safety
    /// Flags must belong to the original pinned-CPU interrupt-save operation.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_restore_interrupt_bridge(flags: CULong) {
    unsafe { super::cpu_restore_interrupt(flags); }
    }

    /// Read the same MSR through the existing Rust provider.
    ///
    /// # Safety
    /// The original legal MSR index and privileged CPU ownership must hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_read_msr_bridge(register: CInt) -> CULong {
    unsafe { super::rdmsr(register as u32) }
    }

    /// Write the same MSR through the existing Rust provider.
    ///
    /// # Safety
    /// The original legal MSR/value and privileged CPU ownership must hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_write_msr_bridge(register: CInt, value: CULong) {
    unsafe { super::wrmsr(register as u32, value); }
    }

    /// Forward the same actual C-ABI fixed mapping request.
    ///
    /// # Safety
    /// The original mapping ownership and physical span must hold. Preserve the
    /// C int parameter boundary; do not silently change it to a Rust u64 flag.
    #[no_mangle]
    pub unsafe extern "C" fn x86_map_fixed_area_bridge(
        physical: CULong,
        size: CULong,
        uncached: CInt,
    ) -> *mut c_void {
    unsafe { c_map_fixed_area(physical, size, uncached) }
    }

    /// Forward the same complete existing node-allocation ABI.
    ///
    /// # Safety
    /// All allocator flags/spans/node/user/diagnostic-pointer lifetime contracts
    /// of the real existing allocator apply; no pointer is retained here.
    #[no_mangle]
    pub unsafe extern "C" fn x86_alloc_aligned_pages_node_bridge(
        pages: CInt,
        alignment: CInt,
        flags: CULong,
        node: CInt,
        user: CInt,
        virtual_address: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void {
    unsafe { allocate_node(pages, alignment, flags, node, user, virtual_address, file, line) }
    }

    /// Forward the same existing physical-address translation.
    ///
    /// # Safety
    /// The address must satisfy the original real translation provider contract.
    #[no_mangle]
    pub unsafe extern "C" fn x86_virt_to_phys_bridge(address: *mut c_void) -> CULong {
    unsafe { c_virt_to_phys(address) }
    }

    /// Return the same current CPU identity.
    ///
    /// # Safety
    /// Retain the original CPU-local initialization and pinned-CPU contract.
    #[no_mangle]
    pub unsafe extern "C" fn x86_current_cpu_bridge() -> CInt {
    unsafe { crate::x86_local::ihk_mc_get_processor_id() }
    }

    /// Reuse the same existing Rust KVM detection body.
    ///
    /// # Safety
    /// Retain the original CPUID and CPU initialization contracts.
    #[no_mangle]
    pub unsafe extern "C" fn x86_running_on_kvm_bridge() -> CInt {
    unsafe { super::running_on_kvm() }
    }

    /// Return the same CPUID6 EAX then ECX outputs.
    ///
    /// # Safety
    /// Both output spans must be live/writable u64 objects as in C. This is the
    /// existing selected leaf6 contract, not arbitrary HOST feature eligibility.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpuid6_bridge(eax: *mut CULong, ecx: *mut CULong) {
    unsafe {
        let result = core::arch::x86_64::__cpuid_count(6, 0);
        eax.write(result.eax as CULong);
        ecx.write(result.ecx as CULong);
    }
    }

    /// Return the same selected CPUID leaf EDX.
    ///
    /// # Safety
    /// The output span is writable u64. Actual current callers use leaves whose
    /// subleaf is immaterial; arbitrary subleaf semantics are not newly promised.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpuid_edx_bridge(operation: CULong, edx: *mut CULong) {
    unsafe {
        let result = core::arch::x86_64::__cpuid_count(operation as u32, 0);
        edx.write(result.edx as CULong);
    }
    }

    /// Return the same selected leaf outputs in original source order.
    ///
    /// # Safety
    /// The four C output spans are writable u64 objects, with original aliasing
    /// allowed. Reuse the existing native CPUID core and its selected-leaf scope.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpuid_leaf_bridge(
        operation: CULong,
        eax: *mut CULong,
        ebx: *mut CULong,
        ecx: *mut CULong,
        edx: *mut CULong,
    ) {
    unsafe { super::x86_native_cpuid_leaf(operation, eax, ebx, ecx, edx); }
    }

    /// Call the same existing page-attribute NX provider.
    ///
    /// # Safety
    /// Preserve the original boot page-table and publication ownership contract.
    #[no_mangle]
    pub unsafe extern "C" fn x86_enable_ptattr_no_execute_bridge() {
    unsafe { enable_ptattr_no_execute(); }
    }

    /// Read the same actual C CPU-info ncpus field.
    ///
    /// # Safety
    /// The existing accessor returns a live actual C CPU-info object; immutable
    /// C offsetof data is witnessed against that real header, not a model type.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_info_ncpus_bridge() -> CInt {
    unsafe {
        let info = c_cpu_info().cast::<u8>();
        info.add(x86_cpu_info_ncpus_offset as usize).cast::<CInt>().read()
    }
    }

    /// Call the same existing Rust processor-local initializer.
    ///
    /// # Safety
    /// Retain the original boot allocation/CPU-count and singleton ownership.
    #[no_mangle]
    pub unsafe extern "C" fn x86_init_processors_local_bridge(maximum: CInt) {
    unsafe { crate::x86_local::init_processors_local(maximum); }
    }

    /// Return the same current architecture kernel stack.
    ///
    /// # Safety
    /// The actual current architecture CPU-local object/stack remains live.
    #[no_mangle]
    pub unsafe extern "C" fn x86_this_kstack_bridge() -> *mut c_void {
    unsafe { c_current_stack() }
    }

    /// Return the same actual boot-status slot without a read.
    ///
    /// # Safety
    /// The caller retains the original boot-status volatile publication and
    /// lifetime contract; returning the raw slot adds no ownership or ACK.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_boot_status_slot_bridge() -> *mut CInt {
    addr_of_mut!(boot_status)
    }

    /// Read the same boot trampoline mapping slot.
    ///
    /// # Safety
    /// Boot owns the existing mapping slot and retains its mapped allocation.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_trampoline_va_bridge() -> *mut c_void {
    unsafe { addr_of!(trampoline).read() }
    }

    /// Return the same linker-provided trampoline byte start.
    ///
    /// # Safety
    /// The linker-provided code interval remains valid through its caller use.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_trampoline_code_data_bridge() -> *const u8 {
    addr_of!(trampoline_code_data)
    }

    /// Return the same linker-provided trampoline byte distance.
    ///
    /// # Safety
    /// The two actual linker boundary symbols must retain their original order
    /// and interval contract; no Rust same-allocation reference is invented.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_trampoline_code_size_bridge() -> CULong {
    (addr_of!(trampoline_code_data_end) as usize)
        .wrapping_sub(addr_of!(trampoline_code_data) as usize) as CULong
    }

    /// Read the same physical AP trampoline address.
    ///
    /// # Safety
    /// Retain the original boot publication of this real C physical-address slot.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_ap_trampoline_bridge() -> CULong {
    unsafe { addr_of!(ap_trampoline).read() }
    }

    /// Return the same selected setup_x86_ap function address.
    ///
    /// # Safety
    /// The caller must obey the genuine AP setup function/stack ABI and lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_setup_ap_bridge() -> *mut c_void {
    super::descriptor_load_and_ap_handoff_entries::setup_x86_ap as *const () as *mut c_void
    }

    /// Translate the same existing boot page-table pointer.
    ///
    /// # Safety
    /// The original boot page-table allocation and translation contract apply.
    #[no_mangle]
    pub unsafe extern "C" fn x86_boot_page_table_phys_bridge() -> CULong {
    unsafe { c_virt_to_phys(get_boot_page_table()) }
    }

    /// Return the same architecture kernel stack address for CPU.
    ///
    /// # Safety
    /// The original CPU index and architecture-local allocation remain valid.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_kstack_bridge(cpu: CInt) -> CULong {
    unsafe { get_x86_cpu_local_kstack(cpu) as CULong }
    }

    /// Call the same existing transit-page-table provider.
    ///
    /// # Safety
    /// The original boot page-table publication and lifetime contracts apply.
    #[no_mangle]
    pub unsafe extern "C" fn x86_transit_page_table_bridge() -> CULong {
    unsafe { get_transit_page_table() }
    }

    /// Call the same already ported AP wakeup transaction.
    ///
    /// # Safety
    /// The original APIC ID, trampoline, mapped controller and AP boot ownership
    /// contracts of the existing complete wakeup body must hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_wakeup_bridge(cpu: CInt, trampoline_address: CULong) {
    unsafe { super::x86_wakeup(cpu, trampoline_address); }
    }

    /// Call the same existing pause instruction provider.
    ///
    /// # Safety
    /// Retain the original polling/CPU context; no timeout or progress is added.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_pause_bridge() {
    unsafe { super::cpu_pause(); }
    }

    /// Return the same immutable actual C trace offsets descriptor.
    ///
    /// # Safety
    /// The real descriptor has boot/static lifetime and its actual C/Rust type
    /// witness must match. No descriptor contents or schema are invented here.
    #[no_mangle]
    pub unsafe extern "C" fn x86_trace_enter_user_offsets_bridge(
    ) -> *const super::X86TraceEnterUserOffsets {
    addr_of!(trace_offsets)
    }

    /// Read the same actual current-thread slot.
    ///
    /// # Safety
    /// The current CPU-local object and returned raw thread remain caller-owned
    /// through the original use. The returned pointer adds no lifetime hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_current_thread_bridge() -> *mut c_void {
    unsafe { addr_of!((*c_current_local()).current).read().cast() }
    }

    /// Return the same existing current CPU-local object.
    ///
    /// # Safety
    /// The caller retains the original CPU-local lifetime and CPU ownership.
    #[no_mangle]
    pub unsafe extern "C" fn x86_this_cpu_local_var_bridge() -> *mut c_void {
    unsafe { c_current_local().cast() }
    }

    /// Return the actual shared Rust CPU runqueue-lock offset.
    ///
    /// # Safety
    /// Actual current C/Rust CpuLocalVar layout equality remains required.
    #[no_mangle]
    pub unsafe extern "C" fn x86_runq_lock_offset_bridge() -> CULong {
    core::mem::offset_of!(CpuLocalVar, runq_lock) as CULong
    }

    /// Return the actual shared Rust saved runqueue-IRQ offset.
    ///
    /// # Safety
    /// Actual current C/Rust CpuLocalVar layout equality remains required.
    #[no_mangle]
    pub unsafe extern "C" fn x86_runq_irqstate_offset_bridge() -> CULong {
    core::mem::offset_of!(CpuLocalVar, runq_irqstate) as CULong
    }

    /// Call the same real selected spinlock unlock provider.
    ///
    /// # Safety
    /// The raw lock is a live actual IhkSpinlock owned by this saved-IRQ operation;
    /// retain original pinned CPU, lock lifetime and saved flags until unlock.
    #[no_mangle]
    pub unsafe extern "C" fn x86_runq_unlock_bridge(lock: *mut c_void, flags: CULong) {
    unsafe { c_spin_unlock(lock.cast(), flags); }
    }

    /// Call the same selected IPI transaction target.
    ///
    /// # Safety
    /// The real boot-selected callback and APIC destination/vector satisfy their
    /// original contracts; C implicitly narrowed both arguments to unsigned32.
    #[no_mangle]
    pub unsafe extern "C" fn x86_issue_ipi_bridge(apic_id: CULong, vector: CInt) {
    unsafe {
        addr_of!(x86_issue_ipi).read().unwrap_unchecked()(apic_id as u32, vector as u32);
    }
    }
}


// Exact descriptor storage ownership. Existing init/reload bodies keep every
// write, ordering, exclusion and hardware-lifetime requirement unchanged.
mod selected_descriptor_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::X86DescPtr;

    // The actual C table is 256 four-u32 entries with object alignment 16.
    // Its extent is already a multiple of that alignment; no tail grows.
    #[repr(C, align(16))]
    pub(crate) struct IdtStorage {
        words: [[u32; 4]; 256],
    }

    #[no_mangle]
    pub(crate) static mut x86_cpu_idt: IdtStorage = IdtStorage {
        words: [[0; 4]; 256],
    };

    const _: () = {
        assert!(size_of::<IdtStorage>() == size_of::<[[u32; 4]; 256]>());
        assert!(size_of::<IdtStorage>() == 4096);
        assert!(align_of::<IdtStorage>() == 16);
        assert!(offset_of!(IdtStorage, words) == 0);
        assert!(size_of::<X86DescPtr>() == 10);
        assert!(align_of::<X86DescPtr>() == 1);
        assert!(offset_of!(X86DescPtr, address) == 2);
    };

    // The real C objects are packed ten-byte descriptors, but the retained
    // selected GCC object gives each COMMON symbol alignment eight. A Rust
    // align(8) wrapper would grow their ELF extents to sixteen bytes. These
    // declarations allocate exactly ten zero bytes at alignment eight instead.
    // There are no instructions, pointer conversions, references or new stores.
    core::arch::global_asm!(
        ".pushsection .bss.x86_cpu_idt_desc,\"aw\",@nobits",
        ".balign 8",
        ".globl x86_cpu_idt_desc",
        ".type x86_cpu_idt_desc,@object",
        "x86_cpu_idt_desc:",
        ".zero {descriptor_bytes}",
        ".size x86_cpu_idt_desc,.-x86_cpu_idt_desc",
        ".popsection",
        ".pushsection .bss.gdt_desc,\"aw\",@nobits",
        ".balign 8",
        ".globl gdt_desc",
        ".type gdt_desc,@object",
        "gdt_desc:",
        ".zero {descriptor_bytes}",
        ".size gdt_desc,.-gdt_desc",
        ".popsection",
        descriptor_bytes = const size_of::<X86DescPtr>(),
    );
}


// Exact zero-initialized AP boot slots. Existing Rust producers and consumers
// retain their raw pointer ownership, volatile accesses and publication order.
mod selected_APboot_storage {
    use core::ffi::c_void;
    use core::mem::{align_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::CInt;

    #[no_mangle]
    pub(crate) static mut x86_cpu_trampoline_va: *mut c_void = null_mut();

    #[no_mangle]
    pub(crate) static mut x86_cpu_first_page_va: *mut c_void = null_mut();

    // Volatile is an access property. The original C alias keeps volatile int,
    // and existing Rust reads/writes remain volatile at their original sites.
    #[no_mangle]
    pub(crate) static mut x86_cpu_boot_status: CInt = 0;

    const _: () = {
        assert!(size_of::<*mut c_void>() == 8);
        assert!(align_of::<*mut c_void>() == 8);
        assert!(size_of::<CInt>() == 4);
        assert!(align_of::<CInt>() == 4);
    };
}


// Exact existing FPU capability/snapshot storage. XSAVE/XRSTOR/FINIT and their
// eligibility, ownership and fault behavior remain in the unchanged bodies.
mod selected_fp_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::CInt;

    #[repr(C, align(64))]
    pub(crate) struct InitialFpStorage {
        bytes: [u8; super::PAGE_SIZE as usize],
    }

    #[no_mangle]
    pub(crate) static mut x86_cpu_xsave_available: CInt = 0;

    #[no_mangle]
    pub(crate) static mut x86_cpu_xsave_size: CInt = 0;

    #[no_mangle]
    pub(crate) static mut x86_cpu_xsave_mask: u64 = 0;

    #[no_mangle]
    pub(crate) static mut x86_cpu_initial_fp_regs: InitialFpStorage = InitialFpStorage {
        bytes: [0; super::PAGE_SIZE as usize],
    };

    #[no_mangle]
    pub(crate) static mut x86_cpu_initial_fp_regs_available: CInt = 0;

    const _: () = {
        assert!(size_of::<CInt>() == 4);
        assert!(align_of::<CInt>() == 4);
        assert!(size_of::<u64>() == 8);
        assert!(align_of::<u64>() == 8);
        assert!(size_of::<InitialFpStorage>() == super::PAGE_SIZE as usize);
        assert!(align_of::<InitialFpStorage>() == 64);
        assert!(offset_of!(InitialFpStorage, bytes) == 0);
    };
}


// Initial GDT/TSS storage for the existing init_gdt and init_local_gdt bodies.
// This changes storage ownership only; no selector, publication or CPU operation.
mod selected_initial_descriptor_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{CULong, Tss64};

    #[repr(C, align(16))]
    pub(crate) struct GdtStorage {
        entries: [CULong; 16],
    }

    // These sixteen values are the complete retained C initializer, in order.
    // Boot owns mutation of the two existing TSS slots; per-CPU setup copies the
    // same 128 bytes under its original exclusion before descriptor publication.
    #[unsafe(no_mangle)]
    pub(crate) static mut gdt: GdtStorage = GdtStorage {
        entries: [
            0,
            0,
            0,
            0,
            0x00af_9b00_0000_ffff,
            0x00cf_9300_0000_ffff,
            0x00af_fb00_0000_ffff,
            0x00af_f300_0000_ffff,
            0x0000_8900_0000_0067,
            0,
            0,
            0,
            0,
            0,
            0,
            0x0000_f100_0000_0000,
        ],
    };

    const _: () = {
        assert!(size_of::<CULong>() == 8);
        assert!(size_of::<GdtStorage>() == 128);
        assert!(align_of::<GdtStorage>() == 16);
        assert!(offset_of!(GdtStorage, entries) == 0);
        assert!(size_of::<Tss64>() == 104);
        assert!(align_of::<Tss64>() == 1);
        assert!(offset_of!(Tss64, rsp0) == 4);
    };

    // C allocates exactly 104 zero bytes but aligns this particular packed TSS
    // object to sixteen. An align(16) Rust wrapper would wrongly grow it to112.
    // Data assembly preserves both extent and alignment. It has no instructions,
    // typed unaligned accesses, references, fences or hardware publication.
    core::arch::global_asm!(
        ".pushsection .bss.tss,\"aw\",@nobits",
        ".balign 16",
        ".globl tss",
        ".type tss,@object",
        "tss:",
        ".zero {tss_bytes}",
        ".size tss,.-tss",
        ".popsection",
        tss_bytes = const size_of::<Tss64>(),
    );
}


// Zero storage for the existing init_idt, registration and mainIRQ consumers.
// List initialization still happens at its original point in init_idt; these
// are null pairs at image load, not prematurely self-linked list heads.
mod selected_handler_storage {
    use core::mem::{align_of, offset_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::AbiListHead;

    #[repr(C, align(32))]
    pub(crate) struct HandlerStorage {
        entries: [AbiListHead; 224],
    }

    // The actual selected GCC9 COMMON symbol has extent3584/alignment32.
    // The wrapper preserves that object alignment and has no tail growth.
    // Startup/registration retain their existing exclusion. This storage adds
    // no lifetime reference, lock, handler retention or IRQ publication rule.
    #[unsafe(no_mangle)]
    pub(crate) static mut handlers: HandlerStorage = HandlerStorage {
        entries: [AbiListHead {
            next: null_mut(),
            prev: null_mut(),
        }; 224],
    };

    const _: () = {
        assert!(size_of::<AbiListHead>() == 16);
        assert!(align_of::<AbiListHead>() == 8);
        assert!(offset_of!(AbiListHead, next) == 0);
        assert!(offset_of!(AbiListHead, prev) == 8);
        assert!(size_of::<HandlerStorage>() == 3584);
        assert!(align_of::<HandlerStorage>() == 32);
        assert!(offset_of!(HandlerStorage, entries) == 0);
    };
}


// Exact existing boot/PAT/pvclock state. The same startup and pvclock bodies
// own every mutation, volatile access and publication; no eager initialization
// or allocation, new synchronization, CPUID, MSR or hardware access is added.
mod selected_boot_clock_storage {
    use core::mem::{align_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::{CInt, CLong, CULong};

    use super::PvclockVsyscallTimeInfo;

    #[unsafe(no_mangle)]
    static mut boot_pat_state: CULong = 0;

    // The existing early kargs parser can still update this exact C symbol.
    #[unsafe(no_mangle)]
    static mut no_turbo: CInt = 1;

    // Reuse the already-consumed typed pointer. No pointee is allocated or
    // dereferenced here; arch_setup_pvclock retains its allocation/zero/order.
    #[unsafe(no_mangle)]
    static mut pvti: *mut PvclockVsyscallTimeInfo = null_mut();

    #[unsafe(no_mangle)]
    static mut pvti_npages: CInt = 0;

    #[unsafe(no_mangle)]
    static mut pvti_msr: CLong = -1;

    const _: () = {
        assert!(size_of::<CULong>() == 8);
        assert!(align_of::<CULong>() == 8);
        assert!(size_of::<CLong>() == 8);
        assert!(align_of::<CLong>() == 8);
        assert!(size_of::<CInt>() == 4);
        assert!(align_of::<CInt>() == 4);
        assert!(size_of::<*mut PvclockVsyscallTimeInfo>() == 8);
        assert!(align_of::<*mut PvclockVsyscallTimeInfo>() == 8);
    };
}


// The existing immutable trace descriptor, derived from actual shared Rust
// Thread/Process fields rather than a duplicate numeric C-offset table.
mod selected_trace_offset_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{CULong, Process, Thread};

    use super::X86TraceEnterUserOffsets;

    #[unsafe(no_mangle)]
    static x86_trace_enter_user_offsets: X86TraceEnterUserOffsets = X86TraceEnterUserOffsets {
        thread_tid_offset: offset_of!(Thread, tid) as CULong,
        thread_status_offset: offset_of!(Thread, status) as CULong,
        thread_proc_offset: offset_of!(Thread, proc) as CULong,
        process_pid_offset: offset_of!(Process, pid) as CULong,
    };

    const _: () = {
        assert!(size_of::<X86TraceEnterUserOffsets>() == 32);
        assert!(align_of::<X86TraceEnterUserOffsets>() == align_of::<CULong>());
        assert!(offset_of!(X86TraceEnterUserOffsets, thread_tid_offset) == 0);
        assert!(offset_of!(X86TraceEnterUserOffsets, thread_status_offset) == 8);
        assert!(offset_of!(X86TraceEnterUserOffsets, thread_proc_offset) == 16);
        assert!(offset_of!(X86TraceEnterUserOffsets, process_pid_offset) == 24);
    };
}


// Existing syscall-handler address slot. Existing setters/entry code keep their
// original function-pointer ownership and privilege contracts. Use the same raw
// CULong storage view already consumed by the accepted Rust setters, so all bits
// remain representable without introducing an Option/function-pointer validity
// assumption or a new handler lifetime/reference protocol.
mod selected_syscall_handler_slot {
    use core::mem::{align_of, size_of};

    use crate::abi::CULong;

    #[unsafe(no_mangle)]
    static mut __x86_syscall_handler: CULong = 0;

    const _: () = {
        assert!(size_of::<CULong>() == 8);
        assert!(align_of::<CULong>() == 8);
    };
}


// Existing gettime support publication and FP-image extent. No CPUID/MSR/FPU
// instruction is introduced here; the unchanged bodies retain their calls,
// volatile stores, startup exclusion and eligibility checks.
mod selected_time_fp_extent_storage {
    use core::mem::{align_of, size_of};

    use crate::abi::{CInt, CULong};

    use super::selected_fp_storage::InitialFpStorage;

    #[unsafe(no_mangle)]
    static mut gettime_local_support: CInt = 0;

    #[unsafe(no_mangle)]
    static x86_initial_fp_regs_extent: CULong = size_of::<InitialFpStorage>() as CULong;

    const _: () = {
        assert!(size_of::<CInt>() == 4);
        assert!(align_of::<CInt>() == 4);
        assert!(size_of::<CULong>() == 8);
        assert!(size_of::<InitialFpStorage>() == super::PAGE_SIZE as usize);
    };
}

// Selected architecture-header policy, not the Rust instruction target features.
// The source-bound build producer must provide this value from the selected march.h.
// Missing or malformed producer input is a compile error, never an assumed disable.
mod selected_fp_sse_policy {
    use crate::abi::CInt;

    const fn decode(value: &[u8]) -> CInt {
        assert!(value.len() == 1, "selected SSE policy must be one byte");
        assert!(value[0] == b'0' || value[0] == b'1', "invalid selected SSE policy");
        (value[0] - b'0') as CInt
    }

    #[no_mangle]
    pub static x86_cpu_fp_sse_enabled: CInt =
        decode(env!("MCKERNEL_X86_ENABLE_SSE").as_bytes());
}

// Exact three-field declaration from the selected lib/include/ihk/cpu.h.
// This representation only constructs immutable geometry; it does not authorize
// dereferencing handler storage or extend any registration/callback lifetime.
mod selected_irq_handler_geometry {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{AbiListHead, CULong};

    type InterruptCallback = Option<unsafe extern "C" fn(*mut c_void)>;

    #[repr(C)]
    struct InterruptHandler {
        list: AbiListHead,
        func: InterruptCallback,
        private: *mut c_void,
    }

    #[no_mangle]
    pub static x86_main_irq_handler_layout: [CULong; 9] = [
        size_of::<InterruptHandler>() as CULong,
        align_of::<InterruptHandler>() as CULong,
        offset_of!(InterruptHandler, list) as CULong,
        offset_of!(InterruptHandler, func) as CULong,
        offset_of!(InterruptHandler, private) as CULong,
        size_of::<InterruptCallback>() as CULong,
        size_of::<*mut c_void>() as CULong,
        size_of::<AbiListHead>() as CULong,
        offset_of!(AbiListHead, next) as CULong,
    ];
}

// Writable existing dynamic-debug records, preserving the real Ddebug ABI.
// C __FILE__ is an input of the producer: Rust file!() identifies a different file.
// Missing producer input deliberately fails compilation; no source name is guessed.
mod selected_cpu_verbose_records {
    use crate::debug::Ddebug;

    const FILE: &[u8] = concat!(env!("MCKERNEL_CPU_C_FILE"), "\0").as_bytes();

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_init_fpu_debug: [Ddebug; 6] = [
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 712,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 718,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 728,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 735,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 740,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"init_fpu\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 744,
        },
    ];

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_cpu_setup_log_debug: Ddebug = Ddebug {
        file: FILE.as_ptr().cast(),
        func: b"x86_cpu_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 1104,
    };

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_tick_log_debug: [Ddebug; 3] = [
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_tick_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1720,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_tick_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1723,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_tick_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1726,
        },
    ];

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_pvclock_log_debug: [Ddebug; 11] = [
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1735,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1738,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1741,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1744,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1747,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1750,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1753,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1759,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1762,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1765,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"x86_pvclock_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 1768,
        },
    ];

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_main_irq_debug: [Ddebug; 2] = [
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"handle_interrupt\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 2086,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"handle_interrupt\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 2158,
        },
    ];

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_interrupt_log_debug: Ddebug = Ddebug {
        file: FILE.as_ptr().cast(),
        func: b"x86_interrupt_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3140,
    };

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_switch_context_debug: Ddebug = Ddebug {
        file: FILE.as_ptr().cast(),
        func: b"arch_switch_context\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3168,
    };

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_multi_nmi_debug: [Ddebug; 2] = [
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"multi_nm_interrupt_handler\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 3854,
        },
        Ddebug {
            file: FILE.as_ptr().cast(),
            func: b"multi_nm_interrupt_handler\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 3859,
        },
    ];
}

// Both languages already select these policies from the same CMake options.
// This moves the immutable view only; arch_switch_context ordering is unchanged.
mod selected_switch_context_policy {
    use crate::abi::CInt;

    #[no_mangle]
    pub static x86_switch_context_perf_enabled: CInt = cfg!(enable_perf) as CInt;

    #[no_mangle]
    pub static x86_switch_context_profile_enabled: CInt = cfg!(enable_profile) as CInt;
}

// Immutable address initializers only: no instructions, loads, dereferences or
// callback calls. Existing typed declarations still govern every consumer.
// Each target is the actual Rust-owned slot already qualified in the CPU81
// data proof; the exact one-address relocation remains to be checked for this
// new source. Readonly assembly data avoids inventing a Sync pointer wrapper or
// converting a pointer to an integer during Rust const evaluation.
core::arch::global_asm!(
    r#"
    .pushsection .rodata.x86_wakeup_lapic_write_slot,"a",@progbits
    .balign 8
    .global x86_wakeup_lapic_write_slot
    .type x86_wakeup_lapic_write_slot,@object
x86_wakeup_lapic_write_slot:
    .quad lapic_write
    .size x86_wakeup_lapic_write_slot,8
    .popsection
    .pushsection .rodata.x86_wakeup_lapic_read_slot,"a",@progbits
    .balign 8
    .global x86_wakeup_lapic_read_slot
    .type x86_wakeup_lapic_read_slot,@object
x86_wakeup_lapic_read_slot:
    .quad lapic_read
    .size x86_wakeup_lapic_read_slot,8
    .popsection
    .pushsection .rodata.x86_wakeup_wait_slot,"a",@progbits
    .balign 8
    .global x86_wakeup_wait_slot
    .type x86_wakeup_wait_slot,@object
x86_wakeup_wait_slot:
    .quad lapic_wait_icr_idle
    .size x86_wakeup_wait_slot,8
    .popsection
    .pushsection .rodata.x86_wakeup_first_page_slot,"a",@progbits
    .balign 8
    .global x86_wakeup_first_page_slot
    .type x86_wakeup_first_page_slot,@object
x86_wakeup_first_page_slot:
    .quad x86_cpu_first_page_va
    .size x86_wakeup_first_page_slot,8
    .popsection
    .pushsection .rodata.x86_wakeup_boot_status_slot,"a",@progbits
    .balign 8
    .global x86_wakeup_boot_status_slot
    .type x86_wakeup_boot_status_slot,@object
x86_wakeup_boot_status_slot:
    .quad x86_cpu_boot_status
    .size x86_wakeup_boot_status_slot,8
    .popsection
    "#
);

// Reuse the real existing AP CPU-info type, also used by kernel/rust/init.rs.
// abi::IhkCpuInfo is a different control descriptor and must not substitute for
// struct ihk_mc_cpu_info merely because its name and first field look similar.
mod selected_cpu_info_offset {
    use core::mem::offset_of;

    use crate::abi::CULong;
    use crate::ap::IhkMcCpuInfo;

    #[no_mangle]
    pub static x86_cpu_info_ncpus_offset: CULong = offset_of!(IhkMcCpuInfo, ncpus) as CULong;
}

// Literal values transcribed from the exact selected C macro definitions.
// No build-dependent MAP_KERNEL_START or configuration policy is inferred here.
// Real-header object equality remains mandatory before these private providers
// can be integrated; alternate header values are not qualified by this source.
mod selected_fixed_cpu_selectors {
    use crate::abi::{CInt, CULong};
    use super::CUInt;

    // Existing cpu.c APIC_BASE_MSR definition, retained source value 0x800.
    #[no_mangle]
    pub static x86_local_apic_base_msr: CUInt = 0x800;

    // Selected march.h LAPIC_ICR_ID_SHIFT definition.
    #[no_mangle]
    pub static x86_ipi_icr_id_shift: CInt = 24;

    // Selected process.h PS_INTERRUPTIBLE, PS_UNINTERRUPTIBLE, PS_STOPPED, PS_TRACED.
    #[no_mangle]
    pub static x86_lookup_sleep_mask: CInt = 0x2 | 0x4 | 0x20 | 0x40;

    // Selected arch-memory.h USER_END definition.
    #[no_mangle]
    pub static x86_panic_user_end: CULong = 0x0000_8000_0000_0000;
}

// Descriptor shape uses the real existing Rust storage/types already qualified
// in CPU81. Selectors below are the literal selected arch-memory.h definitions,
// not a new selector policy. Every new array still needs real C object equality.
mod selected_descriptor_ap_geometry {
    use core::mem::{offset_of, size_of};

    use crate::abi::{CULong, X86DescPtr};

    const KERNEL_CS: CULong = 4 * 8;
    const KERNEL_DS: CULong = 5 * 8;
    const USER_CS: CULong = 6 * 8 + 3;
    const USER_DS: CULong = 7 * 8 + 3;
    const GLOBAL_TSS_ENTRY: CULong = 8;
    const GLOBAL_TSS: CULong = GLOBAL_TSS_ENTRY * 8;

    #[no_mangle]
    pub static x86_idt_geometry: [CULong; 9] = [
        size_of::<super::selected_descriptor_storage::IdtStorage>() as CULong,
        size_of::<[u32; 4]>() as CULong,
        size_of::<[u32; 4]>() as CULong,
        size_of::<X86DescPtr>() as CULong,
        offset_of!(X86DescPtr, size) as CULong,
        offset_of!(X86DescPtr, address) as CULong,
        size_of::<u16>() as CULong,
        size_of::<u64>() as CULong,
        KERNEL_CS,
    ];

    #[no_mangle]
    pub static x86_gdt_geometry: [CULong; 2] = [
        size_of::<super::selected_initial_descriptor_storage::GdtStorage>() as CULong,
        GLOBAL_TSS_ENTRY,
    ];

    #[no_mangle]
    pub static x86_gdt_reload_geometry: [CULong; 3] = [KERNEL_CS, KERNEL_DS, GLOBAL_TSS];

    // AP_TRAMPOLINE_SIZE is exactly 0x2000 in the selected arch-memory.h.
    // PAGE_SIZE reuses the existing module constant, not another page-size model.
    #[no_mangle]
    pub static x86_ap_init_geometry: [CULong; 2] = [0x2000, super::PAGE_SIZE];

    // registers.h RFLAGS_IF is (1 << 9); existing exit code uses that same bit.
    #[no_mangle]
    pub static x86_user_start_geometry: [CULong; 3] = [USER_CS, USER_DS, 1 << 9];
}

// Existing main-IRQ table order is part of the current private consumer contract.
// Values below transcribe the exact selected C enum/macro definitions recorded
// in this source packet. This does not execute/authorize the IRQ transaction,
// prove its post-unlock lifetimes or change any EOI/callback/locking order.
mod selected_main_irq_constants {
    use crate::abi::CULong;

    #[no_mangle]
    pub static x86_main_irq_constants: [CULong; 23] = [
        1, // CPUTIME_MODE_U2K
        2, // CPUTIME_MODE_K2K_IN
        0, // CPUTIME_MODE_K2U
        3, // CPUTIME_MODE_K2K_OUT
        0x1, // CPU_FLAG_NEED_RESCHED
        0x2, // CPU_FLAG_NEED_MIGRATE
        0xef, // LOCAL_TIMER_VECTOR
        0xf0, // LOCAL_PERF_VECTOR
        0x340, // LAPIC_LVTPC
        0x38e, // MSR_PERF_GLOBAL_STATUS
        0x390, // MSR_PERF_GLOBAL_OVF_CTRL
        68, // IHK_TLB_FLUSH_IRQ_VECTOR_START
        68 + 64, // IHK_TLB_FLUSH_IRQ_VECTOR_END
        0xf1, // LOCAL_SMP_FUNC_CALL_VECTOR
        8, // SIGFPE
        1, // FPE_INTDIV
        11, // SIGSEGV
        4, // SIGILL
        2, // ILL_ILLOPN
        7, // SIGBUS
        1, // BUS_ADRALN
        29, // SIGIO
        256 - 32, // 256-32
    ];
}

// Fixed selected-header/CPU macro arrays. Values retain the original expressions
// and table order; original C-expression witnesses are frozen alongside this code.
// These immutable providers do not publish hardware state or run AP/IRQ actions.
mod selected_remaining_cpu_arrays {
    use crate::abi::CULong;
    use super::CUInt;

    // IA32_X2APIC_ICR, LAPIC_ICR2, LAPIC_ICR0, APIC_ICR_BUSY.
    #[no_mangle]
    pub static x86_icr_geometry: [CULong; 4] = [0x830, 0x310, 0x300, 0x1000];

    #[no_mangle]
    pub static x86_init_geometry: [CULong; 11] = [
        0x1b, // MSR_IA32_APIC_BASE, distinct from the existing 0x800 enable mask.
        !(super::PAGE_SIZE - 1), // PAGE_MASK uses the existing unsigned-long page size.
        super::PAGE_SIZE,
        0x800,
        0x277, // MSR_IA32_CR_PAT.
        0xc000_0080, // MSR_EFER.
        0xc000_0081, // MSR_STAR.
        0xc000_0082, // MSR_LSTAR.
        4 * 8, // KERNEL_CS.
        6 * 8 + 3, // USER_CS.
        1 << 11,
    ];

    #[no_mangle]
    pub static x86_smp_init_geometry: [CULong; 6] = [
        0x802, // IA32_X2APIC_APICID.
        0x020, // LAPIC_ID.
        24, // LAPIC_ID_SHIFT.
        8, // GLOBAL_TSS_ENTRY.
        15, // GETCPU_ENTRY.
        0xc000_0103,
    ];

    #[no_mangle]
    pub static x86_switch_context_geometry: [CULong; 6] = [
        0x200, // PS_DELAY_STOPPED.
        0x400, // PS_DELAY_TRACED.
        0x20, // PS_STOPPED.
        0x40, // PS_TRACED.
        1, // PP_RESET.
        2, // PP_COUNT.
    ];

    #[no_mangle]
    pub static x86_wakeup_constants: [CUInt; 5] = [
        0x280, // LAPIC_ESR.
        0x8000, // APIC_INT_LEVELTRIG.
        0x4000, // APIC_INT_ASSERT.
        0x500, // APIC_DM_INIT.
        0x600, // APIC_DM_STARTUP.
    ];
}

// The actual current CPU81 compiler profile leaves DEBUG_PRINT_CPU undefined.
// C compile guards reject an enabled-debug profile before it could silently
// observe these disabled values; that alternate producer is not qualified.
mod selected_exception_debug_policy {
    use super::CUInt;

    #[no_mangle]
    pub static x86_debug_handler_debug_print_enabled: CUInt = 0;

    #[no_mangle]
    pub static x86_int3_debug_print_enabled: CUInt = 0;
}
