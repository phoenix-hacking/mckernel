# Run the complete OS milestone campaign

Preparation on 2026-09-27 leaves the campaign stopped. A later normal launcher
invocation is explicit authorization to resume; this preparation hold does not
stop that invocation. Full dedicated-computer, aggressive scheduling supersedes
older three-child/workstation scheduling numbers only; acceptance, failure-family,
evidence, isolation and cleanup remain.

For a later launch, start or resume with one command, from any directory:

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

This starts the watcher and account-metered agent work using the local signed-in Codex CLI.
It selects **Sol/medium for coordination**, Luna/low for audits, Luna/medium for
specified implementation, bounded Terra repair escalations and focused Astra/high
reviews under START.md, without model upgrades. Default `--profile aggressive`
allows up to eight children within measured host CPU/RAM and one delegation level;
no recursive dispatch. Small disjoint packets feed one dispatcher owning
integration, Git, evidence and the single heavy build/guest lease.

The objective covers all 14 milestones, 68 tasks, 130 production gates, seven
language gates and 273 catalog cases. The goal engine continues across turns.
The Python launcher observes events and persisted goal state; it does not spend
model tokens on repeated status prompts or inject a second continuation loop.
The actual dispatcher still has to obey the plan, review workers and satisfy
each original acceptance contract. A script cannot guarantee OS correctness.

The default is no time limit and no cap on eligible recovery attempts. Explicit
stops, unclassified paused/blocked goals and generic server/turn errors stop the
watcher; recovery eligibility is described below. Completion or credit exhaustion
also ends work.
Checkpoints do not end the campaign. Earlier window-ending instructions in the
saved thread are superseded when a new invocation resumes it. Keep the computer
awake and the terminal/session available, or run the command inside an existing
persistent terminal session. This launcher does not install a system service or
change sleep settings. Startup or final shutdown may add bounded overhead.

The script creates its own durable goal on the first run. Later invocations
resume that exact thread ID, preserve the exact OBJECTIVE and usage accounting, and
use a repository-wide launcher lock to reject a second launcher. Keep the older
goal in this chat paused while the launcher works; other clients do not share
this script's lock. The older goal was usageLimited during preparation.
The launcher records policy hashes. Read GOAL.md, START.md, CONVERGENCE.md and
HANDOFF.md in that order; this overrides the preserved OBJECTIVE's older
read-order text without replacing the objective or thread.

## Controls

| Command suffix | Result |
| --- | --- |
| `--status` | Print the last saved local snapshot without starting Codex. |
| `--check` | Inspect effective settings and advertised models without inference. |
| `--check-sudo` | Test the private sudo helper with `id -u`, without starting an agent. |
| `--dry-run` | Print the command, objective and settings without starting a server. |
| `--profile aggressive` | Default: up to eight children, all affinity CPUs for build jobs (currently seven), and `min(24 GiB, measured available RAM minus 4 GiB headroom)`. Effective limits are constrained by measured host CPU/RAM. |
| `--profile balanced` | Restore three children, four build jobs and 12 GiB, subject to host capacity. |
| `--max-agents N --build-jobs N --memory-gib N` | Override requested child/job/memory limits within measured host capacity. |
| `--hours 4` | Run a four-hour window, including checkpoint time. |
| `--hours 0` | Default: continue without a wall-clock cutoff. |
| `--grace-seconds 600` | Set the checkpoint reserve; default is 600 seconds. |
| `--model gpt-5.6-sol --effort medium` | Explicitly select the default coordinator. |
| `--token-budget N` | Explicitly set the goal's total token budget; omitted means preserve it. |
| `--max-restarts -1` | Default: no cap on eligible automatic recoveries; not permission to retry every failure. Use 0 to disable or a positive count to cap them. |
| `--restart-delay 5` | Initial restart backoff; doubles per retry, capped at 60 seconds. |
| `--watchdog-seconds 180` | Recover a worker whose saved state stops updating; default is 180 seconds. |
| `--heartbeat-seconds 15` | Print launcher liveness and agent activity every 15 seconds (default). |
| `--stall-seconds 0` | Default: disable recovery based on agent-event silence so healthy silent builds can continue. A positive interval enables it. |
| `--agent-windows auto` | Default: each child gets its own `gnome-terminal` window when a desktop is available; main terminal stays with the coordinator. `on` explicitly requests child windows. |
| `--agent-windows off` | Headless operation; retain per-thread logs without opening child windows. |
| `--quiet` | Hide live agent output in the terminal, retaining heartbeats and the complete readable log. |

