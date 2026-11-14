# Linux collector stopped-rescue source review — 2026-09-15

Status: **NOT_EXECUTION_READY**. No command was run and no acceptance follows.

The fixed 25-case profile and the reviewed adverse setup/completed-wait design do
not include stopped collector/external rescue. Existing
`supervisor_host38.py::_rescue_worker()` acts only after supervisor timeout or
interruption and owns its private Python worker and direct descendants. The root
watchdog can clean an owned Docker container, but neither helper supplies a
reviewed identity-bound stimulus that stops the collector itself. Re-running the
accepted root profile would not exercise this case.

A future packet must use a separately named, hash-bound adverse collector and an
external stopper/rescuer. It must acquire the collector PID plus startticks from
an owned record, send SIGSTOP, verify the stopped identity/state, perform the
reviewed rescue, and retain signal actions, raw collector/container waits, all
streams/setup/events/report, watchdog and cleanup journal, procfs/container
absence and the first failure. Bare numeric PID signaling is invalid. The pinned
Docker image, UID 0, development flock, four-CPU/12-GiB limit and 40-second case,
15-second cleanup and 300-second whole-run bounds remain required. Existing
supervisor/watchdog helpers may be reused only after a separate source and
execution review.
