# M14/M15 engineering estimate — October25,2026

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
User explicitly requested measurement and estimates. Evidence snapshot05:09–05:10UTC;
canonical CURRENT05:06UTC plus the identified05:08:50 private M14 result.

| Milestone | Estimated overall engineering completion | Rough planning range | Implementation-only estimate |
| --- | --- | --- | --- |
| M14 | **About70%** | **60–85%** | **80–95%** |
| M15 | **About65–70%**, roughly two-thirds | **60–75%** | **85–95%** |

Confidence is low. These are supported-scope effort estimates, with explicit
judgment weights and uncertainty. Both milestone acceptance states remain OPEN.
Percentages are not measured hours, formal gate fractions, native coverage or a
completion date. Existing Rust is credited; unknown work is not treated as zero.

Measured coverage: M14 has six tracked translation units,30 behavior areas and
three final integration obligations. The current canonical HOST cohort qualifies
55 process/syscall and100 CPU providers; newer private60+100 proof is separate.
Those symbol counts are not completion fractions. M15 assesses eight former C
targets and five installed programs, reusing the three existing native Rust module
roots and shared dependencies once. Rust successor source exists for all13 known
targets. Four former C target selectors and one program selector currently choose
Rust/assembly; four C targets and four interpreted programs remain selected.
Four SDK private installs and three loader checks passed. New changed-cohort
native and whole-file retirement acceptances remain zero.

The M14 model weights implementation/focused checks/selected build-link/native
stage effort55/20/10/15. Its six complexity weights20/25/25/10/12/8 cover generic
memory, process, generic syscalls, CPU, architecture memory and architecture
syscalls. Per-file evidence/ranges are in the retained assessment. Weighted
bounds59.0155–83.26% give the approximate60–85 range. The favorable native-stage
upper bound is a historical-evidence reuse scenario, not accepted final native
proof; granting zero final native-stage credit gives59.0155–77.41% and still
rounds to roughly70% centrally.

M15 weights implementation/focused checks/default delivery/native effort50/20/15/15.
Stage ranges85–95/55–75/35–55/15–30 reproduce61–75.25%, reported roughly60–75.
Giving native qualification more effort weight lowers this to roughly55–70.
Incomplete delivered inventory widens overall uncertainty to about55–80;
conditional crash/QLMPI/UTI disposition is not silently counted complete.

Largest remaining work: finish residual behavior and callback/data ownership,
join the current Rust replacements into the actual default image/modules/tools,
qualify remaining executor/BFD/daemon/runtime-program consumers, and run matching
native application/lifecycle checks. Substantial source progress precedes these
end-to-end joins.

[Reproducible summary and retained assessments](../evidence/m14-m15-engineering-estimate-20261025-0512/ESTIMATE.json)
include measured counters, per-component evidence, stage assumptions, arithmetic
and independent method review. Preserve this baseline for future comparisons.
Update it only through a new dated assessment using the same scope and weights;
counts of symbols or tests alone do not imply a percentage gain. The campaign,
resource controls and thirty-minute steering continue unchanged.
