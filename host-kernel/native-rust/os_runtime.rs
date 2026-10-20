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
    sync::atomic::{AtomicI32, AtomicPtr, AtomicU32, Ordering},
};
use kernel::{
    bindings,
    error::to_result,
    prelude::*,
    sync::{new_mutex, Mutex},
    uaccess::UserSlice,
};

use super::{
    abi::{
        IhkKmsgBuffer, IHK_DEVICE_CREATE_OS, IHK_DEVICE_DESTROY_OS, IHK_OS_BOOT,
        IHK_OS_GET_BUILDID, IHK_OS_LOAD, IHK_OS_QUERY_STATUS, IHK_OS_READ_KMSG,
        IHK_OS_SHUTDOWN, IHK_OS_STATUS,
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
const KMSG_DATA_BYTES: usize = KMSG_BYTES - 4096;
// A stopped guest may retain the inter-kernel lock. Never spin indefinitely.
const KMSG_LOCK_ATTEMPTS: usize = 65_536;

struct KmsgReadLock<'a>(&'a AtomicI32);

impl Drop for KmsgReadLock<'_> {
    fn drop(&mut self) {
        // The guest uses the same 32-bit CAS lock and a final zero store.
        self.0.store(0, Ordering::Release);
    }
}
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

    // Called under OsObject.operations while the caller's exact-generation
    // OsLease retains this owned allocation. No physical/user address is used
    // to locate it. Reads remain available after failed boot/shutdown for logs.
    fn read(&self, argument: usize) -> Result<isize> {
        // Allocate and initialize before taking the inter-kernel lock. Neither
        // allocation nor usercopy may sleep while guest writers are excluded.
        let mut output = Vec::with_capacity(KMSG_DATA_BYTES, GFP_KERNEL)?;
        for _ in 0..KMSG_DATA_BYTES {
            output.push(0, GFP_KERNEL)?;
        }
        let bytes = self.snapshot(&mut output)?;
        // Legacy __ihk_os_read_kmsg returns EINVAL for any failed copy_to_user.
        // UserSlice supplies checked user access, including compat-normalized
        // addresses; there is no raw user dereference or retained user pointer.
        UserSlice::new(argument, bytes)
            .writer()
            .write_slice(&output[..bytes])
            .map_err(|_| EINVAL)?;
        Ok(bytes as isize)
    }

    fn snapshot(&self, output: &mut [u8]) -> Result<usize> {
        // Allocation creates a nonzero, page-aligned address; reject a broken
        // trusted owner before dereferencing, never substitute a physical map.
        if self.0 == 0 || self.0 % 4096 != 0 || output.len() < KMSG_DATA_BYTES {
            return Err(EINVAL);
        }
        let buffer = self.0 as *mut IhkKmsgBuffer;
        // SAFETY: KmsgPages owns this live, aligned 4MiB allocation. The guest
        // sees the identical lock at offset zero and uses atomic CAS(0,1).
        // No Rust reference to the concurrently mutable whole ring is formed.
        let lock = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!((*buffer).lock)) };
        let mut acquired = false;
        for _ in 0..KMSG_LOCK_ATTEMPTS {
            if lock.compare_exchange(0, 1, Ordering::Acquire, Ordering::Relaxed).is_ok() {
                acquired = true;
                break;
            }
            core::hint::spin_loop();
        }
        if !acquired {
            return Err(EBUSY);
        }
        let _lock = KmsgReadLock(lock);
        // Only guest CPUs write this ring; no Linux IRQ callback reads/writes
        // it. operations serializes host readers and teardown. IRQ disabling
        // is therefore unnecessary: no local interrupt can take this lock.
        // All work below is bounded, allocation-free and does not sleep.
        // SAFETY: The shared lock excludes guest changes to metadata and data;
        // volatile reads fetch the shared fields after acquisition. Each index
        // is checked against the exact allocated data area before pointer use.
        let (length, head, tail) = unsafe {
            (ptr::addr_of!((*buffer).length).read_volatile(),
             ptr::addr_of!((*buffer).head).read_volatile(),
             ptr::addr_of!((*buffer).tail).read_volatile())
        };
        if length != KMSG_DATA_BYTES as i32 || head < 0 || tail < 0
            || head >= length || tail >= length {
            return Err(EINVAL);
        }
        let (head, tail) = (head as usize, tail as usize);
        // SAFETY: addr_of forms a raw pointer within the live owned buffer.
        let data = unsafe { ptr::addr_of!((*buffer).bytes).cast::<u8>() };
        let (bottom, top) = if head > tail {
            // Preserve legacy read_kmsg's strnlen on the wrapped bottom span,
            // including its embedded-NUL behavior; the top span is raw bytes.
            let mut bottom = 0;
            while bottom < KMSG_DATA_BYTES - head {
                // SAFETY: The checked loop bounds remain inside the allocation;
                // the lock excludes writes until this snapshot has completed.
                if unsafe { data.add(head + bottom).read_volatile() } == 0 {
                    break;
                }
                bottom += 1;
            }
            (bottom, tail)
        } else {
            (tail - head, 0)
        };
        // SAFETY: The source spans are bounded by validated ring indices and
        // cannot overlap the independently allocated, sufficiently sized output.
        // The lock retains the snapshot through both copies. No head/tail shift
        // occurs: repeated per-OS reads must return the same retained bytes.
        unsafe {
            ptr::copy_nonoverlapping(data.add(head), output.as_mut_ptr(), bottom);
            ptr::copy_nonoverlapping(data, output.as_mut_ptr().add(bottom), top);
        }
        Ok(bottom + top)
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
// SAFETY: IHK invokes this resident, non-unwinding scalar-ABI callback with
// the exact live generation lease and provider module pin, while holding the
// per-OS operation mutex after closing admission and entering Shutdown.
// The provider must report every possibly irreversible effect with the v6
// post-effect tag, retain affected owners on failure, and never reenter OS
// operations or destruction while that mutex is held.
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
    // Registration selects publication explicitly: existing callbacks retain
    // Ready; v6 callback ABI 2 promises the full running-service boundary.
    success_status: OsStatus,
}

