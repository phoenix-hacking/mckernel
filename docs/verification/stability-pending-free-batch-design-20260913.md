# Pending-free batch transfer: next isolated implementation slice

Status: **SOURCE DESIGN ONLY; NO PRODUCTION EDIT, BUILD, TEST OR GUEST.**
This narrows the batch-ownership prerequisite in
`stability-invalidation-ownership-review-20260913.md`. It does not repair failed
host invalidation, authorize backing reuse, or establish a quarantine owner.
The recommended next change is one Rust list-transfer primitive and its
independent exact-helper tests. Leave every production caller unchanged until
that primitive and the separate durable transaction contract are reviewed.

## What the existing primitives require

`kernel/mem.c:3827–3829` supplies the current CPU's intrusive list head on
every public begin, enqueue and finish operation. It is not stored in the
calling thread or VM. The Rust-selected implementations are in
`kernel/rust/mem_helpers.rs`:

| Operation | Source | Relevant invariant |
| --- | --- | --- |
| Begin | 3828–3833 | `head.next == NULL` means inactive; begin makes an empty circular list. A second begin rejects an already active list. |
| Enqueue | 3899–3922 | A tracked page joins an active head; its mode becomes `PM_PENDING_FREE` and its offset stores the page count. The legacy unexpected-mode path warns and still enqueues. |
| Finish | 3926–3956 | Iterate in list order, set mode to `PM_NONE`, unlink, call the real allocator, then reset both head pointers to NULL. |
| Allocator dispatch | 4648–4703 | A missing page descriptor or inactive head allows immediate allocator release. Pending capture does not cover every backing owner. |

`MemPage` at 1076–1085 has the list as its first field, followed by hash,
mode, physical identity, reference/mapping counters, offset and page shift.
The transfer must change list links only. It must not manufacture a physical
identity, adjust references, clear the pending mode, or call the allocator.

The existing finish is not an all-or-nothing validator: a bad mode on a later
node returns `-EINVAL` after earlier nodes have already been freed. This is
visible at 3937–3949. A future safe commit needs complete validation before
the first release, with a reviewed callback contract and stable exclusive
ownership across validation and release. Calling the old finish and then
labeling its error “retained” would be incorrect.

## The smallest useful API

Add a private Rust `PendingFreeBatch` with a stable head, a transaction identity
provided by its future owner, and explicit `Vacant`, `Retained`, and `Drained`
states. It is neither `Copy` nor `Clone`; use `PhantomPinned` and require
`Pin<&mut PendingFreeBatch>` once any node links to its head. Do not add
cross-CPU `Send`/`Sync` implementations in this slice. Construction may produce
a movable vacant value with NULL links; initialize its circular head only at
its final pinned address.

The first production candidate should expose only a private unsafe operation
with this shape; this is an API design, not a compiled signature:

```rust
unsafe fn detach_from_exclusive(
    destination: Pin<&mut PendingFreeBatch>,
    source: NonNull<AbiListHead>,
) -> Result<DetachSummary, PendingBatchError>;
```

Its safety contract requires a live, valid intrusive source list and page
descriptors; exclusive mutation rights to the source and destination;
exclusion of local interrupt/reentrant enqueue during the pointer edits;
and destination storage that remains pinned and reachable until drained.
It does not validate arbitrary pointers. An eventual CPU capture guard must
establish those conditions from real scheduling/interrupt ownership; a supplied
CPU number is only a check, not that ownership proof.

Before changing any pointer, reject an inactive source, a non-vacant destination,
the same source/destination address, an inconsistent empty head, or inconsistent
first/last boundary links. A valid source is either circular-empty or has
`first.prev == source` and `last.next == source`. Interior validity remains the
existing list ownership invariant; a separate bounded inventory can detect
additional inconsistencies without releasing anything.

For a nonempty source, perform the following under one short exclusive scope:

1. Set `destination.head.next = first` and `destination.head.prev = last`.
2. Set `first.prev = &destination.head` and `last.next = &destination.head`.
3. Set `source.next = NULL` and `source.prev = NULL`.
4. Mark the destination Retained; retain the original transaction/source
   identity as metadata. Do not report a page count without walking the list.

For an empty active source, initialize a circular-empty destination and reset
the source to NULL/NULL. This is a successful ownership transfer of an empty
capture, not an error. Every rejected precondition must leave both lists and
all page metadata unchanged. The operation allocates nothing, emits no log,
calls no allocator, and performs a fixed number of pointer edits.

`list_replace_init` and `list_splice_init` are insufficient unchanged:
`kernel/rust/list_helpers.rs:88–101,217–228` leave the old head circular,
whereas the pending allocator interprets any non-NULL next pointer as active.
For an already-empty source, splice-init does nothing and leaves that same
active circular head in place.
An empty-list replacement also needs an explicit branch. Copying a head value
without fixing the first and last node links is invalid.

A future inventory API should return actual node/physical-page counts or an
explicit incomplete/error result, using a caller-frozen finite node budget.
An over-budget or corrupt batch stays reachable and unchanged; it cannot be
silently truncated or passed to finish. The transfer primitive itself does
not need to traverse or impose an arbitrary production batch-size limit.

No implicit destructor may release these pages. Conversely, dropping a live
batch or forgetting it is not a production retention policy. Before wiring
this into munmap, a real transaction owner must prevent that lifetime loss
and define how an unresolved batch is enumerated and eventually drained.
The isolated fixture can keep the pinned destination alive through explicit
mock drainage; that supplies no host-invalidation proof.

