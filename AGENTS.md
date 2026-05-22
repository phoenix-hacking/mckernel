# McKernel Rust Migration Agent Notes

Updated: 2026-05-22

## Mission

This repository is migrating McKernel from the traditional CentOS-based
deployment to Rocky Linux 8.x while porting McKernel-owned implementation logic
from C to Rust. The active target is smp-x86 / x86_64. Arm64 is deferred until
the x86_64 path is stable.

Focus porting effort on McKernel-owned software. Do not spend migration
iterations on externally owned or third-party software unless the change is a
small build/ABI boundary needed to keep McKernel validation working. Treat IHK,
Linux kernel APIs, bundled third-party libraries, and toolchain behavior as
interfaces to preserve rather than porting targets unless the user explicitly
asks for that scope.

The Rust migration is intentionally incremental:

- Keep public C headers, exported symbol names, syscall numbers, ioctl values,
  IKC packet formats, and linker-visible entry points stable.
- Introduce Rust behind existing C ABI surfaces first.
- Preserve C fallback builds throughout the migration.
- Keep allocation/free, refcount mutation, lock/list mutation, page-table
  mutation, page I/O, sysfs IKC exchange, procfs buffer mutation, and user-copy
  in C until there is direct runtime coverage for those bodies.
- Prefer large, coherent helper/lifecycle batches only when they can be built
  and equivalence-tested without weakening fallback behavior.
- Each active migration iteration should target a meaningful 3-5 percentage
  point functional ownership improvement in the subsection being worked. If
  safety, runtime coverage, or ownership boundaries prevent that, state the
  reason clearly and choose the largest safe McKernel-owned slice instead.
- Recent long-running goals are measured as aggregate functional percentage
  points across the dashboard rows, not as literal whole-tree LOC percentage.
  The latest verified run added +34 aggregate points toward the requested +135
  campaign, leaving 101 requested campaign points still to earn with verified
  code. Count only verified, McKernel-owned movement; do not inflate
  percentages with external software, third-party code, or unverified high-risk
  mutation.

## Safety Rules

- Do not run scripts or commands that reboot the OS or force a VM reboot.
- Treat `mcreboot.sh`, reboot advice in logs, and any host reboot command as
  unsafe unless the user explicitly approves it for that run.
- Non-reboot validation is allowed: formatting, C fallback/Rust builds,
  equivalence tests, ownership report gates, and module-load smoke tests that
  do not reboot the host.
- Stop on the first failing validation step. Record the failing command,
  environment, and short error summary in `kernel.log` before making unrelated
  changes.
- The worktree may already be dirty. Do not revert changes unless the user
  explicitly asks for that exact revert.

## Current Rust Ownership Baseline

The dashboard below is a functional-area estimate from `overview.txt`, not a
strict line-count. A conservative mechanical LOC baseline is available with
`scripts/rust-ownership-report.py`.

