# One source-only capture correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The original runner, proposal, fixture inputs, fixtures and frozen manifest remain
unchanged. Original runner b05bcc6b was blocked by source review before execution:
launch had an asynchronous ownership gap, wait reaped its leader before group
retirement, and surviving descendants were merely asserted. No compiler/test
attempt occurred, and this proposal is no execution grant.

The corrected runner replaces only the capture lifecycle with the existing exact
990807 owned_capture API and its accepted96d175 census. It gives all five same
compiler/link/test commands one28-second deadline, preserving the existing
ordinary CPU6/one-job/1GiB/30CPU/32MiB-stream/no-core/256nofile profile and root
35-second outer owner requirement. Each command persists command/started/direct
wait/direct join and whole result; stream hashes follow direct join and closed
FDs. The pinned helper blocks stop signals across launch ownership assignment,
anchors the creator unreaped during any group signaling, retires before reap,
and never sends a signal after reap. The driver stops immediately on any failed
command or unproved closure and preserves originals. It imports the read-only
pinned helper with bytecode writing disabled.

No C/Rust fixture/vector/toolchain change. As root explicitly qualified, the
finite observation covers exact complete original settid, selected C adapter/log
and Rust bodies, with equivalent trivial forwarding bridges. It does not claim
literal complete production transport-body extraction, fullcrate/image link,
production default activation, native runtime or C retirement.

Failure history: one source-level runner rejection, one bounded source correction
proposed, zero executed compiler/test candidates. If this exact capture proposal
is rejected again, escalate the concrete remaining lifecycle issue to the
reviewer/root instead of producing another unreviewed capture mechanism.
