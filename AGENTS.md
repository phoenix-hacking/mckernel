# McKernel Rust Migration Agent Notes

Updated: 2026-05-23

## Mission

This repository is migrating McKernel from the traditional CentOS-based
deployment to Rocky Linux 8.x while porting McKernel-owned implementation logic
from C to Rust. The active target is smp-x86 / x86_64. Arm64 is deferred until
the x86_64 path is stable.

Focus porting effort on McKernel-owned software. Do not spend migration
iterations on externally owned or third-party software unless the change is a
small build/ABI boundary needed to keep McKernel validation working. IHK host
module conversion is now explicitly in scope; Linux kernel APIs, bundled
third-party libraries, and toolchain behavior remain interfaces to preserve.

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
  The requested +135 campaign target is met with verified code. Post-campaign
  work toward actual 100% completion has added +113 more verified aggregate
  points so far, but the full port is not complete. Count only verified,
  McKernel-owned movement; do not inflate percentages with external software,
  third-party code, or unverified high-risk mutation.
- Mechanical LOC ownership is audit-only. Use it to find remaining C debt, not
  to score progress toward the functional 100% core-category goal.

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
strict line-count. It is the progress score for this goal. A conservative
mechanical LOC report remains available with `scripts/rust-ownership-report.py`
only as a debt inventory.

