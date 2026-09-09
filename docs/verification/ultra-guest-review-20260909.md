# Ultra review: selected native x86_64 guest application paths

This is a source review of the verified signal-module-1 / signal-image-2
baseline, performed after the user's switch to Ultra on 2026-09-09. It is not
a new runtime result. No build, guest, fault probe or native implementation
change was performed for this review. Historical baseline PASS results remain
valid for their stated inputs and assertions. The findings below constrain
the next application test scope.

The current [handoff](native-application-ultra-handoff-20260909.md) and the top
of `AGENTS.md` were read. The reviewed paths were the complete native signal
and clone3 adapters, selected syscall-policy bodies and their C callers,
x86 return/exception assembly, relevant process-copy helpers, native pending
zero-page consumer and the selected syscall table/build macros. This is not
a complete audit of the 23,000-line syscall-policy file, legacy process/VM
implementations, or every syscall.

Source line numbers refer to the baseline implementation, unchanged since
`3453edd571152132b19d23b26dad32f4204612e6`. Linux comparisons below refer to the
local pinned source tree
`/work/native-source/linux-6.12.0-211.44.1.el10_2`; host distribution headers
were used only to identify the standard x86_64 ucontext layout and must be
replaced by exact fixture-toolchain header captures in executable tests.

## Selection and established coverage

`kernel/CMakeLists.txt:140` sets `native_linux_irq_work_v6_12`,
`MCKERNEL_NATIVE_CLONE3` and `MCKERNEL_NATIVE_SIGNAL_STACK` together for the
selected native Rust profile. `kernel/rust/lib.rs:56` selects `native_signal`.
The x86 syscall list selects local memory, signal, clone/fork/exec/wait and
futex handlers; slot 435 selects native clone3. C continues to own signal
frame production, XSAVE/XRSTOR instructions, clone lifecycle, process/VM
mutation, user-copy and scheduling bridges. Selection does not imply those
C contracts have become safe merely because their sequencing uses Rust.

The accepted memory smoke checks 256 KiB of ordinary memory, protection
changes without deliberately touching prohibited pages, and unmapping. The
thread smoke checks two successful clone3 children, ordinary mutex/barrier,
TLS and joins. The signal smoke checks a one-argument handler, pending and
unblocking, and two successful alternate-stack returns. None covers malformed
signal frames, robust owner death, invalid futex time pointers, child-TID
copyout faults or process creation. Existing signal unit fixtures replace
XRSTOR with a callback and use `xsave_size=0` for the restart case
(`scripts/tests/fixtures/native-application-signals.rs:343` and `:380`).

## Findings that need decisions or fixes before Spark test execution

Priority P0 means an application-controlled input can cross the guest's
privilege/liveness boundary by the selected source path. P1 means a concrete
contract defect or implementation gap blocks the proposed test category.
These are static findings; no crash or exploit is claimed to have been run.

### G01 — native sigreturn trusts privileged return state and restart metadata (P0)

At `kernel/rust/syscall_policy.rs:10816`, saved RIP, RFLAGS and RSP are copied
from the user frame without canonical-address or flag filtering. The same
function restores the old signal mask verbatim at `:10820`, unlike the
existing `rt_sigprocmask_apply` at `:1764`, which excludes SIGKILL/SIGSTOP.
The return assembly uses the resulting frame directly in IRETQ
(`arch/x86_64/kernel/interrupt.S:178`–`:185`). A bad IRET occurs while executing
kernel code; `arch/x86_64/kernel/cpu.c:2227` panics for kernel-mode #GP.

Concrete triggers are a handler changing the saved IOPL/IF bits or supplying
a noncanonical RIP/RSP. The first can change user privilege or interrupt
liveness; the second reaches a kernel-mode general protection fault. A
canonical address in the kernel region also needs an explicit process-local
bad-return contract, not a claim that the integer being canonical makes it
safe.

At `syscall_policy.rs:10842`, nonzero user-frame `restart` directly invokes
`syscall(frame.num, regs)`. A forged `num=15` with restored RSP pointing at
the same frame recursively invokes sigreturn on the kernel stack. Other
numbers follow ordinary dispatch; the important extra hazard is recursive
kernel execution and trusting private continuation state from userspace.

