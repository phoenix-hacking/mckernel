# Selected response retention candidate

This is source-only `response_retention_profile="published-retention-v1"`.
`prepare_stability_selected_retention.py` accepts exact held-v1 composed input
for mode 2 or 3, retains the original tree and changes three Rust files in a
fresh output tree. The original held-v1 fixture, 48 controlled test results and
first published module remain unchanged. None proves this candidate. A new
source review, controlled method tests, native build and stack inspection are
required before a new preparer/runner may authorize the prerequisite guest.
Modes 1 and 4 are unsupported and remain unchanged. Private command/version
`0xc100f502`/2 and operations 1–8 are unchanged.

## Ownership boundary and changes

The immutable selected Claim is published while `Remote.slots` is held. It
contains OS/generation, response ledger serial/index and physical start/end.
The new retention check compares those exact actual fields using the existing
owner matcher; cancellation/kernel/service eligibility and an optional wake
are irrelevant to retention. The real `SyscallResponse` adapter always exposes
this Claim. Selection matches before phase `bind`, so stage 0 is held too.

The original phase gate and its exact counter block move from the optional
send callback to the one actual `Mailbox` call into `Completion::publish`,
before eligibility is computed. Every selected completion stays owned there
until phase 3 **and** its original successful release-commit count is 1.
Unknown states and verification failure hold rather than authorize cleanup.
The healthy path retains the original barrier/host-hold accounting with no
double counting. These counters now describe attempts at the publication
entry; a no-wake attempt is held before the real method can skip `send`.
Actual send-attempt/notification counters retain their original meanings.

`cancel_call` checks a selected Response or Completion before its existing
completion/kernel early returns, `Delivery.cancel`, response take, or prefix
preparation. Before release it latches verification error -125 and returns
-71. Its original callers quarantine the mailbox/application, retaining the
Call and Worker. This is failed verification; it does not cancel the peer or
pretend that a missing completion started a publication timer.

The original prepare body now has an ownership-preserving result variant.
Every error returns the exact Response, including the failed second CAS after
stid/result writes. The selected normal return restores that Response in its
original Call, quarantines the mailbox and records the original error. There
is no retry and no unchanged-prefix claim on error. The original `prepare`
entry point retains its original consuming/error behavior for unselected
callers. Field access order, CAS order, original errors, successful Completion,
status store and release implementation are unchanged. No heap, unsafe code,
new physical read, owner substitution or Drop implementation is added.

The input ACK transfers no publication authority. Retention continues from
selection through input/RET and AcceptedReturn hold until the existing exact
one-shot operation 8 commits after its original Claim, nonce, sequence,
digest, health and coarse `(publication_since + 5)` deadline checks. No host
wait holds slots or the observer Permit. The production timer is neither
initialized early nor reset. The existing failed-release behavior retains the
capability. After a successful release, later verification errors cannot
undo publication; every host path must stop original-response reads before
its first release ACK attempt, including ambiguous transmit/copyout failures.

## Source map

The exact authority is published module build 1, record SHA256
`3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`,
under `/home/holden/mckernel-work/scratch/stability-published-hold-module-20260913-postpublish-notify-1`.
Line anchors below refer to its retained `staged-source` files.

