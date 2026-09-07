# McKernel Rust Migration Agent Notes

Updated: 2026-06-02

## Mission

This repository is migrating McKernel from the traditional CentOS-based
deployment to an exact Rocky Linux 10.2-derived production control-plane kernel
while porting McKernel-owned implementation logic from C to Rust. The frozen
Rocky Linux 8.10 build and runtime evidence remains the historical R0
compatibility oracle, not the native-host-module production target. The active
target is smp-x86 / x86_64. Arm64 is deferred until the x86_64 path is stable.

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
  core Rust ownership is 100% for the scoped sequencing table; C may remain for ABI shims, fallback
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
- Post-+50 strict-core movement is now about +398 strict-core points after
  the broad dashboard reached its current cap. The latest verified movement
  routes Page allocator low-level registration and dispatch through Rust:
  `pa_ops` storage, tracking-init and early-invalidate callback ordering,
  allocator ops publication, aligned/default allocation dispatch, free dispatch,
  early-allocation fallback selection, and exported `___ihk_mc_*()` body
  publication. Recent verified movement also routes top-level host IKC public
  handler/wrapper sequencing through Rust: syscall packet
  cast/response-channel/current-thread dispatch, dummy packet release dispatch,
  and public IKC2Linux/IKC2McKernel init panic-on-error wrapper sequencing.
  Recent verified movement also routes the public bitmap
  `ihk_pagealloc_*()` wrapper layer through Rust: exported init failure
  logging, default init, destroy free-callback dispatch,
  alloc/reserve/free/count/query dispatch, double-free error routing, and
  zero-free begin/done logging. Recent verified movement also routes
  `set_mempolicy()` and `mbind()` body sequencing through Rust: nodemask-bit
  validation, clamp-warning dispatch, mode normalization, default-policy
  empty-mask validation, copyin fault shaping, process NUMA-mask reset,
  preferred-without-mask publication, missing-mask rejection,
  node-bound validation, valid-mask overlap detection, process-mask clearing,
  interleave-state publication, straight-map/FUGAKU gates, mbind mode/flag
  validation, address-range validation, memory-range lock/lookup ordering,
  range-policy clear/allocate/rb-clear/insert sequencing, and range-policy
  mask/policy/interleave publication. Earlier `get_mempolicy()` movement
  already covered validation, `MPOL_F_NODE`/`MPOL_F_MEMS_ALLOWED`, address
  range locking/lookup, range-policy search and unlock ordering, policy selection
  plus mode copyout, and range/process nodemask copyout. The previous verified
  movement routes `ihk_mc_pt_lookup_fault_pte()` and `lookup_node()` sequencing
  through Rust: initial PTE lookup, missing-PTE fault dispatch, retry lookup,
  recovered-PTE logging, lookup-node fault dispatch/error return,
  address-space/page-table extraction, post-fault PTE lookup, absent-PTE
  `-ENOENT` shaping, PTE physical-address extraction, and physical-to-NUMA-node
  return shaping. The earlier verified movement routes
  `query_free_mem_interrupt_handler()` sequencing through Rust:
  NUMA-node iteration, per-node free-page callback dispatch, total
  accumulation/logging, optional FUGAKU panic dispatch, `memdebug` lookup,
  kmalloc/pagealloc memcheck dispatch, page-hash count/log callback dispatch,
  and optional ATTACHED_MIC sbox scratch publication. The earlier verified
  movement routes allocator wrapper selection and free handoff through Rust:
  `mckernel_allocate_aligned_pages_node()` invalid-size/default-idle/
  current-VM/range-policy/process-policy selection, current-node publication,
  and `mckernel_free_pages()` pending-free versus allocator-free sequencing.
  Earlier verified movement routes `init_process_stack()` primary
  execution-body sequencing through Rust: stack sizing, max/min limit
  selection, AP-user policy, aligned allocation, stack zeroing, VM stack range
  creation, page-table set-range callback dispatch, auxv/argv/env stack
  layout, `saved_auxv` publication, user stack pointer/context publication,
  and VM stack bound publication. The earlier verified movement routes host
  args/envs stack-prep sequencing
  through Rust: arg/env page-count and range placement, argenv page
  allocation/physical publication, argenv memory-range creation, remote
  args/envs map/copy/unmap/TLB sequencing, local args/envs length publication,
  saved_cmdline free/alloc/copy publication, argv/env pointer fixup, vDSO
  map/clear, rprocess/rpgtable publication, and init_process_stack callback
  dispatch/error shaping. The previous verified
  movement routes host prepare-ranges ELF section-loop sequencing,
  interpreter/aout relocation, section page-span/range calculation,
  memory-range creation, user-page allocation, page-table mapping
  dispatch/failure cleanup, remote-PA and text/data/map/brk publication,
  entry/auxv/context adjustment, and data-too-large return shaping through
  Rust. The previous verified movement routes host `process_msg_prepare_process()` freeze gates, program-descriptor
  map/span validation, descriptor clone allocation/copy, main-thread creation,
  process/thread/VM metadata publication, NUMA policy publication,
  prepare-ranges dispatch, success cleanup, unmap, TLB flush, destroy, and
  error shaping through Rust. The earlier verified movement
  routes Process/VM `free_process_memory_range()` page-table free/clear
  locking, memobj ref/unref ordering, TOFU removal callback dispatch,
  final detach/straight cleanup, error-log selection, and return shaping
  through Rust. The earlier verified movement
  routes Process/VM remove-process-memory-range straight-map conversion,
  range iteration, split, XPMEM removal, and free-dispatch sequencing through
  Rust. The earlier verified movement routed Process/VM do-page-fault
  outer-body, page-fault retry/page-I/O, and populate-loop sequencing through
  Rust. Earlier verified movement routed Process/VM range lookup,
  next/previous iteration, extend-up,
  change-protection, and `access_ok()` body sequencing through Rust. The
  earlier verified movement routed XPMEM clear-PTE and process-memory-range
  removal sequencing through Rust. Earlier verified movement routed XPMEM
  detach and munmap sequencing through Rust. Earlier verified movement
  routes XPMEM access-permit release lifecycle sequencing through Rust:
  destroy-start gating, attachment-list drain, attachment ref/detach/deref
  callback ordering, final destroyed-state publication, AP hash-list unlink,
  segment AP-list unlink, segment and segment-thread-group deref callback
  ordering, AP destroyable dispatch, and already-destroying early return
  behavior. The earlier verified movement
  routes XPMEM thread-group segment-list drain sequencing through Rust:
  writer-lock acquisition, empty-list detection, first-segment selection from
  the list head, segment refcount callback ordering, unlock-before-removal,
  per-segment removal callback dispatch, deref callback ordering, relock loop
  sequencing, final unlock, and empty-list return behavior. The earlier
  verified movement routes XPMEM segment-removal lifecycle sequencing through
  Rust: destroy-start gating, segment destroy-flag publication, PTE-clear
  callback ordering, final destroyed-state publication, segment-list
  lock/unlock ordering, list unlink, destroyable/refdrop callback dispatch,
  and already-destroying early return behavior. The earlier verified movement
  routes XPMEM `close()`/`dup()`/flush lifecycle sequencing through Rust:
  duplicate data clearing and open-count increment, close open-count decrement,
  flush/partition-exit decisions, flush target-group lookup, hash-list unlink,
  destroy-flag publication, access-permit/segment release callback ordering,
  final destroyed-state publication, and destroy callback dispatch. The
  earlier verified movement routes XPMEM `open()`/`openat()` body sequencing
  through Rust: partition-init gate, Linux fd-forward result handling,
  `__xpmem_open()` callback ordering, mckfd allocation/null handling, mckfd
  zeroing and field publication, locked list-head insertion, unlock ordering,
  open-count increment, and debug-log event selection. The still earlier
  verified movement routed live mckfd syscall dispatch through Rust: `read()`,
  `ioctl()`, `fcntl()`, and `close()` locked lookup, callback-vs-forward
  selection, optional TOFU ioctl/close cleanup gates, close unlink mutation,
  close-callback dispatch, mckfd free-callback dispatch, and Linux-forward
  fallback sequencing. The still earlier verified
  movement routed a ten-slice
  syscall wrapper batch through Rust: `times()`,
  `setpgid()`, `setrlimit()`, `getrlimit()`, `prlimit64()`, `sysinfo()`,
  `get_cpu_id()`, `mlockall()`, `munlockall()`, and `getcpu()` sequencing for
  CPU-time accounting/copyout, pgid normalization/find/forward/mutation,
  prlimit argument routing, sysinfo fill/copyout, CPU/NUMA id copyout,
  mlockall policy/logging, and missing-callback error shaping. The previous
  movement routed signal and credential syscall wrapper bodies through Rust:
  `kill()`, `tgkill()`, `tkill()`, `setresuid()`, `setreuid()`, `setuid()`,
  `setfsuid()`, `setresgid()`, `setregid()`, `setgid()`, and `setfsgid()`
  validation, siginfo shaping, do-kill callback dispatch, Linux-forward
  dispatch, credential-refresh dispatch, setfsid syscall dispatch, and return
  shaping. The previous movement routed top-level `ptrace()` request/callback
  body dispatch through Rust: `PTRACE_TRACEME`, kill/continue/singlestep/syscall
  wake requests, register/fpreg/regset get/set requests, user/text peek/poke
  requests including data aliases, set-options, attach/detach,
  siginfo/eventmsg, arch fallback, and unsupported/missing-callback error
  shaping. The previous movement routed `ptrace_detach_thread()` main-body
  sequencing through Rust:
  main-thread detach gating, zombie finalization selection, tracer child-list
  detach, ptraced reparenting, report-list detach/reattach, ptrace
  cleanup/free dispatch, single-step clear, exit-signal dispatch,
  forwarded-signal siginfo construction, `do_kill()` callback sequencing,
  wake/release dispatch, and final process finalization dispatch. The previous
  syscall movement routed the outer process/thread wait scan under `do_wait()`
  through Rust:
  parent children-lock callback ordering, children-list traversal, pid/pgid
  matching, `empty` publication, zombie/candidate dispatch, ptraced-children
  empty-scan traversal, report-thread list traversal, report-thread candidate
  dispatch, regular thread-list empty-scan traversal, and offset-based C
  fallback parity. The previous syscall movement routed the process-zombie/
  reparent branch under `do_wait()` through Rust: zombie status publication,
  host-wait skip/request/log selection, parent rusage aggregation, rusage
  result fill, parent child-list detach, PID-1 reparent/list attach, child
  main-thread ptrace-detach gate, parent and child lock/unlock callback
  ordering, no-reparent unlock/detach ordering, and process release callback
  dispatch. The previous syscall movement routed wait-scan candidate
  sequencing under `do_wait()` through Rust:
  report-thread exit/no-wait/detach/release decisions, nonptraced and ptraced
  stop candidates, continued candidates, ptraced-stop miss return preservation,
  process TID rewrite, and lock/release callback ordering. The previous
  syscall movement routed top-level `do_wait()` wait-loop sequencing through
  Rust: waitqueue init/prepare/finish callback ordering, process/thread scan
  dispatch gates, no-child and `WNOHANG` result shaping, pending-signal
  interrupt return, schedule callback handoff, wake/rescan behavior, and wait
  log callback ordering. The previous scheduler movement routed `do_migrate()` scheduler
  migration-completion sequencing through Rust: migration queue traversal,
  request detach/ack gates, affinity target selection, runqueue detach/add
  with length mutation, thread CPU update, same-VM sibling scan,
  address-space CPU-set lock/update, target reschedule flag publication,
  interrupt/vector callback selection, waitqueue wake callback dispatch, lock
  ordering, and return shaping. The previous scheduler
  movement routed `sched_request_migrate()` body sequencing through Rust:
  request thread publication, target migration-queue lock callback ordering,
  waitqueue init/prepare/finish callback sequencing, migration request list
  insertion, target runqueue flag/status mutation, remote interrupt
  vector/callback selection, log callback dispatch, scheduler callback
  handoff, and validation/error shaping. The previous dump movement routed
  memory dump user-page process-hash traversal, VM/address-space/page-table
  pointer loading, null skip gates, visitor argument shaping, page-table
  visitor callback dispatch, and dispatch-count/error shaping through Rust.
  The previous dump bitmap movement routed memory dump page-set
  completion, physical-address membership checks, variable-length dump bitmap
  range clearing, user-PTE dump bitmap marking, free-chunk dump bitmap marking,
  and top-level last-CPU dump query sequencing through Rust. The previous
  allocator movement routed NUMA topology and
  allocation dispatch through Rust: allocation-attempt OOM flag
  initialization, NUMA-id bounds validation, rusage OOM callback dispatch,
  NUMA allocation callback dispatch, distance-vector bounds/null checks,
  distance-id lookup, CPU-local readiness checks, current-NUMA callback
  dispatch, and distance-ordered node pointer selection. The earlier lifecycle
  slice moved `numa_distances_init()` node-distance allocation,
  distance-matrix fill, distance/id sorting, node publication,
  allocation-failure logging, and ordered log callback sequencing. The prior
  lifecycle slice moved
  `ihk_mc_set_page_allocator()` tracking-init/early-allocator invalidation/
  `pa_ops` publication plus top-level `mem_init()` monitor, rusage, NUMA,
  allocator registration, page-fault handler publication, query-free interrupt
  registration, page-hash init, virtual-map init, demand-paging flag/log
  publication, and NUMA-distance init ordering. This latest remove-range
  movement does not add broad dashboard percentage because the Process/VM row
  is already capped at 100%.
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
  Libvirt is active, and `/dev/kvm` may be visible in some command contexts,
  but QEMU boot validation should still start with TCG/software emulation
  unless KVM initialization is explicitly verified for that run. Existing
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
| x86_64 memory management | 100 | Classification, NUMA/page queries, splitability, page-attribute conversion, PTE value shaping, page-size PTE validation/value selection, early allocator arithmetic/exhaustion checks, page-table index calculation, walk-bound calculation, normal/safe page-table walk iteration, callback result folding, normal/safe visit-PTE leaf/level/root body sequencing and top-level visit-range dispatch, optional physical-address skip policy, virtual-to-physical per-level miss/walk/hit decisions and physical/size result shaping, split-large-page preparation/entry arithmetic, split-large-page source classification, child-map physical derivation, page-table publish entry shaping, source-unmap gate selection, PTE direct-store helpers, atomic child-table publication helpers, PTE clear-exchange helpers, attribute-apply mutation helpers, page-clear alignment/target selection, page-table visit/direct-walk decision policy, clear/free-range validation and large-entry action selection, clear-range old-PTE phys/fileoff/dirty classification plus flush/free/unmap action selection, clear/set range top-level validation/allocation/free/walk/flush orchestration, change-attribute leaf/large/walk action selection, set-range leaf/direct-large/allocate/busy/walk action selection, set-range mapped physical/PTE value shaping for 4 KiB/2 MiB/1 GiB entries, set-range conflict/alloc-failure/map-store-RSS/walk-failure side-effect sequencing, set-range leaf/level body orchestration, lookup-pte default size/level hit/walk/miss/shape decisions, move-PTE fileoff preflight/destination shaping/PTE phys-attr splitting, page-table destroy descend/skip policy, destroy child-table physical extraction, recursive page-table destroy/free-callback orchestration below the root, page-table root create/destroy-root lifecycle orchestration, page-table prepare-map first-level allocation/publish and last-level set-page callback orchestration, exported set-PTE body sequencing/log/panic/store orchestration, page refcount/hash lifecycle helpers, `page_map()` count increments, locked `page_unmap()` count/list deletion and lock orchestration, locked `phys_to_page()` lookup orchestration, locked `phys_to_page_insert_hash()` lookup/allocation-callback/insert orchestration, locked page-hash count-all traversal, phys-to-page hash traversal, hash insertion initialization, page-hash bucket init/count, VM range validation, memory-policy validation, selected pager/object sizing helpers, process-VM verification/page-fault/copy loop sequencing, mapped versus direct physical-copy selection, byte-copy sequencing, scalar user get/set wrappers, user string length/copy wrappers, dump-page completion/address-check/bitmap marking/query sequencing, and dump user-page process-hash traversal/page-table visitor dispatch are Rust-owned; page-table allocation/free primitives, page-fault primitive behavior, `phys_to_virt()`/`virt_to_phys()` primitive behavior, map/unmap primitive bodies, callback execution, broader page frees/RSS accounting, mapping/free rollback orchestration, page-hash spinlock/allocation primitives and logging, TLB-sensitive primitive behavior, current-thread/resource-set lookup, and C fallback scaffolding remain C. |
| Page allocator | 100 | Rbtree helper cluster, bitmap-backed no-lock allocator internals, bitmap public locked-wrapper orchestration for alloc/reserve/free/count/query/zero-free, `__ihk_pagealloc_init()` layout/allocation-callback/descriptor-init/lock-callback/tail-reservation orchestration, init layout/end/count calculation, descriptor zeroing and descriptor field initialization, tail-map reservation, destroy-page count and descriptor destroy/free-callback orchestration, exported add-free log/error/return sequencing, NUMA free/alloc helpers, public zero-free wrapper dispatch, NUMA zero-free dispatcher/all-node traversal, exported `ihk_numa_alloc_pages()` top-level allocation body sequencing, main `ihk_numa_alloc_pages()` cache-first/source-selection/fallback-to-NUMA orchestration, exported `ihk_numa_free_pages()` top-level and main CPU-cache/direct/deferred free orchestration plus post-action completion sequencing, `numa_init()` node discovery/node-field publication/memory-chunk ingestion/early-heap adjustment/free-page-or-pagealloc dispatch/rusage accounting/final-node logging sequencing, NUMA allocation-attempt OOM/bounds/callback dispatch, distance-id lookup and distance-ordered NUMA node selection, main NUMA allocation lock-callback orchestration, direct free-to-tree lock-callback orchestration, deferred-free enqueue/zero-request orchestration, free-path policy, zeroing-worker atomic increment, CPU-local cache action classification, CPU-local cache rb-tree allocation/free helper entry points, CPU-local cache alloc/free fast-path orchestration with interrupt callback ordering and result classification, CPU-local storage initialization, CPU-local variable selection, normal preempt counter updates, kmalloc chunk header initialization, sorted kmalloc free-list insertion, adjacent free-chunk consolidation, low-level `___kmalloc()` allocation body sequencing, low-level `___kfree()` current/remote free body sequencing, kmalloc remote free-list move/consolidation sequencing, public `_kmalloc()`/`_kfree()` memdebug tracking wrapper sequencing, public `_ihk_mc_alloc_aligned_pages_node()`/`_ihk_mc_free_pages()` pagealloc memdebug tracking wrapper sequencing, pagealloc/kmalloc tracking hash initialization, pagealloc/kmalloc memcheck leak-scan traversal, runcount mutation, leak-log callback sequencing, `ihk_mc_set_page_allocator()` tracking-init/early-invalidate/`pa_ops` publication, top-level `mem_init()` allocator/memory lifecycle sequencing, NUMA-distance allocation/fill/sort/log sequencing, `query_free_mem_interrupt_handler()` node iteration/total accumulation/logging/memdebug/page-hash/sbox sequencing, and Linux zero-request action selection, deferred-zero IKC packet field shaping, Linux zero-request preparation including current/idle/nohost/worker/pid checks plus packet fill and worker increment, and deferred-zero send/log callback sequencing are Rust-owned; logging/panic callbacks, pa-ops implementation callback bodies, actual allocation/free primitive side effects below the published ops callbacks, and MCS/interrupt primitives, broader allocator lifetime, IKC channel lookup, current-thread/channel lookup, actual IKC send side effects, deferred-zero worker timing, and FUGAKU debug preempt path remain C. |
| Process/VM management | 100 | Wait/clone/ptrace/VM policy, fork VM/thread metadata copy, address-space release and PID detach mutation, range-cache lookup relation plus range-cache replace/store mutation for join, free, and lookup paths, full VM range lookup traversal/cache publication, next/previous range iteration bodies, post-bounds `add_process_memory_range()` orchestration including VM range object initialization, mapping-action selection, insert/update failure cleanup, returned-range publication, and VM range-tree insertion traversal/link/color mutation, VM range end/flag commit mutation for extend-up and protection-change paths, stack-growth range-start alignment/commit mutation for the page-fault path, page-fault PTE lookup retry/log sequencing and `lookup_node()` fault/PTE/phys-to-node return sequencing, remove-range split/free preflight, remove-process-memory-range straight-map conversion/range-iteration/split/XPMEM/free dispatch sequencing, `free_process_memory_range()` page-table free/clear lock/memobj/finalize orchestration, split-range high-half field shaping and low-half end commit, join-range adjacency/object-offset validation and surviving-end commit, CPU-set fallback, mckfd decisions plus push/pop-head mutation, TID-table scan/index decisions, TID slot release/replace writes, sigpending list pop/unlink, sigcommon release-body sequencing, release_thread ref/profile/procfs/destroy/VM-release sequencing, release_process_vm ref/mckfd/free-callback/TLB/free-ranges/detach/policy-drain/final-free sequencing, process/thread list add/detach helpers, terminate child cleanup list unlink/reparent mutation helpers, thread report-list attach/detach mutation helpers, ptrace main-thread attach/detach reparent helpers, ptrace detach/wakeup state and pending-signal cleanup helpers, wait signal-flag and exit-status reap mutation helpers, terminate/wait report-thread release cleanup helpers, do-wait child/report-thread traversal and empty-scan sequencing, optional ptrace/fp cleanup gates, and lifecycle/refcount predicates are Rust-owned; VM range allocation/free callbacks, memobj refcounting, TOFU split/merge hooks, split/XPMEM primitive callbacks, page-fault range-resolution primitive behavior, page-table lookup/allocation/mapping side effects, page-table attribute mutation/free/clear, other child-list/lifetime orchestration, rusage aggregation, broad process lifetime mutation, signal forwarding, atomic refcount primitive bodies, lock/free primitive bodies, and remaining wait primitive behavior remain C. |
| Syscall core | 100 | SysV shm, prlimit, scheduler priority/policy plus scheduler syscall body sequencing, syscall/range validation, credential-refresh forwarding gates, direct ID and uid/gid leaf bodies, kill/tkill/tgkill siginfo shaping and do-kill callback sequencing, forwarded uid/gid setter Linux-forward/credential-refresh sequencing, getresuid/getresgid ordered field-read and user-copy callback sequencing, mckfd lookup/dispatch and close sequencing, memory-policy syscalls including `get_mempolicy()`, `set_mempolicy()`, and `mbind()` body sequencing, mmap/brk/mincore/mprotect policy, signal/time syscall body sequencing, ptrace/process-vm helpers, wait4/waitid/do-wait sequencing, execveat/clone/futex policy helpers, bounded wait/ptrace/termination/signal list rewiring, ptrace request/event/register/regset sequencing, getrusage body sequencing, process-exit status/siginfo classification, terminate cleanup/reparent action classification, clone spawn/TID/TLS/reparent result shaping, and ptrace detach signal-forward gates are Rust-owned; top-level syscall dispatch, actual user-copy primitive, Linux forwarding primitive bodies, locks, allocation/free primitives, architecture fp/register/regset primitives, actual process-memory read/patch primitives, signal delivery primitive behavior, rusage aggregation/traversal, CPU interrupt delivery, ptrace lookup/orchestration, scheduler migration side-effect bodies, broader scheduler/time primitive bodies, waitqueue/schedule/signal primitive behavior, and other primitive C callback implementations remain C. |
| Scheduler/timers/wait/futex | 100 | Waitqueue init/entry/list core, wake scheduling predicate, bounded runqueue/migration list rewiring plus runqueue length updates, scheduler set/get-param, set/get-scheduler, RR-interval, set-affinity, and get-affinity syscall validation/target-selection/permission-check/user-copy sequencing, scheduler migration-request body sequencing for waitq setup, request queue publication, target runqueue flag/status mutation, remote interrupt decision, log callback dispatch, schedule handoff, and waitq finish, scheduler migration-completion body sequencing for migration queue traversal, request detach/ack gates, affinity target selection, runqueue detach/add with length mutation, thread CPU update, same-VM sibling scan, address-space CPU-set update, target reschedule flag publication, interrupt dispatch, waitqueue wake, and lock ordering, timer spin-sleep/runqueue/remaining-time arithmetic, `init_timers()` list/lock initialization sequencing, `schedule_timeout()` spin-wake/runqueue/schedule-callback/spin-loop/timeout-expiry sequencing, `wake_timers_loop()` timer tick/decrement/detach/log/wakeup sequencing, `set_timer()` runqueue scan and LAPIC enable/disable decision sequencing, local interval-timer current-value subtraction, elapsed reset, enabled-state publication, and set-timer callback dispatch, futex hash-table allocation-callback/pointer-publication/table-initialization orchestration, futex hash-bucket selection with hash callback, top-level futex command dispatch/private/realtime decode, clock-realtime rejection, wait/wake/requeue/wake-op callback selection, invalid-command callback routing, futex hash-bucket table lock/list initialization, futex key matching/key preparation plus wake/requeue decision policy, futex double hash-bucket lock/unlock ordering, futex wake-list scan/key-match/bitset/limit orchestration, futex wake target orchestration, futex requeue source-list scan/key-match/wake-vs-requeue/drop-count orchestration, futex requeue key-reference callback and key-copy publication, futex wait-setup key-init/get-key/queue-lock/get-value/mismatch cleanup orchestration, futex wake-list detach and lock-pointer clear, futex requeue list move and lock-pointer publication, futex waiter plist initialization/insertion, futex wait-queue bitset/requeue/UTI initialization, key-region zeroing, hash-bucket lock-pointer publication, waiter metadata publication, self-unqueue list detach, wait-side bitset validation, wait scheduling action classification, wait-state status/spin-sleep mutation, futex post-wait success/timeout/interrupt/retry classification, futex wake target classification, Linux response-channel fallback selection, futex wake IKC packet field publication, syscall-offload scheduling decisions, and scheduler/futex/signal/timer policy helpers are Rust-owned; futex allocation/hash primitive callbacks, actual spinlock primitives, rdtsc/pause primitive behavior, LAPIC timer primitive behavior, waitqueue wake primitive behavior, IKC send and scheduler wake primitives, futex key lookup internals, key-reference implementation/lifetime, user-value load, IPIs, context switching, address translation, migration primitive callbacks, race retry, user-value comparison, `schedule()` primitive behavior, and remaining futex queue/requeue/wait side effects remain C. |
| procfs/sysfs/xpmem/file objects | 100 | XPMEM and file/dev/procfs/sysfs/pager decision-helper surface is Rust-owned through multiple batches, including live mckfd lookup/dispatch, XPMEM open/close/dup/flush lifecycle sequencing, XPMEM release/remove wrapper sequencing, XPMEM AP hash-bucket release-drain sequencing, XPMEM thread-group destroy dispatch, XPMEM access-permit release lifecycle sequencing, XPMEM segment-removal lifecycle sequencing, XPMEM thread-group segment-list drain sequencing, procfs cmdline/comm helpers, sysfs show/store/release response-body sequencing, sysfs request packet dispatch, procfs buffer allocation/init/physical-publication sequencing, `/proc/PID/mem` page-fault/translation/memory-gate/copy-loop sequencing, root `mckernel`/`stat` output, per-process `auxv`/`cmdline`/`comm` output, `/proc/PID/pagemap` value-loop sequencing, `/proc/PID/maps` line output, `/proc/PID/status` body output, and per-PID `stat` body output; this is not full subsystem ownership because allocation/free primitives outside covered mckfd allocation/free-callback dispatch, refcount mutation, lock/list primitive behavior, remap/page-table mutation, page I/O, remaining procfs request mapping/lookup/lock primitives, raw sysfs/procfs IKC send behavior, public IKC handler wrapping/logging, and user-copy remain C. |
| host/IKC/mcctrl/IHK modules | 100 | Rust helper linkage is active for `ihk`, `ihk-smp-x86_64`, and `mcctrl`; many host driver, OS/device exclusive-open refcount compare-exchange mutation, generic locked list add/delete mutation, generic list-membership traversal, generic next-entry cursor traversal for notifier/event/aux-call paths, kmsg buffer/container lifecycle mutation, kmsg container atomic count set/read/inc/dec/dec-return, reverse kmsg list lookup traversal, DMA request callback dispatch, load-file dispatch/read-loop policy, shutdown status policy, SMP, sysfs, IKC policy, and mcctrl helpers are Rust-owned, including deferred-zero worker list pop, payload clear, zeroed-list publish, atomic counter updates, top-level host SCD packet dispatcher classification/release sequencing, host prepare-process body sequencing, host prepare-ranges section/range/page-table sequencing, host args/envs stack-prep sequencing, init-stack primary execution-body sequencing, host IKC2Linux/IKC2McKernel initialization body sequencing, top-level syscall packet-handler wrapper sequencing, dummy packet-handler release sequencing, and public host IKC init panic-on-error wrapper sequencing; device allocation, memory registration, file I/O, waits/callbacks beyond the bounded dispatchers, broader IKC exchange mutation, broad allocation/lifetime ownership, and kernel object lifecycle mutation remain pending. |
| User tools | 83 | `mcstat`, `mcexec`, `ihklib`, `mcinspect`, `eclair`, and crash-extension helper surfaces are substantially Rust-owned; device I/O, ioctl handling, DWARF/BFD walking, crash command orchestration, GDB process/socket orchestration, daemon/thread/event-loop mutation, dump NMI side effects, register/memory reads, and most IHK command mutation remain C. |
| Rocky runtime integration | 82 | Rust McKernel image and focused Rocky smokes have passed in prior runs; this pass did not run boot or reboot-capable validation. Wider runtime/performance coverage remains pending. |
| arm64 | 0 | Deferred until x86_64 stabilizes. |

