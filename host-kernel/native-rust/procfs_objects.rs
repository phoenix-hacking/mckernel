// SPDX-License-Identifier: GPL-2.0-only
//! Native Linux procfs publication and per-open callback retirement.
//!
//! Linux owns dentries, inode references and proc_entry_rundown. Rust keeps the
//! callback payload and each open session alive until that rundown completes.
//! Backend callbacks must not acquire the namespace lock or remove themselves.

use core::{
    ffi::{c_char, c_void},
    ptr,
    sync::atomic::{AtomicPtr, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    str::CString,
    sync::{new_mutex, Arc, Mutex},
    uaccess::UserSlice,
};

/// Pinned proc_fs.h ABI, independently checked by the C layout witness. The
/// target's CONFIG_COMPAT field is selected by the same Kbuild configuration.
pub(crate) mod abi {
    use super::*;
    #[repr(C)]
    pub(crate) struct Operations {
        pub flags: u32,
        pub open: Option<unsafe extern "C" fn(*mut bindings::inode, *mut bindings::file) -> i32>,
        pub read: Option<
            unsafe extern "C" fn(*mut bindings::file, *mut c_char, usize, *mut i64) -> isize,
        >,
        pub read_iter: Option<unsafe extern "C" fn(*mut c_void, *mut c_void) -> isize>,
        pub write: Option<
            unsafe extern "C" fn(*mut bindings::file, *const c_char, usize, *mut i64) -> isize,
        >,
        pub seek: Option<unsafe extern "C" fn(*mut bindings::file, i64, i32) -> i64>,
        pub release: Option<unsafe extern "C" fn(*mut bindings::inode, *mut bindings::file) -> i32>,
        pub poll: Option<unsafe extern "C" fn(*mut bindings::file, *mut c_void) -> u32>,
        pub ioctl: Option<unsafe extern "C" fn(*mut bindings::file, u32, usize) -> i64>,
        #[cfg(CONFIG_COMPAT)]
        pub compat_ioctl: Option<unsafe extern "C" fn(*mut bindings::file, u32, usize) -> i64>,
        pub mmap:
            Option<unsafe extern "C" fn(*mut bindings::file, *mut bindings::vm_area_struct) -> i32>,
        pub get_unmapped_area:
            Option<unsafe extern "C" fn(*mut bindings::file, usize, usize, usize, usize) -> usize>,
    }
    // SAFETY: Every descriptor is immutable; its function pointers name resident
    // code. File owners complete Linux rundown before their module may unload.
    unsafe impl Sync for Operations {}

    extern "C" {
        pub(super) fn proc_mkdir_mode(
            name: *const c_char,
            mode: u16,
            parent: *mut bindings::proc_dir_entry,
        ) -> *mut bindings::proc_dir_entry;
        pub(super) fn proc_create_data(
            name: *const c_char,
            mode: u16,
            parent: *mut bindings::proc_dir_entry,
            operations: *const Operations,
            data: *mut c_void,
        ) -> *mut bindings::proc_dir_entry;
        pub(super) fn proc_set_user(
            entry: *mut bindings::proc_dir_entry,
            uid: bindings::kuid_t,
            gid: bindings::kgid_t,
        );
        pub(super) fn proc_remove(entry: *mut bindings::proc_dir_entry);
    }
}

fn overflow() -> Error {
    kernel::error::to_result(-75).unwrap_err()
}

fn validate_name(name: &CStr) -> Result {
    let bytes = name.as_bytes();
    if bytes.is_empty() || bytes == b"." || bytes == b".." || bytes.contains(&b'/') {
        return Err(EINVAL);
    }
    if bytes.len() > 255 {
        return Err(kernel::error::to_result(-36).unwrap_err());
    }
    Ok(())
}

struct Name {
    id: u64,
    parent: u64,
    value: CString,
}

struct Namespace {
    next: u64,
    names: Vec<Name>,
}

struct Node {
    id: u64,
    depth: usize,
    parent: Option<Arc<Node>>,
    namespace: Arc<Mutex<Namespace>>,
    entry: AtomicPtr<bindings::proc_dir_entry>,
}

impl Node {
    /// Called with the shared namespace locked. Ancestors retain their Rust
    /// identities even after Linux recursively removes their proc entries.
    fn live(&self) -> bool {
        let mut next = Some(self);
        while let Some(node) = next {
            if node.entry.load(Ordering::Relaxed).is_null() {
                return false;
            }
            next = node.parent.as_deref();
        }
        true
    }
}

struct Owner(Arc<Node>);

impl Owner {
    fn publish(
        parent: Option<&Directory>,
        name: &CStr,
        create: impl FnOnce(
            *const c_char,
            *mut bindings::proc_dir_entry,
        ) -> *mut bindings::proc_dir_entry,
    ) -> Result<Self> {
        validate_name(name)?;
        let namespace = match parent {
            Some(parent) => parent.0 .0.namespace.clone(),
            None => Arc::pin_init(
                new_mutex!(Namespace {
                    next: 0,
                    names: Vec::new()
                }),
                GFP_KERNEL,
            )?,
        };
        let mut state = namespace.lock();
        let (parent_id, depth, raw_parent) = match parent {
            Some(parent) => {
                let node = &parent.0 .0;
                if !node.live() {
                    return Err(ENODEV);
                }
                if node.depth == 64 {
                    return Err(EINVAL);
                }
                (node.id, node.depth + 1, node.entry.load(Ordering::Relaxed))
            }
            None => (0, 0, ptr::null_mut()),
        };
        if state
            .names
            .iter()
            .any(|old| old.parent == parent_id && old.value.as_bytes() == name.as_bytes())
        {
            return Err(EEXIST);
        }
        let value = CString::try_from(name)?;
        state.names.reserve(1, GFP_KERNEL)?;
        let id = state.next.checked_add(1).ok_or_else(overflow)?;
        state.next = id;
        let node = Arc::new(
            Node {
                id,
                depth,
                parent: parent.map(|parent| parent.0 .0.clone()),
                namespace: namespace.clone(),
                entry: AtomicPtr::new(ptr::null_mut()),
            },
            GFP_KERNEL,
        )?;
        // Metadata insertion precedes publication, so no fallible Rust work
        // remains once Linux may invoke the separately retained callback data.
        state.names.push(
            Name {
                id,
                parent: parent_id,
                value,
            },
            GFP_KERNEL,
        )?;
        let raw = create(state.names.last().unwrap().value.as_char_ptr(), raw_parent);
        if raw.is_null() {
            state.names.pop();
            return Err(ENOMEM);
        }
        node.entry.store(raw, Ordering::Relaxed);
        Ok(Self(node))
    }
}

impl Drop for Owner {
    fn drop(&mut self) {
        let mut state = self.0.namespace.lock();
        let parent_live = self.0.parent.as_ref().is_none_or(|parent| parent.live());
        let entry = self.0.entry.swap(ptr::null_mut(), Ordering::Relaxed);
        if parent_live && !entry.is_null() {
            // SAFETY: This still-live published owner is removed once under
            // the shared namespace lock. Linux drains callbacks and forcibly
            // releases successful opens before returning. Ancestor removal
            // already did this for descendants whose parent is no longer live.
            unsafe { abi::proc_remove(entry) };
        }
        let index = state
            .names
            .iter()
            .position(|name| name.id == self.0.id)
            .expect("procfs owner lost its reserved name");
        state.names.swap_remove(index);
    }
}

/// Unique publication owner; descendants retain ancestor identities. Drop may
/// sleep while Linux drains descendant operations and open-session releases.
pub(crate) struct Directory(Owner);

impl Directory {
    pub(crate) fn new(parent: Option<&Self>, name: &CStr) -> Result<Self> {
        Owner::publish(parent, name, |name, parent| {
            // SAFETY: Names are terminated, the parent is live and all native
            // namespace mutations are excluded until publication finishes.
            unsafe { abi::proc_mkdir_mode(name, 0o555, parent) }
        })
        .map(Self)
    }
}

/// A backend owns every remote operation independently after it is published.
/// Release may run during namespace removal, while the userspace fd stays open.
/// A failed read/write must not advance the session's stream position itself.
pub(crate) trait Session: Send {
    fn read(&mut self, position: i64, output: &mut [u8]) -> Result<usize>;
    fn write(&mut self, _position: i64, _input: &[u8]) -> Result<usize> {
        Err(EIO)
    }
    fn release(&mut self) -> Result {
        Ok(())
    }
}

pub(crate) trait FileOps: Send + Sync + 'static {
    type Session: Session;
    const WRITABLE: bool = false;
    fn open(&self) -> Result<Self::Session>;
}

