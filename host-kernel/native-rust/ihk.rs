// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux IHK host module entry point.
//!
//! The core provider has no legacy module parameters or module dependencies.
//! Behavioral implementation is added only with contract-linked tests, and no
//! path in this crate dispatches into the legacy project C implementation.

// These source-bound foundations are compiled into the provider now, while
// their externally reachable create/destroy entry points remain evidence-gated.
#[allow(dead_code, unreachable_pub)]
#[path = "abi/x86_64.rs"]
mod abi;
#[allow(dead_code)]
mod ikc_queue;
#[allow(dead_code)]
mod os_registry;
#[allow(dead_code)]
mod device_registry;
#[allow(dead_code)]
mod ikc_master;
#[allow(dead_code)]
mod ihk_ioctl;
#[allow(dead_code)]
mod page_allocator;
#[allow(dead_code)]
mod page_owner_registry;

use core::sync::atomic::{AtomicPtr, Ordering};

use kernel::prelude::*;
use self::device_registry::{IHK_DEVICE_REGISTRY, SharePolicy};

const IHK_VERSION: &str = "1.7.0rc4";
const IHK_ABI_VERSION: u16 = 1;
const IHK_PARAMETER_COUNT: usize = 0;
const IHK_DEPENDENCY_COUNT: usize = 0;

const IHK_SMP_PROVIDER_CALLBACK_ABI_V1: u32 = 1;
const IHK_SMP_PROVIDER_FLAG_SHARED: u32 = 1;
const EUCLEAN: i64 = -117;

// SAFETY: This C-ABI callback has no arguments, borrows no caller memory, and
// returns only a scalar status consumed before provider publication.
type IhkSmpProviderInitV2 = extern "C" fn() -> i32;
// SAFETY: This C-ABI callback has no arguments, borrows no caller memory, and
// returns only after the dependent has completed its scalar lifecycle exit.
type IhkSmpProviderExitV2 = extern "C" fn();

// The v2 lease retains only the exact exit function address.  No provider
// object, private pointer, operation callback, or Rust layout crosses the ABI.
// The registry phase remains the lifecycle authority; this atomic binds the
// callback identity to the one live v2 token and is cleared only after the
// unpublishing guard commits the slot to vacant.
static IHK_SMP_PROVIDER_EXIT_V2: AtomicPtr<()> = AtomicPtr::new(core::ptr::null_mut());

fn provider_init_status(status: i32) -> i64 {
    match status {
        0 => 0,
        -2 | -12 | -16 | -22 | -75 | -116 | -117 => status as i64,
        _ => EUCLEAN,
    }
}

// Linux 6.12 recognizes exports through a relocation in `.export_symbol` and
// generates the final ksymtab entry during modpost.  This data-only anchor
// gives native consumers a real module reference without exposing lifecycle
// behavior or involving a project-owned C shim.
#[doc(hidden)]
#[repr(C, align(8))]
pub struct IhkExportSymbolRecord {
    license: [u8; 4],
    namespace: [u8; 16],
    padding: [u8; 4],
    symbol: *const u8,
}

// SAFETY: The record and its target are immutable for the module lifetime.
unsafe impl Sync for IhkExportSymbolRecord {}

const _: [(); 32] = [(); core::mem::size_of::<IhkExportSymbolRecord>()];
const _: [(); 8] = [(); core::mem::align_of::<IhkExportSymbolRecord>()];

#[doc(hidden)]
// SAFETY: This immutable byte is the provider's read-only ABI anchor. Consumers
// must import it through MCKERNEL_IHK_V1 and may not treat its value as state.
#[export_name = "ihk_provider_lifecycle_v1"]
pub static IHK_PROVIDER_LIFECYCLE_V1: u8 = 1;

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the namespaced anchor; neither the record nor its target is mutated in Rust.
#[export_name = "__export_symbol_ihk_provider_lifecycle_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_PROVIDER_LIFECYCLE_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1),
};

