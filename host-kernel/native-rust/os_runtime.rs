// SPDX-License-Identifier: GPL-2.0
//! Linux ownership adapter for unbooted native IHK OS instances.
//!
//! The registry excludes opens during construction and destruction. Each open
//! file owns a generation-checked lease; each instance owns its provider lease,
//! a Linux module reference and a physically contiguous, zeroed kmsg buffer.
//! The versioned backend receives only generation-checked, serialized calls.
//! Image loading and boot are not implemented by this ownership adapter.

use core::{
    ffi::c_void,
    mem::MaybeUninit,
    pin::Pin,
    ptr,
    sync::atomic::{AtomicPtr, AtomicU32, Ordering},
};
use kernel::{
    bindings,
    error::to_result,
    prelude::*,
    sync::{new_mutex, Mutex},
};

use super::{
    abi::{
        IhkKmsgBuffer, IHK_DEVICE_CREATE_OS, IHK_DEVICE_DESTROY_OS, IHK_OS_LOAD,
        IHK_OS_QUERY_STATUS, IHK_OS_STATUS,
    },
    device_registry::{DeviceHandle, DeviceOsLease, IHK_DEVICE_REGISTRY},
    ihk_ioctl::IhkIoctlDispatcher,
    os_registry::{OsLease, OsRegistry, OsStatus, OS_CAPACITY},
    IhkExportSymbolRecord,
};

const MINOR_BITS: u32 = 20;
const MINOR_MASK: u32 = (1 << MINOR_BITS) - 1;
const KMSG_ORDER: u32 = 10;
const KMSG_BYTES: usize = 4 << 20;
const _: [(); KMSG_BYTES] = [(); core::mem::size_of::<IhkKmsgBuffer>()];
const _: [(); KMSG_BYTES] = [(); 4096 << KMSG_ORDER];

static OS_REGISTRY: OsRegistry = OsRegistry::new();
static OS_OBJECTS: [AtomicPtr<OsObject>; OS_CAPACITY] =
    [const { AtomicPtr::new(ptr::null_mut()) }; OS_CAPACITY];
static OS_CLASS: AtomicPtr<bindings::class> = AtomicPtr::new(ptr::null_mut());
static OS_MAJOR: AtomicU32 = AtomicU32::new(0);

// Empty lockdep structs in generated bindings cannot cross a Rust extern
// declaration. Erase only opaque pointees; keep the exact C pointer/scalar ABI.
//
// SAFETY: These are Linux 6.12 kernel exports with their C header ABI.
// Calls below supply only module-resident operations, registered device IDs,
// valid kernel module pointers or allocation addresses owned by this adapter.
extern "C" {
    fn __register_chrdev(
        major: u32,
        base: u32,
        count: u32,
        name: *const i8,
        operations: *const c_void,
    ) -> i32;
    fn __unregister_chrdev(major: u32, base: u32, count: u32, name: *const i8);
    fn class_create(name: *const i8) -> *mut bindings::class;
    fn class_destroy(class: *const bindings::class);
    fn device_create(
        class: *const bindings::class,
        parent: *mut c_void,
        dev: u32,
        data: *mut c_void,
        format: *const i8,
        ...
    ) -> *mut c_void;
    fn device_destroy(class: *const bindings::class, dev: u32);
    fn get_free_pages_noprof(flags: u32, order: u32) -> usize;
    fn free_pages(address: usize, order: u32);
    fn try_module_get(module: *mut c_void) -> bool;
    fn module_put(module: *mut c_void);
}

fn errno(value: i32) -> Error {
    to_result(value).err().unwrap_or(EIO)
}

fn check_pointer<T>(value: *mut T) -> Result<*mut T> {
    let address = value as isize;
    if (-4095..0).contains(&address) {
        Err(errno(address as i32))
    } else if value.is_null() {
        Err(ENOMEM)
    } else {
        Ok(value)
    }
}

#[must_use = "the module reference must remain owned until OS destruction"]
struct ProviderModule(*mut bindings::module);

