// Execute the complete production adapter with fault-injectable Linux calls.
// These mocked bindings test ownership and callbacks, not kernel ABI layout,
// allocator behavior, module loading, device-model concurrency or gate credit.
#![feature(used_with_arg)]
#![allow(dead_code, non_camel_case_types, non_upper_case_globals)]

extern crate self as kernel;

use std::{collections::BTreeMap, sync::{Mutex, atomic::{AtomicBool, AtomicI32, AtomicPtr, Ordering}}};

// SOURCE_MODULES

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Error(i32);
impl Error { pub fn to_errno(self) -> i32 { self.0 } }
pub type Result<T = ()> = std::result::Result<T, Error>;
pub const EINVAL: Error = Error(-22);
pub const ENOMEM: Error = Error(-12);
pub const ENODEV: Error = Error(-19);
pub const EBUSY: Error = Error(-16);
pub const EIO: Error = Error(-5);
pub const GFP_KERNEL: u32 = 1;
pub mod error {
    pub fn to_result(value: i32) -> crate::Result {
        if value < 0 { Err(crate::Error(value)) } else { Ok(()) }
    }
}
pub mod prelude {
    pub use crate::{Error, Result, EINVAL, ENOMEM, ENODEV, EBUSY, EIO, GFP_KERNEL, TestBox as Box, pr_info};
}
#[macro_export] macro_rules! pr_info { ($($arg:tt)*) => { { let _ = format_args!($($arg)*); } }; }
pub struct CStr(&'static [u8]);
impl CStr { pub const fn as_char_ptr(&self) -> *const i8 { self.0.as_ptr().cast() } }
#[macro_export] macro_rules! c_str { ($s:literal) => { &$crate::CStr(concat!($s, "\0").as_bytes()) }; }

pub struct TestBox<T>(std::boxed::Box<T>);
impl<T> TestBox<T> {
    pub fn new(value: T, _flags: u32) -> Result<Self> {
        if FAIL_BOX.swap(false, Ordering::SeqCst) { return Err(ENOMEM); }
        Ok(Self(std::boxed::Box::new(value)))
    }
    pub fn into_raw(value: Self) -> *mut T { std::boxed::Box::into_raw(value.0) }
    pub unsafe fn from_raw(value: *mut T) -> Self { Self(unsafe { std::boxed::Box::from_raw(value) }) }
    pub fn pin_init(value: T, flags: u32) -> Result<core::pin::Pin<Self>> where T: Unpin {
        if FAIL_PIN.swap(false, Ordering::SeqCst) { return Err(ENOMEM); }
        Ok(core::pin::Pin::new(Self::new(value, flags)?))
    }
}
impl<T> core::ops::Deref for TestBox<T> {
    type Target = T;
    fn deref(&self) -> &T { &self.0 }
}
impl<T> core::ops::DerefMut for TestBox<T> {
    fn deref_mut(&mut self) -> &mut T { &mut self.0 }
}
pub mod sync {
    pub struct Mutex<T>(std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        pub const fn new(value: T) -> Self { Self(std::sync::Mutex::new(value)) }
        pub fn lock(&self) -> std::sync::MutexGuard<'_, T> { self.0.lock().unwrap() }
    }
    pub use crate::new_mutex;
}
#[macro_export] macro_rules! new_mutex { ($value:expr) => { $crate::sync::Mutex::new($value) }; }

pub mod bindings {
    // CONFIG_LOCKDEP=n produces this empty C type in the exact Rocky bindings.
    // Typed foreign declarations that transitively expose it must fail linting.
    #[repr(C)] pub struct lockdep_map {}
    #[repr(C)] pub struct module { pub identity: u32, pub lockdep: lockdep_map }
    #[repr(C)] pub struct class { pub identity: u32 }
    #[repr(C)] pub struct device { pub identity: u32, pub lockdep: lockdep_map }
    #[repr(C)] pub struct inode { pub i_rdev: u32 }
    #[repr(C)] pub struct file { pub private_data: *mut core::ffi::c_void }
    #[repr(C)] pub struct file_operations {
        pub owner: *mut module,
        pub open: Option<unsafe extern "C" fn(*mut inode, *mut file) -> i32>,
        pub release: Option<unsafe extern "C" fn(*mut inode, *mut file) -> i32>,
        pub unlocked_ioctl: Option<unsafe extern "C" fn(*mut file, u32, u64) -> i64>,
        pub compat_ioctl: Option<unsafe extern "C" fn(*mut file, u32, u64) -> i64>,
    }
    // Exact Rocky 6.12 gfp_types.h enum positions and available Rust helpers.
    pub const GFP_KERNEL: u32 = 0x0cc0;
    pub const __GFP_ZERO: u32 = 0x0100;
    pub const ___GFP_NORETRY_BIT: u32 = 16;
    pub const ___GFP_NOWARN_BIT: u32 = 13;
    pub const ___GFP_COMP_BIT: u32 = 18;
}
pub struct ThisModule;
impl ThisModule { pub const fn as_ptr(&self) -> *mut bindings::module { core::ptr::addr_of!(MODULE).cast_mut() } }
pub static THIS_MODULE: ThisModule = ThisModule;
static MODULE: bindings::module = bindings::module { identity: 1, lockdep: bindings::lockdep_map {} };
static CLASS: bindings::class = bindings::class { identity: 1 };
static DEVICE: bindings::device = bindings::device { identity: 1, lockdep: bindings::lockdep_map {} };
#[repr(C, align(8))]
pub struct IhkExportSymbolRecord {
    license: [u8; 4], namespace: [u8; 16], padding: [u8; 4], symbol: *const u8,
}
unsafe impl Sync for IhkExportSymbolRecord {}

