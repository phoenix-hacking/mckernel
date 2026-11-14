# Current SDK5 build/run delivery candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This additive handoff delivers the tested SDK5 tuple and its exact recorded build/run recipe for focused M13 final review. The original tested205 handoff and every failed capture remain unchanged. This descriptor grants no execution or replay.

Use `tested-artifact-identities.json` for exact paths, sizes and accepted SHA256 identities, and `exact-command-reference.json` for the original argv arrays, consumed releases, source/profile bindings and per-case commands. Existing general environment/build instructions remain in `../p-m13-01-delivered-handoff-20261022-1/BUILD-RUN-HANDOFF.md`; those historical tested205 identities are distinct.

| Current component | Accepted SHA256 |
| --- | --- |
| IHK | daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c |
| SMP | 2eb3e8e6d7e43f55ca262cb455212e205831e26980f10d4ce8ef99556fd2269d |
| mcctrl | 06e8b9b571f21b41821aa03a32ebf4ae20ae19cf4b110c3af2c81b491b92ef86 |
| McKernel image | 10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2 |
| mcexec | dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954 |
| Readiness collector | 024c1872f30fd63272ff3e6da014baffffa9fc169dd7159223888e1428a43276 |
| V3 manifest | 1fb66e1f61d92723b7191ff1464a07df2d3b131f04081a8cd9ca3fc1fc0c3c2d |

To reproduce the accepted construction, follow the recorded SDK5 request/owner operation (external make -j2), then the recorded one-init staging operation. Staging replaces only the collector in the genuine SDK5 62-member base; the other 61 member contents and metadata remain bound. Source collector mode0700 and guest init0755 are separately authenticated. The existing image, launcher, payload and SDK5 modules are reused, without a rebuild.

For runtime, the accepted mechanism consumes the fixed profile/spec/binding and separately reviewed ordered/per-case releases, through the recorded run_ten_cycles.py caller and finite ten-parent owner. The JSON command reference includes every exact owner argv. The recorded nonces and paths are consumed: a future run requires fresh names, actual identity/admission/capacity and an independent execution release. Do not run these historical argv unchanged.

The supported tested runtime is one serialized heavy container on CPUs2-5, 4CPUs/12GiB/no extra swap/512tasks/network none; the guest has4vCPU/8192MiB/2NUMA. LWK restoration tests use2prepared CPUs and128MiB. HOST holds attempt/capture outputs; immutable manifest and reusable inputs remain on scratch. Preserve16GiB HOST/12GiB scratch floors plus full measured growth/capture requirements. Scratch110GiB is observed geometry; no142GiB growth or capacity is claimed. Actual daemon default logging policy remains the observed json-file/local configuration, not a bounded16m/2 guarantee or a filesystem logging theorem.

Accepted evidence covers strict235, additive strict227 under the original criteria, one first V3 restoration cycle, and ten separately accepted full two-generation restoration/application cycles (20 applications, exact40-byte stdout each, empty stderr, exit0, EOF/procfs empty). The ten-cycle formal receipt includes exact resources/restoration and the physical receipt includes1000 authenticated owner files,300 directly reaped clients,10 container removals, final PROC absence and mutex27:4. The first cycle contributes no transferred credit to the ten-cycle quota. Raw failed observer flags, historical failures and the distinction between offline observer review and live execution remain intact. No unobserved all-child credit is inferred.

At checkpoint0a0eb01ebf7fcf75f342aef7159b15538b5fd2fd, the practical ledger is34/35 checks and11/14 whole milestones. Whole M13 remains pending focused current-delivery review. Final LONG is0/100 launches and0/60 mixed-session minutes; its acceptance reference isNULL. Whole M07 and the separate full Rust/reviewed-assembly M14 cutover remain open. This handoff makes no whole-kernel Rust conversion, long-session, seeded-workload, deferred soak/fuzz/external qualification, performance-speedup or production-breadth claim.