Minimum prerequisite: copy the frame once, validate the complete native
return contract before publishing state, use an explicit permitted RFLAGS
mask while preserving kernel-controlled bits, exclude unmaskable signals,
and give invalid context/FP input a bounded process-local bad-frame outcome.
Replace the user-controlled recursive restart call with a reviewed
nonrecursive continuation mechanism whose authoritative metadata is owned
by the kernel. Preserve existing legitimate interrupted-syscall behavior.
Pinned Linux `arch/x86/kernel/signal_64.c:50` uses `FIX_EFLAGS`, disables
syscall restart checks through `orig_ax=-1`, and returns a failure into its
bad-frame handling; this supplies the comparison contract, not code to copy
without tracing McKernel's saved-register convention.

Tests after the fix: ordinary GPR round-trip, controlled edits to permitted
flags, attempted IOPL/IF changes, SIGKILL/SIGSTOP mask bits, unmapped and
noncanonical context addresses, forged restart metadata and same-frame
recursive restart. Each bad case runs in a fresh application under a
Linux-side watchdog, has a specified signal/errno result, produces no kernel
panic, and is followed by a fresh HELLO in the same OS. Do not execute
uncontained privileged instructions as the oracle: reading the restored
flags and auditing the return frame is enough for the flag filter.

### G02 — unchecked XSAVE bytes reach kernel XRSTOR; restart bypasses FP restore (P0/P1)

`syscall_policy.rs:10869` copies a user-chosen FP buffer into an aligned kernel
allocation and calls `arch_rt_sigreturn_xrstor_bridge`. The C bridge executes
raw XRSTOR at `arch/x86_64/kernel/syscall.c:402`, with no exception recovery or
validation of reserved MXCSR bits, XSAVE header/component bits or format.
Alignment of the destination is checked by construction; that does not make
the contents valid. Invalid XRSTOR state can #GP in kernel mode and reaches
the panic above. An allocation failure silently skips restore and returns
success. A copy failure returns EFAULT after general registers, mask and
stack state have already been changed.

Separately, the `restart` return at `syscall_policy.rs:10842` precedes the FP
restore block. A restartable blocked operation interrupted by a handler that
changes FP/SIMD state can resume with the handler's state.

Minimum prerequisite: validate the enabled user XSAVE format and masks using
the actual CPUID/XCR0/build contract; add a narrowly scoped fault-aware
instruction bridge returning status; define allocation and partial-restore
failure behavior; restore FP state on both ordinary and restarted return
paths. Review the existing exception-table machinery used by user atomics
before adding another recovery mechanism. Pinned Linux
`arch/x86/kernel/fpu/signal.c:268`–`:327` uses fault-returning user FP restore
and treats non-page faults as fatal to the application; its handling also
accounts for partially modified hardware FP state.

Oracles: exact x87 control/status, MXCSR and XMM sentinel values before/after
ordinary, nested, alternate-stack and SA_RESTART delivery; add AVX only when
the captured guest CPUID and XSAVE mask expose it. Valid FP state must
survive handlers that overwrite those registers. Invalid MXCSR/header bits,
unmapped FP pointers and a page-crossing partial copy must cause the declared
process-local failure, release temporary buffers and allow a subsequent
application. Test the real instruction in the disposable guest as well as
the Rust decision code; a stub callback cannot prove instruction safety.

### G03 — handler action mask and standard ucontext mask are not implemented correctly (P1)

The successful handler path in `arch/x86_64/kernel/syscall.c:1923` adds only
the delivered signal to `thread->sigmask` unless SA_NODEFER is set. It does
not add `action.sa_mask`. A SIGUSR1 handler configured to mask SIGUSR2 can
therefore receive SIGUSR2 while still running. Linux's `signal_delivered`
in pinned `kernel/signal.c:3058` combines the old mask with `sa_mask`, then
conditionally adds the delivered signal.

