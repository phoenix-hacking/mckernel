# Independent perf group selector correction review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **PASS_CONDITIONAL_SOURCE_ONLY**. This bounded review addresses the prior missing Rust perf free-bridge selector dependency. It does not accept actual compiler, C/Rust ABI, linked provider, native behavior or M14 retirement. No test, compiler, physical workload or native operation was run.

## Exact inputs

- `SYSCALL-POLICY-APPEND.rs.inc`: SHA-256 `f3c3de8dc22156f50df2bf3865c228fef12da7996eb04701a9c7f857f7d4a629`.
- `SELECTOR-DEPENDENCIES.PRIVATE.patch`: SHA-256 `222a2fd04ef88e6cdcb685d9fe59b34738529e514a1b59ffe8230dea56669880`.
- Prior append preimage: SHA-256 `3806e5a170a00bd4699bc01e500e469cace93c37a187aa7522975f1d42695a63`.

The corrected snippet explicitly rejects `f03_perf_entry_candidate` unless `enable_perf`, x86_64, `f03_sync_child_event_candidate`, `f03_leaf_callbacks_candidate` and `f03_perf_alloc_bridges_selected_candidate` are all selected. The group module is emitted only when the same required Rust conditions hold. With entry selection off, neither the new compile error nor the new module applies, so the entry-disabled source configuration remains unchanged.

The bound `m14-full28-procfs-successor-1/postimage/kernel/CMakeLists.txt` adds the perf-entry Rust selector only in its Linux6.12, x86_64, non-UBSAN path when perf and the experimental option are enabled. In that same configured path it adds the required Rust sync-child, leaf and perf-allocation selectors and corresponding C selection macros. No source contradiction was found for this selected candidate. This is not proof that a later command actually emits those flags or that other independently supplied Rust and C configurations are paired.

The guard checks Rust cfgs only. It cannot detect independently changed C flags, a mismatched provider, alternate linked objects or ABI drift. The compositor must register the module as a source dependency and verify actual emitted C/Rust selectors, provider identities, linked uniqueness and metadata in the integrated profile. The earlier event-release ownership conclusions still require the exact reviewed allocator, counter and free providers and the existing group/descriptor lifetimes and synchronization. The correction changes no event body and grants no native acceptance.
