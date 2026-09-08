// SPDX-License-Identifier: GPL-2.0
//! Linux executable-file ownership and current-caller credential adaptation.

use core::{
    mem::{align_of, offset_of, size_of},
    ptr::{self, NonNull},
    sync::atomic::{AtomicI32, Ordering},
};
use kernel::{bindings, prelude::*, uaccess::UserSlice};

const PATH_MAX: usize = 4096;

fn errno(value: i32) -> Error {
    kernel::error::to_result(value).err().unwrap_or(EIO)
}

fn check_pointer<T>(pointer: *mut T) -> Result<NonNull<T>> {
    let value = pointer as isize;
    if (-4095..0).contains(&value) {
        return Err(errno(value as i32));
    }
    NonNull::new(pointer).ok_or(EIO)
}

fn path_buffer() -> Result<Vec<u8>> {
    // Keep PATH_MAX off the kernel stack. Capacity is allocated once; subsequent
    // pushes cannot grow the allocation and initialize every byte before use.
    let mut bytes = Vec::with_capacity(PATH_MAX, GFP_KERNEL)?;
    for _ in 0..PATH_MAX {
        bytes.push(0, GFP_KERNEL)?;
    }
    Ok(bytes)
}

/// Adapt mcctrl_control_strncpy_from_user_body_result for current-task
/// userspace, retaining its chunking and separate descriptor/data error ABI.
pub(super) fn copy_string(argument: usize, compat: bool) -> Result<isize> {
    let width = if compat { 4 } else { 8 };
    let mut descriptor = [0; 32];
    UserSlice::new(argument, 4 * width)
        .reader()
        .read_slice(&mut descriptor[..4 * width])?;
    let word = |index| {
        let mut bytes = [0; 8];
        bytes[..width].copy_from_slice(&descriptor[index * width..(index + 1) * width]);
        u64::from_le_bytes(bytes) as usize
    };
    let (destination, source, count) = (word(0), word(1), word(2));
    // One initialized x86 page, outside the kernel stack. Existing source
    // consumers continue using read_into without reading past their first NUL.
    let mut buffer = path_buffer()?;
    let result = (|| -> Result<usize> {
        let mut copied = 0usize;
        while copied < count {
            let length = (count - copied).min(buffer.len());
            let input = source.checked_add(copied).ok_or(EFAULT)?;
            let terminated = super::user_string::read_into(input, &mut buffer[..length])?;
            let bytes = if terminated {
                buffer[..length].iter().position(|&byte| byte == 0).unwrap()
            } else {
                length
            };
            let output = destination.checked_add(copied).ok_or(EFAULT)?;
            let written = bytes + usize::from(terminated);
            UserSlice::new(output, written)
                .writer()
                .write_slice(&buffer[..written])?;
            copied = copied.checked_add(bytes).ok_or(EFAULT)?;
            if terminated {
                break;
            }
        }
        Ok(copied)
    })();
    let result = result.map_or_else(|error| error.to_errno() as i64, |bytes| bytes as i64);
    descriptor[3 * width..4 * width].copy_from_slice(&result.to_le_bytes()[..width]);
    UserSlice::new(argument, 4 * width)
        .writer()
        .write_slice(&descriptor[..4 * width])?;
    Ok(0)
}

pub(super) struct Executable {
    file: NonNull<bindings::file>,
    denied: bool,
    // Retained input for the later native procfs/exe integration, not yet a
    // claim that a guest process hierarchy has been published under /proc.
    _canonical_path: Vec<u8>,
}

// SAFETY: This unique Linux file reference and its balanced inode write denial
// may be retired on any task. Native process mutexes serialize replacement;
// the immutable path belongs to this owner and no file-position access escapes.
unsafe impl Send for Executable {}

