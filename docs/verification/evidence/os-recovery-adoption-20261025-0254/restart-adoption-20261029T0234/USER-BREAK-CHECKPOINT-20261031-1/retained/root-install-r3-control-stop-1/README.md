# R3 current control stop and pre-stop metadata — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is an unexecuted, narrow successor of the earlier reviewed control-stop
pattern. It targets only Root Python PID 3121867/birth 120224742, under retained
caller 3121863/birth 120224717 and sudo 3121864/birth 120224735. The failed
keeper identity is PID 3121868/birth 120224750. The source does not signal the
caller, sudo, other Root, watchers, native owners or any process group.

Before signaling, it binds the exact R3 nonce, reservation, request, argv,
Parent5 bootstrap/body, stdout/stderr capture inode identities and the exact two
canonical failure DATA records. It checks the actual process chain, pinned
system interpreter/argv, one Root thread, no current children, no R3
operation/code directories, and every current Root FD. Allowed source leaves
must still match the exact pinned source hashes and inodes; unlisted FDs refuse
the operation. The one retained pidfd must have kernel `Pid=-1` and `NSpid=-1`
in the same PID namespace. Its keeper attribution is explicitly based on the
source-bound Parent5 single-keeper ChildRecord and the captured two failure
records; the original keeper direct-wait status remains **UNKNOWN**. It never
reads process memory, environment, credential material or unrelated children.
The metadata and capture hashes are written and fsynced to the new Root-owned
operation capture before any signal, then all target facts are rechecked.

Only after fresh independent review and actual Root one-shot release does it
open an independent real target pidfd, verify its FD type, CLOEXEC and current
fdinfo PID, and use pidfd-only TERM followed by bounded KILL if necessary.
The helper reports terminal polling and its own pidfd close disposition; it is
not the target's parent and cannot assert a direct wait. Ambiguous handle or
close disposition remains UNKNOWN without numeric-FD retry. No reference to an
old `/usr/bin` mode is used; the separate legitimate mode repair may change it.

The original DFD nonce's UNKNOWN 4-GiB reservation, this R3 UNKNOWN 4-GiB,
native12, V2 UNKNOWN2, scratch21 and mutex27:4 remain charged. The source never
retires a reservation, infers a keeper wait result, or claims native current-free.
Root's existing R3 caller must independently wait its owned sudo child and the
Root session must join the caller before later reconciliation. The reviewer must
separately assess any process-memory-only rule after those actual observations.

The source-bound profile uses sudo-A, CPU6, system Python, 64-MiB AS, 5 CPU
seconds, 128 FDs, no network and no helper fork. Root must independently review
the exact source and current resource ownership, supply a fresh held regular
stdout capture and create a one-shot actual canonical release with the exact
fixed fields in `control_stop.run`, plus actual controller/capacity hashes,
weekly usage/observation, no-new-rejection status, fresh BOOTTIME issue/expiry
(maximum 30 seconds), MONOTONIC expiry and UTC cap within inherited limits. The
release path and hash are the profile's final two argv elements. The Root session
and independent operation review supply authority; a JSON status alone does not.
Root must preserve consumption and UNKNOWN for uncertain dispatch and never replay
it.

System Python 3.8.10 compiled the three source files. The one focused failure-note
binding mock is unrun. No signal, root operation, workload or cleanup was run by
this worker; this packet is not a release.
