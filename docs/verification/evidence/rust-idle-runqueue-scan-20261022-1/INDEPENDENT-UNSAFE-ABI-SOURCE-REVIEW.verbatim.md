PASS for integrating the exact private source changes onto matching preserved preimages. No blocking unsafe/ABI finding within this source and extracted-body review.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

- In `idle()`, `runq_lock` covers traversal and the resulting CPU status update. Existing IRQ handling, halt gating, FP fixes and post-switch cleanup remain unchanged.
- `sched_idle_runqueue_has_running_result()` checks the sentinel before deriving a thread address, uses C-produced offsets and four-byte `CInt` status reads, and tests exact equality. `spin_sleep` and combined status bits cannot independently count as running. It creates no Rust references, retains no pointers, mutates nothing and introduces no ownership transfer.
- Existing runqueue insertion/removal and scheduler exit paths support the supplied locked, live circular-list precondition. Volatile reads provide observations; they do not add synchronization or corruption recovery.

I verified all **110 retained hash entries**, the shared test hash, and exact correspondence between retained generated code and the proposed Rust body, selected C bridge and original C loop. Raw attempt-2 evidence records successful selected/fallback compilation, linking and execution of 80 cases plus alternate-layout checks. The Rust object’s retained disassembly contains integer instructions and its undefined-symbol output is empty. I did not rerun compilation or execution.

Accepted postimage SHA-256 values:

| File | SHA-256 |
|---|---|
| `kernel/process.c` | `910771e0908d3fc69fcad13e94a2f0da13a964ce0293911fa2dcd5180b6e9ca7` |
| `kernel/rust/sched_helpers.rs` | `8b5c15fe52c59964105561d560bca5c648464872a44ead44b672e180c44acbd1` |
| `kernel/include/sched_helpers.h` | `15e506c4a6e6bd359e704a29e89bff20ea65a14ea69f24171aeb43024847d474` |
| New test | `982f7f273930a54658fcd07f00ac05829790980f6d40b85eb930cac909cf4d14` |

[Exact patch](/home/holden/mckernel-work/host-preparation/rust-idle-runqueue-scan-20261022-1/source.patch) · [Evidence hashes](/home/holden/mckernel-work/host-preparation/rust-idle-runqueue-scan-20261022-1/final-sha256.json) · [Test](/home/holden/mckernel/scripts/tests/test_rust_idle_runqueue_scan_20261022.py)

Acceptance covers source integration and retained extracted-body behavior only. Actual production-TU ABI assertions, pinned full-source build, default linked-image selection and native idle behavior remain required before claiming path retirement. The retained SSE2 target warning is visible; the inspected integer-only object does not establish whole-crate ABI acceptance. Preserve the accepted `cbb04` private image/stage unchanged.
