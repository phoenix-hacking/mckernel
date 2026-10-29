// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual Rust storage plus byte-identical BODY10 callback; no mocks here.
#![no_std]
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
#[path="f06_prctl_log_storage.rs"]mod storage;
#[path="f06_prctl_log.rs"]mod callback;
