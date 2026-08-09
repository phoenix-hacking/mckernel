# Rust x86_64 Validation Progress

**Current completion: 25%**

This file tracks evidence for pull request #1 (`codex/rocky-rust-validation`). The
percentage is evidence-gated: it reaches 100% only after the Rust-enabled McKernel
image boots on a Rocky/RHEL-family x86_64 host and `mcexec` successfully runs real
userspace programs.

## Completion gates

| Gate | Weight | Status | Evidence |
| --- | ---: | --- | --- |
| Current PR/head and validation-scope audit | 5% | PASS | Draft PR #1 was audited at old head `95d8bdfd47d854f720f1487872b98d65438c3044`: non-mergeable, two validation files, and no workflow runs. The branch is now based on current `development`; this tracker was first published at head `77b81fb93b5251558cb58ffa7324b5aa4163ce9a`. |
| Runner syntax, CLI, and failure-path checks | 5% | PASS | Fresh current-tree checks passed: `bash -n` on all three Rocky/QEMU runners, `--help` on all three runners, and the Rocky runner's unknown-option path returned the required status 2. |
| IHK patch applicability and pinned-submodule compatibility | 5% | PASS | At pinned IHK `3114d9e7101ad52030eb3effa849a5c108972a1f`, forward check/apply, reverse check/apply, `git diff --check`, and clean-worktree verification passed. `git apply` reports one non-fatal blank-line warning in the patch; it will be removed with the compatibility update. |
| Branch compatibility with current `development` | 10% | PASS | Merged current `development` (`7a779815cba07bacfeed5788acca31629e50a39a`) into the PR branch at GitHub head `6e08e1e6b749fbc90a74b0f09c5b6f4eaec8b951`; old validation files resolve to the current implementations. |
| Rust toolchain and Rust kernel source checks | 10% | BLOCKED | The pinned IHK submodule lacks the Rust core/SMP sources referenced by the merged build and equivalence harness; recovery is in progress. |
| Rocky/RHEL-family configure and complete build | 20% | PENDING | No current-head build transcript yet. |
| IHK, `ihk-smp-x86_64`, and `mcctrl` host-module validation | 10% | PENDING | No module build/load evidence yet. |
| Rust-enabled McKernel image load and boot | 15% | PENDING | No boot log proving the Rust-enabled image reached boot completion. |
| `mcexec` plus real userspace programs | 10% | PENDING | `/bin/true`, identity/hostname, and compiled workload execution not yet proven. |
| Reproducible CI/docs and final PR update | 10% | PENDING | No GitHub Actions runs and no exact end-to-end transcript. |

## Required 100% evidence

- Clean checkout of the PR head with all pinned submodules.
- Rust-enabled x86_64 image and Linux-side IHK/`mcctrl`/`mcexec` artifacts build.
- Host modules load, CPUs and memory reserve, and McKernel boots.
- Boot log identifies the expected McKernel/Rust path.
- `mcexec /bin/true` succeeds and a compiled userspace workload produces checked output.
- Shutdown/release succeeds and the host returns to a clean state.
- Rocky/RHEL-family commands, versions, results, and any environmental limitations are recorded exactly.
- The branch is compatible with current `development`, and automatic/static coverage runs in GitHub Actions where privileged boot is not available.

## Update log

- 2026-08-08: Established 15% baseline from PR metadata and existing recorded checks. Runtime validation and current-branch compatibility remain unproven.
- 2026-08-08: Advanced to 25% after merging current `development` into the PR branch and publishing the merge. Identified a concrete current-head blocker: pinned IHK commit `3114d9e7101ad52030eb3effa849a5c108972a1f` does not contain the Rust IHK core/SMP helper sources expected by the parent build and equivalence test.
- 2026-08-08: Held at 25% while replacing recorded-only evidence with fresh checks. Exact successful command group: `bash -n scripts/{rocky-rust-validation.sh,qemu-rocky-rust-validation.sh,qemu-mckernel-guest.sh}`; each runner with `--help`; the Rocky runner with `--definitely-invalid` (expected status 2); then, from `ihk/`, compatibility-patch forward check/apply, reverse check/apply, `git diff --check`, and a clean-worktree assertion. Result: PASS. Script/patch SHA-256 values were `74c3e47d...`, `fd3bfc9...`, `df9c387...`, and `f4b6a46...`, respectively.
