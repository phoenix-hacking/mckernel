# Guest/host invalidation ownership review — 2026-09-13

Status: **SOURCE REVIEW; FAILURE CONTRACT OPEN; NO STALE WRITE REPRODUCED.**
This lane changed no production source and ran no compiler, container or guest.
It refines the concern in `ultra-guest-review-20260909.md:306` and the closure
requirement in `ultra-handoff-gates-20260909.md:44`. It grants no new execution
or capability gate. Root owns the continuing eight-suite baseline and actual
transport-fault builds/guests.

The concrete defect is the guest's handling of an unsuccessful host clear:
normal `munmap` discards that error and unconditionally drains its pending-free
batch. Guest range metadata is removed before the host operation, but tracked
physical pages are deliberately held while the offload is outstanding. Saying
that all backing is immediately freed before the host operation would be
incorrect. The unresolved safety question is what backing or alias can remain
host-accessible when an unsuccessful offload returns and that batch is freed.

The native host already retains the exact worker, Mirror and completion during
its MM operation, performs a two-pass VMA preflight under the Linux MM write
lock, and carries the actual clear result into the private completion. These
properties must survive a repair. They do not make a failed clear successful
or protect backing after the guest ignores its returned error.

## Source binding

References below are to HEAD `9326d8e616962eb974d30a63b9a8ea83917caf47` and
these freshly read inputs, including the integrated H04 service repair.
Paths beginning with `native/` in the prose mean `host-kernel/native-rust/`.

| Input | SHA-256 |
| --- | --- |
| `host-kernel/native-rust/mcctrl_vm.rs` | `74facf8daac2d3843e2c7c862b7186c8d738d7a78573ac0f1e6ea81436da470d` |
| `host-kernel/native-rust/mcctrl_process.rs` | `392391cc1db8eaf8d26283ca77a7d69150a0bbf026dfd01120970d7fd601a925` |
| `host-kernel/native-rust/smp_application.rs` | `c63a0179a648b0ab90c09c55cf5462779de12937cd5fa2dfa461e34ea29f94a0` |
| `host-kernel/native-rust/smp_application_syscall.rs` | `4118de1401f33b2df17393660e6acbce2f337dca8a9cdfcf10965b1d3dc84c55` |
| `host-kernel/native-rust/smp_service.rs` | `0747b5dbc7a529282c3073294e9ed7f121da927c59923a60455bc6f6aa610478` |
| `kernel/rust/syscall_policy.rs` | `5e770e3375c7eb2f6f5aae23863a961123b5f200c77662780cb04a90dc13bf53` |
| `kernel/rust/mem_helpers.rs` | `35b25b1d67c86ba07a84b308a049806b25eaca4c6e34f2f1a631b6271bce6322` |
| `kernel/rust/process_helpers.rs` | `b3a28ea8b0cd2594305644c224ae718eac384c0709305da315a6b8fd1285d00b` |
| `kernel/syscall.c` | `ac80bb17e41979652e3dd90f8a94d205c28853cd6171975fcf4349f3d301ab58` |

Linux implementation references use the pinned local source directory
`/home/holden/mckernel-work/scratch/native-source/linux-6.12.0-211.44.1.el10_2`:

| Linux input | SHA-256 |
| --- | --- |
| `mm/memory.c` | `e97329a3efcf33701c9afb55cbb0f44b500336a4963ba6590d9d79bf9af02650` |
| `mm/madvise.c` | `8cf443a1397ae11dc63a9db0b54a3881a435517c5a523ee621baf49b332ff6bc` |
| `kernel/fork.c` | `a0dd38fbb599576c8cfcaaffbf556dca11ac24d9ca400047c0a78d1d51f44120` |

## Guest ordering and the failed-return gap

`kernel/syscall.c:5540` through `:5588` supplies the real begin, range-removal,
host-clear and finish callbacks to `do_munmap_body_result`.
`kernel/rust/syscall_policy.rs:4252` holds `vm.memory_range_lock` for writing
across the ordinary `do_munmap` call. Its selected body at `:4302` does this:

1. Begin the current CPU's pending-free batch.
2. Remove the guest ranges, recording the removal result and `ro_freed`.
3. Outside the existing straight-mapping exemption, clear the host PTEs if
   removal failed or `ro_freed == 0`. That callback returns **void**. Otherwise
   call `set_host_vma`, which returns a result.
4. Finish the pending batch unconditionally, then return the chosen error.

The selected C bridge `kernel/syscall.c:5476` explicitly casts the result of
`clear_host_pte_body_result` to void. The Rust helper at
`kernel/rust/syscall_policy.rs:4357` returns the actual delegated error and
logs it; it also publishes the held-range-lock CPU flag before forwarding and
restores it afterward. The error is lost at the public bridge and its void
callback, not in the native host's MM result calculation. The C fallback at
`kernel/syscall.c:9426` and `:9473` has the same sequence and discarded result.

For the common successful removal with `ro_freed == 0`, an unsuccessful host
clear can therefore be followed by a successful `munmap` return and allocator
release. The native `ro_freed != 0` path already returns the host clear error
through `set_host_vma_body_result` (`syscall_policy.rs:5581`), but still drains
the pending batch. Merely changing the void bridge to return an errno cannot
establish safe retention on either path.

Removal itself is not an atomic reversible edit.
`process_remove_memory_range_body_result` (`process_helpers.rs:4752`) can
split/remove earlier ranges before a later allocation or callback fails.
`process_free_memory_range_body_result` (`:3956`) changes guest PTEs under
`page_table_lock`, runs backing-object reference operations, and finalizes
the range. `process_free_range_finalize_result` (`:3786`) erases the rbtree
node, clears caches, may release straight backing, and frees the range object.
The caller cannot safely put the original range pointer back on an error.

### What the pending-free list actually owns

`kernel/mem.c:3827` returns the **per-CPU** `pending_free_pages` head.
`mem_begin_free_pages_pending_result` (`mem_helpers.rs:3829`) requires its
`next` pointer to be null, then initializes the list. An already active list
is an error that the public begin path treats as a panic condition.

`mem_free_pages_pending_enqueue_result` (`:3899`) records the page's physical
identity, page count in `offset`, and `PM_PENDING_FREE` mode, then links it to
that list. `mem_finish_free_pages_pending_result` (`:3926`) validates the mode,
unlinks each page, calls the real allocator free callback, and resets the
head to null. `mem_mckernel_free_pages_body_result` (`:4648`) goes directly to
the allocator when a tracked page/pending list cannot be used. Thus the batch
provides a specific delayed-free mechanism; it does not prove retention of
every shared, remote, device, huge-page, straight, memobj or XPMEM owner.

Skipping `finish` on failure is not a valid quarantine implementation. It
leaves a CPU-global active head, so the next begin can panic and unrelated
frees can join that old list. Moving its raw head without reanchoring the
intrusive list would also leave links pointing to the wrong owner. A repair
needs an explicit durable owner and a verified handoff/reset of this transient
list. Its scheduler, preemption and CPU-migration contract must be established
for the entire begin/remove/offload/finish interval before changing it.

XPMEM shares this mechanism: `kernel/xpmem.c:6183`, `:8600`, and
`kernel/rust/xpmem_helpers.rs:1596` begin/remove/finish their own batch. They
must be included in any change to list ownership or nesting semantics. This
review does not claim that those XPMEM mappings currently share the native
Mirror, or that their separate invalidation protocol has been verified.

## Native operation, result and retained owners

