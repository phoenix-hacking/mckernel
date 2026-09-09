// SPDX-License-Identifier: GPL-2.0-only
//! Native standard-XSAVE input policy. Hardware execution and recovery are
//! architecture providers; this module only examines a private copied buffer.

const XSAVE_MIN_BYTES: usize = 576;
const XSAVE_MAX_BYTES: usize = 65536;

pub(crate) fn buffer_size(provided: i32, configured: i32) -> Result<usize, i64> {
    if provided != configured || provided < XSAVE_MIN_BYTES as i32 {
        return Err(-22);
    }
    let bytes = provided as usize;
    if bytes > XSAVE_MAX_BYTES {
        return Err(-7);
    }
    Ok(bytes)
}

pub(crate) fn validate(
    bytes: &[u8],
    configured: i32,
    xfeatures: u64,
    mxcsr_mask: u32,
) -> Result<(), i64> {
    if buffer_size(configured, configured)? != bytes.len()
        || xfeatures & 3 != 3
        || mxcsr_mask == 0
        || mxcsr_mask & !0xffff != 0
    {
        return Err(-22);
    }
    let mxcsr = u32::from_le_bytes(bytes[24..28].try_into().unwrap());
    let state_bv = u64::from_le_bytes(bytes[512..520].try_into().unwrap());
    let compacted_bv = u64::from_le_bytes(bytes[520..528].try_into().unwrap());
    if mxcsr & !mxcsr_mask != 0
        || state_bv & !xfeatures != 0
        || compacted_bv != 0
        || bytes[528..576].iter().any(|byte| *byte != 0)
    {
        return Err(-22);
    }
    Ok(())
}

#[no_mangle]
pub extern "C" fn native_xstate_buffer_size_result(provided: i32, configured: i32) -> i64 {
    match buffer_size(provided, configured) {
        Ok(bytes) => bytes as i64,
        Err(error) => error,
    }
}

/// `buffer` names the complete private kernel allocation, not user memory.
/// The caller keeps the allocation live through the subsequent instruction.
#[no_mangle]
pub unsafe extern "C" fn native_xstate_validate_result(
    buffer: *const u8,
    bytes: usize,
    configured: i32,
    xfeatures: u64,
    mxcsr_mask: u32,
) -> i64 {
    if buffer.is_null()
        || buffer as usize & 63 != 0
        || buffer_size(configured, configured).ok() != Some(bytes)
    {
        return -22;
    }
    match validate(core::slice::from_raw_parts(buffer, bytes), configured, xfeatures, mxcsr_mask) {
        Ok(()) => 0,
        Err(error) => error,
    }
}
