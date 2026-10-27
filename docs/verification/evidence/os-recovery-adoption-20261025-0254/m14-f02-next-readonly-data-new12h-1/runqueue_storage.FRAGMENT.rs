// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired with MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE in process.c. Reuse the
// existing typed constructor; no scheduler body or callback/lifetime change.
#[cfg(process_global_storage_candidate)]
#[no_mangle]
pub static process_sched_runqueue_offsets: SchedRunqueueOffsets = sched_runqueue_offsets();

const _: () = {
    assert!(core::mem::size_of::<SchedRunqueueOffsets>() == 208);
    assert!(core::mem::align_of::<SchedRunqueueOffsets>() == 8);
};

