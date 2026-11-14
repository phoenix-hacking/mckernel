// SPDX-License-Identifier: GPL-2.0-only
//! Disposable Linux guest check of an explicitly carved low-memory owner.
//! No CPU executes or retains a pointer into the tested page.

use kernel::prelude::*;

#[path = "../../../host-kernel/native-rust/smp_trampoline.rs"]
mod smp_trampoline;
use smp_trampoline::{LowRegion, Reservation};
#[path = "../../../host-kernel/native-rust/smp_boot_code.rs"]
mod smp_boot_code;

module! {
    type: TrampolineRegionVerify,
    name: "mckernel_trampoline_region_verify",
    author: "McKernel developers",
    description: "Owned low-memory region verification; no CPU startup",
    license: "GPL",
}

const PAGE_BYTES: usize = 4096;
const FIRST_ALLOWED: u64 = 64 << 10;
const LIMIT: u64 = 640 << 10;
const TEST_PHYSICAL: u64 = 0x80000;
const LEASE_CYCLES: usize = 64;

extern "C" {
    fn e820__mapped_any(start: u64, end: u64, kind: u32) -> bool;
}

fn check(region: &LowRegion, cycle: usize) {
    for offset in 0..PAGE_BYTES {
        let expected = (offset.wrapping_mul(13) ^ cycle.wrapping_mul(17)) as u8;
        assert_eq!(region.read_byte(offset).unwrap(), expected);
    }
    assert!(region
        .read_byte(PAGE_BYTES)
        .is_err_and(|error| error == EINVAL));
}

fn fill_and_check(region: &mut LowRegion, cycle: usize) {
    for offset in 0..PAGE_BYTES {
        let byte = (offset.wrapping_mul(13) ^ cycle.wrapping_mul(17)) as u8;
        region.write_byte(offset, byte).unwrap();
    }
    assert!(region
        .write_byte(PAGE_BYTES, 0)
        .is_err_and(|error| error == EINVAL));
    check(region, cycle);
}

struct TrampolineRegionVerify {
    retained: Option<LowRegion>,
}

impl kernel::Module for TrampolineRegionVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        assert_eq!(smp_boot_code::trampoline().len(), PAGE_BYTES);
        assert!((56..PAGE_BYTES).contains(&smp_boot_code::startup().len()));
        for bad in [
            0,
            FIRST_ALLOWED - PAGE_BYTES as u64,
            TEST_PHYSICAL + 1,
            LIMIT,
            u64::MAX,
        ] {
            assert!(Reservation::acquire(bad).is_err_and(|error| error == EINVAL));
        }
        // SAFETY: This fixed, nonempty bounded range is checked by Linux's
        // resident E820 overlap predicate without touching the target memory.
        let mapped =
            unsafe { e820__mapped_any(TEST_PHYSICAL, TEST_PHYSICAL + PAGE_BYTES as u64, 0) };
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
            assert_eq!(region.physical(), TEST_PHYSICAL);
            assert!(LowRegion::acquire(TEST_PHYSICAL).is_err_and(|error| error == EBUSY));
            for (offset, byte) in smp_boot_code::trampoline().iter().copied().enumerate() {
                region.write_byte(offset, byte)?;
            }
            for (offset, byte) in smp_boot_code::trampoline().iter().copied().enumerate() {
                assert_eq!(region.read_byte(offset)?, byte);
            }
            fill_and_check(&mut region, cycle);
            // The map and original resource claim retire before reacquisition.
            drop(region);
        }
        let mut retained = LowRegion::acquire(TEST_PHYSICAL)?;
        fill_and_check(&mut retained, LEASE_CYCLES);
        pr_info!("MCKERNEL_TRAMPOLINE_REGION PASS physical=80000 cycles=64 bytes=4096 exclusive=1 mckernel_boot=0\n");
        Ok(Self {
            retained: Some(retained),
        })
    }
}

impl Drop for TrampolineRegionVerify {
    fn drop(&mut self) {
        if let Some(region) = self.retained.take() {
            check(&region, LEASE_CYCLES);
            drop(region);
            pr_info!("MCKERNEL_TRAMPOLINE_REGION UNLOAD released=1\n");
        } else {
            pr_info!("MCKERNEL_TRAMPOLINE_REGION UNLOAD released=0 writes=0\n");
        }
    }
}
