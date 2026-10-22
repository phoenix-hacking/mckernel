Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**PASS_SOURCE_AND_FOCUSED_UNIT_RESULTS.** No blocking finding in the seven-line `pipe_probe()` fallback or affected test changes.

The actual driver diff only derives `input_name` and SHA from `references.make_pipe_proof` when the top-level field is absent. The frozen descriptor remains unchanged. Existing file/hash, proof-content, image, recipe, child-join and pinned-make checks remain intact. Both test diffs match retained snapshots; no test methods were removed. Retirement/resource tests remain unchanged. New tests cover descriptor/map rejection, actual installed-source drift/location, MM provider rejection and reference/proof/content drift.

Raw evidence preserves this sequence:

- Original: 44 tests, 11 failures and 3 errors.
- Candidate: 49 tests, 8 failures; this log contains the missing pipe-proof refusals.
- Corrected fixtures: 51 tests pass.
- The separate real-descriptor capture, observed after the production fallback according to the dispatcher, rejects **`actual pinned make binary`**. It does not demonstrate a missing-field refusal.
- Final [suite log](/home/holden/mckernel-work/host-preparation/m05-sdk68-installed-unit-regressions-20261022-1/pipe-reference-correction-1/suite.log): 53 tests pass in 0.748 seconds, command wall time 0.916610 seconds. The [actual contract](/home/holden/mckernel-work/host-preparation/m05-sdk68-installed-unit-regressions-20261022-1/pipe-reference-correction-1/actual-contract.log) passes in 0.114886 seconds with only `/usr/bin/make`’s digest injected. Recorded bounds: CPU 0, 1-GiB address space, 20 CPU seconds, 30 wall seconds.

Independently verified current hashes:

- Driver: `3ba03f133513835fd888e0efce5866f9a574a7d649a2c4b509f2fe52fa2ed3a3`
- Owner test: `c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340`
- Offline test: `5ba949dbb61d1357c471097d0a8190ddb7c5b7976deaf558a2dbe933d7fe5b13`

Owner `96687487…` and preparation `62c869a8…` remain unchanged. The real retained proof is 4,863 bytes, SHA `462e6fd3dc0db4de7b03370d12b1c50db31156737f072b8859352a9c2ce97cf5`. Owner/driver exact68 maps and dependencies still agree with the frozen descriptor.

Remaining gates: record the refreshed CURRENT11 map before checkpoint/release. Only driver and owner-test pins change; the other nine remain unchanged. Its sorted compact JSON SHA, without trailing newline, is `28f9a79d626abbb30eb3de84c242c8514128823a410bdefe5141c040646d8954`. Bind the offline test separately because it is outside `SOURCES11`.

This accepts source and functional unit evidence only. Actual pinned-container make identity, publication verification, any separately reviewed execution release, module builds, native execution and Rust retirement remain pending. Historical fixture acceptance retains its original bytes and pins. No rerun, edits or privileged action occurred during review.
