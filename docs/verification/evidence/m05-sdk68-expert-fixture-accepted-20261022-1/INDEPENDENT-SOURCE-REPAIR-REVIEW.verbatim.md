Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**PASS_SOURCE_REPAIR — no blocker found for the expert-authorized single helper observation.** No fixture/helper execution or filesystem mutation occurred during this review.

Reviewed [fixture source](/home/holden/mckernel-work/host-preparation/m05-sdk68-expert-fixture-correction-20261022-1/test_owner_source_binding.py:24) SHA-256:
`f7a44a793a4a1e0209157444b7ca248fa79de91a7142989568970b34edbfd042`

Other exact reviewed hashes:

- `INPUT-MANIFEST.json`: `264e65fdca307251fc40fee226a3f714809bcdeb08874708d9c816d266c8bcf5`
- `FIXTURE-REPAIR.diff`: `3d4b58d8f51fa30c37653616a16fc85b02f73ee03237b6b96e6a2df62b798577`
- `SOURCE-PREPARATION.json`: `c43b9eda13ccfd40870b6e8cc82c52dffad77b0daade22cac3c5f7d81f708a3e`

Independently matched all 15 manifest inputs, all 11 role pins, the provenance’s complete expected map, and every retained `FINAL-REFS.json` entry. The diff exactly matches the retained old and repaired sources. The repository test retains `7076a5e1b8c20a0dc7bf6b12be42e884e85feaa0fdbcdf315bd49bbd1d40aab7`.

The repair uses exact full-key roles, eliminating the suffix collision. Cohort creation and copied files are exclusive; cohort/result destinations were absent. All copied bytes are checked before helper execution. It parses the copied owner, uses that pathname for compilation and `__file__`, and evaluates the original `REPO = Path(__file__).resolve().parents[1]` expression. Extraction includes only the five permitted definitions and `REPO`/literal `SOURCES`; the pinned definitions contain no decorators or owner imports.

The positive, missing-key, extra-key, simulated executing-path mismatch, and unchanged-pin byte-drift cases exercise the intended branches. Path substitution and leaf mutation have `finally` restoration; successful completion rechecks the entire cohort. Exceptions propagate, with exclusive result capture and retained fixture evidence.

Under the [expert disposition](/home/holden/mckernel/docs/verification/evidence/m05-sdk68-owner-location-wip-20261022-1/FIXTURE-EXPERT-DISPOSITION.verbatim.md), permit **one unprivileged observation only**, sequentially gated on this successful preparation review: CPU 6; hard/soft address-space limits of 1,073,741,824 bytes; hard/soft CPU limits of 20 seconds; external 30-second wall limit; isolated Python with assertions enabled. No concrete launcher command was supplied, so acceptance covers this profile and reviewed source, not an unseen wrapper. Stop on failure; no automatic retry or profile escalation.

A future PASS proves only the extracted helper’s location/hash checks within the copied cohort. It establishes neither repository publication, full-owner authentication, loaded dependency origins, module/native execution, nor Rust retirement. Source preparation alone proves no helper runtime behavior.
