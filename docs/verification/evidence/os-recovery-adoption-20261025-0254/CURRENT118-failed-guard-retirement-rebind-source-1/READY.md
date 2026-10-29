Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is SOURCE preparation for one exact idle failed-helper retirement, not an
execution release. Target2232651/b103343097 is the failed cleanup helper running
source4179233c, single UID/GID1000 thread, pgrp/session2232651, child of actual
Root parent2232650/b103343093/tool90401, with empty children and FD4 owning sole
permanent FLOCK27:4. These are retained independent FACTS503496d7/REVIEW156735f9;
no new actual capture or target query was performed by this worker.

The kernel-side protocol applies unchanged. We import the exact reviewed3fdb4dde
primitive and retain its original `pidfd_open` syscall434, fdinfo binding,
`sole_sigkill` syscall424, positive exit-readiness poll, nonblocking acquisition
of the unchanged existing27:4 node, sole-holder check, and quarantine loop.
The original execution sequence is reused through an exact-source AST selection:

```
target sole27:4 proof1 -> pidfd_open/bind -> target proof2 -> durable PREPARED
-> bind pidfd/sole target lock -> final current guard/freshness check
-> attempted=True -> exactly one bound pidfd signal -> positive exit readiness
-> acquire SAME27:4 -> postproof -> durable COMPLETE -> close replacement FD
```

The successor never pre-acquires a competing lock, unlinks/replaces the node,
unlocks the target's live FD, signals a numeric PID/group/descendant, retries an
uncertain signal, or touches a model/controller. All six current armed actors
(watcher, worker, server, guardian, monitor, phone) are exact deny targets. Root's
authoritative armed-control and earliest-cap files remain exact external authority
refs in BINDINGS/release, independently authenticated and checked by guardian4889.
They are not falsely presented as Git-published source files. Historical actors,
failed namespaces and excluded records remain retained.

The historical be4ea78f/80259 release cannot apply: its seven Docker exit0 records,
lease/exclusions, stopped exit1 container and process identities describe another
operation. The smallest required extensions are the current typed profile and
three callbacks around that existing protocol:

- Guard identity extends the existing byte/node/boot/UID/GID/thread/source/argv
  checks with dedicated pgrp/session, empty children, exact FD4 link+kernel flock,
  actual parent birth/executable/credentials/group/session/sole-child ownership.
  The expected target argv is derived from STARTED plus the actual failed release
  f3b9c5d6, and must be freshly equal; it is not claimed as a saved argv capture.
- Protected inputs bind62 exact source/image/declared output/failed raw records.
  Original client2232653/b103343210 remains UNKNOWN/positive_wait4false. No RM claim
  or RESULT may have appeared. No old output, source, artifact, exclusion or
  container is removed. Fresh readonly container/image/inventory checks reuse the
  accepted current118 exact profile validator, including inherited image metadata.
- Fresh full process/group reports run every unchanged historical census predicate
  through an explicit schema-name adapter, then require complete group/session
  rows and109 prior actors/old unknown client/prior new-query-client absence. Only
  the exact idle target is allowed as a pre-signal publisher. It must be absent
  after retirement. Two separate preproofs must remain within120s after PREPARED
  fsync; current account/identity/earliest clocks are checked immediately before
  the sole signal. The original deferred-stop list is shared with the existing
  no-signal query transport so a new stop also prevents its next command.

Readonly query transport is reused from compatible44fd69ba/49c0deaa and imports
the sole converterc895898a. Every new query retains raw streams/status and exact
PID/birth/positive wait4/group/closed-stream/resource receipts; there is no query
timeout kill. Failure before signaling leaves the original target's custody
intact. Uncertainty after attempted signaling enters the existing quarantine,
retaining/reacquiring same27:4 without any signal retry.

Receipt schema changes name this failed-helper operation and keep the successful
CURRENT118 build separate from failed cleanup. Completion is explicitly pending
Root's actual direct parent wait, closed streams and tool90401 completion. The
pure `validate_parent_join` contract requires exact parent/target births, child
returncode-9 and preserves the old readonly client's UNKNOWN status. Root must
bind the actual join receipt and fresh owner/group/FD/current physical proof before
accepting reconciliation or admitting corrected container cleanup. Neither pidfd
readiness nor this source packet invents a parent wait or creates current-free.

Root's ordered next steps:

1. Independently review this exact source/profile/dependency map. Author a current
   operation and pending-ledger supplement preserving f3b9c5d6, raw failure, UNKNOWN
   status and consumed e984 nonce; this owner-only operation consumes no build nonce.
2. Publish/fetch the exact runtime files, then fill
   `ROOT-RELEASE.TEMPLATE.NOT-AUTHORITY.json` with actual current Root operation,
   source checkpoint/publication/source review/admission and separate execution
   review. The old release remains inapplicable. Limits remain one invocation,
   one exact pidfd signal, no container mutations or record releases, CPU0/2GiB,
   same06:00Z/boot/credit caps. Source/test success supplies no actual grant.
3. After exact Root release and independent execution review, the future command
   uses taskset0/prlimit/`/usr/bin/python3 -I -B` with the fixed new source and exact
   release SHA. No timeout, automatic replay or numeric/group fallback applies.
4. Positively join the actual guard-retirement helper and original tool90401;
   independently accept preserved outputs and actual target/parent/FD/lock/current
   facts. Only then may Root separately release corrected ordinary stopped-container
   retirement in a fresh namespace. Producer/build/native replay remains forbidden.

Pure tests use `/usr/bin/python3`3.8 and substitute every effect leaf, including
all pidfd syscalls, signals, locks, process observations and transport calls. They
exercise the real rebound protocol ordering and readonly wrapper, current denylist,
UNKNOWN status, stale-proof/no-effect refusal, one uncertain signal budget,
postproof/writer custody, wrong fdinfo, parent-join contract, old-release refusal
and full process/group/client absence. No actual signal, pidfd, root command,
guard call, lock change, Docker query or cleanup has been performed here.

The exact future command shape, after Root publishes the actual release and SHA:

```sh
/usr/bin/taskset -c 0 /usr/bin/prlimit --as=2147483648:2147483648 --fsize=33554432:33554432 --nofile=256:256 --core=0:0 -- /usr/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT118-failed-guard-retirement-rebind-source-1/retire_exact_failed_guard.py --release /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261028T1911/CURRENT118-FAILED-GUARD-RETIREMENT-RELEASE-1/ROOT-RELEASE.ACTUAL.json --release-sha256 ACTUAL_INDEPENDENTLY_REVIEWED_RELEASE_SHA256 --execute
```
