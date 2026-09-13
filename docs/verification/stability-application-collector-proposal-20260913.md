# Proposed guest collector and application observation boundary

This is a source-only proposal for the next backend slice. No collector, wire
decoder, application observer or execution release is implemented here.
`run.py` remains a metadata-only preflight. The original fault controllers,
payloads, captures and catalog remain unchanged. The companion JSON binds the
sources consulted; no test, build or guest was run for this proposal.

## Recommended implementation choice

Use a new native C guest collector for the existing minimal Linux guest. Its
job is ordinary Linux process ownership, literal execve setup, bounded pipe
collection and actual Linux wait status. Reuse reviewed patterns from the
existing C controller, preserving the original translation units. Keep native
McKernel application observations in a separate producer and validator.

| Choice | Useful existing work | Additional obligations |
| --- | --- | --- |
| New C collector | The pinned guest already carries libc/loader closure; the fault controller supplies real fork/setsid/dup2/proc identity, concurrent pump, raw-wait and owned-cleanup patterns. | Generalize input parsing, argv/env/cwd/identity setup, stream limits and ordinary process outcomes under a new source contract. Test the actual new C binary; fault-handshake tests do not cover every collector boundary. |
| Python supervisor inside guest | `supervisor.py` already has broader process-pressure, timeout, signal and pipe-holder tests, executable-path versus argv0 separation, and a private worker watchdog. | Add and bind the guest Python interpreter, standard-library/extension dependencies and native dependencies, prove imports and worker startup inside the exact guest, and retain that closure. The accepted/root4 inventories inspected here contain no Python path. Container Python cannot replace guest Linux execution. |

C is the smaller next deployment step for this guest layout. This is not an
argument to rewrite or remove the Python supervisor: retain it for host/container
orchestration and as an independent implementation reference. Neither language
provides McKernel provenance just by launching mcexec.

## Bounded collector scope

Create a new fixture directory, for example
`scripts/tests/fixtures/application-collector-v1/`, after source review of the
request/observation contract. The first collector supports the existing root
profile, a literal executable plus argv/env, cwd, `/dev/null` or one immutable
regular stdin file, and separate stdout/stderr pipes. No shell, network setup,
arbitrary expression, environment inheritance, executable callback or general
process-name cleanup belongs in that interface.

The host should validate a strict JSON request and encode one separately reviewed
bounded binary argument table for C: an explicit version, byte length and
counts, followed by exact length-delimited bytes. C must validate every length,
count, terminator, duplicate environment key and trailing byte independently.
Preserve argv0 and empty arguments; never infer argv0 from executable path.
This avoids adding a permissive JSON implementation to a small C utility. The
binary layout and its independent positive/negative vectors must be frozen
before implementation; this proposal does not authorize an unspecified layout.

Freeze exactly ten seconds of process time and fifteen seconds of cleanup for
the first slice, with each raw stream bounded to 65536 bytes and an independent
300-second host QEMU watchdog. Preparation remains bounded to 120 seconds.
The caller enforces the existing four-CPU/12-GiB container, four-vCPU/8-GiB Linux
guest and one-CPU/128-MiB McKernel profile. Do not impose an unverified small
RLIMIT_AS on the launcher's mirror mapping. An exported report cannot substitute
for actual cgroup/topology/boot observations.

Existing controller patterns worth reviewing are `start_child` (literal execve
and fd closure), `task_ticks`, `check_launcher` (WNOWAIT), `drain_stream`/`pump`,
and `cleanup_owned`. Reimplement them under the new collector contract instead
of copying its read16/RET phase machine, fixed READY/PASS oracle or UART ACK
logic. Retain the leader unreaped until group cleanup is complete; signal only
the owned group and pinned direct/adopted descendants. Preserve raw child waits
and any uncollected/unknown ownership. A live pipe holder or escaped owned child
cannot become normal collection success. Signal-handler interruptions and a
deadline observed after completion remain explicit outcomes.

An actual guest setup contract must create `/case/work` and payload/input paths,
verify regular/nonsymlink files and loader bytes, establish uid/gid/groups/umask,
and capture actual fd setup before execve. The earlier missing-cwd failure stays
failed and motivates a setup check; a metadata pathname alone proves nothing.

## Proposed observation records

Use separate immutable JSON records with `schema_version: 1`, an exact `kind`
and unknown-field rejection. Every record has `attempt_id`, `case_id`,
`selected_inputs_sha256`, `request_sha256`, `producer_source` and
`producer_executable` artifact references. Artifact references retain the
existing canonical path/size/lowercase-SHA256 format. Every decision keeps
application acceptance false until the final reviewed evaluator exists.

**`linux-process-collection`** describes exactly the process forked and waited
by the C collector. Required fields are:

- `role`: exactly `linux-reference-payload` or `mckernel-launcher`; this label is
  a routing selector, not proof of where an application executed.
- `launch`: `executable_path`, retained executable identity, literal `argv`,
  complete `env`, `cwd`, actual uid/gid/groups/umask and stdin identity. The
  request's desired values and observed child-setup values are separate objects;
  every difference fails setup.
- `process`: actual Linux TGID, process-group/session IDs and startticks,
  joined to the collector's own child-creation record. A list retains every
  subsequently owned child and the basis of ownership.
