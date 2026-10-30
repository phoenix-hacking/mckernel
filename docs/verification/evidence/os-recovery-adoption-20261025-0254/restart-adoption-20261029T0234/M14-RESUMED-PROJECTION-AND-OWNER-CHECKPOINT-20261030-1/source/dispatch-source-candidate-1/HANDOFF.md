Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Owner: /root/dispatch_source. Effective invocation permissions: danger-full-access,
approval_policy=never, confirmed once. All writes are confined to this new private
directory; canonical sources, other owners, retained evidence, native owners,
scratch21/27:4, stopped containers, clocks and service holds were preserved.

The combined CURRENT119 rebase contains the exact already-prepared do_syscall
and util_thread Rust bodies together, plus the already-approved naturally aligned
2/3/wait4 request constructors. It copies only eligible constructor C hunks, not
the old packet's shared CMake/profile or unrelated candidate bodies. The util
args5=0 store retains its exact position after RUNNING_IN_LINUX and immediately
before do_syscall. Number and all six argument slots are individual raw field
writes; sender IDs/valid are still owned by the original prepare/send helpers.
There is no general memset, whole-request assume_init, new ACK or response drain.
The combined rebase adds seven reused original-function replacements as SOURCE
CANDIDATES, not seven newly qualified conversions or any retirement credit.

The new substantive correction is in mcexec_util_thread_body: move only the
borrowed descriptor.uti_info publication from before the param-size/optional
UTI_ATTR checks to immediately before start_syscall_intercept=1. Thus those two
preactivation error returns no longer publish the new guest-info allocation
which the original guest error epilogue then frees. All original return values,
worker creation, saved-context, attribute, and switch calls are retained. This
requires independent review of the exact inactive/current single descriptor and
selected UTI_ATTR contract: no claim is made for concurrent descriptor reuse,
already outstanding intercepts, previous descriptor content, worker cancellation,
getctx ownership, switch failure/UNKNOWN, final context drain or global teardown.
No field is cleared on a guessed switch outcome. No intercepted-info allocation
is pinned by this source change, and no runtime release is implied.

Files:
- CURRENT119-COMBINED.PRIVATE-NOT-APPLIED.patch and postimage/kernel: one combined
  private C/Rust source projection against the input hashes in INPUTS.json.
- UTI-PREACTIVATION-PUBLICATION.PRIVATE-NOT-APPLIED.patch: narrow host correction.
- SELECTED-HEADER-ABI-WITNESS.c.inc: emit 29-word do_syscall and 23-word util C
  witness data in the selected private TU. Kattr/context-prefix/refill mirrors
  are explicitly local witness types because original C types are block-local;
  this is not a claim that all saved-context bytes are initialized or compared.
- constructor_callback_regression.rs: actual constructor bodies, all approved
  syscall-number rows, sender-only ID/valid writes, signed pid/options and return
  conversion boundaries. It never reads ID/valid before the sender writes them.
- uti_publication_regression.rs: actual modified host util body with controlled
  create/getctx/size/attr/switch callbacks, checking no new pointer publication
  on preactivation failure and preserving original switch failure/return states.
  Simplified fixture types are callback models, not host ABI or concurrency proof.
- check_source_projection.py: exact input, reused body, writer/order and combined
  source regression. materialize_source.py wrote sources only; no tests were run.

Next executable checks, only after owner admission: first run the pure source
projection regression; then compile/run each callback regression under its
reviewed source-test profile, edition2021 or newer, in disjoint outputs. Compare
actual emitted C and Rust 29/23-word arrays under matching selected headers,
objects and profile. Compositor /root/m14_arch owns canonical integration, shared
ABI and CMake/profile. Runtime/native checks need the invocation's actual controls
and independent operation admission. Tests, compiler/preprocessor, container,
native, privileged operations and external requests were NOT run by this lane.

Do not enable global MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED or claim all-callsite
closure: held callers remain unproved. Do not enable new default selectors by
virtue of these files. Both util selectors remain separate. Keep original
_collect, PROFILE_SHA256=None, source-binding/effective-view and authenticated
owner/admission gates. Child01a18a76 and equivalent generic_c/execve/direct-TID/
terminate_host work were neither replayed nor reassigned; this packet supplies
no clearance. The original stopped records, UNKNOWN outcomes, consumed nonces,
failures, dirty artifacts and all inherited tighter clocks remain authoritative.
