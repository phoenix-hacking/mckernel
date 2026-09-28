# Retained Layer-B FIFO strategy review 23

Status: **PASS_FIFO_STRATEGY**. Scope: strategy approval only. This record
preserves the completed independent response emitted by canonical agent
`/root/layer_b_fifo_strategy`, turn
`01a0e771-eb1d-77c2-ba7d-6723810d9587`, between 2026-09-28T09:58:21Z and
2026-09-28T09:58:53Z. The closed original launcher log is
`.git/os-autopilot/runs/20260928T095536Z-095509d1/agents/5d70ef8206bc6e265f2745dacc1d1dbfdb4dcd5b917e5cc8ebe3c4c003ce2c8b.log`.
The response is retained below as emitted; this repository copy, rather than the
launcher log, is the immutable input for later packet review.

## Exact completed response

PASS_FIFO_STRATEGY — for the identity-before-compiler invariant, subject to these mandatory packet predicates. This is strategy approval only.

The raw, hash-verified [attempt10 archive](/home/holden/mckernel/docs/verification/evidence/stability-layer-b-native-owner-bootstrap-failure-20260928-10.tar.gz) confirms a 199,901 µs main process and empty terminal `ControlGroup`. The [attempt11 archive](/home/holden/mckernel/docs/verification/evidence/stability-layer-b-native-owner-bootstrap-failure-20260928-11.tar.gz) confirms captured `activating/start-pre` identity, sleep status 0, marker-test status 1, unstarted main command and resolved cleanup. Neither establishes object acceptance.

Required strategy:

1. Use a fresh exclusive mode-0700 root and unique unit. Create the absent FIFO with literal `/usr/bin/mkfifo --mode=0600 R/logs/identity.fifo`; record component resolution, owner, type and device/inode. Create a separate mode-0600 regular token file containing exactly one prehashed byte. Never hash/read the FIFO, open it read-write, add another reader/writer, replace it, or unlink it while supervision is unresolved. Mode 0600 does not isolate against other processes of the same UID.

2. Submit once with `--no-block`, exactly one `ExecStartPre=/usr/bin/cat R/logs/identity.fifo`, no ignored failure, and packet10’s unchanged main command/resource limits. Retain literal argv arrays; rendered `systemctl show` commands remain corroboration, not argument-boundary proof.

3. A concrete bounded timing contract is `TimeoutStartSec=120s`, observation deadline 180 seconds from immediately before submission, and acknowledgement deadline 90 seconds from that timestamp. Preserve `RuntimeMaxSec=60s`, `TimeoutStopSec=5s`, and independent 30-second cleanup. Before every operation require its timeout plus kill allowance to fit the applicable deadline. These limits bound failure; they do not guarantee success under dispatcher stalls.

4. Before acknowledgement require exact `loaded/activating/start-pre`, matching unit, nonzero InvocationID, nonempty ControlGroup, nonzero ControlPID belonging to the recursively mapped original cgroup, `MainPID=0`, unstarted main timestamps, and the expected running cat command. Retain raw identity, both hierarchy mappings, parent identities, packet/root/nonce/FIFO/token bindings and timestamps. Close those regular evidence files, then successfully run bounded `/usr/bin/sync -f R/logs`. Requery identity immediately before release and reject discrepancies.

5. Release only once using literal `/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/dd if=TOKEN of=FIFO bs=1 count=1 status=none`, with fully substituted paths. Retain raw argv, streams, status and monotonic start/end.

The important correction is that **writer initiation authorizes possible compiler execution**. `cat` does not authenticate the token: a writer that opens and closes without writing can produce successful EOF. Therefore any writer timeout, error or disappearance after initiation must assume gcc may have started, latch failure and enter cleanup. This preserves durable-identity ordering but cannot promise “writer failure prevents gcc.” Require successful writer and cat statuses for attempt acceptance. [FIFO/EOF semantics](https://man7.org/linux/man-pages/man7/pipe.7.html), [cat implementation](https://raw.githubusercontent.com/coreutils/coreutils/v8.30/src/cat.c).

If the reader disappears before rendezvous, writer open can block until its timeout; after rendezvous, writes can encounter SIGPIPE/EPIPE. With no writer, cat remains blocked until systemd’s startup timeout. A failed/signaled pre-command must not be confused with successful main execution. [systemd v245 lifecycle](https://raw.githubusercontent.com/systemd/systemd/v245/src/core/service.c).

Require cat exit 0 plus packet10’s main success/status/timestamp predicate. Empty terminal ControlGroup is allowed only with matching prebound unit/InvocationID and subsequent original-path reconciliation. Stop immediately; retain mandatory manager-side group kill on ambiguity, recursive original-path empty/absent evidence and accessible parent identities. Never signal numeric PIDs. Never repeat submission or acknowledgement.

Observed tool SHA256 values, to pin and reauthenticate in the packet:

```text
cat    87e5bd81850e11eeec2d3bb696b626b2a7f45673241cbbd64769c83580432869
dd     944e841180d21c3d60b079bd3e4a4b804d528cee289717c10390c7c0180825fa
mkfifo 701473b4e6883abe695f287feefea5f877d26c0aca460960a1d5b1673f5ab878
```

Retain existing timeout/sync/systemd/compiler pins and packet10/correction11/direct15 provenance requirements. Fresh exact packet review remains necessary. No execution, linking, owner behavior, M02/M03, guest or acceptance is released; FIFO runtime behavior was not tested.

## Scope flags

- Compiler or service executed: **false**
- Linking or owner behavior executed: **false**
- Guest/application executed: **false**
- Production, language or application acceptance promoted: **false**
