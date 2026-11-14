# Practical engineering estimate — 2026-10-18 23:11:44 UTC

Low-confidence engineering estimates, not measured pass rates or whole-kernel Rust conversion. The immutable earlier baseline and four-hour comparison are unchanged.

| Milestone | Estimated completion | Closed practical checks |
|---|---:|---:|
| M00 | 85–95% | 0/2 |
| M01 | 55–75% | 0/2 |
| M02 | 80–90% | 1/3 |
| M03 | 60–80% | 0/3 |
| M04 | 90–95% | 3/3 |
| M05 | 55–75% | 1/3 |
| M06 | 45–65% | 0/3 |
| M07 | 65–80% | 0/2 |
| M08 | 85–95% | 1/2 |
| M09 | 85–95% | 1/2 |
| M10 | 70–85% | 0/2 |
| M11 | 65–80% | 0/3 |
| M12 | 15–30% | 0/2 |
| M13 | 30–50% | 0/3 |

M04 increases from 80–90% to 90–95% following independent acceptance of all three literal checks, including the Rust file roundtrip on FP image 1e7a1f68. Final-profile replay, lifecycle restoration and delivery remain separate; whole M04 remains open. M09 estimates integration only.

Measured facts: 23 distinct accepted native behaviors, 13 selected production Rust paths, 11 with applicable native evidence, 7/35 practical checks closed. All 14 whole milestones remain open. No overall OS percentage is inferred.

New evidence: [M04 literal review](../evidence/practical-m04-02-literal-check-review-20261018-2.json) and [FP Rust file native review](../evidence/practical-rust-file-roundtrip-fp-native-result-review-20261018-1.json).