| Area | Rust % | Status |
| --- | ---: | --- |
| Rust build/link foundation | 95 | Rust objects build and link into `mckernel.img`; user tools link Rust helper objects; IHK Linux-module Kbuild links Rust helpers into `ihk`, `ihk-smp-x86_64`, and `mcctrl`; Rust-linked module-load smoke has passed. |
| ABI/layout foundation | 54 | Shared kernel/user structs plus private process/thread lifecycle, wait/futex, timer, `timeval`/`rusage`, IHK monitor/register/resource, host Linux device/OS/file layouts, and IHK kmsg/event/notifier/aux-call layouts are covered; broader lifecycle layout remains before mutation-heavy Rust ownership. |
| Shared primitives | 84 | rbtree, llist, plist, waitqueue init/entry/list core, wake scheduling predicate, string/memory leaf helpers, numeric parsers, bitops, bitmap, parse, zero-area search, and region helpers are Rust-owned. |
| x86_64 memory management | 84 | Classification, NUMA/page queries, splitability, page-attribute conversion, PTE value shaping, page-size PTE validation/value selection, early allocator arithmetic/exhaustion checks, page-table index calculation, walk-bound calculation, normal/safe page-table walk iteration, callback result folding, optional physical-address skip policy, virtual-to-physical per-level miss/walk/hit decisions and physical/size result shaping, split-large-page preparation/entry arithmetic, split-large-page source classification, child-map physical derivation, page-table publish entry shaping, source-unmap gate selection, PTE direct-store helpers, atomic child-table publication helpers, PTE clear-exchange helpers, attribute-apply mutation helpers, page-clear alignment/target selection, page-table visit/direct-walk decision policy, clear/free-range validation and large-entry action selection, clear-range old-PTE phys/fileoff/dirty classification plus flush/free/unmap action selection, change-attribute leaf/large/walk action selection, set-range leaf/direct-large/allocate/busy/walk action selection, set-range mapped physical/PTE value shaping for 4 KiB/2 MiB/1 GiB entries, lookup-pte default size/level hit/walk/miss/shape decisions, move-PTE fileoff preflight/destination shaping/PTE phys-attr splitting, page-table destroy descend/skip policy, destroy child-table physical extraction, VM range validation, memory-policy validation, and selected pager/object sizing helpers are Rust-owned; page-table allocation/free, destroy recursion, `phys_to_virt()`/free orchestration, callback execution, higher-level visitor and page-table traversal orchestration, `page_map()`/`page_unmap()`, actual page frees, RSS updates, mapping/free orchestration, TLB-sensitive flushing, and user-copy remain C. |
| Page allocator | 74 | Rbtree helper cluster, bitmap-backed no-lock allocator internals, bitmap public locked-wrapper orchestration for alloc/reserve/free/count/query/zero-free, init layout/end/count calculation, descriptor zeroing and descriptor field initialization, tail-map reservation, destroy-page count and descriptor destroy/free-callback orchestration, NUMA free/alloc helpers, NUMA zero-free dispatcher/all-node traversal, main NUMA allocation lock-callback orchestration, direct free-to-tree lock-callback orchestration, deferred-free enqueue/zero-request orchestration, free-path policy, zeroing-worker atomic increment, CPU-local cache action classification, CPU-local cache rb-tree allocation/free helper entry points, CPU-local cache alloc/free fast-path orchestration with interrupt callback ordering and result classification, Linux zero-request action selection, deferred-zero IKC packet field shaping, and Linux zero-request preparation including current/idle/nohost/worker/pid checks plus packet fill and worker increment are Rust-owned; logging, CPU-local variable selection, actual `ihk_mc_free_pages()` and MCS/interrupt primitives, broader allocator lifetime, IKC packet send/channel selection, current-thread/channel lookup, actual IKC send side effects, deferred-zero worker timing, zeroed-list publication, and broader allocator mutation remain C. |
| Process/VM management | 87 | Wait/clone/ptrace/VM policy, fork VM/thread metadata copy, address-space release and PID detach mutation, range-cache lookup relation plus range-cache replace/store mutation for join, free, and lookup paths, VM range end/flag commit mutation for extend-up and protection-change paths, stack-growth range-start alignment/commit mutation for the page-fault path, remove-range split/free preflight, split-range high-half field shaping and low-half end commit, join-range adjacency/object-offset validation and surviving-end commit, CPU-set fallback, mckfd decisions plus push/pop-head mutation, TID-table scan/index decisions, TID slot release/replace writes, sigpending list pop/unlink, process/thread list add/detach helpers, terminate child cleanup list unlink/reparent mutation helpers, thread report-list attach/detach mutation helpers, ptrace main-thread attach/detach reparent helpers, ptrace detach/wakeup state and pending-signal cleanup helpers, wait signal-flag and exit-status reap mutation helpers, terminate/wait report-thread release cleanup helpers, optional ptrace/fp cleanup gates, and lifecycle/refcount predicates are Rust-owned; VM range allocation/free, memobj refcounting, TOFU split/merge hooks, rb-tree mutation, page-fault handling, access-check orchestration, page-table lookup/allocation/mapping, page-table attribute mutation/free/clear, broader child-list orchestration, rusage aggregation, broad process lifetime mutation, signal forwarding, and full wait orchestration remain C. |
| Syscall core | 95 | SysV shm, prlimit, scheduler, syscall/range validation, credential-refresh forwarding gates, requester-TID and preempt-disable gates, getpid/getppid/gettid/set_tid_address return shaping, memory-policy, mmap/brk/mincore, mprotect split/write-change decisions, signal/time, ptrace/process-vm, wait, execveat, clone, futex policy helpers, bounded wait/ptrace/termination/signal list rewiring, pending-signal delivery/offload-interrupt classification, ptrace wakeup/siginfo/eventmsg result classification, ptrace request dispatch classification, ptrace setoptions state mutation, ptrace attach traced-state mutation, ptrace event-message preparation, ptrace siginfo kernel-buffer preparation and pending-siginfo publication, ptrace peek/poke user-word status/callback orchestration, ptrace getregs/setregs register-word loop orchestration, ptrace peek/poke text status and VM-callback staging, ptrace fpregs status/callback orchestration, ptrace getregset/setregset iovec copy/callback/length-publication orchestration, wait/reap result-shape classification, getrusage dispatch/update classification, getrusage thread times-update mutation, getrusage TSC/timeval/rusage result shaping, process-exit status/siginfo classification, terminate cleanup/reparent action classification, clone spawn/TID/TLS/reparent result shaping, and ptrace detach signal-forward gates are Rust-owned; top-level syscall dispatch, user-copy, Linux forwarding, locks, allocation/free, architecture fp/register/regset primitives, actual process-memory read/patch primitives, signal delivery, child-list mutation, rusage aggregation/traversal, CPU interrupt delivery, ptrace lookup/orchestration, and remaining high-risk handlers remain C. |
| Scheduler/timers/wait/futex | 88 | Waitqueue init/entry/list core, wake scheduling predicate, bounded runqueue/migration list rewiring plus runqueue length updates, timer spin-sleep/runqueue/remaining-time arithmetic, futex hash-bucket table lock/list initialization, futex key matching/key preparation plus wake/requeue decision policy, futex double hash-bucket lock/unlock ordering, futex wake-list scan/key-match/bitset/limit orchestration, futex requeue source-list scan/key-match/wake-vs-requeue/drop-count orchestration, futex requeue key-reference callback and key-copy publication, futex wait-setup key-init/get-key/queue-lock/get-value/mismatch cleanup orchestration, futex wake-list detach and lock-pointer clear, futex requeue list move and lock-pointer publication, futex waiter plist initialization/insertion, futex wait-queue bitset/requeue/UTI initialization, key-region zeroing, hash-bucket lock-pointer publication, waiter metadata publication, self-unqueue list detach, wait-side bitset validation, wait scheduling action classification, wait-state status/spin-sleep mutation, futex post-wait success/timeout/interrupt/retry classification, futex wake target classification, Linux response-channel fallback selection, futex wake IKC packet field publication, syscall-offload scheduling decisions, and scheduler/futex/signal/timer policy helpers are Rust-owned; futex table allocation, callbacks, actual spinlock primitives, wakeups, futex key lookup internals, key-reference implementation/lifetime, user-value load, IKC send side effects, IPIs, timer queues, context switching, address translation, race retry, user-value comparison, schedule/schedule_timeout behavior, and remaining futex queue/requeue/wait side effects remain C. |
| procfs/sysfs/xpmem/file objects | 100 | XPMEM and file/dev/procfs/sysfs/pager decision-helper surface is Rust-owned through multiple batches, including procfs cmdline/comm helpers; this is not full subsystem ownership because allocation, refcount mutation, lock/list mutation, remap/page-table mutation, page I/O, procfs buffer mutation, sysfs IKC exchange, and user-copy remain C. |
| host/IKC/mcctrl/IHK modules | 99 | Rust helper linkage is active for `ihk`, `ihk-smp-x86_64`, and `mcctrl`; many host driver, OS/device exclusive-open refcount compare-exchange mutation, generic locked list add/delete mutation, generic list-membership traversal, generic next-entry cursor traversal for notifier/event/aux-call paths, kmsg buffer/container lifecycle mutation, kmsg container atomic count set/read/inc/dec/dec-return, reverse kmsg list lookup traversal, load-file dispatch/read-loop policy, shutdown status policy, SMP, sysfs, IKC policy, and mcctrl helpers are Rust-owned, including deferred-zero worker list pop, payload clear, zeroed-list publish, and atomic counter updates; callback invocation, device allocation, memory registration, file I/O, waits/callbacks, broader IKC exchange mutation, broad allocation/lifetime ownership, and kernel object lifecycle mutation remain pending. |
| User tools | 83 | `mcstat`, `mcexec`, `ihklib`, `mcinspect`, `eclair`, and crash-extension helper surfaces are substantially Rust-owned; device I/O, ioctl handling, DWARF/BFD walking, crash command orchestration, GDB process/socket orchestration, daemon/thread/event-loop mutation, dump NMI side effects, register/memory reads, and most IHK command mutation remain C. |
| Rocky runtime integration | 82 | Rust McKernel image and focused Rocky smokes have passed in prior runs; this pass did not run boot or reboot-capable validation. Wider runtime/performance coverage remains pending. |
| arm64 | 0 | Deferred until x86_64 stabilizes. |

