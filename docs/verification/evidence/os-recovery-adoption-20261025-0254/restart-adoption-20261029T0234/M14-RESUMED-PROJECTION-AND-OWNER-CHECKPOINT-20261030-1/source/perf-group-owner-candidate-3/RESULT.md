# Typed perf owner expert successor — private, unselected and unrun

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is source for a new independent review, not a production implementation
or acceptance. Candidates 1/2 and the independent NO-GO remain intact. Exact
files and bindings are recorded in MANIFEST.json.

The successor distinguishes `DescriptorLease`, `BorrowedPair`, private `ListLease`,
`DetachedLease`, and `PendingStandalone`. Public release accepts only a borrowed
pair. The raw clone helper is module-private; the exposed clone operation uses
process lock, registry membership and matching generation before it can produce
a descriptor lease. Unregister serializes against clone under the registry lock,
performs descriptor count/list detach under the nested group lock, and erases
registration authority before releasing the registry lock. A detached lease has a
distinct private type and cannot be passed to the unpublished-lease count path.

Reference changes associated with published groups are preflighted and committed
under the group lock. Release checks capacity and final owner/anchor invariants
before any decrement; it then performs the bounded transition without fallible
merges or callbacks. On preflight failure it returns an owning `Custody` with
raw event/group/anchor identities, edge states and the incoming `FinalBatch`.
Descriptor finish retains the registry allocation, any unconsumed list lease and
partial custody. Grouped rollback retains its private member and operation pair
or transfers them into a final batch/custody. Batch merge returns BOTH original
inputs on error. There is no automatic drop, retry or free in these APIs, but
Rust `must_use` alone cannot force a caller to retain or process returned tokens.
The actual quarantine owner and destruction protocol are not implemented.

The unrun source regression includes clone-after-unregister, clone unwind,
forced preflight failure retaining an existing finalizer, and non-losing merge;
negative compile fixture source records descriptor/borrow type and private helper
misuse. These are source proposals, not observed results. The earlier member-FD
and leader-first source cases must be adapted to these new types before executable
coverage is claimed. No compiler or tests were run.

All production entry, descriptor read/ioctl/mmap/close, clone/fork/teardown,
monitor/scheduler, event/group finalizer and host-FD/counter routes remain
unwired. The proposed process→registry→group lock order, IRQ/reentrancy,
allocator provenance, actual type/layout selection and no-alias custody remain
unproved. Member-FD compatibility and closed-leader behavior remain open. In
particular this perf source does not supply a reviewed generic mckfd pin API.
The implementation is strictly private and must not be selected until full unsafe,
ABI, all-participant and execution review. Next: independent expert source review
of exact hashes, not production wiring or workload execution.
