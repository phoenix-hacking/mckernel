Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This coherent private successor is ready for Root's focused source/profile
review and canonical adoption. It combines three actual HOST-qualified F03
callbacks (13c162ca), three actual HOST-qualified F06 adapters/490 pairs
(3ba78ed6), and the actual-qualified timer120/15word/25750-oracle data family
(1dd58c83). Current default remains26eb until the new build actually passes.

COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json binds the exact nine canonical
postimages and six existing preimages. They are the changed kernel/syscall.c,
arch/x86_64/kernel/syscall.c, CMakeLists.txt, process.c, syscall_policy.rs,
process_helpers.rs and three new unique production Rust module files:
arch_copy_to_user_bridge.rs, arch_copy_from_user_bridge.rs and
arch_syscall_forward_context_bridge.rs. Each leaf's bytes equal its qualified
bridge.rs. Only its explicit module path changes. All function bodies are reused.

F03 reuses already-public f03_ptrace_io_find/unlock and exports the existing
f03_exit_notify_wake. The one new F03 cfg is
f03_exit_waitq_wake_selected_candidate; three paired kernel C selectors are
MCKERNEL_RUST_F03_WAKEUP_FIND/WAKEUP_UNLOCK/EXIT_WAITQ_WAKE. F06 adds the paired
f06_copy_to_user_candidate/f06_copy_from_user_candidate/f06_forward_context_candidate
and MCKERNEL_RUST_F06_COPY_TO_USER/COPY_FROM_USER/FORWARD_CONTEXT selectors.
They remain within the existing supported CMake branch. F03 guards preserve
their existing logical line contexts. Each F06 guard restores the exact old
following line, preserving actual rt_sigreturn allocator/free __FILE__/__LINE__
arguments before the next original reset. C fallback bodies remain exact.

Timer process1dc76b89/helper439ffb1e postimages are unchanged from their qualified
owner. They select one genuine runtime data descriptor under the already-enabled
GLOBAL_STORAGE pair, with no new cfg or runtime algorithm. The exact current
set_timer/body/types and existing Rust __inline_memset are reused. Old failures
and passed compiler prefixes remain retained; no HOST batch is replayed here.

PROFILE.SOURCE-ONLY.json uses the byteexact already-reviewed FIVE runner25d3b8cc,
worker8512307c, holder91f6dbdf, publisheraf39ab7d and resource21748518. Its literal
stages are whole Rust, changed processC, changed kernelC, changed archC and the
same11-input rawld/link.d. The same seven unchanged C/assembly prefixes remain
read-only. Four objects are new, with genuine timer changes justifying process
compilation. Source6153/SDK21/toolchain/config/CGU selection, UID1000, CPU2-5,
12GiB/noswap/pids512/noNet and all actual reservation/freshness/nonce guards stay.
There is no five-API guard blocker. Unexecuted four-tuple preparation is retained
as history and supplies no active profile or permission.

The actual source export is the single RO rust-subtree-five-timer directory,
closed by RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json. It has109 regular files:
policy/helper change among the previous106, and three real modules are added.
All ABI/scheduler/waitq/lock/memory-provider definitions remain unchanged. New
Rust cfgs occur only in policy selection/attribute positions. New C definitions
are SOURCE-specific syscall properties, and process compile argv remains its
real accepted argv. No unused-define compatibility assumption is substituted.

Prepared acceptance separates counts and proof scopes:

-35 carried function exports plus4 unique public exports make39. There are
 six selected C function removals: kernel75→72 and arch31→28, with exact named
 baseline/remaining sets and no general compiler-elision waiver.
-Process C OBJECTs71→70 removes only timer120; it is one data family, not a
 function. Forty-six mutable descriptor families/78 entries and24 other rodata
 objects remain exact. The original four control/callback and13 CInt owners
 carry forward. Existing13 final-argument proof004291b3/ed3fb6ac is exact26eb
 evidence; new matching consumer proof is never fabricated from it.
-Timer120 must be unique Rust/final immutable storage, align8, exact15 current
 words, no C owner or hidden pointer relocations. set_timer's real table edge
 must be observed; folded edges remain explicitly OPEN for exact argument review.
-The exact Rust import delta removes the three F06 names and timer descriptor,
 adds none. Original panic/logger/clone/alias/storage/full11ld/link.d and required
 native-symbol gates remain. All helpers are loaded from explicit authenticated
 accepted paths; no missing copied helper directory is assumed.
-Warnings begin at actual Rust142, C0/7/0 and existing RWX. Unknown new headers
 block; existing narrow declaration and fixture-import debt is retained without
 suppression, casts or production source changes.

The current source/API/closure check and literal qualifier CLI preflight passed:

```sh
Q=/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/qualified-current26eb-next-default-source-1
taskset -c 0 prlimit --as=2147483648 --cpu=30 --core=0 -- timeout 60s python3 -B "$Q/check_static_cohort.py"
taskset -c 0 prlimit --as=2147483648 --cpu=30 --core=0 -- timeout 60s python3 -B "$Q/qualify_produced_cohort.py" --preflight-only
```

The first command is preadoption-only. Root can now review/adopt only the nine
bound postimages, then check canonical bytes against plan.postimages. Do not
rerun old-preimage checks after adoption. Publish the exact static sources,
profile/reuse/export109 map and literal CLI before the new clock. Root owns its
new disjoint admission A, actual request hash/nonce, source publication, latest
physical clearance, holder/resources and one actual independent execution
release. All those actual fields are NULL here.

After Root adopts the matching actual profile in A and before the fresh clock,
run the literal adopted CLI preflight. It checks real adopted argv/input bindings
and accepted helper imports without reading candidate artifacts or creating a
qualification output:

```sh
taskset -c 0 prlimit --as=2147483648 --cpu=30 --core=0 -- timeout 60s python3 -B "$Q/qualify_produced_cohort.py" --preflight-only --admission "$A"
```

Once the actual five commands finish, the same prepared entry point performs
read-only qualification exactly once under a fresh private output namespace:

```sh
taskset -c 0 prlimit --as=2147483648 --cpu=60 --core=0 -- timeout 90s python3 -B "$Q/qualify_produced_cohort.py" --admission "$A"
```

Reporting is not a new compiler-admission gate. Exact folded consumer gaps stay
OPEN until actual independent artifact proof; original failures stay preserved.
The already prepared postjoin reader may be copied byteexact into A before
publication, then invoked after the actual tool join with the generic terminal
record ROOT-ACTUAL-HOLDER-TOOL-RESULT.json. Its physical queries/probes/floors are
unchanged. No compiler, Docker, canonical/CMake/Git or native action ran here.

Real MM/usercopy/fault/VMlock192 ABI6/final-reference/current-stack/PMU/lifecycle,
Source38 GNU_RETAIN and full-native holds remain. No whole-file credit follows
from this source/profile preparation or the HOST proofs.
