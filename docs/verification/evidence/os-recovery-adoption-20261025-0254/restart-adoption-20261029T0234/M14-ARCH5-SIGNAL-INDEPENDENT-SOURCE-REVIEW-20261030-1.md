# M14 ARCH5 signal atomic candidate: bounded independent source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is a source-only review of the retained private candidate and actual-body fixture. It does not authorize physical execution, assert production selection or grant M14 acceptance. No test, compiler, build, guest or native workload was run for this review; reviewed files were not modified. The candidate is suitable for coherent source integration only, subject to explicit assessment of the diagnostic behavior change below and the remaining integration and qualification gates.

## Reviewed inputs and SHA-256

Paths are relative to the repository root unless stated otherwise. `E` denotes `docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234`.

| Input | SHA-256 |
| --- | --- |
| `arch/x86_64/kernel/syscall.c` | `b5e9a382491d0f6dc4b71a55f54f76f3d4ca610fa9f81adc60e70ec97a194669` |
| `kernel/rust/syscall_policy.rs` | `07cb4bff5a0a9a0d582ebc18e344e5cf06ccd6fc37005292c757ef0501ea50eb` |
| `E/M14-ARCH5-CUTOVER-1/postimage/kernel/rust/syscall_policy.rs` | `b6852ef318b2cc418773b0063ad797ebebdd2b323363f6bd2de48fc7c0e31213` |
| `E/M14-ARCH5-SIGNAL-ATOMIC-PRIVATE-2/SIGNAL-ATOMIC.PRIVATE.patch` | `c7a87f7a67014f794636857e25729cd59764d5f3fbbf54f54ce8d7ffde46c385` |
| `E/M14-ARCH5-SIGNAL-ATOMIC-PRIVATE-2/f06_signal_log_budget.rs` | `474fbc12b68003d3b79f22c557425f2800f37888da4554c782590acfc90f9a0c` |
| `E/M14-ARCH5-SIGNAL-ACTUAL-BODY-20261030-1/check.py` | `e587f6e13f6e1a5e3c9c5af1ff7751fc617f6b838bdc6aa88532c0c32fd31b7c` |
| `E/M14-ARCH5-SIGNAL-ACTUAL-BODY-20261030-1/RESULT.txt` | `5bd76f12d3a82cfa11f398580df43e85fd82137a25ec119d8aaf9d94503a71f9` |

The first four fixture-input hashes match those printed in the retained result. The fixture applies the private patch to the retained ARCH5 postimage and extracts the complete `arch_do_signal_core_terminate_result` from its `#[no_mangle]` declaration through its closing brace, ending at the next functional-comment delimiter. Its reported six passes cover that body under host mock types and five atomic helper unit tests. The mock body test checks 64 diagnostics in 65 calls, the format of the last default diagnostic, context copy and successful termination, PID reset, allocation failure, and dump-failure termination paths. It does not exercise the actual handler call site, real `do_signal` entry, real concurrent or reentrant formatter, kernel layouts, selected linked consumer or native behavior. Its first attempt with the default Rust 1.60 nightly failed on pre-existing raw-pointer methods; the final host fixture used Rust 1.85.1. Neither establishes the selected kernel toolchain or a kernel build.

## Semantics and concurrency

The C entry resets the shared counter on a PID change even if that entry does not log; it tests the count at each logging site and increments it after the formatter returns. The private candidate retains the entry observation but atomically reserves a slot before formatting. Serial, non-reentrant log decisions follow the original counter behavior. Reentry and overlapping entries can differ: with 63 slots used, a reentrant call can cause the original to emit both outer and inner messages and reach 65, while the candidate reserves slot 64 first and suppresses the inner call. If another PID resets the counter while a formatter is in flight, the original post-return increment charges the new epoch, whereas the candidate's earlier reservation was in the previous epoch. This change needs explicit assessment; it is not exact reentrant equivalence or per-PID lifetime accounting.

The packed atomic PID/count is accessed using relaxed atomic operations, appropriate to this independent diagnostic state rather than publishing other data. The state is bounded to 64 claims during an unchanged epoch, and no lock is held over `kprintf`; PID changes can create new epochs and do not impose a global output bound. Delayed entries claim the then-current epoch. The candidate removes the original counter data race in the Rust path but deliberately changes its observable concurrent behavior. The existing `do_signal` safety comment claiming counter races are preserved becomes inaccurate when this patch is integrated and should be corrected by the compositor.

## ABI, selection and remaining restrictions

The exported `#[no_mangle]` helper changes its last parameter from `*mut CInt` to `*const AtomicU64`. Old callers passing an integer counter are incompatible with the new contract even though both arguments are pointer-shaped. A source search of live `arch/` and `kernel/` found the helper definition and its two Rust calls; this does not prove the absence of generated or linked callers. Integrate the module, entry reset, both logging claims, helper signature and both call sites as one coherent source change. Confirm combined-source consumers, real toolchain compilation, symbol/default selection and matching linked ABI in the applicable integration flow.

The existing source comment on `do_signal` also excludes traced default SIGTRAP because its original info bytes are uninitialized. It retains C selection until that debt and the complete ownership/default/native behavior are resolved and qualified. The signal fixture and this review do not clear that separate restriction, establish native proof or accept the broader M14 conversion.

## Additive correction: later full28 SIGTRAP source

The preceding SIGTRAP exclusion describes the standalone ARCH5 postimage used by the actual-body fixture; it must not be applied generally to the later full28 candidate. The retained full28 UTI-Rust-owned postimage at `E/M14-REMAINING23-COMBINED-BATCH-1/full-cutover-successor-1/complete-input-integration-1/final-profile-1/uti-desc-rust-owner-successor-1/postimage/kernel/rust/syscall_policy.rs` has SHA-256 `d1151a64f122d75816f039481dfe19540825a0cc2f4b5bf69123f182241b60b4`. Its traced path calls `f06_construct_trap_notification` immediately after the SIGTRAP state stores and before notification; the untraced path returns first. The constructor at EOF has the same initialization statements as approved private patch `1005153fa0cb5ffa5e5525ca51d8727a4bbb1a96d7dd1d770b7b3cf342ade139`: zero every byte, then set SIGCHLD, CLD_TRAPPED, thread tid and the thread exit status. It is relocated to a cfg-gated helper, so this is not a claim of whole-file byte identity with the earlier correction postimage.

The retained `final-profile-1/FULL28.EXPLICIT-ON.cmake` (SHA-256 `58940eda8d19f9db808dc0899b459fd5d04e99a17e7848d791919aac07d31b64`) sets `MCKERNEL_ARCH5_CUTOVER_CANDIDATE` ON for experimental compile-only feedback. Its source-only compiler argument delta adds `f06_do_signal_whole_candidate` and `MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE`. Thus the specific uninitialized-info source exclusion is addressed in that full28 candidate, conditioned on the reviewed constructor's lifetime and selection assumptions; actual ABI/layout, ownership, linked selection and native proof remain separate and open. This additive comparison changes neither the original fixture scope nor its test limitations. No additional test or workload was run.
