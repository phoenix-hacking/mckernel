# Local recovery after the interrupted session

The environment is restored and the resumed image-loader guest verification
passed. The [retained checkpoint](native-image-loader-checkpoint-20260907.json)
contains 36 artifacts, including the setup recipes, source/compiler records,
built modules, Linux boot image, guest initramfs and complete capture logs.
All retained bytes passed a SHA-256 and compression round-trip check.

The recovered native image-loader work is preserved in commit `04a996fc`.
The six earlier local commits and the GitHub checkpoint instructions in
`14c3ff03` were pushed to `origin/codex/local-native-staging-repair`.
GitHub's branch reference independently matched the local commit after upload.

The active goal remains continued McKernel integration and verification.
`AGENTS.md` now records the user's authorization for autonomous setup,
implementation and isolated verification, together with periodic GitHub
checkpoints. Unfinished checkpoints retain their exact validation limits.

## Current evidence

Three focused Python checks covering the image policy, bounded file adapter
and OS runtime passed with the local upstream Rust 1.92.0 compiler, CPUs 2-5
and a 12 GiB address-space limit. These checks were outside the pinned Rocky
container and do not replace its native build or runtime evidence.

The initial host C syntax check stopped at the fixture's required
`CPUHP_FAILURE_STATE` definition. Recovery found the exact binding value,
234. Both probes subsequently compiled in the pinned native container with
that definition and passed in the guest. The original native loader build
failure and the incomplete host check remain recorded in `kernel.log`.

The existing 60 GiB `scratch.ext4` file survived the restart. The setup script
restored its mount and the four-CPU, 12 GiB and 512-task controls without
installing, upgrading or removing packages. Native and compatibility container
isolation checks passed, followed by all three focused tests in the pinned
Red Hat Rust 1.92.0 environment.

All ten current source overlays and five compiled outputs matched the
successful pre-crash native build. Fresh formatting, ELF64 and no-SIMD/x87
checks passed. The new four-vCPU/two-NUMA guest capture completed at
`2026-09-07T14:54:37.193884+00:00`, with exit code zero, no missing markers
and no error markers. Both ABIs completed two module cycles; all 24 physical
image readbacks matched the independent ELF model. CPU/memory ownership,
rollback, allocation failure, concurrent OS and cleanup checks passed too.
The original interrupted capture is retained separately.

## Prepared restart command

The command used for restoration and initial checks was:

```bash
sudo /usr/bin/bash /home/holden/mckernel/scripts/resume-local-verification.sh
```

The wrapper uses the existing workstation setup script, preserves the scratch
image, checks isolation in the pinned native and compatibility containers,
then runs the focused native image and OS runtime tests. It preserves a fresh
record directory under `mckernel-work/scratch/recovery-*` and stops at the first
failed check. It does not execute guest helpers on the host or boot a guest.

Next integrate image loading into the declared stage, lifecycle contracts,
unsafe/FFI inventory and downstream verification identities. Follow that with
a fresh declared-stage build, guest replay and repository suite. Native AP
startup, IKC, native mcctrl workloads and final Rust/assembly completion remain
open. Keep the four-CPU, 12 GiB, 512-task and one-invocation-at-a-time limits.
No production acceptance or native McKernel boot credit is claimed here.