Honest current distance: the non-arm64 functional dashboard average is 96.7%,
while the McKernel-owned core rows in this table average 100.0%. Mechanical LOC
audit is 27.9% and is not a progress score. The functional percentages track
verified Rust-owned surfaces, and they are not a claim that mutation-heavy
kernel bodies are already fully Rust. The current total distance to 100 is 40
aggregate functional points across non-arm64 dashboard rows, or 0 points
across the McKernel-owned core rows excluding build/host/user/Rocky/arm64.

## Full-Port Tracker

`full-port.txt` is the strict whole-repo x86_64/Rocky full standalone Rust
tracker. It excludes arm64, third-party/vendor/generated code, public
compatibility headers, tests, and unavoidable assembly-adjacent code.

Use `full-port.txt` for the completed scored full-port campaign. Use
`migration.txt` for strict core sequencing history, `overview.txt` for the
functional dashboard, and `rust-source-retirement.txt` for the stricter
per-file C-source retirement inventory. The current non-arm full-port scored
tracker is 100.0% complete with 0.0% left, and the verified aggregate movement
is +611.9 / +611.9 percentage points. Do not keep adding full-port percentage
after this saturation point.

Remaining work after the scored full-port closeout is source-retirement and
default-path C-dependency cleanup outside `full-port.txt`. A C file that still
contains a McKernel-owned implementation body for fallback builds should not be
marked fully retired in `rust-source-retirement.txt`; record such work as
default-path Rust ownership in `overview.txt` or as a validated note until the
C implementation body is actually removed or reclassified by the retirement
tracker's rules.

