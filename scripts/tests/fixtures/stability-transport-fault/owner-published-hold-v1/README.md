# Published hold controller/client candidate v1

Source candidate only. No compile, metadata tests, PTY tests or guest execution.
The starting controller is the reviewed polling correction 2aa11489; the old
controller and phase client are retained byte-for-byte as .original files.
Mode 1/4 fixtures and all original guest reports remain immutable.

This candidate uses STF2 and only the published-mode owner-guest profile (modes
2 and 3), plus its independent Linux reference role. The private native command
is version2/0xc100f502. Exact native final source/build binding remains required.
The original launcher, runnable payload and all raw-wait/stream/owned-cleanup
code remain unchanged. Actual native RET records supply errno/value/timing.

After real read16 input, require the original worker/start ticks and an actual
complete RET procfs sample. Query ACCEPTED_STATUS until a healthy native held
reply is obtained or the existing bounds fail. Each dispatched query consumes
its sequence; only a fresh next-sequence query follows. The complete request is bound to the selected identity, nonce and exact
capture digest. Native reply fields, key identity, timestamps, timer, stage
and snapshot order are checked. Held
state is5; accepted snapshot sequence is2. The client allows at most24 ioctl
attempts, each with four artifacts, keeping a bounded exporter budget.

Request ACCEPTED_RETURN as UART sequence2 BEFORE waiting for RET exit. Its ACK
requires exact identities, a lowercase 32-byte digest and CONTINUED. Bound the
ACK wait by the original native deadline (and the unchanged two-second reserve
for mode3). The client records that raw digest and uses op8 once. It latches
release_possible before any release child/ioctl submission and never retries
release, even for untouched busy output or ambiguous child/copyout failure.
This conservative flag is recorded independently of confirmed released state.
No client response-memory reads occur. The future host must latch the same flag
BEFORE its first ACK send attempt and prohibit every later original-response
read, including emergency and final captures.

Status replies preserve timer and held timestamp; later replies require that
same timer, held timestamp and old barrier count, monotonic host-hold counts,
and strict snapshot/operation sequencing. Metadata parsing does not establish
native ownership, actual physical publication, host durability or QMP recovery.

The existing terminal boundary issues operation2 (TERMINAL) only after actual
original launcher WNOWAIT plus both EOFs, returning snapshot sequence3. After
at least five seconds, operation3 (TERMINAL_PLUS_FIVE) returns snapshot sequence4. Recovery
uses actual payload PASS/exit37 and native Recovery. Eight subsequent same-OS
HELLO launches and the new version2 AfterEightHello client are NOT YET COMPOSED;
mode3 cannot be released for execution or accepted with this candidate alone.
The host STF2 coordinator, strict hold-record join and physical capture gates
are also still pending. Do not run a guest until these independent prerequisites
and focused client/PTY tests pass on the exact final bytes.
