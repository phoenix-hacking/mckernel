# Transport fault controller source review, 2026-09-13

Status: source prepared; compilation NOT_RUN; controller tests NOT_RUN; Linux
reference NOT_RUN; all four fault guests NOT_RUN. This is an author review of
new collection infrastructure. It does not accept a transport fault, an
application case, a retained owner census, or the OS.

The implementation is
`scripts/tests/fixtures/stability-transport-fault/controller.c`. The adjacent
`payload.c` is an exact copy of the original
`scripts/tests/fixtures/native-application-failure.c`; both have SHA-256
`1cb799c6b994250dad9d367bd33b629a095b78d220df5a683f1da607bbfb971b`.
The original source, including its historical kill-controller comment, remains
unchanged. The payload writes the exact readiness line, performs the actual
libc read of 16 bytes into the middle of a 32-byte guarded buffer, checks all
bytes, writes its success line, and exits 37. No replacement launcher or
synthetic returned-result payload is introduced.

The original author freeze preceding the emergency-ordering correction is
preserved with its controller, payload, review document and SHA-256 manifest in
`/tmp/stability-transport-controller-original-k_fvbazz`. The original controller
hash was `6b38229433376ddc4e065c98889e4138fb9c55ba919488b371055b2625e38df3`.
Root must retain that capture with the checkpoint evidence. No failed compiler
or runtime attempt preceded this source correction; those stages remain NOT_RUN.

The controller includes the real `executer/include/uprotocol.h` for WAIT, RET,
and CREATE_PPD. That header's reviewed identity is
`1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69`.
The later build must retain its actual include dependency and identity. It
must reject source drift instead of silently substituting ioctl constants.

## Invocation and execution record

The two exact interfaces are:

```text
controller --guest MODE NONCE ATTEMPT_DIR MCEEXEC PAYLOAD
controller --linux-reference NONCE ATTEMPT_DIR PAYLOAD
```

MODE is one of `prepublish-hard`, `postpublish-notify`,
`recoverable-backpressure`, or `permanent-backpressure`. NONCE is exactly
32 lowercase hexadecimal characters, freshly generated and retained by the
host runner for this attempt. ATTEMPT_DIR must be a fresh absolute path;
MCEEXEC and PAYLOAD must be absolute paths. Reusing an existing directory
fails before execution. The runner prepares `/case/work` in the disposable
guest and the dedicated second UART before starting the controller.

The guest child receives literal argv `[MCEEXEC, "-t", "1", "0", PAYLOAD]`.
The reference child receives `[PAYLOAD]`. Both use `execve`, cwd `/case/work`,
umask 0022, and exactly `LANG=C`, `LC_ALL=C`, `TZ=UTC`,
`PATH=/bin:/usr/bin`. The controller records inherited real/effective uid/gid
and supplementary groups. Child fd 0 is the controller's input pipe; fd 1
and fd 2 are distinct output pipes. Other inherited descriptors are closed
using the child's own `/proc/self/fd` inventory. The child creates its own
session and process group. There is no shell, argv rewriting, environment
inheritance, PATH search, or ptrace.

The host runner must bind the actual controller, unchanged launcher, unchanged
payload ELF, interpreter, all DSOs, compiler/source/header inputs, module,
image, guest kernel, topology, and bootstrap to retained size/SHA-256 evidence
before execution. The controller records literal argv/environment in
`argv.nul` and `env.nul`; those files are metadata, not executable provenance.
The host must retain and hash the full attempt directory after completion or
emergency capture. A label or printed payload success line cannot replace
those bindings.

## Exact second-UART protocol

The controller opens `/dev/ttyS1` in raw, nonblocking mode at 115200 baud,
8 data bits, no hardware flow control, CLOCAL/CREAD, VMIN 0, VTIME 0. The host
must connect this UART to a dedicated byte stream; it cannot also be a
console or getty. The controller does not flush stale input. Unsolicited,
duplicate, malformed, oversized, wrong-identity or wrong-phase input fails
the original attempt. LF is the only line terminator; CRLF is rejected.

The complete request and response are ASCII, with exactly one space between
fields and one final LF:

```text
STF1 REQ NONCE SEQUENCE PHASE MODE LAUNCHER_TGID LINUX_WORKER_TID WORKER_START_TICKS
STF1 ACK NONCE SEQUENCE PHASE MODE LAUNCHER_TGID LINUX_WORKER_TID WORKER_START_TICKS CAPTURE_SHA256 CONTINUED
```

