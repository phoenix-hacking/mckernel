# Continuing-service failure candidate and H04 review — 2026-09-13

Status: **CANDIDATE; production unchanged; guest closure pending.** This is an
additive correction to H04 in `ultra-host-review-20260909.md:134`. It does not
alter that review or grant application execution permission. Root retains
integration/build/guest ownership while the original baseline replays run.

The reviewed source is HEAD `556f70929020d02d742d113c3775db6d6c71a505` with
the exact two production inputs below. Line references in this document refer
to those original files, before applying the candidate.

| Input | SHA-256 |
| --- | --- |
| `host-kernel/native-rust/smp_service.rs` | `38d336ee5d6d1dfaf739b78bf2c9b199a319c1ab2ddc1dedfd0aad0841c9919e` |
| `host-kernel/native-rust/smp_application.rs` | `de751736b2d102fae95f7ddc37d0d414f0fed174093de2f07b1f778f50a5351f` |
| `scripts/tests/fixtures/stability-service-failure-candidate.patch` | `46a9f18d0e27ad52865fe851b35097601d6e18b56eabe663f344ca9a1bb96120` |

## Corrected defect and minimal change

New CREATE/open already calls `Started::require_ready` before reservation:
`smp_memory.rs:2381`, `smp_service.rs:773`, `smp_service.rs:830`. A sequential
open after `Runtime.error` is set is therefore rejected. The original review's
unqualified claim that reservation admits applications after every such error
was too broad.

The remaining defects are concrete. The ready check and `Remote::reserve`
are separated by dropping the memory-context lock; reserve only checks the
separate `Remote.transport_error` under `slots` (`smp_application.rs:172`).
An opener that observed ready before failure can reserve afterward. Existing
`Application` handles dispatch through their retained Remote without repeating
the Runtime health check (`smp_service.rs:824`). Runtime failure presently
does not close those admissions or wake an accepted RET. Finally, the array
of Results in `Runtime::pump` evaluates all seven operations before examining
the first error (`smp_service.rs:537`), so later application publication can
precede failure handling even on one packet worker.

The 83-line candidate adds `Remote::fail_service(&AtomicI32, Error)`, calls it
from `Runtime::fail`, and changes the pump to seven sequential result checks.
The new method uses the same `slots` lock and existing `quarantine_transport`
transition as `fail_transport`. It records the Runtime error **while holding
slots**, applies quarantine, drops slots, then wakes. A standalone Runtime
CAS followed by public `fail_transport` would leave a visible failure/admission
window and is deliberately not the candidate. The original public
`fail_transport` and the internal locked publication transitions remain intact.

All independent drain steps still run in the original order. A failure is
handled before invoking the next step; the candidate does not return early
and strand unrelated sysfs/procfs exchanges. It does not clear errors, free
failed owners, retry unpublished results, stop Linux workers, implement OS
shutdown, or change zeroing/response-memory code.

## Exact failure and ordering contract

1. The first successful CAS of `Runtime.error` from zero wins among
   continuing-service failures. The existing negative Linux errno is retained
   permanently; subsequent errors cannot overwrite it. The one service log is
   emitted after releasing slots. There is no allocation in the new path.
2. `Remote.transport_error` preserves its own first terminal transport errno.
   If a transport error preceded the first continuing-service error, the two
   domains may legitimately hold different errors. The new method does not
   rewrite the earlier transport cause. Example: publication timeout `-110`,
   then metadata failure `-5`, then `-19` leaves Remote `-110`, Runtime `-5`.
   Readiness returns the Runtime error; direct reservation returns the Remote
   error. Evidence must record both, rather than claim a single chronological
   winner across two independent domains.
3. The admission boundary is the application `slots` mutex. An operation
   already holding it may complete before failure wins it. Once failure has
   published the Runtime error under this mutex, no subsequently admitted
   reservation/publication can pass the same mutex without seeing terminal
   state. The pre-existing lock-free CPU selectors can race, but actual
   publication rechecks health under slots (`smp_application.rs:269,516`).
4. Every retained Entry is marked quarantined and needs_cleanup; its real
   mailbox is quarantined; its procfs context is closed; the independent
   release mailbox is quarantined (`smp_application.rs:590`). Entries and
   claims remain allocated. Repeated failure does not close or release these
   owners again. The wake runs after the slots/releases guards are gone.
