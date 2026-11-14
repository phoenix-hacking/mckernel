# Perf descriptor participants 2 and owner 4 — private source, unselected

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is one bounded successor to the four findings in the independent review.
Both exact old sources are preserved; `owner4.patch` and `participants2.patch`
bind their original preimages and the new private sources listed in MANIFEST.
The unchanged C witness is paired for future ABI comparison; no C runtime or
shared source was changed. The previous frontend compile applies ONLY to owner3
and participants1, not these successors.

* Owner lookup returns `Absent`, `Found(key)` or `Invalid(error)`: bounded search
  overflow and inconsistent active/descriptor/opt/generation/owner state do not
  collapse into absence. An entry found with a zero generation is invalid;
  generation is rechecked by the existing unregister and clone operations. This
  checks the stated entry invariants, not arbitrary corrupt-tree pointer validity.
* Close no longer returns `false` for all lookup failures. It returns distinct
  `NoDescriptor`, `MissingPerfRegistration`, `NeedsNonperfProof`, or `Detached`;
  `Invalid` returns its error. A perf callback fingerprint triggers a stop, not
  provenance. `NeedsNonperfProof` does not authorize legacy callback/free: an
  actual nonperf provider still requires a separate positive ownership contract.
  Every unregistered or invalid descriptor remains in its original process list.
* Registration requires `dup_cb == NULL`. Failure retains the descriptor lease
  and inputs via the existing record path. Before each of generic, standalone,
  member or child-clone publication, the destination fd is checked under that
  destination process lock. An existing fd returns `-EEXIST`, retains pending or
  fresh inputs, and if clone had already acquired a lease, unwinds it through
  the registry/group protocol and retains the resulting outcome. Same-process
  clone to the same fd follows this exact failure path. New errno and unbounded
  descriptor-list scans require compatibility and IRQ-cost review before wiring.
* Registration allocation checks size and alignment before `ptr::write`; on a
  misaligned result the exact raw allocation is returned, not dereferenced or
  freed. The participant reservation helper transfers it to the retained record.
  No claim is made that arbitrary allocator pointers or retained records can be
  recovered/freed safely without the separately reviewed provenance owner.

`regression.rs.inc` adds focused source cases for missing perf/nonperf proof,
registered opt mismatch, dup poison, duplicate fd on standalone/member/child
and same-process clone, and raw allocation custody. `owner_regression.rs.inc`
uses the actual allocator initialization helper and checks unchanged misaligned
bytes; its synthetic 129-node search-cap fixture checks overflow leaves the
actual process descriptor intact. These sources are uncompiled and unrun. Future
harness execution must be serial, with controlled allocator and lock bridges;
synthetic corruption does not assert any observed real race. Generic publication
has the same checked helper but does not yet have its own direct fixture.

The existing permanent append-only record owner has no bound, drain, shutdown
or production recovery. Syscall entry/close/fork/teardown, callback/free/host
order, descriptor pins, monitor/scheduler, IRQ lock ordering, member-fd behavior
and counter/host lifetime remain separately blocked. No syscall, selector, host
operation or generic C/execve/TID path is wired. Independent unsafe/ABI review
must precede one applicable frontend rerun on the two exact successor sources.
No compiler, test, native/guest/container, mount or workload was run here.
