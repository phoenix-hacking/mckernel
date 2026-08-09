# Rust x86_64 Validation Progress

**Current completion: 35%**

This percentage is evidence-gated. It reaches 100% only after the current PR
head builds on Rocky/RHEL-family x86_64, boots McKernel, runs real programs
through `mcexec`, and shuts down cleanly.

## Completion gates

| Gate | Weight | Status | Current evidence |
| --- | ---: | --- | --- |
| PR and scope audit | 5% | PASS | Draft PR #1 inspected; the recorded tree is pinned C IHK plus Rust McKernel, Rust-linked `mcctrl`, and Rust-linked `mcexec`. |
| Runner checks | 5% | PASS | Shell syntax, help, invalid-option, numeric-option, and cleanup-regression checks pass. |
| IHK compatibility | 5% | PASS | Forward check/apply, reverse check/apply, `git diff --check`, and clean pinned-IHK status pass at `3114d9e7101ad52030eb3effa849a5c108972a1f`. |
| `development` compatibility | 10% | PASS | Current `development` commit `7a779815cba07bacfeed5788acca31629e50a39a` is merged; GitHub reports the draft PR mergeable. |
| Rust source/toolchain | 10% | PASS | Exact pinned nightly compiles the three selected Rust objects; required symbols, no-SIMD scan, formatting, and variadic behavior checks pass. |
| Rocky complete build | 20% | PENDING | Awaiting the first current-head hosted Rocky 8.10 transcript. |
| Host modules | 10% | PENDING | No current-head load/unload or boot-created module evidence yet. |
| McKernel boot | 15% | PENDING | No current-head `RUNNING` status plus both Rust boot markers yet. |
| Real `mcexec` programs | 10% | PENDING | `/bin/true`, hostname, deterministic workload, `mcstat`, and Rust handoff markers remain unproved at runtime. |
| CI evidence and PR report | 10% | IN PROGRESS | Workflow and reporting are implemented; no current-head Actions result or final runtime report yet. |

## Fresh commands and results

```text
bash -n scripts/rocky-rust-validation.sh \
  scripts/qemu-rocky-rust-validation.sh \
  scripts/qemu-mckernel-guest.sh \
  scripts/ihk-module-load-smoke.sh
result: PASS

rustfmt +nightly-2026-02-19 --edition 2021 --check kernel/rust/numparse.rs
result: PASS

actionlint -config-file .github/actionlint.yaml \
  .github/workflows/rust-x86_64-validation.yml
result: PASS (actionlint 1.7.12; all 10 embedded Bash blocks also pass `bash -n`)

cc -O2 -std=c11 -Wall -Wextra -Werror \
  scripts/smoke/mcexec-rust-smoke.c -o mcexec-rust-smoke
./mcexec-rust-smoke
result: mckernel-rust-smoke: OK bytes=1048576 sum=133693440

git diff --check
result: PASS
```

Pinned compiler: `rustc 1.95.0-nightly (c04308580 2026-02-18)` from
`nightly-2026-02-19`. Production-flag object results:

| Object | SHA-256 | Result |
| --- | --- | --- |
| `mckernel_rust.o` | `408fc2ef755ca0ad188e17d65497c3c24239ce0ce59b24a880833461353bf030` | Required entry/host symbols and no-SIMD gate pass. |
| `mcctrl_helpers.o` | `91a4b57d63b4ed44c3ba0c2d1959accb86a9152646f454b0f15a788856ad54e4` | Required module/control symbols and no-SIMD gate pass. |
| `mcexec_helpers.o` | `1bd472ba5fcacde678ffcb3983004d4e51faea7c6d0fcf0d51a8347fb59526ef` | Required main/image/syscall-loop symbols pass. |

A focused native variadic harness resolved `snprintf` and `sscanf` to the Rust
object and passed dynamic width/precision, promoted integer classes, pointer,
`%n`, and scan-back cases with `numparse-va-smoke: OK`.

## Remaining path to 100%

1. Hosted Rocky build must produce `mckernel.img`, C `ihk.ko` and
   `ihk-smp-x86_64.ko`, Rust-linked `mcctrl.ko`, Rust-linked `mcexec`, and the
   deterministic workload while all linkage/audit gates pass.
2. A protected disposable Rocky KVM guest must load the modules, reserve CPU
   and memory, reach `RUNNING`, and contain `IHK/McKernel started.` plus
   `IHK/McKernel booted.`.
3. The guest must successfully run `/bin/true`, hostname, the deterministic
   workload, and `mcstat` through `mcexec`; kmsg must contain `prepared`,
   `schedule_process queued`, `enter_user`, `send_syscall`, and
   `offload_return` markers.
4. `mcstop+release.sh` must succeed, SELinux mode must be restored, QEMU must
   exit, the backing image checksum must remain unchanged, and exact results
   must be added to this file and PR #1.

The protected boot lane additionally requires repository administrators to
configure the `mckernel-boot` environment, a matching self-hosted KVM runner,
and the two checksum-pinned Rocky image variables. The workflow cannot be
manually dispatched until it exists on the default branch; staged YAML alone
does not count as boot evidence.