struct Open<S> {
    session: Pin<Box<Mutex<Option<S>>>>,
}

/// Field order drains Linux before freeing the callback's published payload.
pub(crate) struct File<T: FileOps> {
    _owner: Owner,
    _data: Box<T>,
}

impl<T: FileOps> File<T> {
    const OPS: abi::Operations = abi::Operations {
        flags: 0,
        open: Some(open::<T>),
        read: Some(read::<T>),
        read_iter: None,
        write: if T::WRITABLE { Some(write::<T>) } else { None },
        seek: Some(seek),
        release: Some(release::<T>),
        poll: None,
        ioctl: None,
        #[cfg(CONFIG_COMPAT)]
        compat_ioctl: None,
        mmap: None,
        get_unmapped_area: None,
    };

    pub(crate) fn new(parent: &Directory, name: &CStr, mode: u16, data: T) -> Result<Self> {
        Self::owned(
            parent,
            name,
            mode,
            data,
            bindings::kuid_t { val: 0 },
            bindings::kgid_t { val: 0 },
        )
    }

    pub(crate) fn owned(
        parent: &Directory,
        name: &CStr,
        mode: u16,
        data: T,
        uid: bindings::kuid_t,
        gid: bindings::kgid_t,
    ) -> Result<Self> {
        if mode & !0o777 != 0 {
            return Err(EINVAL);
        }
        let data = Box::new(data, GFP_KERNEL)?;
        let operations: &'static abi::Operations = &Self::OPS;
        let owner = Owner::publish(Some(parent), name, |name, parent| {
            // SAFETY: Linux borrows this stable Box and immutable descriptor
            // only until our owner completes proc_remove/rundown. procfs copies
            // the name; inode->i_private is exactly this borrowed payload.
            let entry = unsafe {
                abi::proc_create_data(
                    name,
                    mode,
                    parent,
                    operations,
                    ptr::from_ref(&*data).cast_mut().cast(),
                )
            };
            if !entry.is_null() {
                // SAFETY: Publication/removal is excluded; credentials are
                // already kernel kuid/kgid values supplied by the owner.
                unsafe { abi::proc_set_user(entry, uid, gid) };
            }
            entry
        })?;
        Ok(Self {
            _owner: owner,
            _data: data,
        })
    }
}

