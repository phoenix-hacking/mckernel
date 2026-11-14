Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This handoff uses retained selected sources and actual receipts already inspected;
it adds no file census, execution, percentage or retirement claim.

| Body/boundary | Current state and reuse | Relative remaining effort / qualifier |
|---|---|---|
| gpe_handler / int3_handler / debug_handler / arch_cpu_stop | Actual 4623 controlled C/Rust pairs + 34 real ABI words; existing timing/signal/context/IRQ/HALT cores reused. Optional merged exceptions+wakeup postimages sealed. | Production combined Rust + selected merged TU/partial pending; raw exceptions/DR6/HLT/native high uncertainty. |
| __x86_wakeup | Actual 18000 controlled pairs + 22 real ABI words, selected complete GCC9 CPU TU, allocated existing bridge relocation and partial passed. Reuses current warm-reset/APIC/wait/delay providers. | Production combined proof pending; real AP startup and linked placement of const pointer descriptors remain hardware/native work. |
| x86_stack_frame_log_bridge / x86_print_stack_bridge | Source-only complete two-body successor cd6eef65 uses existing Rust kprintf/__print_stack; actual C definitions and actual Rust imports retained. Literal non-Rust stack fallbacks unchanged. | Small focused tape/real ABI check before combined consumer; no kernel-stack memory execution in proposed tape. |
| ihk_mc_print_user_context | Source-only public-entry successor334ecfb5 calls unchanged existing Rust core/context logger. Exported selected C provider proved. | Small fixture/ABI step, but no current external runtime caller proof in this finite packet; do not invent activation. |
| x86_kprintf_lock_bridge / x86_kprintf_unlock_bridge | Existing Rust debug lock/unlock bodies and actual Rust imports already available; two C wrappers remain. | Small source/typed ABI work, retain exact IRQ/lock span; unimplemented here. |
| handle_interrupt | Known main IRQ dispatch/performance/scheduler lifecycle body. Existing Rust classifier, interrupt_exit and CPU/signal types are reusable components. | Larger ownership transaction: exact perf-list/lock/provider layout and ordering must fit before a full port; no placeholder/private port asserted. |

Current canonical pair remains 5574c151/a44a391c. Optional passed combined source
pair 8f2da039/26a4395f is private and is not implicitly included in the frozen
exceptions-only union3 manifest. Genuine future combined Rust object/sourceproof,
selected merged C object and combined global sets remain NULL. The F04-only
marginal source projection 3091T/583U is not a future root-union result.

Inherited freeze(NULL) remains its targeted HOLD; no fabricated frame or guard-as-
success. Existing accepted volatile mod_nmi_ctx/frame/interrupt_exit proof is kept,
and all original E0609/HOST-memory/preflight/observer histories remain immutable.
Actual current-image/default GCC14 whole-kernel link/native retirement remains OPEN.
Engineering percentage is null. No CPU slot, compiler or runtime is reserved.
