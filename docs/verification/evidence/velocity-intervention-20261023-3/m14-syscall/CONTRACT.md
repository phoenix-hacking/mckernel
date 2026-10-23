Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private M14-F03 / M14-03-05 slice replaces exactly one remaining substantive
C implementation: `syscall_signalfd_publish_bridge`, originally
`kernel/syscall.c:19870`. Its allocation, zeroing, locked prepend/find, mask copy,
error returns and return reload move to Rust. The existing Rust `sys_signalfd4`
and `signalfd4_body_result` are reused unchanged and receive no new-port credit.

`candidate.patch` is the integration artifact. It adds the exact same exported
callback symbol in `kernel/rust/syscall_policy.rs`, removes its now-redundant Rust
extern declaration, and selects it through the already-supported
`MCKERNEL_RUST_SYSCALL_POLICY_HELPERS` default. The original C body is unchanged
inside the inverse guard for C fallback builds. No CMake, shared ABI, Linux
forwarding, quarantine or bypass change is needed. `patched/` holds review copies;
canonical sources and the current image are untouched.

`source-bindings.json` binds snapshots of the canonical C/Rust sources and ABI.
The original callback is byte-identical to the exact materialized source named
in the selected M14 inventory. Current selected defines include
`MCKERNEL_RUST_SYSCALL_POLICY_HELPERS`; this is a live callback called by the
already-selected Rust `sys_signalfd4`, rather than a dormant C syscall wrapper.
The existing syscall table entry and Rust export remain the next real consumer.

ABI and ownership contract:

- C ABI stays `long (void *thread, int fd, const unsigned long *mask, int create)`.
  This supported x86_64 profile has signed 64-bit long, unsigned 64-bit mask,
  32-bit int and pointer-sized pointers. Every nonzero create value means create.
- The caller supplies a valid live Thread and its Process, and a readable kernel
  mask word with no overlap with descriptor data. In the actual consumer the
  mask is the existing local copied by `signalfd4_body_result`. The callback does
  not retain thread/mask references. Thread/process and the selected descriptor
  remain live through the final post-unlock fd reload, matching the C caller
  requirement. No Rust shared/exclusive references to those objects are created.
- Existing `abi::{Thread,Process,Mckfd}` layouts are reused. Accessed offsets are
  thread.proc=4304, process.mckfd_lock=1284, process.mckfd=1288,
  mckfd.next=0, fd=8, data=16, size=80. Rust's Mckfd.padding occupies the existing
  C sig_no slot at12; the whole new object is zeroed exactly as in C. No field is
  repurposed and no shared ABI delta is proposed.
- `abi_witness.c` supplies an independent real-kernel-header check for the
  integrator's exact supported compile environment. It has not yet been compiled.
  The host fixture imports the actual unchanged Rust ABI, and its unchanged C
  body uses deliberately minimal fixture-only thread/process views. Therefore
  host equivalence alone is not an independent production C layout witness.
- Create first calls the existing `syscall_alloc_bridge` with size80 and
  IHK_MC_AP_NOWAIT=2. Allocation failure returns -ENOMEM with no lock or list
  mutation. Success zeroes all80 bytes, stores fd, locks the existing process
  spinlock, prepends the new descriptor and copies exactly8 mask bytes to data.
  The existing allocator thunk retains tracked allocation behavior; its existing
  debug file/line callsite replaces the original callback allocation callsite.
- Update acquires the same lock, chooses the first matching fd and changes only
  its8 data bytes. Missing descriptors, including empty lists, unlock once and
  return -EINVAL. No allocation, host call or list rewrite occurs on update.
- Both successful paths pass the exact returned long IRQ state to the same unlock
  callback once, then reload and return the descriptor's fd. Mask bits above the
  signed-long range remain byte-identical. There is no new validation/error path
  for arguments the original callback assumed valid.
- Linux creation/copy/flags/syscall ordering remains in the existing Rust body.
  In particular, host create errors propagate unchanged; a local allocation
  failure after a successful host create still returns -ENOMEM without inventing
  a compensating close. This slice preserves that original behavior.

Focused fixture and admission:

`fixture.rs` compiles the new body literally and includes source-extracted,
unchanged `sys_signalfd4`, `current_thread_ptr`, `signalfd4_body_result`, size and
flag helpers. C reference compilation includes the original callback literally;
preprocessor renaming only connects its allocations/locks to ordinary host mocks.
Direct vectors compare return, order, normalized list links and all descriptor
bytes. Consumer rows execute the actual selected Rust sys_signalfd4 with the new
callback; the reference uses the unchanged body-result with the original C
callback. Host create and usercopy callbacks check their real arguments and
record ordering. The fixtures assert IRQ preservation, balanced locks, process
and thread immutability outside the owned head, full-zero creation and failure
paths.23 cases cover empty/nonempty prepend, first duplicate/interior update,
missing/negative fd, noncanonical true, high mask bits, allocation failure,
post-unlock reload, host failure, supported/invalid flags, copy errors, wrong
sigset size, null mask/context/thread and allocation failure after host creation.

The fixture is executable-ready, but no compiler or test has run without a fresh
ordinary slot grant. Execute only `run_fixture.sh --ordinary-slot-granted` under
an actual parent-relayed CPU6/CPU0 profile. It creates a fresh, non-overwriting
`fixture-attempt-1/` and retains compiler/runtime logs. One candidate and any one
bounded correction must remain separately retained; no auto-retry is authorized.

After focused PASS, root owns integration, exact production ABI/selection and
unique symbol attribution, final linking and native signalfd create/update/use/
close plus same-session descriptor/process resource-restoration proof. A new
fixture PASS does not retire this path in the accepted image or close M14-F03.
No build/container/guest/Git/root/cleanup/resize actions belong to this lane.
