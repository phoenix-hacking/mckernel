# OS launcher live output validation

Scope: terminal observability, local status and bounded stall recovery for `run_os_goal.py`.
No agent inference, kernel build, container or guest was started for this change.

## Interrupted run

The retained attempt is `.git/os-autopilot/runs/20260915T031816Z-78abb831`.
Its protocol contains 22,907 notifications, including 18,300 agent message
deltas, 351 command output deltas and five distinct agent threads. Agent work
continued near interruption: a child completed at 04:12:57 UTC, the dispatcher
executed a command at 04:13:43 UTC, and context compaction started immediately
afterward. The goal was paused at 04:14:25 UTC. The watcher recorded worker
exit -9 at 04:14:27 UTC and stopped with exit 10, with zero automatic restarts.
This is consistent with the user's second Ctrl+C forcing termination; these
records do not establish an earlier server crash or a stalled model.

The original launcher wrote message deltas to its protocol log and dispatcher
transcript but did not render them in the terminal. Status polling updated the
worker snapshot without exposing whether individual agents were progressing.

## Change

- Timestamped dispatcher/worker messages, commands, output, exit codes, file
  changes, tool lifecycle, compaction and server diagnostics stream to stdout
  and a private local `console.log`. Original protocol/stderr logs remain intact.
- Partial lines flush while work is running. Buffers are bounded per stream;
  streamed message/command output is not duplicated on item completion.
- Worker and supervisor heartbeats default to 15 seconds. Worker heartbeats
  show uptime, PIDs, goal token usage, active agents and per-agent silence ages.
  Three minutes of agent silence is flagged without interrupting quiet work.
  The supervisor remains visible during worker startup/RPC/shutdown waits.
- A separate 15-minute progress watchdog detects missing agent events even when
  worker heartbeats continue. It saves process/resource diagnostics before a
  bounded stop, preserving the same thread and existing restart limit. Quota,
  fatal server errors and input-required stops override watchdog retries.
  A worker that fails to exit after SIGKILL stops recovery rather than allowing
  indefinite polling or launching another worker. Large stderr tails are drained
  in bounded chunks at shutdown.
- `--quiet` retains heartbeats and file logging. `--heartbeat-seconds` controls
  frequency. `--status` distinguishes a killed worker's old running snapshot
  from the stopped watcher without changing the stored snapshot.

## Verification

`python3 -B -m unittest discover -s scripts/tests -p test_os_goal_launcher.py -v`
passed 36 tests. Coverage includes real temporary subprocess streaming before
command completion, stderr capture, partial-line timing, interleaved named
workers, completion deduplication, failure output, bounded buffers, quiet mode,
heartbeat progress ages, supervisor liveness during a stall, forced-stop status,
and existing goal, recovery, lease and credential-helper behavior.
Actual temporary processes also exercise a worker that keeps writing heartbeats
without agent progress, ignores SIGTERM, then is killed and recovered; continuing
agent events prevent that recovery. These are isolated offline fixtures.

Replaying all 22,907 retained notifications through the renderer succeeded,
producing 4,893,890 bytes of readable output in a temporary directory, with
zero model calls. `--dry-run`, `--status`, and scoped `git diff --check` passed.
The original interrupted-run files and unrelated candidate changes are preserved.

Event handling was checked against the actual saved protocol and the official
[OpenAI App Server documentation](https://learn.chatgpt.com/docs/app-server).
The next live campaign must demonstrate the new display under actual model
traffic. No whole-OS acceptance or runtime-cleanup credit is claimed here.

The available kernel journal from 2026-09-14 18:00 local time showed no matching
OOM kill, kernel-lockup, hung-task or disk-I/O error record. Current MemAvailable
was approximately 28 GiB; host/scratch free space was 55/23 GiB. These observations
do not establish the cause of any earlier whole-machine freeze. Process-level
watchdogs cannot guarantee host-kernel recovery.
