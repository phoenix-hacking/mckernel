Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

All commands below are for Root. No stage, nonce, live snapshot, grant or guest
has been created by this worker. The offline preparation already succeeded;
never replay its producer/overlay-equivalent argv.

Finish static publication before the 120-second admission clock:

1. Choose a fresh short direct scratch child, for example
   `/home/holden/mckernel-work/scratch/f02mm1`, and run
   `python3 -I -B <this-directory>/stage_strict235_manifest.py --stage-root <chosen-path>`.
   This copies only the existing bc1e08 manifest, creates its empty `p` sibling,
   and runs actual owner450 `_manifest_identity` and
   `_manifest_outside_writable_parent`, the real full manifest loader and pure
   QEMU path-length API. The manifest remains outside the writable attempt parent.
2. Choose a fresh 32-hex nonce and run
   `python3 -I -B <this-directory>/prepare_strict235_bindings.py --nonce <nonce>`.
   This binds only exact staged bytes, paths, nonce and unchanged owner argv;
   it creates empty local CAPTURE. It grants no execution.
3. Publish actual source references in ACTUAL-STATIC-SOURCE-PUBLICATION.json.
   The ready JSON contains exact source refs and the original owner/profile pins.
   No ordinary source change should consume a new native attempt or fresh clock.

Then Root obtains actual fresh admission:

4. Run `python3 -I -B <this-directory>/capture_fresh_strict235_resource.py`,
   capturing stdout once into ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json.
   It uses the unchanged prior native physical observer plus the accepted latest
   F02 actor/container identities, cgroups, one-heavy/7-job/21.7531GiB headroom,
   launcher state and empty exact paths. This is the actual admission clock.
5. Run `python3 -I -B <this-directory>/prepare_strict235_bindings.py --bind-fresh`.
   Obtain independent PASS_EXECUTION for that exact pending packet and bind
   ROOT-ACTUAL-ONE-NATIVE-STRICT235-GRANT.json with decision
   GRANTED_ONE_EXACT_NATIVE_STRICT235, maximum_invocations1, same nonce/argv,
   review/resource/pending-packet refs. No review/grant is supplied here.
6. Run the exact UID1000 entry argv in READY.STATIC.NOT-RELEASED.json.
   It retains direct Popen.wait/caller JOINED, unchanged owner450 and canonical
   account04b5 after-read guard. No outer wall/grace kill is added.

This is P-M06-01-process-exec-wait-235B: exact235B stdout, empty stderr, exit0,
successful exec/wait and ENOENT recovery, reap/ECHILD and empty guest procfs.
The old files oracle (23B/exit37) is excluded. Selected image2ed7, SMP887dc,
mcctrl57546, payload537cb, collectorC020 and launcherdca025 are frozen in the
manifest/overlay final map. Collect their actual native ACK identities before
claiming MM changed-path coverage. This does not claim all process_vm routes,
whole-file retirement, runtime page protection or production acceptance.

The worker's only executed check was the real side-effect-free API/manifest
preflight under CPU6/512MiB/30CPU/60wall. Four helper ASTs parse. No compiler,
container, stage, resource snapshot, actual nonce, live clock or Root grant ran.
