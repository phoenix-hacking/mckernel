# Dedicated root collector infrastructure profile

The existing `/home/holden/mckernel-work/setup/container-run.py` remains unchanged.
It runs the native image as uid/gid1000 with the whole scratch tree writable;
ordinary builder validation still uses it. Root-positive collector validation
uses this distinct profile, because ACRQ profile1 requires actual uid/gid/groups0.
The parent already owns this isolated prerequisite work and its root terminal.

After the pinned builder has retained all compiler inputs/outputs and the three
executables named `linux-collector`, `fixture`, `sha256-harness`, the exact source
helper invocation is:

```
/usr/bin/python3 /home/holden/mckernel/scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root_profile.py \
  --build-root /home/holden/mckernel-work/scratch/RETAINED-PINNED-BUILD \
  --attempt-root /home/holden/mckernel-work/scratch/stability-linux-sealed-root-tests-20260913-1
```

The helper requires actual host root, checks the established parent cgroup, pins
the native image by its existing exact image-record ID, copies stable bytes of
only the three binaries and three source entry points into a fresh root-owned
input directory, and writes a command plan. It does not execute Docker or tests,
acquire the development lock, start containers, change existing trees or grant
runtime acceptance. Every artifact is exclusive; a preparation failure retains
its partial fresh tree. Never reuse the attempt name.

The parent must hold `/run/lock/mckernel-development.lock` through actual cleanup,
run the exact scratch mount/label checks and image inspect in the plan, then
execute create/inspect/start under its independent bounded host collector. The
plan's create argv has:

- the same immutable native image with pull disabled, four CPUs on2–5, parent `/mckernel-dev`,
  12GiB RAM and equal total memory+swap allowance, and512PIDs;
- cap-drop=ALL, no-new-privileges, networknone, unprivileged container mode,
  read-only root, init process, core0 and nofile4096;
- explicit uid/gid0 with supplementary group0; no added capability;
- read-only repository and the fresh copied input directory; only the fresh
  dedicated `work` directory is a writable host bind;
- a256MiB nodev/nosuid temporary filesystem, HOME=/tmp and TMPDIR=/work/tmp;
- the fixed `/usr/bin/python3 /inputs/root_inside.py` entry point.

No Docker socket, host PID namespace, extra device, guests tree, broad scratch
mount or persistent builder home is exposed. The parent must compare the entire
actual inspect configuration before start, reject extra mounts/devices/privilege
flags and retain the real image ID/container ID/ownership label. The random name
and nonce label belong only to this attempt. After creation, use the observed
container ID and matching label to identify every stop/remove action; the plan's
name is a locator, not sufficient proof of cleanup authority. On a create timeout
or missing ID, inspect the unique name/label under a bounded recovery path and
record ambiguity instead of blindly touching an unrelated container.

The actual Docker attach command is bounded to300seconds. The parent watchdog
must stop the identified container, not merely kill the Docker client. Separate
stop/remove/inspect bounds and raw results are in the plan; inability to confirm
removal remains a failure. Retain partial streams, inspect records and first
failure, and verify absence before releasing the serialization lock.

The fixed entry point independently observes uid/euid/gid/egid/groups, all five
capability sets zero, NoNewPrivs1, and read-only root/input/repository filesystems.
It hashes every copied input, runs the nine-line actual SHA harness and then the
25-case actual collector driver, and rechecks copied bytes. Its inner driver has
a180second plus15second outer allowance, in addition to each case's40/15 bounds.
Only actual rawzero exits, complete streams/cleanup and independent fixture
assertions produce its infrastructure-only result. It never creates native
payload records or enables `run.py` or catalog cases. A successful entry-point
record does not replace host inspect, container exit or cleanup evidence.

With cap-drop=ALL, setgroups is denied even for UID0. The OCI profile therefore
supplies exact group0 before capability removal; the collector confirms an
already correct supplementary list and only attempts mutation for a mismatch.
Its actual setresuid/setresgid targets remain0 and are observed afterward.
Source metadata on2026-09-13 reports host Linux5.15.0-139, independently of the
pinned image's Linux6.12 build sources. The collector uses original memfd flags
and verifies actual executable mode/seals; unsupported/no-exec policy blocks.
No host syscall probe is claimed by this source plan.

Only the new dedicated tree contains root-owned output. The parent must archive
that full tree with original uid/gid/modes and verified member hashes before any
optional ownership handoff to1000:1000. Any such handoff is separately recorded,
component-anchored, nonsymlink and confined to this fresh tree; neither this
helper nor the container runs chown or writes broad host directories. Keep the
original builder wrapper, compiler capture and source records unchanged.