5. New workers/PREPARE/START reject quarantined entries. Ordinary WAIT returns
   `-32`; an already accepted RET wakes with `-71` and retains its accepted
   output bit (`smp_application.rs:649,678,916,976,1054`). A SCHEDULE already
   published before failure may already have returned success; this patch
   cannot undo that publication. In-progress Linux file I/O can also finish
   locally, but reacquisition of the mailbox blocks publishing its result.
   This is admission closure, not peer-stop or cancellation of all host I/O.

## Complete failure-caller and lock audit

All production calls to `Runtime::fail`, public `Remote::fail_transport`, and
the internal `quarantine_transport` were enumerated. No public failure method
may be called recursively while holding application slots. Internal
publication/deadline code must keep using the locked helper.

| Caller in original source | Locks at failure transition | Review conclusion |
| --- | --- | --- |
| `smp_service.rs:476`, `pump_regular` dispatch error | Dispatch returned; temporary transport guard assigning `pending = None` ends at its semicolon on line 474. | New slots acquisition follows release of transport and dispatch locks. EAGAIN remains bounded pending-packet backpressure and does not call fail. |
| `smp_service.rs:551`, old pump error loop; all seven replacement checks | Each complete method call has returned. `with_runtime_target` and its transport closure have unwound. `application.advance` has also dropped slots before returning. | Sequential checks may safely acquire slots. Continue other service drains afterward. |
| `smp_service.rs:672`, metadata worker | `metadata` returned; its procfs pending/service, sysfs pending/tree and claim-completion ledger guards have unwound (`smp_service.rs:288`). | No tree/ledger guard spans the new slots acquisition. A normal sysfs operation error encoded by `claim.complete(result)` need not fail Runtime; inject an error that actually propagates out. |
| `smp_service.rs:677`, zeroing worker | `zeroing` and `Memory::zero` returned; zero_pending and ledger guards have unwound. | Acquired zeroing tags survive the return; the failure path must never remove them. |
| `smp_service.rs:790`, `Started::first` during BOOT | Boot OS/CPU/topology/memory context remains held (`smp_memory.rs:2095,2328`). | Special pre-activation path: `prepared.continuing` retained the owner before first dispatch; worker tasks are still stopped. Quarantine takes only slots then releases; procfs close is atomic. It never enters the boot context or CPU locks. This preserves the existing outer-boot-to-slots order. |
| `smp_service.rs:611`, public `fail_transport` in `publish_syscalls` | The entire runtime-target closure ended at line 609, including CPU/controller, hotplug, topology and transport guards. | Public method locks slots, quarantines, drops slots and wakes. A later `Runtime::fail` repeats only the idempotent transition. |
| `smp_application.rs:582`, deadline expiry | Caller `advance` holds slots. The temporary releases guard in the expiry expression is gone before quarantine. | Calls locked helper directly; does not reacquire slots. `advance` drops slots before notify/return. |
| `smp_application.rs:630,639`, notification or hard publication failure | `publish_syscall` holds slots, and native caller may hold transport/CPU guards. A releases publish guard ends before `finish_publication`. | Locked helper acquires only releases; does not acquire transport/CPU or relock slots. Public failure/wake follows outside the native target closure. |

The relevant established ordering for outgoing syscalls is CPU controller /
hotplug / topology -> transport -> application slots -> response-memory ledger
or releases. See `smp_cpu.rs:993`, `smp_service.rs:582`, and
`smp_application.rs:509`. The candidate adds no inverse edge. Other application
operations may use slots -> pager registry -> memory ledger; none of the
new failure work accesses the pager registry or memory ledger.

`smp_application.rs:490` releases its short releases guard before taking slots;
the fallback release selection is after `drop(slots)`. Release admission and
publication already take slots before releases (`smp_application.rs:432,516`).
`Process::close`, the object actually called by quarantine, is an atomic
`live.store(false)` at `smp_procfs.rs:588`. It is **not** the different
`smp_procfs::Remote::close` at line 373, which locks procfs slots. No VFS drop,
procfs namespace teardown, sleep or resource lookup is introduced under slots.

This is a source-level lock audit, not Linux lockdep or scheduler evidence.
The integration review must keep the caller list current if another source
change adds failure paths. In particular, never move the new public helper
into `finish_publication` or `expire_publications`.

## Owned lifetime and zeroing boundaries

