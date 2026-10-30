// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Same 46 word witness; real qualified existing CallerForkOutcome path.
    const _: () = {
        assert!(size_of::<crate::abi::IhkAtomic>() == size_of::<core::sync::atomic::AtomicI32>());
        assert!(core::mem::align_of::<crate::abi::IhkAtomic>() == core::mem::align_of::<core::sync::atomic::AtomicI32>());
        assert!(core::mem::offset_of!(crate::abi::IhkAtomic, counter) == 0);
        assert!(size_of::<crate::abi::McsRwlockLock>() == size_of::<crate::lock_helpers::McsRwlockLock>());
        assert!(core::mem::align_of::<crate::abi::McsRwlockLock>() == core::mem::align_of::<crate::lock_helpers::McsRwlockLock>());
    };

    // Compiler-only real C/Rust layout view; no runtime ownership getter.
    #[no_mangle]
    #[used]
    pub static f03_do_fork_Rust_ABI_v1: [CULong; 46] = [
        size_of::<crate::abi::Thread>() as CULong,
        core::mem::align_of::<crate::abi::Thread>() as CULong,
        core::mem::offset_of!(crate::abi::Thread, proc) as CULong,
        core::mem::offset_of!(crate::abi::Thread, vm) as CULong,
        core::mem::offset_of!(crate::abi::Thread, cpu_id) as CULong,
        core::mem::offset_of!(crate::abi::Thread, uctx) as CULong,
        core::mem::offset_of!(crate::abi::Thread, clone_pthread_start_routine) as CULong,
        core::mem::offset_of!(crate::abi::Thread, mod_clone) as CULong,
        core::mem::offset_of!(crate::abi::Thread, pthread_routine) as CULong,
        core::mem::offset_of!(crate::abi::Thread, cpu_set) as CULong,
        core::mem::offset_of!(crate::abi::Thread, tid) as CULong,
        core::mem::offset_of!(crate::abi::Thread, refcount) as CULong,
        size_of::<crate::abi::Process>() as CULong,
        core::mem::align_of::<crate::abi::Process>() as CULong,
        core::mem::offset_of!(crate::abi::Process, coredump_barrier_count) as CULong,
        core::mem::offset_of!(crate::abi::Process, uti_thread_rank) as CULong,
        core::mem::offset_of!(crate::abi::Process, clone_count) as CULong,
        core::mem::offset_of!(crate::abi::Process, uti_use_last_cpu) as CULong,
        core::mem::offset_of!(crate::abi::Process, cpu_set) as CULong,
        core::mem::offset_of!(crate::abi::Process, ppid_parent) as CULong,
        core::mem::offset_of!(crate::abi::Process, pid) as CULong,
        core::mem::offset_of!(crate::abi::Process, threads_lock) as CULong,
        core::mem::offset_of!(crate::abi::Process, nr_tids) as CULong,
        core::mem::offset_of!(crate::abi::Process, tids) as CULong,
        size_of::<crate::abi::McexecTid>() as CULong,
        core::mem::align_of::<crate::abi::McexecTid>() as CULong,
        core::mem::offset_of!(crate::abi::McexecTid, tid) as CULong,
        core::mem::offset_of!(crate::abi::McexecTid, thread) as CULong,
        size_of::<CpuSet>() as CULong,
        core::mem::align_of::<CpuSet>() as CULong,
        size_of::<crate::fork_control_guest::child_credits::CallerForkOutcome>() as CULong,
        core::mem::align_of::<crate::fork_control_guest::child_credits::CallerForkOutcome>() as CULong,
        core::mem::offset_of!(crate::fork_control_guest::child_credits::CallerForkOutcome, disposition) as CULong,
        core::mem::offset_of!(crate::fork_control_guest::child_credits::CallerForkOutcome, error) as CULong,
        core::mem::offset_of!(crate::fork_control_guest::child_credits::CallerForkOutcome, handle) as CULong,
        core::mem::offset_of!(crate::abi::Process, update_lock) as CULong,
        size_of::<crate::abi::McsRwlockLock>() as CULong,
        core::mem::align_of::<crate::abi::McsRwlockLock>() as CULong,
        size_of::<crate::abi::IhkAtomic>() as CULong,
        core::mem::align_of::<crate::abi::IhkAtomic>() as CULong,
        core::mem::offset_of!(crate::abi::IhkAtomic, counter) as CULong,
        (core::mem::offset_of!(crate::abi::Thread, refcount) + core::mem::offset_of!(crate::abi::IhkAtomic, counter)) as CULong,
        size_of::<CInt>() as CULong,
        core::mem::align_of::<CInt>() as CULong,
        size_of::<core::sync::atomic::AtomicI32>() as CULong,
        core::mem::align_of::<core::sync::atomic::AtomicI32>() as CULong,
    ];

#[no_mangle]
#[used]
pub static f03_clone_lifetime_vm_Rust_ABI_v1:[CULong;10]=[
    size_of::<ProcessVm>() as CULong,
    core::mem::align_of::<ProcessVm>() as CULong,
    offset_of!(ProcessVm,refcount) as CULong,
    (offset_of!(ProcessVm,refcount)+offset_of!(crate::abi::IhkAtomic,counter)) as CULong,
    offset_of!(ProcessVm,memory_range_lock) as CULong,
    size_of::<crate::abi::IhkRwSpinlock>() as CULong,
    core::mem::align_of::<crate::abi::IhkRwSpinlock>() as CULong,
    offset_of!(ProcessVm,exiting) as CULong,
    offset_of!(ProcessVm,proc) as CULong,
    size_of::<AtomicI32>() as CULong,
];