static TEST_LOCK: Mutex<()> = Mutex::new(());
static FOPS: AtomicPtr<bindings::file_operations> = AtomicPtr::new(core::ptr::null_mut());
static FAIL_REGISTER: AtomicBool = AtomicBool::new(false);
static FAIL_CLASS: AtomicBool = AtomicBool::new(false);
static FAIL_MODULE: AtomicBool = AtomicBool::new(false);
static FAIL_PAGES: AtomicBool = AtomicBool::new(false);
static FAIL_NODE: AtomicBool = AtomicBool::new(false);
static FAIL_BOX: AtomicBool = AtomicBool::new(false);
static FAIL_PIN: AtomicBool = AtomicBool::new(false);
static MODULE_REFS: AtomicI32 = AtomicI32::new(0);
static NODES: Mutex<BTreeMap<u32, u32>> = Mutex::new(BTreeMap::new());
static PAGES: Mutex<BTreeMap<usize, usize>> = Mutex::new(BTreeMap::new());
static CLASSES: AtomicI32 = AtomicI32::new(0);

#[no_mangle]
extern "C" fn __register_chrdev(major: u32, base: u32, count: u32, _name: *const i8,
    operations: *const bindings::file_operations) -> i32
{
    assert_eq!((major, base, count), (0, 0, 64));
    if FAIL_REGISTER.swap(false, Ordering::SeqCst) { return -12; }
    assert!(FOPS.swap(operations.cast_mut(), Ordering::SeqCst).is_null());
    assert_eq!(unsafe { (*operations).owner }, THIS_MODULE.as_ptr());
    240
}
#[no_mangle]
extern "C" fn __unregister_chrdev(major: u32, base: u32, count: u32, _name: *const i8) {
    assert_eq!((major, base, count), (240, 0, 64));
    assert!(!FOPS.swap(core::ptr::null_mut(), Ordering::SeqCst).is_null());
    assert!(NODES.lock().unwrap().is_empty());
}
#[no_mangle]
extern "C" fn class_create(_name: *const i8) -> *mut bindings::class {
    if FAIL_CLASS.swap(false, Ordering::SeqCst) { return (-12isize) as *mut _; }
    assert_eq!(CLASSES.fetch_add(1, Ordering::SeqCst), 0);
    core::ptr::addr_of!(CLASS).cast_mut()
}
#[no_mangle]
extern "C" fn class_destroy(class: *const bindings::class) {
    assert_eq!(class, core::ptr::addr_of!(CLASS));
    assert_eq!(CLASSES.fetch_sub(1, Ordering::SeqCst), 1);
    assert!(NODES.lock().unwrap().is_empty());
}
// Fixed x86_64 signature consumes the one %u argument of the production
// variadic call. No format interpretation or Linux publication is simulated.
#[no_mangle]
extern "C" fn device_create(class: *const bindings::class, _parent: *mut bindings::device,
    dev: u32, data: *mut core::ffi::c_void, format: *const i8, minor: u32) -> *mut bindings::device
{
    assert_eq!(class, core::ptr::addr_of!(CLASS));
    assert_eq!(unsafe { std::ffi::CStr::from_ptr(format) }.to_bytes(), b"mcos%u");
    assert_eq!(dev, (240 << 20) | minor);
    assert!(data.is_null());
    if FAIL_NODE.swap(false, Ordering::SeqCst) { return (-12isize) as *mut _; }
    assert!(NODES.lock().unwrap().insert(dev, minor).is_none());
    core::ptr::addr_of!(DEVICE).cast_mut()
}
#[no_mangle]
extern "C" fn device_destroy(class: *const bindings::class, dev: u32) {
    assert_eq!(class, core::ptr::addr_of!(CLASS));
    assert!(NODES.lock().unwrap().remove(&dev).is_some());
}
#[no_mangle]
extern "C" fn get_free_pages_noprof(flags: u32, order: u32) -> usize {
    assert_eq!(flags, 0x52dc0);
    assert_eq!(order, 10);
    if FAIL_PAGES.swap(false, Ordering::SeqCst) { return 0; }
    let size = 4096usize << order;
    let layout = std::alloc::Layout::from_size_align(size, 4096).unwrap();
    let address = unsafe { std::alloc::alloc_zeroed(layout) } as usize;
    assert_ne!(address, 0);
    assert!(PAGES.lock().unwrap().insert(address, size).is_none());
    address
}
#[no_mangle]
extern "C" fn free_pages(address: usize, order: u32) {
    assert_eq!(order, 10);
    let size = PAGES.lock().unwrap().remove(&address).unwrap();
    let buffer = unsafe { &*(address as *const abi::IhkKmsgBuffer) };
    assert_eq!(buffer.length, (4 << 20) - 4096);
    assert_eq!((buffer.lock, buffer.head, buffer.tail), (0, 0, 0));
    assert!(buffer.bytes.iter().all(|byte| *byte == 0));
    let layout = std::alloc::Layout::from_size_align(size, 4096).unwrap();
    unsafe { std::alloc::dealloc(address as *mut u8, layout) };
}
#[no_mangle]
extern "C" fn try_module_get(module: *mut bindings::module) -> bool {
    assert_eq!(module, THIS_MODULE.as_ptr());
    if FAIL_MODULE.swap(false, Ordering::SeqCst) { return false; }
    MODULE_REFS.fetch_add(1, Ordering::SeqCst);
    true
}
#[no_mangle]
extern "C" fn module_put(module: *mut bindings::module) {
    assert_eq!(module, THIS_MODULE.as_ptr());
    assert!(MODULE_REFS.fetch_sub(1, Ordering::SeqCst) > 0);
}

