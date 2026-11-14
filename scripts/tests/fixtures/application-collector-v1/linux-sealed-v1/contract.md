# Linux sealed-image infrastructure collector, version 1

This is a separate **x86-64 Linux infrastructure** execution profile, not new semantics for
ACRQ profile 1 or an application runner backend. The decoder and its original
wire contract remain immutable. `run.py`, native launcher execution, catalog
predicates and application acceptance remain disabled. In particular, immutable
pathname execution is still a concrete gate before any existing case release.

The only supported command is:

```
linux-collector --linux-sealed-infrastructure-v1 REQUEST INPUT_MANIFEST ATTEMPT
```

All three paths are absolute. ATTEMPT must be new; its parent and every input
path component must be existing nonsymlink directories. REQUEST is the exact
ACRQ0001 byte record. INPUT_MANIFEST is retained and hashed against the request's
selected-input digest. Its content is opaque to C; this check does not evaluate
capabilities, compilation, loader closure or a runtime packet. A separate caller
must perform those checks before any future application backend exists.

The collector accepts only the declared Linux reference role (1), request
identity/limit profile 1 and this explicit collector-side mode. McKernel role 2,
unknown/default/pathname modes and any attempt to submit catalog predicates are
unsupported. Ordinary builder-UID invocation is BLOCKED: positive infrastructure
fixtures require root in the separately pinned, isolated container. Desired
child uid/gid/groups/umask are established and observed, never copied into an
"actual" record without checking the child setup.

This first collector further bounds executable source to 1 MiB and regular
stdin to 65536 bytes; otherwise valid ACRQ requests beyond this subset are
BLOCKED. The selected manifest is at most 4 MiB. Request capture is bounded to
65537 bytes, retaining the one-byte-over negative fixture. Preparation has a
120-second monotonic deadline; child time is exactly ten seconds beginning no
later than fork, followed by at most fifteen seconds of owned cleanup. Separate
stdout/stderr retention bounds remain 65536 bytes. An independent external
supervisor must also bound the utility itself, filesystem stalls, interruptions
or a stopped collector and reap all adopted descendants. Local late observations
cannot become on-time completion.

The literal executable pathname is a **source selector**. The collector opens
it without following symlinks, copies and hashes its exact stable bytes, and
checks the requested size/digest. It then seals a private memfd against content
writes, growth and shrinkage before `execveat(fd, "", argv, env, AT_EMPTY_PATH)`.
Creation requests the original CLOEXEC|ALLOW_SEALING flags3; observed mode0500,
regular backing and exact content seals15 are required. This supports the actual
container host's older memfd ABI. A newer kernel's default no-exec policy can
make the setup BLOCKED; no retry opts out of that policy with MFD_EXEC.
This prevents a subsequent source-path replacement or write from selecting
different main executable bytes. Literal argv0 remains independent of that
source path, including empty later arguments and complete environment bytes.
Privileged/script/non-x86-64-ELF sources are outside this initial subset.

The actual backing is a sealed anonymous file, not the requested pathname.
`AT_EXECFN` and `/proc/self/exe` consequently have descriptor/memfd semantics;
path-sensitive predicates are BLOCKED. The report separately names requested
source, verified source stat/hash, sealed descriptor stat/seals, pre-exec child
descriptor observations and any actually observed post-exec `/proc/PID/exe`
identity. Missing post-exec observation stays missing. Error-pipe EOF alone
must not be labeled a directly observed successful exec. Interpreter/DSO closure
is not verified by this utility; no loader or application capability is granted.
The later `/proc/PID/exe` readlink is an independently timed sample, explicitly
not atomic with the earlier matching descriptor stat; a subject can exec again
between these observations. An absent link sample stays null.

Regular stdin receives the same stable-copy/hash/seal treatment with its own
descriptor and offset zero. `/dev/null` requires a real character device 1:3.
The child gets only stdin, separate blocking stdout/stderr pipe writers and
the CLOEXEC setup/error channel and executable descriptor needed before exec.
Cwd is opened component by component and selected by descriptor. Actual child
credentials, supplementary group, umask, cwd identity and fd modes are checked
before attempting exec. All inherited signal dispositions/masks are reset in
the child. The x86-64 kernel rt_sigaction ABI also resets glibc-reserved signals
32/33 rather than overlooking their EINVAL from the public wrapper. The child
uses a private session/process group; the collector confirms Linux subreaping.
The collector unblocks its own handled interruption signals and latches an
interruption through completion, cleanup and final report storage. An interrupt
during/after storage cannot produce an outer success even if an already-written
inner snapshot preceded it. Every observed completion/deadline comparison uses
an exclusive deadline.
`collector_interruption_signal` preserves the actual caught signal separately
from the EINTR error classification; a signal number is not reported as errno.
An already observed exact supplementary group `[0]` is retained without calling
setgroups unnecessarily; a mismatch requires successful setgroups and subsequent
observation. This permits the explicit root container profile to retain
cap-drop=ALL with OCI `--user=0:0 --group-add=0`. Root UID never grants an
unobserved capability or exemption from setup checks.