#[derive(Clone, Copy)]
struct ApplicationCallbacks {
    open: super::application_abi::Open,
    invoke: super::application_abi::Invoke,
    close: super::application_abi::Close,
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
    /// successful boot also calls it after its registered success state is committed.
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
/// Callback ABI 1 preserves Ready on successful start. ABI 2 explicitly
/// promises start returns zero only after full guest/service readiness, so
/// success publishes Running. Failure retains the same Failed semantics.
/// The signatures and shutdown effect contract are identical in both versions.
/// `shutdown` returns zero for complete success, a signed Linux errno for a
/// pre-effect failure, or `SHUTDOWN_V6_POST_EFFECT | (errno as u32)` after an
/// irreversible effect.  The latter keeps admission closed and retains the
/// exact generation for reconciliation/retry.
// SAFETY: Only trusted provider module code may supply the live module owner
// and ABI-correct, resident, non-unwinding callbacks. create_os acquires the
// provider module pin before publication and retains it through teardown;
// shutdown must obey the exact-generation, serialized v6 effect contract above.
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
            boot: Some(OsBackendBootV3 {
                prepare,
                start,
                success_status: if callback_abi == 2 { OsStatus::Running } else { OsStatus::Ready },
            }),
            application: Some(ApplicationCallbacks {
                open,
                invoke,
                close,
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
    if command == IHK_OS_READ_KMSG {
        // This file's lease pins the full slot/generation and the IHK-owned
        // kmsg allocation. The operation lock excludes boot/shutdown/release;
        // guest writers are serialized by the shared ring lock in snapshot.
        // No provider callback, service admission, or arbitrary mapping occurs.
        return match object._kmsg.read(argument as usize) {
            Ok(bytes) => bytes as core::ffi::c_long,
            Err(error) => error.to_errno() as core::ffi::c_long,
        };
    }
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
                // SAFETY: The live lease, operation mutex and module pin retain
                // this exact generation and callback; admission and registry
                // are closed, and the v6 tag preserves post-effect ownership.
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

struct ApplicationForkLeaseV4 {_admission:AdmissionOwner,_lease:OsLease<'static>}
unsafe extern "C" fn release_application_fork_lease_v4(owner:*mut c_void) {
    unsafe {drop(Box::from_raw(owner.cast::<ApplicationForkLeaseV4>()))};
}
/// # Safety
/// Exact live successful paired connections, exclusive caller storage, and
/// resident synchronous consumer code. Scope transfers a genuine IHK lease
/// object before any irreversible MM effect; no locks span the callback.
#[export_name="ihk_os_application_adopt_current_v4"]
pub(crate) unsafe extern "C" fn adopt_current_application_v4(
    parent:*mut c_void,child:*mut c_void,geometry:*const super::application_abi::ForkGeometryV3,
    consumer:Option<super::application_abi::ForkAdoptConsumerV4>,context:*mut c_void)->i32 {
    let result=(||->Result {
        if parent.is_null()||child.is_null()||parent==child||geometry.is_null(){return Err(EINVAL);}
        let parent=unsafe {&*parent.cast::<ApplicationConnection>()};
        let child=unsafe {&*child.cast::<ApplicationConnection>()};let handle=parent._lease.handle();
        if handle!=child._lease.handle(){return Err(EACCES);}
        let geometry=unsafe {*geometry};let consumer=consumer.ok_or(EINVAL)?;
        if geometry.root==0||geometry.root%4096!=0||geometry.start%4096!=0||geometry.length==0
            ||geometry.length%4096!=0||geometry.start.checked_add(geometry.length).is_none(){return Err(EINVAL);}
        let lease=OS_REGISTRY.acquire(handle).map_err(|e|errno(e.errno()))?;
        let raw=OS_OBJECTS[handle.minor()].load(Ordering::Acquire);if raw.is_null(){return Err(EIO);}
        let object=unsafe {&*raw};let registered=object.backend.and_then(|b|b.application).ok_or(ENODEV)?;
        for cb in [parent.backend.callbacks,child.backend.callbacks] {
            if cb.open as usize!=registered.open as usize||cb.invoke as usize!=registered.invoke as usize
                ||cb.close as usize!=registered.close as usize{return Err(EACCES);}
        }
        let status=OS_REGISTRY.snapshot(handle).map_err(|e|errno(e.errno()))?.status;
        if !matches!(status,OsStatus::Ready|OsStatus::Running){return Err(EBUSY);}
        let admission=object.admission.enter()?;
        let owner=Box::into_raw(Box::new(ApplicationForkLeaseV4{_admission:admission,_lease:lease},GFP_KERNEL)?);
        let mut call=super::application_abi::ForkAdoptCallV4{version:4,
            bytes:core::mem::size_of::<super::application_abi::ForkAdoptCallV4>() as u32,
            child:child.backend.context.as_ptr(),geometry,consumer:Some(consumer),context,
            lease:owner.cast(),release_lease:Some(release_application_fork_lease_v4)};
        let result=unsafe {(registered.invoke)(parent.backend.context.as_ptr(),
            super::application_abi::FORK_ADOPT_CURRENT_V4,ptr::from_mut(&mut call).cast(),
            core::mem::size_of::<super::application_abi::ForkAdoptCallV4>())};
        if call.lease==owner.cast() && call.release_lease.map(|f|f as usize)==Some(release_application_fork_lease_v4 as usize){
            // Provider never took ownership; no MM capability could be sealed.
            unsafe {release_application_fork_lease_v4(owner.cast())};
            if result==0{return Err(errno(-71));}
        }else if !call.lease.is_null()||call.release_lease.is_some(){
            // Unknown transfer: retain the real owner rather than reconstruct
            // or release it from output scalar claims.
            return Err(errno(-71));
        }
        if result>0||result< -4095{return Err(errno(-71));}
        kernel::error::to_result(result as i32)?;Ok(())
    })();result.map_or_else(|e|e.to_errno(),|()|0)
}
#[export_name="__export_symbol_ihk_os_application_adopt_current_v4"]
#[link_section=".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_ADOPT_CURRENT_V4_EXPORT:IhkExportSymbolRecord=IhkExportSymbolRecord{
    license:*b"GPL\0",namespace:*b"MCKERNEL_IHK_V1\0",padding:[0;4],
    symbol:adopt_current_application_v4 as *const () as *const u8,
};

/// # Safety
/// Both connections and the exclusive typed call remain owned through this
/// synchronous invocation. The provider retains any transferred capsule.
#[export_name="ihk_os_application_fork_control_current_v1"]
pub(crate) unsafe extern "C" fn fork_control_application_current_v1(
    parent:*mut c_void,child:*mut c_void,call:*mut super::application_abi::ForkControlCallV1)->i32 {
    let result=(||->Result {
        if parent.is_null()||child.is_null()||parent==child||call.is_null(){return Err(EINVAL);}
        let parent=unsafe {&*parent.cast::<ApplicationConnection>()};
        let child=unsafe {&*child.cast::<ApplicationConnection>()};
        if parent._lease.handle()!=child._lease.handle(){return Err(EACCES);}
        let a=parent.backend.callbacks;let b=child.backend.callbacks;
        if a.open as usize!=b.open as usize||a.invoke as usize!=b.invoke as usize
            ||a.close as usize!=b.close as usize{return Err(EACCES);}
        let call=unsafe {&mut *call};
        if call.version!=1||call.bytes as usize!=core::mem::size_of_val(call)||!call.child.is_null(){return Err(EINVAL);}
        call.child=child.backend.context.as_ptr();
        let status=unsafe {(a.invoke)(parent.backend.context.as_ptr(),
            super::application_abi::FORK_CONTROL_CURRENT_V1,ptr::from_mut(call).cast(),core::mem::size_of_val(call))};
        call.child=ptr::null_mut();
        if status>0||status< -4095{return Err(errno(-71));}
        kernel::error::to_result(status as i32)?;Ok(())
    })();result.map_or_else(|e|e.to_errno(),|()|0)
}
#[export_name="__export_symbol_ihk_os_application_fork_control_current_v1"]
#[link_section=".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_FORK_CONTROL_CURRENT_V1_EXPORT:IhkExportSymbolRecord=IhkExportSymbolRecord{
    license:*b"GPL\0",namespace:*b"MCKERNEL_IHK_V1\0",padding:[0;4],
    symbol:fork_control_application_current_v1 as *const () as *const u8,
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