| Area | Rust % | Status |
| --- | ---: | --- |
| Rust build/link foundation | 95 | Rust objects build and link into `mckernel.img`; user tools link Rust helper objects; IHK Linux-module Kbuild links Rust helpers into `ihk`, `ihk-smp-x86_64`, and `mcctrl`; Rust-linked module-load smoke has passed. |
| ABI/layout foundation | 50 | Shared kernel/user structs plus private process/thread lifecycle, wait/futex, timer, `timeval`/`rusage`, IHK monitor/register/resource, and host Linux device/OS/file layouts are covered; broader lifecycle layout remains before mutation-heavy Rust ownership. |
| Shared primitives | 84 | rbtree, llist, plist, waitqueue init/entry/list core, wake scheduling predicate, string/memory leaf helpers, numeric parsers, bitops, bitmap, parse, zero-area search, and region helpers are Rust-owned. |
| x86_64 memory management | 35 | Classification, NUMA/page queries, splitability, page-attribute conversion, PTE value shaping, page-size PTE validation/value selection, early allocator arithmetic/exhaustion checks, page-table index calculation, walk-bound calculation, split-large-page preparation/entry arithmetic, VM range validation, memory-policy validation, and selected pager/object sizing helpers are Rust-owned; page-table mapping mutation, TLB-sensitive mutation, and user-copy remain C. |
| Page allocator | 38 | Rbtree helper cluster, bitmap-backed no-lock allocator internals, init layout/end/count calculation, tail-map reservation, destroy-page count, NUMA free/alloc helpers, free-path policy, and Linux zero-request action selection are Rust-owned; locks/logging, CPU-local cache fast path, allocator lifetime, and IKC zero request side effects remain C. |
| Process/VM management | 72 | Wait/clone/ptrace/VM policy, fork VM/thread metadata copy, address-space release and PID detach mutation, range-cache/lookup relation decisions, CPU-set fallback, mckfd decisions plus push/pop-head mutation, TID-table scan/index decisions, TID slot release/replace writes, sigpending list pop/unlink, process/thread list add/detach helpers, terminate child cleanup list unlink/reparent mutation helpers, thread report-list attach/detach mutation helpers, ptrace main-thread attach/detach reparent helpers, ptrace detach/wakeup state and pending-signal cleanup helpers, wait signal-flag and exit-status reap mutation helpers, terminate/wait report-thread release cleanup helpers, optional ptrace/fp cleanup gates, and lifecycle/refcount predicates are Rust-owned; broader child-list orchestration, rusage aggregation, broad process lifetime mutation, signal forwarding, and full wait orchestration remain C. |
| Syscall core | 72 | SysV shm, prlimit, scheduler, syscall/range validation, credential-refresh forwarding gates, requester-TID and preempt-disable gates, getpid/getppid/gettid/set_tid_address return shaping, memory-policy, mmap/brk/mincore, mprotect split/write-change decisions, signal/time, ptrace/process-vm, wait, execveat, clone, futex policy helpers, bounded wait/ptrace/termination/signal list rewiring, pending-signal delivery/offload-interrupt classification, ptrace wakeup/siginfo/eventmsg result classification, ptrace request dispatch classification, wait/reap result-shape classification, getrusage dispatch/update classification, process-exit status/siginfo classification, terminate cleanup/reparent action classification, clone spawn/TID/TLS/reparent result shaping, and ptrace detach signal-forward gates are Rust-owned; top-level syscall dispatch, user-copy, Linux forwarding, locks, allocation, register/memory access, signal delivery, child-list mutation, rusage aggregation, and high-risk handlers remain C. |
| Scheduler/timers/wait/futex | 39 | Waitqueue init/entry/list core, wake scheduling predicate, bounded runqueue/migration list rewiring plus runqueue length updates, timer spin-sleep/runqueue/remaining-time arithmetic, futex key matching and key preparation, syscall-offload scheduling decisions, and scheduler/futex/signal/timer policy helpers are Rust-owned; callbacks, locks, wakeups, IPIs, timer queues, context switching, and futex queue/wake internals remain C. |
| procfs/sysfs/xpmem/file objects | 100 | XPMEM and file/dev/procfs/sysfs/pager decision-helper surface is Rust-owned through multiple batches, including procfs cmdline/comm helpers; this is not full subsystem ownership because allocation, refcount mutation, lock/list mutation, remap/page-table mutation, page I/O, procfs buffer mutation, sysfs IKC exchange, and user-copy remain C. |
| host/IKC/mcctrl/IHK modules | 61 | Context only unless explicitly in scope. Rust helper linkage is active for `ihk`, `ihk-smp-x86_64`, and `mcctrl`; many host driver, SMP, sysfs, IKC policy, and mcctrl helpers are Rust-owned; lock/list mutation, device allocation, memory registration, IKC exchange mutation, broad allocation/lifetime ownership, and kernel object lifecycle mutation remain pending. |
| User tools | 83 | `mcstat`, `mcexec`, `ihklib`, `mcinspect`, `eclair`, and crash-extension helper surfaces are substantially Rust-owned; device I/O, ioctl handling, DWARF/BFD walking, crash command orchestration, GDB process/socket orchestration, daemon/thread/event-loop mutation, dump NMI side effects, register/memory reads, and most IHK command mutation remain C. |
| Rocky runtime integration | 82 | Rust McKernel image and focused Rocky smokes have passed in prior runs; this pass did not run boot or reboot-capable validation. Wider runtime/performance coverage remains pending. |
| arm64 | 0 | Deferred until x86_64 stabilizes. |