Every full-port movement must be verified. Runtime-sensitive work must use QEMU
and virtualization tooling, preferably KVM when available and verified. Do not
use host reboot paths. Stop on first validation failure and log the failing
command, environment, and short error summary in `kernel.log`.

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

Current strict x86_64 core Rust ownership is 100% for the scoped sequencing
table. This is not the standalone Rust end-state: remaining C still owns
high-risk primitive/runtime bodies such as page-table mutation primitives,
allocator lifetime primitives, syscall dispatch, raw user-copy primitive
callbacks, process lifetime primitives, page-fault primitive behavior,
scheduler wake/context behavior, futex wake/wait side effects, signal delivery,
IKC exchange, and kernel object lifecycle.

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
| Shared primitives | 100 | 100 | Complete for the scoped x86_64/Rocky shared-primitives core. Numeric parsing, `skip_atoi()` format width/precision pointer advancement, `number()` sign/prefix/width/precision/padding/output orchestration, `format_decode()` format-token parsing, `string()` `%s` output formatting, base-10 decimal digit emission, and the main `vsnprintf()` loop orchestration are Rust-owned; public ABI wrappers, `va_arg` extraction glue, and fallback scaffolding still block standalone Rust, not this strict shared-primitives row. |
| x86_64 memory management | 100 | 100 | Page-table decisions, page-table root create/destroy-root lifecycle orchestration, page-table prepare-map orchestration, exported set-PTE body sequencing, page refcount/hash lifecycle bodies, recursive child-table destruction/free-callback orchestration, full virtual-to-physical walks, page-clear traversal, lookup-PTE body orchestration, change-attribute traversal/PTE mutation, page-table setup/allocation traversal, clear-range TLB flush-address queue mutation, old-PTE memobj-flush/free/unmap/RSS side-effect sequencing, full-span child page-table teardown/free sequencing, clear-range leaf/level/root body sequencing, set-range conflict/alloc-failure/map-store-RSS/walk-failure side-effect sequencing, set-range leaf/level body orchestration, clear/set range top-level orchestration, normal/safe visit-PTE visitor body sequencing, process-VM verification/page-fault/copy loop sequencing, mapped versus direct physical-copy selection, byte-copy sequencing, scalar user get/set wrappers, user string length/copy wrappers, dump-page completion/address-check/bitmap marking/query sequencing, and dump user-page process-hash traversal/page-table visitor dispatch moved. Page-table allocation/free primitives, old-entry page lookup/refcount primitive behavior, address-translation primitive bodies, page-fault primitive behavior, broader page frees/RSS accounting, remote TLB shootdown primitive behavior, physical/free orchestration, page-hash primitives/logging, current-thread/resource-set lookup, and fallback scaffolding remain C-owned, but the scoped x86 memory sequencing row is now strict-core complete. |
| Page allocator | 100 | 100 | Complete for the scoped Page allocator sequencing row. Bitmap, NUMA, `__ihk_pagealloc_init()` orchestration, public bitmap `ihk_pagealloc_*()` wrapper sequencing for init failure logging, default init, destroy free-callback dispatch, alloc/reserve/free/count/query dispatch, double-free error routing, and zero-free begin/done logging, exported add-free log/error/return sequencing, public zero-free wrapper dispatch, exported `ihk_numa_alloc_pages()` top-level allocation body sequencing, main `ihk_numa_alloc_pages()` cache-first/source-selection/fallback-to-NUMA orchestration, exported `ihk_numa_free_pages()` CPU-cache/direct/deferred top-level body sequencing, main `ihk_numa_free_pages()` direct-versus-deferred free orchestration, free post-action completion sequencing, allocator pa-ops/early-allocation wrappers, pending-free list mutation, free-in-allocator rbtree traversal, allocation policy loops, `mckernel_allocate_aligned_pages_node()` default/idle/current-VM/range-policy/process-policy wrapper selection, top-level `mckernel_free_pages()` pending-free versus allocator-free handoff, `query_free_mem_interrupt_handler()` node iteration/total accumulation/logging/memdebug/page-hash/sbox sequencing, `numa_init()` node discovery/node-field publication/memory-chunk ingestion/early-heap adjustment/free-page-or-pagealloc dispatch/rusage accounting/final-node logging sequencing, NUMA allocation-attempt OOM/bounds/callback dispatch, distance-id lookup and distance-ordered NUMA node selection, CPU-local storage initialization, CPU-local variable selection, normal preempt counter updates, kmalloc chunk header initialization, sorted kmalloc free-list insertion, adjacent free-chunk consolidation, low-level `___kmalloc()` allocation body sequencing, low-level `___kfree()` current/remote free body sequencing, kmalloc remote free-list move/consolidation sequencing, public `_kmalloc()`/`_kfree()` memdebug tracking wrapper sequencing, public `_ihk_mc_alloc_aligned_pages_node()`/`_ihk_mc_free_pages()` pagealloc memdebug tracking wrapper sequencing, pagealloc/kmalloc tracking hash initialization, pagealloc/kmalloc memcheck leak-scan traversal, runcount mutation, leak-log callback sequencing, `ihk_mc_set_page_allocator()` tracking-init/early-invalidate/`pa_ops` publication, top-level `mem_init()` allocator/memory lifecycle sequencing, and NUMA-distance allocation/fill/sort/log sequencing moved, but pa-ops implementation callback bodies, actual allocation/free primitive side effects below the published ops callbacks, MCS/interrupt primitive bodies, IKC channel lookup/send side effects, logging/panic primitive bodies, deferred-zero worker timing, FUGAKU debug preempt behavior, and broader allocator lifetime remain C-owned. |
| Process/VM management | 100 | 100 | Complete for the scoped Process/VM sequencing row. Many lifecycle, wait, ptrace, range, list, post-bounds add-range orchestration bodies, VM range-tree insertion traversal/link/color mutation, VM range lookup traversal/cache publication, next/previous range iteration, extend-up validation/commit, change-protection attr-delta/private-file/page-table-lock/change-attr/-ENOENT/commit sequencing, `access_ok()` initial/adjacent/permission multi-range validation, do-page-fault stack-grow/lock/exiting/lookup/access/zero-object/normal-vs-XPMEM dispatch sequencing, page-fault `-ERESTART`/page-I/O retry sequencing, populate-loop preempt/page-walk/warning sequencing, page-fault PTE lookup retry/log sequencing, `lookup_node()` page-fault/PTE-present/phys-to-node return sequencing, remove-process-memory-range straight-map conversion/range-iteration/split/XPMEM/free dispatch sequencing, `free_process_memory_range()` page-table free/clear lock/memobj/finalize orchestration, release/cleanup sequencing, sigcommon release-body sequencing, TID release/replace body sequencing, release_thread ref/profile/procfs/destroy/VM-release sequencing, release_process_vm ref/mckfd/free-callback/TLB/free-ranges/detach/policy-drain/final-free sequencing, wait-zombie child rusage aggregation/reparent/list-detach/list-attach/release sequencing, do-wait child/report-thread traversal plus empty-scan sequencing, and ptrace-detach reparent/report/cleanup/wakeup/release/finalize sequencing moved. VM range allocation/free callbacks, split/XPMEM primitive callbacks, memobj refcounting, page-fault range-resolution primitive behavior, actual page-table lookup/allocation/mapping side effects, other child-list/lifetime traversal, broad rusage traversal, broad process lifetime, signal-delivery primitives, atomic refcount primitives, lock/free primitive bodies, and wait primitive behavior remain C-owned outside this completed scoped row. |
| Syscall core | 100 | 100 | Complete for the scoped syscall sequencing row. Policy, many handler subpaths, direct ID leaf bodies, uid/gid getters and setters, mckfd lookup/dispatch, memory-policy syscalls including `get_mempolicy()`, `set_mempolicy()`, and `mbind()` body sequencing, signal/time/scheduler/wait/ptrace body sequencing, `do_wait()` traversal and result shaping, and top-level `ptrace()` request/callback body dispatch moved. Top-level syscall dispatch, actual user-copy primitive, Linux forwarding callback bodies, lock and CPU-interrupt primitive bodies, allocation/free, register/fp primitives, process-memory access, signal-delivery primitive behavior, ptrace lookup/orchestration, waitqueue/schedule/signal primitive behavior, scheduler migration side-effect bodies, broader scheduler/time primitive bodies, and other primitive C callback implementations still block standalone Rust and neighboring primitive ownership outside this completed scoped row. |
| Scheduler/timers/wait/futex | 100 | 100 | Complete for the scoped scheduler/timer/futex sequencing row. Queue/list helpers, policies, scheduler syscall validation/target-selection/permission-check/user-copy sequencing for set/get-param, set/get-scheduler, RR-interval queries, set-affinity, and get-affinity, scheduler migration-request body sequencing for waitq setup, request queue publication, target runqueue flag/status mutation, remote interrupt decision, log callback dispatch, schedule handoff, and waitq finish, scheduler migration-completion body sequencing for migration queue traversal, request detach/ack gates, affinity target selection, runqueue detach/add with length mutation, thread CPU update, same-VM sibling scan, address-space CPU-set update, target reschedule flag publication, interrupt dispatch, waitqueue wake, and lock ordering, `init_timers()` list/lock init sequencing, `schedule_timeout()` spin-wake/runqueue/schedule-callback/spin-loop/timeout-expiry sequencing, `wake_timers_loop()` timer tick/decrement/detach/log/wakeup sequencing, `set_timer()` runqueue scan and LAPIC enable/disable decision sequencing, local interval-timer current-value subtraction, elapsed reset, enabled-state publication, set-timer callback dispatch, futex table orchestration, futex bucket selection, top-level futex command dispatch, futex wake target orchestration, futex queue/unqueue/wait body sequencing, futex key construction, futex wake/requeue/wake-op return orchestration, and futex wait entry/profile sequencing moved. Actual spinlock primitives, rdtsc/pause primitive behavior, LAPIC timer primitive behavior, waitqueue wake primitive behavior, IPIs, context switching, futex key lifetime, user-value loads, allocation/hash callbacks, IKC send and scheduler wake primitives, migration primitive callbacks, race retry, `schedule()` primitive behavior, and broader wait/requeue side effects remain C-owned outside this completed scoped row. |
| procfs/sysfs/xpmem/file objects | 100 | 100 | Complete for the scoped file-object/XPMEM sequencing row. Rust now owns the procfs/sysfs data-production and request-sequencing bodies listed in `overview.txt`, live mckfd syscall lookup/dispatch plus close unlink/callback/free sequencing, XPMEM open/close/dup/flush lifecycle sequencing, XPMEM release/remove wrapper sequencing, XPMEM AP hash-bucket release-drain sequencing, XPMEM thread-group destroy dispatch, XPMEM access-permit release lifecycle sequencing, XPMEM segment-removal lifecycle sequencing, XPMEM thread-group segment-list drain sequencing, public XPMEM detach wrapper sequencing, `xpmem_vm_munmap()` begin/remove/finish sequencing, internal `xpmem_detach_att()` sequencing, XPMEM clear-PTE wrapper/range/AP/attachment traversal and unpin/lookup/munmap/VALIDPTE sequencing, and `xpmem_remove_process_memory_range()` null/destroying/full-detach/trim/split sequencing. Actual allocation/free primitives outside covered mckfd allocation/free-callback dispatch, refcount primitive behavior, lock/list primitive behavior, remove-range/free-range/page-table primitive behavior, page I/O, procfs request mapping/lookup/lock primitive behavior, raw sysfs/procfs IKC send behavior, public IKC handler wrapping/logging, and user-copy still block standalone Rust and neighboring primitive ownership outside this completed row. |
| host/IKC/mcctrl/IHK kernel paths | 100 | 100 | Complete for the scoped host/IKC/IHK sequencing row. Rust now owns the bounded IHK host DMA request callback dispatcher, the host SCD packet dispatcher body for init-channel ACK, prepare-process, schedule-process, wake-syscall-thread, remote page-fault, send-signal, procfs request/release, cleanup process/fd, debug-log, sysfs show/store/release, perf-control, CPU register, unknown-message, and packet-release sequencing, top-level syscall packet-handler wrapper sequencing for raw packet casting, response-channel callback selection, current-thread callback selection, dispatch constant shaping, dispatch call/return, and packet release, dummy packet-handler release sequencing, host `process_msg_prepare_process()` freeze-gate, descriptor map/span validation, mapping, validation, clone, main-thread creation, process/thread/VM metadata publication, NUMA policy publication, prepare-ranges dispatch, success cleanup/unmap/TLB flush, and failure destroy/free/unmap return shaping, host prepare-ranges ELF section-loop sequencing, interpreter/aout relocation, section page-span/range calculation, memory-range creation, user-page allocation, page-table mapping dispatch/failure cleanup, remote-PA and text/data/map/brk publication, entry/auxv/context adjustment, data-too-large return shaping, host args/envs stack-prep sequencing for arg/env range placement, allocation/physical publication, remote/local copy orchestration, saved_cmdline publication, argv/env pointer fixup, vDSO map/clear, rprocess/rpgtable publication, and init-stack callback dispatch, plus `init_process_stack()` primary execution-body sequencing for stack sizing/range selection, AP-user policy, allocation, zeroing, VM range creation, page-table set-range callback dispatch, auxv/argv/env layout, `saved_auxv` publication, user stack pointer publication, and VM stack bounds, plus host IKC2Linux channel-table allocation/zeroing/publication, connect-parameter shaping, retry/delay/log sequencing, channel-slot publication, current-channel callback sequencing, public IKC2Linux init panic-on-error wrapper sequencing, host IKC2McKernel parameter shaping, retry/delay/log sequencing, regular-channel callback sequencing, and public IKC2McKernel init panic-on-error wrapper sequencing. Device allocation, memory registration, file I/O, waits/callbacks beyond those bounded dispatchers, primitive callback side effects including map/unmap/copy/user-page allocation, allocation/connect/delay/current-channel/regular-channel primitive bodies, broad IKC exchange mutation, raw IKC send side effects, broad allocation/lifetime, and kernel object lifecycle remain C-owned outside this completed sequencing row. |