The `struct sigsp` at `arch/x86_64/kernel/syscall.c:945` and Rust
`RtSigreturnFrame` at `syscall_policy.rs:10703` match the x86_64 ucontext prefix
through its 296-byte header/mcontext area. At byte 296, where the first word
of standard `uc_sigmask` resides, McKernel stores private `sigrc`; its
separate `sigmask` field is at byte 304 and is not populated by this producer.
The old mask is instead put in `gregs[REG_OLDMASK]`, and sigreturn restores
that private choice. A standard SA_SIGINFO handler reading or changing
`uc_sigmask` therefore gets the wrong semantics. `REG_CSGSFS` is left zero.
The handler receives a separately addressed siginfo structure and the
context pointer at `syscall.c:1912`; being able to read REG_RIP/REG_RSP does
not establish compatibility of the entire ucontext. Saved RAX is restored
from `gregs` but then the outer syscall return path overwrites it with private
`sigrc`, so explicit user-context RAX changes also need a defined contract.

Minimum prerequisite: specify and implement a native signal-frame ABI with
the standard consumed x86_64 siginfo/ucontext fields, correct mask placement
and restore, and separate kernel-controlled continuation metadata. Retain
the legacy profile's explicit selection. Before writing recovery handlers,
compile offset/size assertions against the exact payload libc headers and
compare the actual C producer, Rust consumer and ELF selection. Do not use
a test-only private struct to call this ordinary libc compatibility.

Oracles: SIGUSR1 handler sees the pre-delivery mask in `uc_sigmask`, sees
SIGUSR2 blocked when requested by `sa_mask`, queues SIGUSR2 and proves it
executes only after SIGUSR1 returns; SA_NODEFER changes self-blocking only.
Use SA_SIGINFO to verify signal number/code/address on a controlled access
fault and a safe edit of saved RIP to a known recovery label. Verify a
mask edit survives sigreturn and SIGKILL/SIGSTOP remain unmaskable. Include
SA_RESETHAND, nested two-signal delivery and signal-stack disable while active
(EPERM). SA_ONSTACK red-zone and checked frame bounds from `native_signal.rs`
should retain their existing tests.

### G04 — futex timeout reads bypass user-copy and deadline arithmetic wraps (P0/P1)

`do_futex_body_result` in `kernel/rust/syscall_policy.rs:22538` dereferences
the raw user timeout pointer with `read_volatile`. There is no checked
copy, whole-timespec span validation or sec/nsec normalization before those
reads. A noncanonical or inaccessible timeout supplied with FUTEX_WAIT or
FUTEX_WAIT_BITSET can fault in kernel context. A pointer into readable kernel
memory also bypasses the intended user-only copy boundary.

`futex_timeout_ns_result` at `:22440` casts signed components to unsigned,
uses wrapping multiplication/addition, and wraps `target-now` for past
absolute deadlines. `:22588` multiplies nanoseconds by 1000 with wrapping
arithmetic before converting to TSC ticks. The representation also uses
timeout zero for the untimed path, so zero-duration and already-expired
timeouts need a deliberate immediate-expiry representation.

Minimum prerequisite: copy the exact timespec once through the selected
user-copy bridge, validate Linux-supported clock/operation combinations and
timespec values, use checked/saturating deadline conversion with immediate
expiry distinguished from no deadline, and make error precedence explicit.
The monotonic absolute-time bridge at `kernel/syscall.c:22355` sends private
nr202 with a physical timespec pointer and clock ID. The independent host
review traced the matching launcher clock handler and authorized 16-byte
return-copy path in `application_syscall.rs:128`, `mcctrl_process.rs:293` and
`executer/user/mcexec.c:7910`. This is an implemented source dependency;
actual timed condition-variable evidence remains necessary.

Oracles: mismatched value -> EAGAIN, unaligned address -> EINVAL, bad timeout
pointer -> EFAULT, invalid nsec/negative relative seconds -> EINVAL, expired
absolute and zero relative waits -> ETIMEDOUT without queueing indefinitely;
positive wait wakes exactly once. Use a Linux-side wall watchdog rather than
the guest futex implementation to time out its own test. Add real
pthread_cond_timedwait with CLOCK_MONOTONIC after the primitive passes.

### G05 — clone child-TID store bypasses user permissions and full-span translation (P0)

`kernel/syscall.c:7552` translates the first byte of `CLONE_CHILD_SETTID`'s
pointer, then `:7559` stores an int through the physical direct map.
`x86_virt_to_phys_level_result` in `kernel/rust/x86_memory_helpers.rs:1360`
checks PRESENT, not writable or user permission. The path has no full
four-byte user span check. A pointer to a read-only page is therefore written
through the direct map; a pointer in the final 1–3 bytes of a page can write
into the physically adjacent page instead of the next mapped virtual page.
Clone3's checked argument decoder does not validate `child_tid` as writable
memory; it passes that value to this existing lifecycle.

