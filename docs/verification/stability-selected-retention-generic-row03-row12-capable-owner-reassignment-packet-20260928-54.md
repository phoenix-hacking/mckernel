# M01-B capable-owner reassignment packet 54

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. Packet52 and its independent
review remain the complete design authority. Attempt52 passed provenance but
failed independent handoff review because its cheap implementation owner left
five explicit packet52 obligations incomplete. This packet does not redesign or
weaken those obligations. It changes implementation strategy to one coherent
capable owner and a fresh root, as required after the escalated candidate failed.

Bind these exact inputs:

- packet52 SHA256 `846605e3c35c48e65ff892ae65ec67182eee1c5e38a43f3d5e83e651aa968568`;
- packet52 review SHA256 `827aa3d059eced6de524441acdc30cedd7482b44de9300bb86f3d46fe4a4df39`;
- attempt52 handoff SHA256 `56337ddd4cd7d76d46f0c6470e5ecf2427f5928b8055b03863a2c324f4ba4ab9`;
- attempt52 archive SHA256 `e29e3b8f47e2dd9572e3d4826c466ef50b05be0744b734c3c00cd397330c3c54`;
- failure review53 at
  `docs/verification/stability-selected-retention-generic-row03-row12-phase-i-handoff-review-failure-20260928-53.json`.

Preserve roots48/52 and both archives byte-for-byte. The fresh root is exactly
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-54`
and must be absent/canonical before creation. After independent packet release,
stage both modes with packet52's exact two commands, authority roots and creation
allowlist. The only content-edit allowlist remains the same five files per mode.
No production checkout, stager, template, authority, prior root or packet byte
may change.

The capable owner must implement packet52 as a single coherent boundary, not
patch only review53's line numbers. In particular it must:

1. establish common baseline fixture/observer address counts 2/1 without a
   contradictory assertion;
2. take a new strict observer begin/end sample at every required checkpoint,
   validate sequence/matching END/unique complete fields, and use the actual
   emitted release/released/address counters rather than defaults or fixture
   substitutions;
3. use complete `verification_mailbox` Rows and assert every named pre-return,
   prepared, row03 close/quarantine/destruction/drain and row12 phase/publication/
   explicit mailbox-destruction/drain invariant from packet52;
4. implement detecting branches that increment prohibited-address and duplicate-
   release attempts before rejection, with distinct deferred/quarantine insertion
   totals and current lengths;
5. compare the complete 128-byte callback packet to the exact otherwise-zero
   expected bytes, while continuing to assert that the callback is not invoked;
6. preserve the already correct generic Vec, explicit drop-before-deallocation,
   status hook, no-backing-read and cfg(not(test)) erasure properties.

Before handoff the owner must produce a requirement-to-source assertion map for
every packet52 named field and sample, in addition to packet52's canonical
handoff schema and static/in-memory inverse checks. Pattern presence alone is
not a pass: no same captured field may be required to equal contradictory values,
no missing parse may default to a passing value, and every row must compare full
snapshots with only its explicitly permitted deltas.

At the first failure create only the exact six-field failure file and stop;
never repair in place or retry. Success still requires independent complete
handoff review. Compilation, Phase II, candidate execution, native/guest runtime
and all acceptance remain prohibited.
