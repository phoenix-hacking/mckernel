# McKernel Rust Migration Agent Notes

Updated: 2026-05-24

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
  work toward actual 100% completion has added +248 more verified aggregate
  points so far, but the full port is not complete. Count only verified,
  McKernel-owned movement; do not inflate percentages with external software,
  third-party code, or unverified high-risk mutation.
- `migration.txt` is the stricter x86_64 core-OS ownership tracker. It answers
  whether core McKernel C bodies have been replaced by Rust-owned core
  programs, not whether Rust helper coverage exists. Current strict x86_64
  core Rust ownership is about 75% (roughly 70-80%); C may remain for ABI shims, fallback
  scaffolding, trivial adapters, and external primitive callbacks, but Rust
  helper-only trampolines do not count as full core ownership.
- `migration.txt` also tracks the final standalone Rust target. This is
  stricter than strict core ownership: everything below the supported
  application/user-code boundary should be Rust-owned by default. Other people
  can still write C or other language code on top of McKernel, and public
  compatibility headers can remain, but the kernel/control-plane
  implementation underneath should not require McKernel-owned C execution
  bodies or C fallback implementations. Current standalone Rust readiness is
  about 40% (roughly 35-45%).
- The previous active continuation target was +50 aggregate functional points.
  Its verified movement is +50 broad dashboard points, so that continuation
  target is complete. The same work is about +53 strict-core points in
  `migration.txt`, after completing the earlier +35 continuation.
- The current requested continuation target is +50 aggregate functional
  points, not +32. The current verified movement is +50 broad dashboard
  points, and about +60 strict-core points in `migration.txt`, so this
  continuation target is complete. Older +32 references are historical 32/50
  checkpoints from a completed prior continuation, not a live goal.
- Post-+50 strict-core movement has added +6 strict syscall points so far by
  moving `waitid()` SIGCHLD siginfo copyout-body sequencing and `wait4()`
  wrapper validation/do-wait/copyout sequencing plus `waitid()` wrapper
  validation/do-wait/siginfo-return sequencing and `wait_continued()`
  status/reap/result sequencing into Rust. This does not add broad dashboard
  percentage because the Syscall Core row is already capped at 100%.
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
- QEMU boot-path setup on 2026-05-24 installed Rocky QEMU/libvirt/image/debug
  tooling and exposed `qemu-system-x86_64` through the Rocky `qemu-kvm` binary.
  Libvirt is active, but `/dev/kvm` is not exposed in this environment, so QEMU
  boot validation must start with TCG/software emulation unless nested KVM is
  enabled. No in-tree system-QEMU McKernel boot harness exists yet. Existing
  Rocky boot scripts still rely on the mcreboot/VM path and must not be run
  without explicit approval.

## Current Rust Ownership Baseline

The dashboard below is a functional-area estimate from `overview.txt`, not a
strict line-count. It is the progress score for this goal. A conservative
mechanical LOC report remains available with `scripts/rust-ownership-report.py`
only as a debt inventory.

