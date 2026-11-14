# Ultra review: native host application ownership and failure behavior

Reviewed source revision: `484e429c63493f54f62de2e6c29fdeefdfa5e549`.
The initial findings below are a source review. The subsequently authorized
H01/H02 edit and its separate protocol results are recorded at the end; the
root agent owns build/guest validation and Git changes. The user has explicitly
started the Ultra phase. The baseline in
[the handoff](native-application-ultra-handoff-20260909.md) remains valid within
its stated limits, for its original source/module/image pair.

The reviewed application, mailbox, process, mirror, pager, continuing-service
and memory-ledger sources are selected compiler inputs of signal module 1,
bound by [the signal checkpoint](native-application-signals-checkpoint-20260909.json).
These findings concern the current tested native path, rather than an unused
legacy implementation. Native implementation sources have not changed since
`3453edd571152132b19d23b26dad32f4204612e6`.

## Findings requiring an explicit decision before stress tests

### H01 — High: permanent failure after RET acceptance can strand an unkillable worker

**Source-established liveness gap; not reproduced in a guest by this review.**

- `host-kernel/native-rust/smp_application.rs:796-852` accepts the copied return,
  sets the accepted output word to one, and waits with uninterruptible
  `CondVar::wait`. It exits on actual mailbox completion or entry quarantine.
- `host-kernel/native-rust/smp_application.rs:506-509` propagates a hard
  publication error without quarantining the entry.
- `host-kernel/native-rust/smp_service.rs:582-610` suppresses queue-full
  `EBUSY/EAGAIN`, propagates other publication/target errors, and wakes host
  waiters. `Runtime::fail` at lines 140-148 records a global error and log; it
  does not set the application's terminal state. A wake alone makes the RET
  waiter check the same incomplete state and sleep again.
- If a wake is required and the destination ring remains full, the same wait
  also has no progress deadline. The independently retained completion avoids
  replay and premature release, but SIGKILL cannot interrupt this sleep.

Trigger: deliver a real syscall to a worker; accept its RET while the guest
response requires a wake; prevent successful wake-ring publication forever,
either through a hard error or permanent queue pressure. The original response,
result and owners remain retained. The accepted blocked-read/SIGKILL baseline
kills a worker **before** RET acceptance and does not exercise this sequence.

The existing test `scripts/tests/fixtures/native-application-committed-return.rs:142`
checks an externally quarantined waiter. Its fake wait implementation at lines
44-57 directly sets `entry.quarantined = true`; it does not prove that a real
transport error invokes that transition. Its 1,024 EAGAIN retries prove retained
publication state, not a bounded Linux task lifetime under permanent pressure.

Required design and validation before enabling transport/exhaustion stress:

1. Add one production failure transition at the owning transport/application
   boundary, with the original error, phase, application token and CPU. An
   error whose channel cannot be isolated must fail admission for that OS
   generation. Update state under its mutex, then notify outside
   transport/resource locks. Ordinary WAIT, new worker/open/prepare/start,
   pager/invalidation waiters and accepted RET must observe the terminal state.
2. On a proven **prepublication** hard error, close affected admissions,
   quarantine the incomplete completion and retain every response/payload
   claim, prepared image and OS owner. Never fabricate status=1, replay the
   syscall, release its memory, or reuse its PID/token. Return a terminal error
   to the host waiter with the accepted bit still one. The adapter already
   consumes that bit at `mcctrl_process.rs:330-337`.
3. Define permanent backpressure separately. Proposed initial contract: a
   monotonic 5-second lack-of-progress deadline for an accepted completion in
   the packet owner, reset only by its actual progress, followed by terminal
   retained quarantine. Ordinary recoverable EAGAIN must keep the same exact
   wake/result. The test's guest watchdog remains 300 seconds; it is not the
   production progress deadline. Confirm this deadline against slow TCG before
   committing it as a product contract.
4. Extract and execute the real failure transition in the existing exact-method
   fixture. Cover 0/1/1,024 EAGAIN retries then success, first-attempt and
   delayed `EIO`, and deadline boundary just before/at/after expiry with a
   deterministic clock. Assert one terminal transition, accepted=1, no duplicate
   return/copy/wake, zero release calls before publication, no worker/PID reuse,
   and no later publication from a terminally quarantined completion.
