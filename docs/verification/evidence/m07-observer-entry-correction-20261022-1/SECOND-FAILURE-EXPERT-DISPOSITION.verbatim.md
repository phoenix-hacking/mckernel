**Decision: failed child closed; execution candidate rejected pending a complete inventory-schema repair. No privileged retry released.**

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The [capture records](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/cohort-actual-observer-capture-1/status.json) consistently bind child `3192325/start48096130`, direct join, exit1, closed streams and absent process group. Both retained stream descriptors and hashes match current files. Fresh unprivileged checks found the PID and group absent.

The [traceback](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/cohort-actual-observer-capture-1/stderr) establishes failure at observer `main():309`. The enclosing `finally` explicitly unlocks/closes the observer’s mutex descriptor; the unmasked traceback and process retirement support release of its own references. This does **not** prove fresh root27:4 reacquisition or grant physical clearance.

Source execution reached output-directory creation, ownership/process records and completed read-only command captures. It never reached finite metadata, observation, draft or success-result construction. Cleanup is unreachable on this path. Preserve the partial root-owned directory; I did not inspect its contents.

Blocking findings:

- [Observer `main():309`](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/observe_current_pass_image_retirement.py:309) iterates `finite_unique_paths`; the case supplies integer `88`. Lines320/344 and [postjoin lines119–120](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/postjoin_readback.py:119) share this defect.
- The current generator’s [`terminal():94–101`](/home/holden/mckernel-work/host-preparation/m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1/prepare_existing_current_terminal_sources.FRESH-CORRECTION-1.py:94) copies the malformed case without validating its consumer schema. The earlier entry fixture deliberately stops before this iteration.

Required coherent repair:

1. Produce a fresh successor case with `finite_unique_paths = sorted({r["path"] for r in finite_roles.values()})`. Preserve the separate `finite_unique_path_count=88` convention and `finite_role_count=97`; current roles derive exactly88 distinct paths without conflicting aliases. Preserve genuine predecessor binding and null future fields.
2. Validate this contract before directory creation in both generator and observer: exact types, canonical absolute paths, descriptor byte/hash shapes, consistent aliases, list equality and derived cardinalities. Expose the observer decoder for postjoin reuse; reject scalar counts rather than accepting two schemas.
3. Bind every changed case/source/helper hash and regenerate dependent cohort records. Preserve immutable originals and failed releases.

The cheapest sufficient regression runs the **generated actual observer `main()` through successful return**, writing all outputs into an unprivileged temporary directory. Substitute only privilege/host boundaries—uid/resource setting, fixture mutex identity, boot/namespace, process reads and fixed Docker/findmnt responses. Keep case decoding, receipt joins, descriptor reads, inventories, comparisons, draft construction, serialization and summary validation real. Exercise the actual postjoin finite-metadata consumer against those outputs.

Require the original scalar reproducer plus negative cases for missing/extra/duplicate paths, wrong counts/types, conflicting aliases, descriptor drift, incomplete client ledger and final inventory drift. Assert refusal stage, absence of success outputs and fixture-lock closure. No early-stop or AST-expression-only fixture suffices.

Stop after the bounded unprivileged regression and independent review. Any new observation requires fresh source publication, release, destinations and live admission; another failure requires a dispatcher boundary decision, not an automatic replay.
