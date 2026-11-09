#![no_std]
// Exact current default-native CPU/local/physical credential dependency partition.
// No data initialization, logging provider, offload implementation or runtime entry.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt, CULong};
use core::ffi::c_void;

mod cls {
use crate::abi::{CInt, CpuLocalVar};
unsafe extern "C" {
    static mut clv: *mut CpuLocalVar;
    fn ihk_mc_get_processor_id() -> CInt;
}
#[no_mangle]
pub unsafe extern "C" fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar {
    clv.add(id as usize)
}

#[inline(always)]
unsafe fn this_cpu_local_var() -> *mut CpuLocalVar {
    get_cpu_local_var(ihk_mc_get_processor_id())
}

#[no_mangle]
pub unsafe extern "C" fn get_this_cpu_local_var() -> *mut CpuLocalVar {
    this_cpu_local_var()
}

}

mod x86_local {
use crate::abi::{CInt, CULong, X86CpuLocalVariables};
use core::arch::asm;
const PAGE_SIZE: usize = 4096;
const LOCALS_SPAN: usize = 4 * PAGE_SIZE;
const MSR_GS_BASE: u32 = 0xc000_0101;
unsafe extern "C" {
    static mut locals: *mut X86CpuLocalVariables;
    static mut num_processors: CInt;
}
#[inline(always)]
unsafe fn rdmsr(index: u32) -> CULong {
    let low: u32;
    let high: u32;
    asm!(
        "rdmsr",
        in("ecx") index,
        out("eax") low,
        out("edx") high,
        options(nomem, preserves_flags)
    );
    ((high as CULong) << 32) | low as CULong
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
    let gs = rdmsr(MSR_GS_BASE) as *mut u8;
    let local_base = locals as *mut u8;
    let local_end = local_base.add(LOCALS_SPAN.wrapping_mul(num_processors as usize));

    if gs < local_base || gs > local_end {
        return -1;
    }

    let id: CInt;
    asm!("mov {0:e}, gs:0", out(reg) id, options(nomem, preserves_flags));
    id
}

}

mod x86_memory_helpers {
use crate::abi::{CInt, CULong};
use core::ffi::c_void;
const MAP_FIXED_START: CULong = 0xffff860000000000;
const MAP_ST_START: CULong = 0xffff800000000000;
const X86_ADDR_LOG_KERNEL: CInt = 1;
const X86_ADDR_LOG_STRAIGHT: CInt = 2;
type X86AddrLogFn = unsafe extern "C" fn(CInt, CULong);
unsafe extern "C" {
    fn x86_addr_log_bridge(event: CInt, value: CULong);
    #[link_name = "x86_map_kernel_start_geometry"]
    static X86_MAP_KERNEL_START_GEOMETRY: CULong;
    #[link_name = "linux_page_offset_base"]
    static mut LINUX_PAGE_OFFSET_BASE: CULong;
    #[link_name = "x86_kernel_phys_base"]
    static mut X86_KERNEL_PHYS_BASE: CULong;
}
#[no_mangle]
pub unsafe extern "C" fn x86_virt_to_phys_body_result(
    va: CULong,
    map_kernel_start: CULong,
    kernel_phys_base: CULong,
    linux_page_offset_base: CULong,
    map_fixed_start: CULong,
    map_st_start: CULong,
    log_fn: Option<X86AddrLogFn>,
) -> CULong {
    if va >= map_kernel_start {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_ADDR_LOG_KERNEL, va);
            }
        }
        return va
            .wrapping_sub(map_kernel_start)
            .wrapping_add(kernel_phys_base);
    }
    if va >= linux_page_offset_base {
        return va.wrapping_sub(linux_page_offset_base);
    }
    if va >= map_fixed_start {
        return va.wrapping_sub(map_fixed_start);
    }

    if let Some(log) = log_fn {
        unsafe {
            log(X86_ADDR_LOG_STRAIGHT, va);
        }
    }
    va.wrapping_sub(map_st_start)
}

#[no_mangle]
pub unsafe extern "C" fn x86_user_map_kernel_start_bridge() -> CULong {
    // SAFETY: Typed readonly C address cells bind the real existing storage.
    // Reads match original plain C loads; there is no borrowed Rust reference.
    unsafe { X86_MAP_KERNEL_START_GEOMETRY }
}

#[no_mangle]
pub unsafe extern "C" fn virt_to_phys(v: *mut c_void) -> CULong {
    x86_virt_to_phys_body_result(
        v as CULong,
        x86_user_map_kernel_start_bridge(),
        X86_KERNEL_PHYS_BASE,
        LINUX_PAGE_OFFSET_BASE,
        MAP_FIXED_START,
        MAP_ST_START,
        Some(x86_addr_log_bridge),
    )
}

}

#[no_mangle]
pub unsafe extern "C" fn syscall_get_processor_id_bridge() -> CInt {
    // SAFETY: The original architecture entry is called under the same CPU context;
    // no MSR access, local-data read or fallback behavior is reimplemented here.
    unsafe { crate::x86_local::ihk_mc_get_processor_id() }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_virt_to_phys_bridge(addr: *mut c_void) -> CULong {
    // SAFETY: The original raw address and mapping-state preconditions pass unchanged.
    // The actual Rust provider retains all range branches, wrapping arithmetic and logs.
    unsafe { crate::x86_memory_helpers::virt_to_phys(addr) }
}
