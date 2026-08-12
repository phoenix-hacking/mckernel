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
mod ikc_master;
#[allow(dead_code)]
mod ihk_ioctl;
#[allow(dead_code)]
mod page_allocator;
#[allow(dead_code)]
mod page_owner_registry;

use kernel::prelude::*;

const IHK_VERSION: &str = "1.7.0rc4";
const IHK_ABI_VERSION: u16 = 1;
const IHK_PARAMETER_COUNT: usize = 0;
const IHK_DEPENDENCY_COUNT: usize = 0;

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
        pr_info!(
            "lifecycle=unload version={} abi={} parameters={} dependencies={}\n",
            IHK_VERSION,
            IHK_ABI_VERSION,
            IHK_PARAMETER_COUNT,
            IHK_DEPENDENCY_COUNT,
        );
    }
}
