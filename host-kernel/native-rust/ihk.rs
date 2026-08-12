// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux IHK host module entry point.
//!
//! The core provider has no legacy module parameters or module dependencies.
//! Behavioral implementation is added only with contract-linked tests, and no
//! path in this crate dispatches into the legacy project C implementation.

use kernel::prelude::*;

const IHK_VERSION: &str = "1.7.0rc4";
const IHK_ABI_VERSION: u16 = 1;
const IHK_PARAMETER_COUNT: usize = 0;
const IHK_DEPENDENCY_COUNT: usize = 0;

// Linux 6.12's Rust `module!` macro does not accept a `version` field. Emit the
// same `.modinfo` record that `MODULE_VERSION()` emits for a loadable module.
#[cfg(MODULE)]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used]
static IHK_VERSION_MODINFO: [u8; 17] = *b"version=1.7.0rc4\0";

// Built-in module metadata is namespaced in `modules.builtin.modinfo`.
#[cfg(not(MODULE))]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used]
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
