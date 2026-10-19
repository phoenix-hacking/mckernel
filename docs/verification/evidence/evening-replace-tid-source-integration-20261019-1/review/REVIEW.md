# Independent private __find_and_replace_tid source review

Decision: PASS for the narrow source integration described below. This is a source-only peer decision, not compiler/guest execution authority, production acceptance, or language-retirement credit. Functional OS/application delivery and real Rust plus reviewed assembly remain the scope; unrelated security work is deferred. No tests, compiler, guest, privileged command, Git mutation, or shared-source edit was performed by this reviewer.

## Exact reviewed inputs and integration boundary

Candidate root: `/home/holden/mckernel-work/host-preparation/evening-next-rust-teardown-20261019-1`. Reviewed RESULT.md, candidate.patch, NEXT-PRODUCTION.md, check.py, checks-1/summary.json and commands.json, frozen C logger/leaf/consumer, unchanged-helper-bodies.rs, production-process-assertions.inc, selected/joined symbol captures and leaf disassembly. Compared actual production caller/helper and dynamic-debug ABI/header.

Both frozen original source files are byte-identical to current live sources and commit `85468476a035f0528c1943e43ba041e4643be333` at this review. Source hashes:

| File | Frozen/live original SHA256 | Private candidate SHA256 |
| --- | --- | --- |
| kernel/process.c | 7c2cee5f29a659923579ef8664c8fc31d01fe2ec7e19c570dd9ac3cc2e7d18a7 | 0a45837d2e3422bb781995811353be909f77c8bb1bc88c8f46f9e1510d997e60 |
| kernel/rust/process_helpers.rs | a5ac237dc120af18ee9555874967e0da387e6c62cb92b5f054fdf00ed62a2043 | 1557abe4ff08363d3b1470295b5f6acdaba6e445f06bf9ae8fb93e5b325f1848 |

Integrate only candidate.patch's three C hunks and 56-line Rust append: guard the C diagnostic callback with `#ifndef MCKERNEL_RUST_PROCESS_HELPERS`; select an actual typed `void __find_and_replace_tid(struct process *, struct thread *, int)` declaration under that define and preserve the unchanged C fallback under `#else`; append the Rust callback/descriptor/layout assertions/public entry. Do not replace either full file from private copies. Preserve __release_tid, time_account_bridge, hash_detach_bridge, other lifecycle WIP, accepted cpu.c/process.c fixes, FP1e7 image and matching modules. No new live compute C implementation is added.

## Caller, ownership, ABI and diagnostic result

The actual selected Rust destroy_thread supplies `process_destroy_thread_replace_tid_bridge` to process_destroy_thread_body_result. That body acquires the owning process threads_lock before detaching siblings and selecting the TID action. UTI_STATE_EPILOGUE selects replacement with thread.uti_refill_tid, synchronously calls the retained C bridge, and unlocks later after the existing cleanup sequence. The sole production C bridge calls __find_and_replace_tid after the new declaration position; no prototype is injected ahead of the real declaration in the reviewed fixture. This is an existing live consumer, not an unused exported symbol.

The Rust entry retains the prior ABI (`extern "C"`, void return, Process*/Thread*/CInt), reading the same proc.tids/proc.nr_tids/thread.tid and passing the same stride/field offsets to the unchanged selected helper. Candidate assertions cover relevant Rust offsets; production-process-assertions.inc checks real C types, layouts, helper/callback/consumer prototypes and ddebug geometry after the complete real translation unit. Those real C-header assertions have not yet compiled.

All six extracted helper bodies, including checked_entry_addr, match their frozen actual production bodies. First pointer ownership match wins; equal numeric TIDs alone do not match. Each successful call clears only that slot's thread pointer, then writes its replacement numeric TID, then invokes diagnostics. Later duplicate owning pointers can be consumed by subsequent calls. Null table, nonpositive count, no pointer match and a match beyond nr_tids perform no mutation. Thread.tid, count, table identity, unrelated slots and padding remain unchanged. Valid live proc/thread and a sufficiently allocated positive-count array remain caller requirements; the leaf adds no allocation/free, lock, owner transition or reentrant mutation.

The Rust dynamic-debug descriptor matches repr(C) Ddebug (32 bytes, alignment 8; line/flags at offset24), is retained in __verbose, initializes flags to zero, and preserves the function selector `process_replace_tid_log_bridge`. The callback uses a volatile flags read and the same any-nonzero enable rule as dkprintf. Its format bytes intentionally preserve the existing spelling `has been relaced`; argument order/types and __find_and_replace_tid label match C. The callback sees pointer-clear and numeric-TID update already completed. As expected when moving the call site, file/line selectors become the Rust source file/line; old process.c file/line selectors are not preserved. Use the unchanged function selector when enabling the native diagnostic. Dynamic-debug sysfs/control integration still needs production/native evidence.

## Evidence limits and one documentation correction

Recorded bounded run: 256 cases = 2 debug states × 4 old TIDs × 4 replacement TIDs × 8 table/ownership patterns, each applying three replacements per implementation (768 C and 768 Rust calls). Both leaves intentionally share the unchanged selected helpers, so this is leaf/callback parity and explicit invariants, not an independent algorithm implementation. Source/minimal-header selected fixture has an undefined leaf reference; fallback defines C; relocatable joined fixture has exactly one Rust definition and no unresolved leaf. Extracted no-FP leaf disassembly uses scalar instructions and contains no vector/FP register use. These are useful bounded checks, not the full native production crate/image.

commands.json records exactly14 direct children, all joined returncode0, no timeout or cleanup signal, and bounded stream files. Existing preparation syntax failure and command-count assertion error remain retained; no rerun was needed or performed here.

Nonblocking documentation correction: NEXT-PRODUCTION.md calls the already-completed `python3 .../check.py` the next ordinary check. As written it cannot run again: check.py exclusively creates checks-1 (`exist_ok=False`) and stream files (`xb`). Retain checks-1; do not delete/reuse it or replay unchanged checks. The next useful observation is the production check. If a changed candidate later needs another cheap run, create a fresh evidence destination/attempt under dispatcher ownership first.

## Remaining required proof

1. Reconcile the two original source hashes before applying only the narrow patch. Preserve other leaf/lifecycle changes and fixed FP1e7 artifacts; bind new outputs to the actual resulting sources.
2. Under the separately reviewed pinned offline heavy profile, compile the actual full candidate process.c selected and fallback translation units with the real production GCC command and real headers, appending production-process-assertions.inc after the complete TU. Compile the full Rust crate with the actual native cfg/features and inherited kernel no-FP flags. No host minimal fixture substitutes for either observation.
3. Retain production symbols/relocations/disassembly and actual default image link: one selected Rust leaf definition, no selected C leaf definition, retained actual destroy consumer reference resolving to that definition, no unresolved/duplicate entry, valid debug descriptor and no forbidden FP/vector code. Preserve fallback compile evidence; do not edit unrelated three-leaf source to force linkage.
4. Use the matching newly linked image with its authorized matching modules and independent execution release/fresh admission. Exercise an actual UTI-refill owning-slot replacement; capture before/after ownership/numeric slot and continuing application/verified retirement. If enabled, capture diagnostic bytes and ordering through the function selector. Ordinary thread cleanup without reaching UTI_STATE_EPILOGUE is insufficient native proof for this leaf.

Current new acceptance credit: zero. Production-default consumer/link proof and the targeted native UTI-refill observation remain pending; source review does not authorize a privileged run or retire this path from C accounting.