Latest strict-core movement for the Page allocator low-level dispatch batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: Page allocator strict
  ownership moves 99% -> 100%, because Rust now owns ten connected low-level
  allocator dispatch slices covering `pa_ops` storage, tracking-init callback
  ordering, early-invalidate callback ordering, allocator ops publication,
  aligned allocation pa-ops versus early-allocation selection, missing
  allocation-callback/null handling, default page-allocation
  alignment/node/virtual-address shaping, free-side pa-ops/null/free-callback
  selection, exported `___ihk_mc_*()` body publication from Rust, and C wrapper
  demotion to fallback/ABI scaffolding.
- Post-+50 strict-core movement is now about +398 points. C still owns C
  fallback scaffolding, pa-ops implementation callback bodies, actual
  allocation/free primitive side effects below the published ops callbacks,
  MCS/interrupt primitive bodies, current-node primitive lookup, IKC
  channel/send side effects, logging/panic primitive bodies, deferred-zero
  worker timing, FUGAKU debug preempt behavior, and broader allocator lifetime.
- Standalone Rust readiness remains about 40% because the default OS/control
  path still requires the C-owned primitive substrate and fallback pieces listed
  above.

Previous strict-core movement for the host IKC public-handler batch:

- Broad dashboard movement is 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: host/IKC/mcctrl/IHK
  kernel paths moves 99% -> 100%, because Rust now owns ten connected public
  handler/wrapper slices covering syscall packet casting, response-channel
  callback lookup, current-thread callback lookup, dispatch constant shaping,
  dispatch call/return, dummy handler packet release, public IKC2Linux init
  result-call sequencing, IKC2Linux panic-on-error behavior, public
  IKC2McKernel init result-call sequencing, and IKC2McKernel panic-on-error
  behavior.
- Post-+50 strict-core movement is now about +397 points. C still owns C
  fallback scaffolding, device allocation, memory registration, file I/O,
  primitive callback side effects including map/unmap/copy/user-page
  allocation, allocation/connect/delay/current-channel/regular-channel
  primitive bodies, raw IKC send side effects, broad IKC exchange mutation,
  broad allocation/lifetime, and kernel object lifecycle.
- Standalone Rust readiness remains about 40% because the default OS/control
  path still requires the C-owned primitive substrate listed above.

Previous strict-core movement for the pagealloc public-wrapper batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: Page allocator strict
  ownership moves 98% -> 99%, because Rust now owns ten connected public
  bitmap page-allocator wrapper slices covering exported
  `__ihk_pagealloc_init()` failure-log/status routing, `ihk_pagealloc_init()`
  default-initializer sequencing, `ihk_pagealloc_destroy()` free-callback
  dispatch, `ihk_pagealloc_alloc()` lock-node/alloc dispatch,
  `ihk_pagealloc_reserve()` lock-node/reserve dispatch,
  `ihk_pagealloc_free()` bad-address capture and double-free error callback
  routing, `ihk_pagealloc_count()` lock/count dispatch,
  `ihk_pagealloc_query_free()` lock/query dispatch,
  `__ihk_pagealloc_zero_free_pages()` begin/locked-zero/done sequencing, and
  focused public-wrapper equivalence coverage for success, invalid,
  init-fail, lock-callback, and zero-log paths.
- Post-+50 strict-core movement is now about +396 points. C still owns C
  fallback scaffolding, pa-ops primitive behavior, low-level page
  allocation/free primitive bodies, MCS/interrupt primitive bodies,
  current-node primitive lookup, IKC channel/send side effects, logging/panic
  primitive bodies, deferred-zero worker timing, FUGAKU debug preempt behavior,
  and broader allocator lifetime.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned allocator primitive substrate listed above.

Previous strict-core movement for the NUMA allocator-lifecycle batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: Page allocator strict
  ownership moves 97% -> 98%, because Rust now owns ten connected
  `numa_init()` lifecycle slices covering NUMA-node discovery, node
  id/Linux-id/type publication, allocator-list and node-distance reset
  publication, rbtree-node primitive-init callback ordering, memory-chunk
  iteration, last-early-heap start adjustment, rbtree add-free dispatch,
  legacy page-allocator init/list publication dispatch, physical-memory and
  final-node log callback sequencing, and total-memory rusage accounting.
- Post-+50 strict-core movement was about +395 points. C still owns C
  fallback scaffolding, pa-ops primitive behavior, low-level page
  allocation/free primitive bodies, MCS/interrupt primitive bodies,
  current-node primitive lookup, IKC channel/send side effects, logging/panic
  primitive bodies, deferred-zero worker timing, FUGAKU debug preempt behavior,
  and broader allocator lifetime.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned allocator primitive substrate listed above.

Previous strict-core movement for the memory-policy syscall batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%.
- Strict-core movement is about +2 verified row points: Syscall core strict
  ownership moves 98% -> 100% for the scoped sequencing row, because Rust now
  owns twenty connected `set_mempolicy()` and `mbind()` slices covering
  nodemask validation/copyin, process-mask mutation, range-policy
  lock/lookup/clear/allocate/insert/update sequencing, and policy/interleave
  publication.
- Post-+50 strict-core movement is now about +394 points. C still owns C
  fallback scaffolding, the actual user-copy primitive, memory-range
  lock/lookup primitives, range-policy tree/allocator primitives, top-level
  syscall dispatch, Linux forwarding, allocation/free, signal-delivery
  primitives, ptrace/process-memory primitives, waitqueue/schedule/signal
  behavior, and broader primitive side effects.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned syscall and primitive substrate listed above.

Previous strict-core movement for the fault/PTE lookup batch:

- Broad dashboard movement is 0 points because the Process/VM row is already
  capped at 100%.
- Strict-core movement is about +1 verified row point: Process/VM strict
  ownership moves 99% -> 100% for the scoped sequencing row, because Rust now
  owns ten connected `ihk_mc_pt_lookup_fault_pte()` and `lookup_node()` slices:
  initial PTE lookup dispatch, missing/inactive PTE classification,
  `PF_POPULATE | PF_USER` page-fault callback dispatch, retry lookup,
  recovered-PTE log dispatch, lookup-node fault error return shaping,
  address-space/page-table extraction by verified offsets, post-fault PTE
  lookup with null output pointers, missing-PTE `-ENOENT` shaping, and
  physical-to-NUMA-node return shaping.
