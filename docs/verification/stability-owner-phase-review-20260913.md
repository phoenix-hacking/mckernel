# Verification-only native phase control — 2026-09-13

Status: **SOURCE PREPARED; FIRST COMPOSED MODULE BUILD PASSES; GUEST GATES OPEN.**
Root owns composition with the fault/RET hooks, isolated builds and all actual
guests. The first actual integrated prepublish-hard module record is
`/work/stability-transport-fault-module-20260913-prepublish-hard-1/record.json`,
status `PASS_BUILD_ONLY`, SHA-256
`b6f9396102ff847f1572aac30a452ff6667ae982b866ca51d1e2cb6baa80dffd`.
Its actual fault/observer guest and stack-frame verification fields remain
false; shared production source and object restoration is true. This review
lane ran no compiler or guest. Build success grants no transport, application
or whole-OS acceptance.

The new inputs are `scripts/tests/fixtures/stability-owner-phase/*.rs` and
`scripts/tests/prepare_stability_owner_phase.py`. The full source-only output
is `/work/stability-owner-phase-source-20260913-2`, using the frozen observer
prototype's `/work/stability-owner-observer-module-20260913-1/staged-source`.
On the host, `/work` maps to `/home/holden/mckernel-work/scratch`.
The earlier source-only attempt 1 remains preserved; the newer attempt adds
root's fault-counter call, captures original source bytes once before decoding,
and prevents a later diagnostic failure from rearming a released barrier.
Neither attempt is a compiler or guest run.

## Minimal entry point and lifetime

The existing SMP miscdevice is `/dev/mcd0`, registered at
`host-kernel/native-rust/ihk_smp_x86_64.rs:830`. Its native ioctl callback at
`:503` has a live Linux file/module pin and `ProviderOpenLease`; no production
lock spans entry. The overlay adds one command before ordinary dispatch and
an explicit compat rejection. It changes no ordinary command, exported symbol,
IHK/mcctrl application ABI or production file.

`smp_memory::verification_phase_ioctl` copies one fixed 256-byte input before
any lock. Under the existing PUBLISHED memory-context mutex it bounds-checks
the slot, checks the actual stored image owner against the requested generation,
requires a started boot with a retained continuing service, and clones Started.
It then drops that mutex before any selection or full snapshot. It does not
construct an OsToken from user values or call `require_ready`, which would
exclude the failed Runtime whose retained owners must be observed.

Started's temporary Arc owners retain the actual Runtime and its service
threads through the synchronous call. No application, Mirror, file pager or
response owner is added to obtain access. In particular, the selected old
application need not survive to make the final AfterEightHello observation.
The active module/file and boot-owner lifetime are the same retained objects
used by `smp_memory.rs:2379`; the scalar slot/generation is only a checked
selector, not a lifetime proof supplied by userspace.

A separate atomic Permit serializes verification requests and snapshots. It
is never acquired by the send or accepted callback. It does not lock the OS
state and cannot make independently sampled inventories atomic. The ioctl
releases it after constructing the local reply and before user copyout; no
production or verification guard spans that potentially faulting copyout.
No new shutdown, reclamation or module-unload behavior is introduced.

## Exact local command ABI

Command `0xc100f501`, version 1, exactly 256 bytes, native x86_64 only. All
integer fields are little endian. The client starts from a zeroed buffer.
This is a private verification-module command, absent from production UAPI.

| Offset | Width | Input |
| ---: | ---: | --- |
| 0 | u32 | Version 1. |
| 4 | u32 | Phase command below. |
| 8 | u32 | Expected OS slot, less than 64. |
| 12 | i32 | Expected PID; only initial selection permits 0 for a unique eligible read across applications. Later requests require the actual selected positive PID. |
| 16 | u64 | Expected nonzero OS generation, obtained from the actual retained boot identity. |
| 24 | u64 | Request sequence; initially 1, then exactly previous consumed sequence + 1. |
| 32, 40 | two u64 | Run nonce, at least one nonzero word; bind the real frozen controller attempt nonce. Subsequent requests must match. |
| 48, 56 | two u64 | Original selected delivery and response-ledger serial; both 0 for initial selection, exact returned values thereafter. |
| 64–255 | 192 bytes | Must all be zero on input; output region. |