fn create(argument: u64) -> i64 {
    unsafe { os_runtime::ihk_os_create_unbooted_v1(0, THIS_MODULE.as_ptr().cast(), argument) }
}
fn destroy(minor: u64) -> i64 { os_runtime::ihk_os_destroy_unbooted_v1(0, minor) }
fn open(minor: u32) -> std::result::Result<bindings::file, i32> {
    let mut inode = bindings::inode { i_rdev: (240 << 20) | minor };
    let mut file = bindings::file { private_data: core::ptr::null_mut() };
    let result = unsafe { (*FOPS.load(Ordering::SeqCst)).open.unwrap()(&mut inode, &mut file) };
    if result == 0 { Ok(file) } else { assert!(file.private_data.is_null()); Err(result) }
}
fn status(file: &mut bindings::file, compat: bool, request: u32) -> i64 {
    let fops = unsafe { &*FOPS.load(Ordering::SeqCst) };
    unsafe { (if compat { fops.compat_ioctl } else { fops.unlocked_ioctl }).unwrap()(file, request, u64::MAX) }
}
fn close(mut file: bindings::file) {
    assert_eq!(unsafe { (*FOPS.load(Ordering::SeqCst)).release.unwrap()(core::ptr::null_mut(), &mut file) }, 0);
    assert!(file.private_data.is_null());
}
fn with_family(test: impl FnOnce()) {
    let _lock = TEST_LOCK.lock().unwrap();
    let family = os_runtime::OsDeviceFamily::register().unwrap();
    let token = device_registry::IHK_DEVICE_REGISTRY.attach_provider_token().unwrap();
    test();
    assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
    assert!(NODES.lock().unwrap().is_empty());
    assert!(PAGES.lock().unwrap().is_empty());
    device_registry::IHK_DEVICE_REGISTRY.retire_owned_provider_token(token);
    drop(family);
    assert!(FOPS.load(Ordering::SeqCst).is_null());
    assert_eq!(CLASSES.load(Ordering::SeqCst), 0);
}

