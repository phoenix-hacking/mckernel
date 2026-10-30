# Perf counter-failure source and direct microtest review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **PASS_SOURCE_WITH_BOUND_PROVIDER_CONDITIONS; PASS_NARROW_DIRECT_MICROTEST_PROFILE_WITH_FRESH_ADMISSION**. Independent source and command-envelope review only; no test, compiler, build, guest or native workload was run. This decision does not accept the actual emitted ABI, linked provider selection, physical execution, functional native behavior or M14 retirement. The dispatcher controls admission and the shared resource budget.

## Bound inputs

The parent profile is `docs/verification/evidence/native-cheap-profile-review-20261017.json`, SHA-256 `cd30aaf1caec5da84a7a34716d837181684f4e8be5a6c959f25bb557dd69309f`. This extension is limited to the following inspected inputs in this directory:

| Input | SHA-256 |
| --- | --- |
| `PREIMAGE.rs` | `a4d5450852b27bee664c7bf60ed5633c8dc463ed2ee91e0ca9c9856ca6383de1` |
| `f03_perf_entry_candidate.rs` | `9f53dceac6e97cf7c961780362de729b13573f547634e9f98859a494fb651bf7` |
| `COUNTER-FAILURE.PRIVATE.patch` | `86a71b0381d4471b15704fc9b3cfa1494c87173f2bb4a0cbca1502ca2be2c425` |
| `counter_wrapper_fixture.rs` | `afc8b3023230ca2bd7f3bccd344b3fbf77270e6aa5fe0f9ff2d5e441f621003f` |
| `candidate-wrapper.rs` | `3450bede2497331ad47debc9f7568b962e4b319fff0b95aa680bda3bf9a90e94` |

The paired exact provider source and required selectors are recorded in `RESULT.json`. On admission, verify all those source identities, every hash above, and that the staged wrapper is the verbatim complete `perf_entry_counter_alloc_or_release` function from the candidate. A mismatch stops this profile; do not regenerate or substitute a candidate silently. Changed fixture, wrapper, callback provider, runner or command requires bounded inspection and an appropriate new review before execution.

## Source ownership and ABI decision

In the inspected paired x86 `ENABLE_PERF` source path, `perf_event_alloc_body_result` returns a fresh tracked allocation through its local output only on success. Its initialization writes event-owned storage and self-linked list heads. Mapping callbacks read scalar/boot data without receiving or publishing the event pointer, and the paired x86 `hw_perf_event_init` does not publish it. The selected `ihk_mc_perfctr_alloc` ignores the event and only scans the current thread's `pmc_alloc_map`, returning an index or a negative result; it does not reserve the counter or publish the event. Counter allocation occurs before group linkage, Linux offload, map update and fd publication.

On the negative counter result, the entry-specific wrapper releases the event once through the matching tracked free bridge, then returns the same signed result. The caller's negative branch returns immediately and does not access the released event. The wrapper's `unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt` matches the selected `PerfCounterAllocFn` source type; it changes no binding layout. Source review supports this narrow release only when the selected allocator, initializer, counter and release providers match the bound source and their original thread and allocation lifetimes hold. A different provider that publishes or reserves, or a caller supplying borrowed/shared event storage, invalidates the conclusion. Actual emitted callback types, matching C/Rust layouts, provider uniqueness and selection need integrated evidence. Existing counter selection/publication concurrency and later group/host/fd failure ownership are separate and remain open.

## Direct-Rust profile extension

The retained parent profile names specific Python entrypoints and does not itself admit this direct compiler command or these host-preparation inputs. This extension admits **only** the exact fixture and wrapper above, staged as read-only inputs in one new exclusive run root. The fixture has one in-process test and two mock C-ABI callbacks, launches no subprocess and makes no hardware, network, credential or host-state calls. It tests return values 0, 7, -22 and -12, callback and release counts, and pointer identity; the stub free records rather than deallocates. Its `PUBLISHED` flag is mock state which no callback sets. Those assertions do not prove actual external nonpublication or allocation ownership. This remains a small behavior check, not a kernel ABI, link or native test.

After fresh dispatcher admission, make a new exclusive `/home/holden/mckernel-work/scratch/native-cheap-20261017-XXXXXX` root and fresh private HOME/TMPDIR beneath it. Copy the two hash-verified inputs into a single case directory as `fixture.rs` and `candidate-wrapper.rs`; verify staged hashes and exact extraction again. Use no generated source with different content. Preserve source inputs and do not modify production or shared records. The only child command families admitted are, sequentially:

1. `/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test -Dwarnings <fresh-root>/<case>/fixture.rs -o <fresh-root>/<case>/fixture`.
2. `<fresh-root>/<case>/fixture --test-threads=1` only if compilation succeeds.

The parent profile's pinned Rust compiler SHA-256 `028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1`, `/usr/bin/cc` and system linker dependencies, and taskset/prlimit/timeout identities remain binding; verify identity and version before admission. No substituted toolchain or extra helper command family is approved. The dispatcher must inspect the staging and process-owning runner's exact implementation before first use; it must not invoke other programs or permit unreviewed imports, builds, network, sudo, Docker, modules, guests or hardware. This is a reusable envelope for these exact inputs, not authorization to repeat a deterministic failure or bypass the campaign's convergence rules.

The controlling serial process and descendants retain the parent limits: clean `env -i` with `PATH=/usr/bin:/bin`, `LC_ALL=C`, `LANG=C`, `PYTHONDONTWRITEBYTECODE=1`, pinned `MCKERNEL_RUSTC_1_92` and fresh HOME/TMPDIR; no credential, askpass, loader, Python or compiler override inheritance. Run from `/home/holden/mckernel`, under the existing CPU6 affinity only if it remains in the live allowed set, with an outer 180-second timeout and no more than five seconds of cleanup before killing **only the owned process group**. All children inherit `RLIMIT_AS=2147483648`, `RLIMIT_CPU=150`, `RLIMIT_NOFILE=256`, `RLIMIT_FSIZE=67108864`, `RLIMIT_CORE=0`; at most eight owned processes, with one compiler or fixture family at a time, including installed linker helpers. Do not claim these per-process limits are aggregate enforcement.

Before every run the coordinator must verify current controls, actual affinity and tool identity, reserve one CPU share and 2 GiB planning share from the existing aggregate campaign budget, check the 16-GiB host and 12-GiB scratch floors plus any larger current requirements, and use a disjoint output root. No extra heavy build/guest lease is granted. Keep generated inputs, exact argv, sanitized environment identities, compiler and fixture stdout/stderr, exit status, timeout/termination result and failed attempts under that root for the normal evidence checkpoint. Stop on unexpected descendants or resource growth; do not widen limits. The parent profile's concurrency, storage, evidence, ownership, cleanup and prohibition clauses remain unchanged. This extension does not approve mutation/compile-fail variants or other fixtures without their own admission.