Minimum prerequisite: reuse the guest user-copy/target-VM copy primitive with
correct write fault/COW semantics, complete span and lifetime checking, and
a reviewed Linux-compatible child-start/failure disposition. Audit
CLONE_PARENT_SETTID and CHILD_CLEARTID alongside it; do not fix only the
successful new clone3 adapter and leave legacy clone using unsafe stores.
Pinned Linux `kernel/sched/core.c:5229` uses `put_user` at child startup.
An invalid child pointer does not necessarily mean Linux's parent clone call
returns EFAULT; record the exact reference behavior before fixing the oracle.

Tests: writable, read-only, unmapped and two-page child-TID spans with
independent canaries in both virtual pages; private-COW child versus parent;
unmapped parent-TID storage; CHILD_CLEARTID zero/wake and repeated failed
clone attempts followed by successful joins. Require no unrelated writes,
no stale TID table slot, no procfs leak and correct returned parent/child IDs.

### G06 — robust registration acknowledges success without an owner (P1, known limitation)

`syscall_policy.rs:13084` passes only the length to
`set_robust_list_body_result` at `:1692`, which returns zero for length 24 and
stores no head. `kernel/syscall.c:19250` explicitly documents that killed
threads do not unlock held mutexes. Thus ordinary mutex/barrier PASS cannot
support robust mutex owner-death claims.

Minimum prerequisite for robust tests: implement checked per-thread robust
head registration, bounded exit traversal including `list_op_pending`,
owner-TID compare/update, FUTEX_OWNER_DIED and wake semantics, with faults
contained and no infinite/cyclic walk. Alternatively keep robust operations
an explicit unsupported capability and exclude robust-dependent application
acceptance; do not count the current successful registration as support.
Plain pthread startup must remain working when making the capability policy
honest. A timed robust mutex test must expect EOWNERDEAD after owner exit,
then exercise consistent/unlock and ENOTRECOVERABLE; it must not hang as its
expected behavior.

## Process creation, exec and wait prerequisites

Fork/clone without shared VM sends private two-phase nr56 requests
(`kernel/syscall.c:7501` and `:7633`). The host review identified that the
selected non-null CREATE_PPD ioctl used by the unchanged launcher's fork
bridge returns EOPNOTSUPP. Therefore shells, posix_spawn, fork/exec pipelines
and process-based application suites are a separate integration milestone.
The parent has already allocated a guest child by that point, so failure
tests must verify guest child/VM/cpuid/TID cleanup and the absence of an
untracked Linux child. The rollback labels at `kernel/syscall.c:7664`–`:7695`
need to be traced with the host's exact phase result rather than assuming a
negative fork result proves all ownership was undone.

The guest also rejects CLONE_VM without CLONE_THREAD
(`syscall_policy.rs:21675`). This is a defined McKernel restriction but
blocks Linux's usual CLONE_VM|CLONE_VFORK posix_spawn optimization. Direct
`sys_vfork` uses CLONE_VFORK|SIGCHLD without CLONE_VM (`:10695`), so vfork
must not inherit a normal fork PASS claim. Plan fork first, exec second,
wait semantics third, then posix_spawn/vfork with an explicit supported
contract or an honest unsupported outcome.

Exec uses private nr59 phase 1 to obtain an ELF descriptor, flattens argv/env,
then destroys the old VM at `kernel/syscall.c:7182`; phase 2 failure kills the
process at `:7219`. Verify this irreversible boundary carefully. A missing
or invalid executable before the boundary must return the correct error and
leave the old process usable; a failure after it must terminate and clean up
without resuming the destroyed address space. The phase-1 error negation at
`:7134` depends on the launcher's positive-error convention and requires an
exact test. Accepted exec must preserve specified PID/FD/cwd/mask semantics,
close CLOEXEC descriptors, reset caught handlers/alternate stack and run the
replacement ELF on McKernel. Only then add wait4/waitid status, WNOHANG,
WNOWAIT, ECHILD and reaping tests.

