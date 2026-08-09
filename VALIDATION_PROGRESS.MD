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
| Rocky complete build | 20% | PENDING | Run `31288499526` compiled every requested target, then a false C-import assertion stopped validation before the source audit; the assertion is corrected for the next run. |
| Host modules | 10% | PENDING | No current-head load/unload evidence or necessarily successful module use during McKernel boot yet. |
| McKernel boot | 15% | PENDING | No current-head `RUNNING` status plus both Rust boot markers yet. |
| Real `mcexec` programs | 10% | PENDING | `/bin/true`, hostname, deterministic workload, `mcstat`, and Rust handoff markers remain unproved at runtime. |
| CI evidence and PR report | 10% | IN PROGRESS | Runs `31288159829` and `31288499526` exposed and recorded two validation blockers; clean shutdown, SELinux restoration, QEMU/backing-image checks, and the final PR report remain pending. |

The first hosted attempt earned no completion credit. Workflow run
`31288159829` (job `93180630285`) failed during container initialization after
three pull attempts with:

```text
manifest for rockylinux:8.10 not found: manifest unknown
```

No checkout or build command ran. The workflow now uses Rocky's own
`rockylinux/rockylinux:8.10` image pinned to multi-architecture digest
`sha256:e8a49c5403b687db05d4d67333fa45808fbe74f36e683cec7abb1f7d0f2338c6`
and asserts `ID=rocky` plus `VERSION_ID=8.10` before installing packages.

The second hosted attempt, run `31288499526` at
`df508bcbaf5867d50514dc7b156f918217439a03`, passed container initialization,
dependency installation, recursive checkout, the exact nightly check, and
development ancestry. It compiled all requested targets, including
`mckernel.img`, the three host modules, `mcexec`, and the deterministic
workload. The linkage gate then reported:

```text
error: .../mcexec.c.o does not import required Rust-path symbol:
mcexec_finish_main_image_body
```

That expectation was wrong: the compiled C `main` shim imports only
`mcexec_main_body`; Rust `mcexec_main_body` directly calls Rust
`mcexec_finish_main_image_body`. Both Rust definitions remain mandatory in the
Rust object and final binary. The run uploaded artifact `9030640799` with
digest `sha256:bc9b0b3acbbde635b4160c928972e40b0c4114a7e7d543d116813e5019cc121d`.
No build completion credit is awarded until the corrected linkage gate and
source audit pass together. Installation and runtime use are proved separately
inside the disposable guest.

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
result: PASS (actionlint 1.7.12; all 14 embedded Bash blocks also pass `bash -n`)

scripts/qemu-rocky-rust-validation.sh \
  --image unused --disk-size invalid
result: expected exit 2; invalid disposable-disk size rejected before QEMU

scripts/qemu-mckernel-guest.sh \
  --image unused --disk-size invalid
result: expected exit 2; invalid disposable-disk size rejected before image or QEMU probing

GitHub Actions run 31288159829 at
  b54e69c6bc3309e8a719b645832c8c37cdc853e1
result: FAILURE during `Initialize containers`
command: docker pull rockylinux:8.10 (three attempts)
error: manifest for rockylinux:8.10 not found: manifest unknown
checkout/build/boot: SKIPPED
artifacts: none
completion: unchanged at 35%

curl -fsSL \
  https://hub.docker.com/v2/repositories/rockylinux/rockylinux/tags/8.10
result: tag=8.10
        digest=sha256:e8a49c5403b687db05d4d67333fa45808fbe74f36e683cec7abb1f7d0f2338c6
        amd64=sha256:f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e

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
3. The guest must successfully run `/bin/true`, hostname, and the deterministic
   workload through `mcexec`, then run host-side `mcstat`; kmsg must contain
   `prepared`, `schedule_process queued`, `enter_user`, `send_syscall`, and
   `offload_return` markers.
4. `mcstop+release.sh` must succeed, SELinux mode must be restored, QEMU must
   exit, the backing image checksum must remain unchanged, and exact results
   must be added to this file and PR #1.

The same-repository PR workflow now has an automatic GitHub-hosted KVM lane. It
downloads Rocky's dated 8.10 GenericCloud qcow2, verifies its published size
and SHA-256, expands only a disposable overlay, performs the full build/boot
inside that guest, and rechecks the untouched backing image and ephemeral host
afterward. It must pass before any runtime percentage is awarded.

The protected self-hosted lane remains useful after merge, but additionally
requires repository administrators to configure the `mckernel-boot`
environment, runner labels, and two image variables. It cannot be manually
dispatched until the workflow exists on the default branch and does not count
as current evidence.