- Post-+50 strict-core movement was about +391 points. C still owns C
  fallback scaffolding, raw page-fault behavior, actual page-table
  lookup/allocation/mapping side effects, VM range allocation/free callbacks,
  split/XPMEM primitive callbacks, memobj refcount primitives, lock/free
  primitive bodies, signal-delivery primitives, child-list/lifetime traversal,
  broad rusage traversal, and broader process lifetime.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned process/VM and page-table primitive substrate listed
  above.

Previous strict-core movement for the allocator query-free interrupt batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: Page allocator strict
  ownership moved 96% -> 97%, because Rust now owns ten connected
  `query_free_mem_interrupt_handler()` slices: NUMA-node iteration, per-node
  free-page callback dispatch, total accumulation, total free-page logging,
  optional FUGAKU panic dispatch, `memdebug` command lookup,
  `kmalloc_memcheck()` callback dispatch, `pagealloc_memcheck()` callback
  dispatch, page-hash count/log callback dispatch, and optional ATTACHED_MIC
  sbox scratch publication.
- Post-+50 strict-core movement was about +390 points. C still owns C
  fallback scaffolding, per-allocator query primitive behavior, pa-ops
  primitive behavior, low-level page allocation/free primitive bodies,
  MCS/interrupt primitive bodies, IKC channel/send side effects,
  logging/panic primitives, deferred-zero worker timing, FUGAKU debug preempt
  behavior, and broader allocator lifetime.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned primitive allocator substrate listed above.

Previous strict-core movement for the allocator policy/free-wrapper batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: Page allocator strict
  ownership moved 95% -> 96%, because Rust now owns ten connected wrapper
  slices: invalid-size rejection, not-initialized/idle fallback policy shaping,
  current-VM lookup gating, user-VA range-policy search, memory-range lookup,
  shared-memory gate selection, range-policy field selection, process-policy
  fallback selection, current-node/nr-node publication into the allocation
  policy body, and top-level `mckernel_free_pages()` virt-to-phys/
  phys-to-page/pending-free/allocator-free handoff sequencing.
- Post-+50 strict-core movement was about +389 points. C still owns C
  fallback scaffolding, pa-ops primitive behavior, low-level page
  allocation/free primitive bodies, MCS/interrupt primitive bodies,
  current-node lookup, IKC send/channel behavior, logging/panic primitives,
  deferred-zero worker timing, FUGAKU debug preempt behavior, and broader
  allocator lifetime.
- Standalone Rust readiness remains about 40% because the default OS path still
  requires the C-owned primitive allocator substrate listed above.

Previous strict-core movement for the init-stack body batch:

- Broad dashboard movement is 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement is about +1 verified row point: host/IKC/mcctrl/IHK
  kernel paths moves 98% -> 99%, because Rust now owns
  `init_process_stack()` primary execution-body sequencing: stack sizing,
  max/min limit selection, AP-user policy, aligned allocation, stack zeroing,
  VM stack range creation, page-table set-range callback dispatch, auxv/argv/env
  stack layout, `saved_auxv` publication, user stack pointer/context
  publication, and VM stack bound publication.
- Post-+50 strict-core movement was about +388 points. C still owns C
  fallback scaffolding, primitive map/unmap/copy/user-page allocation,
  mapping/thread/range primitive callbacks, raw IKC send side effects, device
  allocation, memory registration, file I/O, waits/callbacks beyond bounded
  dispatchers, broad allocation/lifetime, and kernel object lifecycle.
- Standalone Rust readiness remains about 40% because the default OS path
  still requires C fallback scaffolding and the C-owned primitive/control-plane
  substrate listed above.

Previous strict-core movement for the host args/envs stack-prep batch:

- Broad dashboard movement is 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement is about +10 verified body-slice points:
  host/IKC/mcctrl/IHK kernel paths moves 96% -> 98%, because Rust now owns
  `prepare_process_ranges_args_envs()` args/envs stack-prep sequencing:
  arg/env page-count and range placement, argenv page allocation and physical
  publication, argenv memory-range creation and error/free shaping, remote
  args map/copy/unmap/TLB sequencing, remote envs map/copy/unmap/TLB sequencing,
  local args/envs length publication, saved_cmdline free/alloc/copy publication,
  argv/env pointer fixup into process VA, vDSO map/clear and
  rprocess/rpgtable publication, and init_process_stack callback dispatch/error
  shaping.
- Post-+50 strict-core movement was about +387 points. C still owns C
  fallback scaffolding, primitive map/unmap/copy/user-page allocation and
  init_process_stack internals, mapping/thread/range primitive callbacks, raw
  IKC send side effects, device
  allocation, memory registration, file I/O, waits/callbacks beyond bounded
  dispatchers, broad allocation/lifetime, and kernel object lifecycle.
- Standalone Rust readiness remains about 40% because the default OS path
  still requires C fallback scaffolding and the C-owned primitive/control-plane
  substrate listed above.

Previous strict-core movement for the host prepare-process batch:

- Broad dashboard movement was 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement was about +12 verified body-slice points:
  host/IKC/mcctrl/IHK kernel paths moved 91% -> 94%, because Rust now owns
  `process_msg_prepare_process()` body sequencing: monitor freeze/frozen gate
  evaluation, program descriptor map-size/page-span calculation, host memory
  map/virtual map/failure cleanup, descriptor magic and section-count
  validation, descriptor clone allocation/copy, main-thread creation and
  cleanup, process PID/PGID/credential/rlimit/profile/VM metadata publication,
  NUMA bind/nodemask policy publication, prepare-ranges callback dispatch,
  success cleanup/unmap/TLB flush, and failure destroy/free/unmap return
  shaping.
- Post-+50 strict-core movement was about +367 points. C still owns C
  fallback scaffolding, mapping/thread/range primitive callbacks, raw IKC send
  side effects, device allocation, memory registration, file I/O,
  waits/callbacks beyond bounded dispatchers, broad allocation/lifetime, and
  kernel object lifecycle.
- Standalone Rust readiness remains about 40% because the default OS path
  still requires C fallback scaffolding and the C-owned primitive/control-plane
  substrate listed above.

Latest strict-core movement for the Process/VM free-range orchestration batch:

- Broad dashboard movement is 0 points because Process/VM management is already
  capped at 100%.
- Strict-core movement is about +10 verified body-slice points:
  Process/VM management moves 97% -> 99%, because Rust now owns
  `free_process_memory_range()` body sequencing: previous/next range discovery,
  page-table free/clear action planning, page-table lock/unlock callback
  ordering, memobj ref/unref ordering around free-range side effects,
  page-table free callback dispatch, page-table clear callback dispatch,
  TOFU removal callback dispatch, final range detach/straight cleanup callback
  dispatch, error log selection, and final return shaping.
- Post-+50 strict-core movement is now about +355 points. C still owns C
  fallback scaffolding, VM range allocation callbacks, split/XPMEM primitive
  callbacks, memobj refcount primitives, TOFU split/merge hooks, actual
  page-table lookup/allocation/mapping/free/clear primitive effects,
  page-fault range-resolution primitive behavior, broad process lifetime,
  rusage traversal, signal-delivery primitives, atomic refcount primitive
  behavior, lock/free primitive bodies, and wait primitive behavior.
- Standalone Rust readiness remains about 40% because the default kernel path
  still requires C fallback scaffolding and the C-owned primitive substrate
  listed above.

Previous strict-core movement for the Process/VM remove-range orchestration batch:

- Broad dashboard movement is 0 points because Process/VM management is already
  capped at 100%.
- Strict-core movement is about +10 verified body-slice points:
  Process/VM management moved 95% -> 97%, because Rust now owns
  `remove_process_memory_range()` body sequencing: straight-map conversion and
  missing-straight handling, range lookup/iteration, split-start and split-end
  callback sequencing, read-only freed publication, XPMEM removal callback
  dispatch, free callback dispatch, error log selection, and final return
  shaping.
- Post-+50 strict-core movement was about +345 points. C still owned C
  fallback scaffolding, VM range allocation/free callbacks,
  split/free/XPMEM primitive callbacks, memobj refcount primitives, TOFU hooks,
  actual page-table lookup/allocation/mapping/free/clear side effects,
  page-fault range-resolution primitive behavior, broad process lifetime,
  rusage traversal, signal-delivery primitives, atomic refcount primitive
  behavior, lock/free primitive bodies, and wait primitive behavior.

Previous strict-core movement for the Process/VM page-fault/populate batch:

- Broad dashboard movement was 0 points because Process/VM management was
  already capped at 100%.
- Strict-core movement was about +10 verified body-slice points:
  Process/VM management moved 93% -> 95%, because Rust now owns
  do-page-fault VM outer-body sequencing for stack-grow range selection,
  write/read memory-range lock decisions, exiting and out-of-range checks,
  permission checks, zero-object `PF_POPULATE` promotion, normal-vs-XPMEM
  range-fault dispatch, and unlock/return shaping. Rust also owns
  `page_fault_process_vm()` `-ERESTART` retry sequencing around preempt
  enable/disable and page-I/O callback dispatch/clear, plus
  `populate_process_memory()` preempt, per-page fault, first-error warning,
  and return sequencing.
- Post-+50 strict-core movement was about +335 points. C still owned C
  fallback scaffolding, VM range allocation/free callbacks, memobj refcount
  primitives, TOFU hooks, actual page-table lookup/allocation/mapping/free/clear
  side effects, page-fault range-resolution primitive behavior, broad process lifetime, rusage traversal,
  signal-delivery primitives, atomic refcount primitive behavior, lock/free
  primitive bodies, and wait primitive behavior.

Previous strict-core movement for the Process/VM range lookup/access/protection batch:

- Broad dashboard movement was 0 points because Process/VM management was already
  capped at 100%.
- Strict-core movement was about +10 verified body-slice points:
  Process/VM management moved 91% -> 93%, because Rust now owns VM range lookup
  body traversal, range-cache hit/store sequencing, first overlap selection,
  next/previous range iteration, extend-up validation/commit, change-protection
  new-flag calculation, attr-delta shaping, private-file writable suppression,
  page-table lock/change-attr callback sequencing, `-ENOENT` acceptance, final
  flag publication, and `access_ok()` initial-range, adjacency, permission, and
  multi-range loop validation.
- Post-+50 strict-core movement was about +325 points. C still owned C
  fallback scaffolding, VM range allocation/free callbacks, memobj refcount
  primitives, TOFU hooks, actual page-table lookup/allocation/mapping/free/clear
  side effects, page-fault range-resolution primitive behavior, broad process
  lifetime, rusage traversal, signal-delivery primitives, atomic refcount
  primitive behavior, lock/free primitive bodies, and wait primitive behavior.

Previous strict-core movement for the XPMEM clear-PTE/remove-range batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement is about +10 verified body-slice points:
  procfs/sysfs/xpmem/file objects moves 99% -> 100% for the scoped sequencing
  row, because Rust now owns XPMEM clear-PTE wrapper, segment/AP/attachment
  traversal, AP ref/unlock/clear/relock/deref sequencing, attachment
  read-lock/write-lock range calculation, unpin callback dispatch, range
  lookup, munmap callback dispatch, VALIDPTE clearing, and
  out-of-range/missing-range preservation paths. Rust also owns
  `xpmem_remove_process_memory_range()` null-private-data, already-destroying,
  full-detach, front/tail trim, middle split, private-data publication, and
  invalid-split result sequencing.
- Post-+50 strict-core movement was about +315 points. C still owns C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, remove-range/free-range/page-table
  primitive behavior, raw IKC/procfs/sysfs exchange, page I/O, user-copy, and
  broader high-risk file/object bodies.

Previous strict-core movement for the XPMEM release-management wrapper/drain batch:

- Broad dashboard movement was 0 points because the procfs/sysfs/xpmem/file
  objects row was already capped at 100%.
- Strict-core movement is about +9 verified body-slice points:
  procfs/sysfs/xpmem/file objects moved 97% -> 98%, because Rust now owns
  XPMEM release-management wrapper/drain sequencing: AP hash-bucket iteration,
  per-bucket writer-lock/unlock sequencing, empty-bucket handling, first-AP
  selection from hash-list heads, AP ref/unlock/release/deref/relock ordering,
  release/remove syscall wrapper positive-ID, owner, object-lookup, action,
  and deref sequencing, and thread-group destroyable/deref dispatch.
- Post-+50 strict-core movement was about +295 points. The remaining C-owned
  blockers were C fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, raw attachment detach internals,
  raw IKC/procfs/sysfs exchange, page I/O, user-copy, PTE-clear primitive
  behavior, and broader high-risk file/object bodies.

Previous strict-core movement for the XPMEM access-permit release batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement is about +8 verified body-slice points:
  procfs/sysfs/xpmem/file objects moves 96% -> 97%, because Rust now owns
  XPMEM access-permit release lifecycle sequencing: destroy-start gating,
  attachment-list drain, attachment ref/detach/deref callback ordering, final
  destroyed-state publication, AP hash-list unlink, segment AP-list unlink,
  segment and segment-thread-group deref callback ordering, AP destroyable
  dispatch, debug-log event selection, and already-destroying early return
  behavior.
