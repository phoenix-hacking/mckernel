// SPDX-License-Identifier: GPL-2.0-only
//! Owned Linux sysfs objects for the native mcctrl tree.
//!
//! The legacy tree's C mkdir/create/unlink primitives have no safe Rust
//! counterpart in the pinned Linux. Reuse its kobject and kobj_attribute APIs;
//! Rust owns names, callback state, publication and retirement. No McKernel
//! request is acknowledged here. The tree/service must retain these owners.

use core::{
    cell::UnsafeCell,
    mem::{offset_of, MaybeUninit},
    pin::Pin,
    ptr,
};
use kernel::{
    bindings,
    prelude::*,
    str::{CStr, CString},
    sync::{new_mutex, Arc, Mutex},
};

const PAGE_BYTES: usize = bindings::PAGE_SIZE as usize;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

fn check_name(name: &CStr) -> Result {
    let bytes = name.as_bytes();
    if bytes.is_empty() || bytes == b"." || bytes == b".." || bytes.contains(&b'/') {
        return Err(EINVAL);
    }
    if bytes.len() > 255 {
        return Err(errno(-36));
    }
    Ok(())
}

/// Linux mutates the kobject through raw pointers; never borrow that storage
/// as an ordinary Rust reference after handing its initial reference to Linux.
#[repr(C)]
struct DirectoryStorage {
    object: UnsafeCell<bindings::kobject>,
}

const _: () = assert!(offset_of!(DirectoryStorage, object) == 0);

// SAFETY: Linux calls this once for the final kref on exactly the initialized
// allocation handed to kobject_init_and_add. The first field is at offset 0.
unsafe extern "C" fn release_directory(object: *mut bindings::kobject) {
    unsafe { drop(Box::from_raw(object.cast::<DirectoryStorage>())) };
}

struct DirectoryType(bindings::kobj_type);
// SAFETY: The descriptor is immutable and its pointers name resident code or
// Linux's permanent kobj_sysfs_ops. Owners must retire before module exit.
unsafe impl Sync for DirectoryType {}

static DIRECTORY_TYPE: DirectoryType = DirectoryType(bindings::kobj_type {
    release: Some(release_directory),
    sysfs_ops: ptr::addr_of!(bindings::kobj_sysfs_ops),
    default_groups: ptr::null_mut(),
    child_ns_type: None,
    namespace: None,
    get_ownership: None,
});

/// One Linux reference, shared through DirectoryState's Rust Arc. It remains
/// live until every directory/file/link owner releases the shared state.
struct ObjectRef(*mut bindings::kobject);

impl Drop for ObjectRef {
    fn drop(&mut self) {
        // SAFETY: Exactly one owned initial reference is released here.
        unsafe { bindings::kobject_put(self.0) };
    }
}

// SAFETY: DirectoryState serializes name operations; the pointer is stable
// through its owned Linux reference. Symlink targets use Linux's target lock.
unsafe impl Send for ObjectRef {}
// SAFETY: Sharing the pointer does not expose mutable Rust references.
unsafe impl Sync for ObjectRef {}

struct DirectoryState {
    object: ObjectRef,
    registered: Pin<Box<Mutex<bool>>>,
}

/// Uniquely owns a registered directory. Linux owns the final allocation
/// release; dependent files/links retain references and stable callback data.
pub(crate) struct Directory {
    state: Arc<DirectoryState>,
}

impl Directory {
    /// Create under another native directory, or at the sysfs root for an
    /// owning module's namespace. Production OS trees use `under_kobject`.
    pub(crate) fn new(parent: Option<&Self>, name: &CStr) -> Result<Self> {
        match parent {
            Some(parent) => {
                let registered = parent.state.registered.lock();
                if !*registered {
                    return Err(ENODEV);
                }
                // SAFETY: The shared state owns the kobject; its mutex excludes
                // all direct registration/removal operations for this parent.
                unsafe { Self::under_kobject(parent.state.object.0, name) }
            }
            // SAFETY: Null explicitly selects Linux's sysfs root.
            None => unsafe { Self::under_kobject(ptr::null_mut(), name) },
        }
    }

