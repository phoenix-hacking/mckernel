// SPDX-License-Identifier: GPL-2.0-only
//! Bounded native adapters for the eight existing guest snooping operations.

use super::super::super::sysfs_objects::AttributeOps;
use super::{
    errno,
    memory::{Claim, Region},
};
use kernel::{bindings, fmt, prelude::*, str::CString};

pub(super) struct Snoop {
    operation: u64,
    region: Option<Region>,
    bytes: usize,
    bits: usize,
}

impl Snoop {
    pub(super) fn new(claim: &Claim, operation: u64, instance: u64) -> Result<Self> {
        let (physical, bytes, bits) = match operation {
            1 | 3 | 8 => (instance, 4, 32),
            2 | 4 => (instance, 8, 64),
            5..=7 => {
                // The existing guest publishes a temporary 16-byte descriptor
                // on its stack and leaves it unchanged until CREATE completes.
                let (bits, physical) = claim.descriptor(instance)?;
                if bits < 0 || bits > 4096 * 8 || operation == 5 && (bits == 0 || bits % 8 != 0) {
                    return Err(EINVAL);
                }
                (physical, (bits as usize).div_ceil(8), bits as usize)
            }
            _ => return Err(EINVAL),
        };
        if matches!(operation, 1..=4 | 8) && physical % bytes as u64 != 0 {
            return Err(EINVAL);
        }
        let region = if bytes == 0 {
            None
        } else {
            Some(claim.snoop(physical, bytes)?)
        };
        Ok(Self {
            operation,
            region,
            bytes,
            bits,
        })
    }

    fn number(&self) -> Result<u64> {
        self.region.as_ref().ok_or(EIO)?.number()
    }

    fn bitmap(&self, output: &mut [u8]) -> Result<usize> {
        if self.bits == 0 {
            *output.first_mut().ok_or(EIO)? = b'\n';
            return Ok(1);
        }
        let words = self.bits.div_ceil(64);
        let mut snapshot = Vec::with_capacity(words, GFP_KERNEL)?;
        for _ in 0..words {
            snapshot.push(0u64, GFP_KERNEL)?;
        }
        // SAFETY: This private aligned vector covers the bounded guest byte
        // count, including zero padding in the final word. The mutable byte
        // view ends before Linux borrows the immutable bitmap words.
        self.region.as_ref().ok_or(EIO)?.copy(unsafe {
            core::slice::from_raw_parts_mut(snapshot.as_mut_ptr().cast(), self.bytes)
        })?;
        // SAFETY: The explicit-count API receives an owned, aligned and fully
        // bounded snapshot, and a private Linux sysfs output buffer. It keeps
        // neither pointer. The existing setup adapter uses the same functions.
        let count = unsafe {
            let print = if self.operation == 6 {
                bindings::bitmap_print_list_to_buf
            } else {
                bindings::bitmap_print_bitmask_to_buf
            };
            print(
                output.as_mut_ptr().cast(),
                snapshot.as_ptr(),
                self.bits as i32,
                0,
                output.len(),
            )
        };
        kernel::error::to_result(count)?;
        let count = count as usize;
        if count < 2 || count > output.len() || output[count - 2..count] != *b"\n\0" {
            return Err(errno(-75));
        }
        Ok(count - 1)
    }
}

impl AttributeOps for Snoop {
    fn store(&self, _input: &[u8]) -> Result<usize> {
        // Existing snooping ops have no store callback; the legacy mcctrl
        // dispatcher reports ENOSPC for that case.
        Err(ENOSPC)
    }

    fn show(&self, output: &mut [u8]) -> Result<usize> {
        if matches!(self.operation, 6 | 7) {
            return self.bitmap(output);
        }
        if self.operation == 5 {
            let mut snapshot = Vec::with_capacity(self.bytes, GFP_KERNEL)?;
            for _ in 0..self.bytes {
                snapshot.push(0u8, GFP_KERNEL)?;
            }
            self.region.as_ref().ok_or(EIO)?.copy(&mut snapshot)?;
            // Match the existing remote "%.*s" precision: a full bounded
            // string need not contain NUL, but its newline must still fit.
            let length = snapshot
                .iter()
                .position(|&byte| byte == 0)
                .unwrap_or(self.bytes);
            let target = output.get_mut(..length + 1).ok_or_else(|| errno(-75))?;
            target[..length].copy_from_slice(&snapshot[..length]);
            target[length] = b'\n';
            return Ok(length + 1);
        }
        let value = self.number()?;
        let text = match self.operation {
            1 => CString::try_from_fmt(fmt!("{}\n", value as u32 as i32))?,
            2 => CString::try_from_fmt(fmt!("{}\n", value as i64))?,
            3 => CString::try_from_fmt(fmt!("{}\n", value as u32))?,
            4 => CString::try_from_fmt(fmt!("{}\n", value))?,
            8 => CString::try_from_fmt(fmt!("{}K\n", value as u32 >> 10))?,
            _ => return Err(EINVAL),
        };
        let bytes = text.as_bytes();
        output
            .get_mut(..bytes.len())
            .ok_or_else(|| errno(-75))?
            .copy_from_slice(bytes);
        Ok(bytes.len())
    }
}
