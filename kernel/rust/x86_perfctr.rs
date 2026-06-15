use core::{arch::asm, ffi::c_void, mem::offset_of, ptr::read_volatile};

use crate::abi::{CInt, CLong, CULong, IhkAtomic64, Thread};

const EINVAL: CInt = 22;
const X86_CR4_PCE: CULong = 0x0000_0100;
const PERFCTR_USER_MODE: CInt = 0x01;
const PERFCTR_KERNEL_MODE: CInt = 0x02;
const BASE_FIXED_PERF_COUNTERS: CInt = 32;
const MSR_IA32_PMC0: u32 = 0x0000_00c1;
const MSR_IA32_PERFEVTSEL0: u32 = 0x0000_0186;
const MSR_IA32_FIXED_CTR0: u32 = 0x0000_0309;
const MSR_PERF_FIXED_CTRL: u32 = 0x0000_038d;
const MSR_PERF_GLOBAL_CTRL: u32 = 0x0000_038f;
const MSR_OFFCORE_RSP_0: u32 = 0x0000_01a6;
const MSR_OFFCORE_RSP_1: u32 = 0x0000_01a7;
const EXTRA_REG_RSP_0: CInt = 0;
const EXTRA_REG_RSP_1: CInt = 1;
const PERF_TYPE_HARDWARE: u32 = 0;
const PERF_TYPE_RAW: u32 = 4;
const PERF_COUNT_HW_INSTRUCTIONS: CULong = 1;
const PERF_COUNT_HW_INSTRUCTIONS_RAW: CULong = 0x5300c0;
const COUNTER_VALUE_MASK: CULong = 0x0000_00ff_ffff_ffff;
const PERF_EVENT_ATTR_SAMPLE_PERIOD_OFFSET: usize = 16;
const START_ERR_FMT: &[u8] = b"%s,counter_mask out of range\n\0";
const STOP_ERR_FMT: &[u8] = b"%s,counter_mask out of range\n\0";
const START_NAME: &[u8] = b"ihk_mc_perfctr_start\0";
const STOP_NAME: &[u8] = b"ihk_mc_perfctr_stop\0";
const DISCOVERED_FMT: &[u8] = b"NUM_PERF_COUNTERS: %d, NUM_FIXED_PERF_COUNTERS: %d\n\0";

#[repr(C, align(8))]
pub struct PerfEventAttrOpaque {
    data: [u8; 104],
}

#[repr(C)]
struct PerfEventAttrSamplePeriodPrefix {
    typ: u32,
    size: u32,
    config: CULong,
    sample_period: CULong,
}

#[repr(C)]
pub struct HwPerfEventExtra {
    pub config: CULong,
    pub reg: u32,
    pub idx: CInt,
}

#[repr(C)]
pub struct McPerfEvent {
    pub attr: PerfEventAttrOpaque,
    pub extra_reg: HwPerfEventExtra,
    pub hw_config: CULong,
}

extern "C" {
    fn running_on_kvm() -> CInt;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut crate::abi::CpuLocalVar;
    fn ihk_mc_get_extra_reg_event(id: CInt) -> CULong;
}

#[no_mangle]
pub static mut perf_counters_discovered: CInt = 0;
#[no_mangle]
pub static mut NUM_PERF_COUNTERS: CInt = 0;
#[no_mangle]
pub static mut PERF_COUNTERS_MASK: CULong = 0;
#[no_mangle]
pub static mut NUM_FIXED_PERF_COUNTERS: CInt = 0;
#[no_mangle]
pub static mut FIXED_PERF_COUNTERS_MASK: CULong = 0;

#[inline(always)]
unsafe fn read_cr4() -> CULong {
    let reg: CULong;
    unsafe {
        asm!("mov {}, cr4", out(reg) reg, options(nomem, nostack, preserves_flags));
    }
    reg
}