    /// # Safety
    /// A non-null parent must be the caller's live Linux kobject, with removal
    /// excluded throughout this call. It is never a user or guest address.
    /// All returned owners must be dropped before this module's code unloads.
    pub(crate) unsafe fn under_kobject(
        parent: *mut bindings::kobject,
        name: &CStr,
    ) -> Result<Self> {
        check_name(name)?;
        let registered = Box::pin_init(new_mutex!(true), GFP_KERNEL)?;
        // SAFETY: All-zero kobject storage is the input required by Linux's
        // initializer. UnsafeCell covers its subsequent Linux-owned mutation.
        let allocation = Box::new(
            DirectoryStorage {
                object: UnsafeCell::new(unsafe { MaybeUninit::zeroed().assume_init() }),
            },
            GFP_KERNEL,
        )?;
        let object = Box::into_raw(allocation).cast::<bindings::kobject>();
        // SAFETY: Linux takes the initial kref before add can fail. The exact
        // initialized allocation is reclaimed only by release_directory, on
        // either failure or the final put. The fixed format prevents names
        // from being interpreted as a variadic format string.
        let result = unsafe {
            bindings::kobject_init_and_add(
                object,
                &DIRECTORY_TYPE.0,
                parent,
                kernel::c_str!("%s").as_char_ptr(),
                name.as_char_ptr(),
            )
        };
        let reference = ObjectRef(object);
        kernel::error::to_result(result)?;
        let state = Arc::new(
            DirectoryState {
                object: reference,
                registered,
            },
            GFP_KERNEL,
        )?;
        Ok(Self { state })
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        let mut registered = self.state.registered.lock();
        // Linux sysfs_remove_dir explicitly requires callers to exclude other
        // operations on kobj->sd. Kobject references alone do not do that.
        *registered = false;
        // SAFETY: This mutex excludes direct file/link registration/removal
        // while Linux clears sd and drains the namespace. Descendants retain
        // the shared state, and skip subsequent name removals once inactive.
        unsafe { bindings::kobject_del(self.state.object.0) };
    }
}

/// Implementations own their state and synchronize concurrent callbacks.
/// Safe slices bound every operation; errors retain the usual Linux errno.
/// Callbacks must not remove their own file or an ancestor, nor acquire the
/// namespace lock that their own removal holds while draining callbacks.
pub(crate) trait AttributeOps: Send + Sync {
    fn show(&self, _buffer: &mut [u8]) -> Result<usize> {
        Err(EIO)
    }

    fn store(&self, _buffer: &[u8]) -> Result<usize> {
        Err(EIO)
    }
}

#[repr(C)]
struct AttributeStorage<T> {
    attribute: bindings::kobj_attribute,
    name: CString,
    operations: T,
}

// SAFETY: Linux supplies the exact live attribute pointer published by File
// and a PAGE_SIZE output allocation. sysfs removal drains this callback
// before freeing storage; only immutable Rust state is borrowed here.
unsafe extern "C" fn show<T: AttributeOps>(
    _object: *mut bindings::kobject,
    attribute: *mut bindings::kobj_attribute,
    buffer: *mut core::ffi::c_char,
) -> isize {
    if attribute.is_null() || buffer.is_null() {
        return EINVAL.to_errno() as isize;
    }
    // SAFETY: repr(C) puts the attribute first; Linux pins this allocation
    // for the callback. T requires shared callback access to be safe.
    let state = unsafe { &(*attribute.cast::<AttributeStorage<T>>()).operations };
    // SAFETY: The entire Linux output page is exclusively lent to show. Clear
    // it before exposing safe readable bytes, and reserve a trailing NUL.
    unsafe { ptr::write_bytes(buffer, 0, PAGE_BYTES) };
    let output = unsafe { core::slice::from_raw_parts_mut(buffer.cast(), PAGE_BYTES - 1) };
    match state.show(output) {
        Ok(bytes) if bytes < PAGE_BYTES => {
            // SAFETY: The validated count indexes the complete output page.
            unsafe { buffer.add(bytes).write(0) };
            bytes as isize
        }
        Ok(_) => errno(-75).to_errno() as isize,
        Err(error) => error.to_errno() as isize,
    }
}

// SAFETY: Linux pins the published attribute and lends `count` initialized
// input bytes. Removal waits for this invocation; T synchronizes shared state.
unsafe extern "C" fn store<T: AttributeOps>(
    _object: *mut bindings::kobject,
    attribute: *mut bindings::kobj_attribute,
    buffer: *const core::ffi::c_char,
    count: usize,
) -> isize {
    if attribute.is_null() || count > PAGE_BYTES || (count != 0 && buffer.is_null()) {
        return EINVAL.to_errno() as isize;
    }
    // SAFETY: Same stable first-field layout and callback lifetime as show.
    let state = unsafe { &(*attribute.cast::<AttributeStorage<T>>()).operations };
    let input = if count == 0 {
        &[]
    } else {
        // SAFETY: Linux lends these initialized bytes for this call only.
        unsafe { core::slice::from_raw_parts(buffer.cast(), count) }
    };
    match state.store(input) {
        Ok(bytes) if bytes <= count => bytes as isize,
        Ok(_) => errno(-75).to_errno() as isize,
        Err(error) => error.to_errno() as isize,
    }
}

