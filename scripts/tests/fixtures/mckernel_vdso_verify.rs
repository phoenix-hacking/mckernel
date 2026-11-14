// SPDX-License-Identifier: GPL-2.0-only
//! Read-only check of the pinned Linux vDSO exports in a disposable guest.
//! This fixture does not reply to McKernel or grant application acceptance.

use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use core::sync::atomic::{fence, Ordering};
use kernel::{bindings, prelude::*};

module! {
    type: VdsoVerify,
    name: "mckernel_vdso_verify",
    author: "McKernel developers",
    description: "Read-only native Linux vDSO export and live-data verification",
    license: "GPL",
}

#[used]
#[link_section = ".mckernel_native_vdso_layout"]
static LAYOUT: [usize; 44] = [
    bindings::PAGE_SIZE as usize,
    bindings::__VDSO_PAGES as usize,
    bindings::vdso_pages_VDSO_NR_PAGES as usize,
    bindings::VDSO_NR_VCLOCK_PAGES as usize,
    bindings::vdso_pages_VDSO_TIME_PAGE_OFFSET as usize,
    bindings::vdso_pages_VDSO_TIMENS_PAGE_OFFSET as usize,
    bindings::vdso_pages_VDSO_RNG_PAGE_OFFSET as usize,
    bindings::vdso_pages_VDSO_ARCH_PAGES_START as usize,
    bindings::VDSO_PAGE_PVCLOCK_OFFSET as usize,
    bindings::VDSO_PAGE_HVCLOCK_OFFSET as usize,
    offset_of!(bindings::vdso_image, data),
    offset_of!(bindings::vdso_image, size),
    size_of::<bindings::vdso_timestamp>(),
    align_of::<bindings::vdso_timestamp>(),
    offset_of!(bindings::vdso_timestamp, sec),
    offset_of!(bindings::vdso_timestamp, nsec),
    size_of::<bindings::vdso_clock>(),
    align_of::<bindings::vdso_clock>(),
    offset_of!(bindings::vdso_clock, seq),
    offset_of!(bindings::vdso_clock, clock_mode),
    offset_of!(bindings::vdso_clock, cycle_last),
    offset_of!(bindings::vdso_clock, max_cycles),
    offset_of!(bindings::vdso_clock, mask),
    offset_of!(bindings::vdso_clock, mult),
    offset_of!(bindings::vdso_clock, shift),
    offset_of!(bindings::vdso_clock, __bindgen_anon_1),
    bindings::VDSO_BASES as usize,
    bindings::CS_BASES as usize,
    bindings::CS_HRES_COARSE as usize,
    bindings::CS_RAW as usize,
    size_of::<bindings::vdso_time_data>(),
    align_of::<bindings::vdso_time_data>(),
    offset_of!(bindings::vdso_time_data, clock_data),
    offset_of!(bindings::vdso_time_data, tz_minuteswest),
    offset_of!(bindings::vdso_time_data, tz_dsttime),
    offset_of!(bindings::vdso_time_data, hrtimer_res),
    size_of::<bindings::vdso_rng_data>(),
    align_of::<bindings::vdso_rng_data>(),
    offset_of!(bindings::vdso_rng_data, generation),
    offset_of!(bindings::vdso_rng_data, is_ready),
    bindings::vdso_clock_mode_VDSO_CLOCKMODE_NONE as usize,
    bindings::vdso_clock_mode_VDSO_CLOCKMODE_TSC as usize,
    bindings::vdso_clock_mode_VDSO_CLOCKMODE_PVCLOCK as usize,
    bindings::vdso_clock_mode_VDSO_CLOCKMODE_HVCLOCK as usize,
];

/// The vDSO text is permanent Linux image data, patched during early boot and
/// immutable by the time module loading is available. No guest supplies it.
unsafe fn text_hash(text: *const u8) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for offset in 0..8192 {
        // SAFETY: The caller checked the exported image has two complete pages.
        hash ^= unsafe { read_volatile(text.add(offset)) } as u64;
        hash = hash.wrapping_mul(0x100_0000_01b3);
    }
    hash
}

