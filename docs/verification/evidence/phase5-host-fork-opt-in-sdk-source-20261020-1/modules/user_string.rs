// SPDX-License-Identifier: GPL-2.0
//! Shared bounded, single-pass pathname reads for native host consumers.

use kernel::{prelude::*, uaccess::UserSlice};

/// Adapt the existing image-loader loop without reading past its first NUL.
/// Returns whether a terminator was present inside the supplied capacity.
pub(super) fn read_into(argument: usize, bytes: &mut [u8]) -> Result<bool> {
    let mut reader = UserSlice::new(argument, bytes.len()).reader();
    for byte in bytes {
        *byte = reader.read::<u8>()?;
        if *byte == 0 {
            return Ok(true);
        }
    }
    Ok(false)
}