| Area | Rust % | Status |
| --- | ---: | --- |
| Rust build/link foundation | 95 | Rust objects build and link into `mckernel.img`; user tools link Rust helper objects; IHK Linux-module Kbuild links Rust helpers into `ihk`, `ihk-smp-x86_64`, and `mcctrl`; Rust-linked module-load smoke has passed. |
| ABI/layout foundation | 100 | Shared kernel/user structs plus private process/thread lifecycle, wait/futex, timer, x86 signal action/altstack/siginfo/signalfd layouts, x86 CPU-local page and kernel-context layouts, x86 TLS user descriptor layout, ptrace user register/fpreg/user layouts, x86 descriptor/TSS/fxsave/xsave/YMM/LWP/bound-register save-state layouts, futex hash-bucket/key/queue layouts, syscall/init/post, procfs, coredump coretable, ELF core headers/notes/prstatus/prpsinfo, `iovec`, sysinfo, time-of-day, interval-timer and profile-event layouts, CPU mapping, perf, UTI, move-pages SMP request layouts, sysfs create/mkdir/symlink/lookup/unlink/setup request layouts, sysfs ops/handle/bitmap layouts, low-level rwlock, `kref`, rbtree augmentation callbacks, ftrace branch data, memobj ops/object state, SysV shared-memory limits/info/lock-user state, XPMEM ID/hash/thread-group/segment/access-permit/partition/permission/attachment layouts, `timeval`/`rusage`, pager create/map results, memory area/node/page-allocator ops/TLB-flush/page-cache headers, CPU-local/kmalloc/backlog/SMP-call layouts, IHK monitor/register/resource, host Linux device/OS/file layouts, and IHK kmsg/event/notifier/aux-call layouts are covered for the currently scoped x86_64/Rocky ABI foundation. This closes known layout prerequisites; mutation-heavy runtime bodies still need Rust ownership. |
| Shared primitives | 100 | rbtree, llist, plist, waitqueue init/entry/list core, wake scheduling predicate, string/memory leaf helpers, numeric parsers including `skip_atoi()` format width/precision pointer advancement, `number()` sign/prefix/width/precision/padding/output orchestration for `vsnprintf()` numeric and pointer paths, `format_decode()` parsing of flags, width, precision, qualifiers, and conversion types, `string()` output formatting for `%s`, base-10 decimal formatting digit emission for `vsnprintf()`, bitops, bitmap, parse, zero-area search, and region helpers are Rust-owned. |
| x86_64 memory management | 100 | Classification, NUMA/page queries, splitability, page-attribute conversion, PTE value shaping, page-size PTE validation/value selection, early allocator arithmetic/exhaustion checks, page-table index calculation, walk-bound calculation, normal/safe page-table walk iteration, callback result folding, optional physical-address skip policy, virtual-to-physical per-level miss/walk/hit decisions and physical/size result shaping, split-large-page preparation/entry arithmetic, split-large-page source classification, child-map physical derivation, page-table publish entry shaping, source-unmap gate selection, PTE direct-store helpers, atomic child-table publication helpers, PTE clear-exchange helpers, attribute-apply mutation helpers, page-clear alignment/target selection, page-table visit/direct-walk decision policy, clear/free-range validation and large-entry action selection, clear-range old-PTE phys/fileoff/dirty classification plus flush/free/unmap action selection, change-attribute leaf/large/walk action selection, set-range leaf/direct-large/allocate/busy/walk action selection, set-range mapped physical/PTE value shaping for 4 KiB/2 MiB/1 GiB entries, lookup-pte default size/level hit/walk/miss/shape decisions, move-PTE fileoff preflight/destination shaping/PTE phys-attr splitting, page-table destroy descend/skip policy, destroy child-table physical extraction, page-table root create/destroy-root lifecycle orchestration, page-table prepare-map first-level allocation/publish and last-level set-page callback orchestration, exported set-PTE body sequencing/log/panic/store orchestration, page refcount/hash lifecycle helpers, `page_map()` count increments, locked `page_unmap()` count/list deletion and lock orchestration, locked `phys_to_page()` lookup orchestration, locked `phys_to_page_insert_hash()` lookup/allocation-callback/insert orchestration, locked page-hash count-all traversal, phys-to-page hash traversal, hash insertion initialization, page-hash bucket init/count, VM range validation, memory-policy validation, and selected pager/object sizing helpers are Rust-owned; page-table allocation/free primitives, destroy recursion below the root, `phys_to_virt()`/free orchestration, callback execution, higher-level visitor and page-table traversal orchestration, actual page frees, RSS updates, mapping/free rollback orchestration, page-hash spinlock/allocation primitives and logging, TLB-sensitive flushing, and user-copy remain C. |
| Page allocator | 100 | Rbtree helper cluster, bitmap-backed no-lock allocator internals, bitmap public locked-wrapper orchestration for alloc/reserve/free/count/query/zero-free, `__ihk_pagealloc_init()` layout/allocation-callback/descriptor-init/lock-callback/tail-reservation orchestration, init layout/end/count calculation, descriptor zeroing and descriptor field initialization, tail-map reservation, destroy-page count and descriptor destroy/free-callback orchestration, exported add-free log/error/return sequencing, NUMA free/alloc helpers, public zero-free wrapper dispatch, NUMA zero-free dispatcher/all-node traversal, exported `ihk_numa_alloc_pages()` top-level allocation body sequencing, main `ihk_numa_alloc_pages()` cache-first/source-selection/fallback-to-NUMA orchestration, exported `ihk_numa_free_pages()` CPU-cache/direct/deferred top-level body sequencing, main `ihk_numa_free_pages()` direct-versus-deferred free orchestration and post-action completion sequencing, main NUMA allocation lock-callback orchestration, direct free-to-tree lock-callback orchestration, deferred-free enqueue/zero-request orchestration, free-path policy, zeroing-worker atomic increment, CPU-local cache action classification, CPU-local cache rb-tree allocation/free helper entry points, CPU-local cache alloc/free fast-path orchestration with interrupt callback ordering and result classification, CPU-local storage initialization, CPU-local variable selection, normal preempt counter updates, kmalloc chunk header initialization, sorted kmalloc free-list insertion, adjacent free-chunk consolidation, Linux zero-request action selection, deferred-zero IKC packet field shaping, Linux zero-request preparation including current/idle/nohost/worker/pid checks plus packet fill and worker increment, and deferred-zero send/log callback sequencing are Rust-owned; logging callbacks, actual `ihk_mc_alloc_pages()`/`ihk_mc_free_pages()` and MCS/interrupt primitives, broader allocator lifetime, IKC channel lookup, current-thread/channel lookup, actual IKC send side effects, deferred-zero worker timing, and FUGAKU debug preempt path remain C. |
| Process/VM management | 100 | Wait/clone/ptrace/VM policy, fork VM/thread metadata copy, address-space release and PID detach mutation, range-cache lookup relation plus range-cache replace/store mutation for join, free, and lookup paths, post-bounds `add_process_memory_range()` orchestration including VM range object initialization, mapping-action selection, insert/update failure cleanup, returned-range publication, and VM range-tree insertion traversal/link/color mutation, VM range end/flag commit mutation for extend-up and protection-change paths, stack-growth range-start alignment/commit mutation for the page-fault path, remove-range split/free preflight, split-range high-half field shaping and low-half end commit, join-range adjacency/object-offset validation and surviving-end commit, CPU-set fallback, mckfd decisions plus push/pop-head mutation, TID-table scan/index decisions, TID slot release/replace writes, sigpending list pop/unlink, process/thread list add/detach helpers, terminate child cleanup list unlink/reparent mutation helpers, thread report-list attach/detach mutation helpers, ptrace main-thread attach/detach reparent helpers, ptrace detach/wakeup state and pending-signal cleanup helpers, wait signal-flag and exit-status reap mutation helpers, terminate/wait report-thread release cleanup helpers, optional ptrace/fp cleanup gates, and lifecycle/refcount predicates are Rust-owned; VM range allocation/free callbacks, memobj refcounting, TOFU split/merge hooks, range-tree erase/removal side effects, page-fault handling, access-check orchestration, page-table lookup/allocation/mapping side effects, page-table attribute mutation/free/clear, broader child-list orchestration, rusage aggregation, broad process lifetime mutation, signal forwarding, and full wait orchestration remain C. |
| Syscall core | 100 | SysV shm, prlimit, scheduler, syscall/range validation, credential-refresh forwarding gates, requester-TID and preempt-disable gates, getpid/getppid/gettid/set_tid_address return shaping plus direct ID leaf bodies, getuid/geteuid/getgid/getegid process-field leaf bodies, getresuid/getresgid ordered field-read and user-copy callback sequencing, memory-policy, mmap/brk/mincore, mprotect split/write-change decisions, signal/time, ptrace/process-vm, wait, execveat, clone, futex policy helpers, bounded wait/ptrace/termination/signal list rewiring, pending-signal delivery/offload-interrupt classification, ptrace wakeup/siginfo/eventmsg result classification, ptrace request dispatch classification, ptrace setoptions state mutation, ptrace attach traced-state mutation, ptrace event-message preparation, ptrace siginfo kernel-buffer preparation and pending-siginfo publication, ptrace peek/poke user-word status/callback orchestration, ptrace getregs/setregs register-word loop orchestration, ptrace peek/poke text status and VM-callback staging, ptrace fpregs status/callback orchestration, ptrace getregset/setregset iovec copy/callback/length-publication orchestration, wait/reap result-shape classification, getrusage dispatch/update classification, getrusage thread times-update mutation, getrusage TSC/timeval/rusage result shaping, process-exit status/siginfo classification, terminate cleanup/reparent action classification, clone spawn/TID/TLS/reparent result shaping, and ptrace detach signal-forward gates are Rust-owned; top-level syscall dispatch, actual user-copy primitive, Linux forwarding, locks, allocation/free, architecture fp/register/regset primitives, actual process-memory read/patch primitives, signal delivery, child-list mutation, rusage aggregation/traversal, CPU interrupt delivery, ptrace lookup/orchestration, and remaining high-risk handlers remain C. |
| Scheduler/timers/wait/futex | 100 | Waitqueue init/entry/list core, wake scheduling predicate, bounded runqueue/migration list rewiring plus runqueue length updates, timer spin-sleep/runqueue/remaining-time arithmetic, futex hash-table allocation-callback/pointer-publication/table-initialization orchestration, futex hash-bucket selection with hash callback, top-level futex command dispatch/private/realtime decode, clock-realtime rejection, wait/wake/requeue/wake-op callback selection, invalid-command callback routing, futex hash-bucket table lock/list initialization, futex key matching/key preparation plus wake/requeue decision policy, futex double hash-bucket lock/unlock ordering, futex wake-list scan/key-match/bitset/limit orchestration, futex wake target orchestration, futex requeue source-list scan/key-match/wake-vs-requeue/drop-count orchestration, futex requeue key-reference callback and key-copy publication, futex wait-setup key-init/get-key/queue-lock/get-value/mismatch cleanup orchestration, futex wake-list detach and lock-pointer clear, futex requeue list move and lock-pointer publication, futex waiter plist initialization/insertion, futex wait-queue bitset/requeue/UTI initialization, key-region zeroing, hash-bucket lock-pointer publication, waiter metadata publication, self-unqueue list detach, wait-side bitset validation, wait scheduling action classification, wait-state status/spin-sleep mutation, futex post-wait success/timeout/interrupt/retry classification, futex wake target classification, Linux response-channel fallback selection, futex wake IKC packet field publication, syscall-offload scheduling decisions, and scheduler/futex/signal/timer policy helpers are Rust-owned; futex allocation/hash primitive callbacks, actual spinlock primitives, IKC send and scheduler wake primitives, futex key lookup internals, key-reference implementation/lifetime, user-value load, IPIs, timer queues, context switching, address translation, race retry, user-value comparison, schedule/schedule_timeout behavior, and remaining futex queue/requeue/wait side effects remain C. |
| procfs/sysfs/xpmem/file objects | 100 | XPMEM and file/dev/procfs/sysfs/pager decision-helper surface is Rust-owned through multiple batches, including procfs cmdline/comm helpers, sysfs show/store/release response-body sequencing, and sysfs request packet dispatch; this is not full subsystem ownership because allocation, refcount mutation, lock/list mutation, remap/page-table mutation, page I/O, procfs buffer mutation, raw sysfs IKC send behavior, public IKC handler wrapping/logging, and user-copy remain C. |
| host/IKC/mcctrl/IHK modules | 100 | Rust helper linkage is active for `ihk`, `ihk-smp-x86_64`, and `mcctrl`; many host driver, OS/device exclusive-open refcount compare-exchange mutation, generic locked list add/delete mutation, generic list-membership traversal, generic next-entry cursor traversal for notifier/event/aux-call paths, kmsg buffer/container lifecycle mutation, kmsg container atomic count set/read/inc/dec/dec-return, reverse kmsg list lookup traversal, DMA request callback dispatch, load-file dispatch/read-loop policy, shutdown status policy, SMP, sysfs, IKC policy, and mcctrl helpers are Rust-owned, including deferred-zero worker list pop, payload clear, zeroed-list publish, and atomic counter updates; device allocation, memory registration, file I/O, waits/callbacks beyond the bounded DMA dispatcher, broader IKC exchange mutation, broad allocation/lifetime ownership, and kernel object lifecycle mutation remain pending. |
| User tools | 83 | `mcstat`, `mcexec`, `ihklib`, `mcinspect`, `eclair`, and crash-extension helper surfaces are substantially Rust-owned; device I/O, ioctl handling, DWARF/BFD walking, crash command orchestration, GDB process/socket orchestration, daemon/thread/event-loop mutation, dump NMI side effects, register/memory reads, and most IHK command mutation remain C. |
| Rocky runtime integration | 82 | Rust McKernel image and focused Rocky smokes have passed in prior runs; this pass did not run boot or reboot-capable validation. Wider runtime/performance coverage remains pending. |
| arm64 | 0 | Deferred until x86_64 stabilizes. |

Honest current distance: the non-arm64 functional dashboard average is 96.7%,
while the McKernel-owned core rows in this table average 100.0%. Mechanical LOC
audit is 19.9% and is not a progress score. The functional percentages track
verified Rust-owned surfaces, and they are not a claim that mutation-heavy
kernel bodies are already fully Rust. The current total distance to 100 is 40
aggregate functional points across non-arm64 dashboard rows, or 0 points
across the McKernel-owned core rows excluding build/host/user/Rocky/arm64.

