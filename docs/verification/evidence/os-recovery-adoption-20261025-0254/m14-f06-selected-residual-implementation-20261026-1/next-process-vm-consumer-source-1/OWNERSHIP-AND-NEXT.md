Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private proposal closes one coherent selected consumer: the C
do_process_vm_read_writev entry and its thirteen adapters. The retained current290
object contains all fourteen allocated FUNC symbols; SELECTED-SYMBOL-PROOF.json
records only those exact lookups. The current Rust syscall read/write callers
already dispatch through the seven-argument C ABI to this entry. The central
paired selectors must add MCKERNEL_RUST_F06_PROCESS_VM_ENTRY only with
MCKERNEL_RUST_SYSCALL_POLICY_HELPERS, and f06_process_vm_entry_candidate in Rust.
No selector is enabled here.

The whole-file candidates preserve the current source outside two reversible C
guards and one Rust module declaration. The 5428-byte leaf is the existing private
consumer, unchanged. It calls the current canonical orchestration body with two
distinct stack nodes, the canonical thirteen-offset object, thirteen existing
typed adapters and the sole canonical logger. No logger, algorithm or offset
storage is duplicated. Disabling the pair restores the complete original C text.
The original helper-disabled C fallback is retained verbatim.

The entry borrows the CPU-local current thread synchronously. The find-process
callback returns under its hash reader lock; process_unlock releases that lock.
The current body takes the process update reader lock, checks exit state, obtains
the remote VM hold, drops the update/hash locks, and subsequently reads remote
credentials. The retained process_helpers source releases the owning process on
final VM destruction (process_release_vm_detach_process_result). This is the
existing ownership chain, not a new reference or proof of all concurrent paths.
Both stack nodes must remain distinct, correctly aligned and live through every
synchronous callback. No callback may retain either node.

Qualification remains open for this exact consumer. In particular, local iovec
descriptors are checked under the local VM range lock and later read after that
lock is released, just as in the current body. This package does not introduce
user-copy protection, a remote credential snapshot, a new process hold or a
final-reference repair. Preserve existing real MM/usercopy/fault/partial-copy,
current-stack and final-reference holds. Existing logger/offset and VM-lock
qualification must be reused at their original scopes; they do not qualify this
new public-entry selection by themselves.

The older next-process-vm-rw-source-1 packet has an ABI-facts C caller and early
invalid-argument comparisons, but explicitly has no executable driver. Therefore
there is no honest sealed compiler argv yet. The next ordinary fixture dependency
is a complete genuine-header C/Rust public-entry witness: assert both 64-byte lock
node layouts/alignment, all thirteen offsets, CPU-local current offset, and the
actual fourteen callback signatures; redirect CPU access only in the fixture.
Reuse the actual canonical body and compare the original C wrapper with this
leaf on invalid flags/counts and controlled local-range rejection. All later MM,
reference, fault and copy providers must be explicit inert fixture endpoints that
fail on unexpected invocation. This gives ABI/current-capture/local rejection
evidence only, not real cross-process copy or lifetime acceptance. Freeze the
complete fixture and exact input/tool/argv bindings before requesting CPU6.

No compiler, native workload, canonical write, acceptance change or shared policy
merge was performed. Dispatcher owns activation and the required later proofs.

VMlock192/ABI6 direct actual receipt remains unresolved: dispatcher confirmed
only the historical engineering-review summary is known. It supplies no new
acceptance here. NEXT-ABI-FACTS-COMMAND.json is one proposed compile-only argv
for the retained genuine-header ABI caller, using the retained complete C
profile. It has no link/run or invented driver; ordinary Root grant is pending.
