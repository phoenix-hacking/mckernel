# McKernel: finish M14 and M15

The user stopped the previous work loop to simplify its harness. The live state
is shown in the tracker below. Do not restart automatically. The explicit run
command continues the existing saved Root; it does not create a replacement.

## One goal

Get the supported OS booting, running useful applications and shutting down with
its resources restored. Complete every original M14 and M15 requirement using
that functional evidence. M14 final acceptance precedes M15 final acceptance.
After both acceptances, checkpoint and pause the larger saved goal.
Functional OS/apps and Rust/allowed assembly only; **NO SECURITY TESTING**.

Use this file and [the live open-deliverable tracker](../docs/verification/M14-M15-OPEN-DELIVERABLES.md)
as planning context. Read source/captures for the named deliverable as necessary.
Historical conversations, old plans and private publication/review/catalogue
chains are not the default work plan. Preserve their actual evidence and holds.

## Direct work loop

1. Pick the next ready original check and its smallest missing functional result.
2. Reuse passing source, builds, providers, ABI checks, installation and tests.
3. Assign disjoint engineering to existing owners with `followup_task`; use up to
   eleven useful lanes, depth1. Each assignment names its original check, inputs,
   repair/operation and required passing result.
4. Run the operation. Diagnose real failures and give the existing owner a bounded
   repair. Keep independent ready work moving. Do not repeat inventories or green
   work, add optional scaffolding, or mistake a review for functional proof.
5. Record evidence once, update that check's engineering progress and any fully
   satisfied original acceptance, then immediately feed ready successors.

The dispatcher is **GPT-6.1 Sol/MAX** and actively helps failing workers. Every
new worker/reviewer is explicitly **GPT-6.1 Sol/xhigh**. Target at least90% agent
work on implementation and affected functional verification, at most10% on
bookkeeping. This is an allocation priority, not a fabricated measured ratio or
an automatic stop rule. If all remaining work genuinely needs an unavailable
input, checkpoint and report the exact blocker instead of spinning.

## Progress that stays visible

[**M14-M15-OPEN-DELIVERABLES.md**](../docs/verification/M14-M15-OPEN-DELIVERABLES.md)
lists **every remaining original check** with its own verified acceptance,
parent checklist percentage, evidenced engineering checkpoints or unknown,
owner/status, passing scope and next missing original proof.

The original source of truth remains
`docs/verification/m14-m15-closure-progress.json`:156 original checks, original
criteria/weights unchanged. The small engineering sidecar is separate. Activity,
line count, repeated reviews and build success alone do not grant acceptance.
Every assignment must advance a named deliverable; percentage increases require
completed, evidenced increments. Status/watch render all open rows without model
calls. Current baseline:112/156 accepted,44open; M14=80.19%,M15=76.25% verified.

## Commands

From `/home/holden/mckernel`:

```sh
python3 -B scripts/m14_m15.py status
python3 -B scripts/m14_m15.py watch
python3 -B scripts/m14_m15.py agents
python3 -B scripts/m14_m15.py run
python3 -B scripts/m14_m15.py stop
```

`run` is the explicit user start and opens the live agent roster and combined
agent log, while updating the milestone Markdown. `run --no-watch` only submits
that start. `agents` opens the same read-only live agent view without starting
work. `watch` displays every open check and updates the Markdown on changes;
Ctrl-C closes either viewer. `stop` stops new dispatch, pauses the saved goal and
interrupts the campaign's active model turns through their existing owner.
It preserves files, builds, credit accounting and runtime ownership. A retained
controller can remain alive to preserve custody; that is not ongoing dispatch or
proof of guest/container cleanup. Inspect `status` for incomplete interruption.

The standalone detailed agent log also remains available with
`python3 -B scripts/watch_os_agents.py`.

## Start from the work already done

The qualified image, paired modules and changed library are built; **reuse them**.
Their exact hashes, recipes and persistent local cache are in
[the reuse handoff](../docs/verification/m14-m15-build-reuse-20261115/README.md) and
its `ARTIFACTS.json`. Image34478838, modulesff9c6239/08c1f2fc and F05DSObb29f28b
are passing build increments. The authenticated43-file cohort stage is qualified.
Do not recompile these or regenerate ABI witnesses to rediscover their status.

The next useful result is the actual matched native run and its cleanup proof.
Reuse its results across eligible integration, perf, executor, library, tool and
monitor obligations. XPMEM production lifetime/termination wiring remains
incomplete and unselected; its real held-provider boundary is not resolved by a
private helper. The tracker names each remaining proof.

## Necessary boundaries

Keep Root `01a18bc3-e072-7810-9426-75101b0856c0` as sole integrator/native executor.
Preserve finite cumulative credit run `7c6ef3604bfb4008a917bba8cfb6cfaa` and ceiling
`52079.8011050000`; no accounting reset, purchase or account/model workaround.
Preserve actual account/service stops, uncertain delivery, native/source/lease/
IPC/scratch21/UNKNOWN holds and excluded rejected work. Never replay the excluded
signal-frame collector worker01a1c48d/turn01a1ce01 or denied e015/proc2685747 scope.

Use measured resources: HOST CPUs0,6,7; selected28GiB TOTAL includes18GiB retained
non-HOST reservations and10GiB HOST work, all controllers/workers/containers and
retained charges together. Preserve at least2GiB for the OS and existing disk
floors. Dispatcher may adjust aggregate limits to actual headroom; do not multiply
quotas per agent. Native CPUs2-5/12GiB require actual one-owner admission. Retained
HOST baseline4697620480B/jobs4 and other actual holds stay charged until their
own positive closure; empty process lists or a stopped model do not release them.