Honest current distance: the non-arm64 functional dashboard average is 85.4%,
while the McKernel-owned core rows in this table average 83.3%. Mechanical LOC
audit is 17.7% and is not a progress score. The functional percentages track
verified Rust-owned surfaces, and they are not a claim that mutation-heavy
kernel bodies are already fully Rust. The current total distance to 100 is 175
aggregate functional points across non-arm64 dashboard rows, or 134 points
across the McKernel-owned core rows excluding build/host/user/Rocky/arm64.

## Distance To 100

| Area | Current | Points To 100 |
| --- | ---: | ---: |
| Rust build/link foundation | 95 | 5 |
| ABI/layout foundation | 54 | 46 |
| Shared primitives | 84 | 16 |
| x86_64 memory management | 84 | 16 |
| Page allocator | 74 | 26 |
| Process/VM management | 87 | 13 |
| Syscall core | 95 | 5 |
| Scheduler/timers/wait/futex | 88 | 12 |
| procfs/sysfs/xpmem/file objects | 100 | 0 for helper/decision surface; mutation bodies still C |
| host/IKC/mcctrl/IHK modules | 99 | 1 |
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
- The follow-up +10 verified slice toward the requested +135 campaign routes
  futex wake/requeue decision policy, x86 page-clear alignment and target
  selection, and process VM remove-range split/free preflight through Rust
  helpers. C still owns futex queue/list mutation and wakeups, page-table
  writes, range allocation/free, XPMEM removal side effects, locks, user-copy,
  Linux forwarding, and runtime orchestration.
- The latest +5 verified x86 slice toward the requested +135 campaign routes
  page-table visit/direct-walk action selection, clear/free-range validation,
  free-physical gating, and clear-range large-entry action selection through
  Rust helpers. C still owns page-table allocation and traversal side effects,
  `xchg()`/PTE writes, TLB flushes, page frees, RSS/rusage updates, memobj
  flushes, and user-copy.
- The latest +4 verified syscall slice toward the requested +135 campaign routes
  getrusage TSC-to-timespec accumulation and `struct rusage` timeval/maxrss
  result shaping through Rust helpers. C still owns thread-list traversal,
  times-update orchestration, CPU interrupts, locks, user-copy, and actual
  rusage aggregation/lifetime state.
- The latest +3 verified page-allocator slice toward the requested +135
  campaign routes CPU-local cache try/hit/free-success action classification
  through Rust helpers. C still owns interrupt masking, CPU-local rb-tree
  mutation, logging, allocator lifetime, and fallback-to-NUMA free behavior.
- The latest +4 verified x86 slice toward the requested +135 campaign routes
  page-table change-attribute leaf, large-entry, split-error, and walk action
  selection through Rust helpers. C still owns the PTE writes, lower-level page
  table walks, error logging, TLB-sensitive behavior, and user-copy.
- The latest +4 verified x86 set-range slice toward the requested +135
  campaign routes leaf apply/busy, direct large-page map, allocate-and-walk,
  busy, and lower-level walk action selection through Rust helpers. C still
  owns page-table allocation, cmpxchg, PTE writes, RSS updates, rollback
  clears, lower-level walks, TLB-sensitive behavior, and user-copy.
- The latest +4 verified x86 lookup slice toward the requested +135 campaign
  routes lookup default page-size choice, L3/L2 hit/walk/miss classification,
  L4-empty size clamping, and base/size/p2align result shaping through Rust
  helpers. C still owns page-table pointer traversal, `phys_to_virt()`, entry
  dereferences, and returned PTE pointer ownership.
- The latest +3 verified IHK slice toward the requested +135 campaign routes
  host core OS load-file dispatch, file-size validity, kernel-read failure
  classification, and read-loop continuation policy through Rust helpers. C
  still owns file I/O, memory allocation/free, load handler calls, state
  lifetime, and error cleanup.
- The latest +3 verified IHK shutdown slice toward the requested +135 campaign
  routes shutdown status-to-action policy through Rust helpers. C still owns
  waits, thaw calls, NMI fallback, notifier traversal, IKC finalization,
  shutdown callbacks, kmsg release, locks, state mutation, and cleanup.
- The latest +4 verified IHK mutation slice toward the requested +135 campaign
  routes host core kmsg buffer initialization and clear field/buffer mutation
  through Rust helpers. C still owns page allocation/free, inter-kernel lock
  acquire/release, IRQ masking, list insertion/deletion, container lifetime,
  and module lifecycle cleanup.
- The latest +3 verified IHK lifecycle mutation slice toward the requested
  +135 campaign routes kmsg container field initialization and OS container
  pointer take/clear mutation through Rust helpers. C still owns atomic
  refcount initialization, list publication/deletion, release calls, frees,
  locks, and module lifecycle cleanup.