#[doc(hidden)]
// SAFETY: This C-ABI scalar boundary owns no caller memory.  A positive return
// is a versioned opaque token for the single published minor-zero provider;
// every failure is a negative errno and leaves no live reservation behind.
#[export_name = "ihk_smp_provider_attach_v1"]
// SAFETY: This exported C ABI accepts no caller-owned state and returns only
// the registry-owned scalar token or a negative errno.
pub extern "C" fn ihk_smp_provider_attach_v1() -> i64 {
    if !IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire).is_null() {
        return EUCLEAN;
    }
    let token = match IHK_DEVICE_REGISTRY.attach_provider_token() {
        Ok(token) => token,
        Err(error) => return error.errno() as i64,
    };
    pr_info!("provider_lease=attach status=live minor=0\n");
    token
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar attach function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_attach_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_ATTACH_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_attach_v1 as *const () as *const u8,
};

#[doc(hidden)]
// SAFETY: This C-ABI scalar boundary consumes the exact v1 token owned by the
// reviewed namespaced SMP dependent.  The token is an ownership receipt, not
// a security boundary against other privileged in-kernel code.  Any malformed,
// stale, duplicated, busy, or corrupt state fails stop before unload succeeds.
#[export_name = "ihk_smp_provider_detach_v1"]
// SAFETY: This exported C ABI accepts only the opaque scalar issued by attach
// and cannot return while the owned provider entry remains live.
pub extern "C" fn ihk_smp_provider_detach_v1(token: i64) {
    if !IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire).is_null() {
        panic!("v1 provider detach attempted while a v2 callback lease is live");
    }
    let handle = IHK_DEVICE_REGISTRY.retire_owned_provider_token(token);
    pr_info!(
        "provider_lease=detach status=vacant minor={} generation={}\n",
        handle.minor(),
        handle.generation(),
    );
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar detach function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_detach_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_DETACH_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_detach_v1 as *const () as *const u8,
};

