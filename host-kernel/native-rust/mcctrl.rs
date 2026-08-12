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

use kernel::prelude::*;

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

// Declare the namespace consumed by the provider-anchor relocation above.
// This is MODULE_IMPORT_NS() metadata, not a fabricated module dependency.
#[cfg(MODULE)]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used]
static MCCTRL_IHK_IMPORT_NAMESPACE: [u8; 26] = *b"import_ns=MCKERNEL_IHK_V1\0";

#[cfg(not(MODULE))]
#[doc(hidden)]
#[link_section = ".modinfo"]
#[used]
static MCCTRL_BUILTIN_IHK_IMPORT_NAMESPACE: [u8; 33] =
    *b"mcctrl.import_ns=MCKERNEL_IHK_V1\0";

module! {
    type: McctrlModule,
    name: "mcctrl",
    license: "GPL v2",
}

struct McctrlModule;

impl kernel::Module for McctrlModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        // SAFETY: The provider exports this immutable byte in the declared
        // namespace. The volatile read preserves the relocation that makes
        // modpost derive the module dependency and loader unload ordering.
        let _ = unsafe {
            core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1))
        };
        pr_info!(
            "lifecycle=load foundation={} parameters={} declared_dependencies={} ihk_import={} binfmt={}\n",
            MCCTRL_FOUNDATION_VERSION,
            MCCTRL_PARAMETER_COUNT,
            MCCTRL_DECLARED_DEPENDENCY_COUNT,
            MCCTRL_IHK_IMPORT_STATUS,
            MCCTRL_BINFMT_STATUS,
        );
        Ok(Self)
    }
}

impl Drop for McctrlModule {
    fn drop(&mut self) {
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
