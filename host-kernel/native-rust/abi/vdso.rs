// SPDX-License-Identifier: GPL-2.0
//! Native vDSO exchange shared by the Linux adapter and McKernel.
//!
//! This is a separate allocation from the legacy 88-byte descriptor. Native
//! boot note revision 3 identifies its consumer; the IKC packet stays unchanged.

use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile, write_volatile};
use core::sync::atomic::{AtomicU64, Ordering};

pub const NATIVE_BOOT_ABI_VERSION: u32 = 3;
pub const VERSION: u32 = 1;
pub const BYTES: usize = 128;
pub const TEXT_PAGES: usize = 2;
pub const DATA_PAGES: usize = 6;
pub const PAGE_BYTES: u64 = 4096;
pub const PHYSICAL_LIMIT: u64 = 256 << 30;
pub const CLOCK_LAYOUT_GENERIC_OVERFLOW_V1: u32 = 1;
pub const TIME_PAGE: usize = 0;
pub const RNG_PAGE: usize = 2;
pub const PVCLOCK_PAGE: usize = 4;
pub const HVCLOCK_PAGE: usize = 5;
pub const CLOCK_NONE: i32 = 0;
pub const CLOCK_TSC: i32 = 1;
pub const CLOCK_PVCLOCK: i32 = 2;
pub const CLOCK_HVCLOCK: i32 = 3;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    InProgress,
    Version,
    Size,
    HostStatus(i32),
    Pages,
    ClockLayout,
    Reserved,
    Request,
    Alignment,
}

/// Publish the reply payload before completion, without borrowing peer memory.
///
/// # Safety
/// The caller owns the whole writable, 8-aligned request in a retained peer
/// generation. It is disjoint from queues and other writers. The peer has
/// published exactly `Descriptor::request()` and only polls the atomic busy
/// word until completion. There is one responder and no subsequent host write.
pub unsafe fn complete(destination: *mut u8, response: &Descriptor) -> Result<(), Error> {
    if destination.is_null() || destination as usize % 8 != 0 {
        return Err(Error::Alignment);
    }
    response.validate_response()?;
    let busy = unsafe { AtomicU64::from_ptr(destination.cast::<u64>()) };
    let mut request = [0; BYTES];
    request[..8].copy_from_slice(&busy.load(Ordering::Acquire).to_le_bytes());
    for (offset, byte) in request.iter_mut().enumerate().skip(8) {
        *byte = unsafe { read_volatile(destination.add(offset)) };
    }
    Descriptor::decode(&request).validate_request()?;
    let encoded = response.encode();
    for (offset, byte) in encoded.iter().copied().enumerate().skip(8) {
        unsafe { write_volatile(destination.add(offset), byte) };
    }
    busy.store(0, Ordering::Release);
    Ok(())
}

