# Independent perf group-failure source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **CONDITIONAL SOURCE-ONLY PASS** for the exact paired providers and existing lifetime/synchronization contracts. This review does not establish actual selected ABI, compiler/link results, native behavior or M14 acceptance. No compiler, test, physical workload or native execution was run.

## Bound inputs

| Input | SHA-256 |
| --- | --- |
| Bound source `m14-full28-procfs-successor-1/postimage/kernel/rust/syscall_policy.rs` | `7a86da31eba184380922a624c8e9ac562c58c7086f1b6f1d9183fe2d7a44b063` |
| `PREIMAGE-ENTRY.rs` | `9f53dceac6e97cf7c961780362de729b13573f547634e9f98859a494fb651bf7` |
| `f03_perf_entry_candidate.rs` | `d542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5` |
| `f03_perf_group_cleanup.rs` | `0dc2c777c39a9b2f31bc5e3d80badd2d3de8db35bcd0adba205776bb58517293` |
| `SYSCALL-POLICY-APPEND.rs.inc` | `3806e5a170a00bd4699bc01e500e469cace93c37a187aa7522975f1d42695a63` |
| `ENTRY-REBIND.PRIVATE.patch` | `3e6f873b57c0cad24305c13b6450d91b7be7ee1e59b876268cbe49ea9ea3efd2` |

The body comparison against the bound source found one new tracked free on the nonzero group-result branch and the internal entry dispatch to the specialized body; other copied function bodies retain their source statements. The entry rebind changes the called internal function while retaining the preceding counter-failure wrapper. No new `file!()` or `line!()` expression appears in these copied bodies; metadata and dependency preservation still require integration verification.

## Ownership, error and configuration

Under the reviewed matching event allocator, free bridge and x86 counter provider, the event is fresh and remains private through a negative group result. The counter provider only scans its map, with no reservation or event publication. Missing leader or invalid process returns before external list or leader-counter updates. The branch finding a leader with a null list predecessor writes the event's own group-leader pointer but returns before publishing the event into the external list or changing leader counters. The added matching tracked free consumes that allocation once, and `group_rc` is returned unchanged. Counter failure exits earlier and is handled by the retained counter-failure wrapper, so the two added frees do not execute on the same path.

The conclusion depends on the exact selected provider bindings and the pre-existing live, synchronized group and descriptor traversal/leader lifetimes. It does not resolve existing concurrent group access, allocator or caller ownership, nor group-success and later host-fd/allocation/rollback paths. The specialized dispatch is internal Rust and leaves the exported generic helper and callback contract unchanged at source level; actual emitted ABI and linked provider uniqueness remain separate checks.

The new module is gated by `f03_perf_entry_candidate`, `enable_perf` and x86_64, but it directly refers to `super::perf_event_alloc_free_bridge`, whose Rust definition additionally requires `f03_perf_alloc_bridges_selected_candidate`. The exact integrated full28 profile must select that provider; an entry-enabled/bridge-disabled configuration otherwise cannot resolve that Rust item. The compositor must enforce or explicitly constrain this dependency, append the private module without disturbing retained source-location metadata, register its source as a build dependency, and verify actual configuration, bindings and build metadata. These source conditions do not constitute production selection or native proof.