- The latest +4 verified IHK list-publication slice toward the requested +135
  campaign routes locked `list_add_tail` publication for kmsg buffers, event
  registrations, aux-call handlers, and OS notifiers through Rust helpers. C
  still owns list traversal, list deletion, locks, refcounts, callback
  execution, object lifetime, and frees.
- The latest +4 verified IHK list-deletion slice toward the requested +135
  campaign routes locked `list_del` mutation for kmsg buffers, event cleanup,
  aux-call unregister, and OS notifier deregistration through Rust helpers. C
  still owns traversal, locks, refcounts, callback execution, object lifetime,
  and frees.
- The latest +3 verified IHK kmsg traversal slice toward the requested +135
  campaign routes reverse kmsg-buffer lookup traversal by OS index through Rust
  helpers for OS boot and device kmsg lookup. C still owns the locks, refcount
  increments, returned-pointer assignment, user-copy, error handling, and object
  lifetime.
- The latest +3 verified IHK list-membership traversal slice toward the
  requested +135 campaign routes generic forward list membership traversal
  through Rust helpers for OS notifier registration and deregistration. C still
  owns semaphore locking, callback invocation traversal, list add/delete,
  refcounts, object lifetime, and module lifecycle side effects.
- The latest +3 verified IHK next-entry traversal slice toward the requested
  +135 campaign routes generic forward cursor traversal through Rust helpers
  for OS notifier boot/shutdown callbacks, eventfd signaling traversal, and
  aux-call handler-list traversal. C still owns callback invocation, eventfd
  signaling, semaphore/spinlock coverage, handler dispatch, refcounts, user-copy,
  object lifetime, and module lifecycle side effects.
- The latest +4 verified IHK kmsg refcount slice toward the requested +135
  campaign routes kmsg container atomic count set/read/inc/dec/dec-return
  through Rust helpers with C fallbacks. At that point C still owned OS/device
  open refcount `cmpxchg`; the later post-campaign open-refcount slice moved
  that boundary. C still owns callback invocation, locks, container
  allocation/free, page allocation/free, device allocation, memory
  registration, IKC exchange, file I/O, user-copy, and broad lifetime.
- The latest +4 verified ABI/layout slice toward the requested +135 campaign
  adds Rust compile-time layout mirrors for IHK kmsg buffers, kmsg buffer
  containers, event entries, notifier ops/entries, aux-call handler entries,
  and aux-call lists. These assertions compile into the IHK helper object; C
  still owns object allocation/free, callbacks, user-copy, IKC exchange, and
  runtime lifecycle.
- The latest +3 verified page-allocator slice toward the requested +135
  campaign routes the NUMA zeroing-worker atomic increment through Rust helpers
  with equivalence coverage. C still owns the decision to request Linux zeroing,
  IKC packet construction/send, locks, interrupt masking, allocator lifetime,
  and broad zeroing side effects.
- The latest +3 verified scheduler/futex slice toward the requested +135
  campaign routes the futex wake-list detach, compiler barrier, and
  `lock_ptr` clear through Rust helpers with C fallbacks and equivalence
  coverage. C still owns the hash-bucket locks, wake policy, IKC packet
  construction/send, thread wakeup, timeout/requeue orchestration, scheduler
  handoff, and broader futex queue/list mutation.
- The latest +3 verified scheduler/futex requeue slice toward the requested
  +135 campaign routes the futex cross-bucket requeue list move and
  `lock_ptr` publication through Rust helpers with C fallbacks and equivalence
  coverage. C still owns the hash-bucket locks, key reference/lifetime updates,
  `q->key` replacement, wake policy, timeout/requeue loop orchestration,
  scheduler handoff, and broader futex queue/list mutation.
- The latest +3 verified scheduler/futex queue-metadata slice toward the
  requested +135 campaign routes queue-time futex waiter metadata publication
  through Rust helpers with C fallbacks and equivalence coverage. C still owns
  current-thread lookup, address translation, interrupt lookup, queue insertion,
  hash-bucket lock coverage, timeout/wake orchestration, and broader futex
  queue/list mutation.
- The latest +3 verified scheduler/futex unqueue slice toward the requested
  +135 campaign routes self-unqueue priority-list detach through Rust helpers
  with C fallbacks and equivalence coverage. C still owns lock-pointer reads,
  compiler barrier, race retry, hash-bucket lock/unlock, key reference dropping,
  return orchestration, and sleep/wake behavior.
- The latest +3 verified x86 memory slice toward the requested +135 campaign
  routes move-PTE file-offset rejection, mapped-destination calculation, and
  exchanged-PTE physical/attribute splitting through Rust helpers with C
  fallbacks and equivalence coverage. C still owns `pte_xchg()`,
  `ihk_mc_pt_set_range()`, page-table mutation, TLB flush behavior, logging,
  and runtime move orchestration.
- The latest +3 verified x86 clear/free-range slice toward the requested +135
  campaign routes old-PTE physical/fileoff/dirty classification plus
  flush/free/XPMEM/try-unmap action selection through Rust helpers with C
  fallbacks and equivalence coverage. C still owns `xchg()`, `phys_to_page()`,
  `memobj_flush_page()`, `page_unmap()`, actual frees, RSS updates, remote TLB
  flushes, logging, and page-table lifetime.
- The latest +3 verified x86 set-range slice toward the requested +135
  campaign routes mapped physical-address and final PTE value shaping for
  4 KiB, 2 MiB, and 1 GiB mappings through Rust helpers with C fallbacks and
  equivalence coverage. C still owns page-table allocation, compare-exchange,
  direct PTE writes, rollback, RSS updates, and runtime map orchestration.
