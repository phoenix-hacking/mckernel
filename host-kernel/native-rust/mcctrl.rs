// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux mcctrl module entry point.
//!
//! The frozen legacy module exposes no module parameters and depends on `ihk`.
//! This foundation imports the native provider's namespaced lifecycle anchor
//! and deliberately does not manufacture a `depends=ihk` record: modpost must
//! derive that record from the real symbol relocation.
//!
//! The legacy module also owns the mcexec binary-format registration. Linux
//! 6.12 exposes no safe Rust wrapper for `struct linux_binfmt`, so registration
//! remains blocked and is not claimed by this crate.

use core::ffi::c_void;
use kernel::prelude::*;
use mcctrl_process::Context as FileContext;

mod mcctrl_exec;
mod mcctrl_process;
mod mcctrl_vm;
mod user_string;
// Shared byte ABI: SMP and mcctrl intentionally consume different operations.
#[allow(dead_code)]
mod application_image;

#[allow(dead_code, unreachable_pub)]
#[path = "abi/x86_64.rs"]
mod abi;
#[allow(dead_code)]
#[path = "abi/os_service.rs"]
mod service_abi;
#[allow(dead_code)]
#[path = "abi/application.rs"]
mod application_abi;

const MCCTRL_FOUNDATION_VERSION: u16 = 1;
const MCCTRL_PARAMETER_COUNT: usize = 0;
const MCCTRL_DECLARED_DEPENDENCY_COUNT: usize = 1;
const MCCTRL_IHK_IMPORT_STATUS: &str = "source-bound-anchor";
const MCCTRL_BINFMT_STATUS: &str = "blocked-no-safe-rust-api";

// SAFETY: The provider exports this immutable byte for the entire dependent
// module lifetime. Modpost resolves the symbol through MCKERNEL_IHK_V1 before
// initialization, and callers may only read it as a dependency anchor.
extern "Rust" {
    #[link_name = "ihk_provider_lifecycle_v1"]
    static IHK_PROVIDER_LIFECYCLE_V1: u8;
}

// SAFETY: IHK is a real module dependency in the declared namespace. Registration
// borrows this module and its callback identities until our Drop unregisters;
// the narrow topology query validates all scalar identities before dispatch.
extern "C" {
    fn ihk_os_service_register_v1(
        owner: *mut c_void,
        version: u32,
        open: Option<service_abi::Open>,
        ioctl: Option<service_abi::Ioctl>,
        close: Option<service_abi::Close>,
    ) -> i32;
    fn ihk_os_service_unregister_v1(owner: *mut c_void);
    fn ihk_os_topology_query_v1(slot: u32, generation: u64, command: u32) -> i64;
}

// SAFETY: IHK supplies an exact live OS identity, retains this module and gives
// exclusive writable output storage. Pinned mutexes protect process bindings
// during concurrent ioctls; no user memory or independently running work escapes.
unsafe extern "C" fn open(slot: u32, generation: u64, output: *mut *mut c_void) -> i32 {
    let context = match FileContext::new(slot, generation) {
        Ok(context) => context,
        Err(error) => return error.to_errno(),
    };
    let context = match Box::new(context, GFP_KERNEL) {
        Ok(context) => context,
        Err(_) => return ENOMEM.to_errno(),
    };
    // SAFETY: IHK initializes the output null and owns it through this call.
    unsafe { output.write(Box::into_raw(context).cast()) };
    pr_info!(
        "application_file=open os={} generation={}\n",
        slot,
        generation
    );
    0
}

