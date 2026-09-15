# Resume cursor

State: autonomous execution active. M00-A preservation is complete at pushed
commit `6c0f9f81339ed3ad90a8d207cdd995184fcc625f`; all 15 source-indexed
preexisting artifacts were fetched from GitHub and independently matched by size
and SHA256. Evidence is `docs/verification/os-m00-preservation-checkpoint-20260915.json`.
The retained patch has two source-index-bound trailing-space lines; preserve its
bytes. Generated `__pycache__` files remain untracked and outside checkpoints.

Active run directory:
`/home/holden/mckernel-work/scratch/os-goal-20260915T031816Z-78abb831`.
Launcher-owned state remains under
`.git/os-autopilot/runs/20260915T031816Z-78abb831`; do not edit it.
Coordinator is Sol/medium. Use Luna/low audits, Luna/medium specified fixtures
and bounded Astra/high ownership/release review. No child may recurse. The
dispatcher exclusively owns the currently free build/guest lease. Measured free
space is 39 GiB host and 23 GiB scratch; recheck before heavy work.

Active work:

1. M01-A review found a P2 source-binding defect: the retention stager hashes
   only three Rust inputs while five ownership-critical files are presence-only.
   A Luna/medium worker owns the narrow stager/test correction; mode2 release is
   still blocked and no runtime credit is granted.
2. M02-A source audit found no collector orchestrator defect and confirmed the
   fixed 25-case order. Astra/high is checking execution release; the root run
   remains dispatcher-owned and has not started.
3. M00-B Luna/low is deriving the exact live-ledger schema and imported counts.

Next three dependency-ready tasks: integrate/review the M01-B provenance fix;
materialize and validate M00-B; run M02-B only if the exact M02-A review releases
its isolated packet. M03-A source work remains independent if either lane blocks.
No heavy process or McKernel guest is live.

Counters remain: 0/273 application cases accepted (three compiled), 2/4 narrow
fault modes accepted, 6/130 production gates and 350/10,000 points, 0/7 language
gates complete (three IN_PROGRESS). Current production remains exact baseline
module2026091301/image3 with its eight original suites; no broader acceptance is
claimed. External hardware/exposure work remains later and unavailable locally.
