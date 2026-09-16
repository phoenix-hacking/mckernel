# Pending-free inventory source-contract proposal 1

Date: 2026-09-15

Status: **SOURCE-CONTRACT PROPOSAL — NOT ACCEPTED OR RELEASED**

Task: `M03-pending-free-inventory-source-contract`

This document specifies the smallest private production-owned inventory API
that could make pending-free recovery auditable. It authorizes no source
integration, caller change, ABI, build, runtime, or production credit.

## Current facts (not proposal)

The current reviewed `kernel/rust/mem_helpers.rs` is SHA256
`647825d8c51a9f584d1229a2389fbb81105e4bbf94bfcf95a12d172c5dde112b`.
`validate_pending_head` (lines 300–355) follows raw links and dereferences
before an independently trusted bound. `detach_pending_free_batch` (357–399)
transfers links, and `drain_pending_free_batch` (401–434) traverses and mutates
descriptors before/around callbacks. `MemPage` is `repr(C)` at lines 1242–1252;
its links, mode, physical address, and `offset` do not constitute a trusted
inventory. `phys_to_page` (line 71 and call near 962) is only a lookup.
The pending begin/enqueue/finish exports at lines 3995–4144 accept no durable
inventory bound, ownership lease, generation, or range registry. Legacy
`kernel/mem.c` is SHA256
`167ad2b976bcdec048a625dedf68a9b7c1ef6db7c57f3ceddf3582d54887101a` and its
finish traversal is likewise unbounded.

The source audit is SHA256
`bf5d001d2585e7faad70af46d0bc994bd955ab61a40d24db8c209e985d286395`.
The durable-registry feasibility review is SHA256
`a04b94e6c36f0072d297592fe8a0c9b13eddcd6709a03d76db9563a0f1737a4a`.
The invalidation policy audit is SHA256
`0b8f34c355a664314a5a371b97afa05db091e329e70382c856bf93f0c9b4171a`.
Those reviews find no trusted VM incarnation, page-range registry, clear/TLB
acknowledgement, or typed release permit wired today.

Candidate 12's retained checkpoint (`20611dc38ee7adaf42d853cb86491c99e5fb6988`,
owner result SHA256 `b49d3ca6545df51030c35af18ac1fbb5afa14734060a5f3d1ba7437a63ce1e30`)
is focused-equivalence-only. Its 30 Rust/30 C rows and five trait negatives
earn no production credit; nested begin, malformed boundary links, and bounded
incomplete inventory remain untested. Candidates 13–15 do not promote this
scope.

## Proposed private contract

The inventory is an opaque, kernel-owned object, never a public C ABI:

```text
InventoryKey { os_slot, os_generation, vm_incarnation, transaction_serial }
InventoryLease { key, arena_generation, descriptor_generation, capacity, count }
Snapshot { key, arena_generation, descriptor_generation, count, extents[] }
ReleasePermit { key, snapshot_digest, clear_epoch, phase }
```

`InventoryKey` is an authenticated identity join, not a PID, TID, CPU, list
address, or physical address. A lease is created only by a private owner that
also supplies an exclusive pending-list lock. `capacity` is fixed at begin;
`count` is monotonically checked and cannot exceed it. Registration records each
descriptor's immutable generation, pending membership, page count, aligned
physical start, and checked end. Arithmetic uses checked multiplication and
addition; ranges are nonempty, page-aligned, nonwrapping, and pairwise
non-overlapping within the inventory. Membership is exact key plus generation,
never address equality alone.

The lease holds a pinned or reference-counted arena owner, and each snapshot
retains that owner independently of the launcher or initiating process. Neither
owner teardown nor recovery handoff may free or recycle arena storage while a
lease, snapshot, release permit, or quarantine record refers to it.

`snapshot()` takes the pending lock, validates sentinel shape, count, every
descriptor and every link before dereference, and returns an immutable owned
snapshot. It must not invoke callbacks or mutate list/mode/backing state.
`detach()` consumes the matching lease only after snapshot validation and
produces a typed token; it does not make pages reusable. A release permit is
issued only after explicit clear success and TLB completion for the exact
snapshot identity and ranges. `drain()` accepts that permit and a full batch;
any mismatch, later-invalid node, stale generation, failed/unknown clear, or
capacity violation rejects the entire batch, performs no mutation/callback,
and places it in durable quarantine. Quarantine retains `PM_PENDING_FREE`,
descriptor and backing ownership, exact error identity, and retry/terminal
phase.

## Unsafe and concurrency invariants

1. No raw `next`, `prev`, or descriptor pointer is dereferenced until its lease,
   generation, membership, and remaining count are validated. A physical scalar
   may then be inspected for alignment and checked range arithmetic, but the
   physical target range is never dereferenced by inventory validation.
2. The pending lock and owner lease exclude enqueue, begin, detach, drain,
   interrupt/reentrant mutation, and competing recovery for the snapshot.
3. Snapshot validation is all-or-nothing; callbacks cannot observe a partial
   release, and callback reentry cannot borrow the mutable list.
4. Lease, snapshot, and permit identities survive owner/launcher departure;
   teardown cannot silently revoke them or reuse their serial/generation.
5. Clear failure, timeout, unknown completion, TLB incompletion, or alias
   drainage uncertainty preserves mapping, backing, mode, and quarantine.

## Required negative matrix

Reject before dereference or mutation: null/one-sided/malformed sentinel;
zero, negative, overflowing, or over-capacity count; repeated, dangling,
foreign, stale-generation, wrong-arena, two-head, self, or cross-inventory
cycle; non-pending mode; unaligned/wrapping/overlapping/foreign physical
range; descriptor/count mismatch; stale OS/VM/transaction identity; competing
or nested begin; interrupted/replayed/late completion; wrong snapshot digest;
failed/unknown clear or incomplete TLB; callback panic/reentry; owner teardown;
and a later-invalid node after an initially valid prefix. Every negative must
assert zero callbacks and zero source-list, descriptor-mode, or backing mutation.
Only separate quarantine metadata may be created or updated, and it must retain
the unchanged batch identity rather than rewiring or annotating its descriptors.

## Unresolved authority inputs and source questions

No current producer supplies a trusted VM incarnation, nonreused transaction
serial, descriptor arena generation, or physical-range ownership proof. Before
implementation, reviewers must identify: (a) the durable owner and its restart
epoch; (b) the authoritative MM/VM incarnation and inherited-alias lifetime;
(c) who allocates and persists descriptor generations; (d) the lock's IRQ,
reentrant, and recovery-worker semantics; (e) the exact clear/TLB/alias success
acknowledgement; and (f) how quarantine survives OS destruction without a
reference cycle. These are unresolved inputs, not invented producers.

## Required independent gates

Two independent source reviews must confirm ABI/layout safety, ownership and
restart identity, checked arithmetic, pre-dereference ordering, lock/IRQ and
callback discipline, no-mutation rejection, and clear/TLB permit semantics.
An independent model/reference packet must cover the full negative matrix,
later-invalid atomic rejection, repeated drain, retained backing, stale and
late completion, owner departure, and quarantine recovery. Only after those
reviews may a narrowly allowlisted compile-only integration packet be proposed;
it must retain candidate-12's focused-equivalence-only label and grant no
production acceptance.