5. Repeat in an isolated guest with a test-only, source-bound fault hook at the
   real publication boundary. Capture phase and response bytes before fault,
   after terminal observation and after a quiet interval. Require the launcher
   to become killable and reap within 15 seconds. A quarantined OS may require
   discarding that QEMU instance; OS shutdown/reclamation is a separate gate.

### H02 — High: postpublication notification failure is a separate recovery obligation

**Source-established ordering; delivery failure outcome remains untested.**

`application_syscall.rs:438-459` publishes the wake packet, stores response
status=1 and releases the response claim. `smp_application_syscall.rs:542-575`
then marks the worker complete and removes the call. Only afterwards does
`smp_service.rs:602` notify the guest CPU. Thus an APIC notification error can
occur after the guest is already entitled to recycle response memory. RET can
observe the completed mailbox. The current global error record supplies no
explicit pending-notification recovery state.

Do not combine this with H01 by retrying `Completion::publish`: that would
duplicate a published wake and can access recycled memory. Keep an independent
notification obligation owned by the exact live CPU/channel/OS generation.
Retry only the notification, with a bounded terminal-failure policy. Define
whether RET completion promises response/ring publication alone or additionally
successful notification; encode that choice in the API and tests.

Deterministic test requirements: fail notification after one successful ring
publication; immediately overwrite/reuse the response backing bytes; permit
notification recovery; require exactly one original wake, exactly one response
release, no subsequent response read/write, and one guest observation. Repeat
with permanent notification failure and require reported OS failure, closed
new admissions, retained live transport/OS owners and bounded host waiters.
Do not claim successful guest execution solely from the host RET result.

### H03 — High capability gap: process fork is not implemented by the native CREATE_PPD adapter

**Proven explicit unsupported path, not a new regression.**

`mcctrl_process.rs:990-1000` returns `-EOPNOTSUPP` for every non-null
CREATE_PPD descriptor after preserving user-copy errors. The unchanged selected
Rust launcher calls `mcexec_clone_child_bridge`
(`executer/user/rust/mcexec_helpers.rs:2071`). That bridge constructs the fork
page-table descriptor and issues non-null CREATE_PPD at
`executer/user/mcexec.c:5908-5922`. The C fallback repeats the same operation at
lines 8157-8178. Guest fork's private nr56 exchange reaches this path; passing
pthread/clone3 with shared VM does not establish ordinary fork support.

Consequences: shell pipelines, `system`/`popen`, process pools and programs using
fork/exec cannot be promoted to accepted workloads from the present baseline.
First specify whether initial Spark tests should assert the documented failure
and clean rollback or whether Ultra will implement this capability. Successful
fork tests must remain dependency-blocked until the exact child MM/page-table
adoption, stale inherited worker removal, child registration, phase-1 handshake,
PID identity, parent/child exit and rollback adapters are implemented and tested.
Reuse the existing guest/Rust launcher bodies; do not replace their protocol
with a synthetic child result. Coordinate with the guest review for rollback,
wait status and COW semantics.

### H04 — Medium: any continuing-service error disables allocator zeroing globally

**Proven behavior; recovery contract is incomplete.**

Every service failure can set `Runtime.error` in `smp_service.rs:140-148`.
`zeroing` at lines 613-615 then stops processing all later pending zero batches.
The packet worker continues pumping (`smp_service.rs:536-553,660-680`), and
application reservation at `smp_application.rs:172-208` has no runtime-health
check. A fault unrelated to zeroing can therefore leave the OS admitting
applications while its zeroing service is permanently disabled.

The zeroing implementation deliberately retains detached-batch tags on error
(`sysfs_zeroing.rs:50-54`); preserve this safety property. Define the containing
OS as failed and close application admission, or implement a justified narrower
service-failure policy. Never clear the global error to resume a lost batch
without proving ownership of every detached chunk. Validate an unrelated
metadata/protocol hard error followed by an attempted application admission,
and a zeroing allocation failure before and after head detachment. Require
explicit health/retained-count evidence and no silent continued acceptance.

## Required coverage beyond the four smoke categories

These are untested risks and acceptance gaps, **not claims of additional proven
memory corruption**. Current code has meaningful ownership defenses: referenced
Linux PID objects (`mcctrl_process.rs:583-645`), structural MM references without
an `mm_users` cycle (`mcctrl_vm.rs:31-94`), exact mirror identity checks, a shared
overlap ledger (`sysfs_memory.rs:47-89`), deferred in-kernel cancellation
(`smp_application_syscall.rs:403-449,593-604`) and publication-only claim release.
Tests must exercise those production bodies instead of replacing them with
parallel models.

