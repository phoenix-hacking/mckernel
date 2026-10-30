# M14 architecture xstate bridge actual-body regression

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
2026-10-30 07:45 UTC. Source/test only; no Docker, guest or native execution.

Both bridge source copies are byte-identical to the corresponding files under
`.../DISPATCHER-SOL-MAX-20261030-1/arch-signal-postformat-compiler-candidate-1/src/kernel/rust/`:

- `f06_ptrace_xstate_copy_to.rs`: SHA256 `c2a01b19c1434a13b6adf24607490b35ea8771c17824b8cebf10e7d5ae19618a`
- `f06_ptrace_xstate_copy_from.rs`: SHA256 `6a6e89f1e956ca599cee4dd9c851125acada5565aa2c3835d3e5184fbfb6dde5`
- `xstate_test.rs`: SHA256 `4c4b563c637d6a83767b67ae6791b6282dae8b6c7cfd433df973d7640a1a46e3`
- `xstate_test`: SHA256 `fa42051975410bb0cf8af55da51ce859c473c9f8cb71ce05e8c7908cf071af38`

Actual command, from this directory:

```
/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test xstate_test.rs -o xstate_test && ./xstate_test --test-threads=1
```

Rustc `1.95.0-nightly (c04308580 2026-02-18)` returned zero; one test passed, zero failed. The actual candidate bodies were included unmodified. For each copy direction the injected provider verifies exact pointers/count and copies the expected bytes; the fixture exercises partial writes with `-14`, zero count with `i32::MIN`, positive return, and null FP state with no provider invocation. The positive and negative int results widen without normalization.

The first fixture compile failed with E0506 because a closure borrowed `fp` while it was reassigned; a single bounded correction captured its address before the closure. The candidate source was unchanged. The first compiler failure occurred before a test binary executed. This local receipt retains the error and correction; it does not represent a failure of a kernel candidate.

The fixture deliberately replaces the full Thread definition and real user-copy provider; it does not validate actual ABI offsets, access faults, concurrency, lifetime, native behavior, default selection or retirement. Existing matching ABI and later integrated native qualification remain required. No original acceptance changed.
