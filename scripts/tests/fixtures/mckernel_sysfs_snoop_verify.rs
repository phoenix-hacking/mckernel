// SPDX-License-Identifier: GPL-2.0-only
//! Exercise the production snooping/mapping bodies on disposable Linux RAM.
//! Diagnostic carriers below are not IHK tokens or resource ownership grants.
use kernel::prelude::*;

#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_tree.rs"]
mod sysfs_tree;

// Only the enclosing OS identity/extent inputs are substituted. The helper
// binds the unchanged production checker, mapping ledger and snooping source.
mod smp_resource {
    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    pub(crate) struct OsToken(pub(crate) u64);
    #[derive(Clone, Copy)]
    pub(crate) struct MemoryExtent {
        pub(crate) physical: u64,
        pub(crate) bytes: u64,
        pub(crate) identity: OsToken,
    }
    impl MemoryExtent {
        pub(crate) fn owner(self) -> Option<OsToken> { Some(self.identity) }
        pub(crate) fn start(self) -> u64 { self.physical }
        pub(crate) fn end(self) -> Result<u64, ()> {
            self.physical.checked_add(self.bytes).ok_or(())
        }
    }
    pub(crate) struct MemoryMap<const N: usize>(pub(crate) [Option<MemoryExtent>; N]);
    impl<const N: usize> MemoryMap<N> {
        pub(crate) fn len(&self) -> usize { self.0.iter().flatten().count() }
        pub(crate) fn extent(&self, index: usize) -> Option<MemoryExtent> {
            self.0.get(index).copied().flatten()
        }
    }
}

// Generated only from the retained exact production extent bodies and module
// paths. The generation recipe and every compiler input are archived.
include!("native-sysfs-snoop-bindings.rs");
use memory_fixture::service::checks::Verifier;
module! {
    type: Verifier,
    name: "mckernel_sysfs_snoop_verify",
    author: "McKernel developers",
    description: "Actual native sysfs snooping and mapping lifetime verification",
    license: "GPL",
}
