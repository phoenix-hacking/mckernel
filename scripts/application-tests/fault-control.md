# STF1 host UART coordinator

`fault_control.py` collects the unchanged controller's STF1 control protocol.
Source and synthetic tests are prepared; the author has not run these tests.
It creates no socket, process, guest, QMP client or payload. The parent owns the
connected control socket, actual controller exit, all QMP operations, physical
and typed owner evidence, and an independent outer watchdog.

```python
coordinator = FaultControl(
    connected_socket,
    nonce=nonce32,
    mode="prepublish-hard",
    capture_root=fresh_absolute_host_directory,
    capture_phase=capture_phase,
)
try:
    # Parent serializes this with its other QMP and guest-exit work.
    event = coordinator.poll(wait_seconds=0.1)
    state = coordinator.report()
finally:
    coordinator.close()  # Retains final report; socket stays caller-owned.
```

`poll` processes at most one complete frame and returns an event or `None`.
Its wait may be zero through one second. Continue polling after normal phase
completion until the parent observes actual controller exit: cleanup and
admission can still produce a later FAIL. Neither an ACK nor completed normal
phases establishes controller success, normal McKernel cleanup or acceptance.

The callback receives a fresh plain dict with `kind`, `nonce`, `sequence`,
`phase`, `mode`, `tgid`, `tid`, `start_ticks`, and `ack_phase`. FAIL additionally
has the actual wire `reason` and `errno`; its acknowledgment phase is
`EMERGENCY_CAPTURED`. Changing the callback argument cannot change the parsed
request used for ACK. Return a plain JSON-compatible dict containing a
lowercase 64-character `sha256` and literal `continued: True` only after the
actual capture is retained and checked, QMP is continued, and running is
verified. That hash is the caller's capture-manifest assertion; the coordinator
does not invent or independently verify physical or process provenance.

The callback runs synchronously on the parent's serialized event-loop thread.
This component cannot preempt a stalled callback or local filesystem call.
The independent parent watchdog remains mandatory. A callback observed after
its deadline never receives ACK, even if it returns otherwise valid metadata.
Normal callbacks must enforce their real phase prerequisites; an emergency
callback may retain failed observations, but must still complete its capture
and verified continuation before acknowledging. Emergency collection never
clears the original failure.

The first request must be exact PRE_INPUT sequence 1 and binds positive
launcher TGID, Linux worker TID and start ticks. Subsequent identities, nonce
and mode must match. Normal phases are PRE_INPUT, POST_RET and QUIET for
terminal modes, or PRE_INPUT and POST_RET for recoverable backpressure. Every
received accepted request consumes the next sequence, even when its callback
fails and no ACK is sent. Exact byte framing requires single spaces and LF;
CR, NUL, malformed decimal values, wrong version, stale sequence, unsupported
phase, changed identity, overlong frames and queued repeated frames fail
closed. A duplicate arriving during capture is retained and rejected before
ACK. Peer EOF before ACK also fails, including a half-closed socket.
An interrupted pre-ACK peek retries within the same deadline; it cannot be
treated as evidence that no duplicate or EOF is waiting.

On a callback failure, invalid return or unconfirmed continuation, the first
failure is latched and no normal ACK is sent. The coordinator continues to
wait for the guest's explicit next FAIL for that same pending phase. It then
calls the emergency capture callback and sends only the exact
EMERGENCY_CAPTURED ACK after confirmation. Other post-input FAIL phases are
limited to the controller's actual current execution stages: input, RET/owner
observation, quiet interval, normal completion, cleanup or admission. Only one
emergency request is allowed. A failure before the first input release cannot
qualify as the controller's post-input emergency protocol. In particular, a
rejected PRE_INPUT callback may end in controller exit without any FAIL frame;
the parent must observe that exit and retain its own failed attempt.

Malformed/stale framing, channel failure or an expired coordination deadline
raises `FaultControlError` after retaining available evidence. The parent must
perform its independent first-failure emergency capture; the coordinator does
not attempt to recover protocol synchronization or send a guessed ACK. Other
local failures also withhold further ACKs and propagate for parent retention.

The default total bound is 180 seconds, configurable up to 300 seconds. A
partial frame has five seconds by default, at most 15. A callback plus its ACK
has eight seconds by default, at most 10. All numeric options reject booleans,
nonfinite values and invalid ranges. Frames are at most 512 bytes including
LF. Raw RX and TX each have a 16-KiB cap; event records have a 1-MiB cap.
Callback metadata has a 16-KiB encoded cap, eight nesting levels, 256 total
nodes, at most 64 members per container and 4096 characters per string.
These checks precede unbounded serialization of callback data.

Fresh host capture directories retain `rx.bin`, `tx.bin`, `events.jsonl` and
final `report.json`. Events identify parsed requests, callback calls and
returns, rejected callbacks, exact ACK sequence/hash, and the original failure.
Raw byte hashes/counts advance for each successful artifact write; separate
socket receive/send counters expose incomplete local retention. UART overflow
is an explicit failure with discarded-byte accounting. Final report close
fsyncs its own files and directory; this is not a durable-artifact-transfer ACK
or a claim about ancestor-directory persistence. The capture callback owns the
durability obligations of the manifest it confirms.

Root should run the retained synthetic socketpair suite through its existing
pinned container and supervisor:

```text
python3 -B scripts/tests/test_application_fault_control.py -f
```

Every synthetic attempt is retained under TMPDIR and its path is printed;
there is no automatic cleanup, source/controller mutation or application
execution. The tests exercise literal complete ACK bytes, callback-before-ACK
ordering, normal and emergency flows, first-failure preservation, invalid
identity/sequence/phase/framing, queued duplicates, actual partial-frame and
callback deadlines, false continuation, malformed metadata, peer EOF and byte
caps. They do not prove QMP or guest behavior. Preserve the complete first
unexpected failure before any correction or retry. All reports explicitly
leave application, transport, controller-exit and QMP-provenance acceptance
false or unverified.