- `collection_status`: one of `COMPLETED`, `LAUNCH_ERROR`, `TIMED_OUT`,
  `OUTPUT_LIMIT`, `ORPHANED_DESCENDANTS`, `CLEANUP_ERROR`, `INTERRUPTED` or
  `COLLECTOR_ERROR`. A nonzero exit or signal can still be COMPLETED collection.
- `monotonic`: start no later than fork/exec eligibility, deadline and actual
  terminal-observation time, plus cleanup start/deadline/finish. Late observation
  cannot be called on-time completion. Host QEMU timing is retained separately.
- `linux_wait`: the actual integer raw waitpid status or null when uncollected,
  and its consistent `exited/code` or `signaled/signal/core_dumped` decoding.
  Do not synthesize this integer from a returncode or a printed diagnostic.
- `streams`: each raw artifact, EOF, declared limit, observed/retained/discarded
  byte counts and truncation flag; `cleanup`: complete flag, raw actions/waits,
  remaining owned identities and omitted-record count. Missing data remains
  missing; caps and loss cannot be implicit.

For the Linux reference this raw status is the actual payload status. For
McKernel it is the launcher's Linux status, even when it numerically resembles
the payload's desired outcome. Keep it under that subject and retain it unchanged.

**`mckernel-application-observation`** is produced from separately captured,
source-bound native evidence, never by renaming fields in the Linux report.
Required fields are:

- `observation_status`: `COMPLETE`, `PARTIAL` or `MISSING`, with explicit reasons;
  completeness describes collection, not correctness or acceptance.
- `application_key`: actual OS ID, generation, application token, scheduled
  guest PID and guest TIDs, each with original event references. Unobserved
  identities are null; requested OS0 and a Linux TGID are not substitutes.
- `image_binding`: source-bound observed application image/loader mapping and
  its relation to the exact executable/interpreter/DSOs in the request.
- `route_events`: original event references and actual worker identity,
  delivery token, syscall number/arguments and corresponding return result.
  Record sequence/loss information and join the events to the same application
  and generation. A scheduled application alone is insufficient.
- `terminal`: original native terminal event or null; its actual subject,
  source site, native exit/signal classification and raw native fields. Keep
  `guest_waitpid_status` null unless an actual guest wait observation exists.
  Native exit encoding and Linux launcher wait are distinct fields.
- `lifetime`: original application/worker/process/pager/claim snapshots before
  execution, at terminal observation and after normal retirement, with the
  reviewed invariant/profile identity. Retain all rows and explicit capacities,
  overflow, omission and trace coverage. Quarantine is not normal retirement.

Initial startup cases require independently joined ordinary payload exit0,
normal cleanup, actual routing and the fixed oracle. Fatal-signal cases stay
BLOCKED until an actual payload signal/wait contract is implemented. In
particular, neither launcher exit128+signal nor manufacturing a wait bit pattern
from a native enum satisfies the original real-WIFSIGNALED requirement. A real
guest parent/wait observation would itself require reviewed child capability
and separate attribution; do not introduce one implicitly in this first slice.

**`application-stream-partition`** retains `raw_collection_sha256`, a reviewed
source-bound `framing_profile` identity, and an ordered nonoverlapping complete
partition for each raw stream. Every segment has an offset, length, byte hash
and subject `payload`, `launcher` or `unattributed`. Derived payload stream
artifacts must be recomputed from those raw ranges. The validator must prove
every diagnostic segment's exact bytes and source/order rule, account for every
byte exactly once, and block any ambiguous/unattributed partition. There is no
generic filtering, arbitrary regex normalization or deletion of unexpected
stderr. If framing cannot be proved for the unchanged launcher, retain the raw
stream and leave the payload oracle BLOCKED.

Finally, an **`application-attempt-observations`** bundle references both Linux
process reports, the native application observation, stream partition, actual
profile/boot/root bindings and independent oracle. File hashes make the
relations explicit without a self-hash cycle. The evaluator checks each engine
against the independently frozen oracle and joins same-binary execution,
provenance and lifetime. Agreement between two outputs is not the oracle.

## What remains source work before the first application run

The current owner/phase observers select read16 and fault phases; they are not a
generic normal-application terminal observer. The C collector cannot provide
missing native lifecycle data by reading `/proc` or printing labels. Review a
new source-bound normal-observation interface for the existing baseline before
claiming the proposed application record can be filled. Preserve observer
completeness/capacity checks and original first-64-delivery sampling limits.

The next concrete implementation slice is the request decoder and Linux-process
collector only, with actual-C infrastructure fixtures for argv0/empty argv/env,
cwd/fd failure, missing exec, concurrent pipe pressure, exact stream limits,
real signal versus exit128+signal, independently observed timeout, inherited
pipe holders, owned descendants and interruption. Malformed/trailing/oversized
requests and inconsistent observed identities fail before payload launch.
These are collector tests, not catalog results; root owns their pinned run.

Then qualify the actual guest wiring with an unchanged accepted baseline such
as HELLO and its fixed exit37 under separately reviewed prerequisite authority.
Retain both guest engines, loader/root/identity evidence, every raw byte and
normal lifetime. This prerequisite replay contributes zero new catalog cases.
Keep the new catalog blocked until the complete runner contract, all four
transport fault modes, current binary/capability bindings and a separate packet
release pass. Start one reviewed startup case, then the remaining two and the
explicit same-OS/fresh-guest repeat schedule, within independent deadlines.
No part of this proposal narrows the broader OS, native production, Rust/assembly
or qualification roadmap.
