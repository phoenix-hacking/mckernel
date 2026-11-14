# Native collector blocker source review — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. This narrows the failed M02-C ABI freeze; it
does not authorize a producer change or claim native collection.

## Identity already available

`host-kernel/native-rust/mcctrl_process.rs` defines `ProcessId` as a retained
`NonNull<bindings::pid>`. `current()` and `thread()` acquire Linux TGID/PID
objects; `same()` compares the referenced `struct pid *`, while
`thread_alive()`/`group_alive()` resolve tasks under that retained reference.
This safely distinguishes Linux numeric-PID reuse. Worker registration uses
this object identity, and the independent reaper periodically closes dead
workers and detaches owners after group death. It is not an event-driven birth
ledger and exposes no guest thread generation.

McKernel `struct thread` and `struct mcexec_tid` contain numeric TIDs without a
birth sequence. `kernel/syscall.c` can reassign preallocated proxy TIDs, so a
native collector may not treat numeric TID alone as lifetime identity. Current
procfs publication/deletion observations likewise contain only numeric PID/TID.
The first single-thread fixture can bind a retained host `ProcessId` plus the
application/OS generation, but general thread collection remains blocked until
a reviewed guest birth identity is added or equivalently proven.

## Authoritative terminal path

`kernel/include/process.h` defines `process.status` and
`group_exit_status`; the latter uses an upper-four-byte confirmation flag and a
lower-four-byte exit status. `terminate()` in `kernel/syscall.c` computes
`terminate_status_result(rc, sig)`, writes both process group and current-thread
exit status, then marks the process exited. The final path calls
`finalize_process`, marks the thread exited, releases it and its VM, and
schedules away. Already-exited threads copy the retained group status before
release.

No current native application observer exports this guest terminal status and
joins it to launcher release and final retirement. Host registration observes
Linux group liveness but does not receive guest `group_exit_status`, terminal
signal or a terminal serial. Therefore the fixture-only shift-by-eight encoding
must not become the production ABI.

The smallest future producer seam is a retained terminal publication immediately
after the authoritative status writes, with a distinct later retirement event
at final process release. A reviewed record would need application/OS generation,
PID/current and main TID, encoded status and monotonic sequence. The host native
application service could consume it through the existing application ABI and
retain it across launcher release. That is a production design proposal, not an
authorized edit.

## Existing ordering evidence and its limit

Application WAIT/RET packets already carry a nonzero serial. Native host code
retains delivery CPU/trace state, publishes with Release ordering and consumes
the same serial on RETURN. Existing delivered/route/returned/worker-retired
trace records are capped by a 64-record diagnostic budget, so they cannot prove
a no-loss terminal ledger. Guest TSC accounting measures exit time but supplies
neither terminal event identity nor cross-domain synchronization. A dedicated
retained, loss-detecting terminal/birth producer remains necessary.

Primary inspected locations: `mcctrl_process.rs` lines 82-86, 122-223, 274-340,
580-634 and 820-865; `application_syscall.rs` lines 199-214;
`kernel/include/process.h` lines 492-509 and 624-638; `kernel/syscall.c` lines
148-155, 2128-2180, 5065-5103, 5315-5327 and 7434-7523; and
`smp_procfs.rs` lines 746-811.