| Stage | Exact source | Established contract and limit |
| --- | --- | --- |
| Worker acquisition | `native/mcctrl_process.rs:123`, `:207` | A retained `HostWorker` has stable process identity and an Arc-owned Mirror. The current MM must match before use. The invocation retains its Registration. Numeric worker/TID values alone are insufficient identities. |
| Begin clear | `native/mcctrl_process.rs:235`; `native/smp_application.rs:784`; `native/smp_application_syscall.rs:359` | Kernel-only CLEAR validates nr 11, checked aligned nonempty range, exact worker and delivery, then reserves the call as in-kernel work. A rejected, unaccepted begin rolls back the WAIT copy. |
| Actual MM clear | `native/mcctrl_vm.rs:212` | A transient current `mm_users` reference and the exact Mirror identity cover range validation, two VMA passes and PTE clearing. No application/transport lock spans the MM operation. |
| Finish clear | `native/mcctrl_process.rs:254`; `native/smp_application_syscall.rs:375` | The actual completed `Mirror::clear` result is 0 or its negative errno. CLEAR_DONE always finishes the reservation after that operation, including an actual MM error. Accepted completion is not retried by rerunning the MM operation. |
| Concurrent close | `native/smp_application_syscall.rs:425`, `:636` | While `call.kernel` is set, cancellation is deferred and the response is retained. Finish may publish cancellation `-512` instead of the actual MM value when close won. Record both actual value and completed value. |
| Completion publication | `native/smp_application.rs:807` | The kernel wait is for the exact worker/delivery to be returned through real publication; the condition wait releases slots. An accepted result is not proof of published status or guest consumption. |
| Terminal transport state | `native/smp_application_syscall.rs:517`, `:654` and the integrated H04 transition | Quarantine rejects further completion and retains owners; an accepted waiter can return `-71`. A retained response does not prove Linux PTEs were invalidated. |

`Mirror` retains a structural `mm_count` identity, not a long-lived `mm_users`
reference (`mcctrl_vm.rs:31`, `:48`, `:95`). A transient `CurrentMm` provides
the latter only during an operation and balances it with `mmput`. This avoids
an MM/VMA/file owner cycle. MappingFile retains the Mirror and Registration
through the VMA's live file; final file release drops those owners. Do not add
a persistent `mm_users` reference to a VMA-owned object as a retention fix.

The separate `clear_user_space` ioctl (`mcctrl_process.rs:516`) clones the
Mirror under the mapping mutex and calls `clear` after dropping that guard.
It propagates the actual error. It does not own or drain a guest pending-free
batch, and cannot substitute for the CLEAR/CLEAR_DONE delivery transaction.

The current `host_mapping=invalidated ... value=... completed=...` log is
emitted even when `value` is negative, and before completion publication.
An oracle must parse both results and publication/consumption evidence; the
word `invalidated` alone is not success evidence.

### Lock order and why operation reversal is insufficient

On the guest, ordinary munmap holds the memory-range write lock, takes the
page-table lock for PTE mutation, releases the page-table lock, then delegates
the clear while retaining the range lock. The held-range-lock CPU flag has
specific guest remote-fault consumers (`process_helpers.rs:2462`, `:2485`);
it is not a general replacement for either lock.

On the host, CLEAR begin takes and releases application slots. The worker then
takes the current MM's Linux `mmap_lock` for writing without slots/transport
locks. After releasing that MM lock, CLEAR_DONE takes slots and waits through
a condition variable that drops slots. The existing worker/Mirror ownership
spans these nonoverlapping lock scopes.

Linux faults retain their locked live VMA/file while `lookup_fault`
(`mcctrl_vm.rs:292`) invokes application LOOKUP. LOOKUP takes application
slots through `with_prepared` and reads guest page-table words through the
memory ledger (`smp_service.rs:913`), then returns a PFN for installation
(`mcctrl_vm.rs:326`). It does not take the guest's memory-range or page-table
lock. The Linux MM write lock waits for in-flight fault readers before zapping
their PTEs. Therefore a new repair must not acquire the Linux MM write lock
while holding application slots: faults already establish the opposite order.

Clearing host PTEs before removing the guest PTEs is also insufficient. A host
fault could reload the old still-valid guest PFN between those operations.
The existing revoke-guest-PTEs, then serialize/zap-host-PTEs ordering has a
purpose. A durable failure owner must retain backing through this order and
prevent refault/reuse after failure; moving one call is not that owner.