impl ProviderModule {
    /// # Safety
    /// `module` must point to the calling SMP module, already pinned by its
    /// open control file throughout this call. It must not be a userspace value.
    // SAFETY: Callers must hold a Linux reference to this valid module pointer
    // while acquire attempts to obtain a separately owned reference.
    unsafe fn acquire(module: *mut bindings::module) -> Result<Self> {
        if module.is_null() {
            return Err(EINVAL);
        }
        // SAFETY: The caller supplies its currently pinned Linux module.
        if !unsafe { try_module_get(module.cast()) } {
            return Err(EBUSY);
        }
        Ok(Self(module))
    }
}

impl Drop for ProviderModule {
    fn drop(&mut self) {
        // SAFETY: This unique owner balances one successful try_module_get.
        // The caller's control-file reference remains live during destruction.
        unsafe { module_put(self.0.cast()) };
    }
}

#[must_use = "the allocation must remain owned for the OS lifetime"]
struct KmsgPages(usize);

impl KmsgPages {
    fn allocate() -> Result<Self> {
        // No highmem flags: get_free_pages_noprof supplies a directly mapped x86_64
        // allocation. NORETRY/NOWARN make fragmented-memory failure bounded.
        // Use generated enum bits for flags without Rust const helpers in 6.12.
        let flags = bindings::GFP_KERNEL
            | bindings::__GFP_ZERO
            | (1 << bindings::___GFP_COMP_BIT)
            | (1 << bindings::___GFP_NORETRY_BIT)
            | (1 << bindings::___GFP_NOWARN_BIT);
        // SAFETY: The fixed order is ten (4 MiB), the flags are Linux GFP
        // constants, and this process-context allocation holds no spinlock.
        let address = unsafe { get_free_pages_noprof(flags, KMSG_ORDER) };
        if address == 0 {
            return Err(ENOMEM);
        }
        let pages = Self(address);
        let buffer = address as *mut IhkKmsgBuffer;
        // SAFETY: The allocation is zeroed, directly mapped, exclusively
        // owned, page-aligned and exactly the ABI size. Initialize only the
        // length field in place; never put the 4 MiB structure on the stack.
        unsafe { ptr::addr_of_mut!((*buffer).length).write((KMSG_BYTES - 4096) as i32) };
        Ok(pages)
    }
}

impl Drop for KmsgPages {
    fn drop(&mut self) {
        // SAFETY: Exactly this base address and order came from the successful
        // allocation; no mapping, user reference or co-kernel access escaped.
        unsafe { free_pages(self.0, KMSG_ORDER) };
    }
}

// SAFETY: Only IHK invokes these callbacks with a live OsLease or an exclusive
// DestroyGuard, respectively. The owning SMP module must keep the callbacks
// resident, accept the exact scalar ABI and borrow user addresses only during
// ioctl. The release callback must finish all resource cleanup before success,
// and leave the OS usable on failure. Neither callback may reenter OS ioctls
// or destruction while the per-OS operation lock is held.
type OsBackendIoctlV2 = unsafe extern "C" fn(u32, u64, u32, u64, u32) -> i64;
// SAFETY: The exclusive destruction guard proves this exact slot/generation
// has no open references. Success returns its resources before minor reuse.
type OsBackendReleaseV2 = unsafe extern "C" fn(u32, u64) -> i32;

#[derive(Clone, Copy)]
struct OsBackend {
    ioctl: OsBackendIoctlV2,
    release: OsBackendReleaseV2,
}

struct OsObject {
    provider: DeviceHandle,
    operations: Pin<Box<Mutex<()>>>,
    backend: Option<OsBackend>,
    _kmsg: KmsgPages,
    _provider_lease: DeviceOsLease<'static>,
    // Drop the kernel module pin after the logical provider reference.
    _provider_module: ProviderModule,
}