## Strict Core OS Rust Ownership

`migration.txt` tracks the stricter target: the x86_64 McKernel core OS should
be Rust-owned, not merely have Rust helpers around C execution bodies. Keep this
section synchronized with `migration.txt` whenever strict core ownership moves.

What counts as full core ownership:

- Rust owns the primary execution body for a core OS operation.
- Rust owns the state transition, mutation, validation, error shaping, and
  side-effect orchestration for that operation.
- C is limited to public ABI entry points, fallback scaffolding, trivial
  adapters, or calls into external primitives that are not McKernel-owned logic.

Partial credit applies when Rust owns policy or bounded mutation, but C still
performs locks, allocation/free, user-copy, page-table writes, wakeups, IKC
sends, signal delivery, or lifecycle mutation.

Do not count these as full core ownership:

- Rust functions that only call back into the old C implementation.
- C orchestration paths that call Rust helper islands while keeping the main
  McKernel-owned execution body in C.
- Layout assertions, C ABI declarations, or tests by themselves.
- New C helper logic, unless it is clearly fallback or glue used to verify and
  route Rust behavior.

Current strict x86_64 core Rust ownership is about 75% (roughly 70-80%). This estimate is
lower than the broad `overview.txt` dashboard because remaining C still owns
high-risk core execution bodies: page-table mutation, allocator lifetime,
syscall dispatch, user-copy, process lifetime, page faults, scheduler
wake/context behavior, futex wake/wait side effects, signal delivery, IKC
exchange, and kernel object lifecycle.

## Standalone Rust End-State

The standalone Rust goal is stricter than strict core ownership. Strict core
100% means Rust owns the McKernel core execution bodies. Standalone Rust 100%
means the default x86_64/Rocky kernel and required control-plane path can stand
as a Rust implementation below the external/user-code boundary.

What counts:

- Rust owns all McKernel-owned non-assembly implementation logic needed to boot,
  run, schedule, manage memory, service syscalls, handle waits/futexes/signals,
  exchange required IKC/control-plane messages, and shut down.
- The default build/runtime path does not need C fallback bodies for
  McKernel-owned behavior.
- C, if present, is limited to external compatibility headers, optional
  user-facing API wrappers, generated/declared ABI surfaces, third-party or
  Linux-owned interfaces, tests, and unavoidable architecture assembly.
- Rust APIs are the native internal substrate for allocation/lifetime,
  refcounting, page tables, user-copy orchestration, scheduling, object
  lifecycle, and control-plane behavior.

Do not count as standalone Rust:

- Required C fallback implementations for McKernel-owned logic.
- C wrappers that still perform primary allocation, mutation, traversal,
  user-copy, wakeup, page-table, IKC, signal, or lifecycle side effects.
- Rust helpers that only validate, shape, or call back into C-owned bodies.
- C build/link steps that are required because the implementation still lives
  in C rather than because of external ABI compatibility.

Current standalone Rust readiness is about 40% (roughly 35-45%). Keep this
lower than strict-core ownership until C fallbacks, C runtime bodies, and C
control-plane implementation dependencies stop being required by the default
OS path.

| Area | Overview % | Strict Core % | Strict Core Status |
| --- | ---: | ---: | --- |
| ABI/layout foundation | 100 | 100 | Currently complete for the scoped x86_64/Rocky ABI foundation. Rust/C assertions cover pager create/map result layouts, memory area/node/page-allocator ops/TLB-flush/page-cache headers, rusage-percpu, kmalloc metadata, SMP-call packets, backlog entries, full CPU-local storage layout, x86 CPU-local page and kernel-context layouts, x86 TLS user descriptor layout, x86 signal action/altstack/siginfo/signalfd layouts, ptrace user register/fpreg/user layouts, x86 descriptor/TSS/fxsave/xsave/YMM/LWP/bound-register save-state layouts, futex hash-bucket/key/queue layouts, syscall/init/post, procfs, coredump coretable, ELF core headers/notes/prstatus/prpsinfo, `iovec`, sysinfo, time-of-day, interval-timer and profile-event layouts, CPU mapping, perf, UTI, move-pages SMP request layouts, sysfs create/mkdir/symlink/lookup/unlink/setup request layouts, sysfs ops/handle/bitmap layouts, low-level rwlock, `kref`, rbtree augmentation callbacks, ftrace branch data, memobj ops/object state, SysV shared-memory limits/info/lock-user state, and the XPMEM ID/hash/thread-group/segment/access-permit/partition/permission/attachment object graph. This is prerequisite ownership, not runtime ownership of mutation-heavy bodies. |
| Shared primitives | 100 | 94 | Numeric parsing, `skip_atoi()` format width/precision pointer advancement, `number()` sign/prefix/width/precision/padding/output orchestration, `format_decode()` format-token parsing, `string()` `%s` output formatting, and base-10 decimal digit emission for `vsnprintf()` are Rust-owned; remaining work is making these primitives the normal Rust-side substrate for core bodies. |
| x86_64 memory management | 100 | 64 | Page-table decisions, page-table root create/destroy-root lifecycle orchestration, page-table prepare-map orchestration, exported set-PTE body sequencing, and page refcount/hash lifecycle bodies moved, but page-table allocation/free primitives, recursive child-table destruction below the root, traversal orchestration, page frees, RSS updates, TLB-sensitive flushing, physical/free orchestration, page-hash primitives/logging, and user-copy remain C-owned. |
| Page allocator | 100 | 72 | Bitmap, NUMA, `__ihk_pagealloc_init()` orchestration, exported add-free log/error/return sequencing, public zero-free wrapper dispatch, exported `ihk_numa_alloc_pages()` top-level allocation body sequencing, main `ihk_numa_alloc_pages()` cache-first/source-selection/fallback-to-NUMA orchestration, exported `ihk_numa_free_pages()` CPU-cache/direct/deferred top-level body sequencing, main `ihk_numa_free_pages()` direct-versus-deferred free orchestration, free post-action completion sequencing, CPU-local storage initialization, CPU-local variable selection, normal preempt counter updates, kmalloc chunk header initialization, sorted kmalloc free-list insertion, and adjacent free-chunk consolidation moved, but allocator lifetime, actual allocation/free primitives, MCS/interrupt primitives, IKC channel lookup/send side effects, logging primitive bodies, deferred-zero worker timing, FUGAKU debug preempt behavior, and broader orchestration remain C-owned. |
| Process/VM management | 100 | 70 | Many lifecycle, wait, ptrace, range, list, post-bounds add-range orchestration bodies, and VM range-tree insertion traversal/link/color mutation moved, but VM range allocation/free callbacks, memobj refcounting, range-tree erase/removal side effects, page faults, actual page-table lookup/allocation/mapping side effects, child-list orchestration, rusage aggregation, broad process lifetime, and signal forwarding remain C-owned. |
| Syscall core | 100 | 72 | Policy, many handler subpaths, direct ID leaf bodies, simple uid/gid getter bodies, getresuid/getresgid ordered field-read plus user-copy callback sequencing, sigaltstack old-stack copyout/new-stack copyin/validation/thread-stack mutation sequencing, waitid SIGCHLD siginfo construction/copyout callback sequencing, wait4 wrapper validation/do-wait/copyout sequencing, waitid wrapper validation/do-wait/siginfo-return sequencing, and wait_continued status/reap/result sequencing moved, but top-level dispatch, the actual user-copy primitive, Linux forwarding, locks, allocation/free, register/fp primitives, process-memory access, signal delivery, ptrace orchestration, wait scanning/sleeping/list traversal internals, and high-risk handler bodies remain C-owned. |
| Scheduler/timers/wait/futex | 100 | 63 | Queue/list helpers, policies, futex table orchestration, futex bucket selection, top-level futex command dispatch, and futex wake target orchestration moved, but timer queues, spinlock primitives, IPIs, context switching, futex key lifetime, user-value loads, allocation/hash callbacks, IKC send and scheduler wake primitives, race retry, schedule behavior, and wait/requeue side effects remain C-owned. |
| procfs/sysfs/xpmem/file objects | 100 | 67 | Helper surface is complete, and sysfs show/store/release response-body sequencing plus sysfs request packet dispatch moved into Rust. Allocation, refcount mutation, lock/list mutation, remap/page-table mutation, page I/O, procfs buffer mutation, raw sysfs IKC send behavior, public IKC handler wrapping/logging, and user-copy still block full ownership. |
| host/IKC/mcctrl/IHK kernel paths | 100 | 63 | Broad helper/control-plane coverage is complete, and the bounded IHK host DMA request callback dispatcher moved into Rust. Device allocation, memory registration, file I/O, waits/callbacks beyond that dispatcher, broad IKC exchange mutation, broad allocation/lifetime, and kernel object lifecycle remain C-owned. |

