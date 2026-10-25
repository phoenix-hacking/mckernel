Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source preparation is complete. No compiler, fixture, Docker, root or guest command
has run. Root's current physical acceptance and ordinary compiler grant remain
prerequisites; this document grants neither.

The private `candidate/kernel/process.c` retains the whole original `debug_log`
fallback and selects the Rust symbol under `MCKERNEL_RUST_PROCESS_HELPERS`.
`candidate/kernel/rust/process_helpers.rs` appends the four-case traversal entry
and two focused process/thread traversal helpers to the exact current snapshot.
Both source diffs are independent of earlier COW fragments and preserve existing
FP/process correctness fixes and all current page-fault ports.

The exact four argv arrays are in `EXACT-DEBUG-PARITY.NOT-GRANTED.json`: GCC9
compiles the actual original C oracle, pinned Rust1.92.0 emits a `no_std` object
with one codegen unit, GCC9 links both objects and the fixture runs once. Its
stdout retains every C/Rust output and per-case lock trace, followed by:
`PASS debug_log actual-C/Rust parity: 14 cases, output and lock order`.

Root must create `ROOT-GRANT.DEBUG-PARITY.json` with `scope`, `CPU: 0`,
`ordinary_jobs: 1`, `aggregate_AS_bytes: 536870912`, the current `recipe_sha256`
and `runner_sha256`, `physical_clearance_accepted: true` and `physical_clearance`
containing the actual accepted receipt's exact `path`/`sha256`/`bytes` binding.
This source packet contains no such grant. Service/billing controls remain root's
active controls; the runner does not replace them or enforce historical included
usage stops. After the grant, the next exact invocation is:

```
/home/holden/anaconda3/bin/python3 /home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-process/new-window-source-1/run_debug_parity_once.py
```

The runner uses CPU0, one child at a time, parent AS64MiB plus child AS448MiB
(aggregate at most512MiB), one codegen unit and fresh exclusive output/capture
paths. It reuses h990's unchanged owned capture functions and exact helper hash;
each command retains argv, stdout/stderr, child birth/wait/join and group census.
The first unexpected result stops and retains failure. No automatic retry or
memory-limit increase is allowed if the pinned compiler cannot fit this ceiling.

The fixture uses extracted original C and the exact appended Rust body with mock
layouts. It checks behavior, with original C as oracle. Empty and populated hash
tables exercise all four modes, unknown selectors, pid1 omission, first/last hash
buckets, multiple entries, high-bit ptrace formatting, per-bucket lock order and
reuse of the same lock node. It does not prove production layouts or concurrency.

Then compile the full compute crate and selected plus fallback process consumers
through the existing integration queue. Confirm the selected C object defines no
`debug_log`, Rust defines it once and the linked image resolves that symbol to Rust.
Native diagnostic execution and independent ownership/ABI review remain required
before any whole-file or production credit. Codes 3/4 retain original unlocked
traversal semantics and need the original stable diagnostic context; this port
does not claim an additional lifetime or synchronization guarantee.
