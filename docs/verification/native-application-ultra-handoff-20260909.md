# Application baseline handoff to Astra Ultra

The Max baseline is verified and ready for broader application testing after
the final commit is fetched from GitHub and its selected blobs are verified.
Stop at that point for the user's model switch. Astra Ultra owns the next
review, any fixes found in that review, and the detailed test plan. The user
will later choose when to switch to Spark for implementation and execution.

The [readiness audit](native-application-readiness-20260909.json) maps every
criterion from the [service plan](native-application-service-plan.md) to
retained evidence. All six criteria pass. This is a reproducible application
baseline; it does not close whole-OS production or full Rust/assembly gates.

## Verified behavior

All accepted application runs use the same signal module 1 / signal image 2,
unchanged Rust mcexec launcher, and unchanged ordinary dynamic-libc core.

| Check | Observed result | Evidence |
| --- | --- | --- |
| Ordinary ELF and delegated syscalls | Real McKernel scheduling, exact stdout and exit 37, matching worker/delivery/CPU return routes | [Final checkpoint](native-application-final-checkpoint-20260909.json) |
| Memory | malloc/mmap data, read-only/read-write mprotect, munmap/free; fourteen completed host invalidations; pager references released | Final checkpoint, memory guest 1 |
| Files | 8,209-byte create/write/stat/seek/read/EOF/pwrite/pread/fsync/close/reopen/unlink and ENOENT checks | Final checkpoint, files guest 1 |
| Threads/futexes | Two guest clone3 children, 512-byte TID transfer, barrier/mutex counter, isolated TLS, join results and thread-node removal | Final checkpoint, threads guest 1 |
| Signals | Block/pending/unblock and repeated alternate-stack handlers; both actual sigreturns return zero | [Signals](native-application-signals-checkpoint-20260909.json) and owner-failure replay |
| Actual launcher/worker failure | SIGKILL during a delivered blocked read; retirement and process release return zero; process node removed | [Owner failure](native-application-owner-failure-checkpoint-20260909.json) |
| Reuse and recovery | 700 quiet Linux forks reuse both old IDs three times; no stale return in that interval; eight subsequent applications pass in the same OS | Owner-failure guest 2 |
| Full control regressions | Both original x86_64/i386 suites, exact physical counters and boot/continuing services pass; x86_64 also verifies 388 procfs replies, 72 independent worker reaps and four inherited-TGID retirements | Final checkpoint |

Five accepted fresh application guests total **48 HELLO launches and five core
runs**: memory, files, threads and signals twice. The intentional SIGKILL is
one additional failure case. Two separate guests run the full control suites.
All seven accepted guests exit QEMU with code zero. Normal runs retain every
original output, route, retirement, process/procfs and pager assertion.
The control worker-reap cases have applications=0; scheduled failure coverage
comes from the separate actual blocked-read/SIGKILL case.

## Exact inputs and reproduction

The final checkpoint lists complete SHA-256 identities for all three native
modules, Linux bzImage, McKernel image, launcher and core binary. It binds 57
native and 37 guest compiler sources. Native implementation sources have not
changed since `3453edd571152132b19d23b26dad32f4204612e6`; later commits record
verification. The three native formatter replays remain explicitly bound in
the [signal checkpoint](native-application-signals-checkpoint-20260909.json).
The [image checkpoint](native-application-signals-images-checkpoint-20260909.json)
retains all four image selections and prior clone3/protection/zeroing checks.

Protected current scratch paths:

```text
/work/native-application-signals-module-20260909-1
/work/mckernel-native-signals-images-20260909-2/native-rust/kernel/mckernel.img
/work/native-application-launcher-20260908-2/rust/executer/user/mcexec
/work/native-application-core-build-20260908-1/native-application-core
/work/native-application-failure-build-20260909-1
```

Successful commands inside the pinned **native** container were:

```text
python3 -B /work/run-native-application-signals.py signals 1
python3 -B /work/run-native-application-owner-failure-2.py signals 2
python3 -B /work/run-native-application-final-batch.py 1
python3 -B /work/retain-native-application-final.py 1
python3 -B /work/audit-native-application-readiness.py 1
```

The retained final batch records its five exact child commands, executed
helpers and exit statuses: memory 1, files 1, threads 1, full x86_64 control 1,
and full i386 control 1. Each guest archive contains the exact QEMU command,
boot source/build command, modules/image/binaries, original and executed
helpers, serial/debugcon, and physical memory/queue/register captures.
Application runners bound QEMU execution to 300 seconds; full controls use
600 seconds. Replay requires fresh attempt names; never overwrite originals.
Keep the exact assertions and stop/log/preserve the first failure.

The environment remains four container CPUs (2–5), 12 GiB, no swap, 512 tasks,
offline and unprivileged. TCG runs four Linux vCPUs, 8 GiB and two NUMA nodes,
with one McKernel CPU and 128 MiB. Application boot uses the existing
`hidos allow_oversubscribe`; original controls use `hidos`. The Linux native
kernel is pinned to `6.12.0-211.44.1.el10_2`. No host kernel/module execution or
host reboot is part of these results.

## Failures and remaining scope

Owner-failure attempt 1 remains FAIL: the reused diagnostic helper resumes
only validated captures, so its new unvalidated live capture left QEMU paused
before SIGKILL. The exact runner was interrupted for emergency capture and
cleanup. Attempt 2 adds an explicit QMP resume; its retainer proves the original
assertions are unchanged. No native fix was needed. Earlier real signal,
thread, loader/pager, image-audit and fixture failures remain retained in the
referenced checkpoints and kernel.log. None is relabeled as a passing attempt.

This baseline leaves multicore McKernel, long stress, MPI, representative
application suites, OS shutdown/resource restoration and production acceptance
for later work. It does not prove all OS-owned pending zeroing pages drained.
CPU-online sysfs stores preserve the existing callback that acknowledges input
without changing CPU state; hotplug is not accepted. Native alternate-stack
AUTODISARM and unsupported clone3 flags remain rejected as documented.
Permanent transport failure/quarantine and wider exhaustion behavior need
further testing. No known defect remains that blocks this defined baseline.

Ultra should review these implementations and limits against the retained
evidence, fix issues it finds, and produce a bounded plan with prerequisites,
commands, independent expected results, timeouts, cleanup rules, negative
cases and required captures. That review and Spark execution are later phases.
The final fetch/blob verifier must pass before the Max goal is marked complete.
