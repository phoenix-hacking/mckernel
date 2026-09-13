# Verification-only native owner observer — 2026-09-13

Status: **PREPARED, NOT COMPILED, NOT EXECUTED, NOT WIRED.** No production
source was changed by this lane. The parent owns phase/controller integration,
physical QMP captures, isolated native builds and actual fault guests. This
observer does not itself inject a failure, fill a queue or grant execution
permission. It includes the current H04 production repair through the exact
input capture, without editing `fail_service` or the sequential pump.

New implementation inputs are under
`scripts/tests/fixtures/stability-owner-observer/`. The preparation entry point
is `scripts/tests/prepare_stability_owner_observer.py`. It creates a fresh flat
overlay directory containing complete overlaid files, original copies, exact
diffs, the new `stability_observer.rs` module, appendix/helper copies and a
source identity/inverse-restoration record. It never modifies `--source`.
No production cfg flag or ordinary build configuration is changed.

## What is observed

Every field below is copied from actual retained host metadata. Physical
addresses are reported as identities; the observer never maps or dereferences
those addresses. Missing optional owners are `None`, with explicit state or
completeness; a zero is never substituted for an unavailable owner.

| Domain | Actual source and observations |
| --- | --- |
| Runtime | `smp_service.rs`: exact OS slot/generation, Runtime identity, first Runtime error, metadata/procfs/zero pending counts, completed/rejected/zeroed counters. Counts are sampled in separate short lock scopes. |
| Applications | `smp_application.rs`: all occupied application slots within the explicit cap, application/cleanup tokens, PID, owner slot, prepare/schedule/retirement tokens, retirement delay, scheduled/closed/cleanup/quarantine flags and independent transport errno. |
| RPC/image | `application_rpc.rs`, `smp_application_image.rs`: real exchange token/operation/phase/result/waiter and retirement state; preparation result, thread, page table, retained descriptor/argument/environment BootPages physical identities. `None` means the optional buffer/exchange is actually absent. |
| Procfs | `smp_procfs.rs`: the actual process context token/PID/CPU, live/published/main-seen flags and current TID count. This does not enumerate TID values or read VFS/procfs contents. |
| Mailboxes | `smp_application_syscall.rs`, `application_syscall.rs`: occupied call slots, delivery token and actual phase, request PID/CPU/requester/target/nr/arguments, response identity, copied worker identity, cancellation/kernel/service/transfer flags, completion/response/wake ownership and publication timer; all occupied worker tokens/TIDs/delivery/completed tokens. The release mailbox is a distinct inventory with its real release token. |
| Response claim | `sysfs_memory.rs`: exact OS generation, response ledger slot/serial/span and optional payload ledger serial/span. New `ResponseMemory::verification_owner` defaults to `None`; the actual native adapter overrides it. Generic adapters cannot fabricate native claim evidence. |
| Memory ledger | `sysfs_memory.rs`: each of fixed/request/response/payload/snoop/procfs/zeroing classes, with actual inventory total, emitted count, ledger slot/index, serial where present, physical start/end, and last allocated serial. Fixed regions have no serial and explicitly report `None`. |
| Pager registry | `smp_file_pager.rs`: every occupied handle within the cap, exact `references` field, and readable/optional writable Arc-owned File identity. This is the real guest/server reference count, **not** a Linux `file.f_count` or Arc strong count. In-flight I/O may retain another Arc after a registry entry is removed; total Linux in-flight file ownership is not claimed. |

This inventory covers the native Runtime/application/ledger/pager domains.
It does not replace the separate mcctrl process/MM, CPU/module reservation,
Linux task scheduling, guest response-byte and physical-queue evidence.
The observer does not add Arc clones, file references, ledger tags or packet
ownership, so observation cannot itself explain a retained owner away.

## Early selection and phase wiring

`Runtime::verification_select_read16(pid: Option<i32>)` delegates to the real
Remote/mailbox locks. `Started` exposes the same helper to its parent module.
`Some(pid)` requires that positive PID. `None` requires exactly one eligible
request across the healthy Remote; zero or multiple matches fail with EAGAIN
or EBUSY. A failed/closed/quarantined application is not eligible.

Eligibility requires actual delivery phase `Delivered`, a copied native
worker, no completion yet, no cancellation/kernel service, syscall number 0,
fd argument 0 and length argument 16. The request's response must match the
native owner's exact 40-byte span and real non-missing ledger serial. The
selection stores OS generation, application/worker/delivery tokens, PID/CPU/
requester and original response ledger identity. Selection is one-time per
fresh verification module; it has no reset or reuse operation.

The selector reads host metadata only. `Delivered` proves the successful WAIT
copy transition; it alone does not prove that the Linux worker has entered
its blocking read. The parent must retain actual stdin pipe/task state and
withhold input until the pre-input observation is complete. The old injector
that first selects inside the send callback runs after RET; it cannot provide
this earlier evidence.

The parent calls `Runtime::verification_observe(Phase)` from an **unlocked**
continuing-service boundary, such as a reviewed point in `Runtime::pump`.
The phases are:

| Phase enum | Required external event / oracle |
| --- | --- |
| `BlockedRead` | Selection succeeded, controller has supplied no input, actual read16/task/pipe evidence is retained. Mailbox shows Delivered and a response claim, no accepted completion. |
| `AcceptedReturn` | RET committed its result but selected publication is still held by the parent fault controller. Mailbox shows Returning/completion ownership. Compare bytes with the accepted prefix, not the pre-RET prefix. |
| `Terminal` | The actual fault returned and the terminal transition finished outside publication locks. Capture original Runtime/Remote errors and retained inventories. |
| `TerminalPlusFive` | At least five additional host-monotonic seconds elapsed after the terminal sample, with no reset/retry. Independently sampled owner rows and selected access counters must stabilize as required by the fault oracle. |
| `Recovery` | The actual physical queue recovered, the selected response completed once, and controller/guest exit evidence proves recovery. This enum label alone does not prove success. |
| `AfterEightHello` | Eight subsequent ordinary HELLO launches and their expected cleanup completed in the same recovered OS, proven by the existing guest oracle. Compare the old selected serial's counters and current inventories. |

**Never invoke full observation from `Mailbox::publish`, the send/notify
callback, `finish_publication`, `expire_publications`, or any other function
while holding application/transport/CPU/pager/ledger locks.** Those callbacks
may set a narrow phase flag; the parent must defer full observation until the
call returns and all its guards unwind. Do not call through Started while the
synchronous BOOT resource/context guards are still held. Observation errors
are evidence failures for the controller; do not feed them to `Runtime::fail`
and thereby manufacture the service fault under test.

No phase hook is automatically installed. The parent must bind the marker
phase to the actual event rather than merely call an enum-named function.
The four transport-failure guest gates remain required before case execution.

## Lock, allocation and stack audit

Appendix methods copy metadata into small initialized fixed arrays. They do
not allocate, clone Arc owners, invoke file I/O or print while holding a
production lock. Every print uses the copied local record after release.
Selected-response counter hooks perform only scalar metadata reads and atomics;
they do not print, allocate, sleep or acquire another lock.

The existing order remains application slots -> pager registry -> memory
ledger. Full snapshot emission releases each domain before entering the next;
it does not nest all three. Mailbox capture takes application slots then the
release mailbox when needed, matching the existing release-admission order.
Procfs status copies its TID count under the existing slots -> process-TIDs
order. Pager capture does not dereference its Linux File pointer or clone it.
Ledger capture never enters the application/pager locks. Counter hooks called
inside `SyscallResponse::release` add no lock under the ledger.

There are no arrays sized for the theoretical 4,096 response/pager slots on
the kernel stack. Version 1 limits are:

| Inventory | Maximum emitted live rows |
| --- | ---: |
| Applications | 8 |
| Calls per application or release mailbox | 8 |
| Workers per mailbox | 16 |
| Each of seven ledger classes | 16 |
| Pager handles | 16 |

Sparse production arrays are scanned to count all actual occupied slots
(64 mailbox/application slots or 4,096 response/pager slots). Dense ledger
classes report their true length and copy only the first 16 records. No
dense unbounded vector is traversed just to log a prefix. Exceeding any cap
prints the real total, the emitted count and `complete=false`; the final
marker is `INCOMPLETE_FAIL` and the observer returns an error. No missing
rows are silently treated as absent owners. Raising caps requires a new
version/review and actual stack-frame verification, not a parser exception.

Compile-time size assertions bound the call buffer to 4,096 bytes, workers
to 1,024, applications to 2,048, ledger rows to 1,024, and pager rows to
1,024. Emission helpers use `#[inline(never)]` and receive caller-owned
mailbox buffers by reference to avoid returning large arrays by value.
These are source bounds, **not** measured native stack frames. The parent
must inspect the compiled frame sizes/call chain before loading an overlay
module. The largest source nesting is application inventory -> mailbox
inventory, plus formatting and normal Linux call overhead.

Logging is finite: at most approximately 600 marker/row lines per phase with
these caps. Delivery and call-owner metadata are split into separate records
to stay below the native printk line limit. The parent must verify actual
maximum line lengths, absent truncation/ratelimiting, and complete capture
under its configured output cap. Logging/atomic instrumentation can affect
timing; all guest claims remain bound to this exact verification-only module.

## Snapshot schema and completeness

`STABILITY_OWNER_BEGIN version=1 sequence=N phase=... selection=...` starts
a snapshot. Domain headers give actual total/emitted/completeness and exact
domain keys. Row records repeat version/sequence and stable role/class/
application/ordinal keys. `STABILITY_OWNER_END` closes the snapshot with
`complete`, `counters_valid` and one of `COMPLETE_SNAPSHOT`, `INCOMPLETE_FAIL`,
or `COUNTER_FAIL`. Marker completeness is an observation property, not an
application acceptance result.

