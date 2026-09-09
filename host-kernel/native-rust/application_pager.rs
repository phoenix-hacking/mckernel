// SPDX-License-Identifier: GPL-2.0
//! Existing file-pager request and result geometry, without memory access.

use super::application_syscall::Request;

pub(crate) const CREATE_BYTES: usize = 4128;
pub(crate) const PATH_BYTES: usize = 4096;
pub(crate) const CHUNK_BYTES: usize = 4096;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Operation {
    Create {
        fd: i32,
        physical: u64,
    },
    Release {
        handle: u64,
        references: u64,
    },
    Io {
        write: bool,
        handle: u64,
        offset: u64,
        bytes: usize,
        physical: u64,
    },
}

impl Operation {
    pub(crate) fn decode(request: &Request) -> Result<Self, i32> {
        if request.number() != 9 {
            return Err(-22);
        }
        let args = request.arguments();
        let operation = match args[0] {
            1 => Self::Create {
                fd: args[1] as i32,
                physical: args[2],
            },
            2 => Self::Release {
                handle: args[1],
                references: args[2],
            },
            3 | 4 => {
                if args[2] > i64::MAX as u64
                    || args[3] > isize::MAX as u64
                    || args[2]
                        .checked_add(args[3])
                        .is_none_or(|end| end > i64::MAX as u64)
                {
                    return Err(-22);
                }
                Self::Io {
                    write: args[0] == 4,
                    handle: args[1],
                    offset: args[2],
                    bytes: args[3] as usize,
                    physical: args[4],
                }
            }
            _ => return Err(-38),
        };
        if let Some((physical, bytes, _)) = operation.payload() {
            if physical == 0 || physical.checked_add(bytes as u64).is_none() {
                return Err(-22);
            }
        }
        Ok(operation)
    }

    pub(crate) fn is_release(request: &Request) -> bool {
        request.number() == 9 && request.arguments()[0] == 2
    }

    pub(crate) fn payload(self) -> Option<(u64, usize, bool)> {
        match self {
            Self::Create { physical, .. } => Some((physical, CREATE_BYTES, true)),
            Self::Io {
                write,
                physical,
                bytes,
                ..
            } if bytes != 0 => Some((physical, bytes, !write)),
            _ => None,
        }
    }
}

pub(crate) fn create_result(
    output: &mut [u8],
    handle: u64,
    protection: i32,
    flags: u32,
    size: u64,
    path: &[u8],
) -> Result<(), i32> {
    if output.len() != CREATE_BYTES
        || path.len() > PATH_BYTES
        || path.last() != Some(&0)
        || handle == 0
    {
        return Err(-22);
    }
    output.fill(0);
    output[..8].copy_from_slice(&handle.to_le_bytes());
    output[8..12].copy_from_slice(&protection.to_le_bytes());
    output[12..16].copy_from_slice(&flags.to_le_bytes());
    output[16..24].copy_from_slice(&size.to_le_bytes());
    // Normal file paging leaves pgshift zero, as in the original host body.
    output[28..28 + path.len()].copy_from_slice(path);
    Ok(())
}
