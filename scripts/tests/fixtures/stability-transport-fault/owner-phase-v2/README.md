# Owner phase controller version 2

Source candidate only; not compiled or executed. Original owner-phase-v1 is
preserved byte for byte. The forward/inverse patches bind this narrow change.

After observing the selected RET leave, terminal owner modes now wait for the
actual launcher to become waitable with both output streams at EOF. They check
its original start ticks and waitid(WNOWAIT) result without signaling or reaping
it. The existing min(input+15seconds, controller overall90seconds) deadline is
rechecked after the final observation. OWNER_TERMINAL remains the existing
emergency-protocol phase, so failures retain the original capture/cleanup path.
The normal recovery and legacy controller modes are unchanged.

Only then does the existing Terminal ioctl take its complete typed snapshot;
the existing POST_RET ACK and five-second quiet interval remain unchanged.
This avoids capturing APP.closed while final launcher teardown is still running.
Typed APP.closed and full Terminal/+5 inventory equality remain independent
requirements. Exit status or pipe EOF alone does not establish native safety.
No expected raw exit, RET value, fault counter, owner cap or physical assertion
is weakened; parent acceptance still checks their frozen contracts.

Pinned Linux exit_files/exit_task_work precede exit_notify; a zombie group
leader remains unavailable to waiters while subthreads live. Native final
registration destruction calls Remote.close_inner, which marks the retained
quarantined app closed. Source ordering supports this boundary; actual snapshots
must establish it. The native module and phase ABI require no changes.
