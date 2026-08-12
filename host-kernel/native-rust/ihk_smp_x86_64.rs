// SPDX-License-Identifier: (BSD-2-Clause OR GPL-2.0)
//! Native Rust-for-Linux x86_64 IHK SMP module entry point.

use kernel::prelude::*;

module! {
    type: IhkSmpModule,
    name: "ihk_smp_x86_64",
    author: "McKernel Rust port",
    description: "Native Rust x86_64 IHK SMP host driver",
    license: "Dual BSD/GPL",
}

struct IhkSmpModule;

impl kernel::Module for IhkSmpModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        pr_info!("ihk_smp_x86_64: native Rust host module staging loaded\n");
        Ok(Self)
    }
}

impl Drop for IhkSmpModule {
    fn drop(&mut self) {
        pr_info!("ihk_smp_x86_64: native Rust host module staging unloaded\n");
    }
}