/// Mirror Linux's sequence/read barriers with raw scalar accesses; never form
/// a Rust reference to data that Linux's timekeeper can update concurrently.
unsafe fn coarse(time: *const bindings::vdso_time_data) -> Result<(u32, i32, u64, u64)> {
    for _ in 0..100_000 {
        // SAFETY: The exported, page-aligned Linux object is permanent. The
        // exact generated field layouts are compared with the independent C
        // witness before this module is allowed into the verification guest.
        let first = unsafe { read_volatile(addr_of!((*time).clock_data[0].seq)) };
        if first & 1 != 0 {
            core::hint::spin_loop();
            continue;
        }
        fence(Ordering::Acquire);
        let (mode, sec, nsec) = unsafe {
            let base = addr_of!((*time).clock_data[0].__bindgen_anon_1.basetime[5]);
            (
                read_volatile(addr_of!((*time).clock_data[0].clock_mode)),
                read_volatile(addr_of!((*base).sec)),
                read_volatile(addr_of!((*base).nsec)),
            )
        };
        fence(Ordering::Acquire);
        let second = unsafe { read_volatile(addr_of!((*time).clock_data[0].seq)) };
        if first == second {
            return Ok((first, mode, sec, nsec));
        }
    }
    Err(EAGAIN)
}

struct VdsoVerify {
    text: usize,
    hash: u64,
}

impl kernel::Module for VdsoVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        assert_eq!(LAYOUT.len(), 44);
        // SAFETY: These exact exported symbols are owned for the entire Linux
        // lifetime. Only raw reads occur; this fixture allocates or writes none
        // of the text, time, RNG, or other Linux data pages.
        let (text, bytes, time, rng, physical_base) = unsafe {
            let image = addr_of!(bindings::vdso_image_64);
            (
                read_volatile(addr_of!((*image).data)).cast::<u8>(),
                read_volatile(addr_of!((*image).size)),
                read_volatile(addr_of!(bindings::vdso_k_time_data)),
                read_volatile(addr_of!(bindings::vdso_k_rng_data)),
                read_volatile(addr_of!(bindings::phys_base)),
            )
        };
        assert_eq!(bytes, 8192);
        for address in [text as usize, time as usize, rng as usize] {
            assert!(address >= 0xffff_ffff_8000_0000 && address < 0xffff_ffff_c000_0000);
            assert_eq!(address % 4096, 0);
        }
        assert_ne!(time as usize, rng as usize);
        let magic = unsafe { read_volatile(text.cast::<u32>()) };
        assert_eq!(magic, 0x464c_457f);
        assert_eq!(unsafe { read_volatile(text.add(4)) }, 2);
        let hash = unsafe { text_hash(text) };
        let initial = unsafe { coarse(time)? };
        let mut last = initial;
        let mut updates = 0;
        for _ in 0..16 {
            // SAFETY: Module initialization is sleepable process context and
            // no lock or borrowed Linux object is held across the delay.
            unsafe { bindings::msleep(20) };
            let current = unsafe { coarse(time)? };
            let real_seconds = unsafe { bindings::ktime_get_real_seconds() };
            assert!(real_seconds >= 0);
            assert!(current.2 <= real_seconds as u64 && real_seconds as u64 - current.2 <= 1);
            assert!(current.3 < 1_000_000_000);
            assert!((0..=3).contains(&current.1));
            assert!((current.2, current.3) >= (last.2, last.3));
            updates += u32::from(current.0 != last.0);
            last = current;
        }
        assert!(updates > 0);
        let ready = unsafe { read_volatile(addr_of!((*rng).is_ready)) };
        assert!(ready <= 1);
        assert_eq!(unsafe { text_hash(text) }, hash);
        pr_info!("MCKERNEL_VDSO_VERIFY PASS text={:x} bytes=8192 fnv={:x} time={:x} rng={:x} physical_base={:x} mode={} first_seq={} last_seq={} updates={} samples=16 rng_ready={} read_only=1 service_completed=0\n", text as usize, hash, time as usize, rng as usize, physical_base, last.1, initial.0, last.0, updates, ready);
        Ok(Self {
            text: text as usize,
            hash,
        })
    }
}

impl Drop for VdsoVerify {
    fn drop(&mut self) {
        // SAFETY: Linux still owns the permanent, immutable image at unload.
        assert_eq!(unsafe { text_hash(self.text as *const u8) }, self.hash);
        pr_info!("MCKERNEL_VDSO_VERIFY UNLOAD read_only=1 text_unchanged=1\n");
    }
}