/// # Safety
/// The caller retains the complete aligned exchange and only the sole host
/// responder may write it. Completion is its final release operation.
pub unsafe fn read_response(source: *const u8) -> Result<Descriptor, Error> {
    if source.is_null() || source as usize % 8 != 0 {
        return Err(Error::Alignment);
    }
    let busy = unsafe { AtomicU64::from_ptr(source.cast_mut().cast::<u64>()) };
    if busy.load(Ordering::Acquire) != 0 {
        return Err(Error::InProgress);
    }
    let mut bytes = [0; BYTES];
    for (offset, byte) in bytes.iter_mut().enumerate().skip(8) {
        *byte = unsafe { read_volatile(source.add(offset)) };
    }
    let response = Descriptor::decode(&bytes);
    response.validate_response()?;
    Ok(response)
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Descriptor {
    pub busy: u64,
    pub version: u32,
    pub bytes: u32,
    pub status: i32,
    pub text_pages: u32,
    pub data_pages: u32,
    pub clock_layout: u32,
    pub text_physical: [u64; TEXT_PAGES],
    pub data_physical: [u64; DATA_PAGES],
    pub reserved: [u64; 4],
}

impl Descriptor {
    pub const fn request() -> Self {
        Self {
            busy: 1,
            version: VERSION,
            bytes: BYTES as u32,
            status: -115,
            text_pages: 0,
            data_pages: 0,
            clock_layout: 0,
            text_physical: [0; TEXT_PAGES],
            data_physical: [0; DATA_PAGES],
            reserved: [0; 4],
        }
    }

    pub fn validate_request(&self) -> Result<(), Error> {
        if *self == Self::request() {
            Ok(())
        } else {
            Err(Error::Request)
        }
    }

    pub fn response(
        text_pages: u32,
        text: [u64; TEXT_PAGES],
        data: [u64; DATA_PAGES],
    ) -> Result<Self, Error> {
        let response = Self {
            busy: 0,
            version: VERSION,
            bytes: BYTES as u32,
            status: 0,
            text_pages,
            data_pages: DATA_PAGES as u32,
            clock_layout: CLOCK_LAYOUT_GENERIC_OVERFLOW_V1,
            text_physical: text,
            data_physical: data,
            reserved: [0; 4],
        };
        response.validate_response()?;
        Ok(response)
    }

    pub fn validate_response(&self) -> Result<(), Error> {
        if self.busy != 0 {
            return Err(Error::InProgress);
        }
        if self.version != VERSION {
            return Err(Error::Version);
        }
        if self.bytes as usize != BYTES {
            return Err(Error::Size);
        }
        if self.status != 0 {
            return Err(Error::HostStatus(self.status));
        }
        if self.clock_layout != CLOCK_LAYOUT_GENERIC_OVERFLOW_V1 {
            return Err(Error::ClockLayout);
        }
        if self.reserved != [0; 4] {
            return Err(Error::Reserved);
        }
        if self.text_pages == 0
            || self.text_pages as usize > TEXT_PAGES
            || self.data_pages as usize != DATA_PAGES
            || self.data_physical[TIME_PAGE] == 0
            || self.data_physical[RNG_PAGE] == 0
            || self.data_physical[1] != 0
            || self.data_physical[3] != 0
        {
            return Err(Error::Pages);
        }
        let mut seen = [0_u64; TEXT_PAGES + DATA_PAGES];
        let mut count = 0;
        for (index, physical) in self
            .text_physical
            .iter()
            .chain(self.data_physical.iter())
            .copied()
            .enumerate()
        {
            if index < TEXT_PAGES && (index < self.text_pages as usize) != (physical != 0) {
                return Err(Error::Pages);
            }
            if physical == 0 {
                continue;
            }
            if physical % PAGE_BYTES != 0
                || physical > PHYSICAL_LIMIT - PAGE_BYTES
                || seen[..count].contains(&physical)
            {
                return Err(Error::Pages);
            }
            seen[count] = physical;
            count += 1;
        }
        Ok(())
    }

    /// Explicit wire encoding avoids uninitialized padding and borrowed views
    /// of a descriptor that another kernel may be publishing.
    pub fn encode(&self) -> [u8; BYTES] {
        let mut bytes = [0_u8; BYTES];
        bytes[..8].copy_from_slice(&self.busy.to_le_bytes());
        for (index, value) in [
            self.version,
            self.bytes,
            self.status as u32,
            self.text_pages,
            self.data_pages,
            self.clock_layout,
        ]
        .into_iter()
        .enumerate()
        {
            bytes[8 + index * 4..12 + index * 4].copy_from_slice(&value.to_le_bytes());
        }
        for (index, value) in self
            .text_physical
            .iter()
            .chain(self.data_physical.iter())
            .chain(self.reserved.iter())
            .enumerate()
        {
            bytes[32 + index * 8..40 + index * 8].copy_from_slice(&value.to_le_bytes());
        }
        bytes
    }

    pub fn decode(bytes: &[u8; BYTES]) -> Self {
        let word = |offset| u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
        let long = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let mut result = Self {
            busy: long(0),
            version: word(8),
            bytes: word(12),
            status: word(16) as i32,
            text_pages: word(20),
            data_pages: word(24),
            clock_layout: word(28),
            text_physical: [0; TEXT_PAGES],
            data_physical: [0; DATA_PAGES],
            reserved: [0; 4],
        };
        for (index, value) in result
            .text_physical
            .iter_mut()
            .chain(result.data_physical.iter_mut())
            .chain(result.reserved.iter_mut())
            .enumerate()
        {
            *value = long(32 + index * 8);
        }
        result
    }
}

#[repr(C)]
pub struct Timestamp {
    pub sec: u64,
    pub nsec: u64,
}

/// Exact generic-overflow layout witnessed against the pinned Linux headers.
/// Consumers use raw scalar reads under the Linux sequence protocol.
#[repr(C)]
pub struct Clock {
    pub seq: u32,
    pub clock_mode: i32,
    pub cycle_last: u64,
    pub max_cycles: u64,
    pub mask: u64,
    pub mult: u32,
    pub shift: u32,
    pub basetime: [Timestamp; 12],
}

#[repr(C, align(64))]
pub struct TimeData {
    pub clock_data: [Clock; 2],
    pub tz_minuteswest: i32,
    pub tz_dsttime: i32,
    pub hrtimer_res: u32,
    pub unused: u32,
}

/// Exact x86 vdso_calc_ns arithmetic from the pinned Linux implementation.
/// `cycles` has already passed x86's S64_MAX counter mask. Invalid shifts fail
/// instead of invoking an undefined shift. The wide path returns the low u64
/// just like Linux's mul_u64_u32_add_u64_shr helper.
pub fn tsc_nanoseconds(
    cycles: u64,
    last: u64,
    max: u64,
    mult: u32,
    shift: u32,
    base: u64,
) -> Option<u64> {
    if shift >= 64 || cycles > i64::MAX as u64 {
        return None;
    }
    let delta = cycles.wrapping_sub(last);
    if delta > max {
        if delta & (1 << 62) != 0 {
            return Some(base >> shift);
        }
        return Some(
            (((delta & i64::MAX as u64) as u128 * mult as u128 + base as u128) >> shift) as u64,
        );
    }
    Some(delta.wrapping_mul(mult as u64).wrapping_add(base) >> shift)
}

#[inline(always)]
fn read_barrier() {
    // Match Linux's read-begin/read-retry barriers, including compiler order.
    unsafe { core::arch::asm!("lfence", options(nostack, preserves_flags)) };
}

/// Read a coherent initial-namespace Linux timestamp. Coarse clocks do not
/// need a hardware counter. High-resolution clocks require the actual TSC
/// mode; PV/HV/NONE fall back to the existing Linux syscall transport.
///
/// # Safety
/// `data` is Linux's permanent, correctly aligned generic-overflow time page,
/// retained and mapped read-only by the caller. Only Linux updates its scalar
/// fields under the witnessed sequence protocol. `cycles` is an ordered TSC
/// read, never a user-controlled callback in production.
pub unsafe fn read_clock(
    data: *const TimeData,
    clock_id: i32,
    mut cycles: impl FnMut() -> u64,
) -> Option<(i64, i64)> {
    if data.is_null() || data as usize % align_of::<TimeData>() != 0 {
        return None;
    }
    let coarse = matches!(clock_id, 5 | 6);
    if !coarse && !matches!(clock_id, 0 | 1 | 4 | 7 | 11) {
        return None;
    }
    let clock = unsafe {
        addr_of!((*data).clock_data)
            .cast::<Clock>()
            .add((clock_id == 4) as usize)
    };
    // A bounded retry permits the normal syscall fallback if a host update
    // remains in progress. It never publishes a sample from an odd sequence.
    for _ in 0..1024 {
        let seq = unsafe { read_volatile(addr_of!((*clock).seq)) };
        if seq & 1 != 0 {
            core::hint::spin_loop();
            continue;
        }
        read_barrier();
        let mode = unsafe { read_volatile(addr_of!((*clock).clock_mode)) };
        if mode == i32::MAX || (!coarse && mode != CLOCK_TSC) {
            return None;
        }
        let timestamp = unsafe {
            addr_of!((*clock).basetime)
                .cast::<Timestamp>()
                .add(clock_id as usize)
        };
        let sec = unsafe { read_volatile(addr_of!((*timestamp).sec)) };
        let base = unsafe { read_volatile(addr_of!((*timestamp).nsec)) };
        let nsec = if coarse {
            base
        } else {
            let last = unsafe { read_volatile(addr_of!((*clock).cycle_last)) };
            let max = unsafe { read_volatile(addr_of!((*clock).max_cycles)) };
            let mult = unsafe { read_volatile(addr_of!((*clock).mult)) };
            let shift = unsafe { read_volatile(addr_of!((*clock).shift)) };
            tsc_nanoseconds(cycles() & i64::MAX as u64, last, max, mult, shift, base)?
        };
        read_barrier();
        if seq != unsafe { read_volatile(addr_of!((*clock).seq)) } {
            continue;
        }
        if coarse && nsec >= 1_000_000_000 {
            return None;
        }
        let seconds = sec.checked_add(nsec / 1_000_000_000)?;
        return Some((i64::try_from(seconds).ok()?, (nsec % 1_000_000_000) as i64));
    }
    None
}

const _: () = {
    assert!(size_of::<Descriptor>() == BYTES && align_of::<Descriptor>() == 8);
    assert!(offset_of!(Descriptor, version) == 8);
    assert!(offset_of!(Descriptor, text_physical) == 32);
    assert!(offset_of!(Descriptor, data_physical) == 48);
    assert!(offset_of!(Descriptor, reserved) == 96);
    assert!(size_of::<Clock>() == 232 && align_of::<Clock>() == 8);
    assert!(offset_of!(Clock, cycle_last) == 8 && offset_of!(Clock, max_cycles) == 16);
    assert!(offset_of!(Clock, basetime) == 40);
    assert!(size_of::<TimeData>() == 512 && align_of::<TimeData>() == 64);
};
