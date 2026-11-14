# Bounded exec transfer prerequisite

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Prepared source only. No compiler/test/root/guest/census was run. Shared sources
and accepted gettid contract are unchanged. Private sources match the selected
released producer receipt; see SOURCE-BINDING.json. This is an implementation
blocker and reproducer, not a completed provider or native-cause observation.

The released mcctrl_process.rs450-508 routes live delivery transfers through
TID_TRANSFER. Released smp_application_syscall.rs292-343 checks the exact worker,
delivery, phase and request.tid_buffer; application_syscall.rs113 requires nr186.
Thus both supported exec phases reject before memory copy. Phase2 direction1
also rejects. This establishes source behavior in the selected module lineage;
no actual exec was observed.

A number-only exception cannot repair the provider. Phase1 sends descriptor plus
optional shebang argv to the four-page allocation in kernel/syscall.c7139-7157.
Request arg3 names that allocation but carries no size. Bound to its known16384
capacity, checked descriptor count/size and checked flattened argv, with exact
request physical destination. Phase2 names the exact descriptor in args1/args2;
it first reads that descriptor FROM_REMOTE and then writes multiple ELF pages
TO_REMOTE under the same delivery. Every section physical extent must derive
from that copied guest descriptor, be checked against retained OS extents and
be tied to its exact response, not from arbitrary launcher geometry.

The current native SyscallResponse has one payload: Option<(Tagged,u64,bool)>;
prepare_payload rejects a second claim, and Ledger.payloads[self.slot] holds
one tag until response publication (sysfs_memory.rs581,593-605,662-666). Mailbox
Call.transferred likewise rejects any second transfer. The accepted TID path
must retain those strict semantics. A separate exec transfer state must own:
(1) one exact descriptor claim and immutable validated section plan;
(2) bounded disjoint section claims, acquired atomically before publishing any
page byte, with rollback only before publication; (3) direction/phase and
per-page cursor, preventing duplicate/out-of-order/wrong-size transfers;
(4) all tags and mappings through original RET actual publication, cancellation
and uncertain close. Refactor ledger to store bounded per-response claim groups
or add a dedicated exec group indexed by exact response slot; never overwrite
its existing tag or release descriptor/pages after each ioctl. Reuse Memory
address/Span/tag/conflicts and ordinary Response/Completion release, not a new
raw physical mapping. Build phase2 plan only from the response-owned descriptor
read; keep its bytes plus section plan after user-copy failure. Preserve initial
image PREPARE ownership and TID_TRANSFER unchanged; a separate EXEC_TRANSFER
command is preferable to interpreting arbitrary running operations as exec.

Executable close remains independently owned by existing Process::replace and
must follow successful complete transfer. Bind the exec completion state to RET
so an incomplete sequence cannot publish success. Existing selected launcher
transfer_image catches a transfer ioctl error and breaks only the current inner
loop, eventually returning0 (selected source3376-3469). Do not trust that0 as
proof of all pages: native RET success must require the complete section cursor.
This existing launcher behavior also deserves a separate focused Rust correction
before native use, preserving the error and ensuring phase2 cannot close early.

Smallest next observation after root grants reusable CPU6 <=1GiB ordinary profile:
`rustc --edition=2021 --test actual_rejection_reproducer.rs -o actual_rejection_reproducer`
then `./actual_rejection_reproducer --test-threads=1` from this directory, with
root-selected pinned compiler/private fresh output and captured stdout/stderr.
The reproducer compiles complete receipt-bound Request/Delivery/Mailbox bodies;
only allocation/response storage providers are substituted. It expects the
current rejection and exercises strict successful TID plus negative delivery,
span,length,direction and duplicate checks. No provider acceptance follows.

Stop condition reached: multiple retained claims and transfer-completion ownership
need focused independent review before a safe implementation; no unsafe partial
host patch prepared. One failed candidate plus one bounded correction per family
before escalation; no candidate has yet executed in this lane. Root owns grants,
integration, all execution, review, Git and acceptance. SDK66 capacity gate stays
unchanged; no bypass, resizing, or full-module compilation is promised.
