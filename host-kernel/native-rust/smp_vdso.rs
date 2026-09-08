// SPDX-License-Identifier: GPL-2.0
//! Native adaptation of mcctrl_helpers::get_vdso_info. Linux owns the actual
//! text and data; the caller owns the generation-checked remote descriptor.

use super::vdso_protocol::{self as wire, Descriptor};
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use kernel::{bindings, prelude::*};

extern "C" {
    // Existing exported Linux getters. Their return is an opaque pointer or
    // PFN; this adapter never constructs or mutates a private clock object.
    #[cfg(CONFIG_PARAVIRT_CLOCK)]
    fn pvclock_get_pvti_cpu0_va() -> *mut core::ffi::c_void;
    #[cfg(CONFIG_HYPERV_TIMER)]
    fn hv_get_tsc_pfn() -> u64;
}

const _: () = {
    assert!(size_of::<wire::Clock>() == size_of::<bindings::vdso_clock>());
    assert!(align_of::<wire::Clock>() == align_of::<bindings::vdso_clock>());
    assert!(offset_of!(wire::Clock, seq) == offset_of!(bindings::vdso_clock, seq));
    assert!(offset_of!(wire::Clock, clock_mode) == offset_of!(bindings::vdso_clock, clock_mode));
    assert!(offset_of!(wire::Clock, cycle_last) == offset_of!(bindings::vdso_clock, cycle_last));
    assert!(offset_of!(wire::Clock, max_cycles) == offset_of!(bindings::vdso_clock, max_cycles));
    assert!(offset_of!(wire::Clock, mask) == offset_of!(bindings::vdso_clock, mask));
    assert!(offset_of!(wire::Clock, mult) == offset_of!(bindings::vdso_clock, mult));
    assert!(offset_of!(wire::Clock, shift) == offset_of!(bindings::vdso_clock, shift));
    assert!(
        offset_of!(wire::Clock, basetime) == offset_of!(bindings::vdso_clock, __bindgen_anon_1)
    );
    assert!(size_of::<wire::TimeData>() == size_of::<bindings::vdso_time_data>());
    assert!(align_of::<wire::TimeData>() == align_of::<bindings::vdso_time_data>());
    assert!(
        offset_of!(wire::TimeData, clock_data) == offset_of!(bindings::vdso_time_data, clock_data)
    );
    assert!(bindings::__VDSO_PAGES as usize == wire::DATA_PAGES);
    assert!(bindings::vdso_pages_VDSO_TIME_PAGE_OFFSET as usize == wire::TIME_PAGE);
    assert!(bindings::vdso_pages_VDSO_RNG_PAGE_OFFSET as usize == wire::RNG_PAGE);
};

fn physical(address: u64) -> Result<u64> {
    // SAFETY: These bases are initialized by Linux before any module runs.
    let (physical_base, linear_base) = unsafe { (bindings::phys_base, bindings::page_offset_base) };
    let result = if address >= 0xffff_ffff_8000_0000 {
        super::ihk_mapping::kernel_image_physical(address, physical_base, wire::PHYSICAL_LIMIT)
    } else {
        super::ihk_mapping::kernel_linear_physical(address, linear_base, wire::PHYSICAL_LIMIT)
    };
    result.ok_or(EINVAL)
}

/// Read Linux's permanent objects, adapting the existing Rust mcctrl page
/// enumeration to the exact generic data layout. No guest data selects a Linux
/// pointer. Optional clock pages come from the original exported getters.
pub(super) fn collect() -> Result<Descriptor> {
    #[cfg(CONFIG_AMD_MEM_ENCRYPT)]
    if unsafe { bindings::sme_me_mask } != 0 {
        // The current native startup and mapping contract uses plain RAM. A
        // decrypted PV page needs a separately verified encrypted-memory path.
        return Err(kernel::error::to_result(-(bindings::EOPNOTSUPP as i32))
            .err()
            .unwrap_or(EINVAL));
    }
    let (text, bytes, time, rng) = unsafe {
        let image = addr_of!(bindings::vdso_image_64);
        (
            read_volatile(addr_of!((*image).data)),
            read_volatile(addr_of!((*image).size)),
            read_volatile(addr_of!(bindings::vdso_k_time_data)),
            read_volatile(addr_of!(bindings::vdso_k_rng_data)),
        )
    };
    if text.is_null()
        || time.is_null()
        || rng.is_null()
        || bytes == 0
        || bytes % wire::PAGE_BYTES != 0
        || bytes > wire::TEXT_PAGES as u64 * wire::PAGE_BYTES
    {
        return Err(EINVAL);
    }
    let mut text_physical = [0; wire::TEXT_PAGES];
    for (index, slot) in text_physical[..(bytes / wire::PAGE_BYTES) as usize]
        .iter_mut()
        .enumerate()
    {
        *slot = physical(
            (text as u64)
                .checked_add(index as u64 * wire::PAGE_BYTES)
                .ok_or(EINVAL)?,
        )?;
    }
    let mut data = [0; wire::DATA_PAGES];
    data[wire::TIME_PAGE] = physical(time as u64)?;
    data[wire::RNG_PAGE] = physical(rng as u64)?;
    #[cfg(CONFIG_PARAVIRT_CLOCK)]
    {
        // SAFETY: Linux owns this CPU-0 clock page for its kernel lifetime; it
        // is only exposed by the getter after the platform initializes it.
        let pvclock = unsafe { pvclock_get_pvti_cpu0_va() };
        if !pvclock.is_null() {
            data[wire::PVCLOCK_PAGE] = physical(pvclock as u64)?;
        }
    }
    #[cfg(CONFIG_HYPERV_TIMER)]
    {
        // SAFETY: The existing getter returns zero until Hyper-V initializes
        // its permanent reference page. Multiplication must not lose PFN bits.
        let pfn = unsafe { hv_get_tsc_pfn() };
        if pfn != 0 {
            data[wire::HVCLOCK_PAGE] = pfn.checked_mul(wire::PAGE_BYTES).ok_or(EINVAL)?;
        }
    }
    Descriptor::response((bytes / wire::PAGE_BYTES) as u32, text_physical, data).map_err(|_| EINVAL)
}

/// # Safety
/// `destination` must address the entire writable, 8-aligned 128-byte request
/// in the exact retained OS generation, disjoint from all transport queues.
/// The peer has published its request and only reads busy until completion.
/// This process is the sole responder; it retains every mapping through boot.
pub(super) unsafe fn complete(destination: *mut u8, response: &Descriptor) -> Result {
    // SAFETY: The caller supplies the checked retained generation and complete
    // one-shot publication contract documented above.
    unsafe { wire::complete(destination, response) }.map_err(|_| EINVAL)
}
