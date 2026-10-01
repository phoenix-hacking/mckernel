// Execute the complete production adapter with fault-injectable Linux calls.
// These mocked bindings test ownership and callbacks, not kernel ABI layout,
// allocator behavior, module loading, device-model concurrency or gate credit.
#![feature(used_with_arg)]
#![allow(dead_code, non_camel_case_types, non_upper_case_globals)]

extern crate self as kernel;

use std::{
    collections::BTreeMap,
    sync::{
        atomic::{AtomicBool, AtomicI32, AtomicI64, AtomicPtr, Ordering},
        Mutex,
    },
};

// SOURCE_MODULES

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Error(i32);
impl Error {
    pub fn to_errno(self) -> i32 {
        self.0
    }
}
pub type Result<T = ()> = std::result::Result<T, Error>;
pub const EINVAL: Error = Error(-22);
pub const ENOMEM: Error = Error(-12);
pub const ENODEV: Error = Error(-19);
pub const EBUSY: Error = Error(-16);
pub const EIO: Error = Error(-5);
pub const GFP_KERNEL: u32 = 1;
pub mod error {
    pub fn to_result(value: i32) -> crate::Result {
        if value < 0 {
            Err(crate::Error(value))
        } else {
            Ok(())
        }
    }
}
pub mod prelude {
    pub use crate::{
        pr_info, Error, Result, TestBox as Box, EBUSY, EINVAL, EIO, ENODEV, ENOMEM, GFP_KERNEL,
    };
}
#[macro_export]
macro_rules! pr_info { ($($arg:tt)*) => { { let _ = format_args!($($arg)*); } }; }
pub struct CStr(&'static [u8]);
impl CStr {
    pub const fn as_char_ptr(&self) -> *const i8 {
        self.0.as_ptr().cast()
    }
}
#[macro_export]
macro_rules! c_str {
    ($s:literal) => {
        &$crate::CStr(concat!($s, "\0").as_bytes())
    };
}

pub struct TestBox<T>(std::boxed::Box<T>);
impl<T> TestBox<T> {
    pub fn new(value: T, _flags: u32) -> Result<Self> {
        if FAIL_BOX.swap(false, Ordering::SeqCst) {
            return Err(ENOMEM);
        }
        Ok(Self(std::boxed::Box::new(value)))
    }
    pub fn into_raw(value: Self) -> *mut T {
        std::boxed::Box::into_raw(value.0)
    }
    pub unsafe fn from_raw(value: *mut T) -> Self {
        Self(unsafe { std::boxed::Box::from_raw(value) })
    }
    pub fn pin_init(value: T, flags: u32) -> Result<core::pin::Pin<Self>>
    where
        T: Unpin,
    {
        if FAIL_PIN.swap(false, Ordering::SeqCst) {
            return Err(ENOMEM);
        }
        Ok(core::pin::Pin::new(Self::new(value, flags)?))
    }
}
impl<T> core::ops::Deref for TestBox<T> {
    type Target = T;
    fn deref(&self) -> &T {
        &self.0
    }
}
impl<T> core::ops::DerefMut for TestBox<T> {
    fn deref_mut(&mut self) -> &mut T {
        &mut self.0
    }
}
pub mod sync {
    pub struct Mutex<T>(std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        pub const fn new(value: T) -> Self {
            Self(std::sync::Mutex::new(value))
        }
        pub fn lock(&self) -> std::sync::MutexGuard<'_, T> {
            self.0.lock().unwrap()
        }
    }
    pub use crate::new_mutex;
}
#[macro_export]
macro_rules! new_mutex {
    ($value:expr) => {
        $crate::sync::Mutex::new($value)
    };
}