## Memory and syscall provenance test gaps

No additional fault was proven in the reviewed checked native zero-page
detachment/publication code (`kernel/rust/page_alloc.rs:1078`). Existing
evidence does not prove every pending page drained. Add an allocator ledger
oracle that allows bounded caches, records pending/in-flight/zeroed/free
ownership, and verifies anonymous pages are zero after deterministic reuse.
User contents and host page counters need an independent correlation; a
single allocator counter is not an isolation proof.

Add memory tests in this order: zero-filled first-touch and reuse; anonymous
private mappings split at page boundaries; partial mprotect across an unmapped
hole with precise partial-effect behavior; read/write/execute/PROT_NONE
enforcement; host delegated read/write into those spans; partial/cross-page
user copy; private file COW versus shared persistence; truncate/EOF SIGBUS;
munmap followed by same-VA remap with different backing. Protection-fault
recovery depends on G01–G03. Use fixed subranges within a mapping owned by
the test, not arbitrary MAP_FIXED addresses. MAP_FIXED_NOREPLACE is absent
from the selected supported flags (`arch/x86_64/kernel/syscall.c:766`), and
must be explicitly unsupported until implemented.

`clear_host_pte` discards its error in `kernel/syscall.c:5476`, while normal
munmap removes the guest ranges first (`syscall_policy.rs:4302`). The
permanent invalidation failure contract therefore requires an end-to-end
review: an error log alone is not evidence that old host mappings cannot
access memory subsequently reused by another owner. Treat as an unclosed
transport-failure/VM ownership question, not a reproduced stale-write defect.

Any missing syscall-table slot falls through to generic host forwarding at
`kernel/syscall.c:27108`; the table does not form an allowlist. Classify
every syscall consumed by each new payload as guest-owned, intentionally
delegated with translated pointers/private protocol, or explicitly rejected.
Particular review targets before new runtimes include rseq, futex_waitv,
pidfd APIs, io_uring, userfaultfd, pkeys and modern clone/exec variants. Do not
infer support from a nonnegative Linux worker return. Each accepted test
needs actual McKernel PID/TID/RIP provenance plus matched offload routes.

## Recommended bounded execution sequence

1. Ultra fixes and validates G01–G05 for the selected native path, with an
   explicit dependency/reuse review before changes. G06 and process creation
   must have a written capability decision before Spark receives their rows.
2. Add exact libc ABI/header assertions and Linux reference cases in the
   isolated toolchain. Preserve existing legacy/native fixture assertions;
   add new tests instead of relabeling old ones.
3. Rebuild the required image selections and native modules if touched, bind
   symbols/macros/disassembly to source, then replay all four original core
   cases and full controls on the new pair.
4. Run one narrowly scoped new application per attempt. Use 30-second
   Linux-side application watchdogs and the established 300-second QEMU
   cap; run raw malformed frame/pointer cases in fresh guests. On the first
   unexpected failure stop, append the exact command/environment/error to
   kernel.log and preserve the full original capture.
5. After primitive correctness, run 1, 2, 4 and 8 thread application cases
   within the unchanged one-CPU oversubscription profile: condition variables,
   read/write locks, TLS destructors, thread-local errno, blocked I/O and
   signal delivery to a chosen TID. Require deterministic counts/results and
   no residual thread/procfs/pager/worker claims after each case.
6. Advance to fork/exec/wait only after its native host integration passes;
   then choose representative small applications whose observed syscalls are
   covered. Real multicore, MPI and resource-exhaustion stress remain separate
   gates and need new topology/lifetime evidence.

Every test specification must name its prerequisite finding IDs, exact
payload/toolchain hashes, argv/env/stdin, syscall and ownership expectations,
reference oracle, maximum operations/memory/threads, per-case timeout,
cleanup and recovery check, and required full capture. Spark should receive
these resolved contracts and bounded implementation tasks, not instructions
to invent kernel behavior when a test encounters one of the defects above.

## Pre-edit reuse and design: normal native signal ABI, 2026-09-09

The parent assigned a narrower defensive implementation after the review:
normal SA_SIGINFO/ucontext layout, action masks, ordinary FP preservation and
SA_RESTART. Root owns separate return-input validation and fault-safe FP
instruction integration. No malformed-context runtime payload is part of
this implementation subtask. Builds, guests and Git remain serialized by root.

