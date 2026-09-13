# Native owner phase controller overlay, version 1

Source prepared only. Compilation and runtime validation of this overlay are
NOT_RUN. Successful collection, a successful ioctl, or a phase label never
means application, transport or OS acceptance. The unchanged base controller
and its protocol infrastructure runs remain separate evidence.

`controller.original.c` preserves the exact base controller SHA-256
`be5c32e9298d9d1d8711c0ebfd89d2d9f7bc7b0215f8e897da2db5089fdc99eb`.
`controller.forward.patch` and `controller.inverse.patch` retain the complete
versioned change. `controller.c` adds only the native observation client and
the explicit owner guest flow; original `--guest` and `--linux-reference`
arguments retain their original behavior. Original fixtures remain unchanged.

The private ABI authority is
`docs/verification/stability-owner-phase-review-20260913.md` and its reviewed
`scripts/tests/fixtures/stability-owner-phase/stability_phase.rs`. The client
uses the actual `/dev/mcd0` ioctl command `0xc100f501`, with precisely 256
little-endian request/response bytes. It does not invent owner generations,
derive application tokens from Linux TIDs, or call a production failure path
to manufacture an observable terminal state.

The exact new CLI is:

```text
controller --owner-guest MODE NONCE ATTEMPT_DIR MCEEXEC PAYLOAD OS GENERATION
```

All paths are absolute, the attempt directory must be fresh, and the controller
still launches unchanged `MCEEXEC -t 1 0 PAYLOAD`. The guest initializer must
provide the actual OS slot and generation from this boot's retained native
records. NONCE is a nonzero 32-character lowercase hexadecimal string. Its
first 16 characters are the low nonce word; each word is encoded little-endian
in the binary ABI, matching the source observer's two printed words.

The controller first discovers the real Linux worker blocked on read(fd0,16).
SELECT_BLOCKED uses the actual launcher TGID as the request PID and binds the
returned application/worker/delivery/ledger/response/OS identity. The selected
worker token remains distinct from the sampled Linux worker TID. It retains
the native response before issuing the unchanged PRE_INPUT UART request. The
host must validate the typed BlockedRead snapshot, exact selected key, real
mailbox contents and physical response bytes, then QMP-continue and verify
running before sending the original exact nonce/sequence/phase/identity ACK.
The controller writes its 16 bytes a5 only after that ACK and a new actual
Linux blocked-read/start-tick check.

The module independently emits AcceptedReturn before releasing its selected
publication barrier; the controller cannot substitute an ACK for that record.
For terminal modes, the controller requires the real Terminal phase ioctl to
complete before POST_RET, and TerminalPlusFive before QUIET. Existing
five-second quiet waiting begins after the POST_RET ACK; the native ioctl also
requires five seconds after its actual successful Terminal transition. The
host must compare the accepted prefix and immutable selection, exact per-mode
publication/lifetime counters, ownership inventory and actual source-observed
RET errno. Linux proc sampling remains explicitly incomplete evidence of a
fast RET return. Exact RET errno and terminal semantics are external evidence.

For recoverable backpressure, the controller requires natural launcher exit
37, both stream EOFs, exact `NATIVE_FAILURE_READY\nNATIVE_FAILURE_PASS\n`
stdout and empty stderr within the original 15-second input deadline, using
waitid(WNOWAIT) before any cleanup signal. It then asks for Recovery, which
independently requires the original McKernel application to be gone and the
native runtime to remain healthy. Only then does it request POST_RET capture.
It retains `owner-recovery-response.bin` for the subsequent client. The normal
cleanup raw wait still must prove the natural exit; signalling cannot qualify
Recovery. Actual payload identity remains bound by the guest runtime evidence.

Each ioctl runs in a direct controller-owned child, holding the actual launcher
identity as request data. The miscdevice ABI validates that explicit identity;
the issuer is not labelled as the launcher. The parent concurrently pumps the
actual controller streams/UART while waiting and records the child's actual
raw wait. One probe has five seconds, followed by at most 15 seconds of cleanup
if needed. An unreaped direct child cannot have its PID reused. Cleanup failure
is explicit, and subsequent controller-owned cleanup still covers its actual
children. The external QEMU watchdog remains mandatory.

Each call retains its exact request, response (empty if none), complete or
partial raw probe message, and result JSON including real open/ioctl errno,
raw wait, sequence consumption and monotonic observation time. The raw probe
message is a source/architecture-bound C observation structure, not a portable
wire ABI. The binary request/reply pair is the specified portable ABI.
All files are created exclusively. No retry or failed observation is omitted.

Dispatched EAGAIN consumes its request sequence: the client requires offset
200 to prove that consumption and advances the next request accordingly.
Only actual ioctl EAGAIN with a completely untouched output region permits an
unconsumed busy-Permit retry. Other parse, stale-owner, copyout or inconsistent
response errors fail collection. There is no blind retry after ambiguous
copyout, and a successful late observation fails its deadline. Each phase has
at most 10 seconds within the original 90-second controller bound. Polls are
250 ms apart and the entire controller has at most 48 probe attempts. This
caps four files per probe plus other controller artifacts below 256 entries
and below the host exporter's 16-MiB bound. Reaching the attempt budget fails
collection, even when the peer or module might later recover.

Any post-input phase failure goes through the existing first-failure latch and
30-second emergency UART capture window before owned launcher cleanup. It
preserves the current live owner while awaiting the exact EMERGENCY_CAPTURED
ACK. First-failure reason, phase and timestamp remain unchanged. This ordering,
the extra bounded probe cleanup and ordinary controller/admission cleanup fit
within the root runner's 300-second guest contract; its independent watchdog
and first-failure stopped-machine capture remain required.

After the actual eight HELLO launches in the same healthy OS, root invokes:

```text
after-hello --after-eight-hello OS GENERATION NONCE RECOVERY_RESPONSE_ABS FRESH_ATTEMPT_ABS
```

The recovery input must be an exact regular nonsymlink 256-byte prior Recovery
reply. The client retains those bytes and actual file stat identity, checking
device/inode/size/mtime/ctime consistency across the read. It validates the
original nonce/OS/generation/key and consumed sequence, then requests
AfterEightHello with the same identity and next sequence. A fresh attempt
directory holds every raw call. The client has a 10-second phase bound, the
same per-probe/cleanup and artifact limits, and reports collection only. The
phase enum and this helper do not count HELLO launches: the host must retain
the eight real invocations, exact outputs/raw exits, same-OS provenance, typed
AfterEightHello inventory and physical captures separately.

Root must compile these C sources using the original pinned compiler/container
wrapper and reviewed public ABI include path, retaining full command lines,
dependencies, diagnostics, objects, ELF and disassembly. No local host compiler
or guest invocation was performed while preparing this source. Required next
checks include compilation, source-bound client malformed-reply and sequence
negative checks, and complete real guest/UART/QMP ordering with original
first-failure preservation. No broader runtime gate is promoted by this file.