Collection is distinct from an oracle. A completed child can have a nonzero
exit or a real signal. Preserve the actual `waitpid` integer and consistent
`WIFEXITED`/`WIFSIGNALED` decoding; do not synthesize it from a printed result or
128+signal. Keep the original leader unreaped until its owned group has been
handled; never target the collector's group. Recheck direct/adopted ownership
and startticks, preserve every raw reap, drain both streams concurrently, and
require final ECHILD plus EOF for complete cleanup. Surviving descendants,
unattributed pipe holders, observation loss, overflow or cleanup deadline are
explicit failures. No unowned process may be signaled to obtain EOF.

Artifacts include original request/manifest, verified executable and stdin
copies where applicable, literal `argv.nul`/`env.nul`, stdout/stderr, the raw
child setup channel, bounded events and a final JSON report. Hash/count updates
follow every successful stored prefix; short writes must not claim unstored
bytes. Unknown/truncated evidence stays explicit. Root must inspect the actual
outer collector status/raw wait and complete artifacts even when an inner
report claims collection completed.
Every attempted artifact separately records whether exclusive creation actually
succeeded and whether a usable descriptor was obtained. Failed creation has a
null observed path/hash and its real creation errno; it cannot masquerade as an
empty file. A failed low-fd relocation preserves successful creation separately,
with explicit descriptor error and no complete hash. An actually observed second
source stat remains present even when it differs from the first stat and fails
the stability comparison.

The report kind is `linux-sealed-infrastructure-collection`, version
1. It records actual Linux collector/child identities, desired request fields,
verified source and backing artifacts, monotonic phase/deadline observations,
setup/exec observations, raw child wait, pipe loss/EOF, owned cleanup and first
failure. Application/transport acceptance and backend enablement are always
false; native payload identity and payload completion are never manufactured.

The private child setup channel consists of one 384-byte READY packet, or a
384-byte ERROR packet, or READY followed by ERROR for a failed exec syscall.
Each packet is 48 little-endian u64 words. Words0..4 are magic0x314c4341,
version1, kind1READY/2ERROR, stage1SETUP/2EXEC, errno0 for READY. ERROR requires
positive errno and words5..47 zero. READY words5..8 are observed PID/PPID/PGID/SID;
9..12 uid/euid/gid/egid; 13..15 supplementary count/first group/observed umask;
16..17 cwd dev/inode; 18..26 triples mode/dev/inode for fd0,1,2; 27..29 actual
sealed executable dev/inode/seals; 30 actual stdin offset or UINT64_MAX when
lseek fails; 31..33 F_GETFL for fd0,1,2; 34..36 F_GETFD for those fds; 37 the
executable FD_CLOEXEC value; 38..47 zero. Raw records are always retained and
the parent independently checks their complete framing/identities/setup values.
The report's `setup_words` represents the actual READY record if one exists;
`setup_ready_record` distinguishes absent zeros. A READY record proves pre-exec
checks, not successful exec. `configured_execution_mechanism` is similarly an
explicit configuration label; only the separate observed records claim events.

Collector exit0 means complete Linux collection, including a nonzero/signaled
child. Exit2 means BLOCKED, exit1 another observed failure, and exit125 means the
exclusive attempt/final report could not be durably retained. Usage without all
four explicit arguments exits2 without an attempt. Collection status is one of
COMPLETED, BLOCKED, PREPARATION_ERROR, COLLECTOR_ERROR, SETUP_ERROR, EXEC_ERROR,
OUTPUT_LIMIT, ORPHANED_DESCENDANTS, TIMED_OUT, INTERRUPTED or CLEANUP_ERROR.
No status is an application oracle. `tests.md` states the initial actual-C batch
and remaining qualification cases separately.

Required actual-C infrastructure fixtures cover SHA256 known answers/chunk
boundaries, missing/malformed/stale/symlink/FIFO files, builder-UID and role/mode
blocks, copied image/stdin identities, literal argv0/empty/env/cwd, simultaneous
pipe pressure, exact limits and overflow, genuine signal versus exit143,
timeout, inherited pipes, escaped adopted children and interruption. Root owns
the pinned compilation and execution. No test or guest run is claimed by this
source document.
