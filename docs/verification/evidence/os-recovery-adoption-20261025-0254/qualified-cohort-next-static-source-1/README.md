Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The active PROFILE.SOURCE-ONLY.json contains FOUR commands: whole Rust,
changed kernel/syscall.c, changed arch/x86_64/kernel/syscall.c, identical eleven-input
raw ld. Root explicitly chose to reuse process object b8168c1f (73408B), with
unchanged F02 source9692036c and unchanged exact compiler argv. Eight C inputs
are retained: seven unaffected original objects plus that matching F02 process
object. Three objects are newly produced. The historical five-command profile
is labelled DO-NOT-EXECUTE; do not replay its process compile.

The private merge reuses the qualified F03 four-slice f8f057 plan, qualified
do_exit, qualified five-provider unmap/page/release backlog and expert-qualified
F06 six-provider3f5b45 batch. Shared source regions have zero overlaps. Seven new
Rust modules are byte-exact reused bodies. The unqualified termination backlog,
other source-only F06 selectors, whole held do_mmap/do_fork/terminate bodies and
unsupported configurations stay OFF. NOCACHE remains genuinely undefined;
f06_use_nocache_mmap is not added. New CMake selectors/cfgs apply only inside the
existing Linux6.12 branch for ARCH=x86_64 and ENABLE_UBSAN=OFF. The inherited
DCFA-undefined/ticket-lock ABI and other source/provider holds remain required.
This is source-ready composition, not a passed merged production compilation.

Root's next concrete adoption/build recipe:

1. Wait for positive retirement/current acceptance of the running native
   workload. Run `python3 -B <this-directory>/check_adoption_preimages.py`.
   It checks only the seven exact canonical preimages, seven new-path absences
   and selected private postimages. No broad source audit or source writes.
   Obtain the focused independent unsafe/ABI integration review. Root alone
   adopts the exact candidate/ files or patches/ after that review/preimage gate.
2. Copy the ORIGINAL bc9e runner and bc00 worker from
   current290-unprivileged-build-only-source-1 into a fresh publication directory.
   Apply run_build_only_four.py.patch to run_build_only.py, and
   build_only_worker_four.py.patch to build_only_worker.py. Copy the unchanged
   holder and ready publisher from that same original source directory. Do not
   apply the historical five-command patches to the active consumer.
3. Copy the active PROFILE.SOURCE-ONLY.json into that publication. Its source,
   compiler argv, eight-object reuse descriptor and mount data are complete.
   Root fills only request_sha256 and native_custody_clearance from the actual
   newly accepted postjoin/current custody, then binds final published hashes.
   Runtime authority stays NULL in the static profile and reuse descriptor.
4. The new source mount is explicit inputs.source_directory_exports, targeting
   the EXISTING /src/kernel/rust directory. Its closed map pins101 regular files
   (10217761B), including the seven new leaf files. It replaces the Rust subtree
   in one RO bind; no absent leaf targets need creation under the RO /src parent.
   The runner addition authenticates the exact source-directory manifest/file
   set and every file, includes it in the export closure and output-disjointness
   checks. It does not use toolchain aliases or widen generic additional exports.
5. Root adopts INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json, setting its author/decision
   and the same exact request hash. It retains corrected IHK/config targets,
   source6153/SDK21/toolchain bytes and adds the explicit closed source refs.
   Use the existing nonce/holder/resource/independent-execution/grant protocol
   after completing all static publication. Actual freshness, resource admission,
   one-heavy, fixed cutoff, account guard and matching native acceptance remain
   required. No actual new nonce, clearance, resource observation or grant exists
   in this package.

The four-command pure suite passes8 methods. The preserved five-command and
source-directory suite passes32 methods (the original25 plus7 closed-map/mount
checks). They run only mocked producers/read-only source checks. No compiler,
container, native, canonical/Git, live-clock or grant action was performed.
Do not rerun assemble_cohort.py/prepare_profile.py: their source materialization
already completed and their historical five-command data is superseded by the
active four-command profile. Matching whole Rust/selected C/link/native/file
retirement remains open until actual production checks pass.