Honest current distance: the non-arm64 dashboard average is 67.6%, while the
McKernel-owned core rows in this table average 61.3%. The conservative
mechanical LOC share is 16.0% Rust implementation. The functional percentages
track verified Rust-owned surfaces; they are not a claim that mutation-heavy
kernel bodies are already fully Rust.

## Distance To 100

| Area | Current | Points To 100 |
| --- | ---: | ---: |
| Rust build/link foundation | 95 | 5 |
| ABI/layout foundation | 50 | 50 |
| Shared primitives | 84 | 16 |
| x86_64 memory management | 35 | 65 |
| Page allocator | 38 | 62 |
| Process/VM management | 72 | 28 |
| Syscall core | 72 | 28 |
| Scheduler/timers/wait/futex | 39 | 61 |
| procfs/sysfs/xpmem/file objects | 100 | 0 for helper/decision surface; mutation bodies still C |
| host/IKC/mcctrl/IHK modules | 61 | 39 |
| User tools | 83 | 17 |
| Rocky runtime integration | 82 | 18 |
| arm64 | deferred | not counted until x86_64/Rocky stabilizes |

## Latest Validated Direction

Recent completed work moved private ABI/layout and lifecycle decision helpers
into Rust. Continue from the McKernel-owned parts first:

- Process/thread lifetime layout mirrors, wait/futex support structs, IHK
  monitor/rusage/register/resource descriptors, and private host Linux
  device/OS/file object assertions compile into the relevant targets.
- Address-space release, clone VM/sighand branch decisions, initial CPU-set
  fallback, mckfd duplicate/close decisions, process/thread refcount cleanup
  gates, TID scan/index decisions, TID slot release/replace writes,
  sigpending list pop/unlink, mckfd pop-head mutation, process/thread list
  add/detach helpers, optional ptrace/fp cleanup gates, and TID-release policy
  predicates route through Rust helpers.
- Scheduler runqueue/migration list detach/add-tail primitives and paired
  runqueue length updates route through Rust helpers; C still owns locks,
  target selection, status flags, wakeups, IPIs, timers, and context switching.
- Syscall-side wait, ptrace detach/attach, clone-report, process termination,
  and signal-wait list detach/add/move primitives route through Rust helpers;
  C still owns the syscall policy, locks, reparenting decisions, signal
  delivery, wait status, user-copy, and Linux forwarding.
- Pending-signal deliverability and offloaded-syscall interrupt/terminate
  classification route through Rust helpers; C still owns traversal, lock
  mode, interrupted-flag writes, signal delivery, and termination calls.
- Ptrace wakeup request shape, resume signal source selection, event-message
  eligibility, and siginfo storage target classification route through Rust
  helpers; C still owns ptrace state writes, register and memory access,
  user-copy, allocation/free, signal delivery, and wakeups.
- Ptrace request-to-handler dispatch classification routes through Rust helpers
  for the direct McKernel ptrace cases; C still owns the handler bodies,
  register/user-memory access, user-copy, state mutation, wakeups, and
  architecture fallback execution.
- Wait/reap stopped-source selection, wait status/result ID shaping, signal flag
  clear masks, reparent/detach/release action selection, and wait4/waitid copy
  gates route through Rust helpers; C still owns locks, child-list mutation,
  rusage aggregation, ptrace detach bodies, user-copy, and Linux forwarding.
- Getrusage dispatch/update decisions, maxrss scaling, process-exit code
  decoding, SIGCHLD code selection, ptrace-vs-termsig signal selection, and
  exit-group status encoding route through Rust helpers; C still owns time
  aggregation, IPIs, signal delivery, locking, atomic status claims, and
  user-copy.