- The latest +5 verified x86 split-large-page slice completes the requested
  +135 campaign by routing split source classification, child-map physical
  derivation, page-table publish entry shaping, and source-unmap gate selection
  through Rust helpers with C fallbacks and equivalence coverage. C still owns
  allocation, child entry writes, `page_map()`, `page_unmap()`, RSS updates,
  PTE publication, remote TLB flushing, and runtime split orchestration.
- The latest post-campaign +3 page-allocator slice routes NUMA zero-free
  dispatcher policy, explicit-node versus all-node traversal, and null-node
  stop behavior through Rust helpers with C fallbacks and equivalence coverage.
  C still owns caller timing, locks, logging, CPU-local rb-tree mutation,
  interrupt masking, allocator lifetime, IKC packet construction/send, Linux
  zero-request side effects, and broad allocator lifecycle ownership.
- The latest post-campaign +3 page-allocator packet slice routes deferred-zero
  IKC packet clearing and field shaping through Rust helpers with C fallbacks
  and equivalence coverage. C still owns request timing, current-thread lookup,
  channel selection, `ihk_ikc_send()`, logging, zeroing side effects, locks,
  CPU-local rb-tree mutation, interrupt masking, allocator lifetime, and broad
  allocator lifecycle ownership.
- The latest post-campaign +3 page-allocator CPU-cache slice routes CPU-local
  cache rb-tree allocation/free helper entry points through Rust helpers with C
  fallbacks and equivalence coverage. C still owns CPU-local variable
  selection, interrupt masking, logging, try/hit/fallback orchestration,
  allocator lifetime, IKC packet send/channel/current-thread lookup, zeroing
  side effects, locks, and broad allocator lifecycle ownership.
- The latest post-campaign +3 x86 memory slice routes direct PTE stores,
  atomic child page-table publication, PTE clear exchange, and attribute-apply
  mutation through Rust helpers with C fallbacks and equivalence coverage. C
  still owns page-table allocation/free, walk orchestration, `page_map()`,
  `page_unmap()`, actual physical frees, RSS updates, remote TLB
  flushing, logging, user-copy, and broader runtime mapping orchestration.
- The latest post-campaign +3 IHK host-core slice routes OS/device
  exclusive-open refcount compare-exchange mutation through Rust helpers with
  C fallbacks and equivalence coverage. C still owns callback invocation, file
  operation orchestration, device allocation, memory registration, file I/O,
  waits/callbacks, IKC exchange mutation, broad allocation/lifetime ownership,
  and kernel object lifecycle mutation.
- The latest post-campaign +3 scheduler/futex slice routes futex wait-state
  status/spin-sleep mutation and post-wait success/timeout/interrupt/retry
  classification through Rust helpers with C fallbacks and equivalence
  coverage. C still owns hash-bucket locking, queue orchestration,
  `schedule()`/`schedule_timeout()`, signal detection, wakeups, timer queues,
  context switching, key lifetime, race retry, and broader futex queue/list
  mutation.
- The latest post-campaign +3 scheduler/futex wake slice routes futex wake
  target classification, Linux response-channel fallback selection, and
  `SCD_MSG_FUTEX_WAKE` IKC packet field publication through Rust helpers with
  C fallbacks and equivalence coverage. C still owns queued-node detach,
  `ihk_ikc_send()`, `sched_wakeup_thread()`, channel-array access, wakeup side
  effects, IPIs, timer queues, context switching, key lifetime, race retry,
  and broader futex queue/list mutation.
- The latest post-campaign +1 mcctrl deferred-zero slice routes the
  Linux-side deferred-zero worker's lockless `to_zero_list` pop, chunk payload
  clear, `zeroed_list` publish, and zeroing-worker/page-count atomic updates
  through Rust helpers with C fallback and module-helper smoke coverage. This
  is credited as +1 rather than forcing the host/IHK row to 100 because
  memory registration, broader IKC exchange, allocation/lifetime ownership,
  callback/device/file orchestration, and module lifecycle mutation still have
  real C debt.
- The latest post-campaign +3 scheduler/futex queue-insertion slice routes
  futex waiter plist node initialization and hash-bucket queue insertion in
  `queue_me()` through Rust helpers with C fallbacks and equivalence coverage.
  C still owns hash-bucket locking, current-thread lookup, physical-address
  input gathering, timeout/wake orchestration, `schedule()`/
  `schedule_timeout()`, wakeups, IKC sends, key lifetime, and broader futex
  queue orchestration.
- The latest post-campaign +3 scheduler/futex wait-q-init slice routes
  futex wait-queue bitset/requeue/UTI initialization, key-region zeroing before
  `get_futex_key()`, and hash-bucket lock-pointer publication through Rust
  helpers with C fallbacks and direct equivalence coverage. C still owns
  hash-bucket locking, user-value comparison, key reference lifetime,
  timeout/wake orchestration, `schedule()`/`schedule_timeout()`, wakeups,
  IKC sends, address translation, race retry, and broader futex wait
  orchestration.
- The latest post-campaign +3 x86 destroy-page-table slice routes page-table
  teardown entry descend/skip policy and child page-table physical-address
  extraction through Rust helpers with C fallbacks and direct equivalence
  coverage. C still owns destroy recursion, `phys_to_virt()`, page-table
  frees, panic handling, and broader page-table lifetime orchestration.
