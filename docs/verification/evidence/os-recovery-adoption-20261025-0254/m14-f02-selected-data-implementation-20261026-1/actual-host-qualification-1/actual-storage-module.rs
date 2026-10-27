#[cfg(process_global_storage_candidate)]
mod process_global_storage {
    use core::mem::{align_of, offset_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::{AbiListHead, CInt, IhkSpinlock, McsRwlockLock};

    // Preserve the existing plain C int ABI and boot defaults. Initialization
    // owns writes before normal scheduler/application consumers observe these
    // flags; existing extern accesses retain their current synchronization.
    // Keep plain mutable storage: changing this to an AtomicI32, bool, or a
    // lazy initializer would change the original C/Rust access contract.
    const _: [(); 4] = [(); size_of::<CInt>()];
    const _: [(); 4] = [(); align_of::<CInt>()];

    #[no_mangle]
    pub static mut idle_halt: CInt = 0;

    #[no_mangle]
    pub static mut allow_oversubscribe: CInt = 0;

    #[no_mangle]
    pub static mut time_sharing: CInt = 1;

    // These are the existing owned ABI types, not replacement representations.
    // The independent genuine-header witness must qualify this exact profile.
    const _: [(); 4] = [(); size_of::<IhkSpinlock>()];
    const _: [(); 4] = [(); align_of::<IhkSpinlock>()];
    const _: [(); 0] = [(); offset_of!(IhkSpinlock, head_tail)];
    const _: [(); 64] = [(); size_of::<McsRwlockLock>()];
    const _: [(); 64] = [(); align_of::<McsRwlockLock>()];
    const _: [(); 0] = [(); offset_of!(McsRwlockLock, slock)];
    const _: [(); 16] = [(); size_of::<AbiListHead>()];
    const _: [(); 8] = [(); align_of::<AbiListHead>()];
    const _: [(); 0] = [(); offset_of!(AbiListHead, next)];
    const _: [(); 8] = [(); offset_of!(AbiListHead, prev)];

    // The genuine C list type has alignment 8, while its retained tentative
    // global symbol requires alignment 16. Preserve that storage requirement
    // around the unchanged owned type, with the original payload at offset 0.
    #[repr(C, align(16))]
    pub struct ResourceSetListStorage {
        head: AbiListHead,
    }

    const _: [(); 16] = [(); size_of::<ResourceSetListStorage>()];
    const _: [(); 16] = [(); align_of::<ResourceSetListStorage>()];
    const _: [(); 0] = [(); offset_of!(ResourceSetListStorage, head)];

    // Preserve original BSS state: NULL links, not an eagerly self-linked list.
    // Extern consumers still use AbiListHead at this exact exported address.
    // proc_init owns the original head/lock initialization and publication;
    // later mutation retains the existing resource_set_lock exclusion.
    #[export_name = "resource_set_list"]
    pub static mut RESOURCE_SET_LIST_STORAGE: ResourceSetListStorage = ResourceSetListStorage {
        head: AbiListHead { next: null_mut(), prev: null_mut() },
    };

    // Preserve the real 64-byte aligned MCS lock and its zero initial state.
    // The existing initializer and MCS bridge own all runtime lock operations.
    #[no_mangle]
    pub static mut resource_set_lock: McsRwlockLock = McsRwlockLock {
        slock: IhkSpinlock { head_tail: 0 },
    };

    // The original reservation lock's zero ticket state is valid before use.
    // Existing scheduler/affinity callers retain their IRQ and lock pairing.
    #[no_mangle]
    pub static mut runq_reservation_lock: IhkSpinlock = IhkSpinlock { head_tail: 0 };
}
