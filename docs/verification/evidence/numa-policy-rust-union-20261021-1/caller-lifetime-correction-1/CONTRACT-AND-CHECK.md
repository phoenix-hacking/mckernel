# Private get_mempolicy returned-policy lifetime correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status: finite source-only candidate ready for independent review. No build,
test, import, native/guest/root execution, CPU grant, resource census, integration,
Git/ledger update or child agent was performed. The source-preparation script
only read bound inputs and wrote this owned private directory. All shared sources
and the separate search-port, fixture, review and current-image inputs are intact.

## Exact input and output binding

`source-bindings.json` records complete SHA256 bindings. Rust preimage is
`54f3103ee88d34f91f29c3c81b647bb9b24cef576bfb02a8c777742547ce97b1`;
C preimage is `55e04a1e152d17c83d61280ea436012d8c073c78cb3c62bf9689c670b4021d34`.
The complete Rust preimage and private candidate are retained here.

The lifetime-only patch is `candidate.patch`, SHA256
`51c38db1f09be3921d6145c5d079ff0ef4054b2956ee152adfd18844491cd1f8`.
Its complete Rust candidate is
`946ef1095f6b9e9c1ca0885211fff384d6debb9345b49a954a4053a34220e729`.
It does NOT incorporate the independent traversal patch
`471b1988100d8b87f2b79f18ff0afd2ebd886f94bf4ecc0fcf1d7edf32038330`;
these touch disjoint Rust bodies. Root must reconcile current preimages and obtain
review of the coherent hunk union before eventual shared integration.

## Production contract and correction

The actual Rust `get_mempolicy_body_result` reads a policy from the NUMA tree
under `memory_range_lock` read ownership, then previously dereferenced that
borrowed policy after read unlock. The actual C body has the same inherited
sequence. `process.h` explicitly places the tree under this lock. Actual Rust
`mbind_body_result` holds the corresponding writer lock across lookup, clear,
insert and policy/mask update. Its clear bridge calls `vm_policy_clear_range`;
the latter erases and frees exact/contained policy nodes. The C mbind caller
similarly holds the writer lock across clear/update. No retained policy reference
or independent node lifetime is provided by search.

The candidate changes only the Rust caller: while the existing read lock remains
held, copy the matched `numa_mem_policy` into an `Option<CInt>` and, only when a
mask will be requested for a non-default range policy, copy exactly
`nodemask_bits >> 3` bytes from the policy's mask to a local aligned mask array.
After unlocking, mode and mask usercopy read only these local values. The raw
returned policy pointer is never dereferenced after unlock. No node reference,
heap allocation, new ABI, protocol, lock, C implementation or provider is added.

Existing types bind CULong=u64, CInt=i32 and PROCESS_NUMA_MASK_WORDS=4 (256 bits)
on supported x86_64. `VmRangeNumaPolicy` is repr(C), mask offset40/32 bytes and
policy offset72; existing C/Rust ABI assertions remain unchanged. The validator
always leaves nodemask_bits <=256, so the intrinsic byte copy is at most32 bytes.
`addr_of!` obtains the source field pointer without borrowing the whole node;
`copy_nonoverlapping` copies ordinary kernel bytes between the live read-locked
policy allocation and disjoint stack array. This is not `copy_to_user`, cannot
fault on a user address, and adds no callback under the spinlock. Existing
`syscall_copy_to_user_bridge` forwards synchronously to `copy_to_user`; both user
copies remain after read unlock and preserve their existing local-source lifetime.

The sequence of argument validation/clamp logging, mandatory copy callback check,
NODE|ADDR fast path, MEMS_ALLOWED fast path, required ADDR callback checks,
lock/range lookup/invalid-range logging/unlock/error, policy search/unlock,
optional mode usercopy, and optional non-default mask usercopy stays unchanged.
Every existing acquired-lock branch still unlocks exactly once. Return codes,
mode-before-mask errors, zero mode suppression, zero mask suppression, zero-length
mask usercopy, byte rounding/clamping and addr.wrapping_add(1) are unchanged.
The new kernel snapshot occurs before mode usercopy even if that later usercopy
fails; this adds no user-visible callback or changed return/error. Concurrent
range-policy updates now yield the single lock-protected snapshot, which is the
intended change. Null policy and non-ADDR calls retain the original VM-policy/
VM-mask fallback; process-wide policy synchronization is outside this correction.

