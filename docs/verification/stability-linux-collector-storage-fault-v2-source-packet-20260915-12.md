# Linux collector storage-fault-v2 source correction packet 12

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This narrow additive packet preserves packet 11 and changes only supervisor
cleanup event schemas for its directly spawned, not-yet-reaped owner. It does not
change adopted-descendant double-identity requirements.

Because an unreaped direct child PID cannot be reused before its parent performs
waitpid, the supervisor may signal that exact spawned PID even when `/proc`
identity was never available or mismatched. It records a direct-owner signal with
exact keys `kind,pid,startticks,signal,direct_child,monotonic_ns`: kind is
`signal`, PID/time are positive exact integers, signal is SIGTERM or SIGKILL,
`direct_child` is true, and startticks is the MATCHED summary birth when available
or null otherwise. A wait for that owner retains packet 4's exact wait keys;
`direct=true`, and startticks follows the same positive-or-null rule. The summary
owner identity state and raw initial observations independently prove why null is
permitted. No adopted child signal/wait may use null or `direct_child`; adopted
operations retain packet 4's exact positive-birth schemas and two fresh matching
identity reads immediately before signal.

Source controls cover UNOBSERVED and MISMATCH direct TERM/KILL/wait with null,
MATCHED direct events with the positive joined birth, and rejection of null for
every adopted event. This representation never treats direct-PID authority as a
birth observation and never invents startticks.

No source/build/root/native/application/production gate is released without
fresh review of this exact packet hash.
