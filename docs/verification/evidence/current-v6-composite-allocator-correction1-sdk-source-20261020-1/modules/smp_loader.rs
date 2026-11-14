// SPDX-License-Identifier: GPL-2.0
//! Bounded Linux file ownership for the native image-load ioctl.

use super::smp_resource::OsToken;
use core::{ffi::c_void, ptr, ptr::NonNull};
use kernel::{bindings, prelude::*};

const MAX_IMAGE_FILE_BYTES: usize = 64 << 20;
const MAX_FILENAME_BYTES: usize = 256;

/// Retain bounded byte-wise user reads, stopping at NUL before a page boundary.
pub(super) fn read_user_string<const N: usize>(
    argument: usize,
    require_nul: bool,
) -> Result<[u8; N]> {
    let mut bytes = [0_u8; N];
    if !super::user_string::read_into(argument, &mut bytes)? && require_nul {
        Err(EINVAL)
    } else {
        Ok(bytes)
    }
}

struct ImageFile {
    buffer: NonNull<c_void>,
    length: usize,
}

impl ImageFile {
    fn read(argument: usize) -> Result<Self> {
        // Match strndup_user(..., 256), stopping at NUL without touching the
        // rest of its page. Compat already normalized the top-level address.
        let name = read_user_string::<MAX_FILENAME_BYTES>(argument, true)?;
        let mut raw = ptr::null_mut();
        // SAFETY: The checked filename is NUL-terminated stack storage. Linux
        // owns open/read/write-exclusion/close and returns a vmalloc buffer.
        // Passing NULL file_size is essential: the exact implementation then
        // rejects an oversized file BEFORE allocation. Offset zero requires a
        // whole-file read and runs the Linux security hooks for a kernel image.
        let result = unsafe {
            bindings::kernel_read_file_from_path(
                name.as_ptr().cast(),
                0,
                &mut raw,
                MAX_IMAGE_FILE_BYTES,
                ptr::null_mut(),
                bindings::kernel_read_file_id_READING_KEXEC_IMAGE,
            )
        };
        if result < 0 {
            kernel::error::to_result(result as i32)?;
            return Err(EIO);
        }
        let image = Self {
            buffer: NonNull::new(raw).ok_or(EIO)?,
            length: result as usize,
        };
        if image.length == 0 || image.length > MAX_IMAGE_FILE_BYTES {
            return Err(EIO);
        }
        Ok(image)
    }

    fn bytes(&self) -> &[u8] {
        // SAFETY: Linux returned the complete immutable buffer with this
        // bounded positive length. The owning borrow excludes vfree in Drop.
        unsafe { core::slice::from_raw_parts(self.buffer.as_ptr().cast(), self.length) }
    }
}

impl Drop for ImageFile {
    fn drop(&mut self) {
        // SAFETY: This is the one vmalloc owner returned by kernel_read_file;
        // all borrowed header/segment slices end before this owner is dropped.
        // Linux kvfree recognizes vmalloc storage and calls vfree. Unlike
        // vfree itself, kvfree is in this exact kernel's generated bindings.
        unsafe { bindings::kvfree(self.buffer.as_ptr()) };
    }
}

/// IHK pins the generation and module and holds the OS operation mutex.
pub(super) fn load(owner: OsToken, argument: usize) -> Result<isize> {
    super::smp_memory::invalidate_os_image(owner)?;
    let image = ImageFile::read(argument)?;
    super::smp_cpu::load_os_image(owner, image.bytes())?;
    Ok(0)
}
