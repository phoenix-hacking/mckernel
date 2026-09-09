// SPDX-License-Identifier: GPL-2.0
//! Linux regular-file pager owners within one retained McKernel OS generation.

use super::{application_pager as wire, application_rpc::Token};
use core::{ptr, ptr::NonNull};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

const CAPACITY: usize = 4096;
// include/linux/fs.h in the pinned Linux 6.12 build. Its cast macros are not
// emitted by bindgen; the native fixture binds these four definitions.
const FMODE_READ: u32 = 1 << 0;
const FMODE_WRITE: u32 = 1 << 1;
const FMODE_PREAD: u32 = 1 << 3;
const FMODE_PWRITE: u32 = 1 << 4;

fn errno(value: i32) -> Error {
    kernel::error::to_result(value).err().unwrap_or(EIO)
}

fn buffer(bytes: usize) -> Result<Vec<u8>> {
    let mut output = Vec::with_capacity(bytes, GFP_KERNEL)?;
    for _ in 0..bytes {
        output.push(0, GFP_KERNEL)?;
    }
    Ok(output)
}

struct File {
    pointer: NonNull<bindings::file>,
}

// SAFETY: fget supplies a Linux file reference; Arc owns it until final fput.
// All operations use Linux's concurrent positional-I/O interface and private
// kernel buffers. No file position or borrowed pointer escapes this owner.
unsafe impl Send for File {}
unsafe impl Sync for File {}

impl Drop for File {
    fn drop(&mut self) {
        // SAFETY: Exactly the owned reference acquired by fget. Linux performs
        // final cleanup in the proper context, including deferred kthread fput.
        unsafe { bindings::fput(self.pointer.as_ptr()) };
    }
}

impl File {
    fn inode(&self) -> usize {
        // SAFETY: The owned file reference pins its immutable inode pointer.
        unsafe { ptr::addr_of!((*self.pointer.as_ptr()).f_inode).read() as usize }
    }

    fn stat(&self) -> Result<bindings::kstat> {
        let mut stat = core::mem::MaybeUninit::<bindings::kstat>::zeroed();
        // SAFETY: The file pins its path. Linux initializes kstat on success.
        let result = unsafe {
            bindings::vfs_getattr(
                ptr::addr_of!((*self.pointer.as_ptr()).f_path),
                stat.as_mut_ptr(),
                bindings::STATX_BASIC_STATS,
                bindings::AT_STATX_SYNC_AS_STAT,
            )
        };
        kernel::error::to_result(result)?;
        Ok(unsafe { stat.assume_init() })
    }

    fn size(&self) -> Result<u64> {
        u64::try_from(self.stat()?.size).map_err(|_| EIO)
    }
}

pub(crate) struct Prepared {
    file: Arc<File>,
    path: Vec<u8>,
    output: Vec<u8>,
    protection: i32,
    flags: u32,
    size: u64,
}