The selected dependencies reviewed before editing are the complete
`native_signal.rs`, the native sigreturn entry and historical return helper
in `syscall_policy.rs`, `struct sigsp`, `isrestart` and `do_signal` in
`arch/x86_64/kernel/syscall.c`, the unchanged x86 SYSCALL/IRET register layout,
and pinned Linux `signal_64.c`, `sighandling.h`, `signal.c::signal_delivered`
and `fpu/signal.c`. Existing `SigStack`, `SigInfo`, `Thread` and
`X86UserContext` layouts are reused. The actual selected copy-from-user
provider and the architecture's existing FP state providers remain the
primitive owners. No second scheduler, process owner, user-copy primitive or
syscall dispatcher is introduced.

The native frame retains the standard 40-byte ucontext prefix and 256-byte
x86 mcontext, followed by 128 bytes reserved for libc's `sigset_t`, with the
kernel's 64 supported signal bits in its first word. Siginfo follows at byte
424. Private `sigrc/num/restart` fields disappear from the native frame;
legacy C/Rust frame layout and the existing regression fixture remain intact.
The producer writes the pre-delivery mask, the syscall's actual result into
saved RAX, and fixed user CS/SS selector information. It updates the live
mask from the prior mask plus action.sa_mask and the optional self bit.

For an interruption already classified restartable by the existing
`isrestart` policy, the producer records a userspace restart context with
RAX equal to the original syscall number and RIP two bytes before the saved
post-SYSCALL address. Reexecution then enters through the ordinary hardware
SYSCALL path after signal return. No user-supplied private syscall number
causes recursive kernel dispatch. Benign tests must prove saved continuation
instruction identity, the original argument registers and a single eventual
operation result. Root supplies the return validation for the saved context.

The new native return consumer copies the frame once, calls a status-returning
FP-restore provider before committing normal register/mask/stack changes,
restores the standard saved mask, and returns the user's saved RAX. Root
supplies the checked FP provider and process-local invalid-frame disposition;
this review subtask does not route unchecked user FP bytes to raw XRSTOR.
The old return helper stays available only as legacy behavior/reference;
new fixtures must bind the newly selected native consumer, not claim the
old helper's historical tests cover the changed selection.

### Prepared implementation and validation handoff

The native frame/normal-context implementation and benign fixtures are now
prepared in the shared worktree. The native consumer returns
`Result<CLong, CLong>` so a legitimate negative saved RAX remains a successful
context return; only `Err` enters root's process-local bad-frame bridge.
Root owns frame validation and the checked status-returning FP provider
before this implementation can be built or accepted. This is not a passing
implementation checkpoint yet.

The dedicated build/reference command, inside the established native
container, is:

```text
python3 -B /workspace/scripts/tests/verify-native-signal-abi.py 1
```

Use a fresh attempt number on every subsequent execution. The helper stores
the complete module/ABI/producer/consumer/fixture inputs and executes the
actual native module with a controlled FP callback. It builds one ordinary
dynamic-libc x86_64 payload and captures compiler/dependency/library identities,
ELF and disassembly. Its three Linux reference modes are:

| Mode | Required behavior | Exact terminal stdout / exit |
| --- | --- | --- |
| `mask-context` | Alternate-stack SA_SIGINFO reads the original mask; action.sa_mask keeps SIGUSR2 pending through the first handler; a standard uc_sigmask edit survives; a saved RAX edit returns 12345 through the triggering raw syscall | `NATIVE_SIGNAL_ABI PASS mask-context\n`, 37 |
| `fp-return` | Handler sees saved x87/MXCSR state, changes x87/MXCSR/XMM0, and the interrupted raw tgkill returns with every selected sentinel restored | `NATIVE_SIGNAL_ABI PASS fp-return\n`, 37 |
| `fp-restart` | Linux-side supervisor observes the blocked one-byte stdin read, sends SIGUSR1, waits for the handler acknowledgement before writing byte a5; the handler sees saved read RAX and SYSCALL instruction, and FP sentinels survive actual restarted read | Ready marker followed by `NATIVE_SIGNAL_ABI PASS fp-restart\n`, 37 |