Latest strict-core movement for the revised +35 continuation:

- Broad dashboard movement is +35 verified points and the revised continuation
  target is complete.
- Strict-core movement is about +33 points because the latest bodies moved real
  page-hash, futex-table, futex-bucket, page-allocator init, allocator
  allocation-orchestration, allocator free-orchestration, futex dispatch, and
  Process/VM range-object initialization, mapping-action selection, and
  add-range orchestration into Rust rather than adding helper-only trampolines.
- Remaining work for this continuation is 0 broad dashboard points.

Latest strict-core movement for the completed prior +50 continuation:

- Broad dashboard movement is +50 verified points, so that prior +50
  continuation target is complete.
- Strict-core movement is about +53 points because Rust now owns
  `vm_range_insert()` traversal and mutation: range-tree descent, overlap
  rejection, success/overlap callback sequencing, `rb_link_node()`
  publication, and `rb_insert_color()` balancing. Rust also owns the direct
  process/thread ID leaf bodies for `getpid`, `getppid`, `gettid`,
  `set_tid_address`, `getuid`, `geteuid`, `getgid`, and `getegid`, including
  field reads and `clear_child_tid` publication. Rust also owns futex wake
  target orchestration, including mark-woken sequencing, Linux-vs-McKernel
  target selection, IKC packet fill, send callback sequencing, scheduler wake
  callback sequencing, and wake logging. Rust also owns `getresuid()` and
  `getresgid()` ordered field-read plus user-copy callback sequencing. Rust
  also owns page-allocator free post-action completion:
  direct-free success/error logging selection, deferred-free error/skip/send
  action handling, Linux zero-request send callback sequencing, and send
  success/failure logging. Rust also owns exported `ihk_numa_free_pages()`
  top-level body sequencing: CPU-cache free attempt classification, cache
  success/error log selection, direct-versus-deferred free dispatch, Linux
  zero-request send callback sequencing, final log selection, and return
  shaping. Rust also owns exported `ihk_numa_alloc_pages()` top-level
  allocation body sequencing: cache-hit logging selection, direct-allocation
  logging selection, source-aware return shaping, and exported allocation
  handoff around cache-first/source-selection/fallback-to-NUMA orchestration.
  Rust also owns exported `ihk_numa_add_free_pages()` and public
  `ihk_numa_zero_free_pages()` top-level sequencing: add-free success/error log
  selection, return shaping around the NUMA add-free mutation body, and public
  zero-free dispatch into the Rust-owned zero-list publication path.
  Rust also owns pager/memory-control ABI layout coverage for pager create/map
  results, memory area/node/page-allocator ops/TLB-flush/page-cache headers,
  plus CPU-local/rusage-percpu/kmalloc/backlog/SMP-call layout coverage. Rust
  also owns CPU-local storage initialization sequencing,
  `get_cpu_local_var()` pointer selection, normal preempt counter inc/dec,
  Rust-owned base-10 decimal digit emission for the `vsnprintf()` numeric path,
  and Rust-owned `skip_atoi()` format width/precision pointer advancement.
  Rust also owns kmalloc chunk header initialization, sorted free-list
  insertion, and adjacent free-chunk consolidation.
  Rust also owns x86 page-table root lifecycle:
  `ihk_mc_pt_create()` allocation-callback orchestration, root zeroing,
  kernel-half entry copy from `init_pt`, and `ihk_mc_pt_destroy()` root
  kernel-half clearing plus destroy-recursion callback dispatch. Rust also owns
  `ihk_mc_pt_prepare_map()` initial page-table selection, L4 range traversal,
  present-entry short-circuiting, allocation callback sequencing, L4 entry
  publication, last-level set-page callback loop sequencing, and first error
  return propagation. Rust also owns `ihk_mc_pt_set_pte()` page-size/value
  selection callback orchestration, alignment error classification,
  log-callback selection, panic-callback dispatch for invalid page sizes, PTE
  store invocation, and final return shaping. The C side keeps ABI wrappers,
  current-thread lookup, argument extraction, the actual user-copy primitive,
  actual IKC send primitive, logging/dump callbacks,
  actual allocator/free primitives, recursive child-table destruction below the
  root, and fallback implementations.

Latest strict-core movement for the active +50 continuation:

- Broad dashboard movement is +50 verified points, so the active +50
  continuation is complete.
- Strict-core movement is about +60 points because Rust now owns the central
  `number()` formatter body for `vsnprintf()` numeric and pointer paths:
  sign handling, prefix selection, width and precision adjustment, zero/space
  padding, octal/hex/decimal digit staging, bounded output writes, and returned
  pointer advancement. Rust also owns `format_decode()` parsing of literal
  spans, flags, field width, precision, qualifiers, conversion type, base,
  signedness, and width/precision continuation state. C keeps the surrounding
  `vsnprintf()` loop, va_arg extraction, string and pointer extension dispatch,
  `%n` writes, final NUL termination, and output buffer lifetime. Rust also
  owns `string()` `%s` output formatting: NULL-string substitution,
  precision-bounded length selection, left/right padding, bounded output
  writes, and returned pointer advancement.
- ABI/layout foundation strict core also moved 62% -> 66% because Rust/C now
  assert x86 signal action, altstack, `siginfo_t`, `signalfd_siginfo`, ptrace
  `user_regs_struct`, `user_fpregs_struct`, `struct user`, futex
  hash-bucket/key/queue layouts, and the key offsets needed before signal,
  ptrace, and futex body ownership can safely move.
- ABI/layout foundation strict core then moved 66% -> 70% because Rust/C now
  assert syscall/control-plane structures used by syscall setup, procfs,
  coredump, sysinfo/time publication, CPU mapping, perf control, UTI context,
  and move-pages SMP requests before those core bodies move.
- ABI/layout foundation strict core then moved 70% -> 74% because Rust/C now
  assert x86 descriptor, TSS, fxsave/xsave, YMM, LWP, and bound-register
  save-state structures used by ptrace, signal-frame FPU save/restore,
  register access, and context paths.
- ABI/layout foundation strict core then moved 74% -> 78% because Rust/C now
  assert sysfs create, mkdir, symlink, lookup, unlink, and setup request packet
  layouts used by the Rocky control-plane exchange.
- ABI/layout foundation strict core then moved 78% -> 82% because Rust/C now
  assert ELF core headers, program headers, note headers, `elf_siginfo`,
  `prstatus64_timeval`, `elf_prstatus64`, `elf_prpsinfo64`, and `iovec`
  layouts used by coredump and user-vector paths.
- ABI/layout foundation strict core then moved 82% -> 87% because Rust/C now
  assert the x86 CPU-local page, x86 kernel context, TLS `user_desc`, sysfs
  operation callbacks/handle/bitmap parameters, `itimerval`, and
  `profile_event` layouts used by CPU-local, sysfs, profiling, timer, and TLS
  paths.
- ABI/layout foundation strict core then moved 87% -> 100% because Rust/C now
  asserts low-level `ihk_rwlock`, `kref`, rbtree augmentation callbacks,
  ftrace branch-data records, `memobj_ops`, `memobj`, SysV shm limit/info and
  lock-user state, and the XPMEM ID/hash/thread-group/segment/access-permit/
  partition/permission/attachment object graph. This closes the known
  x86_64/Rocky layout prerequisite row, but XPMEM attach/detach, SysV shm
  lifetime, memobj refcounting, page I/O, ftrace accounting, rbtree mutation,
  locking primitives, allocation/free, user-copy, and object lifecycle side
  effects still need Rust runtime ownership.
- host/IKC/mcctrl/IHK kernel paths strict core moved 62% -> 63% because Rust
  now owns `ihk_dma_request()` callback dispatch for the IHK host core DMA
  request path: channel/ops validation, request callback presence gate,
  callback invocation, and `-EINVAL` shaping for the no-callback path. C keeps
  the exported ABI wrapper, fallback, and DMA provider callback body.
- Syscall core strict ownership moved 63% -> 66% because Rust now owns
  `sigaltstack()` body sequencing: optional old-stack copyout, optional
  new-stack copyin, validation, disabled-stack normalization, and thread
  `sigstack` publication. C keeps the syscall ABI wrapper, current-thread
  lookup, actual user-copy primitive callbacks, and fallback implementation.
