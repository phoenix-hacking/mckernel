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
    fn __kprintf(format: *const i8, ...) -> CInt;
    fn snprintf(buf: *mut i8, size: usize, format: *const i8, ...) -> CInt;
    fn arch_delay(us: CInt);
    fn do_arch_prctl(code: CULong, address: CULong) -> CLong;
    fn x86_lapic_write_bridge(reg: CInt, value: CUInt);
    fn x86_read_msr_bridge(reg: CInt) -> CULong;
    fn x86_issue_ipi_bridge(apic_id: CULong, vector: CInt);
    fn x86_interrupt_log_bridge(event: CInt, cpu: CInt, vector: CInt);
    fn x86_tick_log_bridge(event: CInt);
    fn x86_pvclock_log_bridge(event: CInt);
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
    fn x86_print_stack_bridge(rbp: *mut c_void, first: CULong);
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
    unsafe {
        write_volatile(
            base.wrapping_add(kernel_stack_offset as usize) as *mut CULong,
            stack_pointer,
        );
        write_volatile(
            base.wrapping_add(tss_rsp0_offset as usize) as *mut CULong,
            stack_pointer,
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