- Post-+50 strict-core movement is now about +286 points. C still owns C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, raw attachment detach internals,
  raw IKC/procfs/sysfs exchange, page I/O, user-copy, PTE-clear primitive
  behavior, and broader high-risk file/object bodies.

Previous strict-core movement for the XPMEM segment-list drain batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement was about +5 verified body-slice points:
  procfs/sysfs/xpmem/file objects moved 95% -> 96%, because Rust now owns
  XPMEM thread-group segment-list drain sequencing: writer-lock acquisition,
  empty-list detection, first-segment selection from the list head, segment
  refcount callback ordering, unlock-before-removal, per-segment removal
  callback dispatch, deref callback ordering, relock loop sequencing, final
  unlock, debug-log event selection, and empty-list return behavior.
- Post-+50 strict-core movement was about +278 points. C still owned C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, raw IKC/procfs/sysfs exchange, page I/O,
  user-copy, PTE-clear primitive behavior, and broader high-risk file/object
  bodies.

Previous strict-core movement for the XPMEM segment-removal lifecycle batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement was about +8 verified body-slice points:
  procfs/sysfs/xpmem/file objects moved 94% -> 95%, because Rust now owns
  XPMEM segment-removal lifecycle sequencing: destroy-start gating, segment
  destroy-flag publication, PTE-clear callback ordering, final destroyed-state
  publication, segment-list lock/unlock ordering, list unlink,
  destroyable/refdrop callback dispatch, debug-log event selection, and
  already-destroying early return behavior.
- Post-+50 strict-core movement was about +273 points. C still owned C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, raw IKC/procfs/sysfs exchange, page I/O,
  user-copy, PTE-clear primitive behavior, and broader high-risk file/object
  bodies.

Previous strict-core movement for the XPMEM close/dup/flush lifecycle batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement was about +8 verified body-slice points:
  procfs/sysfs/xpmem/file objects moved 93% -> 94%, because Rust now owns
  XPMEM `close()`/`dup()`/flush lifecycle sequencing: duplicate data clearing
  and open-count increment, close open-count decrement and logging,
  flush/partition-exit decisions, flush target-group lookup under the
  partition hash-list lock, target-group list unlink, destroy-flag
  publication, access-permit and segment-release callback ordering, final
  destroyed-state publication, and destroy callback dispatch.
- Post-+50 strict-core movement was about +265 points. C still owned C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  raw refcount/list primitive behavior, raw IKC/procfs/sysfs exchange, page I/O,
  user-copy, and broader high-risk file/object bodies.

Previous strict-core movement for the XPMEM open-body batch:

- Broad dashboard movement is 0 points because the procfs/sysfs/xpmem/file
  objects row is already capped at 100%.
- Strict-core movement is about +8 verified body-slice points:
  procfs/sysfs/xpmem/file objects moves 92% -> 93%, because Rust now owns
  XPMEM `open()`/`openat()` body sequencing below the syscall pathname wrapper:
  partition-init gate, Linux fd-forward result handling, `__xpmem_open()`
  callback ordering, mckfd allocation/null handling, mckfd zeroing and
  fd/signal/data/callback publication, locked list-head insertion, unlock
  ordering, open-count increment, and debug-log event selection.
- Post-+50 strict-core movement is now about +257 points. C still owns C
  fallback scaffolding, primitive allocation/free, primitive locks and atomics,
  Linux forwarding, pathname copy/classification in the syscall wrapper, raw
  IKC/procfs/sysfs exchange, user-copy, and broader high-risk file/object
  bodies.

Previous strict-core movement for the mckfd syscall dispatch batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%, and the procfs/sysfs/xpmem/file objects row is also capped.
- Strict-core movement is about +10 verified body-slice points: Syscall core
  strict ownership moves 96% -> 97%, and procfs/sysfs/xpmem/file objects moves
  91% -> 92%, because Rust now owns live `read()`, `ioctl()`, `fcntl()`, and
  `close()` mckfd syscall body sequencing: locked lookup traversal,
  callback-vs-forward selection, optional TOFU ioctl/close cleanup gates,
  close unlink mutation, close-callback dispatch, mckfd free-callback dispatch,
  and Linux-forward fallback sequencing.
- Post-+50 strict-core movement is now about +249 points. C still owns C
  fallback scaffolding, primitive locks, Linux forwarding, XPMEM open/openat
  creation, raw allocation/free primitives, user-copy, syscall dispatch, and
  broader high-risk file/object/syscall bodies.

Previous strict-core movement for the ten-slice syscall wrapper batch:

- Broad dashboard movement was 0 points because the Syscall core row was
  already capped at 100%.
- Strict-core movement was about +10 verified body-slice points while the
  Syscall core strict ownership row moved 95% -> 96%, because Rust now owns
  `times()`, `setpgid()`, `setrlimit()`, `getrlimit()`, `prlimit64()`,
  `sysinfo()`, `get_cpu_id()`, `mlockall()`, `munlockall()`, and `getcpu()`
  wrapper-body sequencing.
- Post-+50 strict-core movement was about +239 points.

Previous strict-core movement for the signal/credential syscall wrapper batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%.
- Strict-core movement is about +10 verified body-slice points while the
  Syscall core strict ownership row moves 94% -> 95%, because Rust now owns
  the wrapper-body sequencing for `kill()`, `tgkill()`, `tkill()`,
  `setresuid()`, `setreuid()`, `setuid()`, `setfsuid()`, `setresgid()`,
  `setregid()`, `setgid()`, and `setfsgid()`: signal-target validation,
  siginfo construction, do-kill callback dispatch, Linux-forward callback
  dispatch, credential-refresh callback dispatch, setfsid syscall callback
  dispatch, return shaping, and missing-callback error shaping.
- Post-+50 strict-core movement is now about +229 points. C still owns the
  primitive bodies behind those callbacks: Linux forwarding, credential source
  refresh, actual signal delivery, user-copy, locks, allocation/free, syscall
  dispatch, default-path C fallback scaffolding, and broader high-risk syscall
  bodies.

Previous strict-core movement for the ptrace syscall request-dispatch batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%.
- Strict-core movement is about +10 verified body-slice points while the
  Syscall core strict ownership row moves 93% -> 94%, because Rust now owns
  the top-level `ptrace()` request/callback body dispatch for `PTRACE_TRACEME`,
  kill/continue/singlestep/syscall wake requests, register/fpreg/regset
  get/set requests, user/text peek/poke requests including data aliases,
  set-options, attach/detach, siginfo/eventmsg, arch fallback, and
  unsupported/missing-callback error shaping.
- Post-+50 strict-core movement is now about +219 points. C still owns the
  primitive handler bodies behind those callbacks: thread lookup/unlock,
  user-copy, register/fpreg/regset primitives, process-memory read/patch,
  signal delivery, allocation/free, default-path C fallback scaffolding, and
  broader high-risk syscall bodies.

Previous strict-core movement for the ptrace-detach body batch:

- Broad dashboard movement is 0 points because the Syscall core and Process/VM
  rows are already capped at 100%.
- Strict-core movement is about +2 points: Syscall core strict ownership moves
  92% -> 93%, and Process/VM strict ownership moves 90% -> 91%, because Rust
  now owns `ptrace_detach_thread()` main-body sequencing: main-thread detach
  gating, zombie finalization selection, tracer child-list detach, ptraced
  reparenting to the original parent, report-list detach/reattach, ptrace
  cleanup/free callback dispatch, single-step clear dispatch, exit-signal
  dispatch, forwarded-signal siginfo construction, `do_kill()` callback
  sequencing, wake/release dispatch, and final process finalization dispatch.
- Post-+50 strict-core movement is now about +209 points. C still owns
  primitive lock/list/free/wakeup/signal callback bodies, syscall dispatch,
  user-copy primitives, ptrace lookup/orchestration, default-path C fallback
  scaffolding, and broader high-risk handler bodies.

Latest strict-core movement for the wait-scan traversal syscall batch:

- Broad dashboard movement is 0 points because the Syscall core and Process/VM
  rows are already capped at 100%.
- Strict-core movement is about +3 points: Syscall core strict ownership moves
  90% -> 92%, and Process/VM strict ownership moves 89% -> 90%, because Rust
  now owns the outer process/thread wait scans under `do_wait()`: parent
  children-lock callback ordering, children-list traversal, pid/pgid matching,
  `empty` publication, process-zombie dispatch, process stopped/continued
  candidate dispatch, ptraced-children empty-scan traversal, report-thread
  list traversal, report-thread candidate dispatch, regular thread-list
  empty-scan traversal, and no-found unlock/return sequencing.
- Post-+50 strict-core movement is now about +207 points. C still owns the
  primitive lock/list/free bodies, waitqueue/schedule/signal primitive
  behavior, host wait primitive behavior, syscall dispatch, user-copy
  primitives, default-path C fallback scaffolding, and broader high-risk
  handler bodies.

Previous strict-core movement for the wait-zombie/reparent syscall batch:

- Broad dashboard movement is 0 points because the Syscall core and Process/VM
  rows are already capped at 100%.
- Strict-core movement is about +2 points: Syscall core strict ownership moves
  89% -> 90%, and Process/VM strict ownership moves 88% -> 89%, because Rust
  now owns the process-zombie branch under `do_wait()`: zombie status
  publication, host wait4 skip/request/log selection, parent rusage
  aggregation, rusage result fill, parent child-list detach, PID-1
  reparent/list attach, child main-thread ptrace-detach gate, parent and child
  lock/unlock callback ordering, no-reparent unlock/detach ordering, and
  process release callback dispatch.
- Post-+50 strict-core movement was about +204 points. C still owned
  child/thread list traversal, broader zombie scan/reparent surroundings,
  primitive lock/list/free bodies, waitqueue/schedule/signal primitive
  behavior, broader rusage traversal, release/detach primitive bodies, and
  fallback scaffolding.

Previous strict-core movement for the wait-candidate syscall batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%.
- Strict-core movement is about +1 point: Syscall core strict ownership moves
  88% -> 89% because Rust now owns the `wait_proc()`/`wait_thread()` candidate
  result sequencing under `do_wait()`: process and report-thread stopped,
  ptraced-stopped, continued, and report-thread exited candidates; ptraced
  stop miss return preservation; process TID rewrite for requested thread
  waits; report-list detach, ptrace-detach, release, reap, unlock, and found
  publication callback ordering.
- Post-+50 strict-core movement was about +202 points. C still owned
  child/thread list traversal, zombie scan/reparent behavior, primitive lock
  bodies, waitqueue/schedule/signal primitive behavior, rusage aggregation,
  release/detach primitive bodies, and fallback scaffolding.

Previous strict-core movement for the do_wait syscall batch:

- Broad dashboard movement is 0 points because the Syscall core row is already
  capped at 100%.
- Strict-core movement is about +1 point: Syscall core strict ownership moves
  87% -> 88% because Rust now owns top-level `do_wait()` wait-loop sequencing
  for waitqueue init/prepare/finish callback ordering, process/thread scan
  dispatch gates, no-child and `WNOHANG` result shaping, pending-signal
  interrupt return, schedule callback handoff, wake/rescan behavior, and wait
  log callback ordering.
- Post-+50 strict-core movement was about +201 points. C still owned
  `wait_proc()`/`wait_thread()` child/thread list traversal and mutation,
  waitqueue/schedule/signal primitive behavior, rusage aggregation,
  release/detach side effects, and fallback scaffolding.

Previous strict-core movement for the scheduler migration-completion batch:

- Broad dashboard movement is 0 points because the Scheduler/timers/wait/futex
  row is already capped at 100%.
- Strict-core movement is about +2 post-cap points: Rust now owns
  `do_migrate()` body sequencing for migration queue traversal, request
  detach and ack gates, affinity target selection, runqueue detach/add with
  length mutation, thread CPU update, same-VM sibling scan, address-space
  CPU-set lock/update, target reschedule flag publication,
  interrupt/vector callback dispatch, waitqueue wake callback dispatch, lock
  ordering, and validation/error shaping.
- Post-+50 strict-core movement was about +200 points. C still owns
  spinlock/waitqueue/interrupt/vector/log primitive bodies, CPU-local lookup
  callbacks, context switching, `schedule()` primitive behavior, and fallback
  scaffolding.

Previous strict-core movement for the scheduler migration-request batch:

- Broad dashboard movement was 0 points because the Scheduler/timers/wait/futex
  row was already capped at 100%.
- Strict-core movement was about +2 post-cap points: Rust moved
  `sched_request_migrate()` body sequencing for request thread publication,
  target migration-queue lock callback ordering, waitqueue init/prepare/finish
  callback sequencing, migration request list insertion, target runqueue
  noirq lock/unlock callback ordering, `CPU_FLAG_NEED_RESCHED` and
  `CPU_FLAG_NEED_MIGRATE` publication, `CPU_STATUS_RUNNING` publication,
  remote interrupt vector/callback selection, migration log callback dispatch,
  scheduler callback handoff, and validation/error shaping.