Every echoed field must match byte for byte. Sequence starts at 1 and increases
once per request. CAPTURE_SHA256 is exactly 64 lowercase hexadecimal characters
identifying the host's retained capture manifest. `CONTINUED` is literal.
The controller preserves the exact request bytes actually written and all
received UART bytes in `uart.tx` and `uart.rx`. The host must retain its own
stream, QMP commands/replies, VM state checks, and the identified capture.
An ACK is the host's assertion that its checks passed; the controller cannot
independently verify the physical capture represented by the digest.

1. PRE_INPUT (sequence 1) follows the exact readiness prefix and discovery of
   exactly one real Linux worker blocked in `read(fd=0,len=16)`. TGID is the
   owned launcher. TID and `/proc/TGID/task/TID/stat` start ticks belong to the
   actual blocked worker. The controller keeps stdin open and supplies no
   bytes while waiting for this ACK.
2. The host must pause QEMU and match the source-bound typed snapshot to the
   actual healthy Delivered read, including its request, fd, length, physical
   response, worker token, delivery, OS generation, and ledger serial. It must
   require response status 0 and wake state 2 before input. The send callback
   selector alone is too late to establish this phase. After preserving and
   validating that capture, the host continues QEMU and confirms QMP reports
   running. Only then may it write the PRE_INPUT ACK.
3. On ACK, the controller rechecks the same worker's start ticks and blocked
   read, then attempts one atomic pipe write containing exactly 16 bytes a5.
   A short, interrupted or failed write fails without retry. The controller
   records the write result and timestamp, then closes its input writer.
4. POST_RET (sequence 2) follows a bounded observation of sampled RET exit,
   post-read WAIT, worker disappearance or launcher becoming waitable. These
   observations are distinct. The host must establish the actual selected
   completion, injection and expected terminal/recoverable transition using
   its typed observer before acknowledging. For a terminal mode it must
   capture ownership before the controller kills the launcher. For a
   recoverable mode it must prove successful return and no quarantine.
5. Terminal modes wait at least five guest-monotonic seconds after POST_RET
   ACK, then request QUIET (sequence 3). The host must prove a five-second
   quiet interval after the real terminal transition, capture again, compare
   the required counters/ownership, continue QEMU, confirm running, and ACK.
   Only after this ACK does the controller terminate/reap its launcher family.

If input has been attempted and a normal phase fails, the controller preserves
its first failure, active phase and monotonic failure timestamp. Before owned
cleanup it sends this separate failure request with a fresh sequence:

```text
STF1 FAIL NONCE SEQUENCE FAILED_PHASE MODE LAUNCHER_TGID LINUX_WORKER_TID WORKER_START_TICKS REASON ERRNO
STF1 ACK NONCE SEQUENCE EMERGENCY_CAPTURED MODE LAUNCHER_TGID LINUX_WORKER_TID WORKER_START_TICKS CAPTURE_SHA256 CONTINUED
```

FAILED_PHASE is the phase that first failed, including `INPUT`, `OBSERVE_RET`,
`POST_RET`, `QUIET_INTERVAL`, `QUIET` or `NORMAL_COMPLETION`. REASON is the
controller's literal failure code and ERRNO its recorded integer; neither
field is an invented RET errno. The host immediately pauses QEMU, retains the
first-failure RAM/request/response/queue/register/owner evidence, continues it,
confirms QMP running, and sends the exact EMERGENCY_CAPTURED ACK. It must not
call a runtime failure transition merely to make an observation succeed.

The controller holds its current launcher/worker and pipe ownership for at most
30 additional guest-monotonic seconds while concurrently draining evidence.
It does not kill/reap the launcher during this window. It then enters bounded
owned cleanup after a valid ACK or deadline expiry. Missing, wrong-identity or
late ACK leaves `emergency_capture_confirmed=false`; an ACK never clears the
original failure or changes its collection exit to zero. If cleanup or the
later admission probe is itself the first failing phase, the same emergency
request captures the state still present, explicitly recording whether the
launcher was already reaped. It cannot resurrect an earlier live snapshot.

Only in this already-failed emergency window, malformed or delayed old UART
frames are retained and rejected individually, followed by bounded LF
resynchronization. An oversized or NUL-containing frame is discarded from
parsing through its next LF; all its actual bytes remain in `uart.rx` within
the declared bound. A subsequent exact current-sequence EMERGENCY_CAPTURED ACK
can confirm capture. No discarded normal ACK can confirm the emergency phase.
Normal handshakes continue to fail immediately on malformed/stale input. UART
artifact truncation prevents emergency confirmation even if a matching line
was observed. The original first failure remains the report's cause throughout.

