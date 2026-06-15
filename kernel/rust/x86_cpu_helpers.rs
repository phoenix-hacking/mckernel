use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong, X86KernelContext, X86UserContext};

type CUInt = u32;

const EINVAL: CInt = 22;
const LAPIC_TIMER: CInt = 0x320;
const LAPIC_LVTPC: CInt = 0x340;
const LAPIC_TIMER_INITIAL: CInt = 0x380;
const LAPIC_TIMER_DIVIDE: CInt = 0x3e0;
const LAPIC_SPURIOUS: CInt = 0x0f0;
const LAPIC_EOI: CInt = 0x0b0;
const LOCAL_TIMER_VECTOR: CUInt = 0xef;
const LOCAL_PERF_VECTOR: CUInt = 0xf0;
const APIC_DIVISOR: CUInt = 16;
const APIC_LVT_TIMER_PERIODIC: CUInt = 1 << 17;

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
type X86GetIntFn = unsafe extern "C" fn() -> CInt;
type X86InitProcessorsFn = unsafe extern "C" fn(CInt);
type X86DelayFn = unsafe extern "C" fn(CInt);

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
pub unsafe extern "C" fn x86_lapic_ack_body_result(write_fn: Option<X86LapicWriteFn>) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_EOI, 0);
    0
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

    disable_interrupt();
    init_idt();
    init_gdt();
    init_page_table();
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