impl Prepared {
    pub(crate) fn open(fd: i32) -> Result<Self> {
        if fd < 0 {
            return Err(errno(-9));
        }
        // SAFETY: This is the original Linux WAIT caller, with its own fd table.
        let pointer = NonNull::new(unsafe { bindings::fget(fd as u32) }).ok_or(errno(-9))?;
        let file = Arc::new(File { pointer }, GFP_KERNEL)?;
        let stat = file.stat()?;
        if stat.mode as u32 & bindings::S_IFMT != bindings::S_IFREG {
            return Err(errno(-3)); // Original guest switches to the device pager.
        }
        let (mode, mount_flags, magic) = unsafe {
            // SAFETY: File pins inode, superblock and mount. f_mode is immutable
            // after open; mount flags are copied once, as in the Linux check.
            let raw = file.pointer.as_ptr();
            let inode = ptr::addr_of!((*raw).f_inode).read();
            (
                ptr::addr_of!((*raw).f_mode).read(),
                ptr::read_volatile(ptr::addr_of!((*(*raw).f_path.mnt).mnt_flags)),
                ptr::addr_of!((*(*inode).i_sb).s_magic).read(),
            )
        };
        if magic == bindings::PROC_SUPER_MAGIC as _ {
            return Err(errno(-3));
        }
        // These require the distinct device/huge-page contract, not file I/O.
        if magic == bindings::HUGETLBFS_MAGIC as _ {
            return Err(errno(-95));
        }
        let mut protection = 0;
        if mode & (FMODE_READ | FMODE_PREAD) == (FMODE_READ | FMODE_PREAD) {
            protection |= 1;
        }
        if mode & (FMODE_WRITE | FMODE_PWRITE) == (FMODE_WRITE | FMODE_PWRITE) {
            protection |= 2;
        }
        if mount_flags & bindings::MNT_NOEXEC as i32 == 0 {
            protection |= 4;
        }
        if protection & 1 == 0 {
            return Err(EACCES);
        }
        let mut path = buffer(wire::PATH_BYTES)?;
        let resolved = unsafe {
            bindings::d_path(
                ptr::addr_of!((*file.pointer.as_ptr()).f_path),
                path.as_mut_ptr().cast(),
                path.len() as i32,
            )
        };
        let value = resolved as isize;
        if (-4095..0).contains(&value) {
            // The old pager returns an empty optional path if d_path fails.
            path.truncate(1);
            path[0] = 0;
        } else {
            let offset = (resolved as usize)
                .checked_sub(path.as_ptr() as usize)
                .ok_or(EIO)?;
            if offset >= path.len() {
                return Err(EIO);
            }
            let size = path[offset..].iter().position(|&b| b == 0).ok_or(EIO)? + 1;
            path.copy_within(offset..offset + size, 0);
            path.truncate(size);
        }
        // Adapt the selected mcctrl_pager_treat_as_device_path_result predicate.
        if path.starts_with(b"/tmp/ompi.")
            || path.starts_with(b"/dev/shm/")
            || path.starts_with(b"/var/opt/FJSVtcs/ple/daemonif/")
                && !path
                    .windows(b"dstore_sm.lock".len())
                    .any(|p| p == b"dstore_sm.lock")
        {
            return Err(errno(-3));
        }
        let mut flags = if magic == bindings::TMPFS_MAGIC as _ {
            4
        } else {
            0
        };
        if path.windows(3).any(|p| p == b".so") {
            flags = 8;
        }
        Ok(Self {
            file,
            path,
            output: buffer(wire::CREATE_BYTES)?,
            protection,
            flags,
            size: u64::try_from(stat.size).map_err(|_| EIO)?,
        })
    }
}

struct Pager {
    token: Token,
    references: u64,
    readable: Arc<File>,
    writable: Option<Arc<File>>,
}

#[pin_data]
pub(crate) struct Registry {
    #[pin]
    entries: Mutex<Vec<Option<Pager>>>,
}

