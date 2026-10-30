# Independent selected perf composition source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **CONDITIONAL SOURCE DESCRIPTION ONLY; NOT A BUILD OR EXECUTION RELEASE**. This review concerns the exact private source recipe and its proposed command arguments. It grants no compiler, linker, guard, native execution, ABI, functional or M14 acceptance. No test or workload was run for this review.

## Bound inputs

- `SELECTED-PROFILE.SOURCE-ONLY.json`: SHA-256 `e3982185d18639c8874b009ffc20d23cb287fc1d2c607908049a5df758d3b13f`.
- `nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch`: SHA-256 `595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a`.
- `perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch`: SHA-256 `7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345`.

## Selection and object scope

The proposed command description adds Rust `f03_perf_entry_candidate` and C `MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL` together. The stated Rust argv also includes `enable_perf`, sync-child, leaf and perf-allocation provider cfgs; the stated C argv includes the corresponding helper, sync-child, leaf and allocation bridge macros. The C `ENABLE_PERF` condition is not directly defined in that argv. Before any real build, resolve the actual generated `config.h` and ordered include closure and bind the bytes proving that condition. Confirm emitted C and Rust arguments and provider identities; source guards cannot detect every independently changed selector or linked provider.

The recipe changes the Rust syscall-policy source, its CMake dependency list, three new Rust modules, and the generic `kernel/syscall.c` source. It calls for rebuilding the Rust crate object and generic syscall C object before a fresh matching link. Reuse of SDK21 and nine other link objects is conditional on fresh exact source, object, compiler, include, flag and linker-input provenance; this review does not establish their current validity. The location-neutral Rust hunks and C `#line` restoration support the stated original metadata intent, but actual selected-object and linked metadata remain unverified.

The proposed Rust argv does **not** enable `f06_do_signal_whole_candidate`. Consequently, the SIGTRAP and atomic signal changes in the 595d patch are inactive in this proposed perf-selected object. They must not be counted as built, linked or behaviorally verified by that profile.

## Witness and held scope

The 7aaa C patch contains witness source text under a separate witness macro, while the proposed production C argv leaves that macro off. The Rust witness-only patch is separate. Use distinct controlled witness objects, exclude them from every production/default link, and later verify actual production objects or artifact for witness symbol and section absence; a source/argv description alone does not establish that result.

The reviewed patch hunks do not alter the held generic-C request or the separately excluded execve work. Baseline command arguments include preexisting selectors outside this patch's changed regions; they neither establish a new assignment nor resolve the retained service hold. Preserve the hold and do not replay the rejected request or equivalent work. The source recipe also leaves Root70 ownership/resource reconciliation and operation-specific review open before any physical action.