// SAFETY: IHK retains the successful context and module pin, excludes final
// release and supplies normalized compat arguments. No service/file/OS lock
// crosses this call; the IHK topology query may take its short operation lock.
unsafe extern "C" fn ioctl(context: *mut c_void, command: u32, argument: u64, compat: u32) -> i64 {
    if compat > 1 || (compat == 1 && argument > u32::MAX as u64) {
        return EINVAL.to_errno() as i64;
    }
    // SAFETY: Successful open supplied this object and its interior locks,
    // live until final close and shared safely by concurrent ioctl borrows.
    let context = unsafe { &*context.cast::<FileContext>() };
    let operation = match command {
        abi::MCEXEC_UP_GET_CREDV => Some(mcctrl_exec::credentials(argument as usize)),
        abi::MCEXEC_UP_STRNCPY_FROM_USER => {
            Some(mcctrl_exec::copy_string(argument as usize, compat == 1))
        }
        abi::MCEXEC_UP_OPEN_EXEC => Some(context.open_executable(argument as usize)),
        abi::MCEXEC_UP_CLOSE_EXEC => Some(context.close_executable()),
        abi::MCEXEC_UP_CREATE_PPD => Some(context.create_process(argument as usize, compat == 1)),
        abi::MCEXEC_UP_PREPARE_IMAGE => Some(context.prepare_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_START_IMAGE => Some(context.start_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_TRANSFER => Some(context.transfer_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_WAIT_SYSCALL => Some(context.wait_syscall(argument as usize, compat == 1)),
        abi::MCEXEC_UP_RET_SYSCALL => Some(context.return_syscall(argument as usize, compat == 1)),
        abi::MCEXEC_UP_RELEASE_USER_SPACE => {
            Some(context.clear_user_space(argument as usize, compat == 1))
        }
        _ => None,
    };
    if let Some(result) = operation {
        return result.map_or_else(|error| error.to_errno() as i64, |value| value as i64);
    }
    if !service_abi::topology_query(command) {
        return EINVAL.to_errno() as i64;
    }
    // SAFETY: The dependency owns the checked scalar query for our lifetime.
    let value = unsafe { ihk_os_topology_query_v1(context.slot, context.generation, command) };
    // Adapt the existing mcctrl_control_get_cpu_body_result check. GET_NODES
    // returns the retained boot node count, matching its existing Rust helper.
    if command == abi::MCEXEC_UP_GET_CPU && value == 0 {
        EINVAL.to_errno() as i64
    } else {
        value
    }
}

// SAFETY: IHK transfers back the unique Box after every ioctl has finished,
// retaining both the OS generation and our module until this returns.
unsafe extern "C" fn close(context: *mut c_void) {
    // SAFETY: This is exactly the allocation returned by successful open.
    let context = unsafe { Box::from_raw(context.cast::<FileContext>()) };
    pr_info!(
        "application_file=close os={} generation={}\n",
        context.slot,
        context.generation
    );
    drop(context);
}

// Declare the namespace consumed by the provider-anchor relocation above.
// This is MODULE_IMPORT_NS() metadata, not a fabricated module dependency.
#[cfg(MODULE)]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used(compiler)]
static MCCTRL_IHK_IMPORT_NAMESPACE: [u8; 26] = *b"import_ns=MCKERNEL_IHK_V1\0";

#[cfg(not(MODULE))]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used(compiler)]
static MCCTRL_BUILTIN_IHK_IMPORT_NAMESPACE: [u8; 33] = *b"mcctrl.import_ns=MCKERNEL_IHK_V1\0";

module! {
    type: McctrlModule,
    name: "mcctrl",
    license: "GPL v2",
}

struct McctrlModule {
    _processes: mcctrl_process::Registry,
}

impl kernel::Module for McctrlModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let processes = mcctrl_process::Registry::new()?;
        // SAFETY: The provider exports this immutable byte in the declared
        // namespace. The volatile read preserves the relocation that makes
        // modpost derive the module dependency and loader unload ordering.
        let _ = unsafe { core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1)) };
        // SAFETY: THIS_MODULE and all callbacks remain resident until Drop
        // unregisters. A failed registration publishes no callbacks. No fallible
        // initialization follows successful publication.
        kernel::error::to_result(unsafe {
            ihk_os_service_register_v1(
                THIS_MODULE.as_ptr().cast(),
                service_abi::VERSION,
                Some(open),
                Some(ioctl),
                Some(close),
            )
        })?;
        pr_info!("application_service=registered abi=1 topology_queries=2\n");
        pr_info!(
            "lifecycle=load foundation={} parameters={} declared_dependencies={} ihk_import={} binfmt={}\n",
            MCCTRL_FOUNDATION_VERSION,
            MCCTRL_PARAMETER_COUNT,
            MCCTRL_DECLARED_DEPENDENCY_COUNT,
            MCCTRL_IHK_IMPORT_STATUS,
            MCCTRL_BINFMT_STATUS,
        );
        Ok(Self {
            _processes: processes,
        })
    }
}

impl Drop for McctrlModule {
    fn drop(&mut self) {
        // SAFETY: File-owned module references exclude entry to Drop while any
        // context/callback is live. The IHK registry serializes a racing acquire.
        unsafe { ihk_os_service_unregister_v1(THIS_MODULE.as_ptr().cast()) };
        pr_info!("application_service=unregistered abi=1\n");
        pr_info!(
            "lifecycle=unload foundation={} parameters={} declared_dependencies={} ihk_import={} binfmt={}\n",
            MCCTRL_FOUNDATION_VERSION,
            MCCTRL_PARAMETER_COUNT,
            MCCTRL_DECLARED_DEPENDENCY_COUNT,
            MCCTRL_IHK_IMPORT_STATUS,
            MCCTRL_BINFMT_STATUS,
        );
    }
}
