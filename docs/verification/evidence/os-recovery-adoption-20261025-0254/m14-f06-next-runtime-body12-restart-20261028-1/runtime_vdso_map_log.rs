// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// New exact logger, real descriptor and byte-identical banked state/storage providers.
#![no_std]
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
#[path="syscall_policy.type.snapshot.rs"]mod syscall_policy;
#[path="f06_vdso_storage.rs"]mod storage;
#[path="f06_vdso_state.rs"]mod state;
#[path="f06_vdso_map_log.rs"]mod candidate;