`Mirror::clear` preflights all VMAs before its apply pass under the same write
lock. Declared errors come from geometry, current-MM or VMA/identity checks.
The actual `zap_vma_ptes` API returns void. Pinned Linux `mm/memory.c:2033`
requires a wholly contained VM_PFNMAP interval and otherwise returns without
zapping; successful execution uses the page-range zap and TLB drain. The
Mirror originally installs VM_PFNMAP, but its clear preflight does not recheck
that flag. An eventual invariant audit should establish its persistence or
check it before reporting success. This review has not shown a supported
ordinary userspace operation that removes that flag from this VMA.

Do not label a synthetic injected post-zap errno as an actual partial Linux
zap failure: the current API does not expose such a result. Distinguish real
preflight failure, completed zap followed by failed completion publication,
and an explicitly instrumented simulated failure boundary.

## The phase distinction that acceptance must preserve

| Observed outcome | What can be concluded | Required unresolved owner proof |
| --- | --- | --- |
| Clear outstanding before MM work | The exact host delivery may be reserved; captured guest pages remain pending. | Entire affected guest backing class and retained VM/range identity; no reuse before resolution. |
| MM operation active during close | Native kernel reservation defers cancellation and keeps its response. | Current MM/file and backing remain alive until MM work and any aliases drain. |
| Actual clear error accepted, response not published | Negative result and accepted response prefix may exist; guest has not necessarily resumed. | Original response/ledger serial and pending backing retained; accepted bytes differ legitimately from their pre-completion snapshot. |
| Actual clear error published and consumed | Guest may resume and currently calls unconditional finish; common munmap may return 0. | This is the central missing retention/failure contract. Record actual guest errno, freed physical identities, host PTE state and any later allocation. |
| Successful zap, later publication/notify failure | Original-MM PTE invalidation can have succeeded independently of transport failure. | Distinguish prepublication retained response from postpublication release; establish guest consumption and alias scope separately. |
| Terminal protocol failure with guest still blocked | H04/quarantine may retain response and prevent guest consumption. | No claim that backing was freed merely from a host errno, or that ownership is safely releasable merely from no task/procfs node. |

## Other callers that must join the contract

| Caller | Existing behavior that a repair must handle |
| --- | --- |
| Ordinary munmap | `syscall_policy.rs:4252`: holds the range write lock and returns `do_munmap`'s error. The void clear error is presently absent. |
| MAP_FIXED replacement | `kernel/syscall.c:5962`, `:5974`: calls `do_munmap` under the range lock, then installs new backing if it reports success. A propagated error stops this invocation, but a durable range reservation is still needed to block later reuse through another mapping call. |
| SysV shared-memory detach | `syscall_policy.rs:4460`: `shmdt_body_result` calls the same `do_munmap` for the exact shared range under the range write lock. Shared backing/reference ownership needs its own explicit coverage. |
| Whole-address-space teardown and exec | `syscall_policy.rs:4390` logs each `do_munmap` error, continues, frees remaining ranges and resets map bounds. `kernel/syscall.c:7183` then prepares a new image; `:7209` discards another whole-space clear result. Once old ranges are gone, exec cannot return to the original image by simply propagating an errno. |
| Native mprotect / read-only removal | `syscall_policy.rs:5581` already returns the actual host clear result with held-lock flag restoration. On failure, changed guest permissions and old cached host permissions still require a safe transaction/terminal policy. Preserve the existing partial-range first-error handling. |
| remap_file_pages | `syscall_policy.rs:6338` calls the void clear callback after successful remapping and can then populate pages. `kernel/syscall.c:25443` supplies the bridge. Backing may already have changed; the same-VA transition needs retained old ownership or proved exclusion. |
| XPMEM and non-native selections | They use the same pending-free primitives but have separate ownership and forwarding assumptions. Preserve the legacy C/Rust behavior until an explicit equivalent transaction contract is reviewed; native success cannot silently grant those capabilities. |

Return-type changes cross real C/Rust ABIs: `kernel/include/syscall.h:628`,
`kernel/syscall.c:591`, `:671`, the bridges and C fallbacks, and Rust
`DoMunmapClearHostFn` / `RemapFilePagesClearHostFn` at `syscall_policy.rs:889`
and `:982`. Existing equivalence fixtures must be updated with independently
expected behavior for each selection, not replaced with matching mocks that
erase the error.