| Offset | Width | Output |
| ---: | ---: | --- |
| 64 | u64 | Phase-wrapper snapshot sequence on successful observation; 0 for query or a failed command. |
| 72 | i64 | Actual executed phase-command errno, or 0. |
| 80, 88, 96 | three u64 | Actual original application token, worker token and delivery. |
| 104, 112 | two u64 | Original response-ledger serial and index. |
| 120, 128 | two u64 | Original response physical start/end. These are identities, not authorization to dereference released memory. |
| 136, 140, 144, 148 | i32, i32, i32, u32 | Actual selected PID, CPU, requester and OS slot. |
| 152 | u64 | Actual selected OS generation. |
| 160 | u64 | Barrier stage: 0 unconfigured, 1 armed, 2 accepted pending, 3 released. |
| 168 | u64 | Successful AcceptedReturn phase-wrapper sequence. |
| 176 | u64 | First successful Terminal snapshot completion's Linux monotonic nanoseconds. |
| 184 | i64 | First latched verification-invalid errno. |
| 192 | u64 | Explicit barrier-only send attempts; never physical-full/fault-mode attempts. |
| 200 | u64 | Last consumed command sequence. |
| 208–255 | 48 bytes | Remains zero. |

Validation, absent/stale owner and busy-Permit failures before dispatch do not
consume the sequence or copy a response. A phase that was dispatched consumes
its request sequence and copies the response even when it returns a negative
phase errno. The client must inspect offset 200 to distinguish those outcomes;
it must not blindly retry a consumed sequence. A copyout failure cannot undo
an emitted snapshot or immutable selection. Preserve the kernel markers and
original failed attempt instead of silently replaying that action.

| Command | Meaning and prerequisites |
| ---: | --- |
| 1 | Select the unique actual healthy Delivered `read(0, buffer, 16)` and emit BlockedRead. Returns its full immutable native identity. The original controller must still prove the Linux worker is blocked and withhold all 16 input bytes until PRE_INPUT capture/ACK. |
| 2 | Emit Terminal only when the actual Runtime and Remote both have terminal errors. No readiness check. Record the first successful snapshot completion time. |
| 3 | Emit TerminalPlusFive with the same actual terminal checks and at least five additional Linux monotonic seconds after that recorded completion. Host-monotonic timing and the controller's QUIET interval remain independently required. |
| 4 | Emit Recovery only after the barrier was released, Runtime/Remote are healthy, the original application is absent and the application inventory is empty. This is a state prerequisite, not proof of normal cleanup or response release. |
| 5 | Emit AfterEightHello only after a successful Recovery observation and the same healthy empty-application conditions. The real eight HELLO launches, their exact outputs/cleanup and same-OS provenance must already be retained externally. The enum label does not count launches. |
| 6 | Query the immutable key, barrier/counter/error/sequence metadata without a full snapshot. This remains available when verification is invalid. |

## AcceptedReturn scheduling and race closure

Root composes three source-bound parts around the existing production methods:

1. Immediately after successful `Completion::prepare` in the selected ordinary
   `Mailbox::return_value` arm (`smp_application_syscall.rs:505`), match the
   actual request/delivery and native completion claim, then call
   `crate::stability_phase::accepted_selected()`. This does only scalar atomics
   under the existing slots lock. It changes armed to accepted-pending once;
   duplicate or impossible transitions latch a verification error.
2. Inside the exact selected completion's send wrapper, before incrementing
   any actual fault-attempt counter, call
   `crate::stability_phase::before_selected_send() -> Result<(), i32>`.
   Until the barrier releases, it returns an explicitly accounted `-11`.
   An already released barrier always permits the real callback, even if a
   later diagnostic cap marks verification invalid. Diagnostic failure must
   not manufacture new production backpressure.
3. At the end of `Runtime::pump`, after all seven service operations have
   returned and their guards unwound, call `verification_accepted_phase()`.
   Only the Runtime matching the immutable selected OS/generation may claim
   this work. It copies the selected call's actual Returning/completion/claim
   state under slots, then drops slots and emits the full AcceptedReturn
   inventory. A complete successful observation releases the barrier
   automatically. No new UART phase or controller ACK is required here.

The exact accepted-call check requires the original PID/CPU/requester,
worker/delivery, read16 arguments, physical response, OS generation and ledger
serial/index/span. It requires an owned completion response and wake, no raw
response remaining in the call, no cancellation, and no kernel/service flag.
This matches the selected real read16's independently checked wake state 2;
the initial selector alone does not establish that response-byte condition.

