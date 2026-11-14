# Runnable-thread transport payload source review

`payload-runnable-thread-v1.c` is an additive fault-fixture variant. It creates
one real pthread alongside the main application thread on the existing single
McKernel CPU. The original `stability-transport-fault/payload.c`, all existing
compiled copies, and failed guest attempts remain unchanged. This document
reviews source only; the companion JSON binds its inputs. Compilation,
disassembly, exact Linux/McKernel guest execution and observed scheduling remain
the parent coordinator's work. No application or transport acceptance is claimed.

## Why this variant exercises a different path

The parent reports that guest4 reached the real delegated read and complete
typed BlockedRead observation but physical `req_thread_status` was 0. The
existing physical prerequisite requires 2 and remains unchanged. In the current
Rust offload loop, `kernel/rust/syscall_policy.rs:2800` checks scheduling while
the response remains in progress; `sched_helpers.rs:5232` permits scheduling
when a nonzero-TID preemptible thread has a runnable competitor (`runq_len > 1`),
among its other conditions. At `syscall_policy.rs:2865`, the production path
changes SPINNING=0 to DESCHEDULED=2 and prepares the wait queue before scheduling.
An additional runnable application thread supplies the missing competitor.
This is a source-derived reason to try the fixture, not proof of a future wake
value. Actual PRE_INPUT physical capture must still establish exactly 2 before
the host acknowledges and the controller writes input. No code here accesses
or modifies a request/response wake field, ioctl, physical address or kernel.

## Existing thread capability and its scope

The retained application handoff records the unchanged core thread test with two
clone3 children, TID transfer, isolated TLS, mutex/barrier behavior and joins on
one McKernel CPU. The original fixture is
`scripts/tests/fixtures/native-application-core.c:72`. The checkpoint's boot
profile explicitly enables `hidos allow_oversubscribe`; the retained current
stability baseline record carries that same command line. The new variant
needs only one pthread, with an explicitly requested 256 KiB stack. It makes
no claim that historical thread success accepts a new payload or modified
module. Root must retain the actual current boot, image, launcher, loader and
module identities and observe the extra real guest thread in the new attempt.

## Exact operations and independent expectations

The spinner uses lock-free C11 unsigned atomics; a compile-time assertion rejects
an implementation where those atomics are not always lock-free. It performs a
release store to `spinner_started`, then only acquire loads of `spinner_done`
until completion. No clock, yield, futex, allocation, I/O or function call occurs
in that loop. Pthread startup and its normal return epilogue remain actual libc
operations. Root must inspect the emitted loop for unexpected calls or syscalls.

Main waits for the actual thread's start store before emitting the original
`NATIVE_FAILURE_READY\n`. It performs the same one read(fd0, buffer+8, 16), with
all 32 buffer bytes initially 0x5a. Exactly the middle 16 must become 0xa5;
both eight-byte guards must remain 0x5a. On a successful read and complete
buffer check it release-stores done, joins the real pthread, checks its returned
token, writes `NATIVE_FAILURE_PASS\n`, and returns 37. These remain the original
Linux-reference/recoverable stdout and raw-exit expectations; stderr is empty
for a successful payload. There is no output-derived expectation or new success
normalization. Main does not write done during a pending read, so the spinner
stays runnable through the selected read and terminal quiet observation.

Pthread failures report their returned error number separately from syscall
errno. Every syscall errno is saved immediately after the failed operation.
Failures after a successful pthread creation set done and join when execution
can reach cleanup; join/token failures remain failure. The first diagnostic is
not replaced by a later cleanup diagnostic. The fixture does not retry a
partial/EINTR read or write and does not print PASS after any failed assertion.

Neither atomic loop has an internal clock. Both remain bounded by the unchanged
external controller's preparation deadline (10 s), RET observation bound
(15 s after input), normal overall deadline (90 s), separate emergency-capture
window (up to 30 s), and separate owned-process cleanup (15 s), all under the
independent outer host QEMU deadline (300 s). A stopped/faulted guest cannot
supply its own reliable timeout. No
unverified TSC scale or syscall-based spinner timeout is introduced. In a hard
fault the spinner may never reach its normal return; terminal quarantine and
owned cleanup remain failures/collection facts, never normal-retirement PASS.

## Controller, owner and input binding

The unchanged controller enumerates at most 512 launcher tasks and selects a
unique actual Linux read(fd0,len16), then records and rechecks that task's
startticks. The spinner performs no second fd0/read16, so it does not create a
second eligible reader. No extra controller/UART protocol fields or weakened
identity checks are needed. Existing owner inventories must retain every
additional process/TID/worker record; do not force the old one-thread inventory
onto this payload or drop rows to fit the original example.

The selected-response counter reasoning is unchanged: selection happens after
the new pthread's startup calls, and the main read still uses the unchanged
generic launcher RET(value16, size/src/dest0). The spinner performs no operation
while that selected response is pending. Therefore the selected pager-copy
counter expectation remains zero, with prepublication address counts 0,1,1,1,
release0 and no after-release/duplicate activity. The new attempt must bind the
new payload source/ELF and retain the exact old counter contract as an input;
the older source sidecar alone does not identify this new fixture. Actual
typed/physical evidence must independently check all counters and raw RET errno.

Root should compile only this new payload with the reviewed C11/pthread/Werror
profile, retain source, full command, compiler dependencies, ELF, disassembly
and loader closure, then create a fresh prepared root. No production source or
native module change is required by this fixture. Both guest engines must use
the same new ELF. The real Linux reference, READY/guarded read/PASS/exit37,
actual extra guest thread, real selected worker, unchanged wake2 prerequisite,
terminal ownership/+5s comparisons and complete first-failure capture all remain
required. A compile success or a spun thread does not release the fault gate.