## Inherited host PFN mappings are a separate closure dependency

The native Mirror sets VM_PFNMAP, VM_DONTEXPAND and VM_DONTDUMP
(`mcctrl_vm.rs:264`); it does not set VM_DONTCOPY or VM_IO. Its mmap callback
checks the initial MM identity, and later fault callbacks reject another MM.
Those checks do not prove that already-populated PTEs cannot be inherited by
a Linux fork. Pinned Linux `mm/memory.c:1346` explicitly requires copying for
PFNMAP VMAs; `copy_page_range` at `:1380` and `:1400` tracks/copies those pages.
`kernel/fork.c:666` skips a VMA when VM_DONTCOPY is present. A child with an
already present PFN need not trigger the rejecting fault callback, while
`Mirror::clear` only zaps the originating MM.

This is a source-bound alias concern, not a reproduced child stale write.
It does not assert guest fork support: that separate capability remains
closed. Existing Linux controller forks or stale-ID reaps do not prove the
populated-PFN inheritance property.

Adding VM_DONTCOPY alone would leave an incomplete enforcement claim:
pinned Linux `mm/madvise.c:1292` allows MADV_DOFORK to clear that flag unless
VM_IO is set. A correct design must either enforce a reviewed no-inheritance
contract across applicable madvise/VMA operations, or retain and invalidate
every inheriting MM alias. Adding VM_IO has behavior/driver/GUP implications
and is not proposed as an unreviewed one-line repair. The alias choice is a
prerequisite for claiming that original-MM clear success authorizes release
of all potentially host-visible backing.

## Minimal correct candidate design and why no patch is attached

There is no source-supported small patch that establishes the full lifetime
contract today. The following is the smallest transaction design to develop
and independently review; it is a work queue, not a claim of implementation.

1. Define the backing/alias scope first. Select supported anonymous/ordinary
   file cases and account for every page, memobj/pager reference, straight or
   external mapping they can release. Reject an unsupported transition before
   mutation rather than silently relying on the pending-page list. Resolve
   the host-inheritance policy above.
2. Allocate a persistent VM-owned invalidation transaction before irreversible
   guest edits. It needs a nonreused identity, exact affected VA intervals,
   backing references and two distinct result fields: first guest mutation
   error and actual host operation/completion outcome. Allocation failure must
   leave the old mappings intact. A range reservation/tombstone must prevent
   later placement, MAP_FIXED replacement, exec replacement or fault refill
   from treating an unresolved interval as free.
3. Revoke guest PTEs under existing range/page-table ordering, capture every
   detached owner including partially changed ranges, and transfer pending
   page links to that durable transaction with correct intrusive-list
   reanchoring. Reset the per-CPU transient head on every handoff. Establish
   no nested batch, unrelated-free capture or CPU migration before changing
   this mechanism; XPMEM users are part of that audit.
4. Delegate the actual host clear through the existing exact worker/delivery
   reservation. Retain native MM ownership and perform MM work outside slots.
   Do not hold a new guest page-table lock across forwarding, acquire a host
   MM lock under slots, or use an indefinite lock hold as failure retention.
5. Commit allocator/reference release only after the required actual clear
   and alias-drain outcome is proven. On failure, move the transaction to a
   named unresolved/terminal state that retains all backing and VA exclusion.
   Error return alone, skipping finish, an unreachable leak or a manufactured
   successful result is insufficient. Recovery or terminal retirement must
   have a real bounded owner-drain path before release; do not invent one by
   treating loss of a process ID as loss of every MM/PFN reference.
6. Apply the result/terminal policy to munmap, MAP_FIXED, shmdt, mprotect,
   remap_file_pages and whole-VM exec/exit teardown. Preserve first-error
   semantics without hiding a later failed clear. After destructive exec
   work, use a defined process-local terminal path with retained old owners;
   a bare errno cannot restore the old address space.