The restart mode's additional stdout is exactly
`NATIVE_SIGNAL_RESTART_READY\n` (28 bytes); its stderr acknowledgement is
exactly `NATIVE_SIGNAL_RESTART_HANDLED\n` (30 bytes). The controller has a
30-second deadline, tracks only its own unreaped process, and always reaps it
on failure. Root must adapt this same protocol to the unchanged mcexec guest
launch while retaining actual delivered-read/return provenance. No native
guest success is asserted by the Linux reference helper.

These fixtures deliberately cover the legacy x87/MXCSR/XMM0 portion of the
FP ABI. The existing producer does not yet advertise Linux extended-state
software magic/size metadata. Extended AVX context inspection remains a
separate ABI obligation unless root supplies and verifies that metadata.
Do not expand this fixture's result into a claim about every XSAVE component.

## Pre-edit reuse and design: checked native FP bridges, 2026-09-09

Root assigned the additional defensive integration of the native FP-return
and bad-frame bridges. The reviewed selected providers are
`arch_rt_sigreturn_alloc_bridge`/`free_bridge`, `arch_copy_from_user_bridge`,
`get_xsave_size`/`get_xsave_mask`, CPU `initial_fp_regs` capture and
`restore_default_fp_regs`, and `terminate(0, SIGSEGV)`. Pinned Linux
`arch/x86/kernel/fpu/xstate.c::validate_user_xstate_header` rejects unsupported
state bits, compacted format and reserved header contents;
`fpu/signal.c` validates MXCSR against the actual CPU mask and restores through
fault-reporting instruction helpers. These ownership boundaries are reused:
Rust owns pure buffer/size policy, C keeps allocation/copy/free and trusted CPU
metadata, and root owns the exact-PC fault-aware assembly instruction helper.

The new `native_xstate` policy accepts only the captured CPU's standard XSAVE
layout: at least 576 bytes, a bounded exact configured size, XSTATE_BV a subset
of the actual XCR0 mask, XCOMP_BV zero, header reserved bytes zero, and MXCSR
within a mask obtained from actual FXSAVE output (architectural 0xffbf fallback
only when the CPU reports zero). The buffer's user-supplied MXCSR_MASK field
is never trusted. Integer loads use checked byte slices and little-endian
decoding. Full checked user-copy precedes validation and the instruction.

The C adapter allocates enough for a 64-byte aligned copy, retains the original
allocation for every cleanup path, and propagates copy, validation and
instruction failure. It does not silently succeed when allocation fails.
Null user FP state restores the known boot initial state through the same
checked instruction provider; absent XSAVE uses the existing default FP
provider. A configured XSAVE size larger than the currently captured initial
buffer remains an explicit error for default restoration, never silent
retention of handler state. The native bad-frame bridge records a concise
diagnostic and calls the existing process-local `terminate(0, SIGSEGV)`.

No malformed-context runtime payload is created or executed. Pure-buffer
policy tests and benign real FP-preservation tests supply the first validation
layer; root retains control of module/image builds and guest execution.

### Pre-edit follow-up: pending signals after native sigreturn

Independent source review traced the outer `syscall()` pending-signal check:
after sigreturn it still passes syscall number 15 alongside the restored
application RAX. If that saved result is EINTR, the old `isrestart` policy
could classify a newly pending SA_RESTART handler as a restart of syscall 15.
For the selected native producer, explicitly exclude rt_sigreturn before
the SIGCHLD shortcut. The interrupted user continuation already contains its
complete return or restart context. Keep the legacy policy unchanged and
extract the complete selected C policy for assertions in both selections.

Signal protocol attempt 1 failed on a fixture SS packing constant: the
producer's `0x3b << 48` is correct, while the fixture literal used `0x3b << 56`.
Root logged and retained that original attempt. The corrected test continues
to assert the exact ABI word, using the proper shift; this is not a production
behavior change or a passing relabel of attempt 1.

### Pre-edit follow-up: native signal entry targets

