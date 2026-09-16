# M01-B packet 31 — Phase I failure-ownership correction

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction changes
only early Phase I failure capture in directed implementation packet 29. It
releases no implementation, compilation, execution, runtime, guest, native,
production-gate, application, or whole-OS acceptance.

Authenticate fetched checkpoint
`353dbeb56a5ca7590516d6d9662fe36b73cde68d`, packet 29 SHA256
`7fa429e0d3e4a960d514296b7cd9fcae71a3e82285efd7513420b9837043e753`, and
independent review-30 failure SHA256
`18c99d3f3b57340addde3fc2880a4b7ba1e47d3920817b2948bcee8e738c41d2`.
All packet-29 authorities, source pins, implementation requirements, two-owner
separation, checks, hard stops, prohibitions, and acceptance limitations remain
normative except for the exact conflict corrected below.

## Exact correction

Before a successful Phase I handoff, the Rust implementation owner is narrowly
authorized to create exactly one additional global file at
`<root>/phase-i-failure.txt`, and only after a Phase I authentication, staging,
hash, anchor, ownership, membership, bytecode, or other packet-29 hard stop.
The file must be UTF-8 text with one LF-terminated `key=value` line for each of:
`status=FAIL_PHASE_I`, `mode=<mode2|mode3|global>`, `stage=<bounded stage>`,
`expected=<exact expected value or invariant>`, `observed=<exact observed value
or diagnostic>`, and `action=PRESERVE_PARTIAL_ROOT_NO_RETRY`. Values must not
contain credentials or newlines. The owner must preserve every partial file and
return immediately. It must not delete, repair, retry, start Phase II, create
any other evidence file, compile, or execute the candidate.

The exact 346-regular-file count and 345 finalized manifest bindings in packet
29 apply only after a fully successful Phase I handoff and completed Phase II.
An early Phase I failure root is intentionally partial and may contain the one
root-level `phase-i-failure.txt`; it is not subject to the 346-file success
count and can never be promoted into a success root.

After a successful Phase I handoff, no root-level `phase-i-failure.txt` may
exist. The independent Phase II evidence owner retains sole ownership of the
nine per-mode evidence files named by packet 29, including each per-mode
`failure.txt`, and the two global success-path files. A Phase II hard stop uses
only its authorized per-mode `failure.txt`; the Rust owner may not edit or
replace Phase II evidence.

For packet 29's final hard-stop paragraph, interpret “preserve `failure.txt`”
as the root-level `phase-i-failure.txt` only for a failure before successful
handoff, and as the applicable Phase II-owned per-mode `failure.txt` only after
successful handoff. These paths and ownership phases are mutually exclusive.

No other packet-29 text is relaxed or superseded. A fresh independent review
must return `PASS_PACKET` on the combined packet 29 plus correction 31 before
either phase may start. A review failure preserves both packet bytes and stops
without implementation.
