#![allow(non_snake_case)]

use core::mem::size_of;

use crate::abi::{CInt, CULong, CpuSet, SizeT};

const CPU_MASK_BITS: SizeT = size_of::<CULong>() * 8;

#[inline(always)]
fn in_cpu_set_range(cpu: SizeT, setsize: SizeT) -> bool {
    cpu < setsize.wrapping_mul(8)
}

#[inline(always)]
fn cpu_word(cpu: SizeT) -> SizeT {
    cpu / CPU_MASK_BITS
}

#[inline(always)]
fn cpu_mask(cpu: SizeT) -> CULong {
    1u64 << (cpu % CPU_MASK_BITS)
}

#[no_mangle]
pub unsafe extern "C" fn CPU_SET_S(cpu: SizeT, setsize: SizeT, cpusetp: *mut CpuSet) -> CULong {
    if cpusetp.is_null() || !in_cpu_set_range(cpu, setsize) {
        return 0;
    }

    let word = unsafe { (cpusetp as *mut CULong).add(cpu_word(cpu)) };
    let value = unsafe { *word } | cpu_mask(cpu);
    unsafe {
        *word = value;
    }
    value
}

#[no_mangle]
pub unsafe extern "C" fn CPU_ISSET_S(cpu: SizeT, setsize: SizeT, cpusetp: *const CpuSet) -> CInt {
    if cpusetp.is_null() || !in_cpu_set_range(cpu, setsize) {
        return 0;
    }

    let word = unsafe { *((cpusetp as *const CULong).add(cpu_word(cpu))) };
    ((word & cpu_mask(cpu)) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn CPU_ZERO_S(setsize: SizeT, cpusetp: *mut CpuSet) {
    if cpusetp.is_null() {
        return;
    }

    let words = setsize / size_of::<CULong>();
    let base = cpusetp as *mut CULong;
    for word in 0..words {
        unsafe {
            *base.add(word) = 0;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn CPU_SET(cpu: SizeT, cpusetp: *mut CpuSet) -> CULong {
    unsafe { CPU_SET_S(cpu, size_of::<CpuSet>(), cpusetp) }
}

#[no_mangle]
pub unsafe extern "C" fn CPU_ISSET(cpu: SizeT, cpusetp: *const CpuSet) -> CInt {
    unsafe { CPU_ISSET_S(cpu, size_of::<CpuSet>(), cpusetp) }
}

#[no_mangle]
pub unsafe extern "C" fn CPU_ZERO(cpusetp: *mut CpuSet) {
    unsafe {
        CPU_ZERO_S(size_of::<CpuSet>(), cpusetp);
    }
}
