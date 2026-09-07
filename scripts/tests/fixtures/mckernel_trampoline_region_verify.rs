// SPDX-License-Identifier: GPL-2.0-only
//! Disposable Linux guest check of an explicitly carved low-memory owner.
//! No CPU executes or retains a pointer into the tested page.

use core::{ptr, ptr::NonNull};
use kernel::{bindings, prelude::*};

module! {
    type: TrampolineRegionVerify,
    name: "mckernel_trampoline_region_verify",
    author: "McKernel developers",
    description: "Owned low-memory region verification; no CPU startup",
    license: "GPL",
}

const PAGE_BYTES: u64 = 4096;
const FIRST_ALLOWED: u64 = 64 << 10;
const LIMIT: u64 = 640 << 10;
const TEST_PHYSICAL: u64 = 0x80000;
const RAM: u32 = 1;
const LEASE_CYCLES: usize = 64;

extern "C" {
    // Exact x86 E820 prototypes are checked in the separate C data witness.
    fn e820__mapped_raw_any(start: u64, end: u64, kind: u32) -> bool;
    fn e820__mapped_any(start: u64, end: u64, kind: u32) -> bool;
}

/// Owns the exact resource-manager claim, never a buddy allocator page.
/// The claim persists independently of the acquiring task and cannot be copied.
struct Reservation {
    physical: u64,
}

impl Reservation {
    fn acquire(physical: u64) -> Result<Self> {
        let end = physical.checked_add(PAGE_BYTES).ok_or(EINVAL)?;
        if physical < FIRST_ALLOWED || physical % PAGE_BYTES != 0 || end > LIMIT {
            return Err(EINVAL);
        }
        // SAFETY: These resident Linux E820 tables are stable after boot.
        // The bounded range is checked first. Type zero asks for any overlap.
        if unsafe { e820__mapped_any(physical, end, 0) } {
            return Err(EBUSY);
        }
        for address in physical..end {
            // SAFETY: Each nonempty byte range fits the checked page. Testing
            // every byte turns the overlap API into complete RAM coverage,
            // including ranges that cross an original firmware entry boundary.
            if !unsafe { e820__mapped_raw_any(address, address + 1, RAM) } {
                return Err(EINVAL);
            }
        }
        // SAFETY: The current E820 map excludes this entire original RAM page.
        // Linux's resource manager arbitrates any other owner under its lock.
        // The descriptor name is static and the exclusive flag has its exact
        // Linux value. No mapping or memory write has occurred before this call.
        let resource = unsafe {
            bindings::__request_region(
                &raw mut bindings::iomem_resource,
                physical,
                PAGE_BYTES,
                c"mckernel-trampoline-verification".as_ptr(),
                bindings::IORESOURCE_EXCLUSIVE as i32,
            )
        };
        NonNull::new(resource).ok_or(EBUSY)?;
        Ok(Self { physical })
    }
}

impl Drop for Reservation {
    fn drop(&mut self) {
        // SAFETY: This unique guard owns exactly this live busy region. Any
        // associated mapping has already been released by LowRegion::drop.
        // No AP has ever been started or given this address in the fixture.
        unsafe {
            bindings::__release_region(&raw mut bindings::iomem_resource, self.physical, PAGE_BYTES)
        };
    }
}

struct LowRegion {
    reservation: Reservation,
    mapping: NonNull<u8>,
}

// SAFETY: The exclusively leased, globally mapped RAM is independent of the
// acquiring task. Moving its unique owner transfers its sole cleanup duty.
unsafe impl Send for LowRegion {}
// SAFETY: Shared access only reads owned RAM. Mutation requires &mut self,
// and no external CPU/device/caller receives this mapping during the fixture.
unsafe impl Sync for LowRegion {}

impl LowRegion {
    fn acquire(physical: u64) -> Result<Self> {
        let reservation = Reservation::acquire(physical)?;
        // SAFETY: The original firmware RAM page is excluded from the current
        // E820 map and exclusively leased. Linux supplies its WB mapping. A
        // mapping failure drops the still-local resource owner automatically.
        let mapping = unsafe { bindings::ioremap_cache(physical, PAGE_BYTES) };
        let mapping = NonNull::new(mapping.cast::<u8>()).ok_or(ENOMEM)?;
        Ok(Self {
            reservation,
            mapping,
        })
    }

