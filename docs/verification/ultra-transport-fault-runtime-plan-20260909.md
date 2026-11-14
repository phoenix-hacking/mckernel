# Actual application transport fault verification

Status: **design and two unexecuted preparation/build helpers**. No injected
module has been compiled, no fault guest has run, and no runtime gate is closed
by this artifact. Root owns serialized native-container builds and guests.
Production repository sources and accepted modules were not modified by this
task. A dedicated guest supervisor/auditor and retained-owner observation still
need implementation before the four fault commands can become runnable.

## Exact injection boundary and protected inputs

Protected production parent:
`/work/native-ultra-module-20260909-1`. Require its authoritative record PASS
and verify the three module identities. The eventual native Ultra guest image
is an explicit `/work/mckernel-native-ultra-images-20260909-N` argument with a
PASS record and exact selected-image hash; never guess `N` or use an old image
because its filename is familiar. The unchanged launcher and guarded-read
payload remain the accepted `native-application-launcher-20260908-2` and
`native-application-failure-build-20260909-1` binaries.

`/work/prepare-native-ultra-transport-fault.py MODE ATTEMPT` prepares two
verification-only source overlays copied from the parent's **actual staged
compiler inputs**. It records originals, injected bytes, unified diffs and
inverse-patch byte equality. It performs no build, module load or guest launch.
The first successful preparation status is PREPARED, not runtime PASS.

The mailbox's existing call to `Completion::publish(send)` is changed only to
pass a controlled send callback. The callback latches the first noncancelled,
non-kernel-service application read whose request is nr0, fd0, length16. It
records PID, guest CPU, requester, delivery, physical response and user buffer.
Every other delivery calls the original sender. It accesses no response bytes.
The separate existing `smp_ikc::notify(cpu)` callback is wrapped for the
notification-only fault. This runs after the real mailbox publication and
before the application mutex permits a RET waiter to observe completion.

`application_syscall.rs`, including **all of `Completion::publish`**, and
`smp_application.rs`, including every production failure/timeout transition,
remain byte-identical to the parent. Verification state lives only in the
staged mailbox appendix; there is no production flag, UAPI addition or Linux
patch. One fresh module/guest instance contains one compile-time mode.

| Mode | Actual operation substituted | Expected terminal behavior |
| --- | --- | --- |
| `prepublish-hard` | The targeted real wake send returns `-EIO` without publishing any packet. | Production application transport quarantine; accepted RET stops waiting; response status remains0 and its claim stays retained. |
| `postpublish-notify` | The target sends through the real queue exactly once; its separate notify callback then returns `-EIO`. | Production terminal quarantine after actual status publication/release; no second wake or later response access. Guest may already consume the published wake. |
| `recoverable-backpressure` | Target send returns `-EAGAIN` for two monotonic seconds, then calls the real sender. | Original result retained through retries; one real publication; read payload completes normally and later applications succeed. |
| `permanent-backpressure` | Target send continues returning `-EAGAIN`. | Production five-second per-completion deadline quarantines the application service, retains the response and wakes the host waiter. |

The two EAGAIN modes are **injected runtime backpressure**, not proof of a
physically full IKC ring. Full-ring saturation remains a separate test requiring
a reviewed per-channel consumer gate or safe filler/recovery mechanism. Pausing
all QEMU CPUs is insufficient: it also pauses Linux's monotonic deadline.
Do not label injected errno coverage as a physically saturated queue result.

## Preparation and build commands

Inside the established native container, one mode at a time:

```text
python3 -B /work/prepare-native-ultra-transport-fault.py prepublish-hard 1
python3 -B /work/build-native-ultra-transport-fault.py prepublish-hard 1
```

Repeat with fresh attempt identities for the other three mode strings. These
helpers have not been executed or syntax/compile validated in this task.
The build helper is adapted from the complete existing
`/work/build-native-ultra.py`, retains that original helper, preserves the
prior shared build/stage directories and uses the original module build
command/checks. Do not run it concurrently with any other module build.

Before overlaying the two files, it requires the newly formatted production
stage to equal the selected parent originals. It rejects source drift. It
rechecks unchanged completion/failure source, formats the verification overlay,
retains the full staged source and builds all three modules with the original
warning/objtool/symbol/namespace/no-SIMD checks. Its result remains
`verification_only=true`, `actual_guest_transport_fault_verified=false`,
`physical_full_ring_verified=false`. A build PASS is only a build result.

Outputs have separate mode-specific names:

```text
/work/native-ultra-transport-fault-source-20260909-MODE-ATTEMPT
/work/native-ultra-transport-fault-module-20260909-MODE-ATTEMPT
```

Do not overwrite production module1, alter the current normal runner, mix a
verification module into the benign acceptance manifest or omit a failed
verification build. Log/preserve the first failure immediately.

## Guest supervisor state machine still to implement

Implement a Linux-only controller using the original controller's owned pipes,
unreaped child identity and `/proc/PID/task/TID/syscall` scan. Retain both
complete original/executed sources. Continue using the **unchanged real
guarded-read payload**: it writes `NATIVE_FAILURE_READY`, reads16 bytes into
the middle of a32-byte sentinel buffer, checks all guards, writes
`NATIVE_FAILURE_PASS` and normally exits37. Its same-guest Linux reference
receives16 bytes0xa5 and must produce the exact two lines and exit37.