The application inventory, each app detail/mailbox, pager registry, each
ledger class, Runtime counters and lifetime counters are explicitly
**independently sampled domains**. An application disappearing between its
inventory and detail sample reports missing detail and fails completeness.
Other changes can be individually valid yet cross-domain inconsistent during
live traffic. Require repeated stable terminal/+5-second inventories and
the actual phase barrier; do not invent an atomic whole-OS snapshot.
`ledger.serial` is the last allocation serial, not a mutation epoch: removing
an entry does not increment it. Compare actual serial-keyed row inventories.

The parent parser must reject unknown/mixed versions, duplicate or missing
begin/end/domain/row records, row-count/ordinal discrepancies, missing selected
native claim metadata, overflow, truncated lines, and any counter failure.
Rows contain only fixed typed fields, numeric values, booleans, `Some`/`None`
and fixed enum labels; no user-provided strings or response contents are
formatted. Preserve raw logs alongside parsed results.

## Original-response lifetime counters and byte oracle

The native adapter's existing `address()` entry point is instrumented before
returning its pointer. Accepted payload copies are counted before their loop.
`release()` is counted after the exact response/payload ledger entries are
removed; the hook reads only the adapter's owned scalar metadata. All counters
match the selected OS generation **and original ledger serial/index/span**.
A later claim at the same physical address has another serial and is ignored.

Counting starts only after the actual Delivered read16 is selected. The
earlier construction-time response address access is outside this epoch.
For the selected ordinary read16, the expected normal progression is:

| Point | Address calls since selection | Release calls | Meaning |
| --- | ---: | ---: | --- |
| Pre-input Delivered | 0 | 0 | Native response retained; no RET prepare. |
| Accepted RET | 1 | 0 | `Response::prepare` legitimately accessed the prefix and wrote stid/result/state. |
| Queue still full / hard prepublication / publication deadline | 1 | 0 | `Completion::publish` did not reach final response access or release. |
| Successful real publication, including later notify failure | 2 | 1 | Final status store and release occurred once; the old response may already be recycled. |
| Terminal+5 / recovery+eight HELLO | Same as applicable prior row | Same | No later old-serial access, replay or duplicate release. |

`after_release_calls` and `duplicate_release` must remain zero. Either makes
`counters_valid=false` / `COUNTER_FAIL`. Counters are independently sampled
atomics; require stable observations after the phase settles.

The accepted RET prefix is different from the pre-RET prefix. The parent H04
fixture initially compared them and correctly failed: `Response::prepare`
writes the servicing TID/result and changes wake state before final status
publication. The independent accepted-prefix correction subsequently passed
the complete 50-test controlled suite. For fault guests preserve a pre-input
prefix, separately verify the exact legitimate accepted transition, then
compare against the accepted prefix for prepublication retention. Never
classify these legitimate writes as post-failure corruption.

The observer itself never reads old response bytes, including after final
publication. These counters cover the reviewed native address/payload/release
access sites; they are not a hardware watchpoint for arbitrary stale raw
pointers. The source audit must remain bound to the exact production bodies
of `Response::prepare`, `Completion::publish` and the native adapter, and the
parent's reused-memory/physical oracle remains independently required. No
new postpublication read is introduced merely to check a canary.

## Preparation and review checks

Example (fresh output name required):

```text
python3 scripts/tests/prepare_stability_owner_observer.py \
  --source host-kernel/native-rust \
  --output /home/holden/mckernel-work/scratch/stability-owner-observer-source-20260913-2
```

Attempt 1 failed closed on the assumed release-method suffix: the actual
source has an ownership comment after payload bookkeeping. That failure's
partial overlay and record are preserved, and the exact command/error is in
`kernel.log`. The corrected anchor names that actual ownership comment.
Fresh attempt 2 is `PREPARED_NOT_COMPILED_NOT_EXECUTED`; every transformed
file reverses byte-for-byte to its captured current original. The generator
rejects already overlaid input, missing/ambiguous anchors and input changes
during generation. Keep both attempts and their exact helpers/records.
Python AST parsing, whitespace checks, rustfmt parsing of every appendix and
all 11 resulting Rust files, and original/overlay/diff hash checks passed.
The ten production source files still equal their captured originals.
The new module SHA-256 in this prepared capture is
`fb0a795209d73262b0415e91b55a9c4e7f9ac357cf255460c16dc84233ad6a31`.

`scripts/tests/fixtures/stability-owner-observer-state.rs` directly includes
the new shared observer module with only a captured logging macro substituted.
Its single bounded test checks inventory overflow without overwriting rows,
immutable original selection, generation/serial isolation, zero initial
counters, legitimate counters, post-release access/duplicate-release failure
and incomplete-snapshot failure. It is prepared, **not compiled/run here**.
It does not model native claims or exercise actual guest memory.

The parent must review the generated diffs, bind the full compiler input set,
run the shared tests and relevant native/control regressions, compile the
overlay in an isolated stage, inspect stack/line bounds, wire the real phase
controller outside locks, and execute all required fresh fault guests. The
unchanged ordinary module baseline remains separate from overlay acceptance.
Prepared code, parser tests and typed counts alone do not close H04 or any
actual transport-failure gate.
