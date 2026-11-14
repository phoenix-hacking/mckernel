Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The next private F06 body is `arch_ptrace_xstate_copy_to_bridge`. The accepted
CURRENT116 arch object77db1a40 defines this GLOBAL FUNC at0x2c0/46bytes among17
selected functions. `SELECTED-CURRENT116-ARCH-FRONTIER.json` derives that fact
directly from the retained exact ELF. This is retained artifact evidence, never
fresh host/native ownership clearance. The banked117 `vdso_get_vdso_info` and
118 `arch_native_signal_restore_fp_bridge` bodies are deliberately untouched.
Existing signal-dispatch undefined-domain obligations and service holds remain
unchanged; this ordinary ptrace-read callback does not depend on that candidate.

The complete Rust provider preserves the original unsigned-long64 address and
size_t64 arguments and signed-long64 return. It reads the real `Thread.fp_regs`
field through a raw pointer. Null FP state returns-ENOMEM without invoking copy;
nonnull state passes the exact destination, source and count to the already
selected Rust `x86_memory_helpers::copy_to_user`. Its signed-int32 result widens
to signed-long64 exactly as C. Partial provider effects remain unchanged. No
new address/count normalization, thread lookup, locking, reference, allocation,
mapping, error translation, FP instruction or C runtime implementation is added.

The caller retains the original live/aligned target-thread and target-FP lifetime
and exclusion obligations. A null/invalid thread has undefined original C
behavior and is excluded from this fixture; the candidate adds no alternate
policy for it. FP-state mutation during this ordinary field read remains outside
the original caller's synchronized contract. No Rust reference is formed over
target state or user memory; ownership stays with the existing ptrace caller.
`ptrace_read_regset` and its existing NT_X86_XSTATE size clamp remain unchanged.

Only this directory was written. Three selection patches target exact CURRENT116
canonical preimages, all tied to Root's actual116 source-adoption receipt:

- `arch-selection.patch` pairs the new selector with a declaration and preserves
  the original C body verbatim in the fallback branch.
- `rust-module-selection.patch` adds the private module to the real crate under
  `f06_ptrace_xstate_copy_to_candidate`.
- `cmake-selection.PROPOSAL.patch` pairs the Rust cfg/source and C selector in
  the same existing supported x86/Linux6.12/non-UBSAN branch. It introduces no
  supported runtime profile. Copy the exact candidate module to its named
  production destination only after independent review and Root adoption.

Root must compose these disjoint hunks with whichever117/118 sources it actually
adopts. Rebind the genuine origin/profile after all source edits; do not reuse
the previous source hash/origin receipt or any consumed build/native prefix.
No canonical/shared file, controller, ledger, checkpoint or global control was
changed. Stopped scratch21, permanent27:4, failures and all exclusions stay intact.

`PREIMAGES.json` records exact source/header/provider/ABI preimages. The real
header witness checks `copy_to_user`'s genuine nominal signature, public bridge
ABI, LP64/int32/ENOMEM, the actual typed fp_regs field and supported Thread/xsave
size/alignment/offset. `abi.snapshot.rs` is the complete current Rust ABI file,
not a second modeled Thread. The original C oracle includes the real kernel
headers and the unmodified original function bytes; only symbol names redirect
to a deterministic test-only user-copy effect.

The fixture includes the entire candidate module unchanged, with its existing
Rust user-copy provider mocked. It prepares1944 pairs over null/nonnull FP,
zero/normal/boundary/high-bit counts, signed-int32 result extrema, actual/null/
high-bit user addresses and four partial-copy prefixes. It compares returns,
provider call count/order/arguments/results, all4096 destination/source bytes
and all5568 Thread bytes. An independent expected-result/effect/full-canary
oracle also runs. Null/high-bit user and huge-count cases only test forwarding
with mocked effects; they do not claim acceptance by real usercopy or ptrace.
No kernel effect, hardware, actual usercopy, allocator, module or guest is run.

`FUTURE-HOST-COMMANDS.NOT-GRANTED.json` contains the exact four future commands.
After a fresh ordinary grant, the smallest first check is its command0: the
actual current-header ABI witness compile. Then compile unchanged C oracle,
compile the exact Rust module/ABI fixture, and run the single1944-pair test.
Root owns the fresh output-directory creation and actual grant/CPU/resource/
source-header closure. No compiler, fixture or native command ran in this lane;
only pure Python source/preimage/exact-patch checks ran on CPU7/jobs1.

Production followup must compile the complete Rust crate, selected full arch C
TU, fallback TU and default image with exact new origin/profile bindings. Require
no selected C definition of this target, exactly one Rust global provider, the
same existing Rust usercopy provider, unchanged regset caller and preserved all
other callbacks/data/389 registry rows. Matching-current native xstate-read/
error/partial-copy/target-lifetime checks remain required before runtime or file
credit. Predicted removal is one C function only; actual build/native/file
deltas are0. CURRENT116/C71/Rust68, M14files4/6, M15files1/8 and35/35 stay unchanged.