- procfs/sysfs/xpmem/file object strict ownership moved 60% -> 64% because
  Rust now owns sysfs show/store/release response-body sequencing: default
  ssize/error shaping, optional callback dispatch, response packet msg/err/arg
  publication, send callback dispatch, and output publication. C keeps callback
  bodies, the actual `ihk_ikc_send()` primitive, logging, global buffer
  lifetime, packet-handler dispatch, allocation/free, sysfs path formatting,
  busy waits, host-side object creation, user-copy, and fallback
  implementation.
- procfs/sysfs/xpmem/file object strict ownership moved 64% -> 67% because
  Rust now owns sysfs packet dispatch for show/store/release requests:
  request-kind classification, typed callback selection, show/store/release
  callback dispatch, store-size publication from the incoming packet error
  field, and unknown-message classification. C keeps the public IKC handler
  wrapper, unknown-message logging, callback bodies, raw IKC send behavior,
  global buffer lifetime, allocation/free, sysfs path formatting, busy waits,
  host-side object creation, user-copy, and fallback implementation.
- Post-+50 strict-core movement added Syscall core 66% -> 67% because Rust now
  owns `waitid()` SIGCHLD siginfo copyout-body sequencing: eligibility,
  zeroed `siginfo_t` preparation, `si_signo`/`si_code` and child PID/status
  population, timeval-to-jiffy conversion for child utime/stime, and copyout
  callback dispatch. C keeps the syscall ABI wrapper, `do_wait()` scanning and
  sleep behavior, wait locks, status/rusage production, the actual
  `copy_to_user()` primitive, scheduler behavior, and fallback implementation.
- Post-+50 strict-core movement then added Syscall core 67% -> 69% because Rust
  now owns `wait4()` wrapper sequencing: option validation, zeroed
  `struct rusage` preparation, `do_wait()` callback invocation with `WEXITED`,
  status copyout gating, rusage copyout gating, copyout callback dispatch, and
  final return shaping. C keeps the syscall ABI wrapper, raw argument
  extraction, `do_wait()` scanning and sleep behavior, wait locks, the actual
  `copy_to_user()` primitive, scheduler behavior, and fallback implementation.
- Post-+50 strict-core movement then added Syscall core 69% -> 71% because Rust
  now owns `waitid()` wrapper sequencing: idtype-to-wait-pid validation,
  option validation, zeroed `struct rusage` preparation, `do_wait()` callback
  invocation, negative wait-result propagation, siginfo copyout dispatch, and
  final waitid return shaping. C keeps the syscall ABI wrapper, raw argument
  extraction, `do_wait()` scanning and sleep behavior, wait locks, the actual
  `copy_to_user()` primitive, scheduler behavior, and fallback implementation.
- Post-+50 strict-core movement then added Syscall core 71% -> 72% because Rust
  now owns `wait_continued()` body sequencing: continued-status publication,
  main-thread versus report-thread signal-flag reap target selection,
  continued-signal reap callback dispatch, WNOWAIT preservation through the
  existing reap helper, and process-pid versus thread-tid return selection. C
  keeps the wait list scans, wait locks, caller-side duplicate reap behavior,
  scheduler behavior, and fallback implementation.

Primary remaining C blockers for "core C replaced with Rust core":

- Page-table allocation/free primitives, recursive child-table destruction below
  the root, traversal orchestration, page frees, RSS updates, TLB-sensitive
  flushing, and map/free rollback.
- Page allocator lifetime, remaining CPU-local allocator-cache ownership, allocation/free-to-
  system primitives, deferred-zero publication, and IKC-backed zeroing effects.
- Process and VM lifetime: VM range allocation/free, memobj refcounting,
  range-tree erase/removal, page-fault orchestration, child-list mutation, rusage
  aggregation, wait orchestration, signal forwarding, and release paths.
- Syscall entry/dispatch, user-copy boundaries, Linux forwarding, remaining
  high-risk handlers, and architecture register/fp/regset operations.
- Scheduler/timer/futex bodies: timer queues, wakeups, IPIs, context switching,
  futex allocation primitive callbacks, futex dispatch side-effect callback
  bodies, futex key lifetime, user-value loads, futex wait/wake/requeue side
  effects, and race retry behavior.
- Kernel-side Rocky control plane: IKC exchange mutation, callback invocation,
  waits, object allocation/free, device lifecycle, memory registration, file
  I/O, and kernel object lifecycle.

Strict tracker update rule:

- Update `overview.txt` for broad functional dashboard movement.
- Update `migration.txt` and this AGENTS section only when Rust owns more of a
  primary core body, not merely another helper called by C.
- Record C additions as glue/fallback only; do not count new C decision logic
  as Rust progress.

## Distance To 100

| Area | Current | Points To 100 |
| --- | ---: | ---: |
| Rust build/link foundation | 95 | 5 |
| ABI/layout foundation | 100 | 0 |
| Shared primitives | 100 | 0 |
| x86_64 memory management | 100 | 0 |
| Page allocator | 100 | 0 |
| Process/VM management | 100 | 0 |
| Syscall core | 100 | 0 |
| Scheduler/timers/wait/futex | 100 | 0 |
| procfs/sysfs/xpmem/file objects | 100 | 0 for helper/decision surface; mutation bodies still C |
| host/IKC/mcctrl/IHK modules | 100 | 0 |
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
- The latest +10 verified continuation slice toward the revised +35 goal
  routes page refcount/hash lifecycle bodies, `__ihk_pagealloc_init()`
  orchestration, and futex table allocation/publication/initialization
  orchestration through Rust helpers with C fallbacks and equivalence coverage.
  In `migration.txt` this is about +8 strict-core points because these are
  real core-body moves rather than helper-only trampolines. C still owns the
  external allocation and lock primitives, page frees, page-table mutation,
  futex wake/wait/requeue side effects, scheduler handoff, user-copy, and
  broad runtime lifetime behavior.
- The latest +5 verified continuation slice toward the revised +35 goal routes
  page-hash lock/allocation orchestration and futex hash-bucket selection
  through Rust helpers with C fallbacks and equivalence coverage. In
  `migration.txt` this adds about +5 strict-core points because Rust now owns
  the lock/unlock callback ordering around page-hash count/lookup/insert/unmap
  plus futex bucket selection, while C keeps the primitive spinlock,
  allocation, and key-hash callbacks. C still owns page-hash debug logging,
  page frees, page-table mutation, futex wake/wait/requeue side effects,
  scheduler handoff, user-copy, and broad runtime lifetime behavior.
- The latest +3 verified continuation slice toward the revised +35 goal routes
  `ihk_numa_alloc_pages()` cache-first/source-selection/fallback-to-NUMA
  orchestration through Rust helpers with C fallbacks and equivalence coverage.
  In `migration.txt` this adds about +3 strict-core points because Rust now
  owns the main allocation path's cache attempt, fallback selection, and source
  publication. C still owns CPU-local variable selection, logging, actual IRQ
  and MCS primitives, allocation/free primitives, IKC send side effects,
  zeroed-list publication, deferred-zero worker timing, and broader allocator
  lifetime.
- The latest +3 verified page-allocator free slice toward the revised +35 goal
  routes `ihk_numa_free_pages()` direct-versus-deferred free orchestration
  through Rust helpers with C fallbacks and equivalence coverage. In
  `migration.txt` this adds about +3 strict-core points because Rust now owns
  direct/free/deferred/ignored action selection and result publication for the
  post-cache free path. C still owns CPU-local current/channel selection,
  logging, actual IRQ and MCS primitives, IKC send side effects, zeroed-list
  publication, deferred-zero worker timing, and broader allocator lifetime.
- The latest +3 verified scheduler/futex dispatch slice toward the revised
  +35 goal routes top-level `futex()` command decode, private/realtime flag
  handling, clock-realtime rejection, wait/wake/requeue/wake-op callback
  selection, and invalid-command callback routing through Rust helpers with C
  fallbacks and equivalence coverage. In `migration.txt` this adds about +3
  strict-core points because Rust owns more of the primary futex syscall body
  instead of only queue/list helper islands. C still owns the dispatch
  side-effect callback bodies, actual spinlock/allocation/hash primitives,
  futex key lifetime, user-value loads, wake/requeue/wait side effects, timer
  queues, scheduler handoff, and context switching.
- The latest +3 verified Process/VM range-initialization slice toward the
  revised +35 goal routes `add_process_memory_range()` VM-range object
  initialization through Rust helpers with C fallbacks and equivalence
  coverage. In `migration.txt` this adds about +3 strict-core points because
  Rust now owns rb-node clear state, range field publication, object offset,
  page shift, private data, straight-start reset, and optional Tofu list
  initialization for the new range object. At that point C still owned allocation/free,
  range-tree insertion, memobj refcounting, page-table updates, XPMEM side
  effects, rollback, user-copy, and broader VM lifetime behavior.