#[inline(always)]
unsafe fn write_cr4(reg: CULong) {
    unsafe {
        asm!("mov cr4, {}", in(reg) reg, options(nomem, nostack, preserves_flags));
    }
}

#[inline(always)]
unsafe fn rdmsr(index: u32) -> CULong {
    let low: u32;
    let high: u32;
    unsafe {
        asm!(
            "rdmsr",
            in("ecx") index,
            lateout("eax") low,
            lateout("edx") high,
            options(nomem, nostack, preserves_flags)
        );
    }
    ((high as CULong) << 32) | (low as CULong)
}

#[inline(always)]
unsafe fn wrmsr(index: u32, value: CULong) {
    let low = value as u32;
    let high = (value >> 32) as u32;
    unsafe {
        asm!(
            "wrmsr",
            in("ecx") index,
            in("eax") low,
            in("edx") high,
            options(nostack, preserves_flags)
        );
    }
}

#[inline(always)]
unsafe fn rdpmc(counter: CInt) -> CULong {
    let low: u32;
    let high: u32;
    unsafe {
        asm!(
            "rdpmc",
            in("ecx") counter as u32,
            lateout("eax") low,
            lateout("edx") high,
            options(nomem, nostack, preserves_flags)
        );
    }
    ((high as CULong) << 32) | (low as CULong)
}

#[inline(always)]
fn mask_for_count(count: CInt) -> CULong {
    if count <= 0 {
        0
    } else if count as usize >= CULong::BITS as usize {
        !0
    } else {
        (1_u64 << (count as u32)) as CULong - 1
    }
}

#[inline(always)]
fn counter_bit(counter: CInt) -> CULong {
    1_u64.wrapping_shl(counter as u32) as CULong
}

#[inline(always)]
fn perf_errno(errno: CInt) -> CULong {
    (-(errno as CLong)) as CULong
}