Every worker callback owns an Entry containing `Arc<Runtime>`
(`smp_service.rs:655`); task creation transfers the callback Box only on entry,
and final Thread drop joins before reclamation (`smp_service.rs:703,751`).
`Started` retains the Runtime and all three Thread owners (`:765`). Boot stores
Started before first dispatch (`smp_memory.rs:2092`). An application owns its
Started (`smp_service.rs:824`), and the external connection retains its exact
OS generation/module lease until after the backend close callback
(`os_runtime.rs:882,899,930,986`). Thus the new reference to `Runtime.error`
is a synchronous borrow of a live retained object; it is not stored or
published, and no new raw pointer or Arc cycle is introduced.

Zeroing control ownership is acquired under the memory ledger before the
pending-head exchange (`sysfs_zeroing.rs:69,81,87`). Acquired chunk tags are
retained before preflight/zero publication (`:113`); errors deliberately keep
all tags acquired so far. Successful completion releases the control only
after the final node access (`:159,177`). This code is untouched. Failure
before the head swap leaves that head unchanged; failure after it cannot
reattach or replay the detached chain merely to resume service.

The Runtime zeroing health check occurs before removing a queued request
(`smp_service.rs:618`). A call that passed this check before an unrelated
failure may still detach, finish or fail its independently owned batch.
There is no claimed atomic stop of a batch already in flight. Subsequent
worker invocations observe the recorded error and stop consuming new work.
The guest can still enqueue bounded pending requests while packet draining
continues; failed OS resource retention is not a shutdown/drain proof.

Unpublished syscall responses likewise retain their exact tags and owners.
Only final response publication calls `SyscallResponse::release`, which
removes bookkeeping under the ledger and does not access guest bytes afterward
(`sysfs_memory.rs:619`). The candidate invokes no release or guest write.

## Independent targeted tests prepared

New `scripts/tests/fixtures/stability-service-failure.rs` supplies six tests.
The complete real mailbox, response protocol and RPC implementation are used.
The candidate's Runtime fail/pump and Remote reserve/health/quarantine/
fail_transport/fail_service/publication/RET bodies are extracted byte-for-byte.
Linux mutex/condvar/allocation and procfs objects are substituted with bounded
standard-library mocks. Pump service bodies record effects and inject errors;
they do not claim to simulate Linux service execution.

| Test | Independent assertion / mutation detected |
| --- | --- |
| `service_error_is_not_visible_until_admission_mutex_is_owned` | Holds slots, blocks the real failure thread at lock entry and checks Runtime error remains zero until release. Detects the tempting CAS-before-quarantine race. |
| `stale_ready_observation_cannot_reserve_after_failure_and_old_owner_is_retained` | Uses the exact reserve method after a stale ready observation; checks existing mailbox/procfs/release closure and unchanged claimed response bytes. |
| `independent_domains_keep_their_first_errors_and_repeat_failure_keeps_owners` | Injects transport -110, Runtime -5 then -19; both original causes, retained bytes and one procfs closure survive. |
| `actual_committed_return_waiter_wakes_without_guest_publication_or_replay` | A standard-library thread waits in the exact RET body on an actual accepted mailbox result. Service failure wakes it with accepted=1/-71, no guest status write, no release and no subsequent publication callback. |
| `both_admission_failure_interleavings_have_one_retained_or_rejected_owner` | 32 barrier-started reserve/fail pairs accept either legitimate ordering, then require precisely a retained quarantined owner or a rejection. No leaked successful unquarantined reservation. |
| `each_pump_error_is_handled_before_later_steps_and_all_drain_steps_run` | Faults each of seven service positions, with a different subsequent errno. Every later step sees the first terminal state, every drain step still runs. Detects eager array evaluation and accidental short-circuiting. |

The test waiter limit is five seconds; synchronization polling is bounded to
three seconds. An outer reviewed supervisor is still required for compiler
and process cleanup. This fixture is not actual Linux task, native module,
guest failure, zeroing-fault, stale PREPARE/START, or lockdep evidence.

`scripts/tests/stage_stability_service_failure.py` only stages a fresh output.
It verifies the retained PASS reference capture's original/compiler-input
hashes and current input bindings, applies the candidate at exact hunk offsets
to copies, regenerates affected original
transport/committed-return extracts, appends the six tests, and emits input
hashes, extraction byte ranges and proposed future commands. The transport
fixture must equal its actual retained compiler input after formatting. The
two reviewed guest producer files may differ outside the seven extracted
methods each; all 14 bodies must appear uniquely byte-identical in the current
files, and the Rust EINVAL constant must also match. All other original inputs
outside the two candidate files must still match in full. These explicit
bindings are recorded alongside the complete current originals. It does not
compile, run tests, mutate production, launch a container, or enable runtime.

