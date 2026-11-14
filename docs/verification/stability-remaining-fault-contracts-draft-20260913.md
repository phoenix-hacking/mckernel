# Remaining native transport modes: draft contracts

Status: **SOURCE-DERIVED DRAFTS; EXECUTION DISABLED.** These three additive
owner-contract inputs use the existing strict parser schema. Their presence
does not release a mode, authorize compilation/execution, or close a runtime
gate. The original hard contract and all frozen runner, preparer, observer and
production sources remain unchanged. Root must review the exact new workload,
mode-specific compiled overlay, collector changes and expected evidence before
execution. The accompanying JSON binds the source bytes read for this draft.

The drafts are under `scripts/application-tests/contracts/drafts/`:

| Overlay mode | ID | Draft file | Owner-parser mode |
| --- | --- | --- | --- |
| postpublish-notify | 2 | stability-postpublish-notify-20260913-v1.json | postpublication-notify |
| recoverable-backpressure | 3 | stability-recoverable-backpressure-20260913-v1.json | recovery-before-deadline |
| permanent-backpressure | 4 | stability-permanent-backpressure-20260913-v1.json | permanent-pressure |

## Shared selected-read contract

Keep the real runnable-thread fixture and its exact Linux-reference result
separately bound. The ordinary operation remains `read(0, buffer + 8, 16)`;
the controller writes exactly sixteen bytes `a5` only after the host validates
the native BlockedRead owner, original Linux worker/start ticks and a stopped
physical response with status0/wake2, then verifies QMP continuation. READY
and a runnable-peer handshake do not replace the wake2 observation.

The immutable selection carries actual OS/generation, PID, guest requester/CPU,
application token, Linux worker token/TID, delivery and response ledger
serial/index/span. Keep all six original request arguments, target, number
and response identity unchanged for every snapshot retaining that delivery.
Other complete thread/owner rows are allowed; no fixed worker count is inferred.
The existing bounds remain8 apps,8 calls per mailbox,16 workers/tags/pagers.
All independently sampled domains must be complete; no phase is a whole-OS
atomic snapshot (`owner_observations.py:224,310`; `phase_observations.py:219`).

Exact selected-serial counters follow below. Every phase has payload_calls0,
payload_bytes0, after_release_calls0 and duplicate_release0. The ordinary Rust
launcher read returns value16 with RET transfer length0; selected payload-copy
hooks are only on the separate pager-copy path. Extra pthread setup claims
cannot count against the selected response serial
(`smp_application.rs:943–973`; `stability_observer.rs:245–277`; the retained
hard-contract derivation and spinner owner review bind the launcher/workload).

| Phase | Modes2 and3: address/release/released | Mode4: address/release/released |
| --- | --- | --- |
| BlockedRead | 0 / 0 / false | 0 / 0 / false |
| AcceptedReturn | 1 / 0 / false | 1 / 0 / false |
| Terminal or Recovery | 2 / 1 / true | 1 / 0 / false |
| TerminalPlusFive or AfterEightHello | 2 / 1 / true | 1 / 0 / false |

`Response::prepare` acquires the first response address and writes only stid,
value and wake state. `Completion::publish` calls the actual send callback
before the second address acquisition, status1 release-store and final host
ledger release (`host-kernel/native-rust/application_syscall.rs:398–459`).
The original response's first word and fault field are opaque preserved bytes,
not requester identity constants. Native ownership covers40 bytes, not the
guest ABI's extra optional/guest-only field.

Each RET is actual native ENTER/LEAVE around the real RETURN invocation,
accepted1, value16, same worker/delivery/CPU, and elapsed at most15 seconds.
Modes2/4 expect errno-71; mode3 expects0. The controller's separate input-to-
return/completion15-second deadline and the outer bounded watchdog also apply.
RET-71 does not mean the guest payload returned errno71. Terminal launcher raw
wait and owned cleanup are recorded separately, with no payload-success claim.

All modes require BlockedRead fault counters0. AcceptedReturn fault counters
are also0 except barrier_attempts, which can legitimately be0 or positive.
Phase barrier_calls and fault barrier_attempts must agree, remain monotonic,
and stop changing after AcceptedReturn. Barrier EAGAIN is observation machinery,
not a fault attempt or physical queue saturation. No production deadline resets.
Fault-selected appears exactly once after AcceptedReturn END. All terminal or
recovery/after-eight fault counters are equal, with no overflow or cap violation
(`send.append.rs:61–124`; `phase_observations.py:240–352`).

## Mode2: successful publication, failed notification

The original queue callback must actually succeed once. Before that final
success, real callbacks may return only-11/-16; no earlier success is allowed.
Final attempts == real_sends, between1 and32; published1 and
notification_failures1. Ordered records are SELECTED, each REAL_SEND, PUBLISHED,
then NOTIFICATION(errno-5,published1), all before the original RET leaves.
The notification wrapper deliberately returns-5 instead of invoking the
original notifier for this selected OS/generation/app/CPU
(`send.append.rs:92–116`). This is a controlled notification failure, not proof
of a hardware IPI failure.

