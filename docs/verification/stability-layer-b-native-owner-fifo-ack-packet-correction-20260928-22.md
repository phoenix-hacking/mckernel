# Layer-B native-owner FIFO acknowledgement packet 22 (correction)

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**.  This is the single bounded
correction after `FAIL_FIFO_EXECUTION_PACKET` for packet 21
(`4d2931e733c88a7d81de543d5b8b574bfc88a82051524107cad96ecc0136d9d1`).  It
releases no execution.  Only an independent PASS on these exact bytes may
authorize one compile-only attempt in fresh root12.  Linking, runtime, tests,
guests, M02/M03 work and acceptance remain prohibited.

## Binding history and strategy provenance

Packet 21 and all earlier lineage, source hashes, failure records, root12
identity, no-retry rule, cleanup, and ET_REL-only boundary remain binding
unless this correction states an explicit replacement.  The checkpoint-6
record is pinned at SHA256
`322d00b463023930292df91dba0079730cc1d5f03375e1b0f21263538b424a64`.
The recorded result is `PASS_FIFO_STRATEGY`, strategy-only, with execution not
run.  Its provenance is the dispatcher run
`.git/os-autopilot/runs/20260928T095536Z-095509d1/console.log` (strategy agent
message and output, including the exact writer and lifecycle constraints),
and checkpoint 6's `results.layer_b_fifo_strategy` entry; no human approval
is inferred.  Before release, the independent reviewer must verify those
records and packet 21's exact SHA.

The pinned tool hashes are: `/usr/bin/cat`
`87e5bd81850e11eeec2d3bb696b626b2a7f45673241cbbd64769c83580432869`,
`/usr/bin/dd`
`944e841180d21c3d60b079bd3e4a4b804d528cee289717c10390c7c0180825fa`, and
`/usr/bin/mkfifo`
`701473b4e6883abe695f287feefea5f877d26c0aca460960a1d5b1673f5ab878`.

## Corrected non-following preflight and exact service

All inventories use metadata-only `lstat` and never open, hash, read, or
follow the FIFO.  The FIFO's type, mode, owner, device identity, link count,
size, timestamps and path ancestry are recorded from `lstat`; its content is
never hashed because it has no regular-file content.  Only the sole declared
`cat` reader and sole bounded writer may subsequently open it.  The regular
one-byte token is separately hashed as
`559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd`.

The packet 18 sleep/marker/test precommands are explicitly removed, not
retained or composed with this packet.  The final rendered `systemd-run`
argv contains exactly one pre-command, exactly this one argv element:

```text
--property=ExecStartPre=/usr/bin/cat R/logs/ack.fifo
```

There is no shell, marker, test, sleep, second opener, response file,
command substitution, second unit or alternate cat.  All other packet 10
`env -i`, `prlimit`, gcc, resource, source and output arguments are rendered
in full, hash-pinned, and parser-verified.  `cat` must remain pending in the
prebound start-pre state until the writer supplies exactly one byte.

After identity binding, the sole writer is exactly:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/dd if=R/logs/ack.token of=R/logs/ack.fifo bs=1 count=1 status=none
```

The paths are substituted literally.  No `iflag`, timeout widening, shell,
echo, printf, tail, regular-file replacement, second dd, or controller FIFO
open is permitted.  Initiating the writer authorizes the possibility that gcc
has started: writer initiation is therefore a one-way boundary.  Any writer
timeout, error, short/long transfer, ambiguous status, or observation race
latches failure and requires the prescribed cleanup; it is never a reason to
retry.  Writer success and cat status 0 are verified separately, followed by
the exact main success predicate.

## Identity barrier, timing states and cleanup

The observer persists and fsyncs the raw identity responses and their
unit-to-control-group/path mappings before the writer is started.  It then
performs a fresh pre-writer query and requires the same unit identity,
nonzero InvocationID, `ControlGroup` mapped to the recorded hierarchy,
nonzero `ControlPID` inside that mapped cgroup, `MainPID=0`, an unstarted
main process, and the expected `/usr/bin/cat` pre-command.  Missing,
changed, empty-unbound or ambiguous fields fail closed.

Pre-ack states are limited to the fresh identity-bound `activating`/
`start-pre` state.  After the writer, the observer records and distinguishes
`active`/`running` and terminal states; it never treats a post-ack state as a
pre-ack identity proof.  The packet 10 terminal predicate remains binding:
cat=0, writer=0, main=0, exact identity and normal completion, followed by
resolved cleanup.  An empty terminal cgroup is valid only with the stable
prebound tuple and successful cleanup; otherwise it is
`FAIL_UNRESOLVED`.

The sole submission's 90-second acknowledgement observation deadline is
anchored to submission time, with the full 90 seconds available after that
instant.  Submission remains bounded by the packet's exact timeout and
`TimeoutStartSec=120s`; the observation deadline is not started early by
preflight or identity polling.  Polling retains raw responses, monotonic
times, unit definition, pre/main/writer statuses, journal, cgroup mappings,
and recursive `cgroup.procs`.  On every result the independent 30-second
cleanup stops the exact unit; ambiguity, residual state, or original-cgroup
non-emptiness additionally requires manager-side kill of the exact unit.
Never signal a numeric PID, reset evidence, delete the root, or start another
unit.  Preserve all original attempts and evidence.

Only after full success may static `readelf`/`objdump` inspection verify an
ET_REL x86-64 object.  No link or execution is released.  One fresh root12
attempt is permitted only after this correction receives an independent PASS;
otherwise no root12, compiler, systemd or privileged operation may run.