| Path | Existing ownership behavior and candidate coverage |
| --- | --- |
| `smp_application.rs:1187` | Selection is committed under slots. The later phase bind at `smp_memory.rs:2459` cannot create an unheld stage-0 window. |
| `smp_application_syscall.rs:263` | Copied delivery updates precede SELECT. A selected Delivered request cannot be converted to kernel work by another `copied` transition (`begin_kernel:345`). Service admission/prepare at 196 also precedes selection. |
| `smp_application_syscall.rs:473` | Failed validation/copy preserves Delivered. A selected consuming prepare after `begin_return` now restores the original Response on failure. |
| `smp_application_syscall.rs:90` | Worker close retains an active delivery and invokes `cancel_call`. The new guard precedes any cancellation mutation; error quarantines rather than removes the worker. |
| `smp_application_syscall.rs:618` | Mailbox close/cancel-pending reaches the same guarded `cancel_call:660`. A selected live completion is guarded before its old early return too. |
| `smp_application_syscall.rs:563` | Sole actual native Completion publisher. The new universal entry gate precedes the old cancellation eligibility check and `Completion::publish`. Its successful final Call removal at 614 is therefore reachable only after release. |
| `application_syscall.rs:393` | Consuming prepare could previously drop its implicit owner on protocol/CAS failure. The selected preserving branch retains the capability, not merely an orphaned ledger tag. |
| `application_syscall.rs:449` | `wake=None` skips `send`; then response take, address, status=1 and release follow. This entire original method stays behind the new entry gate. A guard in `SyscallResponse::release` would be too late. |
| `smp_application.rs:65` | All six Entry removal sites (243,321,365,379,410,1172) require drained/release-ready conditions. A retained or quarantined selected Call prevents them. `Application::drop` (`smp_service.rs:985`) goes through this close path. |
| `sysfs_memory.rs:548` | No explicit Response/Completion/SyscallResponse Drop releases a tag or writes peer bytes. Explicit release at 634 alone removes the response/payload tags. Implicit drop was insufficient to claim typed ownership; the new paths retain the actual object. |
| `smp_memory.rs:895` | Started BootStorage deliberately keeps PreparedBoot, including its continuing Started (883,2094); first CPU start makes retention irreversible (1909). OS memory/resource release requires unstarted (1393,2232). Runtime retains its Memory and application owners. This backs the existing unsafe mapping contract at `sysfs_memory.rs:107`; an Arc alone is not the proof. |
| `smp_application_syscall.rs:636` | Only a real completion obtains its original coarse timer during the unchanged advance scan. Retained preparation/cancellation failure does not invent a timer. |

The unchanged guest `kernel/syscall.c:4050` stores the response on the offload
call's stack; the Rust reply loop at `kernel/rust/syscall_policy.rs:2767` waits
for completed status. Its signal check calls host interruption/termination
(`kernel/syscall.c:27210`); the native cancellation/removal paths above must
remain held. This is a scoped proof for the reviewed single-CPU payload and
current host/guest lifecycle, not general certification of arbitrary guest
memory corruption, asynchronous kernel thread destruction or another driver.
No guest kernel source is changed by this candidate.

## Required focused cases, before execution authority

Run each state scenario in a fresh supervised process using exact retained
native bodies and concrete instrumented ResponseMemory backing, never an
oracle that substitutes for `Completion::publish` or `cancel_call`.

- Exact selected wake-Some and wake-None attempts in stages 0,1,2,4,5,
  invalid states, and forged stage3 with commit0: zero send/address/status/
  release/drop, original capability present. A valid committed release permits
  the original behavior, even if a later verification error is latched.
- Actual cancellation via worker-close and cancel-pending, before and after
  prepare: original Delivery/Response/Completion/Worker preserved, no prefix
  writes, quarantine retained, error -71 with first invalid reason -125.
- Preserve errors for negative servicing TID, initial completed status,
  initial invalid wake state and a failed second CAS; after selected prepare
  failure the same object/Claim remains in the Call, no release/drop/retry.
  A post-write CAS failure may change stid/result and must remain failed.
- Unselected claims, including changed OS/generation/serial/index/span, follow
  unchanged completion/cancellation behavior. A legitimately older completed
  worker serial does not replace the selected active delivery.
- Dropping only launcher/Application handles after selected cancellation must
  leave the existing Entry/drained/retirement conditions false; no synthetic
  Arc-only assertion can stand in for actual BootStorage/Runtime source proof.
- Bound and compare counters: exactly one old gate block at prepublish, zero
  old block in optional send; production completion timer unchanged; no
  selected completion receives address/release before committed release.

The new stager needs original-hash drift, wrong mode, duplicate/missing hooks,
inverse restoration, source-change, reused output and retained special-file
negative checks before use. Root owns those tests, actual compilation, stack
comparison and any subsequent controlled guest. Physical-ring fullness,
payload acceptance and whole-OS acceptance remain separate open gates.
