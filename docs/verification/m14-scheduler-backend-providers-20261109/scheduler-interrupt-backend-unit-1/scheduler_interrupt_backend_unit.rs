#![no_std]
// Finite original general CPU/APIC routing only. No IRQ/hardware/logger body.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod ap {
use crate::abi::CInt;
unsafe extern "C" {
    pub static mut num_processors: CInt;
}
}

mod x86_local {
use crate::abi::{CInt, X86CpuLocalVariables};
unsafe extern "C" {
    pub fn get_x86_cpu_local_variable(id: CInt) -> *mut X86CpuLocalVariables;
}
}

mod x86_cpu_helpers {
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::read_volatile;
use crate::abi::{CInt, CULong};

type X86CpuLocalFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type X86IssueIpiFn = unsafe extern "C" fn(CULong, CInt);
type X86InterruptLogFn = unsafe extern "C" fn(CInt, CInt, CInt);

unsafe extern "C" {
    fn x86_issue_ipi_bridge(apic_id: CULong, vector: CInt);
    fn x86_interrupt_log_bridge(event: CInt, cpu: CInt, vector: CInt);
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
}
