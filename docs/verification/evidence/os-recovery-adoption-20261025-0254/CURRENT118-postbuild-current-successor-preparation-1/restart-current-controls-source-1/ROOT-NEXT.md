Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

`prepare_current_controls.py` constructs the current observer source successor
once actual external controls and matching reviewed cleanup sources exist. It
never imports or calls the guardian, cleanup, observer, proc, Docker or capture
leaves. It authenticates explicit BYTE refs from an exact constructor manifest,
checks source/review coupling, and exclusively creates successor files here.
An interrupted/previous output is preserved and cannot be overwritten/replayed.

Fill `CONSTRUCTOR-INPUTS.TEMPLATE.NOT-AUTHORITY.json` into a separate actual input
with the exact new guardian and its independent source review, actual
NEWSC/ACTUAL-CONTROLS-ARMED.json, matching new compatibility cleanup executor,
bindings, runtime12, SOURCE_READY, and independent cleanup source review. Reviews
must carry independent=true, implementation_ownership=false, PASS decision and
explicitly name the authenticated source refs; cleanup review must include the
executor, bindings and runtime map. Missing actual inputs are refused. The
thread_id must equal the live launcher state and its original credit-run ID.
No actual arm receipt exists at preparation time; no successor is materialized.

Source-only constructor argv, once exact actual inputs are available:

    taskset -c 0 /usr/bin/python3 -B ABS_THIS_DIR/prepare_current_controls.py \
      --inputs ABS_ACTUAL_CONSTRUCTOR_INPUTS --inputs-sha256 ACTUAL_INPUT_SHA256

The observer is copied byte-identically from source2/d216adac. Six INPUTS fields
change: guardian, shared_guard, retirement_source, retirement_bindings,
compatibility_runtime_files, compatibility_source_ready. The shared guard has
only GUARDIAN_SOURCE and THREAD assignments replaced. Every function AST,
accounting/window/caps predicate, original120s/two-probe/full recursive process,
group, FD27:4, cgroup, mount, resource and Docker checks stays exact. The shared
source remains at the same path depth, preserving its relative predecessor
resolution. The original explicit no-argument guard adapter is reused unchanged.

The compatibility executor is required to differ only in BINDINGS_SHA; its
bindings may change only guardian/output_root_parent, with the output parent
matching that executor's exact directory. Runtime12 must equal the original map
with only executor/bindings/guardian refs replaced. No cleanup policy change is
accepted here. cleanup_bindings owns that separate future source construction.

Actual custody90a0ccf3 and supplemented pending ledger3932659c are fixed inputs,
backed by actual existing pure receiptb8e5be77 (128actors/72nonces). They populate
the generated runtime-binding template. Original pending683 pin remains unchanged
inside observer INPUTS because validate_pending_ledger compares that historical
boundary to the new supplemented ledger. Old client exit remains UNKNOWN;
actual recovery/helper-parent joins are preserved and never replayed. Rejected
CURRENT118/original389 tuple checks and accepted116 remain unchanged.

The constructor emits observer, INPUTS, shared guard, exact minimal diff,
construction receipt and a runtime-binding template containing the real custody
and ledger. This remains source-only. Root still supplies actual cleanup RESULT
and direct parent join, all operation/runtime/config/capture refs and existing
independent execution release. Build STATIC-SOURCE-SUBJECTS and observer schema
from the materialized exact source using the existing workflow; old source2
subject hashes cannot describe this successor. Subsequent actual capture and
independent current-free acceptance remain mandatory. No source result releases
container/native custody or authorizes a heavy job.

Focused tests:

    taskset -c 0 /usr/bin/python3 -B ABS_THIS_DIR/test_source_bindings.py

Actual Python3.8 passed6groups in0.019900s: unchanged guard functions/caps,
required assignment/manifest/review bindings, exact mechanical compatibility
successor, stale runtime-map and cutoff-change refusal, fixed actual custody and
ledger pins. TEST_ONLY guardian bodies are never executed or materialized as
runtime authority. First test-run SyntaxError is retained and corrected. No
original source2/oracle or canonical files were edited.
