# Source-derived hard-fault physical comparison

This is a source-only oracle for the first `prepublish-hard` profile. The new
`scripts/application-tests/physical_observations.py` performs no physical reads,
starts no guest and grants no acceptance. Its functions consume already retained
bytes. No test or guest result was used to choose the constants below. The first
two guest invocations supplied no eligible fault snapshots when this derivation
was written; parser execution and focused tests remain separate work.

The caller must bind every input to the exact stopped guest, selected OS
generation, original application/worker/delivery/response claim and native phase.
Queue physical addresses and direction come from that generation's accepted
control channel. Each response read requires an unchanged retained response
claim and zero selected publication/release counts. Never read the original
response after publication or release. These conditions cannot be established
by comparing an isolated byte string.

## Response prefix

The host protocol owns a 40-byte prefix, with these little-endian fields:

| Offset | Width | Field | Hard-profile expectation |
| ---: | ---: | --- | --- |
| 0 | 4 | response `ttid` | Preserve the original bytes |
| 4 | 4 | servicing Linux TID | Original selected worker TID after prepare |
| 8 | 8 | status | Zero throughout these snapshots |
| 16 | 8 | requester wake state | BlockedRead 2; prepared/terminal 1 |
| 24 | 8 | signed return value | 16 after prepare |
| 32 | 8 | fault address | Preserve the original bytes |

`executer/include/uprotocol.h` declares this layout; the guest Rust ABI assertions
in `kernel/rust/abi.rs` check these offsets. The configured guest struct also has
`pde_data` at offset 40 and size 48. This comparator neither reads nor verifies
that additional eight-byte field; native `RESPONSE_BYTES` is 40.

The `ttid` comment describes a requester, but it does not establish the current
contents. `kernel/syscall.c:4052` declares an uninitialized stack response.
`syscall_offload_prepare_result` writes request `rtid`/`ttid`, response wake state
and `pde_data`; `syscall_send_prepare_result` writes response status. Neither
initializes response `ttid`, servicing TID, return value or fault address.
`Response::from_memory` validates the mapped address without initializing them.
The parser must not require the response first word to equal the guest requester
or require other initially unspecified fields to be zero.

`host-kernel/native-rust/application_syscall.rs` makes the expected change
independent of captured outcomes: `Response::prepare` writes only servicing TID
at offset 4, value at 24 and the wake-state transition at 16. Starting from the
retained BlockedRead prefix with status/wake `0/2`, the expected prepared prefix
is a copy with exactly those fields set to original worker TID, 16 and 1.
The hard fault returns `-5` from `send(packet)`; `Completion::publish` exits
before status publication, its next address access and response release.
Terminal and TerminalPlusFive must both equal that expected 40-byte string.

`compare_hard_response(blocked, terminal, plus_five, worker_tid=tid)` checks this
comparison and retains each input's bytes, size and SHA-256. The output explicitly
says `accepted_return_physically_observed=false`: deriving the expected prepared
prefix does not fabricate a physical AcceptedReturn capture. Native timestamps
must independently prove the five-second interval.

## Original request in the receive ring

The original request travels in message 4 on host receive port 503. The native
decoder in `application_syscall.rs` supplies the offsets:

| Packet offset | Width | Field |
| ---: | ---: | --- |
| 8 | 4 | message = 4 |
| 24 | 4 | guest CPU |
| 32 | 4 | application PID |
| 48 | 4 | requester guest TID |
| 52 | 4 | target TID |
| 56 | 8 | valid = 1 |
| 64 | 8 | syscall number = 0 |
| 72 | 48 | all six immutable arguments; fd 0 and length 16 |
| 120 | 8 | original response physical address |

The current guest Rust sender zeroes the full packet and copies the request,
then marks the packet copy valid and publishes it. The comparator binds the
listed fields and all six arguments to the independently parsed original
owner Request. It preserves the full packet but does not invent requirements
for padding, an unused union field, or a channel pointer.

The fixed queue is 16,384 bytes: a 64-byte header, 127 slots of 128 bytes and
64 unused trailing bytes. Native ABI assertions place read, published and
reserved counters at 16, 24 and 32, and queue payload size 16,256 at 40.
This fresh-run profile rejects counter wrap or counter saturation and requires
`read <= published <= reserved`, with `reserved - read <= 126`.
The distance 126 is a legal physically full ring and is accepted; this geometry
check neither requires nor rejects physical fullness.

Sequence `s` occupies offset `64 + (s % 127) * 128`. A consumer copies before
incrementing read. A producer reserves before writing and can overwrite `s`
only when it reserves `s + 127`; therefore only sequences
`max(0, reserved - 127) <= s < read` are provably retained consumed packets.
Arbitrary slot scans can find stale or unpublished bytes and are insufficient.
`locate_consumed_request(receive, request)` requires exactly one matching
retained consumed request. Missing/overwritten and duplicate matches fail closed.
The `request` dictionary contains exactly `cpu`, `pid`, `requester`, `target`,
`number`, `response` and `arguments`; these come from the original owner parser,
not an expected-value dictionary reconstructed from the ring candidate.

## Absence of a new selected wake

`Runtime::publish_syscalls` uses host send port 501 for the selected guest CPU.
`Request::wake` emits message `0x14` with the guest requester in the union's TID
field at offset 24. This differs from both the original request target at 52
and the uninitialized response first word. Native `OutboundQueue::send` passes
the packet directly to the shared-ring producer.

`no_new_requester_wake(before, after, requester)` checks every newly published
sequence from the earlier published counter through the later published counter,
excluding the latter endpoint. Metadata must be unchanged and all counters must
be monotonic. The entire interval must remain in the later ring's retention
window; an overwritten interval yields an explicit error, not proof of absence.
A packet with message `0x14` and matching requester fails this hard-fault check.
Apply it to BlockedRead-to-Terminal and Terminal-to-TerminalPlusFive snapshots,
with independent source/channel/physical-address bindings.

This proves only the bounded captured-byte comparisons. It does not prove a
physical full ring, missing notification interrupts, a safe post-release read,
payload output, actual RET duration, native owner stability, launcher cleanup,
UART acknowledgment, QMP resume, or whole-OS acceptance. Those gates retain their
separate source and runtime evidence.