The project `.codex/config.toml` sets a maximum of eight children. Launcher
profile/explicit overrides take precedence with the measured effective cap;
`--check` must confirm that cap and injected build environment through CLI
`config/read`, without inference. Sizing allows two remote child slots per
affinity CPU and a 2-GiB planning share per child. This host's aggressive default
is eight children/seven build jobs/24 GiB; remeasure on each invocation.
These are preparation instructions; reconcile the implemented launcher before
launch. Configuration reads do not prove actual child execution or OS acceptance.

For example:

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py --status
```

Ctrl+C requests a checkpoint; a second interrupt requests an immediate stop.
Clarification requests automatically receive the user's standing instruction to
proceed autonomously. This is explicitly identified as an automatic response;
it supplies no invented facts, selected approval option or secret. The dispatcher
records assumptions and continues other ready work when a task lacks information.
Structured `serverOverloaded`/`rateLimitExceeded`, positively classified retryable
transport failures and code 24 resume the same thread with backoff. Unclassified
paused/blocked goals and generic server/turn errors stop; a goal status alone
does not authorize recovery. Explicit stops take precedence over watchdogs.
Credit exhaustion stops further inference attempts. Unsupported
interactive protocols, invalid configuration/state and unresolved process
ownership still require repair before another run. Rerun the same command
after replenishing credits or fixing such an error. A budget-limited goal
requires an explicit adequate `--token-budget` before it resumes. A budget is
not a dollar cap or a demonstrated account-wide limit across all child usage.

## Dedicated host scheduling

Saturate useful dependency-ready work within the effective cap. Suggested slots
are four implementation/test lanes, two audit/oracle lanes and two independent
reviews, only if useful and disjoint; do not manufacture tasks to fill them.
The dispatcher owns compiler-command approval, integration/Git and the heavy
lease: one heavy build or guest at once. Bounded cheap tests may run concurrently,
sharing aggregate CPU/RAM budgets with all other work, including the heavy owner.
The launcher injects build environment variables through
`shell_environment_policy.set.KEY` and verifies them with `config/read`; these
are not a cgroup and do not grant each process its own full budget. Remeasure
host/scratch capacity before heavy work and retain free-space/cleanup requirements.
Pinned guest/privileged runtime profiles require independent resource review
before expansion beyond their historical four-CPU/12-GiB envelopes.

## Live output and heartbeat

Each child has a separate thread log; window display does not create another
agent or dispatcher. `--check` and `--dry-run` report the window backend without
opening windows or starting inference. Open windows only for useful ready
children within the effective cap (up to eight); filling all slots is optional.
Window smoke testing is separate from these configuration checks.
Each run keeps `agents/index.json` and separate thread logs beneath its log
directory; `--status` includes each observed thread's log path and window state.
Closing a viewer does not stop its agent. Actually closed/shutdown children close
their viewers after flushing output. At whole-run exit the remaining viewers
stop following and offer Enter to dismiss; a later run may open new windows.
If the desktop is unavailable or a terminal launch fails, the main log reports
the problem and the per-thread logs remain usable.

Normal runs stream timestamped dispatcher and child-agent messages, command
starts/output/exit codes, file changes, tool status, compaction and server errors
to the terminal. Child activity is labeled with its task path when available;
command output includes its item ID suffix to distinguish concurrent commands.
Partial message lines flush during streaming, before the agent finishes its turn.
Raw internal reasoning is represented by a `Working` activity indicator.

The worker prints `HEARTBEAT alive` with uptime, worker/server PIDs, goal status,
reported goal token count, and active-agent count. Each active agent also shows
its last activity and seconds since its last event. After 180 seconds of silence,
the line says `POSSIBLY STALLED`. The supervisor prints its own heartbeat while the worker starts,
waits for an RPC response, or shuts down. Its `state_updated` age measures worker
responsiveness, not agent progress. The existing watchdog still recovers workers
whose state stops updating. Heartbeats do not make model calls.

Readable output is also retained in `console.log` in the run directory printed
at startup. `--status` includes its path, agent activity snapshots, and the last
worker heartbeat time. After forced termination it reports the stopped watcher
state and labels the worker's old phase/turns as historical. For a second terminal,
use `tail -f` on the printed `console.log` path. `--quiet` still writes that file.
Full protocol events and the original server stderr remain available separately.
Console timestamps are UTC. Increase heartbeat frequency with, for example,
`--heartbeat-seconds 5`; this interval must be finite and positive.

## Watchers

The normal command automatically wraps the runner in `watch_os_goal.py`.
Recovery follows the classifications above, including eligible watchdog stalls;
an explicit stop wins even when a watchdog fires. Generic errors and unclassified
paused/blocked states remain stopped. Eligible retries preserve the same saved
thread, have no default count cap and use backoff capped at 60 seconds.
Unexpected non-stop worker death or an early exit with an active goal can also
recover, subject to the same stop/error classifications and ownership checks.
If you explicitly set `--hours`, retries consume the remaining original window
and never reset that deadline.
It keeps a separate supervisor lock and records events in
`.git/os-autopilot/watcher.jsonl`, with the latest snapshot in `watcher.json`.
`--status` includes that snapshot. The dispatcher reconciles live process leases
and retained evidence before resuming a build or guest after recovery.

A separate progress watchdog is disabled by default (`--stall-seconds 0`) to
preserve healthy silent builds. Opt in with a positive interval, for example
`--stall-seconds 3600`, to recover after that many seconds without agent item/turn
events. Heartbeats, status polls and account updates do not reset this timer.
When enabled, it captures worker/server process state, memory/load and
the last campaign snapshot to a private `watchdog-*.json` before requesting a
checkpoint and bounded shutdown. This shares the configured recovery policy
and saved thread, and remains disabled while the campaign is paused or starting.
A positive stall interval must exceed the heartbeat interval; healthy silent
commands or compactions can still reach it. The independent worker heartbeat
watchdog remains `--watchdog-seconds 180`.

A stalled worker first receives a termination/checkpoint request, with up to
30 seconds (or the shorter configured checkpoint grace) before forced termination.
Forced termination has a bounded wait; if a worker remains present after SIGKILL,
recovery stops without starting a replacement. The watcher retires only an app-server PID
whose recorded worker owner and Linux process birth identity match. It stops
recovery if process ownership cannot be established. These actions are not proof
that runtime guests or kernel resources were cleaned up.

These process-level guards cannot guarantee recovery from a host kernel hang,
power loss or an uninterruptible device operation. They do not change existing
build/guest isolation, the aggregate budget or independently reviewed profile limits.

The sudo helper supervises its credential-read child with a five-second timeout
and at most two retries for a transient read failure, timeout or killed process.
Only a complete successful result reaches sudo's password pipe. Missing or
insecure credential files are permanent errors. The watchers do not retry sudo
authentication denials, quota/budget exhaustion, completed goals or a user stop.
Every eligible recovery preserves the exact objective and retained evidence.

These watchers run while their processes and machine remain available; no boot
service is installed. After a machine restart, rerun the same command to recover
the persisted session. No time-based cutoff is applied unless you set `--hours`.

## State and recovery

State is in `.git/os-autopilot/state.json` and each invocation has a unique
`.git/os-autopilot/runs/<attempt>/` directory. The shared Git directory supplies
the lock even in linked worktrees. State and logs are local, created with private
permissions, and excluded from Git by their location. Back up that directory
and retain the local Codex session store if moving to another machine.

The dispatcher maintains CURRENT.md and the implementation evidence/checkpoints
described by README.md. Full protocol events, dispatcher text and server stderr
are retained locally. Do not send raw transcripts back to every worker or commit
them indiscriminately. The user-provided sudo credential is stored separately in
`~/.local/state/mckernel-os-goal/sudo-password`, with directory mode 0700 and file
mode 0600. The tracked launcher/helper contain only its path, so Git checkpoints
carry no password. Recreate this private file if moving to another machine.
Do not read it into agent context or run the askpass helper directly in tool logs.

The user explicitly authorized `danger-full-access` with approval policy `never`
for the standalone launcher. These settings are applied and checked on both new
and resumed threads, giving Codex full filesystem/network access without routine
approval prompts. This is the full-access combination described in the official
[OpenAI documentation](https://learn.chatgpt.com/docs/sandboxing).
The launcher changes no global Codex configuration or project trust. It disables
interactive Git credential prompts and instructs agents to use noninteractive
commands. For authorized host operations, agents use `sudo -A` with the inherited
`SUDO_ASKPASS` helper. Sudo reads the password from the helper through its private
pipe; the password is not put in command arguments or environment values. The
helper rejects symlinks, insecure file permissions and wrong ownership. Use
`--check-sudo` to verify authentication without starting the campaign.
Codex permissions alone do not grant Linux root access
or override restrictions imposed by the launcher process's host environment.
Existing OS isolation, reviewed execution packets, aggregate budgets, pinned
profile limits and cleanup contracts remain mandatory dispatcher instructions.
Unknown approval/authentication protocols are not answered with fabricated consent.

A controlled stop pauses future goal work and interrupts remaining loaded
agent turns. It never records that as proof of guest/container cleanup. After a
crash, forced interruption or quota failure, reconcile retained process identities
and runtime leases before another heavy operation. Periodic checkpoints limit
lost context; no launcher can guarantee a final Git push after power loss or
exhausted quota. `cleanup_verified: false` is intentional until OS evidence proves it.

| Exit code | Meaning |
| --- | --- |
| 0 | The persisted goal reports complete. Assess the original acceptance evidence; this is not a separate OS certification. |
| 10 | Paused/window ended/controlled interruption. No automatic retry from this status alone. |
| 20 | Worker goal reports blocked. No automatic retry from this status alone; inspect the blocker. |
| 21 | Credits/usage exhausted. Resume after availability changes. |
| 22 | Goal token budget exhausted. |
| 23 | Only structured `serverOverloaded`/`rateLimitExceeded` errors retry; generic server/turn errors, unsupported input, cleared goals and manual stops stop recovery. |
| 24 | Active goal did not continue while idle; eligible for same-thread recovery with backoff unless stopped. |
| 1 | Retry only a positively classified retryable transport failure; otherwise inspect state/stderr and repair before restarting. |

## Verified scope

The earlier validation used Codex CLI 0.153.4, its generated experimental
JSON-RPC schemas, offline lifecycle/transport tests, configuration/model reads,
and an empty ephemeral thread to inspect effective permissions. No inference
turn, paid worker, OS payload or 12-hour campaign was started during preparation.
Offline tests also exercise crash/stall recovery with real temporary worker
processes, preservation of the session ID and deadline, PID reuse checks,
automatic clarification handling and the private sudo helper. A separate
`--check-sudo` invocation passed with effective UID 0; it ran only `id -u`.
The first live run still has to demonstrate goal continuation, actual subagent
execution and available quota. The launcher retains failures if any of these fail.

The current preparation uses Codex 0.155.1 with the legacy selected models.
`--check` verifies the measured child cap and injected build environment through
`config/read`; aggressive expects 8 children/7 build jobs/24 GiB on this host,
balanced 3 children/4 build jobs/12 GiB. Preserve those choices and recheck after
integration. This preparation leaves the campaign ready for later launch and
performs no OS execution or new runtime release; existing runtime envelopes remain.
The final tests, restored environment and actual two-window synthetic desktop
probe are recorded in [LAUNCH-PREPARATION-20260927.md](LAUNCH-PREPARATION-20260927.md).

Recheck configuration after upgrading Codex. The protocol is described in the
official [App Server documentation](https://learn.chatgpt.com/docs/app-server),
and durable goals in [Follow a goal](https://learn.chatgpt.com/use-cases/follow-goals).
Required 168-hour soaks, hardware matrices and larger qualification exposures
remain part of the OS goal, regardless of how long the campaign takes.