The new controller must drain stdout and stderr concurrently with fixed64-KiB
bounds; the historical kill controller did not need this after a short READY
prefix. Avoid shell pipelines or a replacement launcher.

1. Fork and exec the unchanged launcher with `-t 1 0` and the payload. Record
   exact argv, environment, uid/gid, fd setup and all binary/DSO identities.
2. Read the exact READY prefix, then identify exactly one actual Linux worker
   blocked in nr0/fd0/read16. Record original TGID/TID and full syscall line.
   Announce a `ULTRA_FAULT_BLOCKED` marker. Keep the pipe writer open without
   supplying bytes. Use a bounded10-second capture window.
3. Host QMP stops the VM and captures the actual guest response/request/queue
   and registers. Verify the scheduled application and delivered read match
   the supervisor's worker. Require response status0 and wake state2 before
   injecting; otherwise this test has not exercised a real wake path. Explicitly
   continue QMP afterwards. Audit that this capture precedes input delivery;
   missing that window fails the original attempt instead of silently retrying.
4. Controller writes exactly16 bytes0xa5 and logs `ULTRA_FAULT_INPUT`. The real
   Linux read then returns16 and the unchanged launcher submits its actual
   RET. The verification send/notify callback is reached by that real result.
5. Retain the exact selection/injection/production error logs and watch the
   original `/proc/TGID/task/TID` until the worker leaves RET ioctl or ceases to
   exist. A live thread still in the RET ioctl after15 seconds is FAIL. A dead
   task must be identified under the retained unreaped TGID, not by a globally
   reused numerical TID. Record monotonic start/end and every observed syscall
   state. In permanent mode the deadline is measured from accepted completion,
   not from the initial intentionally blocking read.
6. For terminal modes, capture first, then terminate/reap only the controller's
   exact owned launcher if it has not exited already. Raw wait status is recorded
   without inventing a particular launcher exit code. Open `/dev/mcos0` from
   the supervisor and issue a correctly bound CREATE_PPD request to prove new
   application admission returns the original transport error: EIO for hard/
   notify, ETIMEDOUT for permanent pressure. This requires extracting the exact
   public ioctl constant; do not encode an assumed numeric command. Require no
   new scheduled application and no success marker from an attempted HELLO.
7. For recoverable mode, require actual `NATIVE_FAILURE_PASS`, intact guards,
   exit37, one returned read value16 and full normal retirement/procfs/pager
   cleanup. Then run eight unchanged HELLO applications with all original
   stdout/exit/route/cleanup assertions. No quarantine or service error is
   allowed in this mode.

Never require normal successful process retirement in terminal-quarantine
tests: that would force releasing storage still referenced by the guest.
Conversely, never allow quarantine as an alternative passing outcome for the
recoverable mode. Every mode has one frozen outcome contract.

## Memory and ownership evidence still required

The selection marker gives the actual physical response and delivery, not a
synthetic response. For prepublication/timeout capture its original40-byte
prefix after quarantine and again after a quiet interval of at least five
seconds. Require status0, the original accepted result16, no second publication
and no host write/reuse. Guest stack storage is still retained in these modes.

For notification failure, status1 publication permits immediate guest reuse.
Do not assert that the old physical address remains unchanged or dereference it
inside the kernel injector. Require one real ring publication and notification
failure marker, then prove no second publication/host access with independent
phase/owner observation. The 44 controlled protocol tests already cover a
recycled backing buffer, but this does not establish actual guest reuse.

The existing logs alone do not expose a complete response/payload/worker ledger
census. Before accepting the fault gate, implement a reviewed, verification-only
read-only observer or a source/DWARF-bound memory decoder that captures the
actual retained entry, completion, worker token, response claim and OS generation.
Freeze exact expected retained counts before execution and show they remain
stable during the quiet interval. A missing `/proc` node or an error printk is
not complete retained-ownership proof. This observer is an explicit remaining
implementation item, not supplied by the current two helpers.

Every mode gets a fresh guest with four Linux vCPUs/8 GiB/two NUMA nodes and one
McKernel CPU/128 MiB, the established four-container-CPU/12-GiB/no-swap/512-task
limit and no network. Keep a300-second outer QEMU bound and an independent host
deadline even if guest time stops. Preserve emergency RAM/queue/register
capture on timeout or failed QMP continuation. Discard quarantined VMs after
capture; no production shutdown/reclamation claim follows.

## Why the old runner is not directly converted

`run-native-application-signals.py` and
`run-native-application-owner-failure-2.py` contain valuable complete bootstrap,
module/input validation, QMP capture and benign assertions. Keep their original
benign regression on the production module as a separate result. The latter
controller kills before RET and expects normal cleanup/PID reuse afterwards;
that oracle is wrong for committed-response quarantine. Removing those normal
assertions and calling the resulting run an original PASS would weaken evidence.

A dedicated fault supervisor/runner can reuse captured platform functions and
exact boot setup with original/executed copies, but must have its own explicit
terminal-mode oracle. That runner, the actual owner observer, physically full
ring setup and all four actual guest results remain outstanding. The current
artifact makes the injection boundary and build path concrete without claiming
that broader missing infrastructure has already been implemented.