- The latest +3 verified Process/VM range mapping-action slice toward the
  revised +35 goal routes `add_process_memory_range()` map/no-map action
  selection through Rust helpers with C fallbacks and equivalence coverage. In
  `migration.txt` this adds about +3 strict-core points because Rust now owns
  NOPHYS skip, remote/uncached/normal page-table update attr selection, XPMEM
  mark action, demand-paging logging action, PROT_NONE skip, and memclear
  gating. At that point C still owned range allocation/free, range-tree insertion, memobj
  refcounting, actual page-table updates, XPMEM flag mutation, memclear,
  rollback, user-copy, and broader VM lifetime behavior.
- The latest +5 verified Process/VM add-range orchestration slice completes the
  revised +35 goal by routing the post-bounds `add_process_memory_range()` body
  through a Rust orchestrator with C fallbacks and equivalence coverage. In
  `migration.txt` this adds about +5 strict-core points because Rust now owns
  allocation-callback handling, VM range initialization, insertion/update
  callback sequencing, insert/update failure cleanup, XPMEM and demand-paging
  actions, memclear callback gating, and returned-range publication. C still
  owned allocation/free callbacks, range-tree insertion/removal side effects, memobj
  refcounting, actual page-table updates, XPMEM flag mutation, memclear side
  effects, rollback side effects, user-copy, and broader VM lifetime behavior.
- The latest +2 verified Process/VM range-tree insertion slice starts the
  completed prior +50 continuation by routing `vm_range_insert()` traversal,
  overlap rejection, success/overlap callback sequencing, `rb_link_node()`
  publication, and `rb_insert_color()` balancing through Rust with C fallbacks and
  equivalence coverage. In `migration.txt` this adds about +4 strict-core
  points because Rust now owns a real VM range-tree mutation body. C still
  owns allocation/free callbacks, memobj refcounting, TOFU split/merge hooks,
  range-tree erase/removal, actual page-table updates, XPMEM flag mutation,
  memclear side effects, rollback side effects, user-copy, and broader VM
  lifetime behavior.
- The latest +2 verified syscall ID leaf-body slice brings the completed prior
  +50 continuation to +4 broad points by routing `getpid`, `getppid`, `gettid`,
  `set_tid_address`, `getuid`, `geteuid`, `getgid`, and `getegid` process/thread
  field reads plus `clear_child_tid` publication through Rust with C fallbacks
  and equivalence coverage. In `migration.txt` this adds about +2 strict-core
  points because Rust owns real syscall leaf bodies rather than return-shaping
  helpers alone. C still owns syscall ABI wrappers, current-thread lookup,
  argument extraction, top-level dispatch, user-copy, Linux forwarding, locks,
  allocation/free, signal delivery, ptrace orchestration, architecture register
  primitives, and high-risk handler bodies.
- The latest +4 verified futex wake orchestration slice brings the completed
  prior +50 continuation to +8 broad points by routing futex wake target orchestration
  through Rust with C fallbacks and equivalence coverage: mark-woken sequencing,
  Linux-vs-McKernel target selection, Linux response-channel fallback
  selection, IKC wake packet fill, IKC send callback sequencing, scheduler wake
  callback sequencing, and wake logging. In `migration.txt` this adds about +4
  strict-core points because Rust owns the wake orchestration body while C keeps
  the primitive side-effect callbacks. C still owns futex key lifetime,
  user-value loads, IKC send and scheduler wake primitives, wait/requeue side
  effects, timer queues, IPIs, context switching, race retry, and
  schedule/schedule_timeout behavior.
- The latest +3 verified syscall getresid body slice brings the completed prior
  +50 continuation to +11 broad points by routing `getresuid()` and `getresgid()`
  body sequencing through Rust with C fallbacks and equivalence coverage:
  process credential field reads, ordered `ruid/euid/suid` and `rgid/egid/sgid`
  copy sequencing, and fault short-circuit behavior through a C `copy_to_user`
  callback. In `migration.txt` this adds about +3 strict-core points because
  Rust owns real syscall body sequencing while C keeps the actual user-copy
  primitive and syscall ABI wrapper.
- The latest +3 verified page-allocator free-finish slice brings the completed
  prior +50 continuation to +14 broad points by routing `ihk_numa_free_pages()`
  post-action completion sequencing through Rust with C fallbacks and
  equivalence coverage: direct-free success/error logging selection,
  deferred-free error/skip/send action handling, Linux zero-request send
  callback sequencing, and send success/failure logging. In `migration.txt`
  this adds about +3 strict-core points because Rust owns more of the primary
  free path while C keeps CPU-local channel lookup, the actual `ihk_ikc_send()`
  primitive, and logging primitive bodies.
- The latest +3 verified x86 page-table root-lifecycle slice brings the completed
  prior +50 continuation to +17 broad points by routing `ihk_mc_pt_create()` and
  `ihk_mc_pt_destroy()` root lifecycle sequencing through Rust with C fallbacks
  and equivalence coverage: allocation-callback orchestration, new root zeroing,
  kernel-half entry copy from `init_pt`, destroy-root kernel-half clearing, and
  destroy-recursion callback dispatch. In `migration.txt` this adds about +3
  strict-core points because Rust owns a real page-table lifecycle body while C
  keeps the actual allocator/free primitives, recursive child-table destruction
  below the root, and `phys_to_virt()`.
- The latest +3 verified x86 page-table prepare-map slice brings the completed
  prior +50 continuation to +20 broad points by routing `ihk_mc_pt_prepare_map()`
  orchestration through Rust with C fallbacks and equivalence coverage: initial
  page-table selection, first-level L4 range traversal, present-entry
  short-circuiting, allocation callback sequencing, L4 entry publication,
  last-level set-page callback loop sequencing, and first error return
  propagation. In `migration.txt` this adds about +3 strict-core points because
  Rust owns a page-table preparation body while C keeps the actual allocation
  primitive, `virt_to_phys()`, and `__set_pt_page()`.
- The latest +3 verified x86 set-PTE body slice brings the completed prior +50
  continuation to +23 broad points by routing `ihk_mc_pt_set_pte()` body
  sequencing through Rust with C fallbacks and equivalence coverage:
  page-size/value selection callback orchestration, alignment error
  classification, log-callback selection, panic-callback dispatch for invalid
  page sizes, PTE store invocation, and final return shaping. In
  `migration.txt` this adds about +2 strict-core points because Rust owns an
  exported page-table mutation body while C keeps debug log wrappers, actual
  log/panic primitives, traversal, and allocation/free primitives.
- The latest +3 verified page-allocator top-level free slice brings the completed prior
  +50 continuation to +26 broad points by routing exported
  `ihk_numa_free_pages()` body sequencing through Rust with C fallbacks and
  equivalence coverage: CPU-cache free attempt classification, cache
  success/error log selection, direct-versus-deferred dispatch, Linux
  zero-request send callback sequencing, final log selection, and return
  shaping. In `migration.txt` this adds about +4 strict-core points because
  Rust owns the exported free body while C keeps CPU-local variable selection,
  actual lock/interrupt primitives, IKC channel lookup/send side effects,
  logging primitive bodies, deferred-zero worker timing, zeroed-list
  publication, and allocator lifetime.
- The latest +3 verified page-allocator top-level allocation slice brings the
  completed prior +50 continuation to +29 broad points by routing exported
  `ihk_numa_alloc_pages()` body sequencing through Rust with C fallbacks and
  equivalence coverage: cache-hit logging selection, direct-allocation logging
  selection, source-aware return shaping, and exported allocation handoff around
  cache-first/source-selection/fallback-to-NUMA orchestration. In
  `migration.txt` this adds about +3 strict-core points because Rust owns the
  exported allocation body while C keeps CPU-local variable selection, actual
  cache/tree lock primitives, `ihk_mc_alloc_pages()`, MCS/interrupt primitives,
  logging primitive bodies, allocator lifetime, zeroed-list publication timing,
  deferred-zero worker timing, and fallback implementation.
- The latest +3 verified page-allocator add/zero top-level slice brought the
  completed prior +50 continuation to a historical 32/50 broad-point checkpoint by routing exported
  `ihk_numa_add_free_pages()` and public `ihk_numa_zero_free_pages()`
  sequencing through Rust with C fallbacks and equivalence coverage: add-free
  success/error log selection, return shaping around the NUMA add-free mutation
  body, and public zero-free dispatch into the Rust-owned zero-list publication
  path. In `migration.txt` this adds about +3 strict-core points because Rust
  owns more exported allocator body sequencing while C keeps logging primitive
  bodies, actual allocation/free and lock/interrupt primitives, allocator
  lifetime, IKC send side effects, deferred-zero worker timing, broad allocator
  mutation, and fallback implementation.
