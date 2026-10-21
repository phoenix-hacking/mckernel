# Exact combined scheduler source; future batch only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Write ownership is ONLY this scheduler-current-combined-source-20261021-1
directory. No shared source, accepted160/compiler capture, frozen6959 image
source, original candidate/failure, Git, resource lease, compile/test/root/guest
or runtime input was changed. The current image route keeps priority and has
no dependency on this new port.

combined.patch and complete candidate/ postimages compose exactly reviewed
mutation8d769da2 plus retained-reference3fbc5a0c on C81404ef3/Rust8c5f6962.
LITERAL-HUNK-UNION.json proves all four literal hunk payloads identical to
their reviewed parents: no extra hunk, logic, ABI, flag or implementation edit.
Only the later Rust hunk's new-line coordinate shifts by38 due to the earlier
reviewed insertion. Both composition orders yield identical full bytes.

| File | Complete postimage SHA256 | Bytes |
|---|---|---:|
| kernel/syscall.c |55e04a1e152d17c83d61280ea436012d8c073c78cb3c62bf9689c670b4021d34|839266|
| kernel/rust/sched_helpers.rs |a5b8ed0f048adcfa6908094f7b8b5d459b9b14aa0ed4b75e5250abe6f8387c57|170508|

The source union preserves the existing default MCKERNEL_RUST_SCHED_POLICY_HELPERS
selection and old C mutation fallback. C supplies its real size/offset ABI to
the Rust mutation body. The retained-reference caller uses the same existing
find/release ABI and original selected target through offload/apply. Both
isolated actual-body acceptances are bound by exact references in the union
receipt: corrected16-case mutation comparison5f9c and retained-reference
7-case acceptance23c21. They do not independently accept the combined source.
Root must obtain focused combined review before guarded shared integration.

## Frozen-image ownership check

OWNERSHIP-AND-FUTURE-COMPILE.json records the actual materializer origins and
distinct devices/inodes for both touched files in accepted160 and frozen6959
private outputs. C's image origin is the accepted private current compiler
materialized-source; sched_helpers.rs comes from the private retained retirement
source. Neither image origin is the live repository. Each actual image output
is a separate copy; both also differ from live repository inodes. Later root
shared integration therefore cannot mutate those frozen inputs. A future
image containing this scheduler union needs an explicit successor source
recipe/review, not relabelling the current four-overlay image.

## Smallest update to the existing future compiler batch

When a successor batch is ready, reuse the accepted CURRENT160 six-stage recipe
in guest-settid-rust-candidate-20261021-1/compile-execution-preparation-1; replace
ONLY the two source rows above in a fresh private materialization. The other158
rows, generated config/header authority, FAM-only lib proof suffix and compiler
toolchain remain unchanged. The proposed two-row successor identity is
25999bf8b2d57ccc64e8c1d7da9107a8e4972179b2d802a9bcb8db0df4c66814.
This is a future metadata calculation, not source preparation/execution release.

Retain both native/legacy whole Rust crates, the two existing fork-selected/
fallback whole-C compiles and unchanged constructor-provider stage. The sixth
whole-C stage already disables SYSCALL_POLICY_HELPERS for settid fallback. Add
only a later -UMCKERNEL_RUST_SCHED_POLICY_HELPERS to that SAME sixth profile so
it also compiles the preserved C mutation fallback; count/streams/resource
budget need not grow. The other two caller C profiles already select the new
Rust mutation body. Preserve every existing fork/settid/FAM/provider oracle.
Add exact one setscheduler_body_result definition in each separate Rust object,
its undefined consumer reference in each selected C object, and its absence
from the combined-policy-off sixth object. This requires a fresh mechanically
bound driver/profile/request/root review; no existing frozen file was edited.

Use the existing one-heavy4CPU/12GiB/no-swap/512task/no-network recipe and actual
root/physical/aggregate admission when that future batch is ready. No new
framework, optional variant, budget expansion, extra stage or new execution
proposal is created here. Keep all failures/retirement receipts. Compiler
success would still be separate from final link/unique default consumer,
matching image/module and native scheduler/application execution. Host numeric
owner/incarnation qualification, scheduler-state concurrency and native/default
retirement credit remain held; no cross-host incarnation protocol is claimed.