/// Owns the Linux character-device family. OS minors remain 0..64 even though
/// the allocated Linux major is dynamic. Only live instances get device nodes.
pub(crate) struct OsDeviceFamily;

impl OsDeviceFamily {
    pub(crate) fn register() -> Result<Self> {
        // SAFETY: The operations and name reside in ihk.ko; .owner pins it for
        // every callback. Linux allocates a major for exactly 64 minor numbers.
        let major = unsafe {
            __register_chrdev(
                0,
                0,
                OS_CAPACITY as u32,
                kernel::c_str!("mcos").as_char_ptr(),
                ptr::from_ref(&OS_FOPS).cast(),
            )
        };
        to_result(major)?;
        // SAFETY: The constant name is NUL terminated and outlives the class.
        let class =
            match check_pointer(unsafe { class_create(kernel::c_str!("mcos").as_char_ptr()) }) {
                Ok(class) => class,
                Err(error) => {
                    // SAFETY: Registration succeeded and no class/OS was published.
                    unsafe {
                        __unregister_chrdev(
                            major as u32,
                            0,
                            OS_CAPACITY as u32,
                            kernel::c_str!("mcos").as_char_ptr(),
                        )
                    };
                    return Err(error);
                }
            };
        OS_MAJOR.store(major as u32, Ordering::Release);
        OS_CLASS.store(class, Ordering::Release);
        pr_info!("os_family=registered minors=64\n");
        Ok(Self)
    }
}

impl Drop for OsDeviceFamily {
    fn drop(&mut self) {
        assert!(OS_REGISTRY.live_count() == 0);
        assert!(OS_OBJECTS
            .iter()
            .all(|slot| slot.load(Ordering::Acquire).is_null()));
        let class = OS_CLASS.swap(ptr::null_mut(), Ordering::AcqRel);
        let major = OS_MAJOR.swap(0, Ordering::AcqRel);
        // SAFETY: All instance nodes are gone and .owner excludes outstanding
        // file callbacks during module exit. These are the owned registrations.
        unsafe {
            class_destroy(class);
            __unregister_chrdev(
                major,
                0,
                OS_CAPACITY as u32,
                kernel::c_str!("mcos").as_char_ptr(),
            );
        }
        pr_info!("os_family=removed active=0\n");
    }
}