## Caller, preemption and migration constraints

Ordinary munmap is more constrained than the initial review could establish.
`kernel/syscall.c:6403–6415` supplies the actual write-lock and do_munmap
bridges. `kernel/rust/lock_helpers.rs:155–169` disables preemption on
write-lock acquisition and restores it after unlock. The offload loop at
`syscall_policy.rs:2816–2835` checks backlog and signals, then explicitly spins
without scheduling when the current CPU's no-preempt counter is nonzero;
the predicate is at 3132–3136. `sched_helpers.rs:2997–3026` similarly returns
a reschedule-only action without switching in that state. The counter itself
is per-CPU (`cls.rs:178–190`). The actual scheduler caller supplies that
current counter and returns unless the action is SWITCH
(`kernel/process.c:4326–4344`). The migration dispatcher runs in the idle
loop after scheduling back to idle, with interrupts disabled
(`kernel/process.c:3768–3796`); it is not an independent interrupt-time
migration of the running held-lock caller.

Thus the ordinary held-range-lock path already pins execution to its CPU
through begin/remove/clear/finish under the current source contract. Do not
balance the no-preempt counter on another CPU or remove that lock on the
assumption that the pending batch is thread-local. Begin and finish each
recompute the current CPU head.

The same actual range-lock wrapper covers MAP_FIXED replacement
(`syscall.c:5961–5974`), the munmap-all loop (`:7063–7076` and
`syscall_policy.rs:4390–4445`), and shmdt (`syscall_policy.rs:4460` onward).
This does not establish every XPMEM context: XPMEM calls its own begin/remove/
finish bridge from detach, invalidate and unpin paths
(`xpmem.c:8562,8867,9050`; `xpmem_helpers.rs:1596–1605`). Preserve those
callers and their existing nesting semantics in the first slice.

Preemption disabling does not disable interrupts. The noirq range-lock
wrapper contains no interrupt-save operation. The delegated wait also runs
remote-fault backlog callbacks before its no-preempt test. Consequently the
CPU head must be detached before the delegated wait in a future integration;
otherwise unrelated frees during that wait can join the old capture. Short
interrupt exclusion can protect the transfer's pointer edits, but it does
not by itself prove that every page already in the batch belongs to this
VM. The capture interval's enqueue/reentrancy contract remains a separate
integration requirement. Do not disable interrupts across removal/offload.

Allocate and register the future pinned transaction before beginning capture
or irreversibly removing ranges. Transfer the captured list and reset the CPU
head immediately after guest removal, before host forwarding, on both success
and partial-removal error paths. Preserve the current page-table/range-lock
ordering; this slice does not propose unlocking around the host operation.
Resetting the CPU head permits subsequent unrelated capture, but does not
prove host aliases drained or make old physical pages reusable.

`process_vm` has a real reference lifetime (`process.h:773–822`,
`process_helpers.rs:9775`), but no existing invalidation transaction owner is
established here. A future registry may retain a VM reference and pinned
transactions with nonreused identities; avoid a strong VM-to-transaction-to-VM
cycle and do not repurpose generic `opt/free_cb` fields without auditing their
users. VA exclusion, detached memobj/backing references and host alias drain
remain prerequisites to caller integration. A page-list transfer alone does
not solve any of those obligations.

## Independent first-slice validation

Reuse the actual begin/enqueue/finish helpers and the literal page fixtures in
`kernel/rust/tests/run_equivalence.sh:6290–6384`. They already check exact
physical identities, page counts, list state and user allocator classification.
The existing bounded memory/XPMEM entrypoint is
`kernel/rust/tests/run_memory_equivalence.py`; its historical results and C/Rust
selection behavior must remain unchanged. Do not execute that broad compiler
lane merely to prototype the new pointer primitive.

Prepare a new focused harness around the exact proposed Rust method and
the retained original helpers. Specify these expected effects independently:

| Case | Required result |
| --- | --- |
| Empty active capture | Transfer succeeds; source NULL/NULL; destination empty circular; zero allocator calls. |
| One page | Both page boundary links target the destination; mode/physical/count/offset unchanged; zero allocator calls. |
| Two or three pages | Preserve exact order and every interior link; only boundary links and heads change. |
| Fresh source reuse | Original begin succeeds immediately after detach; a newly queued page and its later finish never enter or drain the retained destination. |
| Explicit destination drainage | Using the known-valid fixture only, actual finish produces the independently listed physical addresses/counts exactly once and resets the destination. |
| Invalid destination/source or repeated detach | Explicit rejection with byte-identical heads/page metadata and zero allocator calls. |
| Conflicting capture | Existing nested begin rejection/panic bridge remains unchanged; no silent nesting support. |
| Incomplete inventory | A later bounded inspection reports incomplete and preserves the entire retained batch; it never frees a validated prefix. |
| Two independent capture heads | Transfer/reuse of one cannot modify the other's head or pages. This is ownership separation, not a multicore concurrency test. |

The next reviewable deliverable is this additive primitive plus retained
exact-helper tests, without public ABI/caller changes. Only after it passes
review and pinned checks should a separate candidate define transaction
registration, covered backing classes, VA exclusion, host-clear/alias outcome
and release policy. Failed-clear guest closure remains open throughout.
