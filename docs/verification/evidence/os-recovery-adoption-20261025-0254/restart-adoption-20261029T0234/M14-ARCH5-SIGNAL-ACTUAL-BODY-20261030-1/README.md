# Functional McKernel signal diagnostic body check

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

`check.py` applies the retained PRIVATE-2 patch to the exact ARCH5 retained source in a temporary directory and extracts the complete `arch_do_signal_core_terminate_result` function verbatim. A host fixture supplies mock context types, allocator, memcpy, dump/termination hooks and a C variadic `kprintf`. It uses the real PRIVATE-2 atomic helper. The passing output and SHA-256 bindings are in `RESULT.txt`.

The actual extracted body emitted exactly 64 correctly formatted default-signal diagnostics in 65 calls, copied the context each time, and invoked successful core termination with the core bit. A PID change reset the budget. Allocation failure published null and skipped the dump; EBUSY and other dump failures omitted the core bit. Five retained atomic helper tests also passed. These host mock types do not prove the kernel ABI, selected linkage, handler-site execution, concurrency of real logging, native behavior or acceptance. No kernel build or guest ran.

Original C resets PID/count at every do_signal entry (including nonlogging paths), checks count at handler and default sites, and increments after formatter return. PRIVATE-2 claims before formatter: serial non-reentrant output is preserved, while formatter reentry and concurrent log calls acquire defined bounded behavior rather than reproducing the original race. A reset concurrent with an older formatter can assign its already claimed output to an earlier epoch; this is not per-PID lifetime accounting. Independent review must assess this deliberate observable difference and the whole combined source.

Read-only symbol searches of canonical arch/kernel sources and retained ARCH5 pre/postimage found the core helper's two consumers only in Rust. Its exported C ABI changes the last pointer's pointee type from int to atomic state. The compositor must apply module, both call sites and the helper change together, and verify combined-source symbols and real build bindings; source search is not linked-ABI proof.

Initial harness attempt used default `rustc 1.60.0-nightly (777bb86bc 2022-01-20)` and failed to compile the unmodified extracted body: E0599 for raw pointer `cast_mut` and `cast_const`. The bounded correction explicitly selected installed Rust 1.85.1; it passed. This is a host fixture toolchain correction, not a candidate-source change. No existing evidence was modified.
