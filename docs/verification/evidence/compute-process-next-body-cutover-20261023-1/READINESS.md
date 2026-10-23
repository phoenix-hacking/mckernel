Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source candidate only; no compiler, app, root or target instruction was run.

Selected actual body: kernel/process.c set_timer(int), 12 lines including signature/braces.
Existing consumers: process_sched_set_timer_bridge in process_helpers.rs (used by Rust wakeup/schedule paths), cls.rs preemption path, and process.c scheduler calls. Public declaration kernel/include/process.h:909 is unchanged. Before: actual full Rust object needs U set_timer. After expected: one Rust T set_timer, no C PUBLIC definition/no U set_timer.

Rust preserves current-CPU lookup before the mutable time_sharing load, existing descriptor address, exact runq_locked signed int, four callback addresses and ignored signed return. It introduces no early return, lock, timer operation or struct layout. Existing Rust timer_set_timer_body_result remains unchanged. C offset table and four unchanged callback bodies become externally visible under existing PROCESS_SCHED_PUBLIC_BRIDGE; fallback remains static and original set_timer body is verbatim inside !MCKERNEL_RUST_PROCESS_HELPERS. C providers are retained ABI boundaries, not newly ported C implementations.

Focused fixture extracts the original C body and actual Rust wrapper and existing timer body. Both wrappers route through a capture-only C shim then the real existing Rust timer algorithm. Host models are explicitly fixture-only. 25,600 valid CPU cases plus25 NULL-CPU cases and125 arbitrary signed provider-return/mutable-global-order cases compare exact args, ordered callback events and final timer state. It models lock/runqueue state; it never executes lock ASM, APIC, root, guest or production state instructions. ABI compile uses actual sched_helpers.h and source-bound exact process.h declaration.

Private exact run_equivalence.sh delta removes obsolete weak set_timer, adds the five provider bindings, changes U set_timer to T set_timer, and updates expected total U593->597. Existing U time_sharing is retained. Broad harness execution has not occurred; these host bindings are not production providers.

Next executable observation: run NEXT-LEAF-RECIPE.NOT-EXECUTED.json once under dispatcher CPU6 grant/accepted990 capture and handlers. Then independently authorize pinned nightly exact78-input production Rust command; it remains NOT_EXECUTED. Whole process.c TU, default kernel link and native call path remain OPEN. No body/whole-file retirement credit.