impl Executable {
    pub(super) fn open(argument: usize) -> Result<Self> {
        let mut name = path_buffer()?;
        if !super::user_string::read_into(argument, &mut name).map_err(|_| EINVAL)? {
            return Err(errno(-36));
        }
        // SAFETY: The private heap pathname is bounded and NUL-terminated.
        // Linux checks execute permission, regular type, symlinks and noexec.
        let file = check_pointer(unsafe { bindings::open_exec(name.as_ptr().cast()) })?;
        let mut owned = Self {
            file,
            denied: false,
            _canonical_path: Vec::new(),
        };
        // The exact pinned open_exec no longer denies writes. Adapt the Linux
        // inline atomic_dec_unless_positive; never wrap a saturated negative
        // count through zero or acquire a denial over an existing writer.
        let counter = owned.write_count();
        let mut value = counter.load(Ordering::Relaxed);
        loop {
            if value > 0 {
                return Err(errno(-26));
            }
            let next = value.checked_sub(1).ok_or_else(|| errno(-75))?;
            match counter.compare_exchange_weak(value, next, Ordering::SeqCst, Ordering::Relaxed) {
                Ok(_) => break,
                Err(actual) => value = actual,
            }
        }
        owned.denied = true;
        // Reuse the initialized heap buffer after open_exec has finished with
        // the user filename. d_path returns a pointer into this bounded buffer.
        let path = unsafe { ptr::addr_of!((*owned.file.as_ptr()).f_path) };
        // SAFETY: This file reference pins its immutable path; the output buffer
        // is exclusively borrowed, initialized and exactly PATH_MAX bytes long.
        let resolved = check_pointer(unsafe {
            bindings::d_path(path, name.as_mut_ptr().cast(), name.len() as i32)
        })?;
        let begin = (resolved.as_ptr() as usize)
            .checked_sub(name.as_ptr() as usize)
            .ok_or(EIO)?;
        if begin >= name.len() {
            return Err(EIO);
        }
        let length = name[begin..]
            .iter()
            .position(|&byte| byte == 0)
            .ok_or(EIO)?;
        name.copy_within(begin..begin + length + 1, 0);
        name.truncate(length + 1);
        owned._canonical_path = name;
        Ok(owned)
    }

    fn write_count(&self) -> &AtomicI32 {
        // SAFETY: open_exec returns a valid regular file whose owned reference
        // pins its inode. Linux exclusively uses atomic operations on this
        // scalar counter; no Rust reference to the surrounding inode is formed.
        unsafe {
            let inode = ptr::addr_of!((*self.file.as_ptr()).f_inode).read();
            AtomicI32::from_ptr(ptr::addr_of_mut!((*inode).i_writecount.counter))
        }
    }
}

impl Drop for Executable {
    fn drop(&mut self) {
        if self.denied {
            // Match allow_write_access exactly once, before releasing the file.
            let previous = self.write_count().fetch_add(1, Ordering::SeqCst);
            assert!(previous < 0, "unbalanced executable write exclusion");
        }
        // SAFETY: This is the unique file reference returned by open_exec.
        // Linux owns deferred final file cleanup; no project callback is stored
        // in this regular file, and the denial has already been balanced.
        unsafe { bindings::fput(self.file.as_ptr()) };
    }
}

pub(super) fn credential_values() -> [u32; 8] {
    // SAFETY: We are the current syscall task. As documented by current_cred(),
    // no other task can modify its subjective credential pointer, and published
    // UID/GID fields are immutable. Read the pointer once and copy only scalars,
    // before calling any user-copy or other potentially sleeping function.
    unsafe {
        let task = bindings::get_current();
        let cred = ptr::addr_of!((*task).cred).read();
        [
            (*cred).uid.val,
            (*cred).euid.val,
            (*cred).suid.val,
            (*cred).fsuid.val,
            (*cred).gid.val,
            (*cred).egid.val,
            (*cred).sgid.val,
            (*cred).fsgid.val,
        ]
    }
}

pub(super) fn credentials(argument: usize) -> Result<isize> {
    let values = credential_values();
    // The existing Rust helper writes precisely eight 32-bit raw kernel IDs.
    // Keep its EFAULT result and do not reinterpret compat as native-long data.
    UserSlice::new(argument, size_of::<[u32; 8]>())
        .writer()
        .write(&values)?;
    Ok(0)
}

const _: () = {
    assert!(size_of::<bindings::atomic_t>() == size_of::<AtomicI32>());
    assert!(align_of::<bindings::atomic_t>() == align_of::<AtomicI32>());
    assert!(offset_of!(bindings::atomic_t, counter) == 0);
    assert!(size_of::<bindings::kuid_t>() == 4);
    assert!(size_of::<bindings::kgid_t>() == 4);
};