| Priority | Required test family | Exact acceptance points |
| --- | --- | --- |
| P0 | Committed return faults and signals | H01/H02 matrix; nonfatal signals before acceptance, during pending publication and after publication; original return value and one side effect only. |
| P0 | Failure at every worker phase | WAIT idle, descriptor copyout, Delivered, in-kernel pager I/O, in-kernel PTE invalidation, Returning, published, normal exit; real task identity plus no stale memory writes after release. Preserve a separate test for each phase. |
| P0 | Native syscall delegation classification | `Request::decode` validates envelope geometry but no syscall-number allowlist (`application_syscall.rs:35-70`); mcctrl special-cases only pager nr9 and invalidation nr11 before ordinary WAIT copyout. Coordinate with guest review to classify absent modern syscalls before broad binaries can execute them in a Linux worker. |
| P1 | VMA and MM identity | Same-MM worker success; forked/inherited control-file caller and post-exec MM rejected before mutation; fragmented mirror VMAs, holes and foreign mappings; invalidation preflight must prevent partial changes on a later bad VMA (`mcctrl_vm.rs:212-260`). |
| P1 | Guarded user copy | WAIT output crossing an inaccessible page must retain/requeue the exact delivery. RET input/payload faults before acceptance must permit a valid retry without duplicated effects. TID transfer sizes/direction/physical mismatch and second-transfer rejection must leave adjacent guard bytes intact. |
| P1 | File pager lifecycle | Two mappings of one inode, distinct files, close/unlink while mapped, RO versus RW descriptors, fd-number reuse, final RELEASE during in-flight positional I/O, malformed release counts, short I/O/EOF, non-page-sized last page, truncate and page-fault races. Check handle refs and exact file identity, not only path strings (`smp_file_pager.rs:205-377`). |
| P1 | Bounded exhaustion | 64 application slots, 64 workers/calls per application, 4,096 shared response/payload slots, 4,096 pager handles. Exact capacity and capacity+1 tests must use source-bound protocol fixtures first. Guest tests must remain within 128 MiB/512-task limits and must not create 4,096 Linux tasks. Distinguish explicit EAGAIN admission from quarantined leaks. |
| P1 | Concurrent cleanup | Two mcos file bindings in one TGID, racing CREATE_PPD, concurrent last-close and reaper snapshots, surviving inherited files, active procfs reads and VMA references, and numerical PID/TID reuse. Require owner detach once and no cleanup of a winning registration by the loser (`mcctrl_process.rs:673-691,814-863,907-928,1002-1018`). |
| P1 | Zeroing pressure | Reuse freed pages filled with nonzero patterns; cross-extent chunks, empty batches, coalescing and repeated pending batches. Observe actual pending/worker/ledger counts; an earlier nonempty zeroed batch does not prove all current pending pages drained. |
| P2 | Multicore/multi-OS routing | Keep blocked until a separate topology gate. Tests must distinguish guest CPU from Linux worker slot, full destination-specific queues, inter-application fairness and cross-generation rejection. One McKernel CPU cannot establish these results. |

For stress acceptance, add a bounded read-only diagnostic snapshot or exact
test extraction exposing active application/worker/call states, quarantined
entries, all ledger categories, pager handles/reference totals and pending
notification counts. Current logs are deliberately sampled (64 complete syscall
deliveries per registration and 256 zeroing records). A missing log line is not
proof that resources returned to baseline. At each quiet checkpoint require
zero ordinary application owners/calls/response/payload claims, no outstanding
notifications, and explicit documented OS-owned residual counts. Quarantined
tests require stable nonzero retained counts rather than incorrectly requiring
their release.

Any behavior change requires a new pre-edit reuse/dependency review under
AGENTS.md: retain the current mailbox/RPC and guest protocol, use the pinned
Linux CondVar/time/task APIs, preserve fallback selection and all original
assertions, then rebuild and rebind the changed native source. Preserve the
first failing test and stop that validation batch. No existing baseline PASS
should be reinterpreted as coverage for these additional obligations.

## Selected dependency and reuse review before the H01/H02 edit