#[doc(hidden)]
// SAFETY: This C ABI accepts only scalars and nullable C-ABI function pointers.
// The reviewed SMP dependent owns both callback targets for the full returned
// lease lifetime.  Initialization runs while the registry slot is Publishing;
// only a zero result permits publication.  Every failed path aborts or retires
// its reservation and leaves no retained callback identity.
#[export_name = "ihk_smp_provider_attach_v2"]
// SAFETY: The exact nullable function-pointer ABI is validated before either
// callback is invoked; no Rust object or caller-owned data crosses the export.
pub extern "C" fn ihk_smp_provider_attach_v2(
    callback_abi: u32,
    flags: u32,
    init: Option<IhkSmpProviderInitV2>,
    exit: Option<IhkSmpProviderExitV2>,
) -> i64 {
    if callback_abi != IHK_SMP_PROVIDER_CALLBACK_ABI_V1
        || flags != IHK_SMP_PROVIDER_FLAG_SHARED
    {
        return -22;
    }
    let (init, exit) = match (init, exit) {
        (Some(init), Some(exit)) => (init, exit),
        _ => return -22,
    };

    let reservation = match IHK_DEVICE_REGISTRY.reserve(SharePolicy::Shared) {
        Ok(reservation) => reservation,
        Err(error) => return error.errno() as i64,
    };
    if reservation.handle().minor() != 0 {
        return match reservation.abort() {
            Ok(()) => -16,
            Err(error) => error.errno() as i64,
        };
    }

    let init_status = provider_init_status(init());
    if init_status != 0 {
        return match reservation.abort() {
            Ok(()) => init_status,
            Err(error) => error.errno() as i64,
        };
    }

    let exit_pointer = exit as *const () as *mut ();
    if IHK_SMP_PROVIDER_EXIT_V2
        .compare_exchange(
            core::ptr::null_mut(),
            exit_pointer,
            Ordering::AcqRel,
            Ordering::Acquire,
        )
        .is_err()
    {
        exit();
        return match reservation.abort() {
            Ok(()) => EUCLEAN,
            Err(error) => error.errno() as i64,
        };
    }

    let handle = match reservation.publish() {
        Ok(handle) => handle,
        Err(error) => {
            exit();
            IHK_SMP_PROVIDER_EXIT_V2
                .compare_exchange(
                    exit_pointer,
                    core::ptr::null_mut(),
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .unwrap_or_else(|_| {
                    panic!("v2 provider callback identity changed after publish failure")
                });
            panic!(
                "v2 provider publication transition failed: errno={}",
                error.errno(),
            );
        }
    };
    let token = match IHK_DEVICE_REGISTRY.encode_provider_token(handle) {
        Ok(token) => token,
        Err(error) => {
            let unregister = IHK_DEVICE_REGISTRY
                .begin_unregister(handle)
                .unwrap_or_else(|cleanup| {
                    panic!(
                        "v2 provider publication cleanup failed: errno={}",
                        cleanup.errno(),
                    )
                });
            exit();
            unregister.commit().unwrap_or_else(|cleanup| {
                panic!(
                    "v2 provider publication retirement failed: errno={}",
                    cleanup.errno(),
                )
            });
            IHK_SMP_PROVIDER_EXIT_V2
                .compare_exchange(
                    exit_pointer,
                    core::ptr::null_mut(),
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .unwrap_or_else(|_| panic!("v2 provider callback identity changed"));
            return error.errno() as i64;
        }
    };

    pr_info!("provider_lease=attach status=live minor=0 callback_abi=1\n");
    token
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the callback-bound attach function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_attach_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_ATTACH_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_attach_v2 as *const () as *const u8,
};

#[doc(hidden)]
// SAFETY: The exact callback identity was retained before the named token was
// published.  The unregister guard first makes the provider Unpublishing and
// rejects new references.  The callback executes only after all existing open
// and OS references have drained, remains bound throughout the call, and is
// cleared only after exit completes and the slot commits to Vacant.
#[export_name = "ihk_smp_provider_detach_v2"]
// SAFETY: The token and exact retained exit identity name the sole live v2
// lease; invariant violations fail stop before provider retirement can return.
pub extern "C" fn ihk_smp_provider_detach_v2(
    token: i64,
    exit: Option<IhkSmpProviderExitV2>,
) {
    let exit = exit.unwrap_or_else(|| panic!("v2 provider detach omitted exit callback"));
    let exit_pointer = exit as *const () as *mut ();
    if IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire) != exit_pointer {
        panic!("v2 provider detach callback identity mismatch");
    }

    let handle = IHK_DEVICE_REGISTRY
        .decode_provider_token(token)
        .unwrap_or_else(|error| {
            panic!("v2 provider token rejected: errno={}", error.errno())
        });
    let unregister = IHK_DEVICE_REGISTRY
        .begin_unregister(handle)
        .unwrap_or_else(|error| {
            panic!("v2 provider unpublish failed: errno={}", error.errno())
        });
    let snapshot = IHK_DEVICE_REGISTRY.snapshot(handle).unwrap_or_else(|error| {
        panic!("v2 provider unpublish snapshot failed: errno={}", error.errno())
    });
    if snapshot.provider_references != 0 || snapshot.os_references != 0 {
        panic!(
            "v2 provider detach before reference drain: open={} os={}",
            snapshot.provider_references,
            snapshot.os_references,
        );
    }

    exit();
    unregister.commit().unwrap_or_else(|error| {
        panic!("v2 provider retirement failed: errno={}", error.errno())
    });
    IHK_SMP_PROVIDER_EXIT_V2
        .compare_exchange(
            exit_pointer,
            core::ptr::null_mut(),
            Ordering::AcqRel,
            Ordering::Acquire,
        )
        .unwrap_or_else(|_| panic!("v2 provider callback identity changed during exit"));
    pr_info!(
        "provider_lease=detach status=vacant minor={} generation={} callback_abi=1\n",
        handle.minor(),
        handle.generation(),
    );
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the callback-bound detach function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_detach_v2"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_DETACH_V2_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_detach_v2 as *const () as *const u8,
};

#[doc(hidden)]
// SAFETY: This C-ABI boundary accepts only the scalar device minor and returns
// either a positive opaque provider-generation receipt or a negative errno.
// The receipt does not encode a pointer or Rust layout.  Its open reference is
// owned exactly once by the caller's non-Copy per-file wrapper.
#[export_name = "ihk_smp_provider_open_v1"]
// SAFETY: This exported C ABI carries only a u32 argument and i64 result;
// every expected failure becomes a negative errno and no unwind may cross it.
pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {
    let receipt = match IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize) {
        Ok(receipt) => receipt,
        Err(error) => {
            return error.errno() as i64;
        }
    };
    pr_info!("provider_open=acquire status=live minor=0\n");
    receipt
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar open function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_open_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_OPEN_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_open_v1 as *const () as *const u8,
};