- The latest post-campaign +3 x86 page-table walk slice routes normal and safe
  L1-L4 walk result folding through Rust helpers with C fallbacks and direct
  equivalence coverage. C still owns callback execution, page-table allocation,
  physical-address validation, traversal, splitting, `phys_to_virt()`, and all
  page-table mutation side effects.
- The latest post-campaign +3 page-allocator zero-request preparation slice
  routes deferred-free Linux zero-request preparation through Rust helpers:
  current/idle/nohost/worker/pid checks, zeroing-worker increment, and packet
  field publication. C still owns CPU-local variable selection, interrupt
  context, IKC channel selection, `ihk_ikc_send()`, logging, and broader
  allocator lifetime/fast-path orchestration.
- The latest post-campaign +3 scheduler/futex wait-scheduling slice reuses the
  Rust-owned bitset validator on the wait side and routes queued/timeout/direct
  schedule action classification in `futex_wait_queue_me()` through Rust
  helpers with C fallbacks and direct equivalence coverage. C still owns the
  `plist_node_empty()` observation, actual `schedule_timeout()`/
  `spin_sleep_or_schedule()` behavior, signal and timeout mechanics, wakeups,
  locks, timer queues, context switching, race retry, key lifetime, and broader
  futex wait orchestration.
- The latest post-campaign +3 syscall getrusage slice routes per-thread
  `times_update` mutation in the `RUSAGE_SELF` scan through Rust helpers with C
  fallbacks and direct equivalence coverage. C still owns thread-list locking,
  traversal, current/status/in-kernel observations, CPU interrupt delivery,
  TSC aggregation, rusage copyout, and user-copy behavior.
- The latest IHK SMP memory-assignment slice routes free-chunk scan decisions,
  no-chunk/all/fake-chunk action selection, and used-chunk insertion ordering
  through Rust helpers with C fallbacks and direct module-helper coverage. C
  still owns free-list traversal, kmalloc/kfree, list mutation, compound-page
  leftover handling, memory registration side effects, locks, copy_from_user,
  rollback release calls, and broad OS-memory assignment orchestration. Do not
  mark host/IHK as 100% until those remaining bodies are covered and moved.
- The latest post-campaign +3 page-allocator descriptor-init slice routes
  descriptor zeroing and descriptor field initialization in
  `__ihk_pagealloc_init()` through Rust helpers with C fallbacks and direct
  page-allocator equivalence coverage. C still owns descriptor allocation,
  `mcs_lock_init()`, exported wrapper lifetimes, lock ownership, CPU-local
  variable selection, interrupt masking, IKC send side effects, and broader
  allocator lifetime/orchestration.
- The latest post-campaign +3 syscall ptrace slice routes `ptrace_setoptions`
  option-state mutation, `ptrace_attach` traced-state publication, and
  `ptrace_geteventmsg` status validation/event-message preparation through
  Rust helpers with C fallbacks and direct syscall-policy equivalence coverage.
  C still owns tracee lookup, locks, `copy_to_user()`, signal delivery,
  register and process-memory access, ptrace handler orchestration,
  allocation/free, and Linux forwarding.
- The latest post-campaign +3 syscall ptrace siginfo slice routes
  `ptrace_getsiginfo` status validation/kernel siginfo buffer preparation and
  `ptrace_setsiginfo` pending-signal pointer publication plus sendsig/recvsig
  siginfo storage through Rust helpers with C fallbacks and direct
  syscall-policy equivalence coverage. C still owns tracee lookup, locks,
  `kmalloc()`, failure lifetime semantics, `copy_to_user()`/
  `copy_from_user()`, signal delivery, register/process-memory access, and
  broader ptrace handler orchestration.
- The latest post-campaign +3 syscall ptrace register slice routes
  `ptrace_getregs`/`ptrace_setregs` repeated register-word read/write loops and
  first-error behavior through Rust callback helpers with C fallbacks and
  direct syscall-policy equivalence coverage. C still owns tracee lookup,
  status gating, stack buffer lifetime, `copy_to_user()`/`copy_from_user()`,
  architecture `ptrace_read_user()`/`ptrace_write_user()`, debug-register
  details, and broader ptrace orchestration.
- The latest post-campaign +2 syscall ptrace text-access slice routes
  `ptrace_peektext`/`ptrace_poketext` status-gated process-memory word
  read/write callback staging through Rust helpers with C fallbacks and direct
  syscall-policy equivalence coverage. It is scored conservatively because C
  still owns tracee lookup, logging, user-copy, actual `read_process_vm()`/
  `patch_process_vm()` behavior, page-fault/mapping side effects, and broader
  ptrace orchestration.
- The latest post-campaign +3 syscall ptrace fpregs/regset slice routes
  `ptrace_getfpregs`/`ptrace_setfpregs` stopped/traced status handling and
  architecture fpregs callback dispatch through Rust helpers, and routes
  `ptrace_getregset`/`ptrace_setregset` iovec copy-in, architecture regset
  callback dispatch, and iov_len publication orchestration through Rust
  callback helpers with C fallbacks and direct syscall-policy equivalence
  coverage. C still owns tracee lookup, locks, user-copy callback bodies,
  architecture fp/register/regset primitives, signal delivery, allocation/free,
  Linux forwarding, and top-level syscall dispatch.
- The latest post-campaign +2 syscall ptrace user-word slice routes
  `ptrace_peekuser`/`ptrace_pokeuser` stopped/traced status handling and
  architecture user-area word read/write callback dispatch through Rust
  helpers with C fallbacks and direct syscall-policy equivalence coverage. It
  is scored conservatively because C still owns address validation, tracee
  lookup, `copy_to_user()` for peek results, architecture
  `ptrace_read_user()`/`ptrace_write_user()` primitives, and broader ptrace
  orchestration.
