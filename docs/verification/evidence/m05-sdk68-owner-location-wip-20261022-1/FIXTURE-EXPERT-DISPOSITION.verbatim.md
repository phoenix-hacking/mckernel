Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**Decision: block acceptance of the exhausted fixture family. Authorize one newly prepared helper-only observation after the following repair is independently checked. No execution occurred during this review.**

Concrete findings:

- [test_owner_source_binding.py:16](/home/holden/mckernel-work/host-preparation/m05-sdk68-final-consumer-check-20261022-1/test_owner_source_binding.py:16): `endswith()` matches both owner and test paths, copying owner bytes into the fixture test. Replace both role selectors with exact full-key mappings. Keep the test pin `7076a5e1…`; do not refresh pins to accommodate incorrectly copied bytes. I independently confirmed the repository test hash, both erroneous fixture hashes, and every `FINAL-REFS.json` entry.
- [correction failure:9](/home/holden/mckernel-work/host-preparation/m05-sdk68-final-consumer-check-20261022-1/HELPER-CHECK-CORRECTION1-FAILURE.txt:9): dependent execution continued after preparation failed. Use sequential dispatch gated on successful preparation, or checked subprocess calls that propagate failure. Preserve the original failure; no downstream command may run after a failed prerequisite.
- [test_owner_source_binding.py:12](/home/holden/mckernel-work/host-preparation/m05-sdk68-final-consumer-check-20261022-1/test_owner_source_binding.py:12): the retained directory correctly prevented reuse. Create one fresh, explicitly owned attempt directory with exclusive creation; never remove, overwrite or reuse the failed fixture.
- [test_owner_source_binding.py:20](/home/holden/mckernel-work/host-preparation/m05-sdk68-final-consumer-check-20261022-1/test_owner_source_binding.py:20): the test supplies `__file__` and compilation filename independently of the file parsed. For truthful helper provenance, first copy and verify the cohort, then parse the **copied owner file**, compile its selected definitions with that actual pathname, and bind `__file__` to that same source origin. Report AST extraction explicitly. Any deliberately altered `__file__` is a simulated negative case.

Allowed next observation:

1. Verify unchanged input hashes and all 11 exact cohort keys before executing extracted definitions. Assert owner and test destinations receive their distinct pinned bytes.
2. Extract only `Refusal`, `need`, `safe_path`, `sha`, `validate_runtime_source_bindings`, and required literal configuration. Derive fixture `REPO` using the candidate’s actual expression and copied-file origin; execute no owner imports, `authenticate`, admission or `main`.
3. Check complete-map acceptance; missing and extra keys; deliberate executing-path mismatch; and byte drift with unchanged pins. Restore only the mutated fixture leaf using `finally`, verify restoration, and retain the attempt on failure.
4. Record hashes, code origin, explicit fixture substitutions, raw results, limits and return status. Use one attempt; stop and return evidence on failure.

This is meaningful unprivileged helper testing: the 11 repository files total approximately 380 KB. Use CPU 6, 1 GiB address-space limit, 20 CPU seconds and 30 wall seconds, with no profile escalation or automatic retry.

**Scope limitation:** [validate_runtime_source_bindings](/home/holden/mckernel-work/host-preparation/m05-sdk68-final-consumer-check-20261022-1/native_running_external_modules_owner.installed-proposal.py:651) checks location within a cohort. Because `REPO` derives from `__file__`, it does not independently establish publication at `/home/holden/mckernel`. A passing extracted-helper fixture proves neither installed-consumer authentication nor loaded dependency origins, module builds, native execution or Rust retirement.

Preserve all originals and dirty work. No root, Docker, compiler, materialization, guest, cleanup, Git, reserve, `27:4` or scratch21 mutation. Existing heavy-work limits and resource floors remain unchanged.