Prepublication/permanent-pressure response comparisons begin with the real
AcceptedReturn prefix. Preparing RET legitimately changes stid/result/wake
before status publication; the pre-input bytes are not the frozen accepted
prefix. Notification failure permits guest consumption and response-address
reuse. Its oracle must compare phase/owner observations and prohibit a second
host access, rather than treating the old response address as immutable.
The typed observer must freeze expected ledger serials, retained counts and
operation counters before execution. Its own snapshot-completeness label is
not test acceptance.

## Observations and bounded collection

The controller samples `/proc/TGID/task/TID/syscall` at a nominal 5 ms interval
and preserves every sample it uses, as raw hexadecimal bytes with monotonic
time and read errno. It records Linux launcher TGID/start ticks separately
from Linux worker TID/start ticks. It does not invent a McKernel payload TID
from either Linux identity. The launcher stays unreaped during phase capture,
so a numerical TGID cannot be reused underneath the observation.

A sampled RET ioctl followed by a different syscall/running state or task
disappearance records a sampled RET exit. A later WAIT ioctl without a
sampled RET entry is recorded separately. Fast RET calls can be missed by
procfs polling. `accepted_ret_result` and `accepted_ret_errno` therefore stay
null and explicitly require external typed evidence. Neither subsequent WAIT,
raw launcher exit, nor the launcher's retained `perror("ret")` stderr is
mislabelled as a measured ioctl return. Root's verification-only callback
observation must supply the actual accepted-return entry, exit and errno where
the procfs samples cannot, and bind them to the same delivery/worker. The
required accepted-return bound remains 15 seconds from accepted completion.
The controller additionally enforces a conservative 15-second observation
bound starting immediately before its input write.

All clocks use CLOCK_MONOTONIC. Startup/readiness/worker selection has a
10-second bound; each capture handshake has a 10-second bound. Normal result
collection has a 15-second bound from input. The controller's non-cleanup work
has an overall 90-second bound; owned launcher cleanup has a separate
15-second bound. At most one 30-second emergency window may follow a post-input
failure; it is independent of the expired normal-phase deadline. The
new-admission probe has a five-second bound and at most
15 seconds for its own cleanup. These guest deadlines cannot advance while
the VM is paused. The independent host watchdog and the existing 300-second
QEMU bound remain mandatory, including emergency RAM/queue/register capture
if continuation fails or the guest/controller stops responding.

Stdout and stderr are concurrently polled and drained with a 64-KiB bound
each. Their bytes are preserved without decoding or newline normalization.
Each UART direction has a 16-KiB bound. `events.jsonl` has an 8-MiB bound.
Exceeding a bound records failure, truncation and seen/stored counts; it never
silently becomes success. Bounded drain batches keep a busy stream from
starving the other stream, UART or timeout observations. All artifacts use
exclusive creation; partial attempts and failures must be retained.

## Cleanup and mode-specific facts

The controller is a Linux child subreaper. It signals the owned process group
only while the original unreaped launcher still holds that identity, and
then signals/reaps only its actual direct children. Reparented descendants
are collected from its own procfs children list. It never searches globally
for process names or recycled TIDs. Cleanup requires both an actual ECHILD
census and EOF on both output pipes; any missing proof or 15-second expiry
fails. Raw `waitpid` status is retained. A signal death is distinct from a
normal exit with code `128+signal`.

For Linux reference and recoverable mode the local byte/exit oracle is exact
stdout `NATIVE_FAILURE_READY\nNATIVE_FAILURE_PASS\n`, empty stderr and real
WIFEXITED/exit 37, with no controller kill needed to obtain the result. The
host must additionally prove exactly one returned read value 16, full normal
McKernel retirement/procfs/pager cleanup, absence of quarantine, and eight
unchanged subsequent HELLO applications in the same OS. The controller does
not launch those HELLOs or assert those unobserved facts.

Terminal modes preserve the actual launcher stdout/stderr and raw exit without
inventing a required launcher exit code. In postpublication notification
failure the payload may already have consumed the published result; its
success marker is not transport success. After the two terminal captures and
owned Linux cleanup, a separately owned, bounded probe child opens `/dev/mcos0`
and issues the actual header-bound CREATE_PPD ioctl with NULL, matching the
unchanged launcher's initial admission call. Its actual result/errno are
recorded separately: `-1/EIO` for prepublication and notification failure,
`-1/ETIMEDOUT` for permanent backpressure. Open failure is separately encoded
and cannot satisfy this ioctl oracle. The host must still verify that no new
application was scheduled. The accepted RET's current EPROTO return after
quarantine is a different observation and is never substituted for the new
admission's original transport error.