// SAFETY: Linux pins inode/file and the published payload through proc_open.
// Failure transfers no session. Successful opens get one Linux-serialized
// release, including forced release from proc_entry_rundown.
unsafe extern "C" fn open<T: FileOps>(
    inode: *mut bindings::inode,
    file: *mut bindings::file,
) -> i32 {
    let result = (|| -> Result {
        let data = unsafe { (*inode).i_private.cast::<T>() };
        // Finish allocation before the backend acquires a session, so every
        // successful backend open receives exactly one release even under OOM.
        let session = Box::pin_init(new_mutex!(None::<T::Session>), GFP_KERNEL)?;
        let open = Box::new(Open { session }, GFP_KERNEL)?;
        *open.session.lock() = Some(unsafe { &*data }.open()?);
        unsafe { (*file).private_data = Box::into_raw(open).cast() };
        Ok(())
    })();
    result.err().map_or(0, |error| error.to_errno())
}

// SAFETY: Only the corresponding live proc entry invokes this callback; the
// successful open installed this unique Open, and Linux drains I/O before
// calling exactly one release. Duplicated/inherited fds share the same session.
unsafe extern "C" fn release<T: FileOps>(
    _inode: *mut bindings::inode,
    file: *mut bindings::file,
) -> i32 {
    let data = unsafe { (*file).private_data.cast::<Open<T::Session>>() };
    unsafe { (*file).private_data = ptr::null_mut() };
    let open = unsafe { Box::from_raw(data) };
    let mut session = open.session.lock().take().unwrap();
    let result = session.release();
    result.err().map_or(0, |error| error.to_errno())
}

