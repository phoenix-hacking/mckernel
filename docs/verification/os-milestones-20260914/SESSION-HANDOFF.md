# OS development session handoff

Use this concise state summary for ordinary session handoffs. Preserve the
existing blocked campaign and its goal; this file does not authorize replaying a
policy-rejected request in another session. A fresh-session launch archives the
old state and starts ordinary OS development from these Markdown files. No new
dispatcher has been launched during preparation.

The immediate priority is a functioning McKernel image and useful applications.
Defer optional security audits and hardening. Keep routine notes small, reuse
compatible artifacts and run useful independent code/test tasks in parallel.
Required machine isolation and ownership controls remain.

## Next launch and recovery

Run this yourself after reviewing this handoff:

```bash
python3 -B /home/holden/mckernel/scripts/run_os_parallel.py --run --fresh-session
```

The launcher first checks current resources, mount/controls, process ownership,
instruction delivery and exclusive leases. On actual execution it archives the
old state under `.git/os-autopilot/session-archives/`; it does not empty build
caches or delete conversation evidence. GPT-6.1 remains selected for every role,
with medium effort by default and high for difficult work. Parallel workers
share the measured resource budget and one exclusive heavy operation.

The frontend enables `--fresh-on-recovery` by default. Ordinary recoverable
crashes and authenticated watchdog stops can restart from Markdown after the
old worker/server are retired. Recovery preserves the remaining explicit token
budget and included-usage baseline. It must stop for Ctrl-C or another explicit
stop, 97% included usage, authentication/credit trouble, terminal goals, unknown
ownership or a service policy rejection. A fresh context cannot guarantee that
the service will accept a request or disable platform compaction inside a long
turn. Never use session rotation to replay rejected work.

Preparation validation: 191 launcher/recovery/resource/instruction/session tests
and 35 frontend tests passed with `/usr/bin/python3 -B` on CPU0. Tests used
temporary repositories and fake servers/workers, with no inference or OS
payloads. Live read-only admission checks found no process, lease, queue, mount
or resource-control blockers; the original stopped state was unchanged. Host
free space was 18.98GiB and scratch 17.82GiB. Remaining engineering blockers are
the image-guard reconciliation and actual guest validation described below.

## Current service blocker

The 2026-10-17 12:24:24 UTC failure occurred during remote context compaction,
before OS commands ran. The service returned `cyberPolicy`; the campaign is
stopped and its goal is blocked. Recorded worker487903/server487905 are absent.
The local stale-turn restart fix is committed at `5d500bba`; it does not change
service-side safeguards. Automatic policy retries remain disabled. Explicit
--fresh-session archives old state; --fresh-on-recovery permits fresh contexts
only for classified ordinary crashes/hangs with positive process retirement.
An explicit manual `--run` can request a normal resume without changing that
cached goal status itself. It does not guarantee acceptance by the service.

Suspected false-positive report, ready to copy into Codex `/feedback`:

> I am developing my own local McKernel OS in `/home/holden/mckernel`.
> The campaign stopped during remote context compaction before executing new OS
> work. Please review this suspected false positive and advise how to restore
> access to the affected request. Codex CLI: 0.163.0; model: gpt-6.1-sol/medium.
> Time: 2026-10-17 12:24:24 UTC. Error: cyberPolicy, remote compact task.
> Thread: 01a0a312-8c59-7c80-93de-0b64adde646b.
> Failed turn: 01a149cf-235c-7081-bc3a-17aeb5313278.

Retained log:
`.git/os-autopilot/runs/20261017T122108Z-3b2dc9aa/console.log`.
Official reporting guidance: <https://learn.chatgpt.com/docs/cyber-safety>.
No report has been sent automatically. Do not repeatedly relaunch the rejected
request or change model/access tiers to avoid the rejection.

## Retained engineering result and next work

- Source candidate `942c927b1ec93cc31284ff498455909d9bb2d0fc` produced the control
  kernel and all three native Rust modules. All original final checks passed
  diagnostic revalidation after a checker-only correction. The original strict
  build failure remains preserved; fresh-build reproducibility is not established.
- Matching `mckernel.img` compiled and linked, and its driver/owner validation
  passed. The outer image guard entered quarantine during retirement proof;
  reconcile that interrupted ownership before any guest. An absent PID alone
  does not establish accepted cleanup. Preserve the image and failed evidence.
- Once the service accepts a manual resume, continue through reviewed retirement
  reconciliation to `signal.mask-restore`: stdout
  `handled=1 observed_blocked=1 restored=1` plus newline, empty stderr, exit0.
  No new McKernel guest pass is claimed.

Read GOAL.md, START.md, CONVERGENCE.md and the current HANDOFF.md for authority;
load only relevant CURRENT.md entries, source files and selected contracts.
Keep new worker context bounded; avoid dumping historical inventories or full
logs into prompts. Fresh sessions support normal context management; leave
policy-rejected work on hold rather than replaying it in a new session. The
launcher does not disable Codex's own automatic compaction inside a long turn.