pub mod bindings {
    // The mock allocation address is also its physical identity. Native Linux
    // uses its actual initialized direct-map base through this same read.
    pub static mut page_offset_base: u64 = 0;
    // CONFIG_LOCKDEP=n produces this empty C type in the exact Rocky bindings.
    // Typed foreign declarations that transitively expose it must fail linting.
    #[repr(C)]
    pub struct lockdep_map {}
    #[repr(C)]
    pub struct module {
        pub identity: u32,
        pub lockdep: lockdep_map,
    }
    #[repr(C)]
    pub struct class {
        pub identity: u32,
    }
    #[repr(C)]
    pub struct kobject {}
    #[repr(C)]
    pub struct device {
        pub identity: u32,
        pub lockdep: lockdep_map,
        pub kobj: kobject,
    }
    #[repr(C)]
    pub struct inode {
        pub i_rdev: u32,
    }
    #[repr(C)]
    pub struct file {
        pub private_data: *mut core::ffi::c_void,
    }
    #[repr(C)]
    pub struct file_operations {
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
impl ThisModule {
    pub const fn as_ptr(&self) -> *mut bindings::module {
        core::ptr::addr_of!(MODULE).cast_mut()
    }
}
pub static THIS_MODULE: ThisModule = ThisModule;
static MODULE: bindings::module = bindings::module {
    identity: 1,
    lockdep: bindings::lockdep_map {},
};
static CLASS: bindings::class = bindings::class { identity: 1 };
static DEVICE: bindings::device = bindings::device {
    identity: 1,
    lockdep: bindings::lockdep_map {},
    kobj: bindings::kobject {},
};
#[repr(C, align(8))]
pub struct IhkExportSymbolRecord {
    license: [u8; 4],
    namespace: [u8; 16],
    padding: [u8; 4],
    symbol: *const u8,
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
extern "C" fn __register_chrdev(
    major: u32,
    base: u32,
    count: u32,
    _name: *const i8,
    operations: *const bindings::file_operations,
) -> i32 {
    assert_eq!((major, base, count), (0, 0, 64));
    if FAIL_REGISTER.swap(false, Ordering::SeqCst) {
        return -12;
    }
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
    if FAIL_CLASS.swap(false, Ordering::SeqCst) {
        return (-12isize) as *mut _;
    }
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
extern "C" fn device_create(
    class: *const bindings::class,
    _parent: *mut bindings::device,
    dev: u32,
    data: *mut core::ffi::c_void,
    format: *const i8,
    minor: u32,
) -> *mut bindings::device {
    assert_eq!(class, core::ptr::addr_of!(CLASS));
    assert_eq!(
        unsafe { std::ffi::CStr::from_ptr(format) }.to_bytes(),
        b"mcos%u"
    );
    assert_eq!(dev, (240 << 20) | minor);
    assert!(data.is_null());
    if FAIL_NODE.swap(false, Ordering::SeqCst) {
        return (-12isize) as *mut _;
    }
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
    if FAIL_PAGES.swap(false, Ordering::SeqCst) {
        return 0;
    }
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
    if FAIL_MODULE.swap(false, Ordering::SeqCst) {
        return false;
    }
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
fn destroy(minor: u64) -> i64 {
    os_runtime::ihk_os_destroy_unbooted_v1(0, minor)
}
fn open(minor: u32) -> std::result::Result<bindings::file, i32> {
    let mut inode = bindings::inode {
        i_rdev: (240 << 20) | minor,
    };
    let mut file = bindings::file {
        private_data: core::ptr::null_mut(),
    };
    let result = unsafe { (*FOPS.load(Ordering::SeqCst)).open.unwrap()(&mut inode, &mut file) };
    if result == 0 {
        Ok(file)
    } else {
        assert!(file.private_data.is_null());
        Err(result)
    }
}
fn status(file: &mut bindings::file, compat: bool, request: u32) -> i64 {
    let fops = unsafe { &*FOPS.load(Ordering::SeqCst) };
    unsafe {
        (if compat {
            fops.compat_ioctl
        } else {
            fops.unlocked_ioctl
        })
        .unwrap()(file, request, u64::MAX)
    }
}
fn close(mut file: bindings::file) {
    assert_eq!(
        unsafe {
            (*FOPS.load(Ordering::SeqCst)).release.unwrap()(core::ptr::null_mut(), &mut file)
        },
        0
    );
    assert!(file.private_data.is_null());
}
fn with_family(test: impl FnOnce()) {
    let _lock = TEST_LOCK.lock().unwrap();
    let family = os_runtime::OsDeviceFamily::register().unwrap();
    let token = device_registry::IHK_DEVICE_REGISTRY
        .attach_provider_token()
        .unwrap();
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
        for (failure, expected) in [
            (&FAIL_MODULE, -16),
            (&FAIL_PAGES, -12),
            (&FAIL_BOX, -12),
            (&FAIL_NODE, -12),
        ] {
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
        for minor in 0..64 {
            assert_eq!(create(0), minor);
        }
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 64);
        assert_eq!(create(0), -12);
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 64);
        assert_eq!(destroy(64), -22);
        assert_eq!(destroy(u64::MAX), -22);
        assert_eq!(open(64).err(), Some(-22));
        assert_eq!(destroy(17), 0);
        assert_eq!(create(0), 17);
        for minor in (0..64).rev() {
            assert_eq!(destroy(minor), 0);
        }
    });
}

#[test]
fn concurrent_creation_has_unique_minors_and_balanced_destruction() {
    with_family(|| {
        let results: Vec<_> = (0..8).map(|_| std::thread::spawn(|| create(0))).collect();
        let mut minors: Vec<_> = results
            .into_iter()
            .map(|thread| thread.join().unwrap())
            .collect();
        minors.sort_unstable();
        assert_eq!(minors, (0..8).collect::<Vec<_>>());
        let results: Vec<_> = minors
            .into_iter()
            .map(|minor| std::thread::spawn(move || destroy(minor as u64)))
            .collect();
        for result in results {
            assert_eq!(result.join().unwrap(), 0);
        }
    });
}

#[test]
fn concurrent_open_and_destroy_never_free_a_live_file() {
    with_family(|| {
        for _ in 0..40 {
            assert_eq!(create(0), 0);
            std::thread::scope(|scope| {
                let opener = scope.spawn(|| match open(0) {
                    Ok(mut file) => {
                        assert_eq!(status(&mut file, false, 0x112a03), 0);
                        close(file);
                    }
                    Err(error) => assert!(error == -2 || error == -16),
                });
                let result = destroy(0);
                assert!(result == 0 || result == -16);
                opener.join().unwrap();
                if result == -16 {
                    assert_eq!(destroy(0), 0);
                }
            });
        }
    });
}

#[test]
fn provider_cannot_retire_with_live_os_and_invalid_provider_cannot_destroy() {
    with_family(|| {
        assert_eq!(create(0), 0);
        let provider = device_registry::IHK_DEVICE_REGISTRY
            .resolve_minor(0)
            .unwrap();
        assert_eq!(
            device_registry::IHK_DEVICE_REGISTRY
                .snapshot(provider)
                .unwrap()
                .os_references,
            1
        );
        assert_eq!(os_runtime::ihk_os_destroy_unbooted_v1(1, 0), -2);
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 1);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn null_provider_module_is_rejected_without_leaking_provider_lease() {
    with_family(|| {
        assert_eq!(
            unsafe { os_runtime::ihk_os_create_unbooted_v1(0, core::ptr::null_mut(), 0) },
            -22
        );
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
static BACKEND_LOAD_STATUS: AtomicI32 = AtomicI32::new(0);
static BACKEND_ACTIVE: [AtomicI32; 64] = [const { AtomicI32::new(0) }; 64];

unsafe extern "C" fn backend_ioctl(
    slot: u32,
    generation: u64,
    command: u32,
    address: u64,
    compat: u32,
) -> i64 {
    assert!(slot < 64 && generation > 0 && compat <= 1);
    assert!(MODULE_REFS.load(Ordering::SeqCst) > 0);
    assert!(NODES.lock().unwrap().contains_key(&((240 << 20) | slot)));
    assert_eq!(
        BACKEND_ACTIVE[slot as usize].fetch_add(1, Ordering::SeqCst),
        0
    );
    std::thread::sleep(std::time::Duration::from_millis(2));
    BACKEND_CALLS
        .lock()
        .unwrap()
        .push((slot, generation, command, address, compat));
    assert_eq!(
        BACKEND_ACTIVE[slot as usize].fetch_sub(1, Ordering::SeqCst),
        1
    );
    if command == abi::IHK_OS_LOAD {
        let mut observer = open(slot).unwrap();
        assert_eq!(status(&mut observer, false, abi::IHK_OS_STATUS), 1);
        assert_eq!(status(&mut observer, true, abi::IHK_OS_QUERY_STATUS), 1);
        close(observer);
        return BACKEND_LOAD_STATUS.load(Ordering::SeqCst) as i64;
    }
    if command == 0x112a25 {
        -14
    } else if command == u32::MAX {
        -4096
    } else {
        73
    }
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
        os_runtime::ihk_os_create_unbooted_v2(
            0,
            THIS_MODULE.as_ptr().cast(),
            u64::MAX,
            1,
            Some(backend_ioctl),
            Some(backend_release),
        )
    }
}

fn reset_backend() {
    BACKEND_CALLS.lock().unwrap().clear();
    BACKEND_RELEASES.lock().unwrap().clear();
    BACKEND_RELEASE_STATUS.store(0, Ordering::SeqCst);
    BACKEND_LOAD_STATUS.store(0, Ordering::SeqCst);
}

static BOOT_PREPARE_STATUS: AtomicI32 = AtomicI32::new(0);
static BOOT_START_STATUS: AtomicI32 = AtomicI32::new(0);
static BOOT_GENERATION: AtomicI64 = AtomicI64::new(0);
static BOOT_START_CALLS: AtomicI32 = AtomicI32::new(0);
static SHUTDOWN_STATUS: AtomicI32 = AtomicI32::new(0);
static SHUTDOWN_V6_STATUS: AtomicI64 = AtomicI64::new(0);
static SHUTDOWN_CALLS: AtomicI32 = AtomicI32::new(0);
static SHUTDOWN_IDENTITY: Mutex<Vec<(u32, u64)>> = Mutex::new(Vec::new());
static APPLICATION_SUCCEED: AtomicBool = AtomicBool::new(false);
static APPLICATION_CLOSES: AtomicI32 = AtomicI32::new(0);
static APPLICATION_INVOKES: AtomicI32 = AtomicI32::new(0);
static APPLICATION_CLOSE_QUERY: AtomicI64 = AtomicI64::new(0);
static APPLICATION_CLOSE_GENERATION: AtomicI64 = AtomicI64::new(0);
static CHECK_CLOSE_OWNERS: AtomicBool = AtomicBool::new(false);
static APPLICATION_EVENTS: Mutex<Vec<u8>> = Mutex::new(Vec::new());
static APPLICATION_CONTEXT: u8 = 7;
static SERVICE_OPENS: AtomicI32 = AtomicI32::new(0);
static SERVICE_CLOSES: AtomicI32 = AtomicI32::new(0);
static SERVICE_COMMAND: AtomicI32 = AtomicI32::new(0);
static SERVICE_ARGUMENT: AtomicI64 = AtomicI64::new(0);
static SERVICE_COMPAT: AtomicI32 = AtomicI32::new(-1);
static SERVICE_CONTEXT: u8 = 9;

unsafe extern "C" fn service_open(
    slot: u32,
    generation: u64,
    output: *mut *mut core::ffi::c_void,
) -> i32 {
    assert_eq!(slot, 0);
    assert_eq!(generation, BOOT_GENERATION.load(Ordering::SeqCst) as u64);
    SERVICE_OPENS.fetch_add(1, Ordering::SeqCst);
    unsafe { output.write(core::ptr::addr_of!(SERVICE_CONTEXT).cast_mut().cast()) };
    0
}
unsafe extern "C" fn service_ioctl(
    _context: *mut core::ffi::c_void,
    command: u32,
    argument: u64,
    compat: u32,
) -> i64 {
    assert_eq!(command, abi::MCEXEC_UP_PREPARE_IMAGE);
    SERVICE_COMMAND.store(command as i32, Ordering::SeqCst);
    SERVICE_ARGUMENT.store(argument as i64, Ordering::SeqCst);
    SERVICE_COMPAT.store(compat as i32, Ordering::SeqCst);
    0
}
unsafe extern "C" fn service_close(_context: *mut core::ffi::c_void) {
    SERVICE_CLOSES.fetch_add(1, Ordering::SeqCst);
}

unsafe extern "C" fn application_open(
    _slot: u32,
    _generation: u64,
    _pid: i32,
    output: *mut *mut core::ffi::c_void,
) -> i32 {
    if APPLICATION_SUCCEED.load(Ordering::SeqCst) {
        unsafe { output.write(core::ptr::addr_of!(APPLICATION_CONTEXT).cast_mut().cast()) };
        0
    } else {
        unsafe { output.write(core::ptr::null_mut()) };
        -22
    }
}
unsafe extern "C" fn application_invoke(
    _context: *mut core::ffi::c_void,
    _command: u32,
    _buffer: *mut u8,
    _length: usize,
) -> i64 {
    APPLICATION_INVOKES.fetch_add(1, Ordering::SeqCst);
    17
}
unsafe extern "C" fn application_close(_context: *mut core::ffi::c_void) {
    if CHECK_CLOSE_OWNERS.load(Ordering::SeqCst) {
        os_runtime::fixture_assert_application_close_owners();
    }
    APPLICATION_CLOSES.fetch_add(1, Ordering::SeqCst);
    APPLICATION_EVENTS.lock().unwrap().push(1); // Close entered.
    let generation = APPLICATION_CLOSE_GENERATION.load(Ordering::SeqCst) as u64;
    let result = os_runtime::topology_query(0, generation, abi::MCEXEC_UP_GET_CPU);
    APPLICATION_CLOSE_QUERY.store(result, Ordering::SeqCst);
    APPLICATION_EVENTS.lock().unwrap().push(2); // Reentrant query returned.
}
unsafe extern "C" fn backend_shutdown(slot: u32, generation: u64) -> i32 {
    SHUTDOWN_CALLS.fetch_add(1, Ordering::SeqCst);
    SHUTDOWN_IDENTITY.lock().unwrap().push((slot, generation));
    SHUTDOWN_STATUS.load(Ordering::SeqCst)
}

unsafe extern "C" fn backend_shutdown_v6(slot: u32, generation: u64) -> i64 {
    SHUTDOWN_CALLS.fetch_add(1, Ordering::SeqCst);
    SHUTDOWN_IDENTITY.lock().unwrap().push((slot, generation));
    SHUTDOWN_V6_STATUS.load(Ordering::SeqCst)
}

unsafe extern "C" fn backend_prepare_boot(
    slot: u32,
    generation: u64,
    physical: u64,
    bytes: u64,
) -> i32 {
    assert!(slot < 64 && generation > 0);
    BOOT_GENERATION.store(generation as i64, Ordering::SeqCst);
    assert_eq!(
        PAGES.lock().unwrap().get(&(physical as usize)),
        Some(&(bytes as usize))
    );
    assert_eq!(bytes, 4 << 20);
    assert!(MODULE_REFS.load(Ordering::SeqCst) > 0);
    let mut observer = open(slot).unwrap();
    assert_eq!(
        status(&mut observer, false, abi::IHK_OS_STATUS),
        abi::IHK_OS_STATUS_NOT_BOOTED as i64
    );
    assert_eq!(
        status(&mut observer, true, abi::IHK_OS_QUERY_STATUS),
        abi::IHK_OS_STATUS_NOT_BOOTED as i64
    );
    close(observer);
    BOOT_PREPARE_STATUS.load(Ordering::SeqCst)
}

unsafe extern "C" fn backend_start_boot(slot: u32, generation: u64) -> i32 {
    assert!(slot < 64 && generation > 0);
    assert!(MODULE_REFS.load(Ordering::SeqCst) > 0);
    let mut observer = open(slot).unwrap();
    assert_eq!(
        status(&mut observer, false, abi::IHK_OS_STATUS),
        abi::IHK_OS_STATUS_BOOTING as i64
    );
    assert_eq!(
        status(&mut observer, true, abi::IHK_OS_QUERY_STATUS),
        abi::IHK_OS_STATUS_BOOTING as i64
    );
    close(observer);
    BOOT_START_CALLS.fetch_add(1, Ordering::SeqCst);
    BOOT_START_STATUS.load(Ordering::SeqCst)
}

fn create_boot_backend() -> i64 {
    unsafe {
        os_runtime::ihk_os_create_unbooted_v3(
            0,
            THIS_MODULE.as_ptr().cast(),
            u64::MAX,
            1,
            Some(backend_ioctl),
            Some(backend_release),
            Some(backend_prepare_boot),
            Some(backend_start_boot),
        )
    }
}

fn create_shutdown_backend(shutdown: Option<unsafe extern "C" fn(u32, u64) -> i32>) -> i64 {
    unsafe {
        os_runtime::ihk_os_create_unbooted_v5(
            0,
            THIS_MODULE.as_ptr().cast(),
            u64::MAX,
            1,
            Some(backend_ioctl),
            Some(backend_release),
            Some(backend_prepare_boot),
            Some(backend_start_boot),
            Some(application_open),
            Some(application_invoke),
            Some(application_close),
            shutdown,
        )
    }
}

fn create_shutdown_backend_v6(shutdown: Option<unsafe extern "C" fn(u32, u64) -> i64>) -> i64 {
    unsafe {
        os_runtime::ihk_os_create_unbooted_v6(
            0,
            THIS_MODULE.as_ptr().cast(),
            u64::MAX,
            1,
            Some(backend_ioctl),
            Some(backend_release),
            Some(backend_prepare_boot),
            Some(backend_start_boot),
            Some(application_open),
            Some(application_invoke),
            Some(application_close),
            shutdown,
        )
    }
}

#[test]
fn shutdown_v5_validates_tuple_and_not_booted_idempotence() {
    with_family(|| {
        assert_eq!(
            unsafe {
                os_runtime::ihk_os_create_unbooted_v5(
                    0,
                    THIS_MODULE.as_ptr().cast(),
                    0,
                    1,
                    Some(backend_ioctl),
                    Some(backend_release),
                    Some(backend_prepare_boot),
                    Some(backend_start_boot),
                    Some(application_open),
                    Some(application_invoke),
                    Some(application_close),
                    None,
                )
            },
            -22
        );
        assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
        assert_eq!(create(0), 0);
        let mut file = open(0).unwrap();
        assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
        close(file);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn shutdown_v5_callback_identity_commit_and_rollback_preserve_lease() {
    with_family(|| {
        BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
        BOOT_START_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_CALLS.store(0, Ordering::SeqCst);
        SHUTDOWN_IDENTITY.lock().unwrap().clear();
        assert_eq!(create_shutdown_backend(Some(backend_shutdown)), 0);
        let mut file = open(0).unwrap();
        let second = open(0).unwrap();
        assert_eq!(status(&mut file, false, abi::IHK_OS_BOOT), 0);
        for result in [-4096, 1, -5] {
            SHUTDOWN_STATUS.store(result, Ordering::SeqCst);
            assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), -5);
            assert_eq!(
                status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
                abi::IHK_OS_STATUS_READY as i64
            );
        }
        SHUTDOWN_STATUS.store(0, Ordering::SeqCst);
        assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
        assert_eq!(
            status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
            abi::IHK_OS_STATUS_NOT_BOOTED as i64
        );
        BOOT_START_STATUS.store(-5, Ordering::SeqCst);
        assert_eq!(status(&mut file, false, abi::IHK_OS_BOOT), -5);
        assert_eq!(
            status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
            abi::IHK_OS_STATUS_FAILED as i64
        );
        BOOT_START_STATUS.store(0, Ordering::SeqCst);
        assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
        assert_eq!(
            status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
            abi::IHK_OS_STATUS_NOT_BOOTED as i64
        );
        assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
        assert_eq!(SHUTDOWN_CALLS.load(Ordering::SeqCst), 5);
        let identity = SHUTDOWN_IDENTITY.lock().unwrap().clone();
        assert_eq!(identity.len(), 5);
        assert_eq!(identity[0].0, 0);
        assert!(identity.iter().all(|entry| entry.1 == identity[0].1));
        close(file);
        close(second);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn file_service_resident_admission_blocks_shutdown_until_release() {
    with_family(|| {
        BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
        BOOT_START_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_CALLS.store(0, Ordering::SeqCst);
        SERVICE_OPENS.store(0, Ordering::SeqCst);
        SERVICE_CLOSES.store(0, Ordering::SeqCst);
        SERVICE_COMMAND.store(0, Ordering::SeqCst);
        SERVICE_ARGUMENT.store(0, Ordering::SeqCst);
        SERVICE_COMPAT.store(-1, Ordering::SeqCst);
        assert_eq!(create_shutdown_backend(Some(backend_shutdown)), 0);
        let mut first = open(0).unwrap();
        let mut second = open(0).unwrap();
        assert_eq!(status(&mut first, false, abi::IHK_OS_BOOT), 0);
        assert_eq!(
            unsafe {
                os_service::register(
                    THIS_MODULE.as_ptr().cast(),
                    service_abi::VERSION,
                    Some(service_open),
                    Some(service_ioctl),
                    Some(service_close),
                )
            },
            0
        );
        assert_eq!(status(&mut first, false, abi::MCEXEC_UP_PREPARE_IMAGE), 0);
        assert_eq!(SERVICE_OPENS.load(Ordering::SeqCst), 1);
        assert_eq!(
            SERVICE_COMMAND.load(Ordering::SeqCst) as u32,
            abi::MCEXEC_UP_PREPARE_IMAGE
        );
        assert_eq!(SERVICE_ARGUMENT.load(Ordering::SeqCst) as u64, u64::MAX);
        assert_eq!(SERVICE_COMPAT.load(Ordering::SeqCst), 0);
        assert_eq!(status(&mut second, false, abi::IHK_OS_SHUTDOWN), -16);
        assert_eq!(SHUTDOWN_CALLS.load(Ordering::SeqCst), 0);
        close(first);
        assert_eq!(SERVICE_CLOSES.load(Ordering::SeqCst), 1);
        assert_eq!(status(&mut second, false, abi::IHK_OS_SHUTDOWN), 0);
        close(second);
        assert_eq!(destroy(0), 0);
        unsafe { os_service::unregister(THIS_MODULE.as_ptr().cast()) };
    });
}

#[test]
fn application_connection_blocks_shutdown_until_close() {
    with_family(|| {
        BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
        BOOT_START_STATUS.store(0, Ordering::SeqCst);
        APPLICATION_SUCCEED.store(true, Ordering::SeqCst);
        APPLICATION_CLOSES.store(0, Ordering::SeqCst);
        APPLICATION_INVOKES.store(0, Ordering::SeqCst);
        SHUTDOWN_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_CALLS.store(0, Ordering::SeqCst);
        assert_eq!(create_shutdown_backend(Some(backend_shutdown)), 0);
        let mut file = open(0).unwrap();
        let mut second = open(0).unwrap();
        assert_eq!(status(&mut file, false, abi::IHK_OS_BOOT), 0);
        let generation = {
            let mut output = core::ptr::null_mut();
            assert_eq!(
                unsafe { os_runtime::open_application(0, 1, 1, 42, &mut output) },
                0
            );
            assert!(!output.is_null());
            assert_eq!(
                unsafe { os_runtime::invoke_application(output, 1, core::ptr::null_mut(), 0) },
                17
            );
            assert_eq!(APPLICATION_INVOKES.load(Ordering::SeqCst), 1);
            output
        };
        assert_eq!(status(&mut second, false, abi::IHK_OS_SHUTDOWN), -16);
        assert_eq!(SHUTDOWN_CALLS.load(Ordering::SeqCst), 0);
        CHECK_CLOSE_OWNERS.store(true, Ordering::SeqCst);
        unsafe { os_runtime::close_application(generation) };
        assert_eq!(APPLICATION_CLOSES.load(Ordering::SeqCst), 1);
        APPLICATION_CLOSE_GENERATION.store(1, Ordering::SeqCst);
        APPLICATION_CLOSE_QUERY.store(0, Ordering::SeqCst);
        APPLICATION_EVENTS.lock().unwrap().clear();
        FAIL_BOX.store(true, Ordering::SeqCst);
        let mut failed_output = core::ptr::null_mut();
        assert_eq!(
            unsafe { os_runtime::open_application(0, 1, 1, 42, &mut failed_output) },
            -12
        );
        assert!(failed_output.is_null());
        assert_eq!(APPLICATION_CLOSES.load(Ordering::SeqCst), 2);
        assert_eq!(APPLICATION_CLOSE_QUERY.load(Ordering::SeqCst), 73);
        assert_eq!(*APPLICATION_EVENTS.lock().unwrap(), [1, 2]);
        CHECK_CLOSE_OWNERS.store(false, Ordering::SeqCst);
        assert_eq!(status(&mut second, false, abi::IHK_OS_SHUTDOWN), 0);
        close(file);
        close(second);
        assert_eq!(destroy(0), 0);
        APPLICATION_SUCCEED.store(false, Ordering::SeqCst);
    });
}

#[test]
fn boot_prepare_failures_never_start_and_preserve_initial_cleanup() {
    with_family(|| {
        reset_backend();
        BOOT_START_CALLS.store(0, Ordering::SeqCst);
        for compat in [false, true] {
            for result in [-2, -5, -12, -75, -4096, 1] {
                BOOT_PREPARE_STATUS.store(result, Ordering::SeqCst);
                assert_eq!(create_boot_backend(), 0);
                let mut file = open(0).unwrap();
                assert_eq!(
                    status(&mut file, compat, abi::IHK_OS_BOOT),
                    if (-4095..0).contains(&result) {
                        result as i64
                    } else {
                        -5
                    }
                );
                assert_eq!(status(&mut file, compat, abi::IHK_OS_STATUS), 0);
                assert_eq!(BOOT_START_CALLS.load(Ordering::SeqCst), 0);
                close(file);
                assert_eq!(destroy(0), 0);
            }
        }
    });
}

#[test]
fn boot_v3_requires_every_callback_before_acquiring_owners() {
    with_family(|| {
        for (version, has_ioctl, has_release, has_prepare, has_start) in [
            (0, true, true, true, true),
            (2, true, true, true, true),
            (1, false, true, true, true),
            (1, true, false, true, true),
            (1, true, true, false, true),
            (1, true, true, true, false),
        ] {
            let result = unsafe {
                os_runtime::ihk_os_create_unbooted_v3(
                    0,
                    THIS_MODULE.as_ptr().cast(),
                    0,
                    version,
                    has_ioctl.then_some(backend_ioctl),
                    has_release.then_some(backend_release),
                    has_prepare.then_some(backend_prepare_boot),
                    has_start.then_some(backend_start_boot),
                )
            };
            assert_eq!(result, -22);
            assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 0);
            assert!(NODES.lock().unwrap().is_empty());
            assert!(PAGES.lock().unwrap().is_empty());
        }
    });
}

#[test]
fn boot_started_generations_cannot_release_resources_or_repeat_start() {
    // Started instances deliberately have no unsafe reset/cleanup escape hatch.
    // Isolate each mock case in its own process so their retained owners do not
    // contaminate the other adapter cases. This is not real shutdown evidence.
    let Ok(case) = std::env::var("MCKERNEL_MOCK_BOOT_CASE") else {
        for result in [0, -5, -12, -110, -4096, 1] {
            for compat in [0, 1] {
                let output = std::process::Command::new(std::env::current_exe().unwrap())
                    .args(["--exact", "boot_started_generations_cannot_release_resources_or_repeat_start", "--test-threads=1"])
                    .env("MCKERNEL_MOCK_BOOT_CASE", format!("{result},{compat}"))
                    .output().unwrap();
                assert!(output.status.success(), "{}{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
            }
        }
        return;
    };
    let (result, compat) = case.split_once(',').unwrap();
    let result: i32 = result.parse().unwrap();
    let compat = compat == "1";
    let family = os_runtime::OsDeviceFamily::register().unwrap();
    let _provider = device_registry::IHK_DEVICE_REGISTRY
        .attach_provider_token()
        .unwrap();
    BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
    BOOT_START_STATUS.store(result, Ordering::SeqCst);
    assert_eq!(create_boot_backend(), 0);
    let mut file = open(0).unwrap();
    assert_eq!(
        status(&mut file, compat, abi::IHK_OS_BOOT),
        if (-4095..=0).contains(&result) {
            result as i64
        } else {
            -5
        }
    );
    assert_eq!(
        status(&mut file, !compat, abi::IHK_OS_QUERY_STATUS),
        if result == 0 {
            abi::IHK_OS_STATUS_READY as i64
        } else {
            abi::IHK_OS_STATUS_FAILED as i64
        }
    );
    for request in [
        abi::IHK_OS_LOAD,
        abi::IHK_OS_BOOT,
        abi::IHK_OS_ASSIGN_CPU,
        abi::IHK_OS_ASSIGN_MEM,
    ] {
        assert_eq!(status(&mut file, compat, request), -16);
    }
    assert_eq!(BOOT_START_CALLS.load(Ordering::SeqCst), 1);
    close(file);
    assert_eq!(destroy(0), -16);
    assert_eq!(MODULE_REFS.load(Ordering::SeqCst), 1);
    assert_eq!(PAGES.lock().unwrap().len(), 1);
    assert_eq!(NODES.lock().unwrap().len(), 1);
    assert!(BACKEND_RELEASES.lock().unwrap().is_empty());
    std::mem::forget(family);
}

#[test]
fn image_load_publishes_loading_and_restores_initial_state_after_every_result() {
    with_family(|| {
        reset_backend();
        assert_eq!(create_backend(), 0);
        let mut file = open(0).unwrap();
        for compat in [false, true] {
            for result in [0, -2, -5, -12, -14, -75, -4096] {
                BACKEND_LOAD_STATUS.store(result, Ordering::SeqCst);
                assert_eq!(
                    status(&mut file, compat, abi::IHK_OS_LOAD),
                    if result == -4096 { -5 } else { result as i64 }
                );
                assert_eq!(status(&mut file, compat, abi::IHK_OS_STATUS), 0);
                assert_eq!(status(&mut file, compat, 0x112a22), 73);
            }
        }
        close(file);
        assert_eq!(destroy(0), 0);
    });
}

#[test]
fn versioned_backend_validates_callbacks_before_any_publication() {
    with_family(|| {
        reset_backend();
        for (version, ioctl, release) in [
            (0, true, true),
            (2, true, true),
            (1, false, true),
            (1, true, false),
            (1, false, false),
        ] {
            assert_eq!(
                unsafe {
                    os_runtime::ihk_os_create_unbooted_v2(
                        0,
                        THIS_MODULE.as_ptr().cast(),
                        0,
                        version,
                        if ioctl { Some(backend_ioctl) } else { None },
                        if release { Some(backend_release) } else { None },
                    )
                },
                -22
            );
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
            if index > 0 {
                assert!(calls[index].1 > calls[index - 1].1);
            }
        }
    });
}

#[test]
fn backend_serializes_operations_across_concurrent_open_files() {
    with_family(|| {
        reset_backend();
        assert_eq!(create_backend(), 0);
        let threads: Vec<_> = (0..8)
            .map(|_| {
                std::thread::spawn(|| {
                    let mut file = open(0).unwrap();
                    for _ in 0..4 {
                        assert_eq!(status(&mut file, false, 0x112a22), 73);
                    }
                    close(file);
                })
            })
            .collect();
        for thread in threads {
            thread.join().unwrap();
        }
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
    assert_eq!(
        create.require_unbooted_destroy(),
        Err(ihk_ioctl::IoctlError::InvalidArgument)
    );
    let handle = create.handle();
    create.commit_after_external_success().unwrap();
    registry
        .transition(handle, os_registry::OsStatus::Loading)
        .unwrap();
    {
        let destroy = dispatcher
            .prepare_device(0x112901, handle.minor() as u64)
            .unwrap();
        assert_eq!(
            destroy.require_unbooted_destroy(),
            Err(ihk_ioctl::IoctlError::Busy)
        );
        assert_eq!(
            registry.acquire(handle).err(),
            Some(os_registry::RegistryError::Busy)
        );
    }
    assert_eq!(
        registry.snapshot(handle).unwrap().status,
        os_registry::OsStatus::Loading
    );
    registry
        .transition(handle, os_registry::OsStatus::NotBooted)
        .unwrap();
    let destroy = dispatcher
        .prepare_device(0x112901, handle.minor() as u64)
        .unwrap();
    destroy.require_unbooted_destroy().unwrap();
    destroy.commit_after_external_success().unwrap();
    assert_eq!(registry.live_count(), 0);
}
// RUNTIME_PRIVATE_TESTS
// Appended inside the copied production os_runtime module by the driver.
#[cfg(test)]
pub(crate) fn fixture_assert_application_close_owners() {
    let handle = OS_REGISTRY.resolve_minor(0).unwrap();
    // Two open files plus the connection must remain leased during Close.
    assert_eq!(OS_REGISTRY.snapshot(handle).unwrap().references, 3);
    let object = OS_OBJECTS[0].load(Ordering::Acquire);
    assert!(!object.is_null());
    // The fixture invokes this synchronously from the retained Close callback.
    let gate = unsafe { &(*object).admission };
    assert_eq!(gate.word.load(Ordering::Acquire) & ADMISSION_COUNT_MASK, 1);
    assert!(matches!(gate.close_for_shutdown(), Err(error) if error.to_errno() == -16));
    assert!(!gate.is_closed());
}

#[cfg(test)]
mod shutdown_effect_tests {
    use super::*;
    use crate::{
        abi, backend_shutdown_v6, close, create_shutdown_backend_v6, destroy, open, status,
        with_family, BOOT_PREPARE_STATUS, BOOT_START_STATUS, SHUTDOWN_CALLS,
        SHUTDOWN_V6_STATUS,
    };
    use crate::os_registry::{self, OsRegistry, OsStatus, RegistryError};

    fn ready(registry: &OsRegistry) -> os_registry::OsHandle {
        let reservation = registry.reserve().unwrap();
        let handle = reservation.handle();
        reservation.commit().unwrap();
        // Match os_request's successful boot, not an invalid direct Ready edge.
        registry.transition(handle, OsStatus::Booting).unwrap();
        registry.transition(handle, OsStatus::Ready).unwrap();
        handle
    }

    #[test]
    fn v5_outcome_keeps_nonzero_pre_effect() {
        assert_eq!(shutdown_v5_outcome(0), ShutdownCallbackOutcome::Complete);
        for result in [-1, -4095, 1, -4096] {
            assert_eq!(shutdown_v5_outcome(result), ShutdownCallbackOutcome::PreEffectFailure(result));
        }
        assert_ne!(ShutdownCallbackOutcome::PostEffectFailure(-5), shutdown_v5_outcome(-5));
    }

    #[test]
    fn v6_outcome_tag_drives_production_shutdown_transaction() {
        assert_eq!(shutdown_v6_outcome(0), ShutdownCallbackOutcome::Complete);
        assert_eq!(
            shutdown_v6_outcome(-110),
            ShutdownCallbackOutcome::PreEffectFailure(-110)
        );
        let encoded = SHUTDOWN_V6_POST_EFFECT | ((-110_i32 as u32) as i64);
        assert_eq!(
            shutdown_v6_outcome(encoded),
            ShutdownCallbackOutcome::PostEffectFailure(-110)
        );
        assert_eq!(
            shutdown_v6_outcome(1),
            ShutdownCallbackOutcome::PreEffectFailure(-5)
        );
    }

    #[test]
    fn pre_effect_failure_reopens_gate_and_allows_new_admission() {
        let registry = OsRegistry::new();
        let handle = ready(&registry);
        let lease = registry.acquire(handle).unwrap();
        let gate = Admission::new();
        let admission = gate.close_for_shutdown().unwrap();
        let guard = registry.begin_shutdown(handle).unwrap();
        assert_eq!(finish_shutdown(guard, admission, ShutdownCallbackOutcome::PreEffectFailure(-110)), -110);
        assert!(!gate.is_closed());
        let fresh = gate.enter().expect("pre-effect rollback must reopen admission");
        drop(fresh);
        assert!(matches!(registry.snapshot(handle).unwrap().status, OsStatus::Ready));
        drop(lease);
    }

    #[test]
    fn v6_post_effect_failure_keeps_admission_and_registry_closed() {
        with_family(|| {
            BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
            BOOT_START_STATUS.store(0, Ordering::SeqCst);
            SHUTDOWN_CALLS.store(0, Ordering::SeqCst);
            SHUTDOWN_V6_STATUS.store(
                SHUTDOWN_V6_POST_EFFECT | ((-110_i32 as u32) as i64),
                Ordering::SeqCst,
            );
            assert_eq!(create_shutdown_backend_v6(Some(backend_shutdown_v6)), 0);
            let mut file = open(0).unwrap();
            assert_eq!(status(&mut file, false, abi::IHK_OS_BOOT), 0);
            assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), -110);
            assert_eq!(
                status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
                abi::IHK_OS_STATUS_SHUTDOWN as i64
            );
            // A same-handle retry reaches the retained v6 callback while the
            // registry remains Shutdown; its tagged failure is still reported
            // without reopening admission.
            assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), -110);
            assert_eq!(SHUTDOWN_CALLS.load(Ordering::SeqCst), 2);
            SHUTDOWN_V6_STATUS.store(0, Ordering::SeqCst);
            assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
            assert_eq!(
                status(&mut file, false, abi::IHK_OS_QUERY_STATUS),
                abi::IHK_OS_STATUS_NOT_BOOTED as i64
            );
            assert_eq!(SHUTDOWN_CALLS.load(Ordering::SeqCst), 3);
            close(file);
            assert_eq!(destroy(0), 0);
        });
    }

    #[test]
    fn post_effect_retains_shutdown_admission_lease_and_same_generation_retry() {
        let registry = OsRegistry::new();
        let handle = ready(&registry);
        let lease = registry.acquire(handle).unwrap();
        let gate = Admission::new();
        let surviving_callback = gate.enter().unwrap();
        assert!(matches!(gate.close_for_shutdown(), Err(error) if error.to_errno() == -16));
        drop(surviving_callback);
        let admission = gate.close_for_shutdown().unwrap();
        let guard = registry.begin_shutdown(handle).unwrap();
        assert_eq!(finish_shutdown(guard, admission, ShutdownCallbackOutcome::PostEffectFailure(-5)), -5);
        assert!(gate.is_closed());
        assert!(matches!(gate.enter(), Err(error) if error.to_errno() == -16));
        let retained = registry.snapshot(handle).unwrap();
        assert_eq!(retained.status, OsStatus::Shutdown);
        assert_eq!(retained.references, 1);
        assert!(matches!(registry.begin_destroy(handle), Err(RegistryError::Busy)));

        // A retry reporting no new effect must not reopen the old close or
        // resurrect Ready after a previous attempt already changed the guest.
        let admission = gate.close_for_shutdown().unwrap();
        let retry = registry.begin_shutdown(handle).unwrap();
        assert_eq!(finish_shutdown(retry, admission, ShutdownCallbackOutcome::PreEffectFailure(-16)), -16);
        assert_eq!(registry.snapshot(handle).unwrap(), retained);
        assert!(gate.is_closed());
        assert!(matches!(gate.enter(), Err(error) if error.to_errno() == -16));

        let admission = gate.close_for_shutdown().unwrap();
        let retry = registry.begin_shutdown(handle).unwrap();
        assert_eq!(retry.handle(), handle);
        assert_eq!(finish_shutdown(retry, admission, ShutdownCallbackOutcome::Complete), 0);
        let completed = registry.snapshot(handle).unwrap();
        assert_eq!(completed.handle, handle);
        assert_eq!(completed.status, OsStatus::NotBooted);
        assert_eq!(completed.references, 1);
        assert!(gate.is_closed());
        assert!(matches!(gate.enter(), Err(error) if error.to_errno() == -16));
        drop(lease);
        assert_eq!(registry.snapshot(handle).unwrap().references, 0);
    }

    #[test]
    fn mark_irreversible_fault_does_not_reopen_admission() {
        let registry = OsRegistry::new();
        let handle = ready(&registry);
        let lease = registry.acquire(handle).unwrap();
        let gate = Admission::new();
        let admission = gate.close_for_shutdown().unwrap();
        let guard = registry.begin_shutdown(handle).unwrap();
        // Deliberately corrupt only phase, keeping generation/status/references
        // intact; the real mark_irreversible must reject this impossible word.
        os_registry::fixture_invalidate_shutdown_phase(&registry, handle);
        let corrupted = registry.snapshot(handle).unwrap();
        assert_eq!(finish_shutdown(guard, admission, ShutdownCallbackOutcome::PostEffectFailure(-5)), -16);
        assert!(gate.is_closed());
        assert!(matches!(gate.enter(), Err(error) if error.to_errno() == -16));
        assert_eq!(registry.snapshot(handle).unwrap(), corrupted);
        assert_eq!(corrupted.status, OsStatus::Shutdown);
        assert_eq!(corrupted.references, 1);
        drop(lease);
    }

    #[test]
    fn stale_generation_cannot_retry_shutdown() {
        let registry = OsRegistry::new();
        let old = ready(&registry);
        let gate = Admission::new();
        assert_eq!(finish_shutdown(registry.begin_shutdown(old).unwrap(), gate.close_for_shutdown().unwrap(), ShutdownCallbackOutcome::Complete), 0);
        registry.begin_destroy(old).unwrap().commit().unwrap();
        let current = ready(&registry);
        assert_eq!(old.minor(), current.minor());
        assert_ne!(old.generation(), current.generation());
        let before = registry.snapshot(current).unwrap();
        assert!(matches!(registry.begin_shutdown(old), Err(RegistryError::StaleHandle)));
        assert_eq!(registry.snapshot(current).unwrap(), before);
        assert!(gate.is_closed());
    }
}
// REGISTRY_FIXTURE_FAULT
// Appended only to the disposable registry copy. No production test hook.
#[cfg(test)]
pub(crate) fn fixture_invalidate_shutdown_phase(registry: &OsRegistry, handle: OsHandle) {
    let slot = &registry.slots[handle.minor()];
    let current = slot.word.load(Ordering::Acquire);
    assert!(is_shutdown_word(current, handle));
    slot.word.store((current & !PHASE_MASK) | PHASE_LIVE, Ordering::Release);
}
