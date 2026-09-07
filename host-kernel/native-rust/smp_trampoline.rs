// SPDX-License-Identifier: GPL-2.0-only
//! Exclusive low-memory reservation for the native SMP startup adapter.
//!
//! Extracted from the passing trampoline-region fixture. The canonical OS,
//! CPU and image owners must outlive every use of the prepared trampoline.
//! An executing or uncertain AP forbids dropping this unstarted owner.

use core::{ptr, ptr::NonNull};
use kernel::{bindings, prelude::*};

const PAGE_BYTES: u64 = 4096;
const FIRST_ALLOWED: u64 = 64 << 10;
const LIMIT: u64 = 640 << 10;
const RAM: u32 = 1;

extern "C" {
    // Exact x86 E820 prototypes are checked in the separate C data witness.
    fn e820__mapped_raw_any(start: u64, end: u64, kind: u32) -> bool;
    fn e820__mapped_any(start: u64, end: u64, kind: u32) -> bool;
}

/// Owns the exact resource-manager claim, never a buddy allocator page.
/// The claim persists independently of the acquiring task and cannot be copied.
pub(super) struct Reservation {
    physical: u64,
}

impl Reservation {
    pub(super) fn acquire(physical: u64) -> Result<Self> {
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
        // The caller has not published this page to an executing AP.
        unsafe {
            bindings::__release_region(&raw mut bindings::iomem_resource, self.physical, PAGE_BYTES)
        };
    }
}

pub(super) struct LowRegion {
    reservation: Reservation,
    mapping: NonNull<u8>,
}

// SAFETY: The exclusively leased, globally mapped RAM is independent of the
// acquiring task. Moving its unique owner transfers its sole cleanup duty.
unsafe impl Send for LowRegion {}
// SAFETY: Shared access only reads owned RAM. Mutation requires &mut self,
// and no external CPU/device/caller receives this mapping through this unstarted owner.
unsafe impl Sync for LowRegion {}

impl LowRegion {
    pub(super) fn acquire(physical: u64) -> Result<Self> {
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

    pub(super) fn physical(&self) -> u64 {
        self.reservation.physical
    }

    pub(super) fn write_byte(&mut self, offset: usize, byte: u8) -> Result {
        if offset >= PAGE_BYTES as usize {
            return Err(EINVAL);
        }
        // SAFETY: Exclusive mapped RAM owner and a checked byte offset. No
        // external CPU may use the page during mutable preparation.
        unsafe { ptr::write_volatile(self.mapping.as_ptr().add(offset), byte) };
        Ok(())
    }

    pub(super) fn read_byte(&self, offset: usize) -> Result<u8> {
        if offset >= PAGE_BYTES as usize {
            return Err(EINVAL);
        }
        // SAFETY: This complete mapping and exclusive reservation remain live.
        Ok(unsafe { ptr::read_volatile(self.mapping.as_ptr().add(offset)) })
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

const _: () = {
    assert!(bindings::PAGE_SHIFT == 12);
    assert!(core::mem::size_of::<bindings::resource_size_t>() == 8);
    assert!(bindings::IORESOURCE_EXCLUSIVE == 134217728);
};