- The latest +7 verified ABI/shared-primitives slice brings the active +50
  continuation to +39 broad points by adding Rust/C compile-time layout mirrors
  for pager create/map result packets plus McKernel memory area/node,
  page-allocator ops, aligned TLB-flush entry, and page-cache header structs,
  and by routing `vsnprintf()` base-10 digit emission through Rust-owned
  `put_dec_trunc`, `put_dec_full`, and `put_dec` helpers. In `migration.txt`
  this adds about +7 strict-core points because Rust now owns more prerequisite
  ABI layout and an active shared formatting primitive while C keeps variadic
  format parsing, width/sign/precision buffer policy, output orchestration, and
  broader private lifecycle layout coverage.
- The latest +7 verified CPU-local lifecycle slice brings the active +50
  continuation to +46 broad points by adding Rust/C layout mirrors for
  `rusage_percpu`, kmalloc metadata, SMP-call packets, backlog entries, and
  the full x86_64 `cpu_local_var`, and by routing CPU-local storage
  initialization, `get_cpu_local_var()` selection, and normal preempt counter
  updates through Rust with C fallbacks. In `migration.txt` this adds about +8
  strict-core points because Rust now owns a CPU-local execution/lifecycle body
  as well as the prerequisite layout, while C keeps allocation/free primitives,
  MCS/interrupt primitives, logging callbacks, IKC send side effects,
  deferred-zero worker timing, FUGAKU debug preempt behavior, and broader
  allocator lifetime/mutation.
- The latest +4 verified kmalloc/shared-parser slice completes the active +50
  continuation by routing kmalloc chunk header initialization, sorted free-list
  insertion, adjacent free-chunk consolidation, and `skip_atoi()` format
  width/precision pointer advancement through Rust with C fallbacks and
  equivalence coverage. In `migration.txt` this adds about +4 strict-core
  points because Rust now owns bounded allocator mutation and a shared parser
  body while C keeps public `kmalloc()`/`kfree()` sequencing, heap metadata
  lifetime, the surrounding variadic formatter parser, output orchestration,
  locking context, primitive allocation/free behavior, and fallback
  implementations.
- The latest +4 verified shared-formatting slice starts the active +50
  continuation by routing `number()` sign, prefix, width, precision,
  zero/space padding, octal/hex/decimal digit staging, bounded output writes,
  and returned pointer advancement through Rust with C fallbacks and expanded
  equivalence coverage. In `migration.txt` this adds about +4 strict-core
  points because Rust now owns the central numeric/pointer formatter body while
  C keeps format-token decoding, string and pointer extension dispatch, va_arg
  extraction, `%n` writes, final NUL termination, and the surrounding
  `vsnprintf()` loop.
- The latest +4 verified shared-format-decoder slice brings the active +50
  continuation to +8 broad points by routing `format_decode()` literal-span,
  flag, field-width, precision, qualifier, conversion-type, base, signedness,
  and width/precision continuation-state parsing through Rust with C fallbacks
  and equivalence coverage. In `migration.txt` this adds about +4 strict-core
  points because Rust now owns the format-token parser body while C keeps the
  surrounding `vsnprintf()` loop, va_arg extraction, string and pointer
  extension dispatch, `%n` writes, final NUL termination, and output buffer
  lifetime.
- The latest +3 verified shared-string-format slice brings the active +50
  continuation to +11 broad points and completes the broad shared-primitives
  dashboard row by routing `string()` `%s` output formatting through Rust with
  C fallbacks and equivalence coverage. In `migration.txt` this adds about +3
  strict-core points because Rust now owns NULL-string substitution,
  precision-bounded length selection, left/right padding, bounded output
  writes, and returned pointer advancement while C keeps the surrounding
  `vsnprintf()` loop, va_arg extraction, pointer extension dispatch, `%n`
  writes, final NUL termination, and output buffer lifetime.
- The previous +4 verified signal/futex/register ABI-layout slice brings the
  active +50 continuation to +15 broad points by adding Rust/C compile-time
  layout mirrors for x86 signal action, altstack, `siginfo_t`,
  `signalfd_siginfo`, ptrace `user_regs_struct`, `user_fpregs_struct`,
  `struct user`, futex hash-bucket/key/queue layouts, and the offsets that
  feed future signal, ptrace, and futex body ownership. This adds about +4
  strict-core foundation points in `migration.txt`; C still owns top-level
  syscall dispatch, user-copy, signal delivery, actual register access
  primitives, futex key lifetime, wait/wake side effects, scheduler handoff,
  lock primitives, and IKC send behavior.
- The latest +4 verified syscall/control-plane ABI-layout slice brings the
  active +50 continuation to +19 broad points by adding Rust/C compile-time
  layout mirrors for `ikc_scd_init_param`, `syscall_post`, coredump
  `coretable`, procfs request/file descriptors, `sysinfo`, `tod_data_s`, CPU
  mapping requests, perf-control descriptors, UTI attributes/context, and
  `move_pages_smp_req`. This adds about +4 strict-core foundation points in
  `migration.txt`; C still owns procfs buffer mutation, perf-control side
  effects, UTI scheduling, time publication, move-pages page-table mutation,
  CPU mapping exchange, user-copy, locks, IKC exchange, callback bodies, and
  fallback implementation.
- The latest +4 verified x86 register/FPU save-state ABI-layout slice brings
  the active +50 continuation to +23 broad points by adding Rust/C
  compile-time layout mirrors for x86 descriptor pointers, `tss64`,
  `i387_fxsave_struct`, YMM high halves, LWP save areas, bound-register state,
  `xsave_hdr_struct`, and packed/aligned `xsave_struct`. This adds about +4
  strict-core foundation points in `migration.txt`; C still owns context
  switching, ptrace register access, signal-frame FPU save/restore,
  XSAVE/XRSTOR execution, architecture trap behavior, and fallback
  implementation.
- The latest +4 verified sysfs control-plane ABI-layout slice brings the
  active +50 continuation to +27 broad points by adding Rust/C compile-time
  layout mirrors for sysfs create, mkdir, symlink, lookup, unlink, and setup
  request packets. This adds about +4 strict-core foundation points in
  `migration.txt`; C still owns sysfs allocation, path formatting, IKC sends,
  busy waits, host-side object creation, show/store callbacks, release
  handling, and fallback implementation.
- The latest +3 verified sigaltstack strict-core slice moves the
  `sigaltstack()` syscall body sequencing into Rust with C fallbacks and
  equivalence coverage: old-stack copyout, new-stack copyin, validation,
  disabled-stack normalization, and thread `sigstack` mutation. This does not
  add broad dashboard points because Syscall Core is already 100%, but it moves
  `migration.txt` Syscall Core strict ownership from 63% to 66%. C still owns
  the syscall ABI wrapper, current-thread lookup, actual user-copy primitive,
  signal delivery, top-level syscall dispatch, Linux forwarding, and fallback
  implementation.
- The latest +4 verified sysfs response-body strict-core slice moves
  show/store/release response sequencing into Rust with C fallbacks and
  equivalence coverage: default ssize/error shaping, optional callback
  dispatch, response packet msg/err/arg publication, send callback dispatch,
  and output publication. This does not add broad dashboard points because the
  procfs/sysfs/xpmem/file-object row is already 100%, but it moves
  `migration.txt` procfs/sysfs/xpmem/file object strict ownership from 60% to
  64%. C still owns callback bodies, the actual `ihk_ikc_send()` primitive,
  logging, global buffer lifetime, packet-handler dispatch, allocation/free,
  sysfs path formatting, busy waits, host-side object creation, user-copy, and
  fallback implementation.
- The latest +4 verified coredump/uio ABI-layout slice brings the active +50
  continuation to +31 broad points by adding Rust/C compile-time layout
  mirrors for ELF core headers, program headers, note headers, `elf_siginfo`,
  `prstatus64_timeval`, `elf_prstatus64`, `elf_prpsinfo64`, and `iovec`.
  This adds about +4 strict-core foundation points in `migration.txt`; C still
  owns coredump note generation, architecture register capture, process-memory
  dumping, user-vector walking, copy paths, and fallback implementation.
- The latest +3 verified sysfs packet-dispatch strict-core slice moves
  show/store/release request dispatch into Rust with C fallbacks and
  equivalence coverage: request-kind classification, typed callback selection,
  show/store/release callback dispatch, store-size publication from the
  incoming packet error field, and unknown-message classification. This does
  not add broad dashboard points because the procfs/sysfs/xpmem/file-object
  row is already 100%, but it moves `migration.txt` procfs/sysfs/xpmem/file
  object strict ownership from 64% to 67%. C still owns the public IKC handler
  wrapper, unknown-message logging, callback bodies, raw IKC send behavior,
  global buffer lifetime, allocation/free, sysfs path formatting, busy waits,
  host-side object creation, user-copy, and fallback implementation.
