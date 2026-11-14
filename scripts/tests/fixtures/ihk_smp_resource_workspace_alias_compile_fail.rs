#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;

#[cfg(os_token_forge)]
fn forge_os_token() -> smp_resource::OsToken {
    // Direct field construction cannot bypass the versioned IHK lease proof.
    smp_resource::OsToken {
        slot: 0,
        generation: 1,
    }
}

#[cfg(os_token_forge)]
fn main() {
    let _forged = forge_os_token();
}

#[cfg(workspace_alias)]
fn main() {
    let mut memory = smp_resource::MemoryMap::<4>::new();
    // A live map is not staging storage.  This must fail to type-check, which
    // also prevents safe code from aliasing the active and candidate maps.
    let _ = memory.prepare_insert_free(0x1000, 0x1000, 0, &mut memory);
}

#[cfg(lease_without_proof)]
fn main() {
    // Bounds alone cannot justify a live OS generation. This call requires
    // the explicit contract of IHK's checked, module-pinned callback.
    let _ = smp_resource::OsToken::from_ihk_lease_v2(0, 1);
}

#[cfg(not(any(os_token_forge, workspace_alias, lease_without_proof)))]
fn main() {}