- Post-+50 strict-core movement was about +198 points. C still owned target
  CPU-local lookup, current-thread wait-entry construction,
  spinlock/waitqueue/interrupt/vector/schedule/log primitive bodies, actual
  migration completion in `do_migrate()`, context switching, and fallback
  scaffolding.

Previous strict-core movement for the dump user-page traversal/dispatch batch:

- Broad dashboard movement is 0 points because the x86_64 memory-management
  row is already capped at 100%.
- Strict-core movement is about +1 post-cap point: Rust now owns dump
  user-page process-hash bucket iteration, list cursor traversal, process
  recovery from `hash_list`, VM/address-space/page-table pointer loading,
  null skip gates, visitor argument shaping for `[0, USER_END)`,
  `visit_pte_range_safe()` callback dispatch, and dispatch count/error
  shaping.
- Post-+50 strict-core movement was about +196 points. C still owns current
  resource-set lookup, the page-table visitor primitive and PTE visitor body,
  low-level page/address data sources, process lifetime/list mutation, logging
  primitive behavior, and fallback scaffolding.

Previous strict-core movement for the dump bitmap/completion batch:

- Broad dashboard movement is 0 points because the x86_64 memory-management
  row is already capped at 100%.
- Strict-core movement is about +2 post-cap points: Rust now owns dump
  page-set completion publication, physical-address membership checks,
  variable-length dump bitmap range clearing, user-PTE dump bitmap marking,
  free-chunk dump bitmap marking, and top-level last-CPU dump query
  sequencing.
- Post-+50 strict-core movement is now about +195 points. C still owns process
  traversal, rb-tree primitive traversal callbacks, page-table visit callback
  invocation, low-level page/address data sources, logging primitive behavior,
  and fallback scaffolding.

Previous strict-core movement for the allocator NUMA topology/allocation batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 point: Page allocator strict ownership
  moves 94% -> 95% because Rust now owns NUMA allocation-attempt sequencing
  for OOM flag initialization, NUMA-id bounds validation, rusage OOM callback
  dispatch, and NUMA allocation callback dispatch, plus distance-id lookup and
  distance-ordered node selection for `ihk_mc_get_numa_node_by_distance()`.
- Post-+50 strict-core movement was about +193 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, logging/panic primitive behavior, current-node primitive
  lookup, deferred-zero worker timing, IKC send side effects, FUGAKU debug
  preempt behavior, broader allocator lifetime, and fallback scaffolding.

Previous strict-core movement for the allocator NUMA-distance batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 point: Page allocator strict ownership
  moves 93% -> 94% because Rust now owns `numa_distances_init()` sequencing:
  per-node distance-array allocation, allocation-failure logging, distance
  matrix fill, distance/id sorting, node publication, and ordered log callback
  dispatch.
- Post-+50 strict-core movement was about +192 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, logging/panic primitive behavior, deferred-zero worker
  timing, IKC send side effects, FUGAKU debug preempt behavior, broader
  allocator lifetime, and fallback scaffolding.

Previous strict-core movement for the allocator lifecycle/mem_init batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +1 point: Page allocator strict ownership
  moves 92% -> 93% because Rust now owns `ihk_mc_set_page_allocator()`
  tracking initialization, early-allocator invalidation, and `pa_ops`
  publication, plus top-level `mem_init()` sequencing for monitor/rusage/NUMA
  init, allocator registration, page-fault handler publication, query-free
  interrupt registration, page-hash init, virtual-map init, demand-paging
  flag/log publication, and NUMA-distance init ordering.
- Post-+50 strict-core movement was about +191 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, logging/panic primitive behavior, deferred-zero worker
  timing, IKC send side effects, FUGAKU debug preempt behavior, broader
  allocator lifetime, and fallback scaffolding.

Latest strict-core movement for the allocator tracking/lifecycle batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +2 points: Page allocator strict ownership
  moves 90% -> 92% because Rust now owns shared pagealloc/kmalloc tracking
  hash and lock initialization, pagealloc/kmalloc memcheck leak-scan traversal
  with per-entry address-list locking, current-runcount filtering, leak-count
  accumulation, runcount mutation, detail/summary log callback sequencing, and
  kmalloc remote free-list move/consolidation under the remote-list lock.
- Post-+50 strict-core movement is now about +190 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, logging/panic primitive behavior, deferred-zero worker
  timing, IKC send side effects, FUGAKU debug preempt behavior, broad
  allocator lifetime, and fallback scaffolding.

Latest strict-core movement for the pagealloc tracking wrapper batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement is about +2 points: Page allocator strict ownership
  moves 88% -> 90% because Rust now owns public
  `_ihk_mc_alloc_aligned_pages_node()`/`_ihk_mc_free_pages()` pagealloc
  memdebug tracking wrapper sequencing for no-debug/uninitialized fallback,
  allocation-site lookup/create, file-string publication, page-address entry
  publication, exact/partial/split deallocation tracking, address-entry
  rehashing, last-entry cleanup/free, invalid deallocation callback routing,
  final page-free callback sequencing, and log callback selection.
- Post-+50 strict-core movement is now about +188 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, logging/panic primitive behavior, deferred-zero worker
  timing, IKC send side effects, FUGAKU debug preempt behavior, broad
  allocator lifetime, and fallback scaffolding.

Previous strict-core movement for the kmalloc tracking wrapper batch:

- Broad dashboard movement was 0 points because the Page allocator row was
  already capped at 100%.
- Strict-core movement was about +2 points: Page allocator strict ownership
  moved 86% -> 88% because Rust owned public `_kmalloc()`/`_kfree()`
  memdebug tracking wrapper sequencing for no-debug/null fallback, allocation
  hash selection, tracking-entry lookup/create, file-string publication,
  alloc-count mutation, address-entry list/hash publication, free-side address
  lookup/detach, last-entry cleanup/free, invalid-free callback routing, and
  log callback selection.
- Post-+50 strict-core movement was about +186 points at that checkpoint.

Previous strict-core movement for the kmalloc body batch:

- Broad dashboard movement is 0 points because the Page allocator row is
  already capped at 100%.
- Strict-core movement was about +2 points: Page allocator strict ownership
  moved 84% -> 86% because Rust owned low-level `___kmalloc()` size
  alignment, free-list fit search, chunk split/refill, page-allocation callback
  ordering, interrupt save/restore callback ordering, and return shaping, plus
  low-level `___kfree()` null handling, corruption callback routing,
  current-CPU free-list insertion/consolidation, remote-CPU free-list
  publication under lock callbacks, and normal/error return shaping.
- Post-+50 strict-core movement was about +184 points. C still owns actual
  low-level page allocation/free primitive bodies, interrupt and spinlock
  primitive bodies, tracking wrappers, logging/panic primitive behavior,
  deferred-zero worker timing, IKC send side effects, FUGAKU debug preempt
  behavior, broad allocator lifetime, and fallback scaffolding.

Previous strict-core movement for the host IKC init batch:

- Broad dashboard movement is 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement was about +2 points: host/IKC/mcctrl/IHK kernel paths
  strict ownership moved 89% -> 91% because Rust owned host IKC2Linux
  channel-table allocation/zeroing/publication, connect-parameter shaping,
  retry/delay/log sequencing, channel-slot publication, current-channel
  callback sequencing, and host IKC2McKernel parameter shaping, retry/delay/log
  sequencing, and regular-channel callback sequencing.
- Post-+50 strict-core movement was about +182 points. C still owns actual
  allocation/connect/delay/log/panic/current-channel/regular-channel primitive
  bodies, raw IKC exchange side effects, broad allocation/lifetime, and
  fallback scaffolding.

Previous strict-core movement for the procfs maps/status/stat data-production batch:

- Broad dashboard movement was 0 points because the procfs/sysfs/xpmem/file-object
  row was already capped at 100%.
- Strict-core movement was about +3 points: procfs/sysfs/xpmem/file objects
  strict ownership moved 88% -> 91% because Rust owned `/proc/PID/maps`
  range traversal, path/default selection, permission character selection, and
  line output, `/proc/PID/status` locked-size traversal plus state/ID/VmLck/
  thread/mask output, and per-PID `stat` state/identity/comm/constant-field
  output.
- Post-+50 strict-core movement was about +180 points. C still owned actual
  allocation/free primitives, request map/unmap, process/thread lookup,
  memory-range locking, raw procfs IKC answer send, and fallback scaffolding
  behavior.

Previous strict-core movement for the procfs non-mem data-production batch:

- Broad dashboard movement was 0 points because the procfs/sysfs/xpmem/file-object
  row was already capped at 100%.
- Strict-core movement was about +2 points: procfs/sysfs/xpmem/file objects
  strict ownership moved 86% -> 88% because Rust now owned root `mckernel`
  version/buildid output, root `stat` CPU-line output, per-process `auxv`,
  `cmdline`, and `comm` output, and `/proc/PID/pagemap` value-loop/result
  sequencing.
- Post-+50 strict-core movement was about +177 points. C still owned actual
  allocation/free primitives, request map/unmap, process/thread lookup,
  memory-range locking, page-table primitive behavior, complex procfs
  status/stat/maps-style data production, raw IKC answer send, and fallback
  scaffolding behavior at that checkpoint.

Previous strict-core movement for the procfs mem/buffer batch:

- Broad dashboard movement was 0 points because the procfs/sysfs/xpmem/file-object
  row was already capped at 100%.
- Strict-core movement was about +2 points: procfs/sysfs/xpmem/file objects
  strict ownership moved 84% -> 86% because Rust now owns `buf_alloc()`
  allocation-callback/null/init/optional physical-publication sequencing and
  the `/proc/PID/mem` zero-length/page-fault/translation/memory-gate/phys-map/
  read-vs-write copy-loop/error-shaping body.
- Post-+50 strict-core movement was about +175 points. C still owned actual
  page allocation/free primitives, page-fault primitive behavior, page-table
  translation primitive behavior, `is_mckernel_memory()`, `phys_to_virt()`,
  `memcpy()`, request map/unmap, process/thread lookup, raw IKC answer send,
  and fallback scaffolding behavior at that checkpoint.

Previous strict-core movement for the scheduler/timer batch:

- Broad dashboard movement was 0 points because the Scheduler/timers/wait/futex
  row was already capped at 100%.
- Strict-core movement was about +3 points: Scheduler/timers/wait/futex strict
  ownership moved 97% -> 100% because Rust now owns `init_timers()` list/lock
  initialization sequencing, `schedule_timeout()` spin-wake/runqueue/schedule
  handoff/spin-loop/timeout-expiry sequencing, `wake_timers_loop()` timer
  tick/decrement/detach/log/wakeup sequencing, and `set_timer()` runqueue scan
  plus LAPIC enable/disable decision sequencing.

Previous strict-core movement for the x86 user-copy/process-VM batch:

- Broad dashboard movement is 0 points because the x86_64 memory management
  row is already capped at 100%.
- Strict-core movement is about +1 point: x86_64 memory management strict
  ownership moves 99% -> 100% because Rust now owns `verify_process_vm()`,
  `read_process_vm()`, `write_process_vm()`, `patch_process_vm()`,
  `copy_from_user()`, `copy_to_user()`, `strlen_user()`,
  `strcpy_from_user()`, `getlong_user()`, `getint_user()`,
  `setlong_user()`, and `setint_user()` sequencing behind the existing C ABI.
- C still owns current-thread lookup, page-fault primitive behavior, virtual-
  to-physical primitive behavior, map/unmap and phys-to-virt primitive bodies,
  logging callbacks, bridge glue, and fallback scaffolding.
- Validation passed the expanded x86 memory equivalence suite with
  `x86_memory_helpers ok digest=bc79db2659ab2c2a`, Rust-enabled image/module
  build, C-fallback image build, `git diff --check`, script syntax checks,
  ownership report plus dashboard consistency gate, and QEMU version/help/
  dry-run checks. No real QEMU guest boot or reboot-capable validation ran.

Previous strict-core movement for the host SCD dispatcher batch:

- Broad dashboard movement is 0 points because the host/IKC/mcctrl/IHK row is
  already capped at 100%.
- Strict-core movement is about +3 points: host/IKC/mcctrl/IHK kernel paths
  strict ownership moves 86% -> 89% because Rust now owns
  `syscall_packet_handler()` SCD message-family classification, callback
  dispatch, legacy return shaping, sysfs show/store/release argument
  extraction, unknown-message logging dispatch, and final packet release
  sequencing.
- C still owns the ABI wrapper, bridge callbacks, raw IKC send effects,
  primitive lookup/wakeup/register/debug behaviors, allocation/copy/map
  primitive bodies, broad IKC exchange mutation, and fallback scaffolding.
- Validation passed the expanded host helper equivalence suite with
  `object_helpers ok digest=46b2b56d8ab49745`, Rust-enabled image/module
  build, C-fallback image build, `git diff --check`, script syntax checks,
  ownership report plus dashboard consistency gate, and QEMU version/help/
  dry-run checks. No real QEMU guest boot or reboot-capable validation ran.

Previous strict-core movement for the itimer batch:

- Broad dashboard movement is 0 points because Syscall Core and
  Scheduler/timers/wait/futex are already capped at 100%.
- Strict-core movement is about +4 points: Syscall core strict ownership moves
  85% -> 87% and Scheduler/timers/wait/futex strict ownership moves 95% -> 97%
  because Rust now owns local `setitimer()` and `getitimer()` validation,
  ITIMER_REAL forwarding dispatch, virtual/prof old-value snapshot and copyout,
  new-value copyin, elapsed reset, enabled-state publication,
  `set_timer(0)` callback dispatch, null-old handling, and return/error
  shaping.
- C still owns syscall ABI wrappers, raw argument extraction, actual
  `copy_from_user()`/`copy_to_user()` primitive bodies, `do_syscall()`
  forwarding primitive behavior, actual `set_timer()` behavior, timer queues,
  wake/context-switch primitives, spinlocks, broader futex wait/requeue side
  effects, and fallback scaffolding.
- Validation passed the expanded syscall-policy equivalence suite with
  `syscall_policy_helpers ok digest=b445838b397f5e5c`, Rust-enabled
  image/module build, C-fallback image build, `git diff --check`, syntax
  checks over the validation scripts, ownership report plus dashboard
  consistency gate, and QEMU
  version/help/dry-run checks. No real QEMU guest boot or reboot-capable
  validation ran.

Previous strict-core movement for the scheduler affinity batch:

- Broad dashboard movement is 0 points because Syscall Core and
  Scheduler/timers/wait/futex are already capped at 100%.
- Strict-core movement is about +4 points: Syscall core strict ownership moves
  84% -> 85% and Scheduler/timers/wait/futex strict ownership moves 92% -> 95%
  because Rust now owns `sched_setaffinity()` and `sched_getaffinity()`
  validation, target selection, remote lookup/unlock ordering, permission
  gates, cpuset copyin/copyout, target-process mask intersection, thread
  affinity publication, migration callback dispatch, and return/error shaping.
- C still owns syscall ABI wrappers, raw argument extraction, actual
  `copy_from_user()`/`copy_to_user()` primitive bodies, thread
  lookup/hold/release primitive bodies, migration request side effects, and
  fallback scaffolding.
- Validation passed the expanded scheduler equivalence suite with
  `sched_helpers ok digest=91c80d48274899e5`, Rust-enabled image/module build,
  C-fallback image build, `git diff --check`, ownership report, and QEMU
  version/help/dry-run checks. No real QEMU guest boot or reboot-capable
  validation ran.

Latest strict-core movement for the rusage/CPU-time syscall batch:

- Broad dashboard movement is 0 points because Syscall Core is already capped
  at 100%.
- Strict-core movement is about +4 points: Syscall core strict ownership moves
  78% -> 82% because Rust now owns `getrusage()` validation/dispatch,
  SELF/CHILDREN/THREAD aggregation/fill/copyout sequencing, remote thread
  times-update request/interrupt sequencing, pause-callback wait loops, and
  `clock_gettime()` local/forward/thread/process CPU-time sequencing.
- C still owns syscall ABI wrappers, raw argument extraction, the actual
  `copy_to_user()` primitive, lock primitive bodies, CPU interrupt primitive
  behavior, TOD/gettime and Linux-forward callback bodies, scheduler/time
  primitive bodies, and fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `syscall_policy_helpers ok digest=67811b22d625a0cf`, Rust-enabled
  image/module builds, C-fallback image build, build-only wrapper validation,
  no-warning scans over the captured build logs, `git diff --check`, ownership
  report gates, and QEMU version/help/dry-run checks. No real QEMU guest boot
  ran.

Latest strict-core movement for the Process/VM lifecycle release batch:

- Broad dashboard movement is 0 points because Process/VM management is already
  capped at 100%.
- Strict-core movement is about +6 points: Process/VM management strict
  ownership moves 82% -> 88% because Rust now owns sigcommon release-body
  sequencing, TID release/replace body sequencing, `release_thread()`
  ref/profile/procfs/destroy/VM-release sequencing, and
  `release_process_vm()` ref/mckfd/free-callback/TLB/free-ranges/detach/
  policy-drain/final-free sequencing.
- C still owns atomic refcount primitives, spinlock primitives, actual
  allocator/free callbacks, destroy_thread and release_process bodies,
  profile/procfs/TLB/range-free primitive bodies, page-fault behavior, signal
  forwarding, rusage, broad process lifetime, and fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `process_helpers ok digest=b1b68056ccefbaac`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, ownership report gates, and QEMU
  version/help/dry-run checks. No real QEMU guest boot ran.

Latest strict-core movement for the x86 clear-range body batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +1 point: x86_64 memory management strict
  ownership moves 98% -> 99% because Rust now owns clear-range leaf/level/root
  body sequencing: leaf null-skip and PTE clear-exchange sequencing, TLB
  flush-address queue callback sequencing, old-entry action callback handoff,
  old-effect callback orchestration, split-error log/return shaping, large-page
  clear sequencing, child table translation, child-walk dispatch/error
  propagation, `-ENOENT` child-table teardown/free sequencing, root
  skip/translation/dispatch, and level-specific debug logging.
- C still owns the public ABI wrappers, old-entry page lookup/refcount primitive
  behavior, actual allocation/free and address-translation primitive bodies,
  page/RSS primitive bodies, remote TLB shootdown primitive behavior, and
  fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=67f14d5e0baf12ee`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, and QEMU version/help/dry-run checks. No
  real QEMU guest boot ran.

Latest strict-core movement for the x86 visitor-body batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +2 points: x86_64 memory management strict
  ownership moves 96% -> 98% because Rust now owns normal and safe
  `visit_pte_range()` visitor body sequencing: leaf skip/direct visitor
  callback dispatch, level direct/E2BIG retry classification, split-error
  log/return shaping, child page-table allocation/publication, existing
  child-table translation, child-walk callback dispatch, root allocation/
  translation dispatch, and top-level normal/safe visit-range walk dispatch.
- C still owns the public ABI wrappers, actual allocation/free and
  address-translation primitive bodies, page-table walk iteration callbacks,
  broader page frees/RSS accounting, TLB primitive behavior, and fallback
  scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=c701677a3fd62a6f`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, and QEMU version/help/dry-run checks. No
  real QEMU guest boot ran.

Latest strict-core movement for the x86 range-top batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +3 points: x86_64 memory management strict
  ownership moves 93% -> 96% because Rust now owns clear/set range top-level
  orchestration: clear-range bounds validation, TLB invalid-address array
  allocation/free callback sequencing, clear-range argument field publication,
  clear-range top-level `walk_pte_l4` dispatch, final remote TLB flush
  callback dispatch, set-range argument publication, set-range diff/attribute/
  pgshift/range state publication, set-range top-level `walk_pte_l4` dispatch,
  and set-range top-level walk-failure log/return shaping.
- At that checkpoint, C still owned the public ABI wrappers, actual
  allocation/free and TLB flush primitive bodies, page-table visitor
  callbacks, lower-level walk callbacks, address-translation primitive bodies,
  and fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=f60c57b101779395`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, and QEMU version/help/dry-run checks.
  Two initial validation failures were recorded in `kernel.log` and fixed
  before the clean validation pass. No real QEMU guest boot ran because no
  usable Rocky/RHEL-family qcow2 image was available from unprivileged paths.

Latest strict-core movement for the x86 set-range level-body batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +3 points: x86_64 memory management strict
  ownership moves 90% -> 93% because Rust now owns `set_range_l1/l2/l3/l4`
  leaf and level body orchestration: action dispatch, zeroed child page-table
  allocation, atomic page-table publication retry, existing child-table
  translation, child-walk callback dispatch, large-page map/store/RSS routing,
  child-walk failure shaping, and unconsumed child-table free sequencing.
- C still owns the public ABI wrappers, actual allocation/free and
  address-translation primitive bodies, child page-table walk callbacks, RSS
  primitive body, top-level `walk_pte_l4()` dispatch, and fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=a354b06dbddad942`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, and QEMU version/help/dry-run checks. No
  real QEMU guest boot ran because no usable Rocky/RHEL-family qcow2 image was
  available from unprivileged paths.

Latest strict-core movement for the x86 set-range side-effect batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +3 points: x86_64 memory management strict
  ownership moves 87% -> 90% because Rust now owns set-range existing-mapping
  conflict cleanup, page-table allocation-failure cleanup, L1/L2/L3
  map/store/RSS-accounting callback ordering, L2/L3 large-page success
  logging, and child-walk failure logging.
- C still owns actual `clear_range()` primitive effects, page-table
  allocation/publication, `virt_to_phys()`/`phys_to_virt()`, child page-table
  walk callbacks, RSS primitive body, leftover page-table free behavior, and
  fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=fd4909d0a758b83b`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation, no-warning
  scans over the captured build logs, and QEMU version/help/dry-run checks. The
  first equivalence attempt failed at the SIMD guard, was recorded in
  `kernel.log`, fixed by passing scalar values through ignored callback slots,
  checked with `objdump`, and rerun successfully. No real QEMU guest boot ran
  because no usable Rocky/RHEL-family qcow2 image was available from
  unprivileged paths.

Latest strict-core movement for the x86 clear-range side-effect batch:

- Broad dashboard movement is 0 points because x86_64 memory management is
  already capped at 100%.
- Strict-core movement is about +3 points: x86_64 memory management strict
  ownership moves 84% -> 87% because Rust now owns clear-range TLB
  flush-address queue mutation, old-PTE memobj-flush callback dispatch,
  anonymous-page free/RSS-sub callback ordering, file-backed page-unmap/free/
  rusage-sub callback ordering, XPMEM keep classification/log routing, and
  full-span L2/L3 child page-table PTE-null/free sequencing.
- C still owns actual `remote_flush_tlb_array_cpumask()`, `phys_to_virt()`,
  `ihk_mc_free_pages_user()`, `page_unmap()`, RSS primitive bodies,
  page-table walking callbacks, allocation/free primitive behavior, and
  fallback scaffolding.
- Validation passed the expanded equivalence suite with
  `x86_memory_helpers ok digest=05ab1d79d7050a92`, Rust-enabled image/module
  builds, C-fallback image build, build-only wrapper validation,
  `git diff --check`, script syntax checks, ownership-report dashboard gates,
  no-warning scans over the captured build logs, and QEMU dry-run command
  construction. No real QEMU guest boot ran because no usable Rocky/RHEL-family
  qcow2 guest image was available from unprivileged paths.

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

- Page-table allocation/free primitives, broader visitor/mutation traversal
  orchestration, broader page frees/RSS accounting, remote TLB shootdown
  primitive behavior, and map/free rollback.
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

Recommended next phase after stopping the full-port goal:

- Treat `full-port.txt` as complete and stop the full-port scoring campaign.
  Future progress should be reflected outside `full-port.txt`, primarily in
  `overview.txt` for broad/default-path ownership and in
  `rust-source-retirement.txt` only when a C implementation body is actually
  retired under that tracker's definition.
- Continue batching movement at least 2 aggregate percentage points at a time
  when updating percentages. If fewer than 2 points remain in a row, state that
  explicitly and verify the final smaller closure.
- Next concrete default-path user-tools batch: route the always-built
  `sched_yield` shared library through Rust in the Rust-enabled build while
  preserving the C fallback under `ENABLE_RUST_USER_TOOLS=OFF`, then pair it
  with another built user-tool slice such as additional `mcstat` output or loop
  control shaping so the outside tracker movement is at least +2. Validate
  Rust and fallback builds plus symbol/smoke checks before updating trackers.
- Do not count QLMPI (`qlfort`, `qlmpi`, `ql_server`, `ql_talker`,
  `ql_mpiexec_*`) or UTI syscall-intercept work in the current build unless a
  configured validation tree has `ENABLE_QLMPI=ON` or `ENABLE_UTI=ON`; the
  current known Rocky build trees have both disabled.
- Good retirement/default-path candidates after the first user-tools batch are
  built user tools and host/control-plane surfaces with bounded side effects:
  `mcstat`, `mcexec`, `mcinspect`, `eclair`, `ldump2mcdump`, IHK/mcctrl path
  formatting and validation helpers, and additional host-module preflight
  decisions. Avoid deleting fallback bodies unless the fallback requirement has
  been explicitly retired or the C body is no longer McKernel-owned logic.
- Continue to keep high-risk runtime mutation in C until direct runtime
  coverage exists: allocation/free, refcount mutation, lock/list mutation,
  page-table mutation, page I/O, procfs/sysfs IKC exchange, user-copy, process
  lifetime mutation, scheduler wake/context behavior, signal delivery, memory
  registration, and broad IKC exchange side effects.
- Validation for the next batch should include targeted formatting,
  `git diff --check`, `kernel/rust/tests/run_equivalence.sh` when helper logic
  changes, Rust-enabled builds for touched targets, C-fallback builds for the
  same targets, symbol checks proving the Rust-enabled path uses Rust helpers
  and the fallback path does not, and runtime smoke only through the approved
  non-reboot QEMU/guest path.