If a pump passed its earlier checks before RET committed, the send barrier
still returns `-11`; the end-pump observation then finds the actual accepted
completion. No callback logs a full inventory, allocates or waits while
holding slots/transport/CPU guards. Other OS workers return before acquiring
the verification Permit or touching the selected phase state.

An AcceptedReturn observation error latches verification-invalid and leaves
the barrier pending. It never calls Runtime::fail or Remote::fail_transport.
The existing five-second publication clock continues from the production
`application.advance`/`publication_since` epoch with its actual second
granularity. It is not reset, paused or extended. A slow or incomplete
observer can therefore invalidate the run; an ensuing production deadline is
not credited as the intended fault. The host retains failure evidence and
uses a fresh attempt. Root's recoverable two-second mode must account for the
time already consumed by this barrier before making any recovery claim.

## Snapshot correlation and unchanged observer

Each observation has `STABILITY_PHASE_SNAPSHOT_BEGIN/END`, version 1, its own
monotonic phase sequence, run nonce and Linux monotonic nanoseconds. Inside
that interval is exactly one existing `STABILITY_OWNER_BEGIN/END` snapshot,
followed by the root-owned `STABILITY_FAULT_COUNTS` from
`stability_fault_observe()`, then the phase END. The fault-counter call runs
outside all production guards even if the owner observer returned an error.
The phase and owner sequence namespaces are distinct; the parser binds them
by the exact nesting and identity, not numerical equality.

The shared `stability_observer.rs` remains byte-for-byte unchanged. The Permit
serializes these entry points so their envelopes cannot interleave; root must
not install an additional unsynchronized direct observer caller. Require
complete versioned envelopes, one matching owner snapshot, actual owner row
counts, original serial counters, fault counts and correct monotonic ordering.
Live domains remain independently sampled. Terminal/+5 owner stability and
external physical queue/MM/task evidence are still necessary.

For prepublication failure and permanent pressure, POST_RET QMP can inspect
the retained accepted prefix. In notification failure the response may already
have been consumed/reused: never read its old bytes after publication. The
typed AcceptedReturn inventory, actual RET entry/exit, real publication and
original serial's lifetime counters establish the intervening transitions.

## Exact stage recipe and validation remaining

Run the source-only helper on a complete flat native source stage that already
contains the reviewed typed observer:

```text
python3 -B scripts/tests/prepare_stability_owner_phase.py --source FULL_OBSERVER_STAGE --output FRESH_PHASE_OUTPUT
```

It captures each input's bytes once, stores those exact originals, derives
the overlay from that same byte string, verifies inverse restoration and
rechecks source identity afterward. It appends four method files, adds the
new module, and installs native/compat dispatch plus the end-pump call through
unique anchors. The source output is partial: compose its five replaced native
files and new module over the full original observer stage, retaining all other
source files. Root then applies its accepted/send/notify/RET overlay and actual
physical-ring control. Do not replace production files or build the partial
directory by itself.

The complete source output's `record.json` binds originals, overlays, diffs,
helper and appendix copies. The code freeze is:

| Input | SHA-256 |
| --- | --- |
| `prepare_stability_owner_phase.py` | `08f122921f8c496e7b6a67d3175294f7e4d5edd924bf80422418e9a4aade3041` |
| `stability_phase.rs` | `5ce35193f9d88d7b990b92cc90287437ffe9c2e6b3f409ddfa2190b1ebfb9e54` |
| `smp_service.append.rs` | `27ccee5815ccdd09c128803483fa488061d50721ff35f51e67363164379e5579` |

Python AST/whitespace, Rust source parsing/formatting and source-only staging
passed. Independent review found and corrected the other-OS pump race before
freeze, and confirmed no production guard spans full observation or user
copyout. No compiler, fixture executable, container or guest ran in this lane.

Required next checks are the actual composed native compiler/lint/stack-frame
and no-FP checks, then exact-method tests for malformed/version/compat/stale
requests, nonzero output bytes, slot bounds, nonce/delivery/ledger binding,
consumed versus unconsumed failures, duplicate acceptance, other-OS pumps,
barrier-only EAGAIN accounting, accepted snapshot failure, later diagnostic
failure after release, and at-least-five-second phase timing. Source tests
must exercise the real production mailbox/phase methods with independent
expected states; a matching mock cannot establish release or fault behavior.
Finally run the unchanged controller infrastructure tests and actual four
fault guests with retained QMP/task/queue/owner evidence. A label, ioctl 0,
module build or snapshot-completeness marker alone closes none of those gates.
