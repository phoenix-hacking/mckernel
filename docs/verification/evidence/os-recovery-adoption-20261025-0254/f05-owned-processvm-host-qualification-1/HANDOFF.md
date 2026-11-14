Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

SOURCE READY, UNCOMPILED/UNRUN. No canonical edits. Private directory only.

Primary app.rs directly targets F05 via raw CLONE_CHILD_SETTID and owned-child ptrace PEEKDATA/POKEDATA/readback, with8-byte page-crossing copy, synchronized stop/continue/verification, private-buffer isolation and bounded exit/reap. primary-oracle.json freezes exact stdout/empty stderr/exit0. Optional f06_processvm.rs separately preserves supported310/311 roundtrip plus deterministic flag/count EINVAL cases; its oracle is optional-f06-oracle.json. It bypasses F05 public read/write/patch and carries no F05 closure credit.

ROUTE-NOTES.md and SOURCE-EXCERPTS.json preserve original-C/selected-Rust callchains and coverage limits. BUILD-STAGING-PROPOSAL.json reuses existing static Rust profile and stage/overlay pattern, requires actual executable snapshot into the repository export before a container/guest, and matches collector/manifest stream limits at1024 bytes each. Export is proposed, not created.

Only source parsing/formatting and JSON/hash consistency were checked; rustfmt1.92 --edition2021 --check app.rs f06_processvm.rs passed. No rustc, ELF check, Linux reference, guest or canonical integration ran.

Before runtime: background owner supplies existing compiler/guest grants, confirms actual image MCKERNEL_NATIVE_CLONE_TID and selected Rust providers, and qualifies the accepted parent/child collector/evaluator. Generic native_diagnostic.py's exactly-one-schedule gate cannot establish child lifecycle; preserve it and reuse/qualify the accepted process235 evaluator. Public verify entry, partial-fault/error fixups and non-LWK mapping branch remain unproven. M14-05-05 and F05 file stay open; practical35 remains35.
