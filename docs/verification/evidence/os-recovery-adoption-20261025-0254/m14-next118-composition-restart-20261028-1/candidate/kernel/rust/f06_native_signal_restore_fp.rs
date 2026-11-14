// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete selected signal-return FP lifecycle; existing xstate/hardware helpers retained.
use crate::abi::{CInt, CLong, CULong, SizeT};
use core::ffi::c_void;

type Configured = unsafe extern "C" fn() -> CInt;
type Bytes = unsafe extern "C" fn(CInt, CInt) -> CLong;
type Reset = unsafe extern "C" fn() -> CLong;
type Alloc = unsafe extern "C" fn(SizeT) -> *mut c_void;
type Copy = unsafe extern "C" fn(*mut c_void, *const c_void, SizeT) -> CInt;
type Mask = unsafe extern "C" fn() -> u64;
type Mxcsr = unsafe extern "C" fn() -> u32;
type Validate = unsafe extern "C" fn(*const u8, SizeT, CInt, u64, u32) -> CLong;
type Restore = unsafe extern "C" fn(*const u8, u64) -> CLong;
type Free = unsafe extern "C" fn(*mut c_void);

/// Preserve the original signal-return FP allocation/copy/restore transaction.
///
/// # Safety
/// Callbacks retain the original architecture/current-thread exclusion and user
/// copy contract. Successful bytes callback is the existing Rust size validator,
/// bounding bytes to64KiB; allocation covers bytes+63. No exclusive reference is
/// formed over user memory or callback-owned state. Copy writes the private
/// aligned kernel buffer. Validate/restore borrow it only through their return;
/// only the original unaligned allocation pointer is freed, exactly once.
/// Restore/reset retain their separately reviewed hardware/fault-fixup contract.
/// This body adds no timeout, normalization, error policy or FP instruction.
#[inline]
pub(crate) unsafe fn restore_fp_body(
    user_address: CULong,
    size: CInt,
    configured: Configured,
    bytes: Bytes,
    reset: Reset,
    alloc: Alloc,
    copy: Copy,
    mask: Mask,
    mxcsr: Mxcsr,
    validate: Validate,
    restore: Restore,
    free: Free,
) -> CLong {
    // Original C queries configured size even on the null-user reset path.
    let configured = unsafe { configured() };
    if user_address == 0 {
        return unsafe { reset() };
    }
    let bytes = unsafe { bytes(size, configured) };
    if bytes < 0 {
        return bytes;
    }
    // Original LP64 size_t addition and alignment use unsigned wrapping bits.
    let allocation = unsafe { alloc((bytes as SizeT).wrapping_add(63)) };
    if allocation.is_null() {
        return -12; // original -ENOMEM
    }
    let aligned = ((allocation as CULong).wrapping_add(63) & !63) as *mut u8;
    let result = if unsafe {
        copy(aligned.cast(), user_address as *const c_void, bytes as SizeT)
    } != 0 {
        -14 // original any copy error becomes -EFAULT
    } else {
        let mask = unsafe { mask() };
        let result = unsafe {
            validate(aligned, bytes as SizeT, configured, mask, mxcsr())
        };
        if result == 0 {
            unsafe { restore(aligned, mask) }
        } else {
            result
        }
    };
    // SAFETY: release original allocation on every post-allocation branch,
    // including copy/validation/checked-XRSTOR error; never free aligned pointer.
    unsafe { free(allocation) };
    result
}

#[cfg(not(test))]
unsafe extern "C" {
    fn arch_native_signal_reset_fp_bridge() -> CLong;
    fn arch_native_signal_mxcsr_mask_bridge() -> u32;
    fn native_xrstor_checked(buffer: *const u8, mask: u64) -> CLong;
}

#[cfg(not(test))]
unsafe extern "C" fn validated_bytes(provided: CInt, configured: CInt) -> CLong {
    crate::native_xstate::native_xstate_buffer_size_result(provided, configured)
}

#[cfg(not(test))]
unsafe extern "C" fn tracked_alloc(bytes: SizeT) -> *mut c_void {
    // Same kmalloc_tracked int32 narrowing and NOWAIT0x2 flag as original C.
    // Existing bytes validator guarantees bytes+63 fits signed32. Tracking
    // provenance explicitly moves to this actual Rust source/line.
    unsafe {
        crate::mem_helpers::kmalloc_tracked(bytes as CInt, 0x2,
            concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt)
    }
}

#[cfg(not(test))]
unsafe extern "C" fn tracked_free(ptr: *mut c_void) {
    unsafe {
        crate::mem_helpers::kfree_tracked(ptr,
            concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt)
    }
}

/// Public ABI replacing the original selected C callback only.
///
/// # Safety
/// Original signal-return/current-thread/hardware exclusion and usercopy rules.
/// Existing helpers retain size/format checks and checked hardware restoration;
/// no HOST fixture may call this production wrapper or its hardware callbacks.
#[cfg(not(test))]
#[no_mangle]
pub unsafe extern "C" fn arch_native_signal_restore_fp_bridge(
    user_address: CULong,
    size: CInt,
) -> CLong {
    unsafe {
        restore_fp_body(user_address, size,
            crate::x86_cpu_helpers::get_xsave_size,
            validated_bytes,
            arch_native_signal_reset_fp_bridge,
            tracked_alloc,
            crate::x86_memory_helpers::copy_from_user,
            crate::x86_cpu_helpers::get_xsave_mask,
            arch_native_signal_mxcsr_mask_bridge,
            crate::native_xstate::native_xstate_validate_result,
            native_xrstor_checked,
            tracked_free)
    }
}