- The latest post-campaign +3 page-allocator CPU-cache slice routes CPU-local
  cache allocation/free fast-path orchestration through Rust helpers, including
  initialized/not-initialized branch handling, interrupt save/restore callback
  ordering, rb-tree allocation/free attempt, cache-hit shaping, and free
  success/failure classification. C still owns CPU-local variable selection,
  actual interrupt masking primitives, logging, non-cache locks, allocator
  lifetime, IKC send/channel selection, current-thread/channel lookup, and
  broader zero-request side effects.
- The latest post-campaign +3 scheduler/futex double-bucket slice routes
  futex double hash-bucket lock/unlock ordering through Rust helpers with C
  callback bridges and direct equivalence coverage. C still owns the actual
  spinlock primitives, hash-bucket protected list mutation, wakeups, IKC sends,
  scheduling, key lifetime, address translation, user-value comparison, race
  retry, and broader futex wake/requeue orchestration.
- The latest post-campaign +3 page-allocator locked-orchestration slice routes
  main NUMA allocation and direct free-to-tree lock/unlock callback
  orchestration through Rust helpers with direct equivalence coverage. C still
  owns the actual MCS lock primitives, logging, CPU-local variable selection,
  interrupt masking primitives, deferred-zero worker timing, IKC send/channel
  selection, current-thread/channel lookup, actual IKC send side effects, and
  broader allocator lifetime/zero-request orchestration.
- The latest post-campaign +3 page-allocator deferred-free slice routes
  deferred-free chunk enqueue plus Linux zero-request preparation orchestration
  through Rust helpers with direct equivalence coverage. C still owns
  CPU-local current/idle/channel selection, actual IKC send side effects,
  logging, interrupt context, deferred-zero worker timing, zeroed-list
  publication, and broader allocator lifetime.
- The latest post-campaign +3 scheduler/futex wake-scan slice routes
  hash-bucket wake-list scanning, key matching, optional bitset filtering,
  wake-limit handling, and wake callback ordering through Rust helpers for
  `futex_wake()` and `futex_wake_op()`. C still owns futex key lookup,
  hash-bucket locking, actual wake side effects, IKC sends, scheduler handoff,
  key references, user-value operations, address translation, and broader
  wake/requeue orchestration.
- The latest post-campaign +3 scheduler/futex requeue-loop slice routes
  source-list scanning, key matching, wake-vs-requeue selection, task/drop
  count accounting, and wake/requeue callback ordering through Rust helpers for
  `futex_requeue()`. C still owns comparison-user-value loading, hash-bucket
  locking, actual wake side effects, `requeue_futex()` key-reference and
  key-copy mutation, IKC sends, scheduler handoff, address translation, race
  retry, and broader futex wake/requeue orchestration.
- The latest post-campaign +3 scheduler/futex wait-setup slice routes
  `futex_wait_setup()` key initialization, get-key/queue-lock/user-value-load
  callback sequencing, mismatch/error cleanup, key release, and hash-bucket
  publication through Rust helpers. C still owns key lookup internals, address
  translation, page fault behavior, lock primitives, user-value load,
  key-reference lifetime, timeout/schedule behavior, wake side effects, and
  broader futex wait/retry orchestration.
- The latest post-campaign +3 x86 page-table walk slice routes normal and safe
  page-table walk iteration, callback result folding, bounds-derived entry
  selection, and optional physical-address skip policy through Rust helpers.
  C still owns visitor callback execution, table allocation/free,
  `phys_to_virt()` traversal, splitting, page/RSS accounting, page free side
  effects, mapping/free orchestration, TLB-sensitive mutation, and user-copy.
- The latest post-campaign +3 x86 virtual-to-physical slice routes per-level
  miss/walk/hit decisions plus physical-address and page-size result shaping
  for 4 KiB, 2 MiB, and 1 GiB entries through Rust helpers. C still owns
  page-table pointer traversal, `phys_to_virt()`, fault handling, page-table
  lifetime, mapping side effects, and user-copy.
- The latest post-campaign +3 process VM-range split/join slice routes
  split-range high-half field shaping, low-half end commit, join-range
  adjacency/object-offset validation, and surviving-range end commit through
  Rust helpers. C still owns page-table split/clear/free calls,
  `kmalloc()`/`kfree()`, memobj refcounting, TOFU split/merge hooks,
  rb-tree/cache mutation, XPMEM removal, and broader process lifetime/wait
  orchestration.
- The latest post-campaign +3 page allocator bitmap locked-wrapper slice
  routes bitmap allocator alloc/reserve/free/count/query/zero-free
  lock/call/unlock orchestration through Rust helpers. C still owns the actual
  MCS lock primitives, descriptor allocation/destruction, free panic/log
  policy, CPU-local selection, IKC send side effects, deferred-zero worker
  timing, zeroed-list publication, and broader allocator lifetime.
- The latest post-campaign +3 scheduler/futex hash-bucket init slice routes
  futex table lock-word and plist-head initialization through Rust helpers
  while preserving C allocation and fallback behavior. C still owns futex table
  allocation, actual spinlock primitives, wakeups, requeue key-reference
  mutation, futex key lookup internals, user-value load/comparison, IKC send
  side effects, IPIs, timer queues, context switching, address translation,
  key lifetime, race retry, schedule/schedule_timeout behavior, and remaining
  futex wake/requeue/wait side effects.