    fn fill_and_check(&mut self, cycle: usize) {
        for offset in 0..PAGE_BYTES as usize {
            let byte = (offset.wrapping_mul(13) ^ cycle.wrapping_mul(17)) as u8;
            // SAFETY: Unique mapped RAM owner; all writes stay inside the
            // complete checked page. No CPU, device or caller has its address.
            unsafe { ptr::write_volatile(self.mapping.as_ptr().add(offset), byte) };
        }
        self.check(cycle);
    }

    fn check(&self, cycle: usize) {
        for offset in 0..PAGE_BYTES as usize {
            let expected = (offset.wrapping_mul(13) ^ cycle.wrapping_mul(17)) as u8;
            // SAFETY: The complete mapping and its exclusive region owner are
            // still alive. The volatile read observes actual mapped RAM.
            let actual = unsafe { ptr::read_volatile(self.mapping.as_ptr().add(offset)) };
            assert_eq!(actual, expected);
        }
    }
}

impl Drop for LowRegion {
    fn drop(&mut self) {
        // SAFETY: No CPU or external caller ever receives this mapping. It is
        // the successful ioremap_cache result, released exactly once before
        // Rust drops the reservation field and makes the region available.
        unsafe { bindings::iounmap(self.mapping.as_ptr().cast()) };
    }
}

struct TrampolineRegionVerify {
    retained: Option<LowRegion>,
}

impl kernel::Module for TrampolineRegionVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        for bad in [
            0,
            FIRST_ALLOWED - PAGE_BYTES,
            TEST_PHYSICAL + 1,
            LIMIT,
            u64::MAX,
        ] {
            assert!(Reservation::acquire(bad).is_err_and(|error| error == EINVAL));
        }
        // SAFETY: This fixed, nonempty bounded range is checked by Linux's
        // resident E820 overlap predicate without touching the target memory.
        let mapped = unsafe { e820__mapped_any(TEST_PHYSICAL, TEST_PHYSICAL + PAGE_BYTES, 0) };
        if mapped {
            assert!(LowRegion::acquire(TEST_PHYSICAL).is_err_and(|error| error == EBUSY));
            pr_info!("MCKERNEL_TRAMPOLINE_REGION REJECT mapped=1 writes=0 mckernel_boot=0\n");
            return Ok(Self { retained: None });
        }
        for cycle in 0..LEASE_CYCLES {
            // A claim dropped before mapping covers the same RAII cleanup
            // obligation as ioremap_cache returning null in LowRegion::acquire.
            drop(Reservation::acquire(TEST_PHYSICAL)?);
            let mut region = LowRegion::acquire(TEST_PHYSICAL)?;
            assert_eq!(region.reservation.physical, TEST_PHYSICAL);
            assert!(LowRegion::acquire(TEST_PHYSICAL).is_err_and(|error| error == EBUSY));
            region.fill_and_check(cycle);
            // The map and original resource claim retire before reacquisition.
            drop(region);
        }
        let mut retained = LowRegion::acquire(TEST_PHYSICAL)?;
        retained.fill_and_check(LEASE_CYCLES);
        pr_info!("MCKERNEL_TRAMPOLINE_REGION PASS physical=80000 cycles=64 bytes=4096 exclusive=1 mckernel_boot=0\n");
        Ok(Self {
            retained: Some(retained),
        })
    }
}

impl Drop for TrampolineRegionVerify {
    fn drop(&mut self) {
        if let Some(region) = self.retained.take() {
            region.check(LEASE_CYCLES);
            drop(region);
            pr_info!("MCKERNEL_TRAMPOLINE_REGION UNLOAD released=1\n");
        } else {
            pr_info!("MCKERNEL_TRAMPOLINE_REGION UNLOAD released=0 writes=0\n");
        }
    }
}

const _: () = {
    assert!(bindings::PAGE_SHIFT == 12);
    assert!(core::mem::size_of::<bindings::resource_size_t>() == 8);
    assert!(bindings::IORESOURCE_EXCLUSIVE == 134217728);
};
