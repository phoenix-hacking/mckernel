# Parent full DATA handoff — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This preserves parent2 and parent3. The only parent behavior change is a bounded
full-proof DATA handoff to its existing stdout capture, after durable full proof
and before any conditional lease close, followed by a separate disposition
record. Both records bind nonce, profile, actual root-parent PID/birth and
native-release=false. Positive keeper direct wait and installer direct wait /
pidfd terminal evidence are included in the full verified result. The helper
requires a single-link writable regular stdout capture and fsyncs exact canonical
JSONL records. A failed/short full handoff prevents close; an uncertain close is
never retried; any post-close failure reports known VERIFIED_CLOSED with UNKNOWN
outcome where the output remains available. No result implies native current-free.

The exact child4, shared protocol and inherited stop/controller logic are
unchanged. The bootstrap hash-loads the independent helper before the parent,
and the former extra bootstrap summary is removed. All four source files were
compiled with system Python 3.8.10; tests and root operations remain unrun.
The next narrowly scoped local mock check after Root light-test admission is:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-4/test_parent_handoff.py
```

Independent review and actual one-shot resource/ownership admission remain
required. A missing capture, role observation, positive join or full proof stays
UNKNOWN and retains the external Root reservation.