#[doc(hidden)]
// SAFETY: This C-ABI boundary accepts only a positive scalar generation token
// returned by open.  Shared opens intentionally receive the same scalar, so
// the trusted caller's non-Copy per-file owners must keep calls count-balanced;
// malformed, stale, and zero-reference closes fail stop.
#[export_name = "ihk_smp_provider_close_v1"]
// SAFETY: This exported C ABI carries only an i64 receipt; detectable ownership
// faults fail stop inside the kernel and no unwind may cross the module boundary.
pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {
    let _ = IHK_DEVICE_REGISTRY.release_owned_open_token(receipt);
    pr_info!("provider_open=release status=complete minor=0\n");
}

#[doc(hidden)]
// SAFETY: Linux modpost consumes this immutable relocation record to publish
// the scalar close function in MCKERNEL_IHK_V1 for the provider lifetime.
#[export_name = "__export_symbol_ihk_smp_provider_close_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub static IHK_SMP_PROVIDER_CLOSE_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\0",
    namespace: *b"MCKERNEL_IHK_V1\0",
    padding: [0; 4],
    symbol: ihk_smp_provider_close_v1 as *const () as *const u8,
};

// Linux 6.12's Rust `module!` macro does not accept a `version` field. Emit the
// same `.modinfo` record that `MODULE_VERSION()` emits for a loadable module.
#[cfg(MODULE)]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used(compiler)]
static IHK_VERSION_MODINFO: [u8; 17] = *b"version=1.7.0rc4\0";

// Built-in module metadata is namespaced in `modules.builtin.modinfo`.
#[cfg(not(MODULE))]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used(compiler)]
static IHK_BUILTIN_VERSION_MODINFO: [u8; 21] = *b"ihk.version=1.7.0rc4\0";

module! {
    type: IhkModule,
    name: "ihk",
    author: "McKernel Rust port",
    description: "Native Rust IHK host core",
    license: "GPL v2",
}

struct IhkModule;

impl kernel::Module for IhkModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        pr_info!(
            "lifecycle=load version={} abi={} parameters={} dependencies={}\n",
            IHK_VERSION,
            IHK_ABI_VERSION,
            IHK_PARAMETER_COUNT,
            IHK_DEPENDENCY_COUNT,
        );
        Ok(Self)
    }
}

impl Drop for IhkModule {
    fn drop(&mut self) {
        if !IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire).is_null() {
            pr_err!("provider_callback=not-empty callback_abi=1\n");
        }
        match IHK_DEVICE_REGISTRY.active_count() {
            Ok(0) => pr_info!("provider_registry=empty active=0\n"),
            Ok(active) => pr_err!("provider_registry=not-empty active={}\n", active),
            Err(error) => pr_err!(
                "provider_registry=corrupt errno={}\n",
                error.errno(),
            ),
        }
        pr_info!(
            "lifecycle=unload version={} abi={} parameters={} dependencies={}\n",
            IHK_VERSION,
            IHK_ABI_VERSION,
            IHK_PARAMETER_COUNT,
            IHK_DEPENDENCY_COUNT,
        );
    }
}
