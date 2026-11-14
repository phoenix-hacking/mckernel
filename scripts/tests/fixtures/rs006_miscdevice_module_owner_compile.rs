// SPDX-License-Identifier: GPL-2.0
//
// Compile-shape fixture for the unintegrated RS-006 miscdevice follow-up.
// This is a userspace model, not evidence of a kernel build or runtime result.

#![allow(dead_code)]

use std::marker::{PhantomData, PhantomPinned};
use std::mem::size_of;
use std::pin::Pin;
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Debug)]
struct ThisModule(usize);

impl ThisModule {
    const fn as_ptr(&self) -> usize {
        self.0
    }
}

static THIS_MODULE: ThisModule = ThisModule(0x5253_3030_36);
static OTHER_MODULE: ThisModule = ThisModule(0xBAD0);

type CompatIoctl = fn(u32, usize) -> isize;

struct FileOperations {
    owner: usize,
    compat_ioctl: Option<CompatIoctl>,
}

trait MiscDevice {
    const MODULE: &'static ThisModule;
    const HAS_COMPAT_IOCTL: bool;

    fn compat_ioctl(_cmd: u32, _arg: usize) -> isize {
        panic!("compat ioctl was not implemented")
    }
}

fn fops_compat_ioctl<T: MiscDevice>(cmd: u32, arg: usize) -> isize {
    T::compat_ioctl(cmd, arg)
}

const fn maybe_fn(check: bool, callback: CompatIoctl) -> Option<CompatIoctl> {
    if check {
        Some(callback)
    } else {
        None
    }
}

struct VtableHelper<T: MiscDevice> {
    _t: PhantomData<T>,
}

impl<T: MiscDevice> VtableHelper<T> {
    const VTABLE: FileOperations = FileOperations {
        owner: T::MODULE.as_ptr(),
        compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),
    };
}

fn create_vtable<T: MiscDevice>() -> &'static FileOperations {
    &VtableHelper::<T>::VTABLE
}

struct ExplicitCompatDevice;

impl MiscDevice for ExplicitCompatDevice {
    const MODULE: &'static ThisModule = &THIS_MODULE;
    const HAS_COMPAT_IOCTL: bool = true;

    fn compat_ioctl(cmd: u32, arg: usize) -> isize {
        (cmd as isize) + (arg as isize)
    }
}

struct NoCompatDevice;

impl MiscDevice for NoCompatDevice {
    const MODULE: &'static ThisModule = &THIS_MODULE;
    const HAS_COMPAT_IOCTL: bool = false;
}

static DROP_STAGE: AtomicUsize = AtomicUsize::new(0);

struct RawMiscDevice {
    fops: &'static FileOperations,
    registered: bool,
    _pin: PhantomPinned,
}

impl Drop for RawMiscDevice {
    fn drop(&mut self) {
        assert!(!self.registered, "pinned storage freed before deregistration");
        assert_eq!(DROP_STAGE.load(Ordering::SeqCst), 1);
        DROP_STAGE.store(2, Ordering::SeqCst);
    }
}

struct MiscDeviceRegistration<T: MiscDevice> {
    inner: Pin<Box<RawMiscDevice>>,
    _t: PhantomData<T>,
}

impl<T: MiscDevice> MiscDeviceRegistration<T> {
    fn register() -> Self {
        Self {
            inner: Box::pin(RawMiscDevice {
                fops: create_vtable::<T>(),
                registered: true,
                _pin: PhantomPinned,
            }),
            _t: PhantomData,
        }
    }
}

impl<T: MiscDevice> Drop for MiscDeviceRegistration<T> {
    fn drop(&mut self) {
        assert_eq!(DROP_STAGE.load(Ordering::SeqCst), 0);
        // SAFETY: deregistration changes data in place and does not move the
        // pinned allocation. The allocation is released only after this drop
        // method returns.
        let raw = unsafe { self.inner.as_mut().get_unchecked_mut() };
        assert!(raw.registered);
        raw.registered = false;
        DROP_STAGE.store(1, Ordering::SeqCst);
    }
}

fn main() {
    let fops = create_vtable::<ExplicitCompatDevice>();
    assert_eq!(fops.owner, THIS_MODULE.as_ptr());
    assert_ne!(fops.owner, OTHER_MODULE.as_ptr());
    assert_eq!(fops.compat_ioctl.expect("explicit compat callback")(7, 11), 18);
    assert!(create_vtable::<NoCompatDevice>().compat_ioctl.is_none());

    // The registration contains a pointer to a static vtable, not an embedded
    // per-registration file_operations object whose lifetime ends on drop.
    assert_eq!(
        size_of::<MiscDeviceRegistration<ExplicitCompatDevice>>(),
        size_of::<Pin<Box<RawMiscDevice>>>()
    );
    assert!(std::ptr::eq(fops, create_vtable::<ExplicitCompatDevice>()));

    let registration = MiscDeviceRegistration::<ExplicitCompatDevice>::register();
    assert!(std::ptr::eq(registration.inner.as_ref().fops, fops));
    drop(registration);
    assert_eq!(DROP_STAGE.load(Ordering::SeqCst), 2);
}