- The latest post-campaign +3 scheduler/futex requeue key-publication slice
  routes the requeue key-reference callback and `q->key` copy/publication
  through Rust helpers while preserving the C key-reference implementation and
  fallback behavior. C still owns futex table allocation, actual spinlock
  primitives, wakeups, futex key lookup internals, key-reference lifetime,
  user-value load/comparison, IKC send side effects, IPIs, timer queues,
  context switching, address translation, race retry, schedule/schedule_timeout
  behavior, and remaining futex wake/requeue/wait side effects.
- The latest post-campaign +3 page allocator destroy/free-callback slice
  routes descriptor free-page calculation, free-callback validation, and
  descriptor/free-page handoff through Rust helpers while preserving the C
  fallback. C still owns descriptor allocation, the actual
  `ihk_mc_free_pages()` implementation, logging, CPU-local selection, IKC send
  side effects, deferred-zero worker timing, zeroed-list publication, and
  broader allocator lifetime.
- The latest post-campaign +3 process VM range-cache slice routes
  range-cache retarget, clear, and store mutation for join, free, and lookup
  paths through Rust helpers while preserving the C fallback. C still owns
  rb-tree insert/erase, VM range allocation/free, page-table free/clear,
  memobj refcounting, TOFU list moves, and broader process lifetime behavior.
- The latest post-campaign +3 process VM range-commit slice routes final
  VM-range end and flag commits for extend-up and protection-change paths
  through Rust helpers while preserving the C fallback. C still owns page-table
  attribute changes, page-table free/clear, locks, memobj refcounting, TOFU
  hooks, rb-tree mutation, allocation/free, and broader lifetime behavior.
- The latest post-campaign +3 process VM stack-start slice routes
  stack-growth range-start alignment and commit in `do_page_fault_process_vm()`
  through Rust helpers while preserving the C fallback. C still owns range
  lookup, locking, access checks, page-fault handling, page allocation,
  page-table lookup and mapping, retry behavior, VM range allocation/free,
  memobj refcounting, TOFU hooks, rb-tree mutation, and broader process
  lifetime behavior.
- IHK open/release/close/init/exit/minor-registration, register-device cleanup,
  destroy-all-OS candidate/restore, stray-kmsg trim, event-list cleanup,
  destroy callback, notifier policy decisions, and open refcount mutation
  route through Rust helpers; treat these as established boundary context while
  the remaining IHK mutation bodies are still active scope.

Latest documented validation passed:

- `rustfmt kernel/rust/sched_helpers.rs`.
- `rustfmt kernel/rust/x86_memory_helpers.rs`.
- `rustfmt kernel/rust/process_helpers.rs`.
- `rustfmt ihk/linux/driver/smp/rust/smp_driver_helpers.rs`.
- `rustfmt kernel/rust/page_alloc.rs`.
- `rustfmt kernel/rust/syscall_policy.rs`.
- `bash -n kernel/rust/tests/run_equivalence.sh`.
- `git diff --check`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=44f8ebf6efebbadf`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=68635108100ea1c0`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=504d5b3e9c153630`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=a80ef094b43f24e8`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=34117c66f91ba2ea`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=2a415c1756979d79`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=25fb3df8ffceadbb`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=2818dd602ed5bc4c`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc ok digest=db15eec71e0aad78`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=bcb2642411511aea`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=0b3811141e0e5228`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=3b05135350df748e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=81a86d9fa4f9900f`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=68a9fbfe485ec6f0`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=91790b3aa3a68a22`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=a4fa8b1f93b2890e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=90f372a037f1fbff`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=5bf0cbacd30b645e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `ihk_module_helpers ok map=0000000000000018 bits=0000000000000007/0000000000000000`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=6058b8fa4f7180c7`.
- `python3 -m py_compile scripts/rust-ownership-report.py`.
- `scripts/rust-ownership-report.py --check-dashboard overview.txt --check-dashboard overview2.txt --top 25`.
- `cmake --build /tmp/mckernel-rocky-c-fallback --target ihk_ko -j2`.
- `cmake --build /tmp/mckernel-rocky-rust --target ihk_ko -j2`.
- `cmake --build /tmp/mckernel-rocky-c-fallback --target mckernel.img -j2`.
- `cmake --build /tmp/mckernel-rocky-rust --target mckernel.img -j2`.

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

- The requested +135 aggregate-point campaign is complete, but the full Rust
  port is not. Continue toward 100% by targeting
  high-debt McKernel-owned rows first: allocator zeroed-list policy before
  mutation, syscall ptrace handler body slices, scheduler/futex
  wait/wake internals after runtime probes, additional x86 page-table
  map/remove/free preflight decisions, IHK/host-module owned mutation
  preflights and then covered mutation bodies, IHK atomic refcount publication,
  memory registration, IKC exchange, sysfs object creation/module lifecycle, and
  process VM-range mutation bodies only with direct coverage.
- Keep the high-risk orchestration in C until runtime coverage exists:
  process lifetime mutation, child-list mutation, rusage aggregation, ptrace
  detach mutation, scheduling decisions, wakeups, timers, memory registration,
  IKC exchange, sysfs object creation, page-table mutation, page I/O,
  user-copy, and broad lock/list ownership.
- Continue object/file/procfs/sysfs conversion only where runtime coverage can
  exercise the path: file-backed mmap, `/proc/PID/mem`, sysfs create/show/store,
  device PFN mappings, and hugetlbfs-backed mappings.
