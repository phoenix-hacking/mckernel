Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

RESOURCE2 EXPERT SUCCESSOR. No observer or new admission clock ran during source
repair. All original D files, including v1 intermediates, empty Resource1 JSON,
first-failure receipt and stderr traceback, remain untouched. No staging or
--nonce action is needed or allowed by this correction. Existing nonce
86c485c4719a61f118032f283a3f7e62 remains the same unused nonce; original staged
manifest, empty p/ and CAPTURE remain the same intended targets.

Before any fresh observation, Root independently reviews this source correction
and publishes/fetches the new source and STATIC-NATIVE-BINDINGS.RESOURCE-2.NOT-RELEASED.json.
Record ACTUAL-STATIC-SOURCE-PUBLICATION.json in this successor directory with
status PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS, actual verified
commit and files containing the exact SourceRefs in PUBLICATION-INPUTS.json.
The existing original publication and failure records are referenced unchanged.
Do not start a fresh 120-second clock before publication and source review finish.
This source packet grants no workload, clock extension or permission change.

Then Root's ONE new read-only observation + immediate binding command is:

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/resource-output-retention-correction-source-1/run_resource2_once.py
```

No stdout redirection is needed to retain the resource JSON. The command checks
all unique output paths absent and source/publication inputs before the first
observer call. The resource helper itself accepts explicit --output-path, rejects existing
output and output-stem-derived intermediates before any query/account/clock,
and opens all three exclusively. It persists final JSON itself and closes the
file; caller redirection is unnecessary. The batch retains helper status stdout/
stderr, directly joins it and saves RESOURCE-2-CAPTURE-JOIN.json.
On first failure it stops with retained bytes/status; it never runs a binder on
a failing observation. On success it immediately runs the data-only binder with
--resource <exact Resource2 JSON>. It creates this directory's exact pending
execution packet and grant template, binding retained JSON + capture join +
successor static/source publication. All account/cutoff/boot/physical/cgroup/
capacity/custody rules are unchanged. It does not invoke the native capture.
Do not retry unchanged or reuse any existing Resource2 output after failure.

Remaining actual gates after successful one-batch command: independent exact
execution review (PASS_EXECUTION, implementation_ownership:false, reviewer not
/root, payload_sha256 exact pending packet), then Root's exact once grant within
unchanged 120-second freshness/cutoffs. Use this successor pending packet and
new resource/source refs, preserving nonce and argv. Root actual grant file must
still be the original D/ROOT-ACTUAL-ONE-NATIVE-FP_THREAD_STATE-GRANT.json because
unchanged D/run_native_fp_capture.py reads it. Fill the generated successor grant
template using Root authority; do not overwrite old evidence. Native caller is
still the original pinned D/run_native_fp_capture.py, only after those gates.
All actual parent/tool and owned runtime joins and unchanged FP/trace/BEGIN
retirement0 acceptance remain mandatory. No native result is claimed here.

The actual helper argv composed by that single batch is exactly:

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/resource-output-retention-correction-source-1/capture_fresh_fp_resource2.py --output-path /home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current-f42-fp-native-execution-static-source-1/resource-output-retention-correction-source-1/ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-2.json
```

The batch immediately binds exactly that retained file using bind_resource2.py
--resource with the identical absolute path. Run the one-batch command, not an
additional separate helper replay. TEST-LITERAL-CLI.stdout records the 12-check
CLI regression: exact production parser/output prefix and persistence suffix;
only the marked observation body is replaced with an explicit inert producer.
Existing final JSON and either intermediate are rejected before that producer;
success retains JSON without caller redirection; literal binder CLI selects
Resource2 despite an existing empty Resource1. The production helper has no
inert/bypass flag. No account/observer/clock/Docker/guest ran in these tests.
