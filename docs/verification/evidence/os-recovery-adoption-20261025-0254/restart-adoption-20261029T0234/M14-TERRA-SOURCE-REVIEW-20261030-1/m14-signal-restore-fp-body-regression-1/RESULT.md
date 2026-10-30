# M14 F06 signal-return FP body local regression

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Executed 2026-10-30 07:50 UTC in this private directory. This is source-level
functional evidence only, with mocked providers; no native, guest or heavy work.

The included `f06_native_signal_restore_fp.rs` is a byte-identical copy of the
retained `arch-signal-postformat-compiler-candidate-1/src/kernel/rust/` body, SHA256
`126c0aff5baa9a9fd97d910ec46fd7af50ea2a15c49bf7269d0e6c33e510e712`.
Original semantics were read from that candidate's `src/arch/x86_64/kernel/syscall.c`
SHA256 `78546125873dbf1f3619c2ce678bf9a07cc306b72db73f4597cc3d85ac4146de`,
`arch_native_signal_restore_fp_bridge`, lines 481 onward. The C function was
inspected, not compiled or executed in this fixture.

Actual command:

```
/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test test.rs -o test 2>compile.stderr && ./test --test-threads=1 >test.stdout 2>test.stderr
```

Rustc `1.95.0-nightly (c04308580 2026-02-18)` and test returned zero, no
warnings/errors, 1 test passed. The single test invokes the actual Rust body
nine times with different controlled callback results: null user reset; size
rejection; allocation failure; positive and negative copy errors; validation
failure; restore failure and success; and a synthetic zero-byte successful size
callback. It checks exact callback ordering, argument propagation, 64-byte
alignment, error mapping, and exactly one free of the original allocation on
each allocated branch. Source `test.rs` SHA256
`56f4bdec80942a28ee5aa520684a1339881923bb79f8ae351ed90a34cfead3d8`;
`test.stdout` SHA256 `80a48b50a8c29a51b61cfb4b61f54e90ae6a3b19df3e991b20e8e7afbc52696a`;
`test` SHA256 `2ef5dc8fccbe45760efd1a09d7b7be5280873f43d4214eb0f559f0fc4b09bbe2`.
No failures or bounded corrections occurred.

This mocked byte-count callback returning zero is synthetic and does not claim
that the actual production size validator can produce zero. The fixture does not
test real allocations, copy faults, buffer contents, the real validator, FP
hardware, actual caller/exclusion, production ABI or C-vs-Rust execution.
Those and matching integrated/native qualification remain open; no default
selection, C retirement or file completion follows from this result.
