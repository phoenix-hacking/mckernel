# Practical milestone engineering estimate comparison

Evidence cutoff: 2026-10-18T03:12:26Z. Created: 2026-10-18T03:13:55.320408+00:00.

Low-confidence engineering estimates, not measured pass rates, reliability, time remaining or a weighted whole-OS score.

| Milestone | Current estimate | Change from previous table (pp) | Gain from original baseline (pp) |
| --- | --- | --- | --- |
| M00 | 85–95% | +0 | +0 |
| M01 | 55–75% | +0 | +5 |
| M02 | 75–90% | +0 | +5 |
| M03 | 55–75% | +0 | +10 |
| M04 | 70–85% | +5 | +22.5 |
| M05 | 50–70% | +0 | +37.5 |
| M06 | 40–60% | +0 | +10 |
| M07 | 45–65% | +0 | +35 |
| M08 | 85–95% | +0 | +7.5 |
| M09 | 80–95% | +0 | +0 |
| M10 | 60–80% | +0 | +10 |
| M11 | 60–75% | +0 | +7.5 |
| M12 | 15–30% | +0 | +5 |
| M13 | 30–50% | +0 | +5 |

Since the previous saved table, accepted native behaviors increased from 15 to 16. The actual binary file-copy/reopen/readback/unlink utility and retirement passed on the existing a0f/d99 profile. Only M04 changes; this does not close M04.

All 14 milestones remain open; practical checks remain 3 complete and 32 open. Native fork/exec/wait, final matched build/replay, complete resource restoration and final integrated repeatability remain open. The third fork module build failed on Rust/C FFI declarations and retired cleanly. No credit is added for host capacity work, source-only changes or unexecuted fixtures.

Previous comparison: [practical-engineering-estimate-20261018T030255Z.json](practical-engineering-estimate-20261018T030255Z.json). Original baseline and prior comparisons remain unchanged. Detail: [practical-engineering-estimate-20261018T031355Z.json](practical-engineering-estimate-20261018T031355Z.json).
