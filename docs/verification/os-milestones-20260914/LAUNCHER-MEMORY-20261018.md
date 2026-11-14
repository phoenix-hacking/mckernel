# Automatic launcher memory sizing — 2026-10-18

The manual resume at06:04:29UTC stopped before the dispatcher/server started:
the wrapper pinned its automatic23.730960845947266GiB snapshot as an explicit
memory override; the worker's later ceiling was23.7271GiB. The saved goal remains
paused. Preserve that failed attempt and the retained image/container records.

The wrapper now leaves memory automatic through preflight, watcher, worker and
recovery. Each process resolves and caches its current budget. The4GiB host
reserve,24GiB aggressive ceiling, explicit override rejection, fixed agent/job
ceilings, single heavy owner and97% included-usage stop remain enforced. A real
capacity loss crossing the pinned agent/job ceiling still rejects startup.

Validation:39 wrapper tests plus121 resource/launcher/recovery tests passed.
The regression uses the reported readings across preflight/parent/worker;
restoring the old fixed-memory argument reproduces both later-stage failures.
Independent review PASS. Live preview has no launch blockers; inference remains
unstarted. No saved launcher state, evidence, ownership record or lock was edited.

Manual resume from any directory:

```bash
/home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/run_os_parallel.py --run
```

Follow [the pause handoff](PAUSE-20261018T052036Z.md) for engineering prerequisites;
this launcher fix does not release cleanup or the pending native tests.
