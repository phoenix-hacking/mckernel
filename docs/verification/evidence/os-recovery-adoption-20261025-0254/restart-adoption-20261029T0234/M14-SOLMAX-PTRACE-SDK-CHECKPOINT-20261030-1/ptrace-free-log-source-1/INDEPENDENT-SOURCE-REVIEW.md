# Independent bounded source review — ptrace tracked free and wakeup logging

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Verdict: **conditional source pass** for preparing an explicitly paired, default-off
compile candidate. No concrete source-level type or preprocessing blocker was
found for the declared configuration. Selection, source origin and dynamic-debug
concurrency are binding conditions, not proven runtime behavior. This review is
not an execution grant, ABI/object/native acceptance, or C retirement.

Reviewed patch SHA256 `d1275f890ccd9af4a1c8a8fbfd0f72ab8181d5066cfd64c3a730c1300c1ba2dc`
and README `53e3bee4f891a32f9cc317365be2bee1ab7bc109fc85c38c8595b7b65b563234`.
Actual source bytes match their manifest: generic C preimage
`4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4`, postimage
`5880f20d84640b7afbdc6b14fbc86369d5ec2e68dde1a8d35f111ad28d65b0f4`;
Rust policy preimage `11d9d9e14c6c4ee3d593083ce18137414a7780c23507a44fb0834937fa9618e4`,
postimage `543c93628de9565bae3d202589f1155d841f854bcf9830f52bcb6430c9b02a66`;
new logger `4ef213da88797997bf7d7743d651fda6bfc0a090656eaf24211f522b1400cf61`;
reused free module `b5793ef0ee2b837e356917c070a8931de5f893463190deea469641dd1e38e0f0`.
The patch changes only the wakeup callback's C selection and fallback, Rust
module declaration, and new logger; it does not modify do_kill, exec, or held
lifecycle/direct-TID/terminate-host work. The tracked-free body/selector already
exist in the baseline and are not newly written by this patch.

Tracked free requires C `MCKERNEL_RUST_SYSCALL_POLICY_HELPERS`,
`MCKERNEL_RUST_F03_LEAF_CALLBACKS`, `MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119`
and x86_64, paired with Rust `f03_leaf_callbacks_candidate`,
`f03_ptrace_kfree_profile_119` and x86_64. The C callback and Rust
`unsafe extern "C" fn(*mut c_void)` have the same argument/result type; Rust
passes the same pointer, source bytes and selected CInt line to the existing
`mem_helpers::kfree_tracked`, which calls `_kfree`. The real caller passes the
cleanup return directly to the callback, including its possible null value;
the port does not establish allocation ownership or null handling independently.
The filename literal is `/src/kernel/syscall.c`. The immediately preceding
conditional line resets yield 4657 when all of OFFLOAD + POLICY_HELPERS +
DISPATCH_CONTEXT are enabled, otherwise 4664. The source adapter independently
selects Rust `f03_ptrace_kfree_dispatch_origin`; no automatic cross-language
check enforces it. In particular, selected final data32 flags require this cfg;
the build must bind it and the actual C filename. C default-off/fallback remains.

Wakeup log C guard requires POLICY_HELPERS + LEAF_CALLBACKS + x86_64 +
`MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG`; Rust requires leaf cfg + x86_64 +
`f03_ptrace_wakeup_log_candidate`. Those guards are not intrinsically paired:
if C helpers are off while the Rust candidate is on, the fallback remains but
the Rust provider and descriptor also exist. The operation profile must select
or disable both sides consistently and avoid duplicate/unused descriptors. The
C static assertion compares `MCKERNEL_F03_PTRACE_WAKEUP_DDEBUG_FLAGS` to the
actual TU's `DDEBUG_DEFAULT`, and Rust `env!` accepts exactly ASCII `0`/`1`;
the profile must supply the identical value to both compilation commands. The
original header defines default 0, while `DEBUG_PRINT_SC` can change it to 1;
no assumption about alternate configurations is warranted. Event4 alone checks
flags; the original format and two C int varargs are preserved. The descriptor
source field `/src/kernel/syscall.c`, function `ptrace_wakeup_log_bridge`,
null fmt and logical line 24429 match the fallback's `#line 24424` dkprintf;
the unconditional `#line 24433` preserves the next source position.
`Ddebug` is repr(C), asserted 32-byte size, 8-byte alignment and word offset24;
source alone cannot prove C bitfield encoding, section retention/order or final
relocations. The exported function's Rust visibility permits the unmangled C ABI,
but actual object/link uniqueness is a compiler check.

Concurrency condition: the actual `dynamic_debug_sysfs_store` in `debug.rs`
updates descriptor `line_flags` without a lock in that function, while the new
logger reads the same mutable word via `read_volatile`. Volatile is not atomic
or synchronization. The existing C callback also reads flags without a local
lock, but that does not establish a Rust race-free contract. A supported runtime
configuration must demonstrate external exclusion of overlapping descriptor
writes and callback reads, or receive a separately reviewed compatible fix;
source review does not invent such exclusion. Independent review must also prove
that the mutable tracked-free filename pointer is not written and ownership is
transferred once at all actual callers.

Before using this selection, use the exact admitted C TU and Rust crate commands
and their actual SDK configuration to: (1) preprocess the C fallback with
free selector off and both dispatch-origin branches, retaining the resulting
`kfree_tracked` file/line arguments and verifying `/src/kernel/syscall.c`,
4657/4664; (2) run C preprocessing with `-dM -E` to determine `DDEBUG_DEFAULT`,
then compile selected and fallback logger branches and both Rust cfg/env modes,
including intentional mismatch failures, so no one-sided selection passes;
(3) compile a separate C type/layout witness for `void (*)(void *)`,
`void (*)(int,int,int)`, `struct ddebug` offsets/size/alignment and debug default,
and compare the real Rust ABI/object; (4) inspect actual `readelf -Ws -SW -rW`
outputs and link map for the one strong selected provider, C fallback exclusion,
32-byte writable retained `__verbose` record and relocations; compare the full
unaltered original389 registry tuples and demonstrate dynamic-debug updates and
0/1/other-event behavior in an appropriately released test. These are future
checks, not claims that any compiler, test or native run occurred here.
