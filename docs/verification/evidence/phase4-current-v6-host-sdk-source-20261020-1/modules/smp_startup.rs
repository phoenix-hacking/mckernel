// SPDX-License-Identifier: GPL-2.0
//! Checked four-level startup mappings for the preserved x86_64 McKernel.
//!
//! Reuse `BootLayout` and the mapping geometry rather than another memory map.
//! The mappings retain the frozen SMP startup ABI: identity and straight maps
//! cover 256 GiB, and four 2 MiB leaves map the checked kernel window. Linux
//! owns the backing pages in the attached adapter. This plan cannot start CPUs.

use super::smp_image::{BootLayout, IDENTITY_WINDOW_END, KERNEL_BASE, KERNEL_WINDOW_BYTES};

pub(crate) const PAGE_BYTES: usize = 4096;
pub(crate) const ENTRIES_PER_PAGE: usize = 512;
pub(crate) const TABLE_PAGES: usize = 260;
pub(crate) const TABLE_BYTES: usize = TABLE_PAGES * PAGE_BYTES;
pub(crate) const STRAIGHT_BASE: u64 = 0xffff_8000_0000_0000;
const LARGE_PAGE_BYTES: u64 = 2 << 20;
const TABLE_FLAGS: u64 = 0x63;
const LEAF_FLAGS: u64 = 0xe3;
const IDENTITY_PDPT: usize = 1;
const FIRST_IDENTITY_PMD: usize = 2;
const KERNEL_PDPT: usize = 258;
const KERNEL_PMD: usize = 259;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum StartupError {
    TableAddress,
    StorageSize,
    Index,
}

/// Validated addresses only. The adapter must retain the original Linux page
/// owner and the OS lease for every use, and keep the pages below 4 GiB because
/// the real-mode trampoline initially loads CR3 with a 32-bit instruction.
#[derive(Clone, Copy, Debug)]
pub(crate) struct PageTablePlan {
    physical: u64,
    layout: BootLayout,
}

impl PageTablePlan {
    pub(crate) fn new(physical: u64, layout: BootLayout) -> Result<Self, StartupError> {
        let end = physical
            .checked_add(TABLE_BYTES as u64)
            .ok_or(StartupError::TableAddress)?;
        if physical == 0 || physical % PAGE_BYTES as u64 != 0 || end > 1_u64 << 32 {
            return Err(StartupError::TableAddress);
        }
        // These are disjoint allocations. Catch a malformed adapter identity
        // before it could overwrite its assigned kernel or startup memory.
        let extent = layout.extent();
        let extent_end = extent.end().map_err(|_| StartupError::TableAddress)?;
        if physical < extent_end && extent.start() < end {
            return Err(StartupError::TableAddress);
        }
        Ok(Self { physical, layout })
    }

    pub(crate) const fn root(self) -> u64 {
        self.physical
    }

    fn table(self, page: usize) -> u64 {
        // Construction checked the entire allocation; callers use fixed
        // indices strictly smaller than TABLE_PAGES.
        self.physical + page as u64 * PAGE_BYTES as u64 | TABLE_FLAGS
    }

    /// Calculate one PML4/PDPT/PMD entry without a temporary page on the Linux
    /// stack. The identity PMDs are shared by the two disjoint virtual windows.
    pub(crate) fn entry(self, page: usize, index: usize) -> Result<u64, StartupError> {
        if page >= TABLE_PAGES || index >= ENTRIES_PER_PAGE {
            return Err(StartupError::Index);
        }
        let value = match page {
            0 => match index {
                0 | 256 => self.table(IDENTITY_PDPT),
                511 => self.table(KERNEL_PDPT),
                _ => 0,
            },
            IDENTITY_PDPT if index < 256 => self.table(FIRST_IDENTITY_PMD + index),
            FIRST_IDENTITY_PMD..=257 => {
                let leaf = (page - FIRST_IDENTITY_PMD) * ENTRIES_PER_PAGE + index;
                leaf as u64 * LARGE_PAGE_BYTES | LEAF_FLAGS
            }
            KERNEL_PDPT if index == 511 => self.table(KERNEL_PMD),
            KERNEL_PMD => {
                let first = ((KERNEL_BASE >> 21) & 511) as usize;
                let leaves = (KERNEL_WINDOW_BYTES / LARGE_PAGE_BYTES) as usize;
                if (first..first + leaves).contains(&index) {
                    self.layout.kernel().start() + (index - first) as u64 * LARGE_PAGE_BYTES
                        | LEAF_FLAGS
                } else {
                    0
                }
            }
            _ => 0,
        };
        Ok(value)
    }

    /// Fill the exact useful table extent. The adapter owns any page-order
    /// padding separately; passing a short or oversized slice writes nothing.
    pub(crate) fn fill(self, entries: &mut [u64]) -> Result<(), StartupError> {
        if entries.len() != TABLE_BYTES / core::mem::size_of::<u64>() {
            return Err(StartupError::StorageSize);
        }
        for (offset, entry) in entries.iter_mut().enumerate() {
            *entry = self.entry(offset / ENTRIES_PER_PAGE, offset % ENTRIES_PER_PAGE)?;
        }
        Ok(())
    }
}

const _: () = {
    assert!(IDENTITY_WINDOW_END == 256 << 30);
    assert!(KERNEL_WINDOW_BYTES == 4 * LARGE_PAGE_BYTES);
    assert!((STRAIGHT_BASE >> 39) & 511 == 256);
    assert!((KERNEL_BASE >> 39) & 511 == 511);
    assert!((KERNEL_BASE >> 30) & 511 == 511);
    assert!(FIRST_IDENTITY_PMD + 256 == KERNEL_PDPT);
    assert!(KERNEL_PMD + 1 == TABLE_PAGES);
};
