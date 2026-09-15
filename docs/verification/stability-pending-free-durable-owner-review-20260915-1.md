# Pending-free durable ownership/recovery review — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. Source integration remains blocked.

The private candidate `kernel/rust/mem_helpers.rs` (SHA256
`647825d8c51a9f584d1229a2389fbb81105e4bbf94bfcf95a12d172c5dde112b`)
reanchors descriptors and resets the CPU head, but its pinned destination has no
surviving registry, transaction generation, VM reference or recovery hook. Drop
can destroy retained head storage; forget can make ownership unreachable. Pinning
prevents movement under its contract, not loss. The recurring CPU-head pointer
cannot authenticate a delayed completion, and drain has no clear authorization.

The guest munmap path removes mappings before host clear, loses errors through a
void callback, and finishes unconditionally. Host zeroing exchanges the pending
head to zero, then holds its cursor/chunk inventory only on the stack; later error
can leave acquired tags while an unvisited suffix lacks persisted reconstruction.
Service failure retains started storage and stops, which is fail-stop retention,
not bounded recovery. Mirror clear retains the originating MM for its locked
operation, but does not prove every inherited PFN alias drained.

Before capture or irreversible removal, a future contract must preallocate and
register a pinned transaction under a surviving OS registry owning VM/backing
references. Identity needs `(OS incarnation, VM incarnation, monotonic transaction
serial)` with checked exhaustion and no reuse. Durable state and complete inventory
must precede fallible work. Preserve lock order, VA reservation, mutation result,
actual MM result, accepted completion, publication and alias-drain as distinct
facts; only verified release authorization permits drain.

Recovery needs one exclusive lease, finite retry/work budgets, persisted cursor
and release progress, and an interruption-safe allocator handoff. Exhaustion must
leave an enumerable retained terminal transaction. Required negatives include
registration failure; caller exit at every transition; stale completion against a
reused CPU head/OS/VM; serial exhaustion; partial removal; clear/publication
failure; incomplete inventory; competing or interrupted recovery; conflicting VA
reuse; and inherited aliases.

Reviewed hashes include `sysfs_zeroing.rs`
`221b3427849c4c5d62254cf16445e2851631d3fed6f4f7875f4e59e2c0d6a290`,
`sysfs_memory.rs`
`11eadff3fde6d46edfefcd988e941cb9bbab443e059a03d082245c3db6f1ec73`,
`smp_service.rs`
`0747b5dbc7a529282c3073294e9ed7f121da927c59923a60455bc6f6aa610478`,
`zero_pages.rs`
`47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def`,
`page_alloc.rs`
`3e89740f0215d46d83d731fe9338ae70792e2cb2b4cbdafd416dc5d1bb6200fd`,
`syscall_policy.rs`
`5e770e3375c7eb2f6f5aae23863a961123b5f200c77662780cb04a90dc13bf53`,
and `mcctrl_vm.rs`
`74facf8daac2d3843e2c7c862b7186c8d738d7a78573ac0f1e6ea81436da470d`.
No build, runtime or production credit follows.