Terminal quarantine never satisfies normal McKernel cleanup. Every report
sets `application_acceptance=false`, `transport_acceptance=false`,
`normal_mckernel_cleanup_verified=false` and `quarantine_verified=false`.
`collection_status=COMPLETE` and controller exit 0 mean this utility collected
its declared facts without detecting a local failure. Independent kernel,
ownership, provenance and mode-oracle evaluation is still required. The
quarantined VM is discarded after retained evidence; there is no production
reclamation or shutdown claim.

## Required validation before use

No compilation or execution was performed for this source preparation task.
The next serialized pinned-container stage must compile the exact controller
and unchanged payload with the actual include directory, retaining command,
toolchain/header/dependency identities, diagnostics and output ELF. A proposed
controller command shape is below; the orchestrator supplies fresh paths and
the already established pinned toolchain/container limits:

```text
gcc -std=c11 -D_GNU_SOURCE -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread -MD -I /workspace/executer/include CONTROLLER_SOURCE -o CONTROLLER_ELF
```

Compiler acceptance is only a build result. The subsequent reviewed
infrastructure tests must exercise malformed/stale/duplicate ACKs, missing
ACK deadlines, byte bounds under concurrent pressure, real signal/raw waits,
an escaped pipe holder, initial setup failure, admission probe timeout, and
the same-guest Linux reference. Every unexpected first failure is logged and
retained before a correction/retry. No application/vector host payload is
authorized by this document. The four actual fault modes require fresh
disposable guests, the reviewed observer/injection overlay, the original
one-CPU/128-MiB McKernel topology and all host/container limits from the
runtime plan. Injected EAGAIN does not establish a physically full IKC ring;
that remains a separate gate.

The UART negative-test plan uses an ordinary fake peer and fake owned process
only inside the later pinned container, under the existing isolation limits.
It must retain the exact controller source, harness, fake program, compiler
outputs, peer byte stream, process identities, host-monotonic timing and all
attempt artifacts. The fixture is infrastructure evidence only; a fake
launcher never establishes a real mcexec or transport result. A dedicated
pseudoterminal may be wired to `/dev/ttyS1` inside that disposable container;
no host device, host McKernel module or real application payload is involved.

| Negative scenario | Required observed result |
| --- | --- |
| Wrong version, nonce, sequence, mode, TGID, TID, start ticks or phase in PRE_INPUT ACK | Original attempt fails; fake child receives zero input bytes. |
| Missing PRE_INPUT ACK | Ten-second capture window expires; zero input bytes; bounded owned cleanup; no emergency window because no input was attempted. |
| CRLF, NUL, oversized line, short/nonhex digest, missing CONTINUED, duplicate ACK or unsolicited bytes | Raw bytes retained; normal handshake fails; no acceptance. |
| Fragmented but otherwise exact ACK | Accepted only after its complete LF-terminated frame; input remains blocked until then. |
| Post-input observation/POST_RET/QUIET failure with valid emergency ACK | FAIL request precedes cleanup signals; fake process remains owned/live until valid current-sequence EMERGENCY_CAPTURED ACK; collection still FAIL. |
| Missing or wrong emergency ACK | Live ownership held for the declared 30-second window; confirmation false; bounded cleanup afterwards; collection FAIL. |
| Delayed complete old normal ACK followed by valid emergency ACK | Old frame is retained/rejected; later exact emergency frame confirms capture without clearing first failure. |
| Partial old frame, NUL/oversized garbage through LF, then valid emergency ACK | Emergency-only LF resynchronization works; no false confirmation from old bytes; first failure remains unchanged. |
| Emergency ACK observed at or after its deadline | Confirmation false, including an artificially delayed controller observation; original timing and bytes retained. |
| Concurrent stdout/stderr pressure during missing ACK or emergency hold | Both exact bounded streams continue to drain; overflow is explicit FAIL; no silent truncation or timeout starvation. |
| SIGTERM to controller after input, with valid emergency peer response | First interruption recorded; emergency capture opportunity precedes owned cleanup; raw fake-child wait retained. |

The harness must verify actual input-pipe bytes and actual signal/wait order,
not only printed labels. Preserve the first failed test and exact old source
before making a correction. Run these checks serially with explicit per-test
and suite watchdogs; do not shorten production deadlines in the controller
being qualified. Guest QMP/observer ordering and all actual fault outcomes
remain separate tests after this infrastructure suite.