- Terminate cleanup active-thread tests, group-exit status shaping,
  report-thread release gates, and child free/reparent action classification
  route through Rust helpers; C still owns the locks, list mutation, child
  release, ptrace detach, memory cleanup, signal delivery, and scheduling.
- Terminate child cleanup now uses Rust-owned list delete-init and child
  reparent mutation helpers while C holds the existing locks and still owns
  release decisions, ptrace detach, signal delivery, and memory teardown.
- Clone spawn/TID/TLS/reparent result shaping now routes through Rust helpers:
  parent/child TID store gates, child clear-TID gates, TLS source selection,
  last-CPU placement gate, remote-spawn detection, and `CLONE_PARENT` fallback
  to pid1. C still owns the writes, allocation, locking, Linux forwarding,
  CPU assignment, process chaining, user-copy, and scheduler handoff.
- Thread report-list attach mutation for clone report-thread setup,
  `ptrace_traceme()`, and `ptrace_attach_thread()` now routes through a
  Rust-owned offset-based helper while C holds the existing locks and still
  owns `hold_thread()`, release calls, ptrace state writes, signal delivery,
  allocation/free, user-copy, Linux forwarding, CPU placement, and scheduling.
- Thread report-list detach/retarget mutation and main-thread ptrace-detach
  reparenting now route through Rust helpers while C keeps the same locks and
  still owns ptrace state reset, debug-register free, signal forwarding,
  zombie reporting, release calls, user-copy, Linux forwarding, and scheduling.
- Terminate/wait report-thread release cleanup now uses Rust helpers for
  report-list detach/clear and release-time `termsig` clearing while C still
  owns release decisions, `release_thread()`, ptrace detach bodies, locks,
  signal delivery, allocation/free, user-copy, Linux forwarding, and scheduling.
- Ptrace detach state cleanup now clears ptrace flags, saved-context-valid
  state, and the debug-register pointer in Rust, returning the old debugreg
  pointer for C to free. C still owns `kfree()`, single-step clearing, signal
  forwarding, release calls, user-copy, Linux forwarding, and scheduling.
- Wait stopped/continued signal-flag reap mutation now routes through Rust
  helpers for process and report-thread wait paths while C still owns wait
  selection, status construction, locking, rusage, user-copy, and sleep/wake.
- Wait stopped exit-status reap mutation now routes through Rust helpers for
  thread exit status, process group-exit status, and main-thread exit status
  while preserving WNOWAIT. C still owns wait-source selection, status copy,
  rusage, user-copy, locks, and waitqueue behavior.
- Ptrace wakeup saved-context clear and syscall-trace flag mutation now route
  through Rust helpers while C still owns request action selection, locks,
  single-step setup, signal construction/delivery, wakeups, and user-copy.
- Ptrace resume pending-signal take/clear now routes through Rust helpers for
  sendsig/recvsig pointers while C still copies `siginfo`, frees the pending
  object, sends the signal, and owns wakeup/user-copy behavior.
- Ptrace detach signal-forward and exit-report gates now route through Rust
  syscall policy helpers; C still owns siginfo construction, signal delivery,
  thread-exit reporting, wakeups, user-copy, and Linux forwarding.
- Ptrace attach main-thread reparent/list-add mutation now routes through Rust
  helpers while C preserves the existing parent/proc children-lock split,
  debug-register allocation, hold-thread, single-step, signal, and scheduling
  ownership.
- The latest +30 McKernel-owned lift routes five more bounded surfaces through
  Rust helpers: timer spin/runqueue/remaining-time arithmetic plus futex key
  matching, x86 PTE value shaping and page-size PTE validation/value
  selection, page-allocator init layout and tail-map reservation, address-space
  PID detach plus mckfd push-head mutation, and syscall credential-refresh
  forwarding gates. C still owns locks, allocation/free, user-copy, signal
  delivery, page-table walking/mutation, timer queues, futex wake queues,
  rusage aggregation, and scheduler/context-switch side effects.
