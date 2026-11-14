# M01-B packet29 correction36 — exact handoff and final-manifest binding

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction changes
only the two packet ambiguities identified by review35. Authenticate correction34
SHA256 `61dd037ef1363b63f35e7bd29c2bd3e3c6d2e594914f621cc90d6c7b399f451c`
and review35 SHA256
`b61a5b4416c725dca11ed214961d3298a54491e8c19e3edaa08a63670e52d334`.
Packet29, correction31, correction34 and all of their nonconflicting
requirements remain normative. No implementation, compilation, execution or
acceptance is released without a new independent `PASS_PACKET` review.

## Canonical root identity

Add the top-level field `"root":"<absolute fresh root>"` immediately after
`"status":"PASS_PHASE_I"` in correction34's exact `phase-i-handoff.json`
schema. Its value must equal the canonical absolute path of the newly absent
root selected before Phase I. The field participates in correction34's exact
sorted-key, compact UTF-8 serialization with one trailing LF. No other schema
key is added or removed.

## Unambiguous final manifest

The completed Phase II `manifest.json` enumerates exactly 347 paths: 346
ordinary finalized entries, each with actual size and SHA256, including
`phase-i-handoff.json`; plus only `manifest.json` itself with kind
`externally_bound` and without a self-size or self-hash. Thus the handoff file
is ordinary hash-bound evidence, never externally bound. The sole externally
bound self-entry is the final `manifest.json`.

Separate dispatcher evidence must record the raw byte size and SHA256 of both
`phase-i-handoff.json` and final `manifest.json`. The final successful root
remains exactly 347 regular files. All early-failure roots and ownership rules
remain those of correction31.
