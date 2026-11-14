# Independent source review: ten-minute steering

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Verdict: PASS_SOURCE for the frozen queue-only timer and its parent launch profile; no source-code blocker found. The author's TEST-RESULT.json reports14 pure fixtures PASS/.128s/exit0 and CPU0 released. I read that receipt and reviewed the sources, but did not execute tests, monitor, queue API or any live/root/workload operation. Parent owns launch.

Reviewed sources:

- `steer_every_ten_minutes.py`: SHA256 `231af6003652e9596c35415823cda65178978e8569842e6903869a3af4e4373b`.
- `test_steering.py`: SHA256 `11357ccdc4909ff993ff3d3741b75034dc8e81a3d55963ef1060ffa58bf7e072`.
- Existing `run_os_goal.py` queue/helper definitions and resident delivery guards: SHA256 `009d00f1aa2c07d0d4c50fd1eace64c1a04afe8d33a0b691968b877d4310b3f5`.

The timer imports only standard-library modules and extracts only the existing `utc`, `atomic_json` and `queue_instruction` function bodies. The selected call supplies no capture-progress argument, so the existing optional registration branch and its additional dependencies do not execute. The extracted queue API only persists a bounded pending instruction; it does not start a launcher/server, call inference, resume/restart a campaign, change a model, mutate native resources or start a workload. Resident delivery separately requires a controlled active goal/turn and no checkpoint/stop condition.

`decision` stops for changed thread/goal, paused/nonrunning phase, holds/policy error/checkpoint/stop, invalid or stale heartbeat, missing launcher IDs, changed journal thread, ambiguous durable intent, prior stop or clock rollback. A fresh read and backlog check repeat after snapshotting, including worker/server/log-directory identity comparison. Pending or sending queue items suppress additions. The600-second interval is durable; a queue exception or crash after intent cannot silently replay on restart. The monitor holds only its private flock and never unlinks campaign/native locks.

State reads are capped at1MiB. Each observation reads at most8192raw bytes from each of the two selected log files and retains current/previous snapshots. Event history rotates current/previous files at the1MiB threshold; only queue/backlog transitions/stops are logged, not every15-second poll. The instruction is bounded by the existing8192-byte queue API and explicitly preserves active-thread-only, hold/pause, native ownership, resource and physical acceptance rules. It requests M14/P12 parallel progress under existing reviewed controls and grants no automatic workload or retry authority.

The staged fixtures cover due/cadence/rollback, paused/stopped/completed goals, holds/policy errors, stale/future/invalid heartbeat, state/goal thread changes, durable intent/uncertain nonreplay, actual existing queue persistence in a temporary campaign, pending/sending backlog, and pause/thread changes during snapshot. The author's retained TEST-RESULT.json reports14 PASS/.128s and binds main231af600/test11357ccd; this reviewer did not rerun them. Main-loop/process-receipt/event rotation, optional stop helper and a live timer are not exercised by these fixtures; do not claim them as tested.

Known narrow limitation, already explicit in source: the existing queue API has no atomic compare-thread/phase parameter. A final-moment thread/pause change can leave one already-persisted pending instruction. The request itself names the exact thread and forbids acting/resuming after change; the post-submit check stops all subsequent timer submissions, and the resident dispatcher does not deliver to a paused/stopped goal. This is not a promise that no item can be persisted during that race, nor authority to replay/remove it automatically.

The final main also records PID birth/boot/script identity and refuses a retained explicit private stop request on startup; these main-only additions are source-reviewed here, not runtime-tested by the decision/step fixtures. The optional stop_supervisor.py uses pidfd plus recorded boot/birth/UID/script checks and targets only that exact monitor; no PID fallback, workload/campaign signal or helper execution is supplied. Its source-only status does not delay the separately authorized queue-only monitor.

TEST-RESULT.json SHA256 `862e2d6ae3cf88a1b6af4ae06fa29315ec8c5d332460f868d3e0fed3a0e9676f`; LAUNCH-PROFILE.json SHA256 `6f680c591ba617f2353feae41de7f5243c00d82e69e67dd35a10bfdb9437c29d`. The launch profile fixes CPU0/256MiB AS/128FD/core0/32MiB FSIZE, with unlimited inherited lifetime CPU time so a long-lived sleeping timer is not mistaken for a60-second fixture. Author must re-freeze SOURCE-MANIFEST.json after this review update; no executable source change or new test cycle is required.

Proceed with the parent-owned exact reviewed launch. The current healthy workload must not wait for this timer. No canonical source change is required by this review.