## Smallest meaningful next actual-body check (proposal; NOT run)

Root may place one finite fixture in a fresh owned output root within an existing
reviewed unprivileged profile after independent source/fixture review. Extract the
complete candidate `get_mempolicy_body_result`, actual validator and clamping
helper from these exact bytes and use the actual bound ABI module/constants.
Do not rewrite a model of the caller. Callbacks must implement only the existing
injected ABI boundaries. Use real initialized aligned ProcessVm, VmRange and
VmRangeNumaPolicy allocations, distinct policy/mask bytes and guarded output
buffers; no synthetic node addresses or forged references. Match existing exact
ABI assertions before passing allocation pointers across C/Rust, if C is used.

Instrument a single finite callback state machine:

1. Valid ADDR with a matched non-default policy: record lock, lookup, search,
   unlock, mode-copy, mask-copy in that order; require lookup/search under lock,
   both copies unlocked and one lock/unlock. In unlock callback, after recording
   release, overwrite the still-live policy's mode and all32 mask bytes with
   distinct valid replacement values. Candidate must return the original mode
   and original requested bytes, proving it stopped consulting the borrowed node
   after release. Keep this allocation alive throughout, including original-body
   comparisons; do not execute the inherited body after freeing its allocation.
2. A second valid matched case leaves policy unchanged during unlock but replaces
   it during mode-copy; require mask still comes from the earlier snapshot.
   This distinguishes correct paired snapshotting from copying mask later.
3. Repeat matched non-default path at maxnode0,1,65,256,257 (nr_numa_nodes=1):
   expected mask byte counts0,1,9,32,32. Compare precisely that prefix and guard
   bytes; mode-copy still precedes mask-copy, including the zero-byte callback.
   Include high-bit mask bytes to expose truncation. Clamp log precedes lock only
   in the final case. Reuse the same source harness and existing callback oracle.
4. Matched MPOL_DEFAULT: mode-copy only, no mask-copy even with a nonzero mask
   address; zero mode address with non-default mask: mask-copy only. Neither
   output address: no copies and success. No range match with a valid VM range:
   preserve current VM-policy/VM-mask fallback; MPOL_DEFAULT fallback skips mask.
5. Invalid VM range: lock, lookup, invalid-range log, unlock, -EFAULT; no search
   or copy. Missing any required ADDR callback: -EINVAL before lock. Mode-copy
   failure: -EFAULT with no mask-copy; mask-copy failure: -EFAULT after mode-copy.
6. Existing early errors/fast paths: null VM, invalid flags/address/maxnode,
   missing copy callback, NODE|ADDR including missing node callback/node-copy
   failure, and MEMS_ALLOWED including mask-copy failure. Require no range lock,
   lookup or policy-search calls and existing exact output sizes/errors. Include
   ULONG_MAX ADDR with recorded wrapping lookup end0; no new address rule.

For stable policy cases, compare actual original and candidate bodies against
independent expected values/errors/event sequences. For overwrite-on-unlock and
mode-copy cases, original's later reads are expected to differ; candidate must
match the pre-unlock snapshot oracle. These are deterministic lifetime-boundary
and ordering checks, not proof of arbitrary concurrent execution. Keep full
failed compiler/test streams and source bindings. This family has zero candidate
executions/zero corrections; allow only one failed candidate and one bounded
correction before focused escalation, carrying history across continuation.

The next downstream steps are separately admitted finite actual-body observation,
coherent traversal/lifetime union review, full selected/fallback C/Rust-crate and
ABI compilation, unique final symbol/link checks, and matching native
mbind/get_mempolicy functional evidence. No default/native/C-retirement claim
follows from this private candidate or a future finite fixture alone.

Stop condition reached: one private correction and one finite check proposal,
with no execution. No production prerequisite prevented preparing the correction.
