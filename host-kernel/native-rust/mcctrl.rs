// SPDX-License-Identifier: GPL-2.0
//! Native Rust-for-Linux mcctrl module entry point.

use kernel::prelude::*;

module! {
    type: McctrlModule,
    name: "mcctrl",
    author: "McKernel Rust port",
    description: "Native Rust McKernel host control module",
    license: "GPL v2",
}

struct McctrlModule;

impl kernel::Module for McctrlModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        pr_info!("mcctrl: native Rust host module staging loaded\n");
        Ok(Self)
    }
}

impl Drop for McctrlModule {
    fn drop(&mut self) {
        pr_info!("mcctrl: native Rust host module staging unloaded\n");
    }
}
