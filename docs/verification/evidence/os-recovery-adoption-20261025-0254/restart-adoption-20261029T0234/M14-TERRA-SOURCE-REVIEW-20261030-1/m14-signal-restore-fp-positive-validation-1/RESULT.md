# M14 F06 positive validation-result regression

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
2026-10-30 07:52 UTC. Private focused fixture; no native, guest or heavy work.

The prior unmodified result remains at `../m14-signal-restore-fp-body-regression-1/`:
its `RESULT.md` SHA256 `d5498c5df787df40fe25aba80743a573230f91b146eaca9a9321a6e3a63ef695`,
test source SHA256 `56f4bdec80942a28ee5aa520684a1339881923bb79f8ae351ed90a34cfead3d8`,
and `test.stdout` SHA256 `80a48b50a8c29a51b61cfb4b61f54e90ae6a3b19df3e991b20e8e7afbc52696a`
record 1/1 pass. That earlier run covered nine controlled inputs.

This successor adds one positive nonzero validator result (17); the actual Rust
body must return 17, call the original-pointer free exactly once, and not call
restore. The exact source in `f06_native_signal_restore_fp.rs` is unchanged from
the first fixture, SHA256 `126c0aff5baa9a9fd97d910ec46fd7af50ea2a15c49bf7269d0e6c33e510e712`.
Successor `test.rs` SHA256 `a194c8e0e01094bab73e49352e7dc6e7843a7d4e728f1789d558f6912c43c8c9`.

Actual command from this directory:

```
/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test test.rs -o test 2>compile.stderr && ./test --test-threads=1 >test.stdout 2>test.stderr
```

Compile and test returned 0, one test passed, no warnings or errors, covering ten
controlled inputs. `test.stdout` SHA256 `80a48b50a8c29a51b61cfb4b61f54e90ae6a3b19df3e991b20e8e7afbc52696a`;
`test` SHA256 `2e5fddf24d695948adc25a24ec0888203a4864f7fa658d39e5fb96f43c6231fc`.
The output bytes happen to be identical to the first test because the test name
and aggregate report are unchanged. No failures occurred.

Callbacks are controlled mocks: positive validation is a synthetic return, not
an assertion that the production validator can return it. This establishes the
body's branch behavior only; the prior receipt's real-provider, hardware, ABI,
integration and native qualification limitations remain unchanged.
