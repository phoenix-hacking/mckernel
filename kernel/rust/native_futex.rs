// SPDX-License-Identifier: GPL-2.0-only
//! Native futex user-timeout decoding and bounded timer conversion.
//!
//! This does not replace futex queue ownership or the scheduler. A missing
//! timeout is zero in their existing ABI; a present expired timeout must
//! therefore retain the minimum positive timer quantum.

use crate::abi::{CInt, CLong, CULong, SizeT, TimeSpec};
use core::mem::size_of;

const NSEC_PER_SEC: i64 = 1_000_000_000;
const KTIME_MAX: i64 = i64::MAX;
const KTIME_SEC_MAX: i64 = KTIME_MAX / NSEC_PER_SEC;
const PRIVATE: i32 = 128;
const REALTIME: i32 = 256;
const WAIT: i32 = 0;
const WAIT_BITSET: i32 = 9;
type CopyFrom = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;

#[inline(always)]
pub(crate) fn ticks_now() -> u64 {
    let low: u32;
    let high: u32;
    unsafe {
        core::arch::asm!("lfence", "rdtsc", out("eax") low, out("edx") high,
            options(nostack, preserves_flags));
    }
    (high as u64) << 32 | low as u64
}

/// Range-only authorization is also valid for private WAKE, which need not
/// fault in an otherwise unmapped userspace word. WAIT prefaults separately.
pub(crate) fn word_range(address: u64, user_start: u64, user_end: u64) -> Result<(), i32> {
    if address % size_of::<u32>() as u64 != 0 {
        return Err(-22);
    }
    let end = address.checked_add(size_of::<u32>() as u64).ok_or(-14)?;
    if address < user_start || address >= user_end || end > user_end {
        return Err(-14);
    }
    Ok(())
}

/// Match pinned Linux timespec64_valid plus ktime_set, including its
/// seconds-threshold saturation rather than unsigned wrapping arithmetic.
pub(crate) fn nanoseconds(ts: &TimeSpec) -> Result<i64, i64> {
    if ts.tv_sec < 0 || !(0..NSEC_PER_SEC).contains(&ts.tv_nsec) {
        return Err(-22);
    }
    Ok(if ts.tv_sec >= KTIME_SEC_MAX {
        KTIME_MAX
    } else {
        ts.tv_sec * NSEC_PER_SEC + ts.tv_nsec
    })
}

/// Linux FUTEX_WAIT adds its relative duration to monotonic now with
/// ktime_add_safe; WAIT_BITSET already supplies an absolute deadline.
pub(crate) fn remaining(op: CInt, target: i64, now: &TimeSpec) -> Result<u64, i64> {
    let now = nanoseconds(now).map_err(|_| -5)?;
    let deadline = if op == WAIT {
        now.checked_add(target).unwrap_or(KTIME_MAX)
    } else {
        target
    };
    Ok(deadline.saturating_sub(now).max(0) as u64)
}

/// ihk_mc_get_ns_per_tsc returns picoseconds per TSC tick. Round up so
/// conversion cannot expire a positive deadline early, and cap at the
/// signed-positive range consumed by the scheduler's return ABI.
pub(crate) fn timer_ticks(nanoseconds: u64, picoseconds_per_tick: u64) -> Result<u64, i64> {
    if picoseconds_per_tick == 0 {
        return Err(-22);
    }
    let numerator = nanoseconds as u128 * 1000;
    // Freestanding x86 has no __udivti3. Compute only the 63 quotient bits
    // representable by the timer ABI, using bounded shift/subtraction.
    // A larger exact quotient greedily fills every bit and is saturated.
    let mut remainder = numerator;
    let mut quotient = 0u64;
    for bit in (0..63).rev() {
        let shifted = (picoseconds_per_tick as u128) << bit;
        if remainder >= shifted {
            remainder -= shifted;
            quotient |= 1u64 << bit;
        }
    }
    // quotient <= i64::MAX, so rounding up cannot overflow u64.
    let ticks = quotient + u64::from(remainder != 0);
    Ok(ticks.max(1).min(i64::MAX as u64))
}

/// Copy the exact user timespec once, then validate/convert only that private
/// snapshot. `clock` supplies precise pinned-Linux time, including the owned
/// private clock service when the native vDSO cannot supply a sample.
pub(crate) unsafe fn timeout(
    flags: CInt,
    user_timeout: CULong,
    has_uti_clv: CInt,
    copy_from: Option<CopyFrom>,
    mut clock: impl FnMut(CInt) -> Result<TimeSpec, i64>,
    mut picoseconds_per_tick: impl FnMut() -> Result<u64, i64>,
) -> Result<u64, i64> {
    // UTI has a Linux-owned user-copy/scheduler context. It has no accepted
    // native adapter yet; never run a guest-current-VM copy in that context.
    if has_uti_clv != 0 {
        return Err(-95);
    }
    let op = flags & !(PRIVATE | REALTIME);
    let has_timeout = user_timeout != 0 && matches!(op, WAIT | 6 | WAIT_BITSET | 11 | 13);
    let target = if has_timeout {
        let copy = copy_from.ok_or(-14)?;
        let mut ts = TimeSpec { tv_sec: 0, tv_nsec: 0 };
        if unsafe { copy((&mut ts as *mut TimeSpec).cast(), user_timeout, size_of::<TimeSpec>()) } != 0 {
            return Err(-14);
        }
        Some(nanoseconds(&ts)?)
    } else {
        None
    };

    // Match Linux's ordering: timeout copy/normalization precede do_futex's
    // clock/command rejection. Unsupported PI operations retain ENOSYS.
    if flags & REALTIME != 0 && !matches!(op, WAIT_BITSET | 11 | 13) {
        return Err(-38);
    }
    // Legacy WAKE_OP's unchecked RMW instructions have no selected guest
    // exception recovery. Keep this capability closed until that owner exists.
    if op == 5 {
        return Err(-95);
    }
    if !matches!(op, WAIT | 1 | 3 | 4 | WAIT_BITSET | 10) {
        return Err(-38);
    }
    let Some(target) = target else { return Ok(0) };
    let clock_id = if flags & REALTIME != 0 { 0 } else { 1 };
    let now = clock(clock_id)?;
    timer_ticks(remaining(op, target, &now)?, picoseconds_per_tick()?)
}
