# M14 GET_CRED guest-physical mapping prerequisite

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source analysis; no implementation, guest or host execution. Hashes of
all inspected workspace sources are in `SOURCE-SHA256.txt`. These are current
workspace bytes, not a claim that each is selected in an accepted image.

## Observed producer and consumer

`kernel/syscall.c` getcred (around 19750) and its Rust `getcred_body_result`
(`kernel/rust/syscall_policy.rs` around 2199) select 8 C `int` slots from a
16-int caller scratch area so the selected 32-byte virtual span stays within a
page. They send its physical address in `args[0]` using `__NR_setfsuid`, with
`args[1] = 1`, and ignore the return from the synchronous request. Rust getcred
explicitly documents that this does not prove a producer initialized the output.
The proof that the selected physical span belongs to a live request and that
virtual-to-physical mapping yields the same page must be retained at runtime.

In legacy `executer/user/mcexec.c` around 8569, the special setfsuid branch
invokes `MCEXEC_UP_GET_CRED` with that physical argument, ignores the ioctl
return, sets `ret=0`, and completes the syscall. Its helper at 2782 also has a
void return. `executer/kernel/mcctrl/control.c` at 3212 uses `phys_to_virt(phys)`
and writes eight 32-bit values directly: uid, euid, suid, fsuid, gid, egid,
sgid, fsgid; it has no separate mapping/unmapping lifetime. This is the original
behavior, not a safe general authority to write arbitrary physical RAM.

Current Rust `mcctrl.rs` registers GET_CREDV only; GET_CRED is listed as a
service command but falls through to EINVAL. `mcctrl_exec::credential_values()`
reads the current task's immutable Linux credential and supplies the eight raw
32-bit IDs. Its `credentials()` writes a Linux *user virtual* `UserSlice` for
GET_CREDV and is not an implementation for a guest physical GET_CRED argument.
The host current task must remain the actual servicing task when values are
sampled; image-prepare's existing credential vector is not a later refresh.

## Reusable mapping and lifetime evidence

- `smp_resource.rs:58` defines `OsToken` as exact `(slot,generation)` and
  `from_ihk_lease_v2` requires a genuine lease/module owner; arbitrary integers
  are not authority. `os_runtime.rs:1821` shows a concrete scalar-only model:
  generation resolve and lease, operation lock, admission owner, Ready/Running
  validation, then synchronous backend callback. Its exported topology ABI
  accepts only CPU/node queries and cannot write memory.
- `smp_memory.rs:765` `checked_guest_bytes` checks nonzero address/length,
  overflow and identity-window/direct-map bounds, and a whole range contained
  in one extent owned by that exact token. It returns a raw pointer, not a
  lease or exclusive capability. The `MemoryContext` and `PageOwner` retain
  original allocation ownership under a sleepable mutex (`smp_memory.rs:295`,
  `1513`). `write_image_range` at 1978 splits at physical allocation boundaries;
  logical extent continuity alone is not one Rust allocation. For GET_CRED,
  show 32 bytes fit a single 4-KiB physical page and that the original retained
  PageOwner covers it; never infer that proof from an extent alone.
- `sysfs_memory.rs:187,275` `Memory` carries exact owner, retained extent
  snapshot and shared ledger; `Memory::new` explicitly requires Started
  BootStorage and original page/module owners to outlive every view.
  `Memory::syscall` at 479 validates and claims an actual response. Its private
  `SyscallResponse::prepare_payload` at 906 reserves an exact disjoint payload
  tag and `pager_copy` performs bounded volatile byte writes while the real
  mailbox reservation excludes completion/cancellation. Final
  `ResponseMemory::release` retires the tag after actual final publication.
  These primitives are internal, currently tied to other protocols, and do not
  authorize enabling held TID, exec or transfer paths.
- `os_runtime.rs:1321` runs mcctrl service callbacks with the file's OS lease and
  resident admission owner but deliberately without the OS operation lock.
  Its existing `OsBackendIoctlV2` carries user arguments, not a kernel-buffer
  guest-memory write ABI. No public credential-specific guest-write export was
  found in the examined interfaces. `Memory::application_copy` is a scoped
  prepared-image operation and is not itself credential request authority.

## Concrete candidate boundary and open proof

A bounded implementation would snapshot eight credential `u32`s on the actual
servicing task, then use a new, versioned synchronous IHK-to-SMP credential-write
callback carrying `(slot, generation, original-delivery identity, physical,
exact 32-byte kernel-owned input)`. IHK must resolve and lease the exact OS and
retain admission/module owners; SMP would validate the current boot epoch,
actual request and exclusive writable 32-byte claim, use the existing extent
and physical-allocation checks, and copy while all owners/claims remain live.
No bare pointer, ledger snapshot or user-chosen scalar may escape this operation.
Reuse `SyscallResponse`'s ledger/payload approach only if the actual original
response/delivery is genuinely bound; do not dispatch held protocol variants.
The existing V2 backend ioctl cannot silently be repurposed to accept a kernel
buffer. The ABI version, strict errno contract, lock order and callback lifetime
need an independent review before implementation or exposure.

Unresolved facts that prevent treating this as an implemented port:

1. GET_CRED's current ioctl supplies a physical scalar but does not expose an
   authenticated original worker/delivery/response capability to the service.
   Show the actual association, caller/guest ownership and non-aliasing against
   response, queues, fixed structures and any live claims; or design a narrowly
   reviewed equivalent owner.
2. Prove OS lease/admission, boot epoch and retained PageOwner continue across
   the write and concurrent shutdown, and that OS-operation/CPU/memory/ledger
   ordering cannot deadlock. An owner snapshot by itself is not a physical lease.
3. Bind the actual kernel ABI sizes, alignment, endian and compat behavior;
   validate the whole original 32-byte span and exact physical allocation.
4. Establish real request/cancellation and memory-order completion: all eight
   writes must happen before guest-visible successful completion, and a failed
   mapping/claim must never be acknowledged as initialized credentials. Both the
   legacy host branch and guest helper currently ignore an error; the existing
   status/ACK pathway and any necessary compatible repair require independent
   functional review. No output may be zero-filled or a failed request counted
   as success to mask this gap.
5. Verify exact production-selected modules, bindings, link and matching runtime
   behavior after the separately reviewed release. No native or C-retirement
   credit follows from this prerequisite analysis.
