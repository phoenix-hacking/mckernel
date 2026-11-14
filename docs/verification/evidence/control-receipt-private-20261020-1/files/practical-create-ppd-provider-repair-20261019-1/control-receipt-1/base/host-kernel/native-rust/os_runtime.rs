// SPDX-License-Identifier: GPL-2.0
//! Linux ownership adapter for unbooted native IHK OS instances.
//!
//! The registry excludes opens during construction and destruction. Each open
//! file owns a generation-checked lease; each instance owns its provider lease,
//! a Linux module reference and a physically contiguous, zeroed kmsg buffer.
//! The versioned backend receives only generation-checked, serialized calls.
//! The additive boot backend separates preparation from CPU-start effects.

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
    sync::{new_mutex, Arc, Mutex},
};

use super::{
    abi::{
        IhkKmsgBuffer, IHK_DEVICE_CREATE_OS, IHK_DEVICE_DESTROY_OS, IHK_OS_BOOT,
        IHK_OS_GET_BUILDID, IHK_OS_LOAD, IHK_OS_QUERY_STATUS, IHK_OS_SHUTDOWN, IHK_OS_STATUS,
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
pub(super) struct ProviderModule(*mut bindings::module);

impl ProviderModule {
    /// # Safety
    /// `module` must be a valid Linux module pointer whose allocation remains
    /// live throughout this call. A pinned control file or a registration lock
    /// excluding the owner's unregister/exit supplies that lifetime. It must
    /// never be a userspace value. A going-away module may refuse acquisition.
    pub(super) unsafe fn acquire(module: *mut bindings::module) -> Result<Self> {
        if module.is_null() {
            return Err(EINVAL);
        }
        // SAFETY: The caller keeps this Linux module allocation live for the call.
        if !unsafe { try_module_get(module.cast()) } {
            return Err(EBUSY);
        }
        Ok(Self(module))
    }
}

impl Drop for ProviderModule {
    fn drop(&mut self) {
        // SAFETY: This unique owner balances one successful try_module_get.
        // No callback into that module may continue after this final put.
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

    fn physical(&self) -> Result<u64> {
        // SAFETY: get_free_pages_noprof without HIGHMEM returned this owned
        // x86 direct-map allocation. Linux fixes the base before module init.
        let base = unsafe { bindings::page_offset_base };
        let physical = (self.0 as u64).checked_sub(base).ok_or(EIO)?;
        physical.checked_add(KMSG_BYTES as u64).ok_or(EIO)?;
        if physical % 4096 != 0 {
            return Err(EIO);
        }
        Ok(physical)
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

// SAFETY: Preparation receives only a live OS identity and IHK-owned physical
// kmsg scalars. It must finish every fallible preparation without starting a
// CPU or publishing guest work. All retained storage belongs to this generation.
type OsBackendPrepareBootV3 = unsafe extern "C" fn(u32, u64, u64, u64) -> i32;
// SAFETY: IHK publishes Booting first. Success requires full backend readiness;
// any other result retains all possibly reachable resources for proven cleanup.
// This callback cannot permit unload, assignment or reuse after a start effect.
type OsBackendStartBootV3 = unsafe extern "C" fn(u32, u64) -> i32;
// SAFETY: The callback runs under the per-OS operation lock after the
// registry has entered PHASE_DESTROYING/Shutdown. It must only perform the
// provider's shutdown attempt and return a Linux-style errno result.
type OsBackendShutdownV5 = unsafe extern "C" fn(u32, u64) -> i32;
/// v6 carries the effect boundary in-band.  Zero is a complete transaction;
/// a signed Linux errno is pre-effect; the high tag bit marks a post-effect
/// failure whose admission and registry state must remain closed.
type OsBackendShutdownV6 = unsafe extern "C" fn(u32, u64) -> i64;

const SHUTDOWN_V6_POST_EFFECT: i64 = 1_i64 << 62;
const SHUTDOWN_V6_PAYLOAD_MASK: i64 = 0xffff_ffff;

/// The transaction boundary is deliberately separate from the v5 C result.
/// v5 callbacks are rollback-safe: every nonzero result is pre-effect.  A
/// future teardown adapter may report a failure after its irreversible effect
/// using the post-effect variant, which keeps Shutdown and closed admission for a
/// same-generation retry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ShutdownCallbackOutcome {
    Complete,
    PreEffectFailure(i32),
    // Reserved for the future teardown adapter; v5 cannot produce this tag.
    #[allow(dead_code)]
    PostEffectFailure(i32),
}

fn shutdown_v5_outcome(result: i32) -> ShutdownCallbackOutcome {
    if result == 0 {
        ShutdownCallbackOutcome::Complete
    } else {
        ShutdownCallbackOutcome::PreEffectFailure(result)
    }
}

fn shutdown_v6_outcome(result: i64) -> ShutdownCallbackOutcome {
    if result == 0 {
        return ShutdownCallbackOutcome::Complete;
    }
    // Pre-effect Linux errno values are negative and therefore have all high
    // bits set when widened.  The tag is intentionally positive so this
    // range check cannot confuse an ordinary negative errno for post-effect.
    if result >= SHUTDOWN_V6_POST_EFFECT {
        let payload = (result & SHUTDOWN_V6_PAYLOAD_MASK) as u32 as i32;
        return ShutdownCallbackOutcome::PostEffectFailure(payload);
    }
    if (-4095..0).contains(&result) {
        ShutdownCallbackOutcome::PreEffectFailure(result as i32)
    } else {
        ShutdownCallbackOutcome::PreEffectFailure(-5)
    }
}

fn shutdown_errno(result: i32) -> i32 {
    if (-4095..0).contains(&result) {
        result
    } else {
        -5
    }
}

#[derive(Clone, Copy)]
struct OsBackendBootV3 {
    prepare: OsBackendPrepareBootV3,
    start: OsBackendStartBootV3,
    success_status: OsStatus,
}

#[derive(Clone, Copy)]
struct ApplicationCallbacks {
    open: super::application_abi::Open,
    invoke: super::application_abi::Invoke,
    close: super::application_abi::Close,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
    adopt_fork_scoped: Option<super::application_abi::ForkAdoptScopedV1>,
    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,
    fork_progress_payload: Option<super::application_abi::ForkProgressPayloadV1>,
    prepare_fork_ack: Option<super::application_abi::ForkPrepareAckV1>,
    fork_publication_verify: Option<super::application_abi::ForkPublicationVerifyV1>,
    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,
    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,
}

#[derive(Clone, Copy)]
struct OsBackend {
    ioctl: OsBackendIoctlV2,
    release: OsBackendReleaseV2,
    boot: Option<OsBackendBootV3>,
    application: Option<ApplicationCallbacks>,
    shutdown: Option<OsBackendShutdown>,
}

#[derive(Clone, Copy)]
enum OsBackendShutdown {
    V5(OsBackendShutdownV5),
    V6(OsBackendShutdownV6),
}

// The high bits close/poison admission; the low bits count every callback borrow
// and every callback context whose Drop will call provider code.  It deliberately
// does not replace OsLease: the latter pins the object for destruction, while
// this gate makes shutdown bounded instead of racing a still-live provider
// context.  All methods are atomic only and therefore may run under the OS
// operation mutex or in callback-adjacent paths without sleeping.
struct Admission {
    word: AtomicU32,
}

const ADMISSION_CLOSED: u32 = 1 << 31;
const ADMISSION_OVERFLOW: u32 = 1 << 30;
const ADMISSION_COUNT_MASK: u32 = !(ADMISSION_CLOSED | ADMISSION_OVERFLOW);

impl Admission {
    const fn new() -> Self {
        Self {
            word: AtomicU32::new(0),
        }
    }

    /// Acquire one callback/context admission.  A full count permanently
    /// closes and poisons the gate, rather than wrapping to zero and admitting
    /// a callback that shutdown could no longer observe.
    fn enter(&self) -> Result<AdmissionOwner> {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & (ADMISSION_CLOSED | ADMISSION_OVERFLOW) != 0 {
                return Err(EBUSY);
            }
            let count = current & ADMISSION_COUNT_MASK;
            if count == ADMISSION_COUNT_MASK {
                let _ = self.word.compare_exchange(
                    current,
                    current | ADMISSION_CLOSED | ADMISSION_OVERFLOW,
                    Ordering::AcqRel,
                    Ordering::Acquire,
                );
                return Err(EBUSY);
            }
            if self
                .word
                .compare_exchange(current, current + 1, Ordering::AcqRel, Ordering::Acquire)
                .is_ok()
            {
                return Ok(AdmissionOwner {
                    admission: ptr::from_ref(self),
                });
            }
        }
    }

    /// Close admission for one shutdown attempt. This is called only under the
    /// per-OS operation mutex, which is also the order used by serialized
    /// application/topology callbacks. An idle close left by an earlier
    /// successful shutdown can be claimed for cleanup retry after a failed
    /// reboot; an overflow poison can never be claimed or reopened.
    fn close_for_shutdown(&self) -> Result<ShutdownAdmission> {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & ADMISSION_OVERFLOW != 0 {
                return Err(EBUSY);
            }
            let count = current & ADMISSION_COUNT_MASK;
            if current & ADMISSION_CLOSED != 0 {
                if count != 0 {
                    return Err(EBUSY);
                }
                return Ok(ShutdownAdmission {
                    admission: ptr::from_ref(self),
                    reopen_on_drop: false,
                    armed: true,
                });
            }
            if self
                .word
                .compare_exchange(
                    current,
                    current | ADMISSION_CLOSED,
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .is_ok()
            {
                if count != 0 {
                    // The close was ours, so it is safe to undo immediately.
                    // Do not wait for drain: shutdown reports bounded EBUSY.
                    self.reopen_unpoisoned();
                    return Err(EBUSY);
                }
                return Ok(ShutdownAdmission {
                    admission: ptr::from_ref(self),
                    reopen_on_drop: true,
                    armed: true,
                });
            }
        }
    }

    /// Reopen a non-poisoned gate. Only a ShutdownAdmission that changed the
    /// gate from open to closed may call this on a pre-effect failure; a
    /// successful boot also calls it after Ready is committed.
    fn reopen_unpoisoned(&self) {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & ADMISSION_OVERFLOW != 0 {
                return;
            }
            if self
                .word
                .compare_exchange(
                    current,
                    current & !ADMISSION_CLOSED,
                    Ordering::Release,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                return;
            }
        }
    }

    fn is_closed(&self) -> bool {
        self.word.load(Ordering::Acquire) & ADMISSION_CLOSED != 0
    }
}

/// An exclusive shutdown-close claim. Its Drop restores admission only when
/// this attempt changed an open gate to closed. A retry that borrowed a prior
/// idle close leaves that close intact on failure, while a poisoned gate stays
/// closed in either case.
#[must_use = "a shutdown close claim must commit or restore admission"]
struct ShutdownAdmission {
    admission: *const Admission,
    reopen_on_drop: bool,
    armed: bool,
}

impl ShutdownAdmission {
    /// Leave the gate closed after the successful shutdown effect/registry
    /// commit, or after an impossible post-effect registry corruption.
    fn commit(mut self) {
        self.armed = false;
    }
}

impl Drop for ShutdownAdmission {
    fn drop(&mut self) {
        if !self.armed || !self.reopen_on_drop {
            return;
        }
        // SAFETY: The operation mutex and caller's OsLease retain the object
        // through the complete shutdown transaction.
        unsafe { &*self.admission }.reopen_unpoisoned();
    }
}

/// Finish one shutdown transaction at its explicit effect boundary.  The v5
/// adapter below supplies only `Complete` or `PreEffectFailure`; the
/// post-effect arm is intentionally available for the reviewed future
/// teardown adapter and is the only path that marks the registry irreversible.
fn finish_shutdown(
    mut guard: super::os_registry::ShutdownGuard<'_>,
    admission: ShutdownAdmission,
    outcome: ShutdownCallbackOutcome,
) -> i32 {
    match outcome {
        ShutdownCallbackOutcome::Complete => match guard.commit() {
            Ok(()) => {
                admission.commit();
                0
            }
            Err(error) => {
                // A completed callback is already post-effect.  Keep
                // admission closed even if registry publication is corrupt.
                admission.commit();
                error.errno()
            }
        },
        ShutdownCallbackOutcome::PreEffectFailure(result) => shutdown_errno(result),
        ShutdownCallbackOutcome::PostEffectFailure(result) => {
            // The callback declared an effect. Commit admission first so even
            // an unexpected registry word cannot reopen the callback surface.
            admission.commit();
            if let Err(error) = guard.mark_irreversible() {
                // ShutdownGuard may restore only the registry word on this
                // rejected publication. The effect boundary is still final:
                // the committed admission claim must remain closed while the
                // registry error is returned to the caller.
                return error.errno();
            }
            shutdown_errno(result)
        }
    }
}

/// The raw pointer is valid because every stored owner also holds the exact
/// `OsLease` that outlives it. Temporary owners borrow an object protected by
/// the caller's local `OsLease`. This keeps a resident owner allocation-free.
#[must_use = "an admitted callback/context must release its admission owner"]
struct AdmissionOwner {
    admission: *const Admission,
}

impl Drop for AdmissionOwner {
    fn drop(&mut self) {
        // SAFETY: See the type-level lifetime contract above. The object and
        // its Admission remain live until this owner has dropped.
        let admission = unsafe { &*self.admission };
        loop {
            let current = admission.word.load(Ordering::Acquire);
            let count = current & ADMISSION_COUNT_MASK;
            if count == 0 {
                // Never underflow into a false live count. This is reachable
                // only after a trusted owner lifetime violation.
                return;
            }
            if admission
                .word
                .compare_exchange(current, current - 1, Ordering::Release, Ordering::Relaxed)
                .is_ok()
            {
                return;
            }
        }
    }
}

struct OsObject {
    provider: DeviceHandle,
    // Published before the registry becomes live. Registry leases exclude
    // device_destroy, including while a backend borrows the parent kobject.
    node: AtomicPtr<bindings::device>,
    operations: Pin<Box<Mutex<()>>>,
    admission: Admission,
    forks: Pin<Box<Mutex<ForkPendingTable>>>,
    backend: Option<OsBackend>,
    _kmsg: KmsgPages,
    _provider_lease: DeviceOsLease<'static>,
    // Drop the kernel module pin after the logical provider reference.
    _provider_module: ProviderModule,
}

/// Owns the Linux character-device family. OS minors remain 0..64 even though
/// the allocated Linux major is dynamic. Only live instances get device nodes.
pub(crate) struct OsDeviceFamily {
    _services: super::os_service::Registry,
}

impl OsDeviceFamily {
    pub(crate) fn register() -> Result<Self> {
        let services = super::os_service::Registry::new()?;
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
        Ok(Self {
            _services: services,
        })
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
        (1, Some(ioctl), Some(release)) => OsBackend {
            ioctl,
            release,
            boot: None,
            application: None,
            shutdown: None,
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The caller supplies pinned module-resident callbacks. The
    // object stores only their copied identities and its own module reference.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Add boot preparation/start callbacks while retaining the v1/v2 contracts.
///
/// # Safety
/// The caller pins `owner`; all four callbacks belong to that module and obey
/// their exact generation, execution-context and resource-retention contracts.
// SAFETY: No pointer or callback reaches publication until the complete ABI
// tuple is checked and create_os has acquired the provider's module reference.
#[export_name = "ihk_os_create_unbooted_v3"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v3(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
) -> i64 {
    let backend = match (callback_abi, ioctl, release, prepare, start) {
        (1, Some(ioctl), Some(release), Some(prepare), Some(start)) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: OsStatus::Ready }),
            application: None,
            shutdown: None,
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The complete callback identities stay resident through the
    // provider module owner acquired before any OS object is published.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Add kernel application connections while retaining the v1/v2/v3 contracts.
///
/// # Safety
/// The caller pins owner and all seven callbacks have the declared signatures,
/// module lifetime and exact-generation ownership contracts.
#[export_name = "ihk_os_create_unbooted_v4"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v4(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
    ) {
        (
            1,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: OsStatus::Ready }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork: None,
                fork_progress: None,
                adopt_fork_scoped: None,
                prepare_fork_link: None,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: None,
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: Publication follows validation and acquisition of the callback
    // module owner, using the same create transaction as the retained versions.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Add the no-effect shutdown dispatch callback while retaining v1-v4 ABI
/// signatures and exports. The callback is invoked with the exact published
/// slot/generation and is rollback-safe until a later effect acknowledgement.
///
/// # Safety
/// `owner` is the trusted live native module owner retained by `create_os`'s
/// initial reference. All eight callbacks remain resident, use their declared
/// ABI without unwinding, and obey the existing ownership, concurrency, and
/// locking rules. `shutdown` receives the exact generation under the operation
/// lock; a nonzero result is pre-effect or rollback-safe, so it performs no
/// stop, drain, release, or visible teardown.
#[export_name = "ihk_os_create_unbooted_v5"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v5(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV5>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: OsStatus::Ready }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork: None,
                fork_progress: None,
                adopt_fork_scoped: None,
                prepare_fork_link: None,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V5(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and all eight ABI-correct resident callbacks are
    // transferred into its existing ownership/concurrency transaction.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Add the effect-aware shutdown callback while preserving the v5 ABI.
/// `shutdown` returns zero for complete success, a signed Linux errno for a
/// pre-effect failure, or `SHUTDOWN_V6_POST_EFFECT | (errno as u32)` after an
/// irreversible effect.  The latter keeps admission closed and retains the
/// exact generation for reconciliation/retry.
#[export_name = "ihk_os_create_unbooted_v6"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v6(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork: None,
                fork_progress: None,
                adopt_fork_scoped: None,
                prepare_fork_link: None,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v5.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Additive private application adoption registration. All v1-v6 layouts and
/// callback contracts remain unchanged; absence of adoption returns ENODEV.
/// # Safety
/// Same live provider ownership and callback-residency contract as v6.
#[export_name = "ihk_os_create_unbooted_v7"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v7(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork,
                fork_progress: None,
                adopt_fork_scoped: None,
                prepare_fork_link: None,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v6. The optional private adoption
    // callback adds no public operation or ownership-bearing Rust ABI.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Additive private completion registration; v7 and earlier signatures stay fixed.
/// # Safety
/// Same provider/module lifetime contract as v7 and the scoped progress ABI.
#[export_name = "ihk_os_create_unbooted_v8"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v8(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork,
                fork_progress,
                adopt_fork_scoped: None,
                prepare_fork_link: None,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v6. The optional private adoption
    // callback adds no public operation or ownership-bearing Rust ABI.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Additive scoped payload/link registration; earlier signatures remain fixed.
/// # Safety
/// Same module ownership as v8, plus borrowed payload/continuation contracts.
#[export_name = "ihk_os_create_unbooted_v9"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v9(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
    adopt_fork_scoped: Option<super::application_abi::ForkAdoptScopedV1>,
    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork,
                fork_progress,
                adopt_fork_scoped,
                prepare_fork_link,
                fork_progress_payload: None,
                prepare_fork_ack: None,
                fork_publication_verify: None,
                release_fork_ack: None,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v6. The optional private adoption
    // callback adds no public operation or ownership-bearing Rust ABI.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// Additive authenticated finalization registration; earlier signatures remain fixed.
/// # Safety
/// Same module ownership as v8, plus borrowed payload/continuation contracts.
#[export_name = "ihk_os_create_unbooted_v10"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v10(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
    adopt_fork_scoped: Option<super::application_abi::ForkAdoptScopedV1>,
    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,
    fork_progress_payload: Option<super::application_abi::ForkProgressPayloadV1>,
    prepare_fork_ack: Option<super::application_abi::ForkPrepareAckV1>,
    fork_publication_verify: Option<super::application_abi::ForkPublicationVerifyV1>,
    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork,
                fork_progress,
                adopt_fork_scoped,
                prepare_fork_link,
                fork_progress_payload,
                prepare_fork_ack,
                fork_publication_verify,
                release_fork_ack,
                prepare_fork_control: None,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v6. The optional private adoption
    // callback adds no public operation or ownership-bearing Rust ABI.
    match unsafe { create_os(provider_minor, owner.cast(), argument, Some(backend)) } {
        Ok(minor) => minor as i64,
        Err(error) => error.to_errno() as i64,
    }
}

/// # Safety
/// Same module ownership as v8, plus borrowed payload/continuation contracts.
#[export_name = "ihk_os_create_unbooted_v11"]
pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v11(
    provider_minor: u32,
    owner: *mut c_void,
    argument: u64,
    callback_abi: u32,
    ioctl: Option<OsBackendIoctlV2>,
    release: Option<OsBackendReleaseV2>,
    prepare: Option<OsBackendPrepareBootV3>,
    start: Option<OsBackendStartBootV3>,
    open: Option<super::application_abi::Open>,
    invoke: Option<super::application_abi::Invoke>,
    close: Option<super::application_abi::Close>,
    shutdown: Option<OsBackendShutdownV6>,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
    adopt_fork_scoped: Option<super::application_abi::ForkAdoptScopedV1>,
    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,
    fork_progress_payload: Option<super::application_abi::ForkProgressPayloadV1>,
    prepare_fork_ack: Option<super::application_abi::ForkPrepareAckV1>,
    fork_publication_verify: Option<super::application_abi::ForkPublicationVerifyV1>,
    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,
    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,
) -> i64 {
    let backend = match (
        callback_abi,
        ioctl,
        release,
        prepare,
        start,
        open,
        invoke,
        close,
        shutdown,
    ) {
        (
            1 | 2,
            Some(ioctl),
            Some(release),
            Some(prepare),
            Some(start),
            Some(open),
            Some(invoke),
            Some(close),
            Some(shutdown),
        ) => OsBackend {
            ioctl,
            release,
            boot: Some(OsBackendBootV3 { prepare, start, success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready } }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
                adopt_fork,
                fork_progress,
                adopt_fork_scoped,
                prepare_fork_link,
                fork_progress_payload,
                prepare_fork_ack,
                fork_publication_verify,
                release_fork_ack,
                prepare_fork_control,
            }),
            shutdown: Some(OsBackendShutdown::V6(shutdown)),
        },
        _ => return EINVAL.to_errno() as i64,
    };
    // SAFETY: The validated trusted owner is retained through create_os's
    // initial reference, and every v6 callback remains resident for the
    // complete OS lifetime exactly as with v6. The optional private adoption
    // callback adds no public operation or ownership-bearing Rust ABI.
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
            node: AtomicPtr::new(ptr::null_mut()),
            operations: Box::pin_init(new_mutex!(()), GFP_KERNEL)?,
            admission: Admission::new(),
            forks: Box::pin_init(new_mutex!(ForkPendingTable::new()), GFP_KERNEL)?,
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
    // SAFETY: The reserved registry slot excludes readers until commit. The
    // successful device_create owns the registration until destroy_os.
    unsafe { (*object).node.store(node.cast(), Ordering::Release) };
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
    assert!(!object_ref
        .node
        .swap(ptr::null_mut(), Ordering::AcqRel)
        .is_null());
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

// SAFETY: Only a synchronous kernel caller supplies this function and context.
// The second argument borrows the real mcos device's Linux kobject while an
// exact-generation OsLease excludes unregister. Neither Rust layout nor a user
// or guest address crosses this callback boundary.
type OsKobjectCallbackV1 = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;

/// Borrow the real OS device without taking its operation mutex again.
///
/// # Safety
/// The caller pins its callback code and context through the synchronous call.
/// It must not retain the borrowed pointer or reenter OS operations. A created
/// Linux child must own its parent reference and retire before the backend's
/// release callback succeeds and before the child's module can unload. Holding
/// an OsLease for the entire child lifetime would prevent that release callback
/// from ever running; only this short borrow owns an additional registry lease.
#[export_name = "ihk_os_with_kobject_v1"]
pub(crate) unsafe extern "C" fn ihk_os_with_kobject_v1(
    slot: u32,
    generation: u64,
    callback_abi: u32,
    context: *mut c_void,
    callback: Option<OsKobjectCallbackV1>,
) -> i32 {
    if callback_abi != 1 || callback.is_none() {
        return EINVAL.to_errno();
    }
    let result = (|| -> Result<i32> {
        let handle = OS_REGISTRY
            .resolve_minor(slot as usize)
            .map_err(|error| errno(error.errno()))?;
        if handle.generation() != generation {
            return Err(errno(-116));
        }
        // Acquisition rechecks generation atomically against destruction and
        // minor reuse between resolve_minor and this compare/exchange.
        let _lease = OS_REGISTRY
            .acquire(handle)
            .map_err(|error| errno(error.errno()))?;
        let object = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        assert!(!object.is_null());
        // Hold admission until the foreign callback returns. Shutdown closes
        // this gate before its provider callback and returns EBUSY rather than
        // racing a borrowed kobject or its callback context.
        // SAFETY: The exact-generation registry lease retains the published,
        // initialized, aligned, nonnull OsObject and its admission field
        // through this callback and its drop. Admission excludes shutdown but
        // is not the pointer-lifetime proof; the lease and field drop order are.
        let _admission = unsafe { &*object }.admission.enter()?;
        // SAFETY: The lease keeps this exact object and registered device live.
        // Only form a raw field pointer: Linux owns the device's mutable data.
        let node = unsafe { (*object).node.load(Ordering::Acquire) };
        assert!(!node.is_null());
        // SAFETY: The same registry lease retains the Linux device allocation
        // and embedded kobject. addr_of_mut forms only the raw kobject field
        // pointer; it neither dereferences nor aliases Linux-owned mutable data.
        let parent = unsafe { ptr::addr_of_mut!((*node).kobj) };
        // SAFETY: The caller owns callback/context and obeys the borrowed-parent
        // contract above. No operation mutex is acquired across reentry from a
        // backend that already holds it during preparation or request handling.
        let status = unsafe { callback.unwrap()(context, parent.cast()) };
        if (-4095..=0).contains(&status) {
            Ok(status)
        } else {
            Err(EIO)
        }
    })();
    result.unwrap_or_else(|error| error.to_errno())
}

// Fields drop in declaration order: the service and its admission owner drop
// while the exact OS lease still prevents destruction, minor reuse and provider
// module release.
struct OsFile {
    service: Pin<Box<Mutex<Option<AttachedFileService>>>>,
    lease: OsLease<'static>,
}

// Keep the service callback context before its resident admission owner. The
// close callback therefore runs while shutdown still observes this file as
// busy, and before the later OS registry/module lease can be released.
struct AttachedFileService {
    service: super::os_service::FileService,
    _admission: AdmissionOwner,
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
    let service = match Box::pin_init(new_mutex!(None), GFP_KERNEL) {
        Ok(service) => service,
        Err(_) => return -12,
    };
    let context = match Box::new(OsFile { service, lease }, GFP_KERNEL) {
        Ok(context) => context,
        Err(_) => return -12,
    };
    // SAFETY: Linux gives this open callback exclusive initialization of the
    // new file. Failure above drops the lease before leaving private_data alone.
    unsafe { (*file).private_data = Box::into_raw(context).cast() };
    0
}

// SAFETY: Linux calls release once after the final file reference. No ioctl
// can still borrow the private lease, and .owner keeps this module resident.
unsafe extern "C" fn os_release(_inode: *mut bindings::inode, file: *mut bindings::file) -> i32 {
    // SAFETY: This is the exact Box installed by a successful os_open, reclaimed
    // once. Linux excludes concurrent use at final file release.
    unsafe {
        let context = (*file).private_data.cast::<OsFile>();
        (*file).private_data = ptr::null_mut();
        drop(Box::from_raw(context));
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
    let context = unsafe { &*((*file).private_data.cast::<OsFile>()) };
    let lease = &context.lease;
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
    if super::service_abi::handles(command) {
        // No OS operation lock may cross a blocking application callback. The
        // resident admission owner prevents shutdown from racing this attached
        // callback context, while the file lease still prevents destruction.
        let (callback, service_context) = {
            let mut service = context.service.lock();
            if service.is_none() {
                let admission = match object.admission.enter() {
                    Ok(admission) => admission,
                    Err(error) => return error.to_errno() as core::ffi::c_long,
                };
                match OS_REGISTRY.snapshot(handle) {
                    Ok(snapshot)
                        if matches!(snapshot.status, OsStatus::Ready | OsStatus::Running) => {}
                    Ok(_) => return EBUSY.to_errno() as core::ffi::c_long,
                    Err(error) => return error.errno() as core::ffi::c_long,
                }
                match super::os_service::FileService::open(
                    handle.minor() as u32,
                    handle.generation(),
                ) {
                    Ok(attached) => {
                        *service = Some(AttachedFileService {
                            service: attached,
                            _admission: admission,
                        })
                    }
                    Err(error) => return error.to_errno() as core::ffi::c_long,
                }
            }
            // SAFETY: Published service ownership cannot change until final
            // file release. Linux pins this file for the entire ioctl below.
            unsafe { service.as_ref().unwrap().service.borrowed_call() }
        };
        // SAFETY: The file owns the context and module pin; publication guards
        // have ended. The argument is only a borrowed user value for this call.
        let status = unsafe { callback(service_context, command, argument, u32::from(compat)) };
        return if status < -4095 {
            EIO.to_errno() as core::ffi::c_long
        } else {
            status as core::ffi::c_long
        };
    }
    let _operation = object.operations.lock();
    // Shutdown is the sole operation permitted outside the NotBooted-only
    // generic gate. It atomically closes admission before publishing the
    // registry Shutdown/DESTROYING transaction and invoking its callback.
    if command == IHK_OS_SHUTDOWN {
        let snapshot = match OS_REGISTRY.snapshot(handle) {
            Ok(snapshot) => snapshot,
            Err(error) => return error.errno() as core::ffi::c_long,
        };
        if snapshot.status == OsStatus::NotBooted {
            return 0;
        }
        let Some(backend) = object.backend else {
            return EINVAL.to_errno() as core::ffi::c_long;
        };
        let Some(shutdown) = backend.shutdown else {
            // ENOSYS is the defined fail-closed result for v1-v4 providers.
            return -38;
        };
        let admission = match object.admission.close_for_shutdown() {
            Ok(admission) => admission,
            Err(error) => return error.to_errno() as core::ffi::c_long,
        };
        let guard = match OS_REGISTRY.begin_shutdown(handle) {
            Ok(guard) => guard,
            Err(error) => return error.errno() as core::ffi::c_long,
        };
        // SAFETY: The lease, operation lock and provider module owner pin the
        // exact callback and generation. v5 remains rollback-safe; v6 carries
        // an explicit post-effect tag so a STOP/drain failure cannot reopen
        // admission or resurrect the registry's live state.
        let outcome = match shutdown {
            OsBackendShutdown::V5(callback) => {
                let result = unsafe { callback(handle.minor() as u32, handle.generation()) };
                shutdown_v5_outcome(result)
            }
            OsBackendShutdown::V6(callback) => {
                let result = unsafe { callback(handle.minor() as u32, handle.generation()) };
                shutdown_v6_outcome(result)
            }
        };
        let result = finish_shutdown(guard, admission, outcome);
        return result as core::ffi::c_long;
    }
    // The immutable compatibility ID is also available on a booted OS, without
    // creating an application service. Resource assignment remains restricted
    // to the initial state, under the same lock as load/boot transitions.
    match OS_REGISTRY.snapshot(handle) {
        Ok(snapshot) if command == IHK_OS_GET_BUILDID || snapshot.status == OsStatus::NotBooted => {
        }
        Ok(_) => return EBUSY.to_errno() as core::ffi::c_long,
        Err(error) => return error.errno() as core::ffi::c_long,
    }
    let Some(backend) = object.backend else {
        return EINVAL.to_errno() as core::ffi::c_long;
    };
    if command == IHK_OS_BOOT && backend.boot.is_some() {
        let boot = backend.boot.unwrap();
        let physical = match object._kmsg.physical() {
            Ok(physical) => physical,
            Err(error) => return error.to_errno() as core::ffi::c_long,
        };
        // SAFETY: The file lease and operation lock retain the exact OS,
        // backend code and kmsg allocation. User ioctl arguments do not enter
        // this callback. No CPU-start effect is allowed during preparation.
        let prepared = unsafe {
            (boot.prepare)(
                handle.minor() as u32,
                handle.generation(),
                physical,
                KMSG_BYTES as u64,
            )
        };
        if prepared != 0 {
            return if (-4095..0).contains(&prepared) {
                prepared as core::ffi::c_long
            } else {
                EIO.to_errno() as core::ffi::c_long
            };
        }
        if let Err(error) = OS_REGISTRY.transition(handle, OsStatus::Booting) {
            return error.errno() as core::ffi::c_long;
        }
        // SAFETY: Booting is visible before the first possible CPU effect.
        // This same operation lock excludes resource changes and subsequent
        // starts. Every uncertain result leaves the instance non-destroyable.
        let started = unsafe { (boot.start)(handle.minor() as u32, handle.generation()) };
        let state = if started == 0 {
            boot.success_status
        } else {
            OsStatus::Failed
        };
        if let Err(error) = OS_REGISTRY.transition(handle, state) {
            return error.errno() as core::ffi::c_long;
        }
        // A successful reboot after committed shutdown makes the normal
        // callback surface visible again. Failed boot leaves a formerly closed
        // gate closed, so it cannot expose new service/application callbacks.
        if started == 0 && object.admission.is_closed() {
            object.admission.reopen_unpoisoned();
        }
        return if (-4095..=0).contains(&started) {
            started as core::ffi::c_long
        } else {
            EIO.to_errno() as core::ffi::c_long
        };
    }
    // Every ordinary backend ioctl has an admission owner throughout the
    // callback. Take it before a Loading transition so a post-shutdown closed
    // gate cannot strand the registry in Loading without invoking its backend.
    let _admission = match object.admission.enter() {
        Ok(admission) => admission,
        Err(error) => return error.to_errno() as core::ffi::c_long,
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

struct BackendApplication {
    context: ptr::NonNull<c_void>,
    callbacks: ApplicationCallbacks,
}

// SAFETY: The registered callback contract supplies a concurrency-safe opaque
// owner. Only invoke borrows it; final Drop follows the last such borrow.
unsafe impl Send for BackendApplication {}
// SAFETY: The same registered opaque owner permits shared references; invoke
// serializes its callback contract, and final Drop follows every such borrow.
unsafe impl Sync for BackendApplication {}

impl Drop for BackendApplication {
    fn drop(&mut self) {
        // SAFETY: This successful open is uniquely owned and its OS/module
        // lease is the later-dropping field of ApplicationConnection.
        unsafe { (self.callbacks.close)(self.context.as_ptr()) };
    }
}

struct ApplicationConnection {
    backend: BackendApplication,
    // BackendApplication drops first so its close callback retains admission;
    // this owner then drops before the exact OS lease/module release.
    _admission: AdmissionOwner,
    _lease: OsLease<'static>,
}

/// # Safety
/// Output is exclusive kernel storage. The dependency caller pins IHK until
/// close; the returned opaque connection may never be exposed to userspace.
#[export_name = "ihk_os_application_open_v1"]
pub(crate) unsafe extern "C" fn open_application(
    slot: u32,
    generation: u64,
    version: u32,
    pid: i32,
    output: *mut *mut c_void,
) -> i32 {
    if output.is_null() {
        return EINVAL.to_errno();
    }
    // SAFETY: The caller grants this writable kernel output for the call.
    unsafe { output.write(ptr::null_mut()) };
    let result = (|| -> Result<Box<ApplicationConnection>> {
        if version != super::application_abi::VERSION || pid <= 0 {
            return Err(EINVAL);
        }
        let handle = OS_REGISTRY
            .resolve_minor(slot as usize)
            .map_err(|error| errno(error.errno()))?;
        if handle.generation() != generation {
            return Err(errno(-116));
        }
        let lease = OS_REGISTRY
            .acquire(handle)
            .map_err(|error| errno(error.errno()))?;
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        assert!(!raw.is_null());
        // SAFETY: The exact lease excludes OS/backend object destruction.
        let object = unsafe { &*raw };
        // Keep the legacy serialized Open contract. Taking operations before
        // admission matches shutdown's operations -> close order, so shutdown
        // cannot wait on a contender that already holds admission.
        let _operation = object.operations.lock();
        // This owner stays with the opaque connection, including every invoke
        // and its close callback. Shutdown therefore returns EBUSY instead of
        // racing any application context that escaped open.
        let admission = object.admission.enter()?;
        let backend = {
            let snapshot = OS_REGISTRY
                .snapshot(handle)
                .map_err(|error| errno(error.errno()))?;
            if !matches!(snapshot.status, OsStatus::Ready | OsStatus::Running) {
                return Err(EBUSY);
            }
            let callbacks = object
                .backend
                .and_then(|backend| backend.application)
                .ok_or(ENODEV)?;
            let mut context = ptr::null_mut();
            // SAFETY: The lease and admission pin all callbacks. The legacy
            // operation mutex continues to serialize Open with provider state.
            let status = unsafe { (callbacks.open)(slot, generation, pid, &mut context) };
            if status != 0 {
                if !context.is_null() {
                    // SAFETY: A misbehaving trusted callback still transferred
                    // its owned output; close it while the lease remains live.
                    unsafe { (callbacks.close)(context) };
                }
                return Err(errno(status));
            }
            BackendApplication {
                context: ptr::NonNull::new(context).ok_or(EIO)?,
                callbacks,
            }
        };
        // Preserve the legacy lock scope: Open is serialized, but fallible
        // connection allocation and its BackendApplication cleanup are not.
        // A provider Close may reenter a serialized topology query.
        drop(_operation);
        // Box allocation failure drops the backend before the retained lease.
        Ok(Box::new(
            ApplicationConnection {
                backend,
                _admission: admission,
                _lease: lease,
            },
            GFP_KERNEL,
        )?)
    })();
    match result {
        Ok(connection) => {
            // SAFETY: Transfer the sole allocation to the dependency caller.
            unsafe { output.write(Box::into_raw(connection).cast()) };
            0
        }
        Err(error) => error.to_errno(),
    }
}

/// # Safety
/// Context is a live successful open; the caller excludes close during this
/// call and supplies only command-defined kernel storage, never user addresses.
#[export_name = "ihk_os_application_invoke_v1"]
pub(crate) unsafe extern "C" fn invoke_application(
    context: *mut c_void,
    command: u32,
    buffer: *mut u8,
    bytes: usize,
) -> i64 {
    if context.is_null() {
        return EINVAL.to_errno() as i64;
    }
    // SAFETY: The caller retains this exact connection and its OS/module lease.
    let connection = unsafe { &*context.cast::<ApplicationConnection>() };
    // SAFETY: No OS operation/publication lock spans this potentially blocking
    // operation. The backend owns any work remaining after the call returns.
    unsafe {
        (connection.backend.callbacks.invoke)(
            connection.backend.context.as_ptr(),
            command,
            buffer,
            bytes,
        )
    }
}

// BEGIN PRIVATE FORK IHK PROVIDER BRIDGE
// A pending entry owns independent exact-generation admission/OS/provider
// ownership. All table access uses OsObject.forks; lookup clones an Arc while
// holding that mutex before it may release the guard. No raw table pointer is
// read outside exclusion. A monotonic epoch distinguishes every slot reuse.
const FORK_PROVIDER_CAPACITY: usize = 64;
const FORK_PROVIDER_PENDING: u32 = 1;
const FORK_PROVIDER_QUARANTINED: u32 = 2;
const FORK_PROVIDER_HOST_REVOKED: u32 = 3;
const FORK_PROVIDER_BUSY: u32 = 4;
static FORK_PROVIDER_OWNER_COUNT: AtomicU32 = AtomicU32::new(0);

struct ForkProviderCapacity;
impl ForkProviderCapacity {
    fn reserve() -> Result<Self> {
        FORK_PROVIDER_OWNER_COUNT.fetch_update(Ordering::AcqRel, Ordering::Acquire,
            |count| (count < FORK_PROVIDER_CAPACITY as u32).then(|| count + 1))
            .map_err(|_| EBUSY)?;
        Ok(Self)
    }
}
impl Drop for ForkProviderCapacity {
    fn drop(&mut self) {
        let old = FORK_PROVIDER_OWNER_COUNT.fetch_sub(1, Ordering::Release);
        assert!(old > 0);
    }
}

struct ForkProviderOwner {
    _admission: AdmissionOwner,
    _lease: OsLease<'static>,
    // Release aggregate capacity only AFTER admission and OS/module ownership.
    _capacity: ForkProviderCapacity,
}
// SAFETY: The exact lease pins Admission's address. All owner operations are
// immutable or atomic; final field destruction follows the last Arc borrow.
unsafe impl Send for ForkProviderOwner {}
// SAFETY: The pinned registry and admission support concurrent atomic borrows.
unsafe impl Sync for ForkProviderOwner {}

struct ForkConsumerCapsule {
    context: AtomicPtr<c_void>,
    destroy: super::application_abi::ForkCapsuleDestroyV1,
    verify: super::application_abi::ForkVerifyV1,
    accept: super::application_abi::ForkCapsuleAcceptV1,
    _link: Option<super::application_abi::ForkCapsuleLinkV1>,
    // Drop invokes the consumer first; this field releases its pin afterwards
    // from IHK code, with the independent provider owner still live.
    _module: ProviderModule,
}
// SAFETY: The trusted constructor supplies one owned concurrency-safe context;
// exact pending claims serialize verify/accept, and Arc pins final destruction.
unsafe impl Send for ForkConsumerCapsule {}
// SAFETY: Context access is confined to the exclusive epoch claim callbacks.
unsafe impl Sync for ForkConsumerCapsule {}
impl Drop for ForkConsumerCapsule {
    fn drop(&mut self) {
        // SAFETY: IHK uniquely owns the successful constructor output. Every
        // callback borrow has ended, no table/MM/slots guard is live, and the
        // later-dropping module field still pins this exact consumer code.
        let context = self.context.load(Ordering::Acquire);
        if !context.is_null() { unsafe { (self.destroy)(context) }; }
    }
}
#[derive(Clone, Copy, Eq, PartialEq)]
enum ForkReceiptPhase { Reserved, Acknowledged, Published, Finished }

// Storage is allocated and installed BEFORE Construct transfers any context.
// Only scoped Abort/future authenticated Complete may consume that context.
// No ordinary Drop invokes foreign code or treats a failed cleanup as success.
struct ForkPayloadCapsule {
    context: AtomicPtr<c_void>,
    abort: super::application_abi::ForkPayloadDropV1,
    _complete: super::application_abi::ForkPayloadDropV1,
}
// SAFETY: Context is opaque; the exclusive initializing scope or exact BUSY
// claim serializes callbacks, and its owner pins the provider module.
unsafe impl Send for ForkPayloadCapsule {}
// SAFETY: Scalar context publication is atomic; no unsynchronized dereference.
unsafe impl Sync for ForkPayloadCapsule {}

struct ForkPendingEntry {
    identity: Option<super::application_abi::ForkIdentityV1>,
    epoch: u64,
    phase: u32,
    host_revoked: bool,
    guest_released: bool,
    final_published: bool,
    consumer_accepted: bool,
    payload_completed: bool,
    backend_released: bool,
    attempted: bool,
    receipt_index: Option<usize>,
    capsule: Option<Arc<ForkConsumerCapsule>>,
    payload: Option<Arc<ForkPayloadCapsule>>,
    child_context: usize,
    // Any entry teardown, including conservative reconciliation, destroys the
    // consumer capsule/module before releasing independent provider ownership.
    owner: Arc<ForkProviderOwner>,
}
#[derive(Clone, Copy)]
struct ForkCompletedReceipt {
    identity: super::application_abi::ForkIdentityV1,
    child_context: usize,
    epoch: u64,
    phase: ForkReceiptPhase,
}
struct ForkPendingTable {
    next_epoch: u64,
    entries: [Option<ForkPendingEntry>; FORK_PROVIDER_CAPACITY],
    completed: [Option<ForkCompletedReceipt>; FORK_PROVIDER_CAPACITY],
}
impl ForkPendingTable {
    fn new() -> Self {
        Self { next_epoch: 0, entries: [const { None }; FORK_PROVIDER_CAPACITY],
            completed: [None; FORK_PROVIDER_CAPACITY] }
    }
}

struct ForkProviderReservation {
    object: *const OsObject,
    index: usize,
    epoch: u64,
    owner: Arc<ForkProviderOwner>,
    active: bool,
}
impl ForkProviderReservation {
    fn reserve(object: &OsObject, owner: Arc<ForkProviderOwner>, child_context: usize) -> Result<Self> {
        let mut table = object.forks.lock();
        let index = table.entries.iter().position(Option::is_none).ok_or(EBUSY)?;
        let epoch = table.next_epoch.checked_add(1).ok_or(EOVERFLOW)?;
        table.next_epoch = epoch;
        table.entries[index] = Some(ForkPendingEntry {
            owner: owner.clone(), identity: None, epoch, phase: 0,
            host_revoked: false, guest_released: false, final_published: false,
            consumer_accepted: false, payload_completed: false, backend_released: false,
            attempted: false, receipt_index: None, capsule: None, payload: None, child_context,
        });
        drop(table);
        Ok(Self { object: ptr::from_ref(object), index, epoch, owner, active: true })
    }
    fn bind_identity(&self, identity: super::application_abi::ForkIdentityV1) -> Result {
        // SAFETY: Our owner lease pins the object/table until this Arc drops.
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || !Arc::ptr_eq(&entry.owner, &self.owner)
            || entry.phase != 0 || entry.identity.is_some()
        { return Err(EIO); }
        entry.identity = Some(identity);
        Ok(())
    }
    fn retain(mut self, quarantined: bool) {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        if let Some(entry) = table.entries[self.index].as_mut() {
            if entry.epoch == self.epoch && Arc::ptr_eq(&entry.owner, &self.owner) {
                if self.active && entry.phase == 0 {
                    entry.phase = if quarantined { FORK_PROVIDER_QUARANTINED } else { FORK_PROVIDER_PENDING };
                } else if !self.active && quarantined && entry.phase == FORK_PROVIDER_PENDING {
                    // Scoped ready may publish before backend return. Never
                    // overwrite a concurrent BUSY/advanced completion claim.
                    entry.phase = FORK_PROVIDER_QUARANTINED;
                }
            }
        }
        self.active = false;
    }
}
impl Drop for ForkProviderReservation {
    fn drop(&mut self) {
        if !self.active { return; }
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            if table.entries[self.index].as_ref().is_some_and(|entry|
                entry.epoch == self.epoch && Arc::ptr_eq(&entry.owner, &self.owner) && entry.phase == 0)
            {
                if table.entries[self.index].as_ref().unwrap().payload.is_some() {
                    // No exceptional preseal return may orphan a live carrier.
                    // Keep its exact reachable capsule and real owner until
                    // explicit scoped rollback consumed and detached it.
                    table.entries[self.index].as_mut().unwrap().phase = FORK_PROVIDER_QUARANTINED;
                    None
                } else { table.entries[self.index].take() }
            } else { None }
        };
        // All ownership destructors run after the table guard/callback ends.
        drop(removed);
    }
}

struct ForkPayloadScopeStack {
    reservation: *mut ForkProviderReservation,
    descriptor: *mut super::application_abi::ForkPayloadScopeV1,
    consumer: *const ForkConsumerScope,
    constructing: bool,
    cleaning: bool,
    rollback_ready: bool,
    // Default true: only the actual provider's completed scoped rollback may
    // clear uncertainty after removing claims/restoring its exact response.
    uncertain: bool,
}

unsafe fn fork_payload_scope_binding(scope: *mut super::application_abi::ForkPayloadScopeV1)
    -> Result<*mut ForkPayloadScopeStack>
{
    use super::application_abi::{ForkPayloadScopeV1, VERSION};
    if scope.is_null() { return Err(EINVAL); }
    let descriptor = unsafe { &*scope };
    if descriptor.version != VERSION || descriptor.bytes as usize != core::mem::size_of::<ForkPayloadScopeV1>()
        || descriptor.reserved0 != 0 || descriptor.context.is_null()
        || descriptor.attach.map(|f| f as usize) != Some(fork_payload_attach_scope as super::application_abi::ForkPayloadAttachV1 as usize)
    { return Err(EINVAL); }
    // SAFETY: This is an IHK-created stack context borrowed synchronously by
    // the registered provider, never wire/user storage or an owned lease.
    let stack = unsafe { &*descriptor.context.cast::<ForkPayloadScopeStack>() };
    if stack.descriptor != scope || stack.reservation.is_null() || stack.consumer.is_null() { return Err(EACCES); }
    let reservation = unsafe { &*stack.reservation };
    let handle = reservation.owner._lease.handle();
    if descriptor.slot as usize != handle.minor() || descriptor.generation != handle.generation()
        || descriptor.epoch != reservation.epoch || !reservation.active
    { return Err(EACCES); }
    Ok(descriptor.context.cast())
}

unsafe fn abort_fork_payload_scope(raw: *mut ForkPayloadScopeStack, rollback_ready: bool) -> Result {
    let stack = unsafe { &mut *raw };
    if stack.constructing || stack.cleaning { return Err(EBUSY); }
    let consumer = unsafe { &*stack.consumer };
    if consumer.active || consumer.sealed || consumer.uncertain { return Err(EBUSY); }
    let reservation = unsafe { &*stack.reservation };
    let object = unsafe { &*reservation.object };
    let capsule = {
        let table = object.forks.lock();
        let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0
            || !Arc::ptr_eq(&entry.owner, &reservation.owner)
        { return Err(EACCES); }
        entry.payload.clone()
    };
    if let Some(capsule) = capsule {
        let context = capsule.context.load(Ordering::Acquire);
        if !context.is_null() {
            // No MM/table/slots/registry guard spans foreign cleanup. The
            // original independent provider owner pins its code through return.
            stack.cleaning = true;
            // End the exclusive stack borrow BEFORE foreign code can reenter
            // this synchronous scope; reacquire only after callback return.
            let status = unsafe { (capsule.abort)(context) };
            let stack = unsafe { &mut *raw };
            stack.cleaning = false;
            if status != 0 {
                stack.uncertain = true;
                return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
            }
            capsule.context.store(ptr::null_mut(), Ordering::Release);
        }
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner)
                || !entry.payload.as_ref().is_some_and(|stored| Arc::ptr_eq(stored, &capsule))
            { return Err(EACCES); }
            entry.payload.take()
        };
        drop(removed);
        drop(capsule);
    }
    if rollback_ready {
        let stack = unsafe { &mut *raw };
        stack.rollback_ready = true;
        stack.uncertain = false;
    }
    Ok(())
}

unsafe extern "C" fn fork_payload_attach_scope(
    context: *mut c_void,
    construct: Option<super::application_abi::ForkPayloadConstructV1>, seed: *mut c_void,
    abort: Option<super::application_abi::ForkPayloadDropV1>,
    complete: Option<super::application_abi::ForkPayloadDropV1>, out: *mut *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        if context.is_null() || out.is_null() { return Err(EINVAL); }
        unsafe { out.write(ptr::null_mut()) };
        let descriptor = unsafe { (*context.cast::<ForkPayloadScopeStack>()).descriptor };
        let raw = unsafe { fork_payload_scope_binding(descriptor) }?;
        let stack = unsafe { &mut *raw };
        if raw.cast::<c_void>() != context || stack.constructing || stack.cleaning || stack.rollback_ready { return Err(EBUSY); }
        let consumer = unsafe { &*stack.consumer };
        if consumer.active || consumer.invoked || consumer.sealed || consumer.uncertain { return Err(EBUSY); }
        let construct = construct.ok_or(EINVAL)?;
        let abort = abort.ok_or(EINVAL)?;
        let complete = complete.ok_or(EINVAL)?;
        let reservation = unsafe { &*stack.reservation };
        let object = unsafe { &*reservation.object };
        {
            let table = object.forks.lock();
            let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.payload.is_some()
            { return Err(EBUSY); }
        }
        // Every fallible metadata allocation precedes owned context transfer.
        let capsule = Arc::new(ForkPayloadCapsule {
            context: AtomicPtr::new(ptr::null_mut()), abort, _complete: complete,
        }, GFP_KERNEL)?;
        {
            let mut table = object.forks.lock();
            let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.payload.is_some()
            { return Err(EBUSY); }
            entry.payload = Some(capsule.clone());
        }
        stack.constructing = true;
        let mut owned = ptr::null_mut();
        // No &mut stack borrow is kept across a potentially reentrant ctor.
        let status = unsafe { construct(seed, &mut owned) };
        // Capture even an error's non-NULL output into preallocated storage.
        capsule.context.store(owned, Ordering::Release);
        let stack = unsafe { &mut *raw };
        stack.constructing = false;
        if status != 0 || owned.is_null() {
            unsafe { abort_fork_payload_scope(raw, false) }?;
            return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
        }
        unsafe { out.write(owned) };
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Only the registered provider borrows this actual IHK stack scope. It has
/// cleared every payload pointer/borrow and restored its response/rollback
/// state, with provisional publication still frozen and no dependent guard.
/// No wire value or generic Drop may fabricate this rollback authority.
#[export_name = "ihk_os_application_abort_fork_payload_v1"]
pub(crate) unsafe extern "C" fn abort_fork_payload_application(
    scope: *mut super::application_abi::ForkPayloadScopeV1,
) -> i32 {
    let result = (|| -> Result {
        let stack = unsafe { fork_payload_scope_binding(scope) }?;
        unsafe { abort_fork_payload_scope(stack, true) }
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Called only by the actual registered provider after the MM callback/local
/// publication has returned, with its typed PreparedForkLease still prepared.
/// No dependent lock is live. This publishes IHK ownership before the SAME
/// slots-lock canonical first-write/READY transaction can permit first RET.
#[export_name = "ihk_os_application_ready_fork_payload_v1"]
pub(crate) unsafe extern "C" fn ready_fork_payload_application(
    scope: *mut super::application_abi::ForkPayloadScopeV1,
) -> i32 {
    let result = (|| -> Result {
        let raw = unsafe { fork_payload_scope_binding(scope) }?;
        let stack = unsafe { &mut *raw };
        if stack.constructing || stack.cleaning || stack.rollback_ready { return Err(EBUSY); }
        let consumer = unsafe { &*stack.consumer };
        if !consumer.invoked || consumer.active || !consumer.sealed || consumer.uncertain { return Err(EBUSY); }
        let reservation = unsafe { &mut *stack.reservation };
        let object = unsafe { &*reservation.object };
        let mut table = object.forks.lock();
        let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity.is_none()
            || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.attempted
            || entry.capsule.as_ref().is_none_or(|capsule| capsule.context.load(Ordering::Acquire).is_null())
            || entry.payload.as_ref().is_none_or(|capsule| capsule.context.load(Ordering::Acquire).is_null())
        { return Err(EBUSY); }
        let key = entry.identity.unwrap();
        if key.slot != consumer.slot || key.generation != consumer.generation
            || key.root != consumer.geometry.root || key.start != consumer.geometry.start
            || key.length != consumer.geometry.length
        { return Err(EACCES); }
        entry.phase = FORK_PROVIDER_PENDING;
        reservation.active = false;
        stack.uncertain = false;
        drop(table);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

struct ForkProviderClaim {
    object: *const OsObject,
    index: usize,
    epoch: u64,
    identity: super::application_abi::ForkIdentityV1,
    previous_phase: u32,
    guest_released: bool,
    attempted: bool,
    receipt_index: Option<usize>,
    // Capsule destruction/module_put precede the last provider owner release.
    capsule: Option<Arc<ForkConsumerCapsule>>,
    payload: Option<Arc<ForkPayloadCapsule>>,
    owner: Arc<ForkProviderOwner>,
    active: bool,
}
enum ForkClaimLookup { Pending(ForkProviderClaim), Completed }
impl ForkProviderClaim {
    // stage0 is private attachment/cancellation lookup, never a wire opcode.
    fn acquire(object: &OsObject, identity: super::application_abi::ForkIdentityV1,
        child_context: usize, stage: u32) -> Result<ForkClaimLookup>
    {
        let mut table = object.forks.lock();
        if stage == super::application_abi::FORK_GUEST_DESTROYED_V1
            && table.completed.iter().flatten().any(|receipt|
                receipt.identity == identity && receipt.child_context == child_context
                    && receipt.phase == ForkReceiptPhase::Finished)
        { return Ok(ForkClaimLookup::Completed); }
        let index = table.entries.iter().position(|entry| entry.as_ref().is_some_and(|entry|
            entry.identity == Some(identity) && entry.child_context == child_context)).ok_or(ENOENT)?;
        let entry = table.entries[index].as_ref().unwrap();
        if stage == super::application_abi::FORK_HOST_REVOKED_V1 && entry.host_revoked {
            return Ok(ForkClaimLookup::Completed);
        }
        if entry.phase == 0 || entry.phase == FORK_PROVIDER_BUSY
            || stage == super::application_abi::FORK_GUEST_DESTROYED_V1 && !entry.host_revoked
        { return Err(EBUSY); }
        if stage != 0 && entry.capsule.is_none() { return Err(ENODEV); }
        // Completion receipts have an independent lifetime from pending slots.
        // Reserve before the first revoke effect; Finished cells are never
        // evicted by pending-slot reuse. Until authenticated receipt retirement
        // exists, exhaustion deliberately retains ownership and fails closed.
        let receipt_index = if stage != 0 {
            if let Some(receipt_index) = entry.receipt_index {
                let receipt = table.completed[receipt_index].as_ref().ok_or(EIO)?;
                if receipt.epoch != entry.epoch || receipt.identity != identity
                    || receipt.child_context != child_context
                    || receipt.phase == ForkReceiptPhase::Finished
                { return Err(EIO); }
                Some(receipt_index)
            } else {
                if stage != super::application_abi::FORK_HOST_REVOKED_V1 { return Err(EIO); }
                let receipt_index = table.completed.iter().position(Option::is_none).ok_or(EBUSY)?;
                let epoch = entry.epoch;
                table.completed[receipt_index] = Some(ForkCompletedReceipt { identity, child_context,
                    epoch, phase: ForkReceiptPhase::Reserved });
                table.entries[index].as_mut().unwrap().receipt_index = Some(receipt_index);
                Some(receipt_index)
            }
        } else { entry.receipt_index };
        let entry = table.entries[index].as_mut().unwrap();
        let claim = Self { object: ptr::from_ref(object), index, epoch: entry.epoch,
            identity, previous_phase: entry.phase, guest_released: entry.guest_released,
            attempted: entry.attempted, receipt_index, capsule: entry.capsule.clone(), payload: entry.payload.clone(), owner: entry.owner.clone(), active: true };
        entry.phase = FORK_PROVIDER_BUSY;
        if stage == super::application_abi::FORK_HOST_REVOKED_V1 { entry.attempted = true; }
        drop(table);
        Ok(ForkClaimLookup::Pending(claim))
    }

    fn acquire_control(object: &OsObject, identity: super::application_abi::ForkIdentityV1,
        child_context: usize, epoch: u64) -> Result<Self> {
        let mut table = object.forks.lock();
        let index = table.entries.iter().position(|e| e.as_ref().is_some_and(|e|
            e.identity == Some(identity) && e.child_context == child_context && e.epoch == epoch)).ok_or(ENOENT)?;
        let entry = table.entries[index].as_mut().unwrap();
        if epoch == 0 || entry.phase != FORK_PROVIDER_PENDING || entry.host_revoked || entry.guest_released
            || entry.attempted || entry.capsule.is_none() || entry.payload.is_none()
            || entry.final_published || entry.consumer_accepted || entry.payload_completed || entry.backend_released
        { return Err(EBUSY); }
        let claim = Self { object: ptr::from_ref(object), index, epoch, identity,
            previous_phase: entry.phase, guest_released: entry.guest_released,
            attempted: entry.attempted, receipt_index: entry.receipt_index,
            capsule: entry.capsule.clone(), payload: entry.payload.clone(), owner: entry.owner.clone(), active: true };
        entry.phase = FORK_PROVIDER_BUSY;
        Ok(claim)
    }
    // Only for the strict park-only claim. A failed table identity check
    // cannot hand its original ownership to an unrelated/reused pending cell.
    // Keep every original owner/capsule/module pin on that uncertainty.
    fn restore_control(mut self) -> Result {
        let result = {
            let object = unsafe { &*self.object };
            let mut table = object.forks.lock();
            match table.entries[self.index].as_mut() {
                Some(entry) if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                    && Arc::ptr_eq(&entry.owner, &self.owner) => {
                    if entry.phase == FORK_PROVIDER_BUSY && self.previous_phase == FORK_PROVIDER_PENDING {
                        entry.phase = FORK_PROVIDER_PENDING;
                        self.active = false;
                        Ok(())
                    } else {
                        entry.phase = FORK_PROVIDER_QUARANTINED;
                        Err(EIO)
                    }
                },
                _ => Err(EIO),
            }
        };
        // No table/Remote/MM guard is held. Forgetting this original claim
        // retains its OS/admission/capsule/module owners; no foreign Drop or
        // arbitrary decrement may run on a mismatched/reused pending entry.
        if result.is_err() { core::mem::forget(self); }
        result
    }
    fn begin_link_attempt(&mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || entry.host_revoked || entry.guest_released || entry.capsule.is_none() || entry.payload.is_none()
        { return Err(EBUSY); }
        entry.attempted = true;
        self.attempted = true;
        Ok(())
    }
    fn restore(mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
        { return Err(EIO); }
        entry.phase = self.previous_phase;
        self.active = false;
        Ok(())
    }
    fn install_capsule(mut self, capsule: Arc<ForkConsumerCapsule>) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || entry.attempted || entry.capsule.is_some()
        { return Err(EBUSY); }
        entry.capsule = Some(capsule.clone());
        entry.phase = self.previous_phase;
        self.active = false;
        Ok(())
    }
    fn cancel_capsule(mut self) -> Result {
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
            if entry.epoch != self.epoch || entry.identity != Some(self.identity)
                || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
                || entry.attempted
            { return Err(EBUSY); }
            let removed = entry.capsule.take();
            entry.phase = self.previous_phase;
            removed
        };
        self.active = false;
        // The caller retains an independent live file/callback module owner
        // through return into consumer code. This cancels ONLY its unattempted
        // capsule; the pending root owner, identity and epoch remain intact.
        drop(removed);
        Ok(())
    }
    fn mark_guest_released(&mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
        { return Err(EIO); }
        if entry.receipt_index != self.receipt_index { return Err(EIO); }
        let receipt_index = self.receipt_index.ok_or(EIO)?;
        let receipt = table.completed[receipt_index].as_mut().ok_or(EIO)?;
        if receipt.epoch != self.epoch || receipt.identity != self.identity
            || receipt.phase != ForkReceiptPhase::Reserved
        { return Err(EIO); }
        // This durable exact key survives Accept failure. Retry must never
        // repeat the guest verifier, checked destructor or backend transition.
        receipt.phase = ForkReceiptPhase::Acknowledged;
        table.entries[self.index].as_mut().unwrap().guest_released = true;
        self.guest_released = true;
        Ok(())
    }
    fn finalization_state(&self) -> Result<(bool, bool, bool, bool)> {
        let object = unsafe { &*self.object };
        let table = object.forks.lock();
        let entry = table.entries[self.index].as_ref().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || !entry.host_revoked || !entry.guest_released { return Err(EBUSY); }
        Ok((entry.final_published, entry.consumer_accepted, entry.payload_completed, entry.backend_released))
    }
    fn mark_finalization_step(&mut self, step: u32) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || !entry.host_revoked || !entry.guest_released { return Err(EIO); }
        match step {
            0 => {
                if entry.final_published { return Ok(()); }
                let receipt_index = entry.receipt_index.ok_or(EIO)?;
                let receipt = table.completed[receipt_index].as_mut().ok_or(EIO)?;
                if receipt.epoch != self.epoch || receipt.identity != self.identity
                    || receipt.phase != ForkReceiptPhase::Acknowledged { return Err(EIO); }
                receipt.phase = ForkReceiptPhase::Published;
                table.entries[self.index].as_mut().unwrap().final_published = true;
            }
            1 if entry.final_published => entry.consumer_accepted = true,
            2 if entry.final_published && entry.consumer_accepted => {
                entry.payload_completed = true;
                entry.payload = None;
            }
            _ => return Err(EIO),
        }
        Ok(())
    }
    fn final_release_ready(&self) -> Result {
        let object = unsafe { &*self.object };
        let table = object.forks.lock();
        let entry = table.entries[self.index].as_ref().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || !entry.final_published || !entry.consumer_accepted || !entry.payload_completed
            || entry.payload.is_some() || entry.backend_released { return Err(EIO); }
        let receipt = table.completed[entry.receipt_index.ok_or(EIO)?].as_ref().ok_or(EIO)?;
        if receipt.epoch != self.epoch || receipt.identity != self.identity
            || receipt.phase != ForkReceiptPhase::Published { return Err(EIO); }
        Ok(())
    }
    // Every fallible check and all storage reservations precede ReleaseAck.
    // This exclusive BUSY claim forbids entry/cache reuse through its return;
    // the final commit is infallible unless that proved invariant is corrupt.
    fn finish_final_publication(mut self) {
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[self.index].as_mut().expect("BUSY final ACK entry disappeared");
            assert!(entry.epoch == self.epoch && entry.identity == Some(self.identity)
                && Arc::ptr_eq(&entry.owner, &self.owner) && entry.phase == FORK_PROVIDER_BUSY
                && entry.final_published && entry.consumer_accepted && entry.payload_completed
                && entry.payload.is_none());
            entry.backend_released = true;
            let receipt_index = entry.receipt_index.expect("reserved ACK receipt disappeared");
            let receipt = table.completed[receipt_index].as_mut().expect("reserved ACK cache disappeared");
            assert!(receipt.epoch == self.epoch && receipt.identity == self.identity
                && receipt.phase == ForkReceiptPhase::Published);
            receipt.phase = ForkReceiptPhase::Finished;
            table.entries[self.index].take()
        };
        self.active = false;
        // Capsule Destroy/module_put, then provider owner, all outside guards.
        drop(removed);
    }
    fn finish(mut self, stage: u32) -> Result {
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
            if entry.epoch != self.epoch || entry.identity != Some(self.identity)
                || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            { return Err(EIO); }
            if stage == super::application_abi::FORK_HOST_REVOKED_V1 {
                entry.host_revoked = true;
                entry.phase = FORK_PROVIDER_HOST_REVOKED;
                None
            } else {
                if !entry.guest_released || !self.guest_released { return Err(EIO); }
                // Stage2 alone is not final transport publication. Payload
                // Complete stays closed until its genuine final-RET receipt
                // is joined; never remove ownership with a live carrier.
                if entry.payload.is_some() { return Err(EBUSY); }
                if entry.receipt_index != self.receipt_index { return Err(EIO); }
                let receipt = table.completed[self.receipt_index.ok_or(EIO)?].as_mut().ok_or(EIO)?;
                if receipt.epoch != self.epoch || receipt.identity != self.identity
                    || receipt.phase != ForkReceiptPhase::Acknowledged
                { return Err(EIO); }
                // Accept succeeded. Cache FINISHED before releasing ownership.
                receipt.phase = ForkReceiptPhase::Finished;
                table.entries[self.index].take()
            }
        };
        self.active = false;
        drop(removed);
        Ok(())
    }
}
impl Drop for ForkProviderClaim {
    fn drop(&mut self) {
        if !self.active { return; }
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        if let Some(entry) = table.entries[self.index].as_mut() {
            if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                && Arc::ptr_eq(&entry.owner, &self.owner) && entry.phase == FORK_PROVIDER_BUSY
            { entry.phase = FORK_PROVIDER_QUARANTINED; }
        }
    }
}

#[derive(Clone, Copy)]
struct ForkInitialCapsule {
    module: *mut c_void,
    construct: super::application_abi::ForkInitialConstructV1,
    seed: *mut c_void,
    destroy: super::application_abi::ForkCapsuleDestroyV1,
    verify: super::application_abi::ForkVerifyV1,
    accept: super::application_abi::ForkCapsuleAcceptV1,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
}

unsafe fn construct_initial_fork_capsule(reservation: *const ForkProviderReservation,
    identity: super::application_abi::ForkIdentityV1, initial: ForkInitialCapsule) -> Result
{
    let reservation = unsafe { &*reservation };
    let object = unsafe { &*reservation.object };
    {
        let table = object.forks.lock();
        let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity != Some(identity)
            || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.capsule.is_some()
        { return Err(EBUSY); }
    }
    let module = unsafe { ProviderModule::acquire(initial.module.cast()) }?;
    // Allocate every capsule byte BEFORE the constructor transfers ownership
    // and before the actual MM consumer can seal any VMA adoption.
    let capsule = Arc::new(ForkConsumerCapsule {
        context: AtomicPtr::new(ptr::null_mut()), destroy: initial.destroy,
        verify: initial.verify, accept: initial.accept, _link: initial.link, _module: module,
    }, GFP_KERNEL)?;
    let mut context = ptr::null_mut();
    let status = unsafe { (initial.construct)(initial.seed, &identity, &mut context) };
    capsule.context.store(context, Ordering::Release);
    if status != 0 || context.is_null() {
        // Non-NULL error output is destroyed while its IHK-owned consumer pin
        // and independent provider owner remain live, outside every guard.
        drop(capsule);
        return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
    }
    let mut table = object.forks.lock();
    let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
    if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity != Some(identity)
        || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.capsule.is_some()
    { return Err(EBUSY); }
    entry.capsule = Some(capsule.clone());
    drop(table);
    drop(capsule);
    Ok(())
}

struct ForkConsumerScope {
    callback: super::application_abi::ForkAdoptConsumerV1,
    context: *mut c_void,
    reservation: *mut ForkProviderReservation,
    geometry: super::application_abi::ForkGeometryV1,
    slot: u32,
    generation: u64,
    invoked: bool,
    sealed: bool,
    uncertain: bool,
    active: bool,
    initial: Option<ForkInitialCapsule>,
}

// SAFETY: Only the registered provider calls this synchronously with its actual
// borrowed seal descriptor; neither this wrapper nor the consumer retains it.
unsafe extern "C" fn fork_consumer_scope(
    context: *mut c_void,
    descriptor: *mut super::application_abi::ForkSealV1,
) -> i32 {
    use super::application_abi::{ForkSealV1, VERSION};
    // SAFETY: adopt_fork owns this stack context until provider return.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    if descriptor.is_null() || scope.invoked {
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    let descriptor = unsafe { &mut *descriptor };
    let identity = descriptor.identity;
    let flag = descriptor.sealed;
    if descriptor.version != VERSION || descriptor.bytes as usize != core::mem::size_of::<ForkSealV1>()
        || identity.reserved0 != 0 || identity.reserved1 != 0
        || identity.slot != scope.slot || identity.generation != scope.generation
        || identity.root != scope.geometry.root || identity.start != scope.geometry.start
        || identity.length != scope.geometry.length || flag.is_null()
        || identity.parent == 0 || identity.child == 0 || identity.child == identity.parent
        || identity.worker == 0 || identity.delivery == 0 || identity.nonce == 0
        || identity.child_pid <= 0 || identity.child_mm == 0
    {
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    // The provider guarantees the exact atomic outlives the callback. Capture
    // its address before the consumer; descriptor edits never redirect our read.
    if unsafe { &*flag }.load(Ordering::Acquire) {
        scope.sealed = true;
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    // Bind under table exclusion BEFORE calling the MM consumer. Completion
    // rejects initializing entries; no table guard spans the consumer callback.
    if let Err(error) = unsafe { &*scope.reservation }.bind_identity(identity) {
        scope.uncertain = true;
        return error.to_errno();
    }
    let initial = scope.initial;
    let reservation = scope.reservation;
    if let Some(initial) = initial {
        if let Err(error) = unsafe { construct_initial_fork_capsule(reservation, identity, initial) } {
            return error.to_errno();
        }
    }
    // The constructor may reenter private APIs; do not retain an exclusive
    // scope borrow across it. Phase0 still forbids every progress operation.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    scope.invoked = true;
    // No operations, registry, provider, table or Remote lock spans callback.
    scope.active = true;
    let callback = scope.callback;
    let callback_context = scope.context;
    let status = unsafe { callback(callback_context, descriptor) };
    // End the earlier exclusive stack borrow before foreign code; a reentrant
    // scoped payload operation may inspect its active flag, never mutate it.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    scope.active = false;
    scope.sealed = unsafe { &*flag }.load(Ordering::Acquire);
    status
}

/// # Safety
/// Both contexts are borrowed live successful opens; caller excludes close and
/// pins its consumer module throughout this synchronous call. Geometry/context
/// are private kernel storage and the callback may not retain borrowed pointers.
#[export_name = "ihk_os_application_adopt_fork_v1"]
pub(crate) unsafe extern "C" fn adopt_fork_application(
    parent: *mut c_void,
    child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>,
    context: *mut c_void,
) -> i32 {
    unsafe { adopt_fork_application_inner(parent, child, geometry, consumer, context, None) }
}

/// # Safety
/// Same borrowed connection/geometry contract as v1. The additional constructor
/// seed and callbacks are actual live consumer-module storage, borrowed only
/// through this call. IHK pins and preallocates its capsule before MM effects;
/// preview keys allocate storage only and never replace actual ForkClaim proof.
#[export_name = "ihk_os_application_adopt_fork_v2"]
pub(crate) unsafe extern "C" fn adopt_fork_application_v2(
    parent: *mut c_void, child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    module: *mut c_void,
    construct: Option<super::application_abi::ForkInitialConstructV1>, seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void,
) -> i32 {
    let (Some(construct), Some(destroy), Some(verify), Some(accept)) = (construct, destroy, verify, accept)
        else { return EINVAL.to_errno(); };
    if module.is_null() { return EINVAL.to_errno(); }
    let initial = ForkInitialCapsule { module, construct, seed, destroy, verify, accept, link };
    unsafe { adopt_fork_application_inner(parent, child, geometry, consumer, context, Some(initial)) }
}

unsafe fn adopt_fork_application_inner(
    parent: *mut c_void, child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void,
    initial: Option<ForkInitialCapsule>,
) -> i32 {
    let result = (|| -> Result {
        if parent.is_null() || child.is_null() || geometry.is_null() { return Err(EINVAL); }
        let consumer = consumer.ok_or(EINVAL)?;
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let child = unsafe { &*child.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        if handle != child._lease.handle() { return Err(EACCES); }
        let geometry = unsafe { *geometry };
        if geometry.root == 0 || geometry.root % 4096 != 0 || geometry.start % 4096 != 0
            || geometry.length == 0 || geometry.length % 4096 != 0
            || geometry.start.checked_add(geometry.length).is_none()
        { return Err(EINVAL); }
        let lease = OS_REGISTRY.acquire(handle).map_err(|error| errno(error.errno()))?;
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        // SAFETY: The independent exact lease excludes OsObject/provider free.
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let adopt = registered.adopt_fork.ok_or(ENODEV)?;
        for callbacks in [parent.backend.callbacks, child.backend.callbacks] {
            if callbacks.open as usize != registered.open as usize
                || callbacks.invoke as usize != registered.invoke as usize
                || callbacks.close as usize != registered.close as usize
                || callbacks.adopt_fork.map(|callback| callback as usize) != Some(adopt as usize)
                || callbacks.fork_progress.map(|callback| callback as usize) != registered.fork_progress.map(|callback| callback as usize)
                || callbacks.adopt_fork_scoped.map(|callback| callback as usize) != registered.adopt_fork_scoped.map(|callback| callback as usize)
                || callbacks.prepare_fork_link.map(|callback| callback as usize) != registered.prepare_fork_link.map(|callback| callback as usize)
                || callbacks.fork_progress_payload.map(|callback| callback as usize) != registered.fork_progress_payload.map(|callback| callback as usize)
                || callbacks.prepare_fork_ack.map(|callback| callback as usize) != registered.prepare_fork_ack.map(|callback| callback as usize)
                || callbacks.fork_publication_verify.map(|callback| callback as usize) != registered.fork_publication_verify.map(|callback| callback as usize)
                || callbacks.release_fork_ack.map(|callback| callback as usize) != registered.release_fork_ack.map(|callback| callback as usize)
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
            { return Err(EACCES); }
        }
        let snapshot = OS_REGISTRY.snapshot(handle).map_err(|error| errno(error.errno()))?;
        if !matches!(snapshot.status, OsStatus::Ready | OsStatus::Running) { return Err(EBUSY); }
        let admission = object.admission.enter()?;
        let capacity = ForkProviderCapacity::reserve()?;
        let owner = Arc::new(ForkProviderOwner {
            _admission: admission, _lease: lease, _capacity: capacity,
        }, GFP_KERNEL)?;
        let mut reservation = ForkProviderReservation::reserve(object, owner, child.backend.context.as_ptr() as usize)?;
        let mut scope = ForkConsumerScope {
            callback: consumer, context, reservation: ptr::from_mut(&mut reservation), geometry,
            slot: handle.minor() as u32, generation: handle.generation(),
            invoked: false, sealed: false, uncertain: false, active: false, initial,
        };
        // SAFETY: Both connections and independent admission/OS/provider hold
        // stay live; the wrapper and caller context are synchronous stack borrows.
        // No OS operation, registry, provider or pending-table lock is held.
        let status = if let Some(adopt_scoped) = registered.adopt_fork_scoped {
            let mut payload_stack = ForkPayloadScopeStack {
                reservation: ptr::from_mut(&mut reservation), descriptor: ptr::null_mut(),
                consumer: ptr::from_mut(&mut scope).cast_const(), constructing: false, cleaning: false,
                rollback_ready: false, uncertain: true,
            };
            let stack_pointer = ptr::from_mut(&mut payload_stack);
            let mut payload_scope = super::application_abi::ForkPayloadScopeV1 {
                version: super::application_abi::VERSION,
                bytes: core::mem::size_of::<super::application_abi::ForkPayloadScopeV1>() as u32,
                slot: handle.minor() as u32, reserved0: 0, generation: handle.generation(),
                epoch: reservation.epoch, context: stack_pointer.cast(), attach: Some(fork_payload_attach_scope),
            };
            unsafe { (*stack_pointer).descriptor = ptr::from_mut(&mut payload_scope) };
            let status = unsafe { adopt_scoped(
                parent.backend.context.as_ptr(), child.backend.context.as_ptr(), &geometry,
                &mut payload_scope, Some(fork_consumer_scope), ptr::from_mut(&mut scope).cast(),
            ) };
            if !scope.sealed && (!payload_stack.rollback_ready || payload_stack.uncertain) {
                scope.uncertain = true;
            }
            status
        } else {
            unsafe { adopt(
                parent.backend.context.as_ptr(), child.backend.context.as_ptr(), &geometry,
                Some(fork_consumer_scope), ptr::from_mut(&mut scope).cast(),
            ) }
        };
        if scope.sealed || scope.uncertain {
            reservation.retain(status != 0 || scope.uncertain);
        } else {
            drop(reservation); // Safe pre-effect rollback, after callback return.
        }
        if status == 0 && (!scope.invoked || !scope.sealed || scope.uncertain) {
            return Err(errno(-71));
        }
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        to_result(status)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}
// SAFETY: The caller supplies a live successful connection, excludes close
// and retains its exact allocation through this entire private borrow.
unsafe fn fork_application_binding<'a>(
    child: *mut c_void, key: super::application_abi::ForkIdentityV1,
) -> Result<(&'a ApplicationConnection, &'a OsObject, ApplicationCallbacks)> {
    if child.is_null() { return Err(EINVAL); }
    let child = unsafe { &*child.cast::<ApplicationConnection>() };
    let handle = child._lease.handle();
    if key.slot as usize != handle.minor() || key.generation != handle.generation()
        || key.reserved0 != 0 || key.reserved1 != 0
    { return Err(EACCES); }
    let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
    if raw.is_null() { return Err(EIO); }
    let object = unsafe { &*raw };
    let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
    let callbacks = child.backend.callbacks;
    if callbacks.open as usize != registered.open as usize
        || callbacks.invoke as usize != registered.invoke as usize
        || callbacks.close as usize != registered.close as usize
        || callbacks.adopt_fork.map(|callback| callback as usize) != registered.adopt_fork.map(|callback| callback as usize)
        || callbacks.fork_progress.map(|callback| callback as usize) != registered.fork_progress.map(|callback| callback as usize)
        || callbacks.adopt_fork_scoped.map(|callback| callback as usize) != registered.adopt_fork_scoped.map(|callback| callback as usize)
        || callbacks.prepare_fork_link.map(|callback| callback as usize) != registered.prepare_fork_link.map(|callback| callback as usize)
        || callbacks.fork_progress_payload.map(|callback| callback as usize) != registered.fork_progress_payload.map(|callback| callback as usize)
        || callbacks.prepare_fork_ack.map(|callback| callback as usize) != registered.prepare_fork_ack.map(|callback| callback as usize)
        || callbacks.fork_publication_verify.map(|callback| callback as usize) != registered.fork_publication_verify.map(|callback| callback as usize)
        || callbacks.release_fork_ack.map(|callback| callback as usize) != registered.release_fork_ack.map(|callback| callback as usize)
        || registered.fork_progress.is_none()
    { return Err(EACCES); }
    Ok((child, object, registered))
}

struct ForkLinkResolverScope {
    object: *const OsObject,
    slot: u32,
    generation: u64,
}

unsafe extern "C" fn resolve_fork_link_scope(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkLinkSealV1,
    finish: Option<super::application_abi::ForkLinkFinishV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkLinkSealV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let finish = finish.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let d = unsafe { &*descriptor };
        let key = d.identity;
        if d.version != VERSION || d.bytes as usize != core::mem::size_of::<ForkLinkSealV1>()
            || d.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation
            || key.parent == 0 || key.child == 0 || key.parent == key.child
            || key.worker == 0 || key.delivery == 0 || key.nonce == 0 || key.child_pid <= 0 || key.child_mm == 0
            || d.second_worker == 0 || d.second_delivery == 0 || d.second_cpu < 0
            || d.carrier_physical == 0 || d.carrier_sequence == 0 || d.gate.is_null()
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let before = (d.version, d.bytes, d.identity, d.second_worker, d.second_delivery,
            d.second_cpu, d.reserved, d.carrier_physical, d.carrier_sequence, d.gate);
        let object = unsafe { &*scope.object };
        // Copy only a scalar under exclusion. No context is dereferenced until
        // acquire rechecks the full key and clones its actual owner/capsules.
        let child_context = {
            let table = object.forks.lock();
            table.entries.iter().flatten().find(|entry| entry.identity == Some(key))
                .map(|entry| entry.child_context).ok_or(ENOENT)?
        };
        let mut claim = match ForkProviderClaim::acquire(object, key, child_context, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        claim.begin_link_attempt()?;
        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let verify = capsule._link.ok_or(ENODEV)?;
        let consumer_context = capsule.context.load(Ordering::Acquire);
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        let payload_context = payload.context.load(Ordering::Acquire);
        if consumer_context.is_null() || payload_context.is_null() { return Err(EIO); }
        // Every exact epoch/capsule/module/OS pin remains owned by claim. No
        // table/Remote/MM guard spans either callback. Cache the provider's
        // continuation and ticket before consumer code can edit its descriptor.
        let status = unsafe { verify(consumer_context, descriptor) };
        let d = unsafe { &*descriptor };
        let after = (d.version, d.bytes, d.identity, d.second_worker, d.second_delivery,
            d.second_cpu, d.reserved, d.carrier_physical, d.carrier_sequence, d.gate);
        if after != before { return Err(errno(-71)); }
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        if unsafe { &*before.9 }.load(Ordering::Acquire) != 2 { return Err(errno(-71)); }
        let status = unsafe { finish(ticket, payload_context) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        // Restore only this exact BUSY epoch; all attempted errors instead
        // quarantine and retain its contexts, including any SEALED link gate.
        claim.restore()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}


unsafe extern "C" fn resolve_fork_control_scope(
    context: *mut c_void, descriptor: *const super::application_abi::ForkControlV1,
    park: Option<super::application_abi::ForkControlParkV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkControlV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let park = park.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let before = unsafe { *descriptor }; let key = before.identity;
        if before.version != VERSION || before.bytes as usize != core::mem::size_of::<ForkControlV1>()
            || before.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation || before.epoch == 0
            || key.parent == 0 || key.child == 0 || key.parent == key.child || key.worker == 0
            || key.delivery == 0 || key.nonce == 0 || key.child_pid <= 0 || key.child_mm == 0
            || before.worker == 0 || before.delivery == 0 || before.cpu < 0
            || before.physical == 0 || before.response == 0
        { return Err(EACCES); }
        let object = unsafe { &*scope.object };
        let child_context = {
            let table = object.forks.lock();
            table.entries.iter().flatten().find(|e| e.identity == Some(key) && e.epoch == before.epoch)
                .map(|e| e.child_context).ok_or(ENOENT)?
        };
        let claim = ForkProviderClaim::acquire_control(object, key, child_context, before.epoch)?;
        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        if capsule.context.load(Ordering::Acquire).is_null() { return Err(EIO); }
        let payload_context = payload.context.load(Ordering::Acquire);
        if payload_context.is_null() { return Err(EIO); }
        // No IHK table guard spans backend/Remote code. Both exact capsules,
        // module and OS admission remain owned by this BUSY claim. Callback is
        // registered backend code, and receives ONLY shared payload metadata.
        let status = unsafe { park(ticket, payload_context.cast_const()) };
        if unsafe { *descriptor } != before { return Err(errno(-71)); }
        if status != 0 {
            // The trusted park callback has no fallible step after moving its
            // response. A refusal therefore has no backend ownership effects.
            claim.restore_control()?;
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        // Restore failure retains the original IHK claim; caller retains its durable
        // parked response and independently marks its backend owner uncertain.
        claim.restore_control()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// Actual live ApplicationConnection pre-RETURN hook. Positive result means
/// durable park ONLY: no revoke/receipt/terminal authority and no standard RET.
#[export_name = "ihk_os_application_prepare_fork_control_v1"]
pub(crate) unsafe extern "C" fn prepare_fork_control_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result<bool> {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|b| b.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.adopt_fork.map(|f| f as usize) != registered.adopt_fork.map(|f| f as usize)
            || callbacks.fork_progress.map(|f| f as usize) != registered.fork_progress.map(|f| f as usize)
            || callbacks.adopt_fork_scoped.map(|f| f as usize) != registered.adopt_fork_scoped.map(|f| f as usize)
            || callbacks.prepare_fork_link.map(|f| f as usize) != registered.prepare_fork_link.map(|f| f as usize)
            || callbacks.fork_progress_payload.map(|f| f as usize) != registered.fork_progress_payload.map(|f| f as usize)
            || callbacks.prepare_fork_ack.map(|f| f as usize) != registered.prepare_fork_ack.map(|f| f as usize)
            || callbacks.fork_publication_verify.map(|f| f as usize) != registered.fork_publication_verify.map(|f| f as usize)
            || callbacks.release_fork_ack.map(|f| f as usize) != registered.release_fork_ack.map(|f| f as usize)
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_control else { return Ok(false); };
        let mut scope = ForkLinkResolverScope { object: ptr::from_ref(object), slot: handle.minor() as u32,
            generation: handle.generation() };
        match unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_control_scope), ptr::from_mut(&mut scope).cast()) } {
            0 => Ok(false), 1 => Ok(true), e if (-4095..0).contains(&e) => Err(errno(e)), _ => Err(errno(-71)),
        }
    })();
    result.map_or_else(|e| e.to_errno(), |parked| i32::from(parked))
}

unsafe extern "C" fn resolve_fork_ack_scope(
    context: *mut c_void, descriptor: *const super::application_abi::ForkGuestAckV1,
    verify: Option<super::application_abi::ForkAckVerifyV1>,
    finish: Option<super::application_abi::ForkAckFinishV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkGuestAckV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let verify = verify.ok_or(EINVAL)?;
        let finish = finish.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let d = unsafe { &*descriptor };
        let key = d.identity;
        if d.version != VERSION || d.bytes as usize != core::mem::size_of::<ForkGuestAckV1>()
            || d.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation
            || d.epoch == 0 || d.worker == 0 || d.delivery == 0 || d.cpu < 0
            || d.physical == 0 || d.sequence != 2 || key.nonce == 0
        { return Err(EACCES); }
        let epoch = d.epoch;
        let object = unsafe { &*scope.object };
        let child_context = {
            let table = object.forks.lock();
            let entry = table.entries.iter().flatten().find(|entry|
                entry.identity == Some(key) && entry.epoch == epoch).ok_or(ENOENT)?;
            if !entry.host_revoked || entry.payload.is_none() { return Err(EBUSY); }
            entry.child_context
        };
        let mut claim = match ForkProviderClaim::acquire(object, key, child_context, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.epoch != epoch || claim.receipt_index.is_none() { return Err(EACCES); }
        if !claim.guest_released {
            let payload = claim.payload.as_ref().ok_or(ENODEV)?;
            let payload_context = payload.context.load(Ordering::Acquire);
            if payload_context.is_null() { return Err(EIO); }
            // Actual registered SMP ticket authenticates the owned selector3
            // and private original guest checked-result2 carrier. All table,
            // Remote and MM guards have ended; the raw borrow never escapes.
            let status = unsafe { verify(ticket, payload_context) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            claim.mark_guest_released()?;
        }
        // Durable ACK_RECEIVED precedes permission for final RETURN value0.
        // A retry never reruns the guest destructor or its verifier.
        let status = unsafe { finish(ticket) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        claim.restore()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// This is the actual live parent file's pre-RETURN hook. Only registered
/// backend code derives a guest ACK key from its owned original delivery.
#[export_name = "ihk_os_application_prepare_fork_ack_v1"]
pub(crate) unsafe extern "C" fn prepare_fork_ack_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.prepare_fork_ack.map(|f| f as usize) != registered.prepare_fork_ack.map(|f| f as usize)
            || callbacks.fork_publication_verify.map(|f| f as usize) != registered.fork_publication_verify.map(|f| f as usize)
            || callbacks.release_fork_ack.map(|f| f as usize) != registered.release_fork_ack.map(|f| f as usize)
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_ack else { return Ok(()); };
        let mut scope = ForkLinkResolverScope { object: ptr::from_ref(object),
            slot: handle.minor() as u32, generation: handle.generation() };
        let status = unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_ack_scope), ptr::from_mut(&mut scope).cast()) };
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        to_result(status)
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// ONLY the actual joined packet worker calls this outside all dependent
/// guards with its non-Copy publication receipt borrowed through return. Its
/// joined worker lifecycle pins provider text independently of the owner this
/// endpoint may release. No wire/user scalar or ordinary Drop calls it.
#[export_name = "ihk_os_application_publish_fork_ack_v1"]
pub(crate) unsafe extern "C" fn publish_fork_ack_application(
    slot: u32, generation: u64, identity: *const super::application_abi::ForkIdentityV1,
    epoch: u64, receipt: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        if identity.is_null() || receipt.is_null() || epoch == 0 { return Err(EINVAL); }
        let key = unsafe { *identity };
        if key.reserved0 != 0 || key.reserved1 != 0 || key.slot != slot || key.generation != generation { return Err(EACCES); }
        // Pin the exact live OS BEFORE loading or dereferencing its object.
        let handle = OS_REGISTRY.resolve_minor(slot as usize).map_err(|e| errno(e.errno()))?;
        if handle.generation() != generation { return Err(EACCES); }
        let _lease = OS_REGISTRY.acquire(handle).map_err(|e| errno(e.errno()))?;
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let publication_verify = registered.fork_publication_verify.ok_or(ENODEV)?;
        let release = registered.release_fork_ack.ok_or(ENODEV)?;
        let child_context = {
            let table = object.forks.lock();
            if table.completed.iter().flatten().any(|cached| cached.identity == key
                && cached.epoch == epoch && cached.phase == ForkReceiptPhase::Finished) { return Ok(()); }
            table.entries.iter().flatten().find(|entry|
                entry.identity == Some(key) && entry.epoch == epoch).map(|entry| entry.child_context).ok_or(ENOENT)?
        };
        let mut claim = match ForkProviderClaim::acquire(object, key, child_context, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.epoch != epoch { return Err(EACCES); }
        let (published, accepted, completed, released) = claim.finalization_state()?;
        if released { return Err(EIO); }
        if !published {
            let status = unsafe { publication_verify(child_context as *mut c_void, &key, epoch, receipt) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            claim.mark_finalization_step(0)?;
        }
        if !accepted {
            let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
            let context = capsule.context.load(Ordering::Acquire);
            if context.is_null() { return Err(EIO); }
            let status = unsafe { (capsule.accept)(context, &key) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            claim.mark_finalization_step(1)?;
        }
        if !completed {
            let payload = claim.payload.as_ref().ok_or(ENODEV)?;
            let context = payload.context.load(Ordering::Acquire);
            if context.is_null() { return Err(EIO); }
            let status = unsafe { (payload._complete)(context) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            // Complete0 consumed the context. Null it before any retry or
            // subsequent fallible step; never call the destructor twice.
            payload.context.store(ptr::null_mut(), Ordering::Release);
            claim.mark_finalization_step(2)?;
        }
        claim.final_release_ready()?;
        let status = unsafe { release(child_context as *mut c_void, &key, epoch) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        claim.finish_final_publication();
        Ok(())
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// The actual live parent Registration/file pins this connection and caller
/// module through return. Scalars come from its retained RETURN invocation;
/// only the registered backend derives a child key from the owned delivery.
#[export_name = "ihk_os_application_prepare_fork_link_v1"]
pub(crate) unsafe extern "C" fn prepare_fork_link_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.adopt_fork.map(|f| f as usize) != registered.adopt_fork.map(|f| f as usize)
            || callbacks.fork_progress.map(|f| f as usize) != registered.fork_progress.map(|f| f as usize)
            || callbacks.adopt_fork_scoped.map(|f| f as usize) != registered.adopt_fork_scoped.map(|f| f as usize)
            || callbacks.prepare_fork_link.map(|f| f as usize) != registered.prepare_fork_link.map(|f| f as usize)
            || callbacks.fork_progress_payload.map(|f| f as usize) != registered.fork_progress_payload.map(|f| f as usize)
            || callbacks.prepare_fork_ack.map(|f| f as usize) != registered.prepare_fork_ack.map(|f| f as usize)
            || callbacks.fork_publication_verify.map(|f| f as usize) != registered.fork_publication_verify.map(|f| f as usize)
            || callbacks.release_fork_ack.map(|f| f as usize) != registered.release_fork_ack.map(|f| f as usize)
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_link else { return Ok(()); };
        let mut scope = ForkLinkResolverScope {
            object: ptr::from_ref(object), slot: handle.minor() as u32, generation: handle.generation(),
        };
        let status = unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_link_scope), ptr::from_mut(&mut scope).cast()) };
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        to_result(status)
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// The caller has an independent LIVE file/callback module owner through
/// return into consumer text. consumer_module is that exact THIS_MODULE, never
/// a userspace value. Constructor seed is borrowed until callback return; its
/// transferred context retains the exact Registration. No owned module lease
/// crosses this ABI. All callbacks are module-resident immutable identities.
#[export_name = "ihk_os_application_attach_fork_capsule_v1"]
pub(crate) unsafe extern "C" fn attach_fork_capsule_application(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    consumer_module: *mut c_void,
    construct: Option<super::application_abi::ForkCapsuleConstructV1>,
    seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
) -> i32 {
    // SAFETY: The original ABI preserves its exact arguments and lifetime.
    unsafe { attach_fork_capsule_application_v2(child, identity, consumer_module,
        construct, seed, destroy, verify, accept, None) }
}

/// # Safety
/// Same ownership contract as v1. The distinct optional link verifier borrows
/// only its actual preallocated gate; host revoke never substitutes for link.
#[export_name = "ihk_os_application_attach_fork_capsule_v2"]
pub(crate) unsafe extern "C" fn attach_fork_capsule_application_v2(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    consumer_module: *mut c_void,
    construct: Option<super::application_abi::ForkCapsuleConstructV1>,
    seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
) -> i32 {
    let result = (|| -> Result {
        if identity.is_null() { return Err(EINVAL); }
        let construct = construct.ok_or(EINVAL)?;
        let destroy = destroy.ok_or(EINVAL)?;
        let verify = verify.ok_or(EINVAL)?;
        let accept = accept.ok_or(EINVAL)?;
        let key = unsafe { *identity };
        let (child, object, _) = unsafe { fork_application_binding(child, key) }?;
        let claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.capsule.is_some() || claim.attempted {
            claim.restore()?;
            return Err(EBUSY);
        }
        // The table lock ended before module acquisition or consumer code.
        let module = match unsafe { ProviderModule::acquire(consumer_module.cast()) } {
            Ok(module) => module,
            Err(error) => { claim.restore()?; return Err(error); }
        };
        let mut context = ptr::null_mut();
        let status = unsafe { construct(seed, &mut context) };
        if status != 0 || context.is_null() {
            if !context.is_null() { unsafe { destroy(context) }; }
            // Consumer Drop/Destroy has returned BEFORE this IHK-owned put.
            drop(module);
            claim.restore()?;
            return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
        }
        let capsule = ForkConsumerCapsule {
            context: AtomicPtr::new(context), destroy, verify, accept, _link: link, _module: module,
        };
        let capsule = match Arc::new(capsule, GFP_KERNEL) {
            Ok(capsule) => capsule,
            Err(error) => { claim.restore()?; return Err(error.into()); }
        };
        claim.install_capsule(capsule)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Same live connection and independent caller file/module ownership as attach.
/// This is never called by a generic Drop or unpinned consumer context. It
/// detaches ONLY an unattempted capsule; physical pending ownership remains.
#[export_name = "ihk_os_application_cancel_fork_capsule_v1"]
pub(crate) unsafe extern "C" fn cancel_fork_capsule_application(
    child: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    let result = (|| -> Result {
        if identity.is_null() { return Err(EINVAL); }
        let key = unsafe { *identity };
        let (child, object, _) = unsafe { fork_application_binding(child, key) }?;
        let claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.attempted || claim.capsule.is_none() {
            let status = if claim.attempted { EBUSY } else { ENOENT };
            claim.restore()?;
            return Err(status);
        }
        claim.cancel_capsule()
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// The live child and proof context are retained through return. Stage1 uses
/// ONLY the IHK-owned capsule's registered verifier/context. Stage2 proof comes
/// ONLY from authenticated original in-band final destruction, never a host
/// receipt. Final release is initiated outside MCCTRL, or the caller retains a
/// separate live file/callback module owner until return into consumer text.
#[export_name = "ihk_os_application_fork_progress_v1"]
pub(crate) unsafe extern "C" fn fork_progress_application(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    stage: u32,
    verify: Option<super::application_abi::ForkVerifyV1>,
    context: *mut c_void,
) -> i32 {
    use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_GUEST_DESTROYED_V1};
    let result = (|| -> Result {
        if identity.is_null() || !matches!(stage, FORK_HOST_REVOKED_V1 | FORK_GUEST_DESTROYED_V1)
        { return Err(EINVAL); }
        let key = unsafe { *identity };
        let (child, object, registered) = unsafe { fork_application_binding(child, key) }?;
        let progress = registered.fork_progress.ok_or(ENODEV)?;
        let mut claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, stage)? {
            ForkClaimLookup::Completed => return Ok(()),
            ForkClaimLookup::Pending(claim) => claim,
        };
        let (host_verify, capsule_context, accept) = {
            let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
            let context = capsule.context.load(Ordering::Acquire);
            if context.is_null() { return Err(EIO); }
            (capsule.verify, context, capsule.accept)
        };
        if stage == FORK_HOST_REVOKED_V1 {
            // Independent capsule Arc/module/Registration and OS/provider
            // ownership survive last fd closure or any attempted error.
            let status = if let Some(payload) = claim.payload.as_ref() {
                let callback = registered.fork_progress_payload.ok_or(ENODEV)?;
                let payload_context = payload.context.load(Ordering::Acquire);
                if payload_context.is_null() { return Err(EIO); }
                unsafe { callback(child.backend.context.as_ptr(), &key, stage,
                    Some(host_verify), capsule_context, payload_context) }
            } else {
                unsafe { progress(child.backend.context.as_ptr(), &key, stage, Some(host_verify), capsule_context) }
            };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            return claim.finish(stage);
        }
        // Carrier transactions accept guest destruction only through the
        // actual owned selector3 ticket and later final-publication endpoint.
        if claim.payload.is_some() { return Err(EBUSY); }
        if !claim.guest_released {
            let verify = verify.ok_or(EINVAL)?;
            let status = unsafe { progress(child.backend.context.as_ptr(), &key, stage, Some(verify), context) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            claim.mark_guest_released()?;
        }
        // ACK_RECEIVED is durable and receipt capacity was reserved before
        // Remote's irreversible transition. Retry executes ONLY Accept here.
        let status = unsafe { accept(capsule_context, &key) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        claim.finish(stage)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}
// END PRIVATE FORK IHK PROVIDER BRIDGE

// SAFETY: Immutable relocation with the same module lifetime and namespace.
#[export_name = "__export_symbol_ihk_os_application_adopt_fork_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ADOPT_FORK_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: adopt_fork_application as *const () as *const u8,
};

// SAFETY: Additive private initializing-capsule callback relocation.
#[export_name = "__export_symbol_ihk_os_application_adopt_fork_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ADOPT_FORK_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: adopt_fork_application_v2 as *const () as *const u8,
};

// SAFETY: Immutable relocation with the same module lifetime and namespace.
#[export_name = "__export_symbol_ihk_os_application_fork_progress_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_FORK_PROGRESS_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: fork_progress_application as *const () as *const u8,
};

// SAFETY: Immutable module-resident private callback relocation.
#[export_name = "__export_symbol_ihk_os_application_attach_fork_capsule_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ATTACH_FORK_CAPSULE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: attach_fork_capsule_application as *const () as *const u8,
};

// SAFETY: Immutable additive private callback relocation; v1 is unchanged.
#[export_name = "__export_symbol_ihk_os_application_attach_fork_capsule_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ATTACH_FORK_CAPSULE_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: attach_fork_capsule_application_v2 as *const () as *const u8,
};

// SAFETY: Private synchronous scoped rollback relocation, never a user ABI.
#[export_name = "__export_symbol_ihk_os_application_abort_fork_payload_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ABORT_FORK_PAYLOAD_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: abort_fork_payload_application as *const () as *const u8,
};

// SAFETY: Private synchronous ownership publication relocation.
#[export_name = "__export_symbol_ihk_os_application_ready_fork_payload_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_READY_FORK_PAYLOAD_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ready_fork_payload_application as *const () as *const u8,
};

// SAFETY: Private parent-delivery link preparation relocation.
#[export_name = "__export_symbol_ihk_os_application_prepare_fork_link_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_PREPARE_FORK_LINK_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: prepare_fork_link_application as *const () as *const u8,
};

// SAFETY: Immutable module-resident private callback relocation.
#[export_name = "__export_symbol_ihk_os_application_cancel_fork_capsule_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_CANCEL_FORK_CAPSULE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: cancel_fork_capsule_application as *const () as *const u8,
};

/// # Safety
/// Return the unique successful open after all concurrent invocations end.
#[export_name = "ihk_os_application_close_v1"]
pub(crate) unsafe extern "C" fn close_application(context: *mut c_void) {
    // SAFETY: The trusted caller transfers the original unique Box exactly once.
    unsafe { drop(Box::from_raw(context.cast::<ApplicationConnection>())) };
}

// SAFETY: These immutable relocations name module-resident ABI exports.
#[export_name = "__export_symbol_ihk_os_application_open_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_OPEN_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: open_application as *const () as *const u8,
};
// SAFETY: Immutable relocation with the same module lifetime and namespace.
#[export_name = "__export_symbol_ihk_os_application_invoke_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_INVOKE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: invoke_application as *const () as *const u8,
};
// SAFETY: Immutable relocation with the same module lifetime and namespace.
#[export_name = "__export_symbol_ihk_os_application_close_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_CLOSE_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: close_application as *const () as *const u8,
};

/// Query only the running OS's retained topology, never a user pointer.
///
/// # Safety
/// Callers provide only scalar slot, generation, and command values. The exact
/// generation is leased before any object dereference; operation and admission
/// locking retain the callback surface through the query, and this C ABI never
/// unwinds.
#[export_name = "ihk_os_topology_query_v1"]
pub(crate) extern "C" fn topology_query(slot: u32, generation: u64, command: u32) -> i64 {
    let result = (|| -> Result<i64> {
        if !super::service_abi::topology_query(command) {
            return Err(EINVAL);
        }
        let handle = OS_REGISTRY
            .resolve_minor(slot as usize)
            .map_err(|error| errno(error.errno()))?;
        if handle.generation() != generation {
            return Err(errno(-116));
        }
        let _lease = OS_REGISTRY
            .acquire(handle)
            .map_err(|error| errno(error.errno()))?;
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        assert!(!raw.is_null());
        // SAFETY: The exact-generation lease excludes object and backend release.
        let object = unsafe { &*raw };
        // Retain the v2 backend serialization contract. This lock order is
        // operations -> admission, matching shutdown and application Open.
        let _operation = object.operations.lock();
        // Keep shutdown from closing the callback surface through the complete
        // backend query.
        let _admission = object.admission.enter()?;
        let snapshot = OS_REGISTRY
            .snapshot(handle)
            .map_err(|error| errno(error.errno()))?;
        if !matches!(snapshot.status, OsStatus::Ready | OsStatus::Running) {
            return Err(EBUSY);
        }
        let backend = object.backend.ok_or(ENODEV)?;
        // SAFETY: The exact OS/module lease, operation mutex and admission
        // owner pin and serialize the backend callback for this scalar query.
        let value = unsafe { (backend.ioctl)(slot, generation, command, 0, 0) };
        if value < -4095 || value > i32::MAX as i64 {
            return Err(EIO);
        }
        Ok(value)
    })();
    result.unwrap_or_else(|error| error.to_errno() as i64)
}

// SAFETY: Immutable module-resident relocation for Linux modpost.
#[export_name = "__export_symbol_ihk_os_topology_query_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static TOPOLOGY_QUERY_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: topology_query as *const () as *const u8,
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
#[export_name = "__export_symbol_ihk_os_create_unbooted_v3"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V3_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v3 as *const () as *const u8,
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v4"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V4_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v4 as *const () as *const u8,
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v5"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V5_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v5 as *const () as *const u8,
};

// SAFETY: Linux modpost reads this immutable relocation for the module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v6"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V6_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v6 as *const () as *const u8,
};

// SAFETY: Additive immutable relocation with the same module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v7"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V7_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v7 as *const () as *const u8,
};

// SAFETY: Additive immutable relocation with the same module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v8"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V8_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v8 as *const () as *const u8,
};

// SAFETY: Additive immutable relocation with the same module lifetime.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v9"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V9_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v9 as *const () as *const u8,
};

// SAFETY: Additive module-resident private callback registration.
#[export_name = "__export_symbol_ihk_os_create_unbooted_v10"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V10_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_create_unbooted_v10 as *const () as *const u8,
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

// SAFETY: Immutable data-only modpost relocation for this module's lifetime.
#[export_name = "__export_symbol_ihk_os_with_kobject_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_KOBJECT_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_os_with_kobject_v1 as *const () as *const u8,
};

// SAFETY: Module-resident additive private finalization callback relocation.
#[export_name = "__export_symbol_ihk_os_application_prepare_fork_ack_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_PREPARE_FORK_ACK_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: prepare_fork_ack_application as *const () as *const u8,
};

// SAFETY: Module-resident additive private finalization callback relocation.
#[export_name = "__export_symbol_ihk_os_application_publish_fork_ack_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_PUBLISH_FORK_ACK_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: publish_fork_ack_application as *const () as *const u8,
};

// SAFETY: Module-resident additive private control callback relocations.
#[export_name = "__export_symbol_ihk_os_application_prepare_fork_control_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_PREPARE_FORK_CONTROL_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: prepare_fork_control_application as *const () as *const u8,
};
#[export_name = "__export_symbol_ihk_os_create_unbooted_v11"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V11_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: ihk_os_create_unbooted_v11 as *const () as *const u8,
};
