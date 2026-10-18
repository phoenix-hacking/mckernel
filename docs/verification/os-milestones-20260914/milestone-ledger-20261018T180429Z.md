# Milestone ledger baseline

Saved 2026-10-18T18:04:29Z. Four-hour comparison target: **2026-10-18T22:04:29Z** (15:04:29 Pacific on October 18).

This preserves the table reported in chat. The ranges are low-confidence engineering estimates, not measured completion, pass rates or time remaining. Their original evidence cutoff is 16:30:01 UTC; later accepted facts below are current through 18:03:51 UTC. Changes in this table are midpoint percentage points since the saved 04:35:31 UTC baseline. M09 covers integration only; whole-kernel Rust conversion remains unmeasured.

| Milestone | Estimated completion | Increase since 04:35 (pp) | Complete practical checks |
| --- | --- | --- | --- |
| M00 | 85–95% | 0 | 0/2 |
| M01 | 55–75% | 0 | 0/2 |
| M02 | 80–90% | +2.5 | 1/3 |
| M03 | 55–75% | 0 | 0/3 |
| M04 | 80–90% | +7.5 | 2/3 |
| M05 | 55–75% | 0 | 1/3 |
| M06 | 45–65% | +5 | 0/3 |
| M07 | 65–80% | +12.5 | 0/2 |
| M08 | 85–95% | 0 | 1/2 |
| M09 (integration only) | 85–95% | +2.5 | 1/2 |
| M10 | 70–85% | +7.5 | 0/2 |
| M11 | 65–80% | +5 | 0/3 |
| M12 | 15–30% | 0 | 0/2 |
| M13 | 30–50% | 0 | 0/3 |

Accepted facts for the four-hour comparison: **20 distinct native behaviors; 9 selected Rust production/default-link paths; 8 paths with applicable native integration evidence; 6 complete / 29 open practical checks; all 14 whole milestones open.**

The newly accepted zero-length mmap behavior proves the exact failure/EINVAL/output/exit result and physical retirement. It does not establish mapping publication, leak freedom or whole-memory-check completion. The next clear_debugreg production/native proof and private save_debugreg candidate remain open.

At the comparison target, preserve this baseline and save a separate table with range-midpoint deltas and actual accepted-result/check deltas. Count implementation, test and integration evidence; do not turn preparation, activity or token use into percentage credit. Do not sum the overlapping milestone ranges into an overall OS percentage.

Estimated-range source: [16:32 table](practical-engineering-estimate-20261018T163207Z.md). Older comparison baseline: [04:38 table](practical-engineering-estimate-20261018T043803Z.md). Machine-readable ledger: [JSON](milestone-ledger-20261018T180429Z.json).

The four-hour comparison is tracked by the existing active supervisor chat; no separate background scheduler or campaign process was launched.
