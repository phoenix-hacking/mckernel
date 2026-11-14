**Decision: PASS_CORRECTION_SEMANTICS_AND_PREREQUISITE_ENTRY_ONLY. No execution release.**

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The correction fixes the demonstrated failure in `main`: `current_live_postjoin` now equals the genuine `finite_roles.guard_postjoin` descriptor, SHA256 `2f092dd706e7b1f6bb740164eda938a66ed7dcc7a92cee38a304bf878ccff357`. That retained record binds the actual CID, owner-receipt and guard-result hashes, direct guard join and root `27:4` reacquisition. It explicitly retains the container/common/shared records and denies cleanup authority. Future cleanup/postjoin fields remain null.

The unchanged prerequisite function joins that record to the current physical-retention projection, separate artifact authority, retained owner descriptors and frozen source identity. No fabricated result or substituted future cleanup evidence was found.

The [actual-entry fixture](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/check_main_entry.py) reproduces the original TypeError, passes genuine corrected inputs and rejects seven specified corruptions. It calls actual `main`, source loading, bounded reads and prerequisite joins; uid, release validation and resource setting are mocked. It deliberately stops immediately after prerequisite acceptance. [Recorded results](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/CHECK-RESULTS.json) report both entry and existing 49-refusal body checks exit 0 with empty stderr; retained output hashes match. This proves no privileged observation or physical clearance.

Exact reviewed SHA256 values:

| File | SHA256 |
|---|---|
| `PASS-CASE-STATIC.json` | `742bc4a0f829e773a3170355b8341e938494d322bc4797fd2565f8809ac69110` |
| `observe_current_pass_image_retirement.py` | `4e2360edb61802b9c5ea87af04a725d04708311899d9422f8349cdacbe377f6a` |
| `postjoin_readback.py` | `b72aa7f5306c78cfd406b79aeeccdad3a448a562f9bf36ba50298e418e8ddad2` |
| `check_current_pass_bodies.py` | `89d34e6ce532e5930cfb05de6606a7f11c1806511b9cc13e42efcffcffe89f41` |
| `readback_observer.py` | `4e82c6830428d756b58815ac028ac71b6d1705947a79f91580b22ebd1cf1597e` |
| `OBSERVER-REQUEST-DRAFT.json` | `4a2dca1e25a91b4dac070f311a2568b40a31a2434e002a40d556932ff2980777` |
| `check_main_entry.py` | `ca228e9c4da50da97d5014b98d5f6d46266897c69fe6ee95d1e5961ba211ff59` |

[CORRECTION-MAP.json](/home/holden/mckernel-work/host-preparation/m07-observer-current-postjoin-correction-20261022-1/CORRECTION-MAP.json), SHA256 `43168b3687d71671b78e4e4dff5086c492c8d4ba101abcf3123662f20e655dc6`, matches all six old/new pairs.

**Required before freezing an executable cohort:** rebind `read_original_five_metadata.py`’s summary path/hash and `export_raw_five.py`’s summary path/hash/output/tar argv. Both currently consume the old cohort. Regenerate source/data indexes, executor/operation manifests and fresh capture paths; create new independent source/execution reviews, publication/fetched-blob proof and exact release bindings. Preserve the failed attempt unchanged. No blocking semantic flaw remains in the reviewed correction itself; the old execution chain cannot authorize it.
