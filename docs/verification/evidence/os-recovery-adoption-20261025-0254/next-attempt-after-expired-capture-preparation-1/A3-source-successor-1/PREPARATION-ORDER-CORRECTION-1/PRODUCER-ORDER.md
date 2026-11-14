Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Cause: the preparation sequence refreshed PREPARATION-MANIFEST.external_inputs before rebinding the schema to the final observer hash. The later schema rewrite left external_inputs[16] pointing at ccc7 rather than final reviewed e90ace39. Root preserved the first static failure and original cfe manifest; no admission directory or resource clock existed.

Correct future sequence: finish typed core/frontier-input pins; rebind final observer CORE/selection; rebind and write observer schema; update materializer/capture/publication import refs; finish runtime_guard source refs; update runner runtime guard and capture GUARD_SHA; only then generate the cohort manifest file rows and external-input rows from final bytes. Refresh operation/source map and templates after those writes. Do not write a schema after its manifest snapshot.

The focused schema_first_manifest.py helper requires the schema already points at the final observer, then returns a separate manifest DATA successor changing only that schema row. It never edits a frozen source/schema/manifest, and it carries all other validated rows without another artifact hash loop. Root already completed this exact DATA correction and static PASS; this recipe is a future producer fix, not a new prerequisite, audit or actual materialization attempt.

Publication remains original227-owned accepted Q role collector rebind, not the frozen generic typed.runtime_data_rows collector. The A3 timed physical→holder→fill→held→actual independent Hot PASS→oncepublisher plan is unchanged and starts only after fixed metadata/Q publication/ColdPREWARM are complete.