#[inline(always)]
fn cval2(event: CInt, mask: CInt, inv: CInt, count: CInt) -> u32 {
    (((event as u32 & 0xf00) << 24)
        | ((mask as u32) << 8)
        | (event as u32 & 0xff)
        | (((inv as u32) & 1) << 23)
        | (((count as u32) & 0xff) << 24)) as u32
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_perfctr() {
    #[cfg(not(enable_perf))]
    {
        return;
    }

    #[cfg(enable_perf)]
    unsafe {
        if running_on_kvm() != 0 {
            return;
        }

        write_cr4(read_cr4() | X86_CR4_PCE);

        if perf_counters_discovered == 0 {
            let cpuid = core::arch::x86_64::__cpuid(0x0a);
            NUM_PERF_COUNTERS = ((cpuid.eax & 0xff00) >> 8) as CInt;
            PERF_COUNTERS_MASK = mask_for_count(NUM_PERF_COUNTERS);
            NUM_FIXED_PERF_COUNTERS = (cpuid.edx & 0x0f) as CInt;
            FIXED_PERF_COUNTERS_MASK =
                mask_for_count(NUM_FIXED_PERF_COUNTERS) << BASE_FIXED_PERF_COUNTERS;
            perf_counters_discovered = 1;
            kprintf(
                DISCOVERED_FMT.as_ptr().cast(),
                NUM_PERF_COUNTERS,
                NUM_FIXED_PERF_COUNTERS,
            );
        }

        let mut value = rdmsr(MSR_PERF_FIXED_CTRL);
        value &= 0xffff_ffff_ffff_f000;
        wrmsr(MSR_PERF_FIXED_CTRL, value);

        let mut i = 0;
        while i < NUM_PERF_COUNTERS {
            wrmsr(MSR_IA32_PERFEVTSEL0 + i as u32, 0);
            i += 1;
        }

        value = rdmsr(MSR_PERF_GLOBAL_CTRL);
        value |= PERF_COUNTERS_MASK;
        value |= FIXED_PERF_COUNTERS_MASK;
        wrmsr(MSR_PERF_GLOBAL_CTRL, value);
    }
}

unsafe fn set_perfctr_x86_direct(counter: CInt, mode: CInt, mut value: u32) -> CInt {
    unsafe {
        if counter < 0 || counter >= NUM_PERF_COUNTERS {
            return -EINVAL;
        }

        value &= !(3 << 16);
        if mode & PERFCTR_USER_MODE != 0 {
            value |= 1 << 16;
        }
        if mode & PERFCTR_KERNEL_MODE != 0 {
            value |= 1 << 17;
        }

        value |= 1 << 22;
        value |= 1 << 18;
        value |= 1 << 20;

        wrmsr(MSR_IA32_PERFEVTSEL0 + counter as u32, value as CULong);
        0
    }
}

unsafe fn set_pmc_x86_direct(counter: CInt, mut val: CLong) -> CInt {
    if counter < 0 {
        return -EINVAL;
    }

    val &= COUNTER_VALUE_MASK as CLong;
    let cnt_bit = counter_bit(counter);

    unsafe {
        if cnt_bit & PERF_COUNTERS_MASK != 0 {
            wrmsr(MSR_IA32_PMC0 + counter as u32, val as CULong);
        } else if cnt_bit & FIXED_PERF_COUNTERS_MASK != 0 {
            wrmsr(
                MSR_IA32_FIXED_CTR0 + (counter - BASE_FIXED_PERF_COUNTERS) as u32,
                val as CULong,
            );
        } else {
            return -EINVAL;
        }
    }
    0
}

unsafe fn set_perfctr_x86(
    counter: CInt,
    event: CInt,
    mask: CInt,
    inv: CInt,
    count: CInt,
    mode: CInt,
) -> CInt {
    unsafe { set_perfctr_x86_direct(counter, mode, cval2(event, mask, inv, count)) }
}

unsafe fn set_fixed_counter(counter: CInt, mode: CInt, enable_overflow: bool) -> CInt {
    let counter_idx = counter - BASE_FIXED_PERF_COUNTERS;
    unsafe {
        if counter_idx < 0 || counter_idx >= NUM_FIXED_PERF_COUNTERS {
            return -EINVAL;
        }

        let mut value = rdmsr(MSR_PERF_FIXED_CTRL);
        let mut ctr_mask: CULong = 0xf;
        ctr_mask <<= (counter_idx * 4) as u32;
        value &= !ctr_mask;

        let mut set_val: CULong = 0;
        if mode & PERFCTR_USER_MODE != 0 {
            set_val |= 1 << 1;
        }
        if mode & PERFCTR_KERNEL_MODE != 0 {
            set_val |= 1;
        }
        if enable_overflow {
            set_val |= 1 << 3;
        }

        set_val <<= (counter_idx * 4) as u32;
        value |= set_val;
        wrmsr(MSR_PERF_FIXED_CTRL, value);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_init_raw(counter: CInt, code: u32, mode: CInt) -> CInt {
    unsafe {
        if counter >= BASE_FIXED_PERF_COUNTERS
            && counter < BASE_FIXED_PERF_COUNTERS + NUM_FIXED_PERF_COUNTERS
        {
            return set_fixed_counter(counter, mode, true);
        }
        if counter < 0 || counter >= NUM_PERF_COUNTERS {
            return -EINVAL;
        }
        set_perfctr_x86_direct(counter, mode, code)
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_set_extra(event: *mut McPerfEvent) -> CInt {
    unsafe {
        let thread = (*get_cpu_local_var(ihk_mc_get_processor_id())).current;
        let mut idx = (*event).extra_reg.idx;

        if (*thread).extra_reg_alloc_map & counter_bit(idx) != 0 {
            if idx == EXTRA_REG_RSP_0 {
                idx = EXTRA_REG_RSP_1;
                (*event).extra_reg.idx = idx;
            } else if idx == EXTRA_REG_RSP_1 {
                idx = EXTRA_REG_RSP_0;
                (*event).extra_reg.idx = idx;
            }

            if (*thread).extra_reg_alloc_map & counter_bit(idx) != 0 {
                return -1;
            }
        }

        if idx == EXTRA_REG_RSP_0 {
            (*event).hw_config &= !0xff;
            (*event).hw_config |= ihk_mc_get_extra_reg_event(EXTRA_REG_RSP_0);
            (*event).extra_reg.reg = MSR_OFFCORE_RSP_0;
        } else if idx == EXTRA_REG_RSP_1 {
            (*event).hw_config &= !0xff;
            (*event).hw_config |= ihk_mc_get_extra_reg_event(EXTRA_REG_RSP_1);
            (*event).extra_reg.reg = MSR_OFFCORE_RSP_1;
        }

        (*thread).extra_reg_alloc_map |= counter_bit((*event).extra_reg.idx);
        wrmsr((*event).extra_reg.reg, (*event).extra_reg.config);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_start(counter_mask: CULong) -> CInt {
    unsafe {
        let mask = PERF_COUNTERS_MASK | FIXED_PERF_COUNTERS_MASK;
        if counter_mask & !mask != 0 {
            kprintf(START_ERR_FMT.as_ptr().cast(), START_NAME.as_ptr());
            return -EINVAL;
        }

        let counter_mask = counter_mask & mask;
        let value = rdmsr(MSR_PERF_GLOBAL_CTRL) | counter_mask;
        wrmsr(MSR_PERF_GLOBAL_CTRL, value);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_stop(counter_mask: CULong, _flags: CInt) -> CInt {
    unsafe {
        let mask = PERF_COUNTERS_MASK | FIXED_PERF_COUNTERS_MASK;
        if counter_mask & !mask != 0 {
            kprintf(STOP_ERR_FMT.as_ptr().cast(), STOP_NAME.as_ptr());
            return -EINVAL;
        }

        let counter_mask = counter_mask & mask;
        let mut value = rdmsr(MSR_PERF_GLOBAL_CTRL);
        value &= !counter_mask;
        wrmsr(MSR_PERF_GLOBAL_CTRL, value);

        if (counter_mask >> 32) & 0x1 != 0 {
            value = rdmsr(MSR_PERF_FIXED_CTRL);
            value &= !0xf;
            wrmsr(MSR_PERF_FIXED_CTRL, value);
        }
        if (counter_mask >> 32) & 0x2 != 0 {
            value = rdmsr(MSR_PERF_FIXED_CTRL);
            value &= !(0xf << 4);
            wrmsr(MSR_PERF_FIXED_CTRL, value);
        }
        if (counter_mask >> 32) & 0x4 != 0 {
            value = rdmsr(MSR_PERF_FIXED_CTRL);
            value &= !(0xf << 8);
            wrmsr(MSR_PERF_FIXED_CTRL, value);
        }
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_reset(counter: CInt) -> CInt {
    unsafe { set_pmc_x86_direct(counter, 0) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_set(counter: CInt, val: CLong) -> CInt {
    unsafe { set_pmc_x86_direct(counter, val) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_read_mask(
    mut counter_mask: CULong,
    value: *mut CULong,
) -> CInt {
    unsafe {
        let mut i = 0;
        let mut j = 0;
        while i < NUM_PERF_COUNTERS && counter_mask != 0 {
            if counter_mask & 1 != 0 {
                *value.add(j) = rdpmc(i);
                j += 1;
            }
            i += 1;
            counter_mask >>= 1;
        }
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_alloc(thread: *mut Thread, _event: *mut c_void) -> CInt {
    let mut ret = -EINVAL;
    let counters = unsafe { ihk_mc_perf_get_num_counters() };
    let mut i = 0;
    while i < counters {
        if unsafe { read_volatile(&(*thread).pmc_alloc_map) } & counter_bit(i) == 0 {
            ret = i;
            break;
        }
        i += 1;
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_read(counter: CInt) -> CULong {
    if counter < 0 {
        return perf_errno(EINVAL);
    }

    let cnt_bit = counter_bit(counter);
    unsafe {
        if cnt_bit & PERF_COUNTERS_MASK != 0 {
            rdpmc(counter)
        } else if cnt_bit & FIXED_PERF_COUNTERS_MASK != 0 {
            rdpmc((1 << 30) + (counter - BASE_FIXED_PERF_COUNTERS))
        } else {
            perf_errno(EINVAL)
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_value(counter: CInt, correction: CULong) -> CULong {
    unsafe { ihk_mc_perfctr_read(counter).wrapping_add(correction) & COUNTER_VALUE_MASK }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_read_msr(counter: CInt) -> CULong {
    if counter < 0 {
        return perf_errno(EINVAL);
    }

    let cnt_bit = counter_bit(counter);
    unsafe {
        if cnt_bit & PERF_COUNTERS_MASK != 0 {
            rdmsr(MSR_IA32_PMC0 + counter as u32)
        } else if cnt_bit & FIXED_PERF_COUNTERS_MASK != 0 {
            rdmsr(MSR_IA32_FIXED_CTR0 + counter as u32)
        } else {
            perf_errno(EINVAL)
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perfctr_alloc_counter(
    typ: *mut u32,
    config: *mut CULong,
    pmc_status: CULong,
) -> CInt {
    unsafe {
        if *typ == PERF_TYPE_HARDWARE {
            if *config == PERF_COUNT_HW_INSTRUCTIONS {
                *typ = PERF_TYPE_RAW;
                *config = PERF_COUNT_HW_INSTRUCTIONS_RAW;
            } else {
                return -1;
            }
        } else if *typ != PERF_TYPE_RAW {
            return -1;
        }

        let mut ret = -1;
        let mut i = 0;
        while i < NUM_PERF_COUNTERS {
            if pmc_status & counter_bit(i) == 0 {
                ret = i;
                break;
            }
            i += 1;
        }
        ret
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perf_counter_mask_check(counter_mask: CULong) -> CInt {
    unsafe {
        if (counter_mask & PERF_COUNTERS_MASK) | (counter_mask & FIXED_PERF_COUNTERS_MASK) != 0 {
            1
        } else {
            0
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_perf_get_num_counters() -> CInt {
    unsafe { NUM_PERF_COUNTERS }
}

#[no_mangle]
pub unsafe extern "C" fn hw_perf_event_init(_event: *mut McPerfEvent) -> CInt {
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_event_set_period(_event: *mut McPerfEvent) -> CInt {
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_event_update(_event: *mut McPerfEvent) -> u64 {
    0
}

#[no_mangle]
pub unsafe extern "C" fn is_sampling_event(event: *const McPerfEvent) -> CInt {
    unsafe {
        let sample_period = event
            .cast::<u8>()
            .add(offset_of!(McPerfEvent, attr) + PERF_EVENT_ATTR_SAMPLE_PERIOD_OFFSET)
            .cast::<CULong>();

        (read_volatile(sample_period) != 0) as CInt
    }
}

const _: () = {
    use core::mem::{align_of, size_of};

    assert!(size_of::<PerfEventAttrOpaque>() == 104);
    assert!(align_of::<PerfEventAttrOpaque>() == 8);
    assert!(
        offset_of!(PerfEventAttrSamplePeriodPrefix, sample_period)
            == PERF_EVENT_ATTR_SAMPLE_PERIOD_OFFSET
    );
    assert!(offset_of!(McPerfEvent, extra_reg) == 104);
    assert!(offset_of!(McPerfEvent, hw_config) == 120);
    let _ = size_of::<IhkAtomic64>();
    let _ = set_perfctr_x86 as unsafe fn(CInt, CInt, CInt, CInt, CInt, CInt) -> CInt;
    let _ = set_fixed_counter as unsafe fn(CInt, CInt, bool) -> CInt;
};
