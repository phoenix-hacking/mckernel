#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;

#[cfg(os_token_forge)]
fn forge_os_token() -> smp_resource::OsToken {
    // Production code cannot mint an OS lease without the future provider ABI.
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

#[cfg(not(any(os_token_forge, workspace_alias)))]
fn main() {}
