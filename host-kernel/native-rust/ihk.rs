// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux IHK host module entry point.
//!
//! Behavioral implementation is added only with contract-linked tests. This
//! module intentionally contains no dispatch path into the legacy project C
//! implementation.

use kernel::prelude::*;

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
        pr_info!("ihk: native Rust host module staging loaded\n");
        Ok(Self)
    }
}

impl Drop for IhkModule {
    fn drop(&mut self) {
        pr_info!("ihk: native Rust host module staging unloaded\n");
    }
}
