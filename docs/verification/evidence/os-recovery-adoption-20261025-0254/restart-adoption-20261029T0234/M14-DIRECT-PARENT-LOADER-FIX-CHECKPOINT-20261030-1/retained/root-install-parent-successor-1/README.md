# Direct root parent for install-only operation — source candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is a source-only candidate, not an operation release. The previous drafts,
nonce outcomes, controllers, native ownership and holds remain unchanged.

The fixed post-sudo bootstrap hash-loads the parent and the child successor's
fixed entry/closure; its stdin is exact fresh canonical phase-zero admission.
The same root parent forks the keeper, which forks the waiting installer. The
keeper transmits its actual lease open-file-description and installer pidfd over
an inherited private Unix seqpacket socket. Each message is bound to kernel
per-message credentials and the nonce; the parent registers all received
handles before acknowledging. It verifies the held lease against the sealed
release and sends release-bound GO_AUTH only after the fixed direct-child
verifier rechecks actual controls and source facts. GO remains a separate
keeper action. No pathname reopening can substitute for the transferred OFD.

After the keeper's actual installer wait and durable result/captures, the
parent verifies the published files and proof, ACKs custody, then checks the
keeper's direct wait and the same installer's pidfd terminal state. It owns the
lease and success proof throughout. `serve` retains the operation indefinitely
unless the fixed verifier confirms the original conditional operation-only
retirement authority; a single lease close is recorded as CLOSING then either
VERIFIED_CLOSED or CLOSURE_UNKNOWN with no retry. The external Root caller
must capture the final result and positively join the parent. No native release,
current-free claim, or global descendant proof is produced.

The parent arms a bounded in-process SIGALRM to interrupt ordinary blocking
work at the stop cap and attempts pidfd TERM/KILL before journal work. It masks
SIGALRM and configured stop handlers only over acquisition-to-registration and
close dispositions. An uninterruptible syscall, parent death, lost handoff or
unobserved join remains UNKNOWN; the external Root caller must have durably
reserved the operation resources and capture before launch. If the keeper dies
before lease ACK, the parent has no claim to an unreceived lease. The three
operation roles and aggregate 4 GiB plan do not account for the actual sudo
frontend/monitor; Root must measure and review that host-control overhead and
narrow the invoking unprivileged driver's own affinity to CPU 6 before sudo.

`PROFILE.SOURCE-ONLY.json` contains the exact proposed argv, with its Python
literal at index 16 and CPU operand at index 4. Root must independently review
both the exact parent/child closure and the real resource/operation admission,
provide fresh one-shot admission and actual controls/usage/source-review bytes,
and bind no-replay nonce and capture custody. No root execution, installed
source, fresh nonce, proof or physical ownership is asserted by this packet.

Existing `parent-control-0001` already passed five unchanged protocol tests;
do not rerun them. The proposed changed-source-only synthetic check, after
Root's light-test admission, is:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-1/test_parent_source.py TestProfile TestRetirement
```

These mocked tests perform no real fork, signal, pidfd, or root operation. They
are unrun. Python 3.8 AST parsing passed for the four parent Python files.
