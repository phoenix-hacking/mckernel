Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private owner /root/dispatch_source; recovered-thread danger-full-access and
approval_policy=never were confirmed for this same thread. All other writers and
all earlier candidates, failed oracle/evidence, passing 17-test/7C+2host results,
held work, native owners and execution controls are preserved. No passing check
was replayed. No compiler, workload, native/model/root launch or subagent ran.

This overlay is ready for the actual crate frontend. It appends three uniquely
named private modules to the compositor-supplied H2 syscall_policy.rs parent:
/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-perf-typecheck-integration-2/work-1/src/kernel/rust/syscall_policy.rs
SHA256 217091d13694fb04a4b14930256e60dd9decdc5ae771fc101605b609aa35e403.
The baseline lib.rs is copied unchanged only to state the actual root-crate entry.
Every other crate source stays the H2 source-map owner's responsibility; this
partial source overlay is NOT a standalone mock crate or a fabricated materialized
union. Exact H2 ABI/provider source paths/hashes are bound in INPUTS.json.

m14_private_do_syscall.rs and m14_private_util_thread.rs extract the exact existing
CURRENT119-backed candidate bodies, removing only their outer inline module/cfg
and one indentation level. m14_private_request_constructors.rs reuses the exact
natural-alignment constructor source. Production export_name/no_mangle attributes
are suppressed in these three files; their functions retain actual unsafe extern-C
prototypes. Explicit function-pointer constraints check genuine current provider
signatures. The module names differ from H2's already-declared
f03_request_constructors, avoiding duplicate declarations/production exports.
The private constructor and util bodies still call the original do_syscall
provider. No edge is silently redirected to a new global replacement.

One additional body correction in the extracted do_syscall is concrete and local:
if syscall_offload_prepare_result returns negative BEFORE send_syscall, reverse
this entry's in_syscall_offload increment when counted and restore its captured
monitor status, then return exactly the preparation result. Do not increment the
monitor completion counter on that edge. No request was sent, no preemption edge
was added yet, and no host access/completion/drain is inferred. The exact old/new
branch snippets are retained. The current provider at syscall_policy.rs:3082
returns -EINVAL only for null request/response, whereas this caller's genuine
valid-pointer precondition excludes that case. Thus this closes an unbalanced
error branch in the candidate; it does not claim an observed native failure fix
or new behavior on a currently valid execution. Original defined count domains,
all six initialized wire arguments, sender ID/valid ownership and final-return
accounting are preserved.

No thread/VM/stack/monitor/channel pin or ACK is invented. Existing hold_thread
returns zero even after its internal result is ignored, and a reference increment
alone would not prove actual current-stack/monitor/mapping or host descriptor
lifetimes. The original live-current caller contract stays explicit and open;
a fresh current-pointer lookup, scalar completion or typecheck is not its proof.
The independent host UTI pointer-publication proposal is excluded from this
frontend overlay; process-wide static uti_desc, previous state, inactive/exclusive
single descriptor and no-prior-borrower prerequisites remain held. No new global
UTI publication or reclamation selection is introduced here.

The only added cfg is m14_private_frontend. The private append requires supported
x86_64 + enable_profile and rejects optional enable_tofu/enable_fugaku_hacks. No C
selector or new default Rust selector is added. Global do_syscall, exec/exec-tail,
ACK, direct-TID and every previously held selector/request remain OFF/unreleased.
No host patch is applied. Constructor bodies are source-only reused replacements,
not additional implemented/retired counts. Whole-file, default, link, native and
supported-scope acceptance remain pending.

Compositor integration: apply H2-PRIVATE-FRONTEND.NOT-APPLIED.patch to the exact H2
parent or append SYSCALL-POLICY.APPEND.rs.inc once and add the three named files.
Do not append the old combined inline body fragment or its constructor declaration.
Compositor /root/m14_arch exclusively owns canonical/shared ABI/profile files and
must bind the complete actual H2 sources, generated inputs, tools and output path
through the legitimate owner path. C metadata externs still require their exact
providers at eventual link; this frontend intentionally does not release them.

Next compiler check: Root/compositor's one affected actual-crate Rust frontend,
with the existing H2 cfg/environment/tool tuple plus --cfg m14_private_frontend,
using the composed /src/kernel/rust/lib.rs and a fresh private metadata output.
FRONTEND-REQUEST.json records this as an ungenerated owner-binding request;
frontend argv, operation admission, source-map/mount proof, resource ownership,
controls and output custody are still Root-owned. No compiler success is recorded.