- The latest +5 verified x86 CPU-local/sysfs/profile ABI-layout slice brings
  the active +50 continuation to +36 broad points by adding Rust/C
  compile-time layout mirrors for the x86 CPU-local page, x86 kernel context,
  TLS `user_desc`, sysfs operation callbacks/handle/bitmap parameters,
  `itimerval`, and `profile_event`. This adds about +5 strict-core foundation
  points in `migration.txt`; C still owns CPU-local stack switching, GDT/TSS
  mutation, TLS setup, sysfs callback execution, profile accumulation, timer
  delivery, copy paths, and fallback implementation.
- The previous +13 verified XPMEM/SysV shm/memobj ABI-layout slice brought the
  active +50 continuation to +49 broad points by adding Rust/C compile-time
  layout mirrors for low-level `ihk_rwlock`, `kref`, rbtree augmentation
  callbacks, ftrace branch-data records, `memobj_ops`, `memobj`, SysV shm
  limit/info and lock-user state, and the XPMEM ID/hash/thread-group/segment/
  access-permit/partition/permission/attachment object graph. This closes the
  currently scoped x86_64/Rocky ABI/layout foundation row, but C still owns
  XPMEM attach/detach, SysV shm lifetime, memobj refcounting, page I/O,
  ftrace accounting, rbtree mutation, locking primitives, allocation/free,
  user-copy, object lifecycle side effects, and fallback implementation.
- The latest +1 verified host-core DMA request callback slice completes the
  active +50 continuation by routing `ihk_dma_request()` through Rust-owned
  channel/ops validation, request callback presence handling, callback
  invocation, and no-callback `-EINVAL` shaping. C keeps the exported ABI
  wrapper, C fallback, and DMA provider callback body.
- The latest +1 strict-core syscall slice routes `waitid()` SIGCHLD siginfo
  construction and copyout callback sequencing through Rust helpers with C
  fallbacks. C still owns `do_wait()` scanning/sleeping, wait locks, status and
  rusage production, the actual user-copy primitive, scheduler behavior, and
  fallback implementation.
- The latest +2 strict-core syscall slice routes `wait4()` wrapper sequencing
  through Rust helpers with C fallbacks. Rust owns option validation, zeroed
  rusage preparation, do-wait callback invocation, status/rusage copyout
  gating, copyout callback dispatch, and return shaping; C still owns
  `do_wait()` internals, wait locks, the actual user-copy primitive, scheduler
  behavior, and fallback implementation.
- The latest +2 strict-core syscall slice routes `waitid()` wrapper sequencing
  through Rust helpers with C fallbacks. Rust owns idtype/options validation,
  zeroed rusage preparation, do-wait callback invocation, negative-result
  propagation, siginfo copyout dispatch, and return shaping; C still owns
  `do_wait()` internals, wait locks, the actual user-copy primitive, scheduler
  behavior, and fallback implementation.
- The latest +1 strict-core syscall slice routes `wait_continued()` body
  sequencing through Rust helpers with C fallbacks. Rust owns continued-status
  publication, reap-target selection, continued-signal reap callback dispatch,
  WNOWAIT preservation through the reap helper, and pid/tid return selection; C
  still owns wait list scans, wait locks, caller-side duplicate reap behavior,
  scheduler behavior, and fallback implementation.
- IHK open/release/close/init/exit/minor-registration, register-device cleanup,
  destroy-all-OS candidate/restore, stray-kmsg trim, event-list cleanup,
  destroy callback, notifier policy decisions, and open refcount mutation
  route through Rust helpers; treat these as established boundary context while
  the remaining IHK mutation bodies are still active scope.

Latest documented validation passed:

- `rustfmt kernel/rust/abi.rs`.
- `bash -n kernel/rust/tests/run_equivalence.sh`.
- `git diff --check -- kernel/rust/abi.rs kernel/rust/abi_checks.c`.
- Rust-enabled `cmake --build /tmp/mckernel-rocky-rust --target mckernel.img -j2`.
- C-fallback `cmake --build /tmp/mckernel-rocky-c-fallback --target mckernel.img -j2`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `object_helpers ok digest=5aa2610a74119a37`.
- `python3 -m py_compile scripts/rust-ownership-report.py`.
- `scripts/rust-ownership-report.py --check-dashboard overview.txt --check-dashboard overview2.txt --top 5`.
- `git diff --check`.
- `rustfmt kernel/rust/sched_helpers.rs`.
- `rustfmt kernel/rust/x86_memory_helpers.rs`.
- `rustfmt kernel/rust/process_helpers.rs`.
- `rustfmt ihk/linux/driver/smp/rust/smp_driver_helpers.rs`.
- `rustfmt kernel/rust/page_alloc.rs`.
- `rustfmt kernel/rust/syscall_policy.rs`.
- `rustfmt kernel/rust/abi.rs kernel/rust/numparse.rs`.
- `rustfmt kernel/rust/abi.rs kernel/rust/cls_helpers.rs`.
- `rustfmt kernel/rust/mem_helpers.rs kernel/rust/numparse.rs`.
- `rustfmt kernel/rust/numparse.rs`.
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
  `page_helpers ok digest=83a48b282c82457c`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=cf493b9170405954`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=91790b3aa3a68a22`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_helpers ok digest=8487e6bc559e457d`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=1e4506b505343675`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=c7e535b154b79d5e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `ihk_module_helpers ok map=0000000000000018 bits=0000000000000007/0000000000000000`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=6058b8fa4f7180c7`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=78fdc3d33065184f`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=c8c7596d6bc6cb66`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=df124e68726bad52`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=010895ac2df2169d`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `process_helpers ok digest=46e57fd40b55a03e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `syscall_policy_helpers ok digest=e6e8d5fc8faaf78a`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `sched_helpers ok digest=61cc5097489f9e38`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `syscall_policy_helpers ok digest=5bc42cf54d03b151`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc ok digest=bc5add72ff7bd6de`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=b1a9ce41d6284016`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=39dcb1d0c6c1e89e`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `x86_memory_helpers ok digest=0db20cb0350e799f`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=953c73f87339c534`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=d8ba50a90955fad2`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `page_alloc_bitmap ok digest=8556bdeaa7090fa7`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `printf_decimal ok digest=31ce3c0f3ecf93c1`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `cls_helpers ok digest=3020b4b56921f7dc`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `kmalloc_helpers ok digest=54cdbef90d9c7f07`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `printf_decimal ok digest=9b42843c73ef2870`.
- `kernel/rust/tests/run_equivalence.sh` passed, including
  `printf_decimal ok digest=ba6e3675fed38849`.
- `cmake --build /tmp/mckernel-rocky-c-fallback --target mckernel.img -j2`.
- `cmake --build /tmp/mckernel-rocky-rust --target mckernel.img -j2`
  passed with the existing jobserver warning.
- `python3 -m py_compile scripts/rust-ownership-report.py`.
- `scripts/rust-ownership-report.py --check-dashboard overview.txt --check-dashboard overview2.txt --top 25`.
- QEMU setup now provides `qemu-system-x86_64` through the Rocky `qemu-kvm`
  binary and libvirt is active, but `/dev/kvm` is not exposed and no
  system-QEMU boot harness exists yet.
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

- The requested +135 aggregate-point campaign, the follow-up +35 continuation,
  the prior +50 continuation, and the active +50 continuation are complete.
  Strict-core movement for the latest continuation is about +60 points, and
  the full Rust port is not
  complete. Continue toward 100% by targeting
  high-debt McKernel-owned rows first: allocator zeroed-list policy before
  mutation, syscall ptrace handler body slices, scheduler/futex
  wait/wake internals after runtime probes, additional x86 page-table
  map/remove/free preflight decisions, IHK/host-module owned mutation
  preflights and then covered mutation bodies, IHK atomic refcount publication,
  memory registration, IKC exchange, sysfs object creation/module lifecycle, and
  remaining process VM range erase/removal and lifetime bodies only with direct
  coverage.
- Keep the high-risk orchestration in C until runtime coverage exists:
  process lifetime mutation, child-list mutation, rusage aggregation, ptrace
  detach mutation, scheduling decisions, wakeups, timers, memory registration,
  IKC exchange, sysfs object creation, page-table mutation, page I/O,
  user-copy, and broad lock/list ownership.
- Continue object/file/procfs/sysfs conversion only where runtime coverage can
  exercise the path: file-backed mmap, `/proc/PID/mem`, sysfs create/show/store,
  device PFN mappings, and hugetlbfs-backed mappings.