impl Registry {
    pub(crate) fn new() -> Result<Arc<Self>> {
        let mut entries = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            entries.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { entries <- new_mutex!(entries) }),
            GFP_KERNEL,
        )
    }

    /// Called only after the exact request wins its completion/cancellation
    /// race. Failed output copying publishes no file handle or server reference.
    pub(crate) fn create(
        &self,
        mut prepared: Prepared,
        copy: impl FnOnce(&mut [u8]) -> Result,
    ) -> Result<i64> {
        let mut entries = self.entries.lock();
        let existing = entries.iter().position(|slot| {
            slot.as_ref()
                .is_some_and(|pager| pager.readable.inode() == prepared.file.inode())
        });
        let index = existing
            .or_else(|| entries.iter().position(Option::is_none))
            .ok_or(EAGAIN)?;
        let (token, references) = match &entries[index] {
            Some(pager) => (
                pager.token,
                pager.references.checked_add(1).ok_or(errno(-75))?,
            ),
            None => (Token::allocate().map_err(errno)?, 1),
        };
        wire::create_result(
            &mut prepared.output,
            token.wire(),
            prepared.protection,
            prepared.flags,
            prepared.size,
            &prepared.path,
        )
        .map_err(errno)?;
        copy(&mut prepared.output)?;
        if let Some(pager) = &mut entries[index] {
            pager.references = references;
            if pager.writable.is_none() && prepared.protection & 2 != 0 {
                pager.writable = Some(prepared.file.clone());
            }
        } else {
            entries[index] = Some(Pager {
                token,
                references,
                readable: prepared.file.clone(),
                writable: (prepared.protection & 2 != 0).then(|| prepared.file.clone()),
            });
        }
        pr_info!(
            "file_pager=create handle={} references={} shared={}\n",
            token.wire(),
            references,
            existing.is_some() as u8
        );
        Ok(0)
    }

    pub(crate) fn release(&self, handle: u64, references: u64) -> Result<i64> {
        let removed = {
            let mut entries = self.entries.lock();
            let slot = entries
                .iter_mut()
                .find(|slot| {
                    slot.as_ref()
                        .is_some_and(|pager| pager.token.wire() == handle)
                })
                .ok_or(errno(-9))?;
            let pager = slot.as_mut().unwrap();
            if references == 0 || references > pager.references {
                return Err(EINVAL);
            }
            pager.references -= references;
            let remaining = pager.references;
            let removed = if remaining == 0 { slot.take() } else { None };
            pr_info!(
                "file_pager=release handle={} references={} remaining={}\n",
                handle,
                references,
                remaining
            );
            removed
        };
        // File references drop outside the registry lock. In-flight I/O retains
        // its own Arc even if a final guest RELEASE removes this table entry.
        drop(removed);
        Ok(0)
    }

    pub(crate) fn io(
        &self,
        write: bool,
        handle: u64,
        offset: u64,
        bytes: usize,
        mut copy: impl FnMut(usize, &mut [u8], bool) -> Result,
    ) -> Result<i64> {
        let file = {
            let entries = self.entries.lock();
            let pager = entries
                .iter()
                .flatten()
                .find(|pager| pager.token.wire() == handle)
                .ok_or(errno(-9))?;
            if write {
                pager.writable.as_ref().cloned().ok_or(errno(-9))?
            } else {
                pager.readable.clone()
            }
        };
        let size = file.size()?;
        if (write && offset >= size) || (!write && offset > size) || bytes == 0 {
            return Ok(0);
        }
        let limit = if write {
            bytes.min((size - offset).min(usize::MAX as u64) as usize)
        } else {
            bytes
        };
        let mut buffer = buffer(wire::CHUNK_BYTES)?;
        let mut done = 0usize;
        while done < limit {
            let length = (limit - done).min(buffer.len());
            if write {
                copy(done, &mut buffer[..length], false)?;
            } else {
                buffer[..length].fill(0);
            }
            let mut count = 0;
            loop {
                let mut position =
                    i64::try_from(offset + (done + count) as u64).map_err(|_| EINVAL)?;
                // SAFETY: The Arc pins the Linux file throughout this operation.
                // Only private initialized kernel storage is passed. The exact
                // retained guest payload is copied separately outside file I/O.
                let result = unsafe {
                    if write {
                        bindings::kernel_write(
                            file.pointer.as_ptr(),
                            buffer.as_ptr().cast(),
                            length,
                            &mut position,
                        )
                    } else {
                        bindings::kernel_read(
                            file.pointer.as_ptr(),
                            buffer.as_mut_ptr().add(count).cast(),
                            length - count,
                            &mut position,
                        )
                    }
                };
                if result < 0 {
                    return Err(errno(result as i32));
                }
                let result = result as usize;
                if result > length - count {
                    return Err(EIO);
                }
                count += result;
                if write || result == 0 || count == length {
                    break;
                }
            }
            if write {
                done += count;
                if count != length {
                    break;
                }
            } else {
                // Original pager reports a complete zero-padded page at EOF.
                copy(done, &mut buffer[..length], true)?;
                done += length;
            }
        }
        Ok(done as i64)
    }
}