/// Registered file plus the stable data Linux can use from its callbacks.
/// Failed publication never owns a name and therefore never removes it.
pub(crate) struct File<T: AttributeOps> {
    parent: Arc<DirectoryState>,
    storage: Box<AttributeStorage<T>>,
}

impl<T: AttributeOps> File<T> {
    pub(crate) fn new(parent: &Directory, name: &CStr, mode: u16, operations: T) -> Result<Self> {
        check_name(name)?;
        if mode & !0o777 != 0 {
            return Err(EINVAL);
        }
        assert_eq!(offset_of!(AttributeStorage<T>, attribute), 0);
        let name = CString::try_from(name)?;
        let mut attribute = bindings::kobj_attribute::default();
        attribute.attr.name = name.as_char_ptr();
        attribute.attr.mode = mode;
        attribute.show = Some(show::<T>);
        attribute.store = Some(store::<T>);
        let storage = Box::new(
            AttributeStorage {
                attribute,
                name,
                operations,
            },
            GFP_KERNEL,
        )?;
        let reference = parent.state.clone();
        let registered = reference.registered.lock();
        if !*registered {
            return Err(ENODEV);
        }
        // SAFETY: Stable initialized Box and name remain owned on success.
        // On failure Linux has published no callback; local storage may drop.
        kernel::error::to_result(unsafe {
            bindings::sysfs_create_file_ns(reference.object.0, &storage.attribute.attr, ptr::null())
        })?;
        drop(registered);
        Ok(Self {
            parent: reference,
            storage,
        })
    }
}

impl<T: AttributeOps> Drop for File<T> {
    fn drop(&mut self) {
        let registered = self.parent.registered.lock();
        if !*registered {
            return;
        }
        // SAFETY: The mutex excludes direct parent removal; the unique file
        // registration owns this exact parent/name. Linux
        // deactivates and drains callbacks before returning; only then may
        // fields drop. A previously removed parent has no replacement under
        // this old kobject, and the separate reference keeps it valid.
        unsafe {
            bindings::sysfs_remove_file_ns(
                self.parent.object.0,
                &self.storage.attribute.attr,
                ptr::null(),
            )
        };
    }
}

// SAFETY: The registered metadata is immutable; T is Send+Sync and removal
// drains all callbacks before freeing the Box. Linux owns namespace locking.
unsafe impl<T: AttributeOps> Send for File<T> {}
// SAFETY: Shared access exposes no raw mutation or deregistration operation.
unsafe impl<T: AttributeOps> Sync for File<T> {}

/// A registered symlink owns its name and keeps both endpoint objects alive.
pub(crate) struct Link {
    parent: Arc<DirectoryState>,
    _target: Arc<DirectoryState>,
    name: CString,
}

impl Link {
    pub(crate) fn new(parent: &Directory, target: &Directory, name: &CStr) -> Result<Self> {
        check_name(name)?;
        let name = CString::try_from(name)?;
        let parent = parent.state.clone();
        let target = target.state.clone();
        let registered = parent.registered.lock();
        if !*registered {
            return Err(ENODEV);
        }
        // SAFETY: The parent mutex excludes removal of its sd. Linux's
        // sysfs_symlink_target_lock protects the target's sd independently;
        // the target Arc retains the kobject. No second Rust lock is needed,
        // including same-directory or reciprocal links.
        kernel::error::to_result(unsafe {
            bindings::sysfs_create_link(parent.object.0, target.object.0, name.as_char_ptr())
        })?;
        drop(registered);
        Ok(Self {
            parent,
            _target: target,
            name,
        })
    }
}

impl Drop for Link {
    fn drop(&mut self) {
        let registered = self.parent.registered.lock();
        if !*registered {
            return;
        }
        // SAFETY: The parent mutex excludes directory removal. This owner
        // alone removes its registered name. Both endpoint
        // references and the name remain live until after Linux returns.
        unsafe { bindings::sysfs_remove_link(self.parent.object.0, self.name.as_char_ptr()) };
    }
}
