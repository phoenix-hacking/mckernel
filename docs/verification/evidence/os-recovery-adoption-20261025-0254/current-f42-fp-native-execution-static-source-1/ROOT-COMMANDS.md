Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

SOURCE ONLY. These are Root's future commands after independent source review;
this file grants none. No stage, nonce, fresh resource clock or workload was
started by the source worker. Static real generic-owner/import/manifest API check
already passed; its exact result is STATIC-API-CHECK.json. Do not replay a
consumed command or replace any existing file/directory.

1. Review/publish/fetch the complete new static source, template and this handoff
   through Root's normal engineering checkpoint. Use the installed checkpoint
   wrapper, and preserve every historical file. Record actual fetched exact
   source blobs; STATIC-SOURCE-PUBLICATION.SCHEMA.NOT-RELEASED.json specifies
   the source file closure. All static publication must finish before fresh
   resource clocks. Do not copy an old publication commit/nonce/receipt.

2. With Root approval, ordinary manifest-only stage (no image/overlay build):

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/stage_manifest_only.py
```

   Creates only the new scratch/f42-fp-native1/m.json exact manifest bytes,
   empty sibling p/, and ACTUAL-SCRATCH-MANIFEST-STAGE.json. The scratch name
   must be absent; any collision is a stop, never replacement/reuse. This is
   required by unchanged generic owner._manifest_identity's scratch path guard.

3. Root generates a genuinely fresh 32-hex nonce through its existing workflow,
   substitutes it for ROOT_FRESH_32HEX below, then binds once:

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/prepare_fp_bindings.py --nonce ROOT_FRESH_32HEX
```

   Publish/fetch the actual stage receipt and STATIC-NATIVE-BINDINGS.NOT-RELEASED.json;
   record ACTUAL-STATIC-SOURCE-PUBLICATION.json with actual commit/fetched hashes
   and current unconsumed nonce. Finish independent static/source review now.
   No fresh admission clock should precede these steps.

4. Root checks no conflicting workload/lease/reservation, then runs the read-only
   fresh observation once. Preserve stdout as a new, exclusively created
   ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json (and all stderr); do not truncate
   or replace an existing receipt:

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/capture_fresh_fp_resource.py
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/prepare_fp_bindings.py --bind-fresh
```

   Both physical/account observations and the final caller must remain within
   the original boot/wall/monotonic cutoffs. The latter rejects any resource
   age >=120 seconds. Expiry requires Root's reviewed fresh successor, never
   relabeling or replacing the expired receipt. No automatic retry is granted.

5. One independent execution review of exact ROOT-EXECUTION-GRANT.PENDING-REVIEW.json:
   decision PASS_EXECUTION, reviewer other than /root, implementation_ownership
   false, payload_sha256 equal to that exact pending packet. Root alone writes
   ROOT-ACTUAL-ONE-NATIVE-FP_THREAD_STATE-GRANT.json from the generated
   ROOT-GRANT.TEMPLATE.NOT-RELEASED.json, with decision
   GRANTED_ONE_EXACT_NATIVE_FP_THREAD_STATE, maximum_invocations1, same exact
   nonce/argv/resource reference and exact independent-review reference.

6. Root dispatches this UID1000 direct-wait capture once under the reviewed
   generic owner/container resource profile:

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/run_native_fp_capture.py
```

   Its exact child argv is already the static template's generic owner argv:
   taskset CPU7; prlimit FSIZE32MiB/AS2GiB/core0; sudo -A; pinned owner45010;
   exact staged manifest/fresh nonce/empty parent. No outer wall/grace kill.
   CAPTURE/STARTED.json, stdout, stderr and JOINED.json preserve actual caller
   identity, argv, direct wait, CPU/RSS and start/finish. Root retains its genuine
   parent/tool join and owner/container/guest/child joins independently; no
   source worker infers or fabricates those receipts.

Acceptance remains the unchanged generic evaluator and original FP oracle:
254 exact stdout bytes, stderr0, exit0; original argv/env/cwd/caps; actual AVX
XSAVE/OSXSAVE and XCR0 bits0/1/2; two overlapping workers on one inherited
actual CPU; 16 YMM/64 lanes and64 rounds each; distinct TIDs and restored x87/
MXCSR. Exit77 fails the prerequisite. Preserve ordinary matched-TGID syscall
trace, exact one final231, no sampled60, worker slots0/1, guestCPU0. FP is not
added to BEGIN_PROCESS_CASES. Exact BEGIN identity requires intent0/ACK0 and
final genuine retirement0; ACK0 is not retirement. Empty procfs, error scans,
QMP shutdown, guest reaping, full owned teardown, direct caller and genuine
parent/tool joins are mandatory. Missing final retirement0 remains FAIL even
if frozen collector c020 captured early at first procfs-empty. Root independent
actual review must inspect these values; source/API success gives no native
or whole-file language-retirement credit.