The root agent authorized a bounded fix of H01/H02 after this review. The edit
will retain `application_syscall::{Response,Completion}` and its exact
publication/release ordering; retain the entire `smp_application_syscall::Mailbox`
and add only terminal quarantine and a per-completion monotonic deadline;
adapt `smp_application::Remote` and the existing `smp_service::Runtime` caller.
No new C bridge, Linux patch, wire/UAPI field or kernel module is needed.

Pinned Linux `rust/kernel/sync/condvar.rs:115-148` queues the waiter before
unlocking and uses `TASK_UNINTERRUPTIBLE`; retain that committed-result wait and
wake it by setting production terminal state under the same application mutex.
Reuse existing `ktime_get_seconds`, declared in `include/linux/timekeeping.h:58`
and implemented/exported in `kernel/time/timekeeping.c:931-946`; it is
CLOCK_MONOTONIC, already selected by application retirement retries. Deadlines
apply to committed completions, not ordinary intentionally blocking syscalls.
The initial timeout is five monotonic seconds after a completion is first
observed by the packet pump; expiry retains ownership and returns a terminal
error rather than fabricating a syscall result.

`smp_ikc::notify` is the existing nonblocking APIC notification adapter. Keep
its result separate from the callback passed to `Completion::publish`:
the latter still means queue publication only. Serialize application mailbox
publication and its notification outcome under the application mutex so an
accepted RET cannot race through success before a notification error is
recorded. On notification failure, the published response remains retired;
only transport/OS/application owners and unfinished calls are quarantined.
The selected bounded recovery policy is terminal failure for that OS's
application service, with no second publication and no retry of a completed
response. Broader OS recovery/shutdown is outside this edit.

A hard application transport error will close every application admission in
that exact Remote generation, retain its bounded slots/claims, and wake
waiters. Separate `Runtime::fail` sources remain outside the H01/H02 claim
unless explicitly connected and validated. Reuse the current exact-method
committed-return fixture and its full mailbox/producers; add a dedicated
failure fixture calling extracted production transition/publication methods,
including postpublication memory-reuse guards. Root owns serialized container
validation and later source/module/image binding.

Implementation draft now changes only `smp_application.rs`,
`smp_application_syscall.rs` and `smp_service.rs`, plus the dedicated
`native-application-transport-failure.rs` fixture. In particular, the callback
passed into `Mailbox::publish` still performs queue publication alone. A
separate `finish_publication` handles notification while the application mutex
remains held. A postpublication error never returns control to the mailbox
publication code; it permanently closes that Remote and subsequent publication
attempts fail before calling either callback. Completed response claims stay
released, while incomplete claims and bounded application owners stay retained.
The first transport error is preserved and the terminal transition is
idempotent. Actual guest fault-injection acceptance is still pending.

The new helper is `/work/test-native-application-transport-failure.py`; it
copies complete original inputs, retains seven exact Remote method extractions,
runs the complete original producer/mailbox and committed-return tests, then
the dedicated failure matrix. It uses a controlled mutex/clock/notification
environment and does not claim Linux scheduler or real guest failure coverage.
Root will serialize this helper and all subsequent module/guest validation.

Root's native-container attempt 1 failed during Rust compilation under the
unchanged `-D warnings`: the new fixture had an unused logging macro, and its
discarding error macro left the production error variable unused. Root logged
and preserved that entire original attempt. The fixture now consumes real
`format_args!` and supplies only the scalar owner/cleanup values needed by
those production logs; no warning checks were disabled.

Root's fresh `/work/native-application-transport-failure-20260909-2/record.json`
reports PASS: all **44 tests** pass, comprising all 37 original
producer/mailbox/committed-return tests plus seven new failure tests. It
retains the seven production method extractions, full originals, actual
compiler inputs, commands and three pinned Linux reference files. The record
explicitly sets `actual_guest_transport_fault_verified=false`. The passing
controlled tests establish prepublication hard-error handling, postpublication
notification failure, 1,024 recoverable queue-full retries, safe response reuse,
idempotent quarantine, per-completion deadline boundaries and refusal of later
in-kernel copy/publication. They do not establish real task wakeup latency or
real fault-injected guest execution.

The deadline depends on the independent packet worker continuing to run. It
does not bound a dead packet worker or Linux I/O that never returns before a
completion exists. Existing guest watchdog/discard remains necessary for those
conditions. H03, H04, full OS recovery/shutdown, real fault injection and the
remaining coverage table are not resolved by this bounded H01/H02 change.
