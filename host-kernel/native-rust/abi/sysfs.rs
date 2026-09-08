// SPDX-License-Identifier: GPL-2.0-only
//! Existing sysfs setup wire layout and release-last completion.
use core::{
    mem::{align_of, offset_of, size_of},
    ptr,
    sync::atomic::{AtomicI32, Ordering},
};

pub(crate) const SETUP_MESSAGE: i32 = 0x40;
pub(crate) const SETUP_BYTES: usize = 1056;
pub(crate) const DATA_BYTES: usize = 4096;

#[repr(C)]
pub(crate) struct SetupRequest {
    pub(crate) error: i32,
    padding: i32,
    pub(crate) physical: u64,
    pub(crate) bytes: i64,
    padding3: [u8; 1024],
    padding2: i32,
    pub(crate) busy: i32,
}

/// # Safety
/// The caller retains the entire aligned request in the exact peer generation,
/// disjoint from queues. Queue publication precedes this read. The peer only
/// polls busy until this sole service completes; no Rust reference escapes.
pub(crate) unsafe fn read_setup(request: *mut u8) -> Result<(u64, usize), i32> {
    if request.is_null() || request as usize % 8 != 0 {
        return Err(-22);
    }
    let request = request.cast::<SetupRequest>();
    let busy = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!((*request).busy)) };
    if busy.load(Ordering::Acquire) != 1 {
        return Err(-16);
    }
    let physical = unsafe { ptr::read_volatile(ptr::addr_of!((*request).physical)) };
    let bytes = unsafe { ptr::read_volatile(ptr::addr_of!((*request).bytes)) };
    if bytes != DATA_BYTES as i64 || physical == 0 || physical % DATA_BYTES as u64 != 0 {
        return Err(-22);
    }
    Ok((physical, DATA_BYTES))
}

/// # Safety
/// Same retained, exclusive request as read_setup. All successful setup owners
/// have been stored, or failed publication has been rolled back. The peer may
/// free/reuse this allocation immediately after the final busy store.
pub(crate) unsafe fn complete_setup(request: *mut u8, error: i32) -> Result<(), i32> {
    if request.is_null() || request as usize % 8 != 0 || !(-4095..=0).contains(&error) {
        return Err(-22);
    }
    let request = request.cast::<SetupRequest>();
    let busy = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!((*request).busy)) };
    if busy.load(Ordering::Relaxed) != 1 {
        return Err(-16);
    }
    unsafe { ptr::write_volatile(ptr::addr_of_mut!((*request).error), error) };
    busy.store(0, Ordering::Release);
    Ok(())
}

const _: () = {
    assert!(size_of::<SetupRequest>() == SETUP_BYTES);
    assert!(align_of::<SetupRequest>() == 8);
    assert!(offset_of!(SetupRequest, error) == 0);
    assert!(offset_of!(SetupRequest, physical) == 8);
    assert!(offset_of!(SetupRequest, bytes) == 16);
    assert!(offset_of!(SetupRequest, busy) == 1052);
};
