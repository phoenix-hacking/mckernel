// SPDX-License-Identifier: GPL-2.0
//! File-owned callback and module lifetimes for the native mcctrl service.

use core::{ffi::c_void, pin::Pin, ptr, sync::atomic::{AtomicPtr, Ordering}};
use kernel::{prelude::*, sync::{new_mutex, Mutex}};
use super::{os_runtime::ProviderModule, service_abi, IhkExportSymbolRecord};

#[derive(Clone, Copy)]
struct Registration {
    owner: *mut c_void,
    open: service_abi::Open,
    ioctl: service_abi::Ioctl,
    close: service_abi::Close,
}

// SAFETY: The registering module retains its immutable identities until
// unregister under this same mutex. Acquisition pins it before using callbacks.
unsafe impl Send for Registration {}

type State = Mutex<Option<Registration>>;
static PUBLISHED: AtomicPtr<State> = AtomicPtr::new(ptr::null_mut());

/// Owned by the IHK OS device family; dependent modules cannot outlive IHK.
pub(super) struct Registry(Pin<Box<State>>);

impl Registry {
    pub(super) fn new() -> Result<Self> {
        let state = Box::pin_init(new_mutex!(None), GFP_KERNEL)?;
        let raw = ptr::from_ref(&*state).cast_mut();
        PUBLISHED.compare_exchange(ptr::null_mut(), raw, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| EBUSY)?;
        Ok(Self(state))
    }
}

impl Drop for Registry {
    fn drop(&mut self) {
        // All service consumers depend on IHK; OS files also pin its fops.
        assert!(self.0.lock().is_none());
        assert!(PUBLISHED.swap(ptr::null_mut(), Ordering::AcqRel) == ptr::from_ref(&*self.0).cast_mut());
    }
}

fn state() -> Result<&'static State> {
    let state = PUBLISHED.load(Ordering::Acquire);
    if state.is_null() { return Err(ENODEV); }
    // SAFETY: Only module-dependent registration calls or IHK-owned file
    // operations enter this private helper. Both prevent Registry destruction.
    Ok(unsafe { &*state })
}

/// # Safety
/// The caller supplies its own live Linux module and module-resident callbacks.
/// It must unregister on init failure or unload, before any callback code or
/// module storage can disappear. Callback semantics are specified by service_abi.
#[export_name = "ihk_os_service_register_v1"]
pub(crate) unsafe extern "C" fn register(
    owner: *mut c_void, version: u32, open: Option<service_abi::Open>,
    ioctl: Option<service_abi::Ioctl>, close: Option<service_abi::Close>,
) -> i32 {
    let result = (|| -> Result {
        if owner.is_null() || version != service_abi::VERSION { return Err(EINVAL); }
        let (Some(open), Some(ioctl), Some(close)) = (open, ioctl, close) else { return Err(EINVAL); };
        let mut guard = state()?.lock();
        if guard.is_some() { return Err(EBUSY); }
        *guard = Some(Registration { owner, open, ioctl, close });
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Only the registering owner calls this from failed initialization or module
/// teardown. Linux's module reference protocol excludes any acquired file
/// services, and the registration mutex excludes an unpinned acquisition.
#[export_name = "ihk_os_service_unregister_v1"]
pub(crate) unsafe extern "C" fn unregister(owner: *mut c_void) {
    let mut guard = state().expect("IHK service registry lifetime").lock();
    assert!(guard.as_ref().is_some_and(|entry| entry.owner == owner));
    *guard = None;
}

pub(super) struct FileService {
    context: *mut c_void,
    ioctl: service_abi::Ioctl,
    close: service_abi::Close,
    // This field drops after the explicit close callback has returned to IHK.
    _module: ProviderModule,
}

// SAFETY: The registration contract permits concurrent shared operations and
// final close on any task. The context is never dereferenced by IHK. The file
// publication mutex serializes ownership transfer; VFS final release excludes
// every borrowed callback. The module reference follows this unique owner.
unsafe impl Send for FileService {}

impl FileService {
    pub(super) fn open(slot: u32, generation: u64) -> Result<Self> {
        let (entry, module) = {
            let guard = state()?.lock();
            let entry = (*guard).ok_or(ENODEV)?;
            // SAFETY: The registration mutex prevents unregister. Linux keeps
            // the module allocation until its exit callback has unregistered;
            // try_module_get refuses a module already going away.
            let module = unsafe { ProviderModule::acquire(entry.owner.cast()) }?;
            (entry, module)
        };
        let mut context = ptr::null_mut();
        // SAFETY: The caller's exact OS file lease outlives this attachment;
        // the acquired module pins the callbacks, and context is writable here.
        let status = unsafe { (entry.open)(slot, generation, &mut context) };
        if status != 0 {
            assert!(context.is_null(), "failed mcctrl open retained a context");
            return Err(kernel::error::to_result(status).err().unwrap_or(EIO));
        }
        assert!(!context.is_null(), "successful mcctrl open omitted its context");
        Ok(Self { context, ioctl: entry.ioctl, close: entry.close, _module: module })
    }

    /// # Safety
    /// The enclosing file must remain live until the returned invocation ends.
    /// Its service slot is immutable once published, and final release must
    /// exclude the invocation. No ownership is transferred with these pointers.
    pub(super) unsafe fn borrowed_call(&self) -> (service_abi::Ioctl, *mut c_void) {
        (self.ioctl, self.context)
    }
}

impl Drop for FileService {
    fn drop(&mut self) {
        // SAFETY: The OS file drops this unique context at final release, before
        // its OS lease. Linux excludes ioctls, and _module still pins this code.
        unsafe { (self.close)(self.context) };
    }
}

// SAFETY: Modpost consumes these immutable relocation records for IHK's lifetime.
#[export_name = "__export_symbol_ihk_os_service_register_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static REGISTER_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: register as *const () as *const u8,
};

// SAFETY: Same immutable module-resident export relocation contract.
#[export_name = "__export_symbol_ihk_os_service_unregister_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static UNREGISTER_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0", namespace: *b"MCKERNEL_IHK_V1\0", padding: [0; 4],
    symbol: unregister as *const () as *const u8,
};
