# Four-hour milestone comparison — 2026-10-18

Saved 2026-10-18T22:05:44Z; factual cutoff 2026-10-18T22:04:48Z. Baseline saved18:04:29UTC, comparison due22:04:29UTC. Scope unchanged.

The original [ledger](milestone-ledger-20261018T180429Z.json) is preserved. Its SHA256 was verified once against the saved baseline receipt. The comparison is a separate record.

These are low-confidence engineering estimates, not measured completion or pass rates. Deltas compare range midpoints in percentage points. Only M03 is revised; other coarse bands are held.

| Milestone | Baseline | Current estimate | Delta |
|---|---:|---:|---:|
| M00 | 85–95% | 85–95% | 0 pp |
| M01 | 55–75% | 55–75% | 0 pp |
| M02 | 80–90% | 80–90% | 0 pp |
| M03 | 55–75% | 60–80% | +5 pp |
| M04 | 80–90% | 80–90% | 0 pp |
| M05 | 55–75% | 55–75% | 0 pp |
| M06 | 45–65% | 45–65% | 0 pp |
| M07 | 65–80% | 65–80% | 0 pp |
| M08 | 85–95% | 85–95% | 0 pp |
| M09 | 85–95% | 85–95% | 0 pp |
| M10 | 70–85% | 70–85% | 0 pp |
| M11 | 65–80% | 65–80% | 0 pp |
| M12 | 15–30% | 15–30% | 0 pp |
| M13 | 30–50% | 30–50% | 0 pp |

M03 increases by a rough5points for the independently accepted partial-unmap/fault-recovery case, including adjacent-page and survivor data. Failed-invalidation ownership, cross-process/multicore behavior and broad memory qualification remain open. M09 measures integration readiness only; whole-kernel Rust conversion is unmeasured. No overlapping milestones are summed into an OS score.

| Accepted fact | Baseline | Current | Delta |
|---|---:|---:|---:|
| Distinct native behaviors | 20 | 22 | +2 |
| Selected production/default Rust paths | 9 | 12 | +3 |
| Paths with applicable native integration evidence | 8 | 11 | +3 |
| Closed practical checks | 6/35 | 6/35 | 0 |

New behaviors: closed-write EBADF and the two-page map/protect/partial-unmap case. New selected Rust paths: clear_debugreg, save_debugreg and restore_debugreg, with scoped matching-image AVX/thread evidence. This does not establish exhaustive or hardware debug-register behavior. All14 whole milestones remain open.

The FP release source, actual full compilation/export checks and image build progressed, but final link/body/descriptor acceptance is pending and is not included in these counts. Non-null FP release additionally needs the native kmsg-read prerequisite. The Rust std133B file roundtrip has accepted Linux/staging/parent evidence but no native result. Original DWARF failure/full-validity limitations remain preserved.

Selected accepted evidence:

- [practical-file-closed-write-native-result-review-20261018-1.json](../evidence/practical-file-closed-write-native-result-review-20261018-1.json)
- [practical-mapping-isolation-native-result-review-20261018-1.json](../evidence/practical-mapping-isolation-native-result-review-20261018-1.json)
- [rust-clear-debugreg-image-actual-result-review-20261018-1.json](../evidence/rust-clear-debugreg-image-actual-result-review-20261018-1.json)
- [rust-debugreg-pair-image-actual-result-review-20261018-1.json](../evidence/rust-debugreg-pair-image-actual-result-review-20261018-1.json)
- [rust-debugreg-pair-avx-native-result-review-20261018-1.json](../evidence/rust-debugreg-pair-avx-native-result-review-20261018-1.json)
- [rust-debugreg-pair-threads-native-chain-result-review-20261018-1.json](../evidence/rust-debugreg-pair-threads-native-chain-result-review-20261018-1.json)

Continue the existing30-minute monitoring loop; next full review22:17:50UTC. No second launcher or background scheduler was installed.
