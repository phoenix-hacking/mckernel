# Local recovery after the interrupted session

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

The host C syntax check stopped at the fixture's required
`CPUHP_FAILURE_STATE` definition. Recover that value from the exact kernel
bindings before retrying; preserve the prerequisite guard. No 32-bit C check
or guest validation followed. The original native loader build failure and
this attempted check remain recorded in `kernel.log`.

The existing 60 GiB `scratch.ext4` file survived the restart, but the scratch
mount is absent. The local setup notes specify restoring the transient
cgroups and mount after a host reboot. Docker and the restore command require
administrator authentication, which is unavailable to the current tool
session. No privileged restoration has run yet.

## Prepared restart command

Run this in an authenticated local terminal:

```bash
sudo /usr/bin/bash /home/holden/mckernel/scripts/resume-local-verification.sh
```

The wrapper uses the existing workstation setup script, preserves the scratch
image, checks isolation in the pinned native and compatibility containers,
then runs the focused native image and OS runtime tests. It preserves a fresh
record directory under `mckernel-work/scratch/recovery-*` and stops at the first
failed check. It does not execute guest helpers on the host or boot a guest.

After the preflight, inspect the restored image-loader build script and its
retained records, recover the exact CPU hotplug binding, and continue native
Kbuild, staging and guest verification in the existing isolated runner. Keep
the four-CPU, 12 GiB, 512-task and one-invocation-at-a-time limits. No production
acceptance or native McKernel boot credit is claimed by this recovery record.
