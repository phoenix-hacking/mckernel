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
    ptr,
};
use kernel::{
    bindings,
    prelude::*,
    str::{CStr, CString},
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

/// One Linux reference, without ownership of a registered name. Dependents
/// keep this separate reference even if their directory is removed first.
struct ObjectRef(*mut bindings::kobject);

impl ObjectRef {
    // SAFETY: The caller lends a live kobject through the get operation.
    unsafe fn acquire(object: *mut bindings::kobject) -> Self {
        // SAFETY: The live directory owner excludes its final put here.
        Self(unsafe { bindings::kobject_get(object) })
    }
}

impl Drop for ObjectRef {
    fn drop(&mut self) {
        // SAFETY: Exactly one owned get/initial reference is released here.
        unsafe { bindings::kobject_put(self.0) };
    }
}

// SAFETY: References are atomic in Linux; access is through Linux's own APIs.
unsafe impl Send for ObjectRef {}
// SAFETY: Sharing the pointer does not expose mutable Rust references.
unsafe impl Sync for ObjectRef {}

/// Uniquely owns a registered directory. Linux owns the final allocation
/// release; dependent files/links retain references and stable callback data.
pub(crate) struct Directory {
    object: ObjectRef,
}

impl Directory {
    /// Create under another native directory, or at the sysfs root for an
    /// owning module's namespace. Production OS trees use `under_kobject`.
    pub(crate) fn new(parent: Option<&Self>, name: &CStr) -> Result<Self> {
        let parent = parent.map_or(ptr::null_mut(), |parent| parent.object.0);
        // SAFETY: An optional directory borrow keeps its kobject live; null
        // explicitly denotes Linux's sysfs root.
        unsafe { Self::under_kobject(parent, name) }
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
        Ok(Self { object: reference })
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        // SAFETY: Only this owner can delete the registered directory. Linux
        // removes and drains descendant sysfs operations before returning.
        // ObjectRef then drops the initial reference, after namespace removal.
        unsafe { bindings::kobject_del(self.object.0) };
    }
}

/// Implementations own their state and synchronize concurrent callbacks.
/// Safe slices bound every operation; errors retain the usual Linux errno.
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
    parent: ObjectRef,
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
        // SAFETY: The parent borrow excludes its removal during this get and
        // publication. The separate reference also covers later file removal.
        let reference = unsafe { ObjectRef::acquire(parent.object.0) };
        // SAFETY: Stable initialized Box and name remain owned on success.
        // On failure Linux has published no callback; local storage may drop.
        kernel::error::to_result(unsafe {
            bindings::sysfs_create_file_ns(reference.0, &storage.attribute.attr, ptr::null())
        })?;
        Ok(Self {
            parent: reference,
            storage,
        })
    }
}

impl<T: AttributeOps> Drop for File<T> {
    fn drop(&mut self) {
        // SAFETY: The unique registration owns this exact parent/name. Linux
        // deactivates and drains callbacks before returning; only then may
        // fields drop. A previously removed parent has no replacement under
        // this old kobject, and the separate reference keeps it valid.
        unsafe {
            bindings::sysfs_remove_file_ns(self.parent.0, &self.storage.attribute.attr, ptr::null())
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
    parent: ObjectRef,
    _target: ObjectRef,
    name: CString,
}

impl Link {
    pub(crate) fn new(parent: &Directory, target: &Directory, name: &CStr) -> Result<Self> {
        check_name(name)?;
        let name = CString::try_from(name)?;
        // SAFETY: Both directory borrows exclude removal through registration.
        let parent = unsafe { ObjectRef::acquire(parent.object.0) };
        let target = unsafe { ObjectRef::acquire(target.object.0) };
        // SAFETY: Linux owns namespace locking and acquires its kernfs target
        // reference. Only success transfers registered-name ownership to Link.
        kernel::error::to_result(unsafe {
            bindings::sysfs_create_link(parent.0, target.0, name.as_char_ptr())
        })?;
        Ok(Self {
            parent,
            _target: target,
            name,
        })
    }
}

impl Drop for Link {
    fn drop(&mut self) {
        // SAFETY: This owner alone removes its registered name. Both endpoint
        // references and the name remain live until after Linux returns.
        unsafe { bindings::sysfs_remove_link(self.parent.0, self.name.as_char_ptr()) };
    }
}
