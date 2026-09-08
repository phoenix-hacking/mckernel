// SPDX-License-Identifier: GPL-2.0
//! Native Linux generic vDSO exchange and read-only clock access. This owns a
//! separate descriptor; the C-owned legacy ArchVdso allocation stays 88 bytes.

use crate::abi::{CInt, CpuLocalVar, IkcScdPacket, TimeSpec};
use crate::vdso_protocol::{self as wire, Descriptor};
use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::sync::atomic::{fence, AtomicU32, Ordering};

struct Exchange(UnsafeCell<Descriptor>);
// SAFETY: The sole boot caller initializes the request. The host owns payload
// writes until its release completion; thereafter all users only read. STATE
// publishes validation to other McKernel CPUs before AP startup.
unsafe impl Sync for Exchange {}
static EXCHANGE: Exchange = Exchange(UnsafeCell::new(Descriptor::request()));
static STATE: AtomicU32 = AtomicU32::new(0);

unsafe extern "C" {
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn x86_arch_mem_virt_to_phys_bridge(address: *mut c_void) -> u64;
    fn x86_arch_mem_phys_to_virt_bridge(physical: u64) -> *mut c_void;
}

/// Reuse the original message preparation and IKC sender, adapting only the
/// exchange storage, version checks and release/acquire completion protocol.
pub unsafe fn initialize() -> Result<Descriptor, CInt> {
    STATE
        .compare_exchange(0, 1, Ordering::Acquire, Ordering::Relaxed)
        .map_err(|_| -16)?;
    let result = unsafe { exchange() };
    STATE.store(if result.is_ok() { 2 } else { 3 }, Ordering::Release);
    result
}

unsafe fn exchange() -> Result<Descriptor, CInt> {
    let cpu = unsafe { get_this_cpu_local_var() };
    if cpu.is_null() || unsafe { (*cpu).ikc2linux.is_null() } {
        return Err(-14);
    }
    let pointer = EXCHANGE.0.get();
    unsafe { pointer.write(Descriptor::request()) };
    let physical = unsafe { x86_arch_mem_virt_to_phys_bridge(pointer.cast()) };
    if physical == 0 || physical % 8 != 0 || physical > wire::PHYSICAL_LIMIT - wire::BYTES as u64 {
        return Err(-22);
    }
    let mut packet: IkcScdPacket = unsafe { core::mem::zeroed() };
    let error = unsafe {
        crate::x86_memory_helpers::x86_vdso_packet_prepare_result(&mut packet, 0xb, physical)
    };
    if error != 0 {
        return Err(error);
    }
    fence(Ordering::Release);
    let error = unsafe {
        crate::ikc_manycore::ihk_ikc_send(
            (*cpu).ikc2linux.cast(),
            (&mut packet as *mut IkcScdPacket).cast(),
            0,
        )
    };
    if error != 0 {
        return Err(error);
    }
    loop {
        match unsafe { wire::read_response(pointer.cast()) } {
            Ok(response) => return Ok(response),
            Err(wire::Error::InProgress) => core::hint::spin_loop(),
            Err(_) => return Err(-22),
        }
    }
}

pub fn snapshot() -> Option<Descriptor> {
    if STATE.load(Ordering::Acquire) != 2 {
        return None;
    }
    // SAFETY: Validation is published only after host completion, and the
    // retained one-shot host service never mutates the descriptor again.
    Some(unsafe { EXCHANGE.0.get().read() })
}

pub unsafe fn time_mapping(response: &Descriptor) -> *mut wire::TimeData {
    unsafe { x86_arch_mem_phys_to_virt_bridge(response.data_physical[wire::TIME_PAGE]).cast() }
}

#[inline(always)]
fn ordered_tsc() -> u64 {
    let low: u32;
    let high: u32;
    unsafe {
        core::arch::asm!("lfence", "rdtsc", out("eax") low, out("edx") high,
            options(nostack, preserves_flags));
    }
    (high as u64) << 32 | low as u64
}

pub fn clock(clock_id: CInt) -> Option<TimeSpec> {
    let response = snapshot()?;
    // SAFETY: The validated response names the exact, permanent Linux page in
    // the existing direct mapping. Only Linux writes under its sequence lock.
    let (tv_sec, tv_nsec) =
        unsafe { wire::read_clock(time_mapping(&response), clock_id, ordered_tsc) }?;
    Some(TimeSpec { tv_sec, tv_nsec })
}
