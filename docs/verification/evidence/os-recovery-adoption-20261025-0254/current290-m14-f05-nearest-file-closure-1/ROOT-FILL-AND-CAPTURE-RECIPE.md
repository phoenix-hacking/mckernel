Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

These are templates only. No nonce, resource proof, current physical acceptance,
review, runtime authority, Root admission directory or capture directory is supplied.
The two null argv values are the attempt-parent and nonce. Never execute either
template or reuse the consumed startup2 nonce/attempt/capture.

Root fill sequence:

1. Reuse published memory-manifest.json40c1d0f4, memory.cpio.gza4bc4935,
   memory-overlay.json and collector70a6de49 as-is. Existing static validator
   passed; STATIC-MEMORY-READY.json is the actual packaging result. `stage_result`
   is null because no new scratch stage-result file was created. Bind this actual
   packaging record in the Root operation rather than borrowing startup2's stage.
2. After accepted growth FD closure/final custody release, choose one genuinely
   fresh nonce and Root-owned attempt-parent and admission/capture directories.
   Fill both templates' nonce and attempt_parent fields and the corresponding
   --nonce/--attempt-parent argv values identically. Preserve every known argv
   element, manifest path/hash, owner45010e54, container/guest profile and cutoff.
3. Bind actual fresh resource/physical/current observations and their independent
   acceptance. Replace null resources/current_physical/current_postbuild_observation/
   independent_current_acceptance with current exact file references. Preserve
   original BUILD3 proof records, including its retained failed first validator.
4. Publish the completed static bindings, capture directory and operation inputs
   before beginning the fresh admission clock. Obtain the applicable independent
   execution release for this exact memory operation. Fill the final grant's
   static_bindings ref with the actual filled static file hash, fresh_resource_physical
   and independent_review refs with actual accepted files, and runtime decision only
   through Root's actual admission. Do not infer release from these templates.
5. Root executes the exact filled argv once with inherited SUDO_ASKPASS. Redirect
   raw stdout/stderr to new CAPTURE/stdout and CAPTURE/stderr, retaining the actual
   caller PID, /proc starttime, exact argv, entry time and resource age in
   CAPTURE/STARTED.json. Keep the owner/caller session until genuine join; retain
   actual return code/time in CAPTURE/JOINED.json. Do not manufacture exit0,
   substitute model process retirement for native retirement, or reset a workload
   because a model worker hangs. The original owner keeps normal workload cleanup.
6. Export actual raw owner/guest records and preserve any failure. Apply unchanged
   evaluator to memory stdout exactly `NATIVE_CORE PASS memory\n` (24 bytes),
   stderr empty and exit37, plus existing lifecycle/kmsg/retirement/teardown gates.
   Complete fresh postjoin physical/current observation and independent acceptance.
   A successful core memory diagnostic leaves the whole-file limits in RESULT.md
   open. Do not automatically dispatch another heavy workload.

No compiler, payload rebuild, new overlay, framework, guest/root action or replay
is necessary to prepare these known inputs. The grant template intentionally
retains maximum_invocations1 while its decision is TEMPLATE_ONLY and runtime
fields are null; it authorizes zero invocations.
