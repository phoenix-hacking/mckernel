# Controller protocol infrastructure harness

Source prepared; compilation NOT_RUN; all 23 cases NOT_RUN. No controller,
payload, application, transport fault or OS runtime acceptance is claimed.

`protocol_harness.c` includes the unchanged `controller.c` translation unit
with its main symbol renamed. It calls the actual `prepare_read`, `capture`,
`receive_uart` (through capture/pump), `release_input`, `emergency_capture` and
`cleanup_owned` functions. It does not reproduce their ACK parser, change their
clocks, replace their deadlines or edit production source. The source under
test is SHA-256
`be5c32e9298d9d1d8711c0ebfd89d2d9f7bc7b0215f8e897da2db5089fdc99eb`.

The ordinary fake child creates its own session, writes readiness, blocks on
an actual Linux 16-byte pipe read, checks the injected bytes and then pauses.
It never executes mcexec, the guarded application payload, an application
catalog case or a vector fixture. A separate ordinary child acts as a PTY
peer, compares literal complete requests from the reviewed wire contract,
and checks the fake child's real procfs start ticks and non-zombie state before
responding. The controller parent separately checks the actual blocked-read
and pause syscalls; the sibling peer does not need ptrace permission. Both
fake-process roles are explicitly infrastructure evidence. Their synthetic
capture digests and fake phase labels are never guest/QMP/owner evidence.

Each case uses a fresh process and attempt directory. Normal malformed cases
require zero injected input bytes and the still-blocked fake read. Emergency
cases first complete an actual valid PRE_INPUT handshake, release exactly 16
bytes a5, and fail the actual POST_RET handshake. They then invoke the real
emergency collector and require the fake child to remain live and unreaped
until its return. The original failing phase/reason/errno/timestamp remain
latched. Actual raw SIGKILL wait status and complete EOF streams are checked
after the actual owned cleanup. Peer raw wait must independently be exit zero.
The harness parent holds a duplicate stdin writer through cleanup, and the
peer closes its copy. The real cleanup closes its own stdin writer before
signalling; the harness duplicate prevents an EOF/exit race in the deliberately
blocked fake, so the required raw SIGKILL result remains deterministic.
It supplies no input and does not change the actual controller's cleanup.

`protocol-expectations.json` states the independent driver expectations:
literal output bytes, original failure reason, confirmation state, ACK count,
invalid-frame rejection and real elapsed-time lower bounds. The Python driver
also verifies each peer's independent live-process witness, actual harness raw
exit, its frozen executable identity and the supervisor's owned cleanup.
Malformed negative cases pass the infrastructure test only when the controller
rejects them; the controller remains failed in their retained observations.

The normal missing-ACK test uses the real 10-second deadline. The missing
emergency ACK uses the real 30-second window, with a live-process witness near
its end. The late-observer test installs a harness-only SIGALRM handler that
stalls this process for 31 real seconds. The peer receives a pipe notification
that the handler has started, then queues its valid emergency ACK. After the
handler returns, the actual controller observes the valid ACK after its
unchanged monotonic deadline and must leave confirmation false. This is an
actual delayed observation, not a replaced clock or an unreceived late ACK.
The harness does not stop or signal an unrelated host process.

The stale/partial/NUL/overflow cases require a later exact emergency ACK to
succeed without clearing the original failure. The partial case deliberately
lets a partial old POST_RET response reach its real 10-second timeout, then
sends its stale suffix, LF and a valid new emergency frame. All bytes are
retained by the controller and the independent peer. Normal parsing retains
its immediate rejection behavior; only the already-failed emergency parser
resynchronizes after malformed frames.

Root must compile and run these sources only through the already-authorized
pinned container wrapper, serially with other builds/guests, under its existing
four-CPU/12-GiB/no-swap/512-task/no-network restrictions. A compile command shape
is:

```text
gcc -std=c11 -D_GNU_SOURCE -O2 -g -Wall -Wextra -Werror -fno-pie -no-pie -pthread -MD -I /workspace/executer/include /workspace/scripts/tests/fixtures/stability-transport-fault/protocol_harness.c -o /work/FRESH/protocol-harness
```

Retain the real compiler invocation, version, full dependencies including the
included controller/ABI header, diagnostics, objects and ELF. Compilation alone
does not qualify the harness or establish application acceptance.

The exact single-case harness CLI is:

```text
/work/FRESH/protocol-harness CASE /work/FRESH/CASE-ATTEMPT
```

The complete driver invocation is:

```text
python3 -B /workspace/scripts/tests/fixtures/stability-transport-fault/run_protocol_tests.py --harness /work/FRESH/protocol-harness --attempt-root /work/FRESH-SUITE
```

Supply repeated `--case NAME` arguments for an explicitly selected subset; no
argument runs all 23 reviewed cases in manifest order. Every harness process
has a 65-second independent process-supervisor bound plus 15 seconds for
cleanup. The driver has a 150-second suite budget and reserves a full next
case before launching it. Typical declared sleeps total about 82 seconds for
the full suite. The container's independent outer watchdog remains required.

The helper stops on the first unexpected result, prints its identity promptly,
and preserves source copies, exact invocation, executable, supervisor outputs,
all controller/peer stream bytes and JSON reports. Root must log the first
unexpected failure and retain that complete original attempt before any fix
or retry. Existing attempt paths are never overwritten. A dockerenv marker is
only an execution guard; the real wrapper/limits/build record supplies
isolation and provenance. This suite does not substitute for actual UART/QMP
ordering, source-bound owner snapshots, actual RET returns or any fault guest.
