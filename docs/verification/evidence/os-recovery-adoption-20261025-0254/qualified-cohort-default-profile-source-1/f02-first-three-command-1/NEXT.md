Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

F02 can run through the ORIGINAL THREE-command runner/worker unchanged. Its
mounts() and export authentication loop accept five postimages; no literal
postimage count is enforced. The one old 'three postimage' error string is
historical diagnostic prose, not a gate. Eleven focused pure tests pass.

All five whole canonical files were copied into this directory's read-only
postimages/ snapshots only after checking the exact expected hashes. They are:
CMake f2933667, lib a05908f8, policy fefec3eb, process 9692036c, process_helpers
851acd51. The first three are unchanged baseline content; the final two are the
promoted F02 pair. Source6153 remains immutable. The same nine original objects,
retained configuration, pinned image/toolchain, Rust cfgs, process flags and
raw-link argv are reused. Only the whole Rust and process objects are newly
compiled before the same eleven-input link. This is a NEW source cohort, not
replay of BUILD3's already successful old-source prefix.

Root can publish the data now without waiting for F03/F06:

1. Copy the ORIGINAL run_build_only.py, build_only_worker.py,
   hold_and_run_build_only.py and publish_approved_ready.py unchanged from
   current290-unprivileged-build-only-source-1 into a fresh source publication
   directory. Their exact source references are in REQUEST-PAYLOAD.DRAFT.
   Copy this PROFILE.SOURCE-ONLY.json into that same directory; its frozen
   postimage and reuse-descriptor paths are already absolute and complete.
2. Root adopts request SHA256
   ccb6fc38b5864252d688eeb6be1e9d4081e59907bc98a1a88a5db88e924d681c
   into the published profile.request_sha256. The static payload stays unchanged;
   its null author/nonce/grant/runtime fields are deliberate non-authority.
   Recompute the published final profile reference for the actual new grant.
3. Copy INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json to a new Root actual descriptor;
   set author=/root, decision=PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS and
   request_sha256 to the same adopted SHA. Keep runtime_authority NULL. Its
   corrected IHK/config nested mount layout, tool file pins and all qualified
   configuration/nine-object/five-postimage references are already populated.
4. After static publication is finished, use a fresh nonce/output/handshake and
   the unchanged holder protocol. Bind the actual current holder/resources and
   final published source/profile/worker/export bytes to one independent actual
   execution review and a new one-use Root grant. Admit only under the campaign's
   current 7-job/21.7531GiB aggregate ceiling (23357213271 bytes); the unchanged
   runner's older upper ceiling does not increase that current reservation.
   Then publish the fresh exact grant via the unchanged ready helper.

Nothing here supplies Root authority, a nonce, a grant, a holder, an independent
execution release or native acceptance. Actual matching default source/object
validation and F02 native/ownership proof remain required. No compiler,
container, Root/Git/canonical action or native cleanup was performed here.
The broader five-command future profile remains separate and unchanged.