Successful publication removes the original CALL/DELIVERY, clears its WORKER
delivery and records completed=original delivery; response/payload ledger tags
for that selected serial are absent. Notification quarantine happens under
the same slots mutex before RET may observe success. The selected worker
record remains retained because quarantined close_worker rejects retirement
(`smp_application_syscall.rs:90–118,555–590`; `smp_application.rs:509–540,636–649`).
These selected ownership assertions need an explicit additional checker;
the current mode2 phase parser checks health and counters but does not assert
all selected CALL/tag absence and WORKER completion properties.

Terminal and TerminalPlusFive runtime/application errors are-5; all observed
application entries need_cleanup/quarantined and all mailboxes closed/
quarantined. The complete independently sampled inventories and selected
counters must match exactly across those snapshots, separated by at least
five native monotonic seconds. New admission must return-1/errno5, not RET's
errno71. No eight-HELLO success is expected in this terminal OS.

**Never read the original response after publication/release**, including
POST_RET, QUIET, final-export and emergency paths. A released address can
already belong to the guest again. Retain real ring bytes and selected owner
metadata instead. Prove the unique selected wake's actual publication using
source-bound port501/message0x14/requester-at-offset24 and a retained counter
interval; an overwritten interval cannot prove presence or absence. A later
unrelated notification or timer may let the guest consume that packet, so
do not require it to remain queued or require the payload to stay asleep.

## Mode3: transient injected backpressure and recovery

The first post-barrier attempt fixes since_ns and returns-11. Every attempt
before since_ns+2,000,000,000ns returns-11 without calling the real publisher.
After that hold, real sends may return-11/-16 and finally exactly one0.
Final attempts > real_sends >=1, real_sends <=32, published1,
notification_failures0. Records end in RECOVERED after the actual successful
callback. This final callback must complete strictly before the original
production deadline `(publication_since_seconds + 5) * 1,000,000,000`.

The production timer is initialized by the first `publication_expired` scan
of a committed completion, using `ktime_get_seconds`; it is not initialized
at RET or reset on retry (`smp_application_syscall.rs:610–622`;
`smp_application.rs:22,217–223,570–583`). Pump publishes syscalls before that
scan (`smp_service.rs:551–555`). AcceptedReturn can legitimately contain None.
If no original timer value was observed, the existing parser reports
METADATA_MATCH_WITH_MISSING_TIMER and the exact deadline gate stays **OPEN**.
Do not substitute fault since_ns. A future minimal verification-only scalar
record of the actual selected Call timer, captured while its existing lock
is held, needs separate source review, exact key binding and parser tests.

Recovery requires the payload's natural launcher exit37, raw wait9472,
no cleanup kill, exact stdout `NATIVE_FAILURE_READY\nNATIVE_FAILURE_PASS\n`,
empty stderr and both EOFs within the original15-second input deadline. The
guarded buffer check and stopping/joining the spinner remain in the exact
payload source. Then native Recovery must report runtime0/transport0, stage3,
original app absent and application count0. This is already required by the
phase ioctl and natural-completion controller path
(`owner-phase-v1/controller.c:862–880,934–973`; phase `smp_service.append.rs:77`).

After Recovery, run exactly eight sequential ordinary
`/bin/mcexec -t 1 0 /bin/native-application-hello` invocations in the same live
OS/generation. For each, retain fresh command/argv/env/cwd, actual raw wait9472,
stdout exactly `NATIVE_APPLICATION_HELLO\n` (25 bytes), empty stderr, EOFs,
bounded completion, exact ELF/launcher identities and original registration
retirement. No restart, module reload, generation change or substituted Linux
execution qualifies. The expected bytes and exit37 come from
`scripts/tests/fixtures/native-application-hello.S:8–32`; historical baseline
results do not substitute for these eight new launches.

Only then invoke the existing after-hello client with the exact retained
256-byte Recovery reply, same OS/generation/nonce and fresh attempt directory.
It validates key/sequence and asks for AfterEightHello, but deliberately sets
eight_hello_launches_verified=false: it counts no launches itself
(`owner-phase-v1/after_hello.c:7–34`; `phase_client.h:278–315`).

AfterEightHello requires healthy runtime/app errors0, application count0,
original app/call/worker/selected response tag absent, complete domains and
unchanged selected-serial and fault counters. Verify each HELLO's owner/procfs
retirement separately. Do not require whole Recovery/AfterEight inventories
to be byte-equal: legitimate new allocation serials and cumulative counters
advance across eight applications. Do not invent zero for all shared ledger
classes or unrelated permanent owners; bind a quiescent class inventory and
verify actual transient-owner drainage explicitly. The current phase ioctl
checks applications0, not eight launches or complete global leak freedom.