- The latest +60 McKernel-owned lift routes eight more bounded surfaces through
  Rust helpers: waitqueue entry initialization and wake scheduling predicates,
  x86 early allocator alignment/exhaustion/next-pointer arithmetic,
  page-allocator init end/count and destroy-page count helpers, fork-time
  process VM/thread metadata copy, getpid/getppid/gettid/set_tid_address return
  shaping, procfs cmdline/comm helpers, and timer ABI layout assertions. C
  still owns locks, allocation/free, user-copy, signal delivery, page-table
  walking/mutation, timer queues, futex wake queues, rusage aggregation,
  scheduler/context-switch side effects, and procfs/sysfs buffer or IKC
  mutation.
- The latest +34 verified slice toward the requested +135 campaign routes
  futex key preparation, syscall-offload scheduling decisions, x86 page-table
  index and walk-bound arithmetic, split-large-page preparation/entry
  arithmetic, syscall requester/preempt gates, `mprotect` split/write-change
  decisions, VM range-cache/lookup relation decisions, page-allocator Linux
  zero-request action selection, and `timeval`/`rusage` ABI assertions through
  Rust helpers. C still owns locks, allocation/free, user-copy, Linux
  forwarding, page-table map/unmap mutation, signal delivery, wakeups, timer
  queues, futex queues, scheduler handoff, and broad lifetime mutation.
- IHK open/release/close/init/exit/minor-registration, register-device cleanup,
  destroy-all-OS candidate/restore, stray-kmsg trim, event-list cleanup,
  destroy callback, and notifier policy decisions route through Rust helpers;
  treat these as already established boundary context, not the default next
  porting target.

Latest documented validation passed:

- `rustfmt` on touched Rust helpers.
- `bash -n kernel/rust/tests/run_equivalence.sh`.
- `kernel/rust/tests/run_equivalence.sh`.
- `git diff --check`.
- `python3 -m py_compile scripts/rust-ownership-report.py`.
- `scripts/rust-ownership-report.py --check-dashboard overview.txt --check-dashboard overview2.txt --top 25`.
- `cmake --build /tmp/mckernel-rocky-rust --target mckernel.img -j2`.
- `cmake --build /tmp/mckernel-rocky-c-fallback --target mckernel.img -j2`.

## Validation Ladder

Use staged validation and stop at the first failure:

1. Source checks: formatting, shell syntax, `git diff --check`, and targeted
   compile checks.
2. Rust/C equivalence: `kernel/rust/tests/run_equivalence.sh`.
3. C fallback build for touched surfaces.
4. Rust-enabled `mckernel.img` build.
5. IHK/module build targets such as `ihk_ko` when host-module code changes.
6. Module-load smoke only when it does not reboot the host.
7. Boot and runtime smoke tests only with explicit user approval for that run,
   because boot scripts may reboot or restart the McKernel environment.

## Next Major Work

At the start or end of every run, describe the next major set of work.

Recommended next phase:

- Continue the remaining +101 points in the requested +135 campaign by
  targeting high-debt McKernel-owned rows first: x86 page-table clear/visit
  decision helpers, allocator CPU-cache/zeroed-list policy before mutation,
  syscall ptrace/getrusage handler body slices, scheduler/futex wake/requeue
  decisions, and process VM-range mutation preflight with synthetic equivalence
  coverage.
- Keep the high-risk orchestration in C until runtime coverage exists:
  process lifetime mutation, child-list mutation, rusage aggregation, ptrace
  detach mutation, scheduling decisions, wakeups, timers, memory registration,
  IKC exchange, sysfs object creation, page-table mutation, page I/O,
  user-copy, and broad lock/list ownership.
- Continue object/file/procfs/sysfs conversion only where runtime coverage can
  exercise the path: file-backed mmap, `/proc/PID/mem`, sysfs create/show/store,
  device PFN mappings, and hugetlbfs-backed mappings.
