// SPDX-License-Identifier: GPL-2.0-only
//! Bind native sysfs ownership to the actual generation-owned mcos device.

use core::ffi::c_void;
use kernel::{bindings, prelude::*};

use super::sysfs_tree::Tree;
use super::{smp_resource::OsToken, sysfs_objects::Directory};

// SAFETY: IHK's namespaced export synchronously lends its actual Linux kobject
// while a generation-checked registry lease excludes device unregister.
extern "C" {
    fn ihk_os_with_kobject_v1(
        slot: u32,
        generation: u64,
        callback_abi: u32,
        context: *mut c_void,
        callback: Option<unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32>,
    ) -> i32;
}

// SAFETY: Only root calls this callback, with a unique stack-local output slot.
// IHK lends a registered kernel parent with removal excluded until return.
unsafe extern "C" fn attach(context: *mut c_void, parent: *mut c_void) -> i32 {
    // SAFETY: The synchronous borrow above satisfies under_kobject. Linux takes
    // an explicit parent reference on successful add; the bare pointer does
    // not escape. root's caller must retire the child before backend release.
    match unsafe {
        Directory::under_kobject(parent.cast::<bindings::kobject>(), kernel::c_str!("sys"))
    } {
        Ok(directory) => {
            // SAFETY: root owns this initialized None for the entire call.
            unsafe { *context.cast::<Option<Directory>>() = Some(directory) };
            0
        }
        Err(error) => error.to_errno(),
    }
}

/// Create the legacy tree's /sys root under this OS's actual Linux device.
/// This owns a namespace only; it does not complete SYSFS_REQ_SETUP.
///
/// # Safety
/// The caller holds IHK's exact OS lease, operation lock and SMP module pin.
/// Store the result in this OS's backend ownership graph, retiring it before
/// backend release succeeds. Once a CPU starts, retain it until proven shutdown.
pub(super) unsafe fn root(owner: OsToken) -> Result<Tree> {
    let mut directory = None;
    // SAFETY: The stack output and module-resident callback remain live. IHK
    // checks the exact generation before lending a registered device parent.
    kernel::error::to_result(unsafe {
        ihk_os_with_kobject_v1(
            owner.slot(),
            owner.generation(),
            1,
            (&mut directory as *mut Option<Directory>).cast(),
            Some(attach),
        )
    })?;
    Tree::new(directory.ok_or(EIO)?)
}
