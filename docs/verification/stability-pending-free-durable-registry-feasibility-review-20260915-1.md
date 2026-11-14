# Pending-free durable registry feasibility review 1

Date: 2026-09-15
Task: `M03-pending-free-durable-registry-source-feasibility`
Reviewed commit: `ac28cafecfbfd5cfd933de3c5d0ec0b5004e1f89`
Disposition: `SOURCE_FEASIBILITY_ONLY`

This independent read-only source review does not endorse the dirty
`kernel/rust/mem_helpers.rs` candidate or the untracked rejected inventory
fixtures. It performs no build, test or execution and grants no integration,
runtime or production credit.

The smallest reusable host foundations are `OsRegistry::acquire` and
`begin_destroy` in `host-kernel/native-rust/os_registry.rs`, which provide
generation-checked OS lifetime exclusion; the published OS runtime and operation
mutex in `os_runtime.rs`; and `PreparedBoot::continuing`/`Started` in
`smp_memory.rs`, whose retained `Arc<Runtime>` owns the OS service and
`Arc<Memory>`. A separate transaction table could live under that durable owner.
The preallocated `Remote` slots and caller-departure quarantine in
`smp_application.rs`, plus the nonwrapping allocation pattern of
`application_rpc::Token`, are useful models rather than reusable identities.
Guest `hold_process_vm` retains a VM but supplies no VM incarnation or surviving
pending-free registry.

Production integration remains blocked:

1. `mcctrl_vm.rs::Mirror::clear` targets the current task's MM and rejects a
   different MM. An OS recovery worker cannot use it after launcher departure.
   Recovery needs an audited explicit-target-MM operation and lifetime policy;
   success must also address inherited PFN aliases.
2. `syscall.c::clear_host_pte` discards the returned error and
   `do_munmap_body_result` completes after removal/clear regardless. Removal,
   actual-MM clear, TLB completion and alias drainage must remain separate states.
   Failed or unknown clear must retain pending mode and backing. Only a typed,
   transaction-bound permit may authorize release.
3. `sysfs_zeroing.rs::Memory::zero` exchanges the head before fallible traversal.
   It cannot reconstruct an interrupted suffix. Complete trusted inventory,
   phase and progress must be durable before transfer, with exclusive bounded
   recovery and enumerable terminal quarantine.
4. Current ownership objects do not prove lifetime for every removed backing
   class. `RawPageOwnerRegistry` releases raw-address allocations in its
   destructor and cannot reject identical-address reuse, so it is unsuitable
   unchanged. The design must avoid VM/transaction reference cycles and leases
   whose only release path requires OS destruction.

Required identity joins authenticated OS slot/generation, a checked nonreused VM
incarnation, checked transaction serial, inventory arena/descriptor generations
and exact extent geometry. Completion binds that identity to operation and range.
Pointers, PID/TID, CPU-head addresses and physical addresses are attributes, not
identities. Restart additionally requires an epoch or proof that old messages
cannot survive.

A next private model packet is now specifiable for reserve/register, frozen
inventory attachment, owner abandonment, exclusive recovery, quarantine and
retirement. It must use opaque owned references, computed independent vectors
and negatives for exhaustion, stale identity, competing/interrupted recovery,
late completion and teardown refusal. It grants no real detach/free authority.