#[test]
fn lifecycle_status_aliases_busy_close_destroy_and_reuse() {
    with_family(|| {
        assert_eq!(create(u64::MAX), 0); // SMP's frozen create ignores this scalar.
        let mut first = open(0).unwrap();
        let second = open(0).unwrap();
        for compat in [false, true] {
            assert_eq!(status(&mut first, compat, 0x112a03), 0);
            assert_eq!(status(&mut first, compat, 0x112a14), 0);
            assert_eq!(status(&mut first, compat, 0x112a01), -22);
            assert_eq!(status(&mut first, compat, u32::MAX), -22);
        }
        assert_eq!(destroy(0), -16);
        close(first);
        assert_eq!(destroy(0), -16);
        close(second);
        assert_eq!(destroy(0), 0);
        assert_eq!(open(0).err(), Some(-2));
        assert_eq!(destroy(0), -22);
        assert_eq!(create(0), 0);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn every_external_create_failure_unwinds_every_owner_and_reuses_minor() {
    with_family(|| {
        for (failure, expected) in [(&FAIL_MODULE, -16), (&FAIL_PAGES, -12), (&FAIL_BOX, -12), (&FAIL_NODE, -12)] {
            failure.store(true, Ordering::SeqCst);
            assert_eq!(create(0), expected);
            assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
            assert!(NODES.lock().unwrap().is_empty());
            assert!(PAGES.lock().unwrap().is_empty());
            assert_eq!(create(0), 0);
            assert_eq!(destroy(0), 0);
        }
    });
}

#[test]
fn failed_open_allocation_releases_os_lease() {
    with_family(|| {
        assert_eq!(create(0), 0);
        FAIL_BOX.store(true, Ordering::SeqCst);
        assert_eq!(open(0).err(), Some(-12));
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn capacity_64_first_free_reuse_and_overflow_arguments() {
    with_family(|| {
        for minor in 0..64 { assert_eq!(create(0), minor); }
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 64);
        assert_eq!(create(0), -12);
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 64);
        assert_eq!(destroy(64), -22);
        assert_eq!(destroy(u64::MAX), -22);
        assert_eq!(open(64).err(), Some(-22));
        assert_eq!(destroy(17), 0);
        assert_eq!(create(0), 17);
        for minor in (0..64).rev() { assert_eq!(destroy(minor), 0); }
    });
}

#[test]
fn concurrent_creation_has_unique_minors_and_balanced_destruction() {
    with_family(|| {
        let results: Vec<_> = (0..8).map(|_| std::thread::spawn(|| create(0))).collect();
        let mut minors: Vec<_> = results.into_iter().map(|thread| thread.join().unwrap()).collect();
        minors.sort_unstable();
        assert_eq!(minors, (0..8).collect::<Vec<_>>());
        let results: Vec<_> = minors.into_iter().map(|minor| std::thread::spawn(move || destroy(minor as u64))).collect();
        for result in results { assert_eq!(result.join().unwrap(), 0); }
    });
}

#[test]
fn concurrent_open_and_destroy_never_free_a_live_file() {
    with_family(|| {
        for _ in 0..40 {
            assert_eq!(create(0), 0);
            std::thread::scope(|scope| {
                let opener = scope.spawn(|| {
                    match open(0) {
                        Ok(mut file) => {
                            assert_eq!(status(&mut file, false, 0x112a03), 0);
                            close(file);
                        }
                        Err(error) => assert!(error == -2 || error == -16),
                    }
                });
                let result = destroy(0);
                assert!(result == 0 || result == -16);
                opener.join().unwrap();
                if result == -16 { assert_eq!(destroy(0), 0); }
            });
        }
    });
}

#[test]
fn provider_cannot_retire_with_live_os_and_invalid_provider_cannot_destroy() {
    with_family(|| {
        assert_eq!(create(0), 0);
        let provider = device_registry::IHK_DEVICE_REGISTRY.resolve_minor(0).unwrap();
        assert_eq!(device_registry::IHK_DEVICE_REGISTRY.snapshot(provider).unwrap().os_references, 1);
        assert_eq!(os_runtime::ihk_os_destroy_unbooted_v1(1, 0), -2);
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 1);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn null_provider_module_is_rejected_without_leaking_provider_lease() {
    with_family(|| {
        assert_eq!(unsafe { os_runtime::ihk_os_create_unbooted_v1(0, core::ptr::null_mut(), 0) }, -22);
        assert_eq!(create(0), 0);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn class_failure_unwinds_chrdev_and_family_can_register_again() {
    let _lock = TEST_LOCK.lock().unwrap();
    FAIL_CLASS.store(true, Ordering::SeqCst);
    assert_eq!(os_runtime::OsDeviceFamily::register().err(), Some(ENOMEM));
    assert!(FOPS.load(Ordering::SeqCst).is_null());
    let family = os_runtime::OsDeviceFamily::register().unwrap();
    drop(family);
}

#[test]
fn chrdev_failure_never_creates_class_or_publishes_family() {
    let _lock = TEST_LOCK.lock().unwrap();
    FAIL_REGISTER.store(true, Ordering::SeqCst);
    assert_eq!(os_runtime::OsDeviceFamily::register().err(), Some(ENOMEM));
    assert!(FOPS.load(Ordering::SeqCst).is_null());
    assert_eq!(CLASSES.load(Ordering::SeqCst), 0);
    assert_eq!(create(0), -19);
}

static BACKEND_CALLS: Mutex<Vec<(u32, u64, u32, u64, u32)>> = Mutex::new(Vec::new());
static BACKEND_RELEASES: Mutex<Vec<(u32, u64)>> = Mutex::new(Vec::new());
static BACKEND_RELEASE_STATUS: AtomicI32 = AtomicI32::new(0);
static BACKEND_ACTIVE: [AtomicI32; 64] = [const { AtomicI32::new(0) }; 64];

unsafe extern "C" fn backend_ioctl(slot: u32, generation: u64, command: u32,
    address: u64, compat: u32) -> i64
{
    assert!(slot < 64 && generation > 0 && compat <= 1);
    assert!(MODULE_REFS.load(Ordering::SeqCst) > 0);
    assert!(NODES.lock().unwrap().contains_key(&((240 << 20) | slot)));
    assert_eq!(BACKEND_ACTIVE[slot as usize].fetch_add(1, Ordering::SeqCst), 0);
    std::thread::sleep(std::time::Duration::from_millis(2));
    BACKEND_CALLS.lock().unwrap().push((slot, generation, command, address, compat));
    assert_eq!(BACKEND_ACTIVE[slot as usize].fetch_sub(1, Ordering::SeqCst), 1);
    if command == 0x112a25 { -14 } else if command == u32::MAX { -4096 } else { 73 }
}

unsafe extern "C" fn backend_release(slot: u32, generation: u64) -> i32 {
    assert!(MODULE_REFS.load(Ordering::SeqCst) > 0);
    assert!(NODES.lock().unwrap().contains_key(&((240 << 20) | slot)));
    assert!(!PAGES.lock().unwrap().is_empty());
    assert_eq!(BACKEND_ACTIVE[slot as usize].load(Ordering::SeqCst), 0);
    BACKEND_RELEASES.lock().unwrap().push((slot, generation));
    BACKEND_RELEASE_STATUS.load(Ordering::SeqCst)
}

fn create_backend() -> i64 {
    unsafe {
        os_runtime::ihk_os_create_unbooted_v2(0, THIS_MODULE.as_ptr().cast(),
            u64::MAX, 1, Some(backend_ioctl), Some(backend_release))
    }
}

fn reset_backend() {
    BACKEND_CALLS.lock().unwrap().clear();
    BACKEND_RELEASES.lock().unwrap().clear();
    BACKEND_RELEASE_STATUS.store(0, Ordering::SeqCst);
}

#[test]
fn versioned_backend_validates_callbacks_before_any_publication() {
    with_family(|| {
        reset_backend();
        for (version, ioctl, release) in [
            (0, true, true), (2, true, true), (1, false, true),
            (1, true, false), (1, false, false),
        ] {
            assert_eq!(unsafe {
                os_runtime::ihk_os_create_unbooted_v2(0, THIS_MODULE.as_ptr().cast(),
                    0, version, if ioctl { Some(backend_ioctl) } else { None },
                    if release { Some(backend_release) } else { None })
            }, -22);
            assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
            assert!(NODES.lock().unwrap().is_empty());
            assert!(PAGES.lock().unwrap().is_empty());
        }
        for failure in [&FAIL_PIN, &FAIL_PAGES, &FAIL_BOX, &FAIL_NODE] {
            failure.store(true, Ordering::SeqCst);
            assert_eq!(create_backend(), -12);
            assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
            assert!(NODES.lock().unwrap().is_empty());
            assert!(PAGES.lock().unwrap().is_empty());
            assert!(BACKEND_RELEASES.lock().unwrap().is_empty());
        }
        assert_eq!(create_backend(), 0);
        assert_eq!(destroy(0), 0);
        assert_eq!(BACKEND_RELEASES.lock().unwrap().len(), 1);
    });
}

#[test]
fn backend_uses_checked_generation_and_exact_native_compat_arguments() {
    with_family(|| {
        reset_backend();
        assert_eq!(create_backend(), 0);
        let mut file = open(0).unwrap();
        for compat in [false, true] {
            assert_eq!(status(&mut file, compat, 0x112a03), 0);
            assert_eq!(status(&mut file, compat, 0x112a14), 0);
        }
        assert!(BACKEND_CALLS.lock().unwrap().is_empty());
        assert_eq!(status(&mut file, false, 0x112a22), 73);
        assert_eq!(status(&mut file, true, 0x112a24), 73);
        assert_eq!(status(&mut file, false, 0x112a25), -14);
        assert_eq!(status(&mut file, false, u32::MAX), -5);
        let calls = BACKEND_CALLS.lock().unwrap().clone();
        assert_eq!(calls.len(), 4);
        let generation = calls[0].1;
        assert_eq!(calls[0], (0, generation, 0x112a22, u64::MAX, 0));
        assert_eq!(calls[1], (0, generation, 0x112a24, u32::MAX as u64, 1));
        assert_eq!(destroy(0), -16);
        assert!(BACKEND_RELEASES.lock().unwrap().is_empty());
        close(file);
        assert_eq!(destroy(0), 0);
        assert_eq!(*BACKEND_RELEASES.lock().unwrap(), [(0, generation)]);
    });
}

#[test]
fn backend_cleanup_failure_keeps_instance_and_all_owners_live() {
    with_family(|| {
        reset_backend();
        assert_eq!(create_backend(), 0);
        for result in [-16, 1, -5] {
            BACKEND_RELEASE_STATUS.store(result, Ordering::SeqCst);
            assert_eq!(destroy(0), if result < 0 { result as i64 } else { -5 });
            assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 1);
            assert_eq!(NODES.lock().unwrap().len(), 1);
            assert_eq!(PAGES.lock().unwrap().len(), 1);
            let mut file = open(0).unwrap();
            assert_eq!(status(&mut file, false, 0x112a22), 73);
            close(file);
        }
        let calls = BACKEND_CALLS.lock().unwrap().clone();
        assert!(calls.iter().all(|call| call.1 == calls[0].1));
        BACKEND_RELEASE_STATUS.store(0, Ordering::SeqCst);
        assert_eq!(destroy(0), 0);
        let releases = BACKEND_RELEASES.lock().unwrap().clone();
        assert_eq!(releases.len(), 4);
        assert!(releases.iter().all(|release| *release == (0, calls[0].1)));
    });
}

#[test]
fn backend_minor_reuse_always_receives_new_generation() {
    with_family(|| {
        reset_backend();
        for _ in 0..3 {
            assert_eq!(create_backend(), 0);
            let mut file = open(0).unwrap();
            assert_eq!(status(&mut file, false, 0x112a22), 73);
            close(file);
            assert_eq!(destroy(0), 0);
        }
        let calls = BACKEND_CALLS.lock().unwrap().clone();
        let releases = BACKEND_RELEASES.lock().unwrap().clone();
        for index in 0..3 {
            assert_eq!(releases[index], (0, calls[index].1));
            if index > 0 { assert!(calls[index].1 > calls[index - 1].1); }
        }
    });
}

#[test]
fn backend_serializes_operations_across_concurrent_open_files() {
    with_family(|| {
        reset_backend();
        assert_eq!(create_backend(), 0);
        let threads: Vec<_> = (0..8).map(|_| std::thread::spawn(|| {
            let mut file = open(0).unwrap();
            for _ in 0..4 { assert_eq!(status(&mut file, false, 0x112a22), 73); }
            close(file);
        })).collect();
        for thread in threads { thread.join().unwrap(); }
        assert_eq!(BACKEND_CALLS.lock().unwrap().len(), 32);
        assert_eq!(destroy(0), 0);
        assert_eq!(BACKEND_RELEASES.lock().unwrap().len(), 1);
    });
}

#[test]
fn exclusive_unbooted_cleanup_guard_rejects_loading_and_preserves_instance() {
    let registry = os_registry::OsRegistry::new();
    let dispatcher = ihk_ioctl::IhkIoctlDispatcher::new(&registry);
    let create = dispatcher.prepare_device(0x112900, 0).unwrap();
    assert_eq!(create.require_unbooted_destroy(), Err(ihk_ioctl::IoctlError::InvalidArgument));
    let handle = create.handle();
    create.commit_after_external_success().unwrap();
    registry.transition(handle, os_registry::OsStatus::Loading).unwrap();
    {
        let destroy = dispatcher.prepare_device(0x112901, handle.minor() as u64).unwrap();
        assert_eq!(destroy.require_unbooted_destroy(), Err(ihk_ioctl::IoctlError::Busy));
        assert_eq!(registry.acquire(handle).err(), Some(os_registry::RegistryError::Busy));
    }
    assert_eq!(registry.snapshot(handle).unwrap().status, os_registry::OsStatus::Loading);
    registry.transition(handle, os_registry::OsStatus::NotBooted).unwrap();
    let destroy = dispatcher.prepare_device(0x112901, handle.minor() as u64).unwrap();
    destroy.require_unbooted_destroy().unwrap();
    destroy.commit_after_external_success().unwrap();
    assert_eq!(registry.live_count(), 0);
}
