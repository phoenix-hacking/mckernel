# Linux collector storage-fault-v2 source correction packet 9

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive replacement preserves rejected packets 6 through 8. Packet 8's
observable deadlines, exact cleanup/error unions, immutable result partition,
three runtime inputs and fresh-root argv remain mandatory except where this
packet explicitly tightens the supervisor boundary and wait-timeout identity.

## Frozen source and write scope

The only new source path is
`scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/supervise.py`.
This packet permits edits only to that file, the sibling `witness_owner.py` and
`oracle.py`, `packet.json`, `prepare.py`, `tests.md`, and
`scripts/tests/test_collector_storage_fault_packet.py`; `inject.h` and the frozen
collector/generated patch remain outside this correction's write set. Prepare
records exact no-follow stable hashes for supervisor, owner and oracle. The
supervisor resolves its sibling owner path canonically, stable-reads it, requires
the prepared owner SHA256 argument, and invokes it only with the same absolute
`sys.executable` used for the supervisor plus the reviewed owner CLI arguments.

## Exact supervisor interface and bound

The supervisor CLI receives canonical paths and hashes for owner, build source,
generated source, header, collector ELF, original request, selected manifest,
fixture, and the fresh attempt root, plus nonce and selector. It constructs the
packet-8/7 owner invocation; no shell is involved. Before spawn it records an
absolute start time. It observes the child twice through `/proc/PID/stat`, requires
matching positive startticks and PPID equal to itself, then waits at most 220
seconds: 10 READY + 2 RELEASE + 180 collection + 22 owner retirement + 6 owner
publication allowance. Timeout uses two matching birth/PPID observations before
TERM, waits one second, repeats both observations before KILL, waits five seconds,
and performs a final one-second reap; mismatch or unreaped state is failure.

Owner stdout/stderr are bounded to one MiB each through nonblocking pipes and are
fully drained while waiting. After owner exit, the supervisor creates the attempt
root itself only if the owner did not, writes/fsyncs exact
`owner-supervisor.stdout.bin` and `.stderr.bin`, and root-fsyncs them. Those are
the supervisor's only writes besides `supervisor-result.json`; all owner writes
remain beneath the same root. Existing paths, oversized streams, identity
mismatch, timeout, cleanup mismatch, or any persistence failure produce nonzero
supervisor exit and never `COMPLETE`.

The exact supervisor object from packet 8 adds
`owner_pid,owner_startticks,owner_stdout_sha256,owner_stderr_sha256`. PID and
startticks are positive exact integers and must equal the twice-observed child;
stream hashes are 64 lowercase hex and bind the two retained captures. If an
OWNER_RESULT exists, its `owner.pid/startticks` must exactly equal these fields.
The remaining presence/hashes bind actual stable no-follow bytes.

The independent oracle signature adds required exact integer
`supervisor_raw_wait_status`, supplied from the outer packet runner's direct
waitpid result. It must equal zero before any readable supervisor/result bytes
are interpreted. The oracle then requires `status=COMPLETE`, normal owner exit
zero/no signal, the PID/birth join, ordered time bound no greater than 220 seconds,
all hashes/captures, OWNER_ERROR partition, and terminal OWNER_RESULT equality.
The later build/run packet must retain this direct outer wait; source tests pass
literal raw zero or exact nonzero negatives. A readable COMPLETE object after a
supervisor fsync failure cannot pass because the actual supervisor wait is nonzero.

## Owner exit rule

The owner exits zero only when its infrastructure has no OWNER_ERROR, cleanup is
complete, every required owner fsync succeeds, and immutable OWNER_RESULT plus
terminal witness publication succeed. Collector storage-fault outcomes and their
reviewed nonzero collector waits do not themselves make owner exit nonzero. Any
owner infrastructure error exits exactly 125 after bounded cleanup; an actual
signal remains represented by the wait status. The supervisor alone maps these
to `COMPLETE` versus `OWNER_ERROR`.

## Wait-timeout identity tightening

Every cleanup operation maintains `last_matching_startticks` from any successful
double identity observation, including one obtained after an initially missing
observation. A wait-timeout record uses that positive exact value whenever it was
ever observed; startticks is null only if no matching identity was observed at
any point before the record. The source tests include the exact sequence initial
missing, later double-observed matching birth, then timeout with the positive
later startticks, plus a never-observed null control. This supersedes packet 8's
looser wording and matches packet 2.

No source/build/root/native/application/production gate is released by this
draft. Fresh independent review of its exact hash is mandatory.