// SAFETY: Called only by the pinned native SMP control-file ioctl. The owner
// is the caller's Linux module pointer, never a user argument or Rust object.
// No callback or caller data is retained; a Linux module reference is acquired.
#[export_name = "ihk_os_create_unbooted_v1"]
// SAFETY: The C caller supplies its already pinned Linux module pointer; this
// adapter acquires a separate module reference before publishing any OS node.
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v1(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
) -> i64 {
    // SAFETY: The exported boundary's caller guarantees the owner lifetime.
    match unsafe { create_os(provider_minor, owner.cast(), argument, None) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Create an unbooted OS with callbacks pinned by its provider module owner.
/// ABI version 1 uses (slot, generation, command, user address, compat=0/1)
/// for ioctl and (slot, generation) for exclusive resource cleanup.
///
/// # Safety
/// The caller pins `owner`, and both callbacks reside in that module and obey
/// the contracts above. These are trusted code pointers, never userspace data.
// SAFETY: The boundary validates the callback version and complete callback
// pair before acquiring owners or publishing anything. The existing create
// transaction retains the module before storing either function pointer.
#[export_name = "ihk_os_create_unbooted_v2"]
// SAFETY: This C ABI accepts a pinned Linux module pointer and trusted callback
// identities with the exact scalar signature; no unwind may cross the boundary.
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v2(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
) -> i64 {
    let backend = match (callback_abi, ioctl, release) {
        (1, Some(ioctl), Some(release)) => OsBackend { ioctl, release },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The caller supplies pinned module-resident callbacks. The
    // object stores only their copied identities and its own module reference.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// # Safety
/// The owner is the live, control-file-pinned native SMP module.
// SAFETY: The caller pins its Linux SMP module throughout this call. Registry
// reservations and owned allocations below exclude partially initialized opens.
unsafe fn create_os(
    provider_minor: u32,
    owner: *mut bindings::module,
    argument: u64,
    backend: Option<OsBackend>,
) -> Result<usize> {
    let class = OS_CLASS.load(Ordering::Acquire);
    let major = OS_MAJOR.load(Ordering::Acquire);
    if class.is_null() || major == 0 {
        return Err(ENODEV);
    }
    let provider = IHK_DEVICE_REGISTRY
        .resolve_minor(provider_minor as usize)
        .map_err(|error| errno(error.errno()))?;
    let provider_lease = IHK_DEVICE_REGISTRY
        .acquire_os(provider)
        .map_err(|error| errno(error.errno()))?;
    // SAFETY: The live control-file owner is guaranteed by this function's caller.
    let provider_module = unsafe { ProviderModule::acquire(owner) }?;
    let dispatcher = IhkIoctlDispatcher::new(&OS_REGISTRY);
    let transaction = dispatcher
        .prepare_device(IHK_DEVICE_CREATE_OS, argument)
        .map_err(|error| errno(error.errno()))?;
    let handle = transaction.handle();
    let minor = handle.minor();
    let object = Box::new(
        OsObject {
            provider,
            operations: Box::pin_init(new_mutex!(()), GFP_KERNEL)?,
            backend,
            _kmsg: KmsgPages::allocate()?,
            _provider_lease: provider_lease,
            _provider_module: provider_module,
        },
        GFP_KERNEL,
    )
    .map_err(|_| ENOMEM)?;
    let object = Box::into_raw(object);
    assert!(OS_OBJECTS[minor].swap(object, Ordering::AcqRel).is_null());
    let dev = (major << MINOR_BITS) | minor as u32;
    // SAFETY: The registered class owns this unique reserved minor. The format
    // is constant and the variadic integer matches %u. No driver-data escapes.
    let node = unsafe {
        device_create(
            class,
            ptr::null_mut(),
            dev,
            ptr::null_mut(),
            kernel::c_str!("mcos%u").as_char_ptr(),
            minor as u32,
        )
    };
    if check_pointer(node).is_err() {
        let removed = OS_OBJECTS[minor].swap(ptr::null_mut(), Ordering::AcqRel);
        assert!(removed == object);
        // SAFETY: The unpublished registry reservation excludes every open.
        // This uniquely reclaims the Box and all of its allocation/lease owners.
        unsafe { drop(Box::from_raw(removed)) };
        return Err(ENOMEM);
    }
    // Any unexpected registry corruption fails stop; a successful return must
    // never leave a node with an unpublished or mismatched OS identity.
    transaction
        .commit_after_external_success()
        .unwrap_or_else(|_| panic!("OS publication invariant violated"));
    pr_info!(
        "os=create minor={} state=not-booted kmsg_bytes={}\n",
        minor,
        KMSG_BYTES
    );
    Ok(minor)
}

// SAFETY: This C ABI accepts scalar minor numbers only. It tears down solely an
// unbooted OS belonging to the given live provider and propagates busy errors.
#[export_name = "ihk_os_destroy_unbooted_v1"]
// SAFETY: Only scalar identities cross this C ABI. Registry guards validate
// ownership and exclude live open files before any allocation is reclaimed.
pub(crate) extern "C" fn ihk_os_destroy_unbooted_v1(provider_minor: u32, minor: u64) -> i64 {
    match destroy_os(provider_minor, minor) {
        Ok(()) => 0,
        Err(error) => error.to_errno() as i64,
    }
}

fn destroy_os(provider_minor: u32, minor: u64) -> Result {
    let provider = IHK_DEVICE_REGISTRY
        .resolve_minor(provider_minor as usize)
        .map_err(|error| errno(error.errno()))?;
    let dispatcher = IhkIoctlDispatcher::new(&OS_REGISTRY);
    let transaction = dispatcher
        .prepare_device(IHK_DEVICE_DESTROY_OS, minor)
        .map_err(|error| errno(error.errno()))?;
    transaction
        .require_unbooted_destroy()
        .map_err(|error| errno(error.errno()))?;
    let handle = transaction.handle();
    let index = handle.minor();
    let object = OS_OBJECTS[index].load(Ordering::Acquire);
    assert!(!object.is_null());
    // SAFETY: The exclusive destroying guard excludes opens and other
    // destructors. Publication stored the complete object before the live word.
    if unsafe { (*object).provider } != provider {
        return Err(EINVAL);
    }
    // SAFETY: The same exclusive DestroyGuard owns this published object.
    // Backend cleanup runs before its node, allocations or module owner drop.
    let object_ref = unsafe { &*object };
    {
        let _operation = object_ref.operations.lock();
        if let Some(backend) = object_ref.backend {
            // SAFETY: No OsLease exists while the destruction guard is live.
            // The retained ProviderModule pins this exact callback identity.
            let status = unsafe { (backend.release)(index as u32, handle.generation()) };
            if status != 0 {
                return Err(if status < 0 { errno(status) } else { EIO });
            }
        }
    }
    let class = OS_CLASS.load(Ordering::Acquire);
    let dev = (OS_MAJOR.load(Ordering::Acquire) << MINOR_BITS) | index as u32;
    // SAFETY: The node belongs to this exclusive destruction transaction.
    unsafe { device_destroy(class, dev) };
    let removed = OS_OBJECTS[index].swap(ptr::null_mut(), Ordering::AcqRel);
    assert!(removed == object);
    // SAFETY: No file lease or other destruction can hold this object. Drop
    // storage and both provider references before making the minor reusable.
    unsafe { drop(Box::from_raw(removed)) };
    transaction
        .commit_after_external_success()
        .unwrap_or_else(|_| panic!("OS destruction invariant violated"));
    pr_info!("os=destroy minor={} state=vacant\n", index);
    Ok(())
}

// SAFETY: Linux calls this only with a live inode/file and ihk.ko pinned by
// .owner. Successful open installs exactly one owned lease in private_data.
unsafe extern "C" fn os_open(inode: *mut bindings::inode, file: *mut bindings::file) -> i32 {
    // SAFETY: Linux supplies the live inode for this registered device family.
    let minor = unsafe { (*inode).i_rdev } & MINOR_MASK;
    let lease = match OS_REGISTRY
        .resolve_minor(minor as usize)
        .and_then(|handle| OS_REGISTRY.acquire(handle))
    {
        Ok(lease) => lease,
        Err(error) => return error.errno(),
    };
    let lease = match Box::new(lease, GFP_KERNEL) {
        Ok(lease) => lease,
        Err(_) => return -12,
    };
    // SAFETY: Linux gives this open callback exclusive initialization of the
    // new file. Failure above drops the lease before leaving private_data alone.
    unsafe { (*file).private_data = Box::into_raw(lease).cast() };
    0
}

// SAFETY: Linux calls release once after the final file reference. No ioctl
// can still borrow the private lease, and .owner keeps this module resident.
unsafe extern "C" fn os_release(_inode: *mut bindings::inode, file: *mut bindings::file) -> i32 {
    // SAFETY: This is the exact Box installed by a successful os_open, reclaimed
    // once. Linux excludes concurrent use at final file release.
    unsafe {
        let lease = (*file).private_data.cast::<OsLease<'static>>();
        (*file).private_data = ptr::null_mut();
        drop(Box::from_raw(lease));
    }
    0
}

// SAFETY: Linux pins the file for the callback; its immutable private lease
// keeps the exact OS generation live until this callback and all peers finish.
unsafe extern "C" fn os_ioctl(
    file: *mut bindings::file,
    command: u32,
    argument: core::ffi::c_ulong,
) -> core::ffi::c_long {
    // SAFETY: Linux supplies the live file and its owned immutable lease.
    unsafe { os_request(file, command, argument, false) }
}

// SAFETY: Linux's compat callback has the same file lifetime as native ioctl.
// Zero-extend the top-level user address once before any backend can parse it.
#[cfg(CONFIG_COMPAT)]
unsafe extern "C" fn os_compat_ioctl(
    file: *mut bindings::file,
    command: u32,
    argument: core::ffi::c_ulong,
) -> core::ffi::c_long {
    // SAFETY: Linux supplies this live file with its generation-checked lease.
    unsafe { os_request(file, command, argument as u32 as u64, true) }
}

// SAFETY: Only the two Linux file callbacks enter this function. File release
// cannot overlap; its lease excludes OS destruction and minor reuse.
unsafe fn os_request(
    file: *mut bindings::file,
    command: u32,
    argument: u64,
    compat: bool,
) -> core::ffi::c_long {
    // SAFETY: Successful open installed this live Box; release cannot overlap.
    let lease = unsafe { &*((*file).private_data.cast::<OsLease<'static>>()) };
    if matches!(command, IHK_OS_STATUS | IHK_OS_QUERY_STATUS) {
        let dispatcher = IhkIoctlDispatcher::new(&OS_REGISTRY);
        return match dispatcher.dispatch_os(lease.handle(), command, 0) {
            Ok(status) => status as core::ffi::c_long,
            Err(error) => error.errno() as core::ffi::c_long,
        };
    }
    let handle = lease.handle();
    let object = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
    assert!(!object.is_null());
    // SAFETY: The immutable file lease keeps this generation's published
    // object and its provider module owner live throughout the callback.
    let object = unsafe { &*object };
    let _operation = object.operations.lock();
    // Resource assignment is restricted to the initial, unbooted state. Future
    // load/boot transitions must take this same operation lock before changing
    // registry status or accessing the backend's assigned resources.
    match OS_REGISTRY.snapshot(handle) {
        Ok(snapshot) if snapshot.status == OsStatus::NotBooted => {}
        Ok(_) => return EBUSY.to_errno() as core::ffi::c_long,
        Err(error) => return error.errno() as core::ffi::c_long,
    }
    let Some(backend) = object.backend else {
        return EINVAL.to_errno() as core::ffi::c_long;
    };
    let loading = command == IHK_OS_LOAD;
    if loading {
        if let Err(error) = OS_REGISTRY.transition(handle, OsStatus::Loading) {
            return error.errno() as core::ffi::c_long;
        }
    }
    // SAFETY: This exact slot/generation is pinned by the file lease. The OS
    // operation mutex serializes its backend calls, the module owner pins the
    // code, and user addresses are only borrowed for this synchronous call.
    let status = unsafe {
        (backend.ioctl)(
            handle.minor() as u32,
            handle.generation(),
            command,
            argument,
            u32::from(compat),
        )
    };
    if loading {
        if let Err(error) = OS_REGISTRY.transition(handle, OsStatus::NotBooted) {
            return error.errno() as core::ffi::c_long;
        }
    }
    if status < -4095 {
        return EIO.to_errno() as core::ffi::c_long;
    }
    status as core::ffi::c_long
}

// SAFETY: All-zero optional callbacks are valid, and every non-null pointer
// names module-resident code. Compat has its own user-address normalization.
const OS_FOPS: bindings::file_operations = {
    let mut operations: bindings::file_operations = unsafe { MaybeUninit::zeroed().assume_init() };
    operations.owner = super::THIS_MODULE.as_ptr();
    operations.open = Some(os_open);
    operations.release = Some(os_release);
    operations.unlocked_ioctl = Some(os_ioctl);
    #[cfg(CONFIG_COMPAT)]
    {
        operations.compat_ioctl = Some(os_compat_ioctl);
    }
    operations
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v1 as *const () as *const u8,
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v2 as *const () as *const u8,
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_destroy_unbooted_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_DESTROY_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_destroy_unbooted_v1 as *const () as *const u8,
};