Postpublication response reads are forbidden here as in mode2. Separate
prepublication physical-prefix evidence and actual ring publication remain
required even when exact payload output succeeds.

## Mode4: permanent injected backpressure

Every selected post-barrier send attempt returns-11; attempts >=1,
real_sends0, published0, notification_failures0. The actual per-call production
timer eventually expires at five coarse monotonic seconds and the first
transport/runtime error is-110. Terminal and TerminalPlusFive must retain the
same selected Returning delivery, original worker/TID and completion with
response+wake ownership, the response ledger claim and Some(original timer).
Their BEGIN timestamps must be at or after `(timer+5)*1e9`. Selected address1,
release0 and unchanged timer/counters/inventories prove retention only within
the observed scope. New admission returns-1/errno110.

With ownership still retained and published0, stopped PRE_INPUT, Terminal and
TerminalPlusFive response capture can use the hard comparator's exact byte
invariant: only stid/wake/result change after BlockedRead and the two terminal
40-byte images are identical. Retain the real port501/503 rings; no newly
published selected wake is allowed within a complete nonoverwritten interval.
Capture original failure evidence before owned cleanup.

## Collector changes required before releasing any draft

1. Replace hard-coded mode/contract choices in a separately reviewed runner
   and preparer revision. Bind requested mode to its exact compiled overlay,
   payload/compiler/ELF, root inventory, contract hash, nonce and actual boot
   OS/generation. Current restrictions are deliberate
   (`prepare_stability_fault_guest.py:86,120,289`;
   `run_stability_transport_guest.py:107,202,225,320,374,422`).
2. Choose UART/native phase sequences explicitly: terminal modes use three
   ACKs PRE_INPUT/POST_RET/QUIET; recovery uses two PRE_INPUT/POST_RET. Current
   fault_control.py already expresses this, but runner assertions and snapshot
   mapping are hard-coded to Terminal and three ACKs. Recovery must map POST_RET
   to Recovery; AfterEightHello is a later client/exported native observation,
   not an invented third controller ACK.
3. Separate physical capture policy by ownership epoch. Modes2/3 may only
   read the original response at BlockedRead; modes1/4 may read it at retained
   terminal snapshots after validating release0/published0. Emergency reads no
   original response. The automatic AcceptedReturn print barrier releases
   before QMP can guarantee a stopped physical snapshot; metadata is not that
   missing capture. Preserve this gap or add separately reviewed prepublication
   byte observation with a bounded barrier and unchanged production deadline.
4. Add strict selected ownership absence/completion checks for mode2 and
   transient-owner retirement checks for recovery. Adapt admission errno5 vs110,
   raw-wait/payload expectations and final remaining-evidence lists by mode.
   Mode2 payload progress after another wake is possible; retain raw streams
   without silently making terminal launcher exit a payload-success oracle.
5. Extend the recovery initializer to run and capture eight bounded ordinary
   HELLOs, then invoke `/bin/fault-after-hello --after-eight-hello OS GENERATION
   NONCE RECOVERY_REPLY FRESH_DIRECTORY` before final dmesg/export. The current
   preparer copies that ELF but never invokes it (`:157–158,261–268`). Add exact
   per-launch provenance and raw waits; shell `$?` alone is not a raw wait word.
   Budget the complete export tree under existing256-entry/16-MiB limits.
   The controller's48 probe attempts and the after-hello client's independent
   attempt limit cannot both be budgeted as though each had the whole tree.
   Preserve original capture/error/cleanup deadlines and guest300-second cap.
6. Add positive real-publication ring comparison for modes2/3; the current pure
   physical helper only locates a consumed original request, rejects a new
   selected wake, and compares retained hard responses. Do not repurpose its
   absence comparator to assert successful publication. Preserve actual queue
   identities, monotonic counters, retained-slot bounds and exact packet bytes.
7. Resolve mode3's missing original timer if encountered, then independently
   review all source, strict negative cases and exact compiled artifacts.
   These drafts have not been imported, tested or executed in this author lane.

## Physical-full-ring requirement remains separate

Modes3/4 inject EAGAIN before the real publisher; their attempts do not prove
a full queue. The actual queue maps Full and Busy to EBUSY(-16), which also
may mean local producer contention (`ikc_queue.rs:45–50`; `smp_ikc.rs:98–134`).
Neither injected EAGAIN nor an unbound EBUSY alone proves fullness. A real full-ring test
must establish the exact live port501 queue, reserved-read ==126 for its127
slots, actual no-publication failure, stable owned completion, and subsequent
drain/retry or unchanged-deadline quarantine without manually falsifying peer
counters (`ikc_queue.rs:336–338,367–422`; `smp_ikc.rs:98–134`). Its workload,
bounded safe saturation mechanism and evidence plan require separate review.
All these drafts keep physical_full_ring_verified=false and all application,
transport and production acceptance false.
