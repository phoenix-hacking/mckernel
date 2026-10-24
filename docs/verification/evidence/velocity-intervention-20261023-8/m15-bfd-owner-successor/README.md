Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Fixed M15 BFD compile-only owner successor

This private source specializes the accepted compile-only owner 8cd5a194 for the
existing m15-bfd package. It does not start a container or release the prepared
request. Canonical source, existing owners/helpers, P12, native ownership and
Git/launcher state were not edited. The dispatcher alone owns integration and
independent operation release.

The owner/helper/profile/create/inspect paths agree on CPU6, one CPU, 2 GiB,
MemorySwap=Memory, pids128, jobs1, network none. The original P12 reservation is
still CPUs2-5, four CPUs, 12 GiB, no extra swap, pids512; admission still requires
same-boot facts no older than120s and both root/fresh MemAvailable >=24 GiB.
Root admission must prove actual CPU6 retirement, P12 sole native/heavy ownership,
unchanged P12 cgroups, sufficient HOST/scratch capacity and disjoint writable roots.

The effective entrypoint is /usr/bin/env; its Cmd is exactly the BFD READY argv
after argv[0], including -i, fixed PATH/LANG/LC_ALL, Python and the qualifier.
The only writable bind is the fresh HOST operation-1/owner-work at /work. /src is
the original McKernel repository, /candidate is the existing BFD package, and
the retained /out and /nightly closures are read-only. Rootfs remains read-only,
with the inherited bounded /tmp. No image creation, package install, native
activation or new build framework is introduced.

BFD-INPUTS.json binds the proposal and its test/orchestration files plus the
consumed source roots executer/user, cmake/modules and ihk/linux/include. Git
metadata and Python caches are excluded because the fixed job does not execute
them. Existing in-tree file links include resolved bytes; directory links require
their targets to be separately inventoried. The six original-wrapper/tool-source
bindings are checked again against the BFD package. Source/root identities remain
fixed. The original image-toolchain and image-receipt validation are reused from
the retained request, including the complete /out and /nightly inventories.
The retained candidate SHA is image-preparation provenance; it is not presented
as the current repository's identity. The new receipt binds BFD-INPUTS instead.

Completion requires the exact BFD PASS status with native_acceptance=false and
M15_file_closure=false, exact pins, eight expected baseline/Rust comparisons,
matching retained streams, all21 successful logged qualification commands,
four unique Rust bridge exports without old-wrapper dependencies, and nonempty
selected-tool/object/layout/link artifacts. The owner records the actual output
inventory and RESULT hash only after this passes. Actual BFD outputs are absent.

The inherited live-P12 checks, exclusive separate HOST lease, exact-CID lifecycle,
logs/terminal capture, sticky uncertain-client retirement and three-way absence
checks remain. Compiler success retains the lease for sealed root physical
acceptance and separate finite release. A pre-create failure or CIDless ambiguous
failure keeps its lease and cannot use the ordinary accepted-CID release; root
must separately reconcile the exact retained state. No native/global record is
acquired or released by this owner, and permanent native mutex27:4 is untouched.

Actual verification

The dispatcher granted exactly one CPU0 pure-fixture command, 512 MiB AS, CPU10s,
wall30+5s, FSIZE16 MiB, FD128 and core0. run_fixture_1.py imported the full pinned
accepted990 capture helper and used its owned_capture/direct-wait/group census.
fixture-actual-1/stderr says: Ran24 tests in0.242s, OK. The complete raw file has
ordinary unittest spacing; this paragraph is only a summary. Capture rc0,
direct_child_joined=true, group_absent=true, closed_streams=true, error=null,
retirement_error=null; outer capture0.441643261s. CPU0 was returned after whole
join. Tests use fake Docker and private temporary files. The real-script child
checks NULL-release refusal; a separate assertion forbids Docker construction
on that path. Full fake-success fixtures deliberately stub compiler/source/result
validation; they prove owner transport/lease handling, not BFD compilation.

Preserved failure history

The accepted predecessor's missing-entrypoint failure and corrected19-test result
remain authoritative at their original scope. This source-preparation generator
initially rejected the existing UTI hwloc directory link, before owner/profile/
request generation. Its failed source and FAILURE-source-preparation-1.txt remain.
One bounded correction records the link and separately inventories its target.
That family has exhausted its routine correction. No unexpected fixture failure
occurred. Any further same-family failure needs expert review, without an
unchanged replay. Pre-create/CIDless lease limitations remain preserved.

Next dispatcher review

Review compile_image_owner.py.diff, compile_host_helper.py.diff,
test_compile_owner.py.diff, COMPILE-PROFILE.json, BFD-INPUTS.json, the exact
compile-request.PREPARED.json and fixture capture. Root templates remain
_template_only_no_authority with all actual facts/review/admission references
unset. The prepared request's compile_only_release is NULL. Fresh admission must
use the BFD admission schema and PASS_DUAL_CONTAINER_COMPILE_CPU6_2G capacity
verdict; none has been observed or published. Runtime release is separately open.

Full inherited toolchain inventories are revalidated. Their runtime duration has
not been measured here; the120s admission expiry is still enforced and must not
be bypassed if validation makes a release stale. The retained request's disk
device values are historical inputs, not fresh live UUID or capacity evidence.
Root must reconcile them before finalizing an actual request/release. No full
image build is needed for this selected BFD qualification. On an actual BFD PASS,
independently review layout/type/macro/link/behavior evidence, then qualify real
production configuration/install/deployment and matching native sessions. Original35,
M14 and M15 remain separate, and all native/file-closure claims remain open.