An implementation question remains concrete: which existing or new VM-owned
object will retain the intrusive pending batch, detached range/backing refs
and VA exclusion across failed offload, and what exact event proves all host
aliases are drained? This review found no current object satisfying all those
requirements. Preparing an errno-only candidate would obscure that missing
contract, so no candidate patch is attached and production stays unchanged.

## Independent validation needed for closure

Existing `scripts/tests/fixtures/native-application-syscall.rs:1179`, `:1199`,
`:1247` and `:1280` cover request geometry, exact reservation, supplied errno
values, 1,024 queue-full callback retries, cancellation and kind separation.
They establish mailbox behavior. The test named
`invalidation_reserves_only_exact_delivery_and_preserves_real_mm_result`
supplies its values directly; it does not execute `Mirror::clear` or Linux MM
mutation. The ordinary memory baseline exercises successful host clears, not
the failed-clear backing contract. Historical evidence remains unchanged.

Before a production candidate, add exact-method, independently specified
transaction tests for successful commit, actual negative host result, partial
guest removal, allocation failure before mutation, duplicate/stale completion,
close while MM work is active, failed publication, per-CPU batch reset and
rejected conflicting VA reuse. Test the original C selection where shared ABI
surfaces change. Do not count callback-injected errors as actual MM faults.

Actual closure requires fresh bounded guests with frozen source/module/image
and controller identities, complete logs and independent ownership evidence:

| Scenario | Required observation |
| --- | --- |
| Ordinary success and same-VA replacement | Populate the old host PFN using delegated access, remove the guest mapping, prove host PTE/TLB invalidation, then map different backing in the test's own reserved VA interval and verify independent sentinels. Keep the original memory smoke and eight-suite regression intact. |
| Real preflight failure | Produce a reviewed hole or foreign later VMA inside an interval owned by the test, without arbitrary address mutation. Exercise the actual `Mirror::clear` preflight, record its negative errno, and prove earlier valid segments were not zapped by the preflight pass. Observe retained old backing and forbidden guest reuse. Wrong-MM coverage must use an actual valid invocation path; rejection before `Mirror::clear` is a different case. |
| Successful zap, blocked/failed publication | Pause at an observed boundary after actual MM work. Prove the original MM PTE result separately from accepted prefix, response status, physical queue ownership and guest consumption. Compare the accepted response prefix with its own post-acceptance snapshot, not the pre-completion bytes. |
| Close/SIGKILL during MM work | Preserve the actual worker start identity, Mirror/MM identity and kernel reservation, then prove deferred cancellation. Record actual clear value and completed `-512` separately. Retain pending guest backing until the defined transaction outcome. |
| Partial guest edit and clear failure | Force a later guest split/edit failure after an earlier mutation; record both errors, all changed intervals and all detached owners. No missing interval or list reset may be inferred from an empty procfs tree. |
| Host alias inheritance | Independently inspect an actually populated Mirror across Linux fork, including MADV_DOFORK behavior under the selected policy. Establish blocked inheritance or complete child-MM invalidation before enabling a reuse test. This grants no McKernel fork/COW credit. |
| Recovery or terminal retention | At terminal and at least five host-monotonic seconds later, require stable complete owner inventories, no accesses through released original identities and the specified VA exclusion. Only an actually recovered safe OS may run the established eight HELLO repeats. A permanently quarantined OS is not forced through recovery. |

The current typed native owner observer is useful for application/mailbox,
ledger and pager owners, but it does not enumerate guest pending-page lists,
detached VM ranges or Linux MM/PTE aliases. Extend observations to those actual
owners with generation/transaction/physical-page identities and explicit
completeness. A response ledger serial cannot substitute for a guest backing
allocation identity. Never inspect response bytes after publication; use the
original serial's access/release counters for later lifetime evidence.

Use the existing serialized four-CPU/12-GiB guest limits and reviewed local
timeouts; stop on the first unexpected result and preserve the original
capture. Begin each failure placement in a fresh guest. Select fixed finite
repeat counts in the reviewed execution packet; this review authorizes no
open-ended stale-write stress. First establish the failure owner, then test
its drain/reuse contract, and only then broaden VM/application functionality.
