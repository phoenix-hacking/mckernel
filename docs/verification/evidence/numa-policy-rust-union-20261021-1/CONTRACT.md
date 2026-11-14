# Private NUMA policy tree search body candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source preparation only. Root coordinator exclusively owns review, integration, builds, finite checks, artifact/native proof and Git. Next bounded work is independent review of this two-file patch and the proposed actual-body comparison below. No workload or source-retirement claim is made.

## Target and real production consumer

The still-C implementation is `kernel/syscall.c::vm_range_policy_search()` (line20385 in the saved preimage). It owns binary-tree traversal and half-open interval selection, rather than serving as intentionally retained ABI glue.

Actual Rust `sys_mbind`/`mbind_body_result` calls `syscall_mbind_policy_search_bridge()` (C preimage line26011), which calls this helper. Actual Rust `sys_get_mempolicy`/`get_mempolicy_body_result` similarly calls `syscall_get_mempolicy_policy_search_bridge()` (C preimage line26465). Both provider declarations and production callers already exist in `kernel/rust/syscall_policy.rs`. The helper also serves the existing C `vm_policy_clear_range()` reached from mbind. Those calls automatically use the same guarded implementation after integration; no caller/provider ABI changes are proposed.

## Ownership and behavior

The existing `MCKERNEL_RUST_SYSCALL_POLICY_HELPERS` selection makes the C helper call a new actual Rust body, `syscall_vm_range_policy_search_body_result()`. That Rust body owns root loading, node-to-policy container recovery, comparisons, left/right child selection, null termination and result selection. C keeps its exported original function signature and existing provider bridges as ABI glue, and the complete unchanged original algorithm under `#else`. This is a real body migration, not a forwarding-only ownership claim. No new C compute behavior, C subsystem or generic tree framework is added.

Traversal preserves this exact sequence: obtain `vm->vm_range_numa_policy_tree.rb_node`; for each non-null node recover its containing policy; first compare `addr < start` and traverse left; otherwise compare `addr >= end` and traverse right; otherwise return that same policy address. Exhaustion returns NULL. Comparisons stay unsigned machine-word comparisons. Intervals remain `[start,end)`, including start and excluding end. There is no new pointer validation, policy validation, node allocation, balancing, tree mutation, logging, reference change or lock operation. Loads stay ordinary loads, matching original C accesses. Rust introduces no shared/exclusive references to whole tree objects.

## ABI, locks and lifetime

The candidate uses existing checked `ProcessVm`, `VmRangeNumaPolicy`, `AbiRbRoot` and `AbiRbNode` layouts from `kernel/rust/abi.rs`, with `offset_of!(VmRangeNumaPolicy, policy_rb_node)` for container recovery. The relevant current assertions are in abi.rs (RB fields around2050; policy around2283; VM tree around2315) and corresponding C assertions in abi_checks.c (policy around794; VM tree around851). `start` and `end` are consecutive CULong fields in the same existing repr(C) type. No new copied layout or offset table is introduced. The C ABI uses an existing typed `struct process_vm *`, `unsigned long` address and returned policy pointer. These match existing x86_64 provider signatures. Assertions are preserved, not executed in this source-only preparation.

Preconditions remain the original helper's: vm is non-null, allocated and aligned; the root and every reached child/container are valid live allocations with checked layouts; the finite tree is stable while traversed; all reads and byte-pointer container recovery are valid; caller supplies synchronization and object lifetime. The Rust body performs no ownership transfer.

The inspected actual mbind body acquires the VM memory_range_lock for writing before this search and retains it through the policy operations. The actual get_mempolicy body acquires that lock for reading before search and releases it afterward. It then uses the returned pointer under its pre-existing lifetime assumptions; this patch does not add or claim to prove a lifetime guarantee after that unlock. Direct callers including vm_policy_clear_range retain their existing outer-lock requirements. Independent review should check these unchanged provider/lifetime contracts. This bounded patch does not attempt a broader synchronization repair or scheduler qualification.

## Exact source identities and private artifacts

Preimage kernel/syscall.c SHA-256:
`55e04a1e152d17c83d61280ea436012d8c073c78cb3c62bf9689c670b4021d34`

Preimage kernel/rust/syscall_policy.rs SHA-256:
`54f3103ee88d34f91f29c3c81b647bb9b24cef576bfb02a8c777742547ce97b1`

`source-bindings.json` records complete source/candidate/context and patch hashes. `preimage/` preserves both exact files; `candidate/` contains both complete replacements; `candidate.patch` is the narrow unified patch. `actual-c-reference.txt` is the exact original whole C helper, saved from that same preimage. No shared file was changed. Before eventual integration, compare both source preimage hashes and checked ABI context hashes; re-review any changed source rather than force applying a stale snapshot. Existing integrated settid and setscheduler work is preserved and receives no patch hunks.

## Proposed finite actual-body comparison (not executed)

Reuse the existing comparison process. Extract the exact whole original C helper from the saved syscall.c preimage, rename only its exported symbol for coexistence, and compare it against this actual Rust body compiled with the existing ABI module. Do not compare against a handwritten C surrogate, a mock search callback or a Rust reimplementation of the reference. Bind both source hashes and existing C/Rust ABI assertions.

Use actual aligned C process_vm and vm_range_numa_policy objects, not mock structs or arbitrary numeric pointers. An empty root must return NULL. Then construct one valid balanced red-black tree: black root interval[40,50), red left leaf[10,20), red right leaf[70,80), with actual child/parent pointers and null leaf children. Compare exact returned pointer identity for addresses0,9,10,19,20,39,40,49,50,69,70,79,80 and ULONG_MAX. This gives15 total cases including empty and covers root/left/right matches, every interval edge, gaps and exhaustion on either side. Add a second valid three-node adjacency tree with root[40,60), left[20,40), right[60,80) at addresses39,40,59,60,80 if boundary sharing needs an explicit witness:20 cases total.

Before/after every call, compare complete initialized VM/node byte snapshots, including links, parent/color and policy values, to prove no writes. Both actual implementations must return the same original node pointer or NULL; checking only a policy number would miss wrong-node selection. Keep inputs alive and stable for the entire comparison; use valid trees only. This is functional tree-search equivalence, not security testing. No fuzzing, corrupted-pointer cases or new harness framework is proposed.

Passing that finite comparison would establish only its exact input/body correspondence. The coordinator must separately establish C-selected and fallback compilation, Rust crate compilation with ABI assertions, default path linked ownership and appropriate native mbind/get_mempolicy evidence before any production/native/C-retirement credit. No compiler, test or runtime result is claimed here.

## Resource and proof limits

Only this fresh private directory was written (under32MiB). No shared sources, existing private candidates, launcher/state, docs, leases, metadata, ledgers, pins, evidence, Git, current compiled inputs, Scratch21 or permanent lock27:4 were modified. No builds/tests/guests, compiler invocation, Docker, sudo, cleanup, resize, CPU lease, network or remote campaign action occurred. No children were spawned. Credentials and credential helpers were not read.
