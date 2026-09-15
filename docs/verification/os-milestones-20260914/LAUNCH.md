# Run the complete OS milestone campaign

Start or resume with one command, from any directory:

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

This starts the watcher and account-metered agent work using the local signed-in Codex CLI.
It selects **Sol/medium for coordination**, Luna/low for audits, Luna/medium for
specified implementation, and focused Astra/high reviews under START.md. The
CLI enforces at most three children and one level of delegation. Workers get
small task packets; one dispatcher owns builds, guests, integration and evidence.

The objective covers all 14 milestones, 68 tasks, 130 production gates, seven
language gates and 273 catalog cases. The goal engine continues across turns.
The Python launcher observes events and persisted goal state; it does not spend
model tokens on repeated status prompts or inject a second continuation loop.
The actual dispatcher still has to obey the plan, review workers and satisfy
each original acceptance contract. A script cannot guarantee OS correctness.

The default work window is **12 hours**, reserving up to the final ten minutes
for the dispatcher to join workers and save a checkpoint. Keep the computer
awake and the terminal/session available, or run the command inside an existing
persistent terminal session. This launcher does not install a system service or
change sleep settings. Startup or final shutdown may add bounded overhead.

The script creates its own durable goal on the first run. Later invocations
resume that exact thread ID, preserve the objective and usage accounting, and
use a repository-wide launcher lock to reject a second launcher. Keep the older
goal in this chat paused while the launcher works; other clients do not share
this script's lock. The older goal was usageLimited during preparation.

## Controls

| Command suffix | Result |
| --- | --- |
| `--status` | Print the last saved local snapshot without starting Codex. |
| `--check` | Inspect effective settings and advertised models without inference. |
| `--check-sudo` | Test the private sudo helper with `id -u`, without starting an agent. |
| `--dry-run` | Print the command, objective and settings without starting a server. |
| `--hours 4` | Run a four-hour window, including checkpoint time. |
| `--hours 0` | Continue without a wall-clock cutoff until goal completion or a stop condition. |
| `--grace-seconds 600` | Set the checkpoint reserve; default is 600 seconds. |
| `--model gpt-5.6-sol --effort medium` | Explicitly select the default coordinator. |
| `--token-budget N` | Explicitly set the goal's total token budget; omitted means preserve it. |
| `--max-restarts 3` | Permit up to three automatic runner recoveries; default is three. |
| `--restart-delay 5` | Initial restart backoff; doubles per retry, capped at 60 seconds. |
| `--watchdog-seconds 180` | Recover a worker whose saved state stops updating; default is 180 seconds. |

For example:

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py --status
```

Ctrl+C requests a checkpoint; a second interrupt requests an immediate stop.
Clarification requests automatically receive the user's standing instruction to
proceed autonomously. This is explicitly identified as an automatic response;
it supplies no invented facts, selected approval option or secret. The dispatcher
records assumptions and continues other ready work when a task lacks information.
Quota/rate-limit errors, unsupported interactive protocols and unrecoverable server
errors stop the launcher instead of triggering a retry loop. Rerun the same
command after quota or the external blocker changes. A budget-limited goal
requires an explicit adequate `--token-budget` before it resumes. A budget is
not a dollar cap or a demonstrated account-wide limit across all child usage.

## Watchers

The normal command automatically wraps the runner in `watch_os_goal.py`. It
restarts recoverable app-server transport failures, unexpected worker exits and
stalled workers using the same saved thread. Restarts consume the remaining
original work window; they never reset a 12-hour deadline to another 12 hours.
It keeps a separate supervisor lock and records events in
`.git/os-autopilot/watcher.jsonl`, with the latest snapshot in `watcher.json`.
`--status` includes that snapshot. The dispatcher reconciles live process leases
and retained evidence before resuming a build or guest after recovery.

A stalled worker first receives a termination/checkpoint request, with up to
30 seconds before forced termination. The watcher retires only an app-server PID
whose recorded worker owner and Linux process birth identity match. It stops
recovery if process ownership cannot be established. These actions are not proof
that runtime guests or kernel resources were cleaned up.

The sudo helper supervises its credential-read child with a five-second timeout
and at most two retries for a transient read failure, timeout or killed process.
Only a complete successful result reaches sudo's password pipe. Missing or
insecure credential files are permanent errors. The watchers do not retry sudo
authentication denials, quota/budget exhaustion, blocked/completed goals or a
user stop. Default runner recovery is limited to three restarts.

These watchers run while their processes and machine remain available; no boot
service is installed. After a machine restart, rerun the same command to recover
the persisted session. Use `--hours 0` when you want no time-based cutoff.

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
Existing OS isolation, four-CPU/12-GiB resource ceilings, reviewed
execution packets and cleanup contracts remain mandatory dispatcher instructions.
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
| 10 | Paused/window ended/controlled interruption. Resume with the same command. |
| 20 | Goal reports blocked. Read CURRENT.md and retained findings. |
| 21 | Usage/rate limit. Resume after availability changes. |
| 22 | Goal token budget exhausted. |
| 23 | Input required, turn/server error, cleared goal or immediate interruption; inspect the recorded reason. |
| 24 | Active goal did not continue while idle; inspect the CLI/server before restarting. |
| 1 | Launcher/configuration/transport error; inspect state and stderr. |

## Verified scope

Validation used the installed Codex CLI 0.153.4, its generated experimental
JSON-RPC schemas, offline lifecycle/transport tests, configuration/model reads,
and an empty ephemeral thread to inspect effective permissions. No inference
turn, paid worker, OS payload or 12-hour campaign was started during preparation.
Offline tests also exercise crash/stall recovery with real temporary worker
processes, preservation of the session ID and deadline, PID reuse checks,
automatic clarification handling and the private sudo helper. A separate
`--check-sudo` invocation passed with effective UID 0; it ran only `id -u`.
The first live run still has to demonstrate goal continuation, actual subagent
execution and available quota. The launcher retains failures if any of these fail.

Recheck configuration after upgrading Codex. The protocol is described in the
official [App Server documentation](https://learn.chatgpt.com/docs/app-server),
and durable goals in [Follow a goal](https://learn.chatgpt.com/use-cases/follow-goals).
Required 168-hour soaks, hardware matrices and larger qualification exposures
remain part of the OS goal and cannot fit in one 12-hour window.
