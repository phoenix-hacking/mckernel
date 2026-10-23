# Private M14-02-04 idle orchestration implementation brief

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Owner scratch_growth_prepare; private source preparation only. Exact write set
is the NEW idle-orchestration-1/ subdirectories under this evidence packet and
matching HOST packet. Private postimages only: kernel/process.c,
kernel/include/sched_helpers.h, kernel/rust/sched_helpers.rs. No canonical edit,
235 image/profile/SDK mutation, root, Docker, guest, full production TU or heavy
build. Existing idle scan staging/failure/27-source review and original3-file
activation packet remain unchanged. No recursive agents or model fallback.

M14-02-04 directly names runqueue selection, wakeups, idle transitions,
migration/affinity and post-switch sequencing. Its first finite ready slice is
the existing idle scan, whose current10972 production/default/native gap is
already documented. This independent implementation addresses the remaining
idle() state/control ordering around that existing Rust scan. It does not port
or change schedule(), arch_switch_context(), FP state, or post-switch release.

Invariants: capture v/monitor as the original entry does; release the inherited
runq lock with exact saved irqstate; RUNNING→IDLE before enabling interrupts.
Each iteration: current thread STOPPED→schedule→re-read current thread RUNNING→
disable interrupts; migrate if requested, re-read flags then clear only that bit;
for captured CPU IDLE/RESERVED lock runq, invoke existing exact-running scan,
set RUNNING only on success, unlock; re-read status before deciding to halt.
Idle path preserves consolidate→zero→monitor-IDLE→current-INTERRUPTIBLE→safe-halt→
monitor-KERNEL→wrapping unsigned counter increment→re-read current-RUNNING.
Other path enables interrupts. No pointer ownership or allocation is added.

Rust owns initialization, one bounded iteration and the infinite production loop.
The C-selected consumer only supplies C-produced offsets/constants and existing
primitive function addresses. The original complete C idle body is retained
unchanged under the existing PROCESS_HELPERS fallback selection. New callbacks
are ABI types/descriptors, not new compute-C implementations. Reuse existing
Rust/public primitive bodies and the existing Rust zero-free bridge; any required
current-CPU callback bridge is Rust. All other C bytes must remain identical.

Unsafe ABI: valid captured CPU/monitor and valid current CPU/thread remain live
under the original scheduler/IRQ contract; circular runqueue scan remains locked;
immutable valid offset/callback descriptors, LP64 pointers/unsigned long,
four-byte C int status and unsigned-int flags, unsigned-long monitor counter.
Use raw volatile loads/stores for kernel mutable state; no Rust references to
thread/list/CPU/monitor objects. Preserve exact callback order and re-reads across
schedule/migrate/unlock/halt. No corruption/null recovery or stronger concurrency
guarantee is introduced. Actual production C assertions/producer header metadata
and pinned image proof remain mandatory before canonical/native acceptance.

Next executable observation: ordinary actual-body C/Rust state+callback-trace
fixtures using actual production header layouts and C-produced offsets; empty,
stopped/spin-only/running queues, IDLE/RESERVED/other CPU states, migrate/lock/
unlock mutations, changed current-thread pointers and monitor counter wrap.
Tests never execute real IRQ/halt/lock primitives. Reuse earlier scan parity,
not another broad census. CPU6 or explicitly granted CPU0, one job,2GiB AS,
60CPU,90wall+6 grace,32MiB FSIZE, Rust1.92/codegen1/2MiB Rust stack; inherited
NPROC. No512MiB retry. Preserve all exact commands/streams/failures. One failed
candidate plus one bounded correction per new family, then expert escalation.
Earlier missing-cls.h diagnostic family is already corrected and must not recur.

Focused independent ownership/ABI/order review precedes any canonical integration;
the dispatcher must issue a precise canonical write brief then separate pinned
production consumer/default-link/image/native release at a quiescent boundary.
No source/mock retirement credit; full M14 is separate from practical35/35.
Stop on new service/auth/policy error, selected usage guard or unresolved lifetime
invariant; never automatically replay or widen a rejected request/profile.