const IO_BYTES: usize = 4096;

fn buffer(bytes: usize) -> Result<Vec<u8>> {
    let mut output = Vec::with_capacity(bytes, GFP_KERNEL)?;
    for _ in 0..bytes {
        output.push(0, GFP_KERNEL)?;
    }
    Ok(output)
}

// SAFETY: Linux's pde use count protects the session against forced release for
// the entire callback. Per-open locking serializes backend operations. Only
// UserSlice accesses the user address; no pointer becomes a Rust user slice.
unsafe extern "C" fn read<T: FileOps>(
    file: *mut bindings::file,
    buffer: *mut c_char,
    count: usize,
    position: *mut i64,
) -> isize {
    let result = (|| -> Result<usize> {
        if count == 0 {
            return Ok(0);
        }
        let open = unsafe { &*(*file).private_data.cast::<Open<T::Session>>() };
        let mut session = open.session.lock();
        let before = unsafe { *position };
        let mut output = self::buffer(count.min(IO_BYTES))?;
        let bytes = session.as_mut().unwrap().read(before, &mut output)?;
        if bytes > count.min(IO_BYTES) {
            return Err(overflow());
        }
        UserSlice::new(buffer as usize, bytes)
            .writer()
            .write_slice(&output[..bytes])?;
        unsafe { *position = before.wrapping_add(bytes as i64) };
        Ok(bytes)
    })();
    result.map_or_else(|error| error.to_errno() as isize, |bytes| bytes as isize)
}

// SAFETY: Same session lifetime as read. Copy all bounded input before invoking
// the backend, so a user copy fault cannot publish a write or advance position.
unsafe extern "C" fn write<T: FileOps>(
    file: *mut bindings::file,
    buffer: *const c_char,
    count: usize,
    position: *mut i64,
) -> isize {
    let result = (|| -> Result<usize> {
        if count == 0 {
            return Ok(0);
        }
        let open = unsafe { &*(*file).private_data.cast::<Open<T::Session>>() };
        let mut session = open.session.lock();
        let before = unsafe { *position };
        let bytes = count.min(IO_BYTES);
        let mut input = self::buffer(bytes)?;
        UserSlice::new(buffer as usize, bytes)
            .reader()
            .read_slice(&mut input[..bytes])?;
        let written = session.as_mut().unwrap().write(before, &input)?;
        if written > bytes {
            return Err(overflow());
        }
        unsafe { *position = before.wrapping_add(written as i64) };
        Ok(written)
    })();
    result.map_or_else(|error| error.to_errno() as isize, |bytes| bytes as isize)
}

// SAFETY: VFS holds its file-position lock for lseek, including shared fds. The
// original Rust procfs helper accepts SET/CUR only and uses wrapping addition.
unsafe extern "C" fn seek(file: *mut bindings::file, offset: i64, whence: i32) -> i64 {
    let current = unsafe { (*file).f_pos };
    let position = match whence {
        0 => offset,
        1 => current.wrapping_add(offset),
        _ => return EINVAL.to_errno() as i64,
    };
    unsafe { (*file).f_pos = position };
    position
}
