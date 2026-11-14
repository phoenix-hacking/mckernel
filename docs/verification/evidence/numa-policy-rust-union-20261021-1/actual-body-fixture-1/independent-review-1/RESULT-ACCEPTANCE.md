# Independent22-case search-equivalence result acceptance

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: ACCEPT_PASS_FINITE_ACTUAL_C_RUST_VM_POLICY_SEARCH_PARITY. All22 cases,
selected ABI assertions and complete inner/outer closure meet the exact reviewed
fixture boundary. Unchanged222 source/input bindings and source review284529d3
are reused; no source re-audit, replay or production/native acceptance is added.

The actual output has exactly24lines: layout,22independent case passes and exact
final parity summary. Actual C layout is VM304/policy80/rb_node24, VM-tree248,
policy-start24/end32. Rust object compilation with the complete unchanged ABI
module and the separate selected existing C ABI assertion compilation both
exit0. This accepts the relevant fixture layout/body correspondence, not the
full original C ABI TU or complete production crate.

Empty-root, fourteen ordinary boundary/gap queries, five adjacent half-open
queries and two unsigned upper-bound witnesses all return the independently
expected exact original policy pointer or NULL in both actual bodies. In
particular18446744073709551614 selects the high right node while ULONG_MAX
misses. Complete VM/node/guard snapshots match immediately after each C and
Rust call. These observations establish final no-write snapshots on the selected
stable valid trees, not concurrency or absence of a restored transient write.

All five command records exit0 with empty stderr and positive direct-child join,
absent group, closed streams, no timeout, unexpected member, capture error or
retirement error:

- Rust object PID2425477/start35515642.
- Actual C object PID2425484/start35515653.
- Existing selected C ABI assertions PID2425487/start35515662.
- Complete host link PID2425490/start35515668.
- Actual22cases PID2425493/start35515672.

Outer PID2425476/start35515633 exits0 in0.4613891210174188s with matching
started/direct-wait/direct-join/whole evidence and the same positive closure.
Outer stdout167bytes/stderr0bytes match their records. All twelve inner/outer
raw stream sizes and SHA256 values were independently compared and match.
The actual outer command equals the exact approved proposal argv. Dispatcher
reports CPU6 released after full closure; this report creates no grant/lease.

Actual root grant60b18cf7 binds proposal010cfe61 and review95c55648, CPU6/one job,
AS1GiB/FSIZE32MiB/35s outer and the inherited exact proposal limits. It records
no actual census/LAST window and terminal image preparation as source-only.
MemAvailable28,308,430,848bytes exceeds2GiB. Host42,182,443,008bytes exceeds
17,850,957,824required; scratch14,145,949,696 exceeds13,555,990,528. These include
the mandatory root640MiB reserve above BOTH floors, rather than only the
runner's post-command16MiB assertion. Grant usage is52percent; root separately
reports active service and no other ordinary/exclusive census window.

Exact accepted evidence:

- check-1/result.json: `6ee142370a08be3672e63ce53fa0a39c82c6eb8347465d3a4a6c340274ac8507`
- check-1/actual-22-cases/stdout: `675ddb219098c53ffa6a884e90d72ff386fa0cbb1b2aa063a5e1b10465dc70cb`
- actual-outer-capture-1/grant.json: `60b18cf78403901c752e49fa0d97193b02f27777537807ec93f17e23e587be47`
- actual-outer-capture-1/whole.json: `6341edc0d866a1769d393006eeec6dcc8d530c138b8729533bee3d689f26b85f`

This first candidate passes, with no executed correction required. The concrete
inherited get_mempolicy post-unlock policy-node reclamation defect remains
separate. No runtime occurrence, caller lock/lifetime repair, snapshot-patch
behavior, full production compilation, final link/default ownership, native
mbind/get_mempolicy, image/guest, HOST66 or compute-C retirement is proved here.
The independently reviewed caller snapshot candidate was not part of these
parity tests. The retained image/container/records remain independently owned.

Only retained result/capture evidence was read/hashed and this private report
was written. No test replay, compiler/root/guest command, lease, source edit or
Git action was performed by the reviewer.
