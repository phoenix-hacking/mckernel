// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux mcctrl module entry point.
//!
//! The frozen legacy module exposes no module parameters and depends on `ihk`.
//! This foundation declares the future IHK symbol namespace, but deliberately
//! does not manufacture a `depends=ihk` record: Kbuild must derive that record
//! from a real imported provider symbol. The selected Linux 6.12 Rust surface
//! does not yet provide a supported custom module-symbol export API.
//!
//! The legacy module also owns the mcexec binary-format registration. Linux
//! 6.12 exposes no safe Rust wrapper for `struct linux_binfmt`, so registration
//! remains blocked and is not claimed by this crate.

use kernel::prelude::*;

const MCCTRL_FOUNDATION_VERSION: u16 = 1;
const MCCTRL_PARAMETER_COUNT: usize = 0;
const MCCTRL_DECLARED_DEPENDENCY_COUNT: usize = 1;
const MCCTRL_IHK_IMPORT_STATUS: &str = "namespace-only";
const MCCTRL_BINFMT_STATUS: &str = "blocked-no-safe-rust-api";

// Declare the namespace that future real IHK symbol imports must consume.
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