Example staging command (future attempt name must remain unused):

```text
python3 scripts/tests/stage_stability_service_failure.py \
  --reference-capture /home/holden/mckernel-work/scratch/native-application-transport-failure-20260909-2 \
  --output /home/holden/mckernel-work/scratch/stability-service-failure-20260913-1
```

The parent lane must run and retain the staged commands through its reviewed
supervisor in the established build environment before considering the patch
for production. Original transport fixtures and failure evidence stay intact.

## Actual guest closure requirements

H04 remains open until the source-bound candidate passes integration review,
all relevant existing controlled regressions, the rebuilt exact native module
baseline, and the following fresh-guest checks. Bind all compiler inputs,
module/image hashes, host/kernel configuration, commands, phases, deadlines,
raw process waits and physical snapshots. No score changes follow from this
document or a mock PASS.

1. Inject an unrelated metadata or protocol hard error that actually reaches
   `Runtime::fail`. Preserve owner generation, both error domains, typed
   retained counts, pending queues and tags before/at/after transition. A
   rejected user request encoded into an ordinary response is insufficient.
2. From previously retained handles exercise WAIT and accepted RET, worker
   open, PREPARE, queued START and copy/pager completion. Coordinate a CREATE
   stopped after ready checking but before reserve, then release it after the
   service failure. Require bounded rejection or correctly recorded earlier
   publication, no new guest publication after the failure boundary, no
   duplicate response/status write and no premature owner/tag release.
3. Force a zeroing failure before detachment and after detachment with a
   reviewed verification-only injector. Observe original pending/worker/
   control/chunk tags, head and response bytes. Require the pre-detach head to
   remain owned and the post-detach batch to remain quarantined; never reset
   errors or reconstruct a lost head. Separately distinguish a valid batch
   already in flight when an unrelated service fails and let it settle before
   comparing stable retained snapshots.
4. Exercise repeated failures and the earlier-transport/later-service ordering.
   Require unchanged first errors and stable failed-owner identity/counts.
   Demonstrate unaffected sysfs/procfs drain attempts continue within existing
   bounds. The failure log alone is not retained-owner evidence.
5. Run the four actual transport fault guests as separate gates: physical
   queue saturation with recovery, prepublication hard failure,
   postpublication notification failure, and permanent saturation/deadline.
   Record the true phase/ownership distinctions: prepublication has no status
   or release; postpublication can already have one status/release and must
   never touch reused bytes; recoverable fullness stays healthy; permanent
   fullness terminalizes at the existing five-second publication deadline.
6. Use a fresh guest after each terminal failure, preserve failed evidence,
   and rerun the unchanged ordinary native/application/control baseline on
   the final module. Quarantined owners remaining allocated is an expected
   terminal-failure result, not proof of normal shutdown or resource drain.

Only after all global gates pass can separately reviewed execution packets
unlock dependency-ready catalog cases. Normal shutdown/restart, VM
invalidation, external signals, robust futex/fork, vector/FPU and multicore
obligations remain their own queue and acceptance gates.

## Validation state for this preparation

Only source review and source/tool consistency checks were performed in this
lane. Python AST parsing, exact `git apply --check` against the unchanged
production inputs, and rustfmt parsing/formatting of the new fixture passed.
The fixture and candidate are **NOT COMPILED / NOT EXECUTED** here.

Source-only stage attempt `stability-service-failure-stage-20260913-1` failed
closed because its original whole-input rule compared the current transport
fixture with the capture's pre-rustfmt copy. Its immutable failure record is
retained in that scratch directory and the failure command is in `kernel.log`.
Inspection established exact equality with the actual retained compiled
fixture. It also found the later signal/futex/clone changes in the two producer
files; the explicit exact-body rebinding above records those differences.
Fresh attempt `stability-service-failure-stage-20260913-2` completed with
`STAGED_NOT_RUN`. Its source/record are ready for the parent lane, under
`/home/holden/mckernel-work/scratch/`; `/work/` is the container mapping.
The old failure is not overwritten or reclassified as a pass.

The root lane must attach actual compiler/test and guest validation records;
a proposed command or successful source extraction is not a passing test
result. Archive both staging records before any expanded-capture cleanup.
