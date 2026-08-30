#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;

use smp_resource::{MemoryMap, OsToken};

fn forge_os_token() -> OsToken {
    // Production code cannot mint an OS lease without the future provider ABI.
    OsToken {
        slot: 0,
        generation: 1,
    }
}

fn main() {
    let _forged = forge_os_token();
    let mut memory = MemoryMap::<4>::new();
    // A live map is not staging storage.  This must fail to type-check, which
    // also prevents safe code from aliasing the active and candidate maps.
    let _ = memory.prepare_insert_free(0x1000, 0x1000, 0, &mut memory);
}
