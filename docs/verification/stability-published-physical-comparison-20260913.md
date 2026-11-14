# Published-fault retained physical comparison, version 1

This additive helper compares supplied bytes for postpublication-notify and
recoverable-backpressure runs. It never reads memory, contacts QMP, executes a
guest, enables an application backend, or grants transport/application acceptance.
Every successful result is `PHYSICAL_BYTES_MATCH_ONLY`; the phase names describe
the caller's claims until the separate source/owner/capture joins validate them.
The original hard-fault comparator and its tests remain unchanged.

`scripts/application-tests/published_physical_observations.py` loads the exact
sibling `physical_observations.py` using an explicit file path. The caller must
retain and bind both files before import. Queue geometry, input byte type/size,
counter validity and retained-byte encoding come from that frozen base helper.
The new helper independently specifies the prepared-response and positive-wake
expectations below; it does not import the native implementation's constants.

## Source-derived contract

The current native `application_syscall.rs` defines the wake message as `0x14`
at line16. `Request::wake()` at lines148–154 builds a 128-byte packet, writes the
message at bytes8–11 and the original requesting TID at bytes24–27. That offset
is the wake union member, not traditional.pid at32 or request.target at52.
The native x86_64 ABI independently declares the packet header, union and layout
assertions in `host-kernel/native-rust/abi/x86_64.rs` at lines287–334 and491–492.

`Response::prepare()` at `application_syscall.rs:398–430` requires status0 and
wake0 or2; this reviewed read16 profile specifically requires wake2. It writes
the actual Linux worker TID to bytes4–7, writes result16 to bytes24–31, and claims
wake2→1 at bytes16–23. It preserves bytes0–3 (the opaque response.ttid), status
bytes8–15, and the tail bytes32–39. The response's first word is not initialized
from a field comment or from the requester's TID.

`Completion::publish()` at lines438–464 sends the pending wake before the final
status1 store and releases the response immediately afterward. Consequently the
new API accepts only BlockedRead and the actually captured, retained
AcceptedReturn prefix. There is no Terminal/Recovery response-read operation.
The separate host capture code must forbid further selected-response reads as
soon as release becomes possible, including ambiguous/partial ACK or ioctl
submission; that prohibition cannot be proved by a byte comparator.

## APIs and composition

`compare_prepared_response(blocked, accepted, *, worker_tid)` accepts two exact
immutable 40-byte values and a plain positive signed32 worker TID. It requires
BlockedRead status0/wake2, constructs the three allowed writes above, then
compares every byte of AcceptedReturn. Its result retains both complete input
values with size/SHA256/base64, the expected prefix, allowed spans and worker.
No later phase's possibly released response may be supplied as AcceptedReturn.

`one_new_requester_wake(before, after, requester)` accepts complete immutable
16-KiB native port501 queues and a plain positive signed32 requester TID. It
requires identical non-counter header metadata and nondecreasing read,
published and reserved counters. It scans every logical sequence from the
first snapshot's published counter (inclusive) to the last snapshot's published
counter (exclusive), using physical slot `sequence % 127`. The complete interval
must still be retained according to the last **reserved** counter; a reservation
can invalidate a prior slot before the replacement is published. An overwritten
interval is rejected even if one visible matching wake remains. Exactly one
packet with signed32 message0x14 at8 and requester at24 must appear. Already
consumed publications count; unpublished reservations, older slots and other
requesters do not. A second selected wake fails, including across slot wrap.
The result retains both whole queues, interval boundaries and the matching
packet's complete bytes, sequence, slot and offset. This proves the selected
message count only; it does not claim full-ring equivalence or that every
nonselected message is correct.

The runner must separately compose all of the following:

1. Base `locate_consumed_request` joins the original retained port503 request's
   CPU, PID, requester, target, read number/arguments and response physical span.
2. Base `no_new_requester_wake` proves zero selected wakes BlockedRead→AcceptedReturn.
3. The new response comparator proves the exact prepared prefix before release.
4. The new positive-wake comparator proves exactly one selected wake over
   BlockedRead→Terminal/Recovery using complete port501 intervals.
5. Base `no_new_requester_wake` proves zero additional selected wakes through the
   following quiet interval. The native phase identity and actual elapsed time
   are external evidence, not queue fields.

The runner also joins the exact source/image/modules, physical queue addresses,
OS/generation, original selected owner/worker/delivery/ledger identity, complete
typed owner snapshots, real RET result/timing, stopped capture and verified
resume, controller and launcher evidence. Source-derived lifetime counters and
all mode-specific normal-control assertions remain separate obligations. These
APIs cannot infer those facts from labels or input hashes.

## Literal regression fixtures, source-only freeze

`scripts/tests/test_published_physical_observations.py` has18 test methods. It
copies its own source and both comparator sources into a fresh `TMPDIR` evidence
directory, then imports those retained sibling files. Every invocation retains
all input bytes/types, expected return/error, complete returned metadata or
exception traceback. Failures and passed attempts remain on disk.

The fixtures independently transcribe literal wire bytes. Worker421 and
requester307 differ; the blocked response has nonzero opaque first-word/tail
bytes and a deliberately different old result. Tests cover every forbidden and
required prepared byte, strict types/lengths/identity bounds, first/middle/last
wake positions, consumed versus pending publications, physical slot wrap,
wrong union offsets, old/unpublished/other-requester packets, zero/duplicate
matches, the127-entry retention boundary, prepublication reserved overwrite,
counter/geometry/identity failures, and quiet-interval duplicate rejection. A
composition test checks zero/one/zero counts while retaining false acceptance.

The parent may run the frozen test script with its pinned Python and external
supervisor, `-f` for first failure, timeout10s, cleanup15s, bounded stdout/stderr,
and a fresh retained `TMPDIR`. Actual raw wait, exact selected source bytes,
complete output/evidence and owned cleanup must be inspected. At this source
freeze no subject imports, test execution, physical capture or guest run have
been performed by the author. Passing these synthetic byte tests would be
infrastructure evidence only.