The native return checks do not protect the separate IRET into a newly
delivered handler. The reviewed producer writes `sa_handler` into saved RIP
and always pushes the supplied `sa_restorer`; there is no x86_64 kernel
fallback restorer in this selected path. Add one pure Rust target validator
before stack preparation, any user frame copy or live state change. Both
actual targets must be nonzero lower-47-bit canonical addresses within the
configured user interval. Keep the existing supplied-restorer ABI without
adding a new SA_RESTORER-flag requirement. Failure uses the existing native
bad-frame cleanup and process-local SIGSEGV path. Legacy delivery remains
unchanged. Tests are pure policy vectors; no invalid-context runtime payload
is added. Image selection must prove the new call precedes frame preparation.

Signal protocol attempt 2 failed while compiling the exact legacy C restart
policy with `-Werror=sign-compare`: its unsigned-long result was compared with
the signed expression `-EINTR`. Root logged and retained the whole attempt.
The production comparison now spells `(unsigned long)-EINTR`, exactly the
usual arithmetic conversion already performed by C. This is a bounded type
clarification with unchanged values and legacy/native behavior; warning
requirements and policy assertions remain intact.

### Benign guest signal runner and external-forwarding capability boundary

The assigned guest runner reuses the complete current
`/work/run-native-ultra-baseline.py`, with its original source retained as
`/work/run-native-ultra-signal-abi-baseline-original.py` and hashed inside each
new attempt. The separate `/work/run-native-ultra-signal-abi.py` preserves all
original boot/control assertions, eight HELLO applications and the original
signals core on their preceding console window. It then executes the exact
protocol-built signal payload through the unchanged mcexec launcher for
`mask-context` and `fp-return`, with independent schedule, delivery/return,
stdout/stderr, raw exit status, procfs, retirement, invalidation, pager and
actual guest frame/sigreturn assertions. The original four-mode baseline
helper remains unchanged.

The new `native-signal-controller.c` reuses the existing failure supervisor's
Linux-only fork/exec, pipe and `/proc/PID/task/TID/syscall` observation pattern.
It drains both streams concurrently, writes complete streams into guest files
and prints their exact bytes as hexadecimal evidence, enforces a 45-second
child deadline and raw wait status 9472 (exit 37), and kills/reaps only its own
unreaped child on failure. Its supervisor fork is Linux execution and supplies
no McKernel fork capability credit. Direct Linux references for all three
payload modes run inside the same guest, using the same pinned Linux bzImage
and byte-identical payload and libraries as the McKernel launches.

For `fp-restart`, the prepared controller waits for stdout READY, observes one
actual Linux fd-0 read of one byte, sends SIGUSR1 to its owned child, drains
stderr until the exact HANDLED marker, then writes a5 and verifies both full
streams and exit 37. This is implemented for the direct Linux reference. Its
McKernel invocation is deliberately not executed in the initial runner:
native `mcctrl.rs::ioctl` does not implement `MCEXEC_UP_SIG_THREAD` or
`MCEXEC_UP_SEND_SIGNAL`, despite `abi/os_service.rs::handles` routing both
commands to that callback. Both return EINVAL. The unchanged Rust launcher's
`mcexec_helpers.rs::sendsig` treats the failed SIG_THREAD query as non-UTI,
attempts SEND_SIGNAL, then closes the device and exits 1 when it fails.
The independent host review also found no selected native SEND_SIGNAL packet
producer/ACK ownership implementation. Guest-local tgkill acceptance does not
prove this separate external-forwarding path.

The runner records the native restart case as **BLOCKED**, with zero guest
execution/acceptance credit, its exact future oracle and the missing native
forwarding prerequisite. Max must design the versioned descriptor copy/compat
checks, process/TID binding, and owned send/ACK/cancellation lifetime before
enabling it; adding the ioctl number to a match is insufficient. Existing pure
producer/consumer restart fixtures provide bounded context/FP ordering coverage
but do not replace an actual delegated-read restart.

Prepared invocation, to be run only by root inside the serialized pinned
container after the chosen inputs pass:

```text
python3 -B /work/run-native-ultra-signal-abi.py MODULE_ATTEMPT IMAGE_ATTEMPT PROTOCOL_ATTEMPT FRESH_GUEST_ATTEMPT
```

The helper compiles the new controller with `-Wall -Wextra -Werror`, captures
its complete source/dependencies/ELF/disassembly, requires protocol input PASS
and exact payload hashes, retains the unchanged 300-second whole-guest bound,
and captures the original and adapted complete runner sources. No build,
controller execution or guest run was performed by this subagent.
