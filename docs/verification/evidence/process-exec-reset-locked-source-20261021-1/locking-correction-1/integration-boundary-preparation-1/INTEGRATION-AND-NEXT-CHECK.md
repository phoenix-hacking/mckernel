Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Precise source integration handoff, no execution. The current shared two files
still contain the old C fragment and no exec-reset Rust body. The regenerated
current-kernel-activation.patch is byte-identical to locking-correction-1's patch;
CURRENT-PREIMAGE-AND-POSTIMAGE-BINDING.json gives both whole-file pre/post hashes.
Apply only after root joins genuine independent source acceptance and the current
whole boundary. Do not overwrite unrelated edits if the preimages change. No
CMake/library/dependency change is needed: the existing syscall_policy module,
MaybeUninit and McsRwlockNodeIrqsave imports already exist in the full Rust crate.
C kernel/CMakeLists.txt339 already defines MCKERNEL_RUST_SYSCALL_POLICY_HELPERS in
this supported profile. The original C fallback stays byte-for-byte unchanged,
including its separately preserved inherited shared-table race. This proposed
repair is the selected Rust profile only, not an all-configuration race closure.

Root reports the corrected actual-body-comparison-1 PASS0/.249911385s, eight seeds
crossed with incoming IRQ0/0x200 using actual retained Rust lock bodies and modeled
CPU callbacks. All original scalar/corrected source, manifests, three-command
captures and original failures remain in their original directories. No bodytest
or SDK analysis was repeated to prepare this handoff.

ABI/lifetime binding required by this real caller:
- Current live Thread.sigcommon is offset4824 and Thread.sigstack4840.
- SigCommon is2176bytes/align64, lock0/use64/action72/pending2120; 64 actions have
  stride32, handler offset0/word8. SigStack is24bytes with sp0/flags8/size16.
- Actual writer node is64bytes/align64 and the actual table lock64bytes. The
  compile-only assertion header includes REAL process.h, never fixture structs.
- process_clone_sigcommon_share_body_result7398..7419 installs the pointer and
  increments the shared table reference. The current live exec Thread retains
  its table reference through this call; actual destroy releases it at
  process_helpers.rs11092. This body neither changes sigcommon nor acquires or
  drops table/Thread/VM credits. Local preemption disable is not peer exclusion;
  the same writerlock used by do_sigaction serializes the action loop. The
  lock's existing nesting/IRQ behavior is released before FP/altstack effects.

The next cheapest concrete compile is production-compiler-command-data.json's
first argv: complete current /src/kernel/syscall.c, selected Rust policy, real
headers plus production-signal-abi-assertions.h. Second argv compiles the same
complete TU with the inherited policy/scheduler fallback undefines. Third/fourth
compile actual lib.rs as native/legacy whole crates with unchanged production
code model/target flags. All outputs use a NEW exec-reset-whole-consumers-1 root.
Root must stage the exact small assertion header there and bind /src to complete
current integrated postimages plus unchanged dependencies/generated headers.
No output root or source materialization was created by this owner.

These exact tool paths/flags come from the accepted production compile database
and accepted six-stage whole-crate recipe. They are unprivileged command data,
not a borrowed execution grant. Their reusable reviewed environment is the
existing4CPU2-5/12GiB/noSwap/512tasks/nonet container with one compiler at a time.
They do not authorize running /nightly or /src commands directly on CPU6 host,
container creation, root/module/guest work, or a second heavy owner. Root owns
fresh admission/current source binding and execution through the existing owner.
No new wrapper/framework or test gate is proposed.

Finite object/default observations after those actual commands:
1. Selected complete syscall C object imports exec_reset_signal_state_current_v1
   once; policy-off fallback imports it zero times. Real header asserts pass.
2. Native and legacy whole Rust objects each uniquely define that body, without
   unresolved references to existing lock primitives. Keep all compiler warnings;
   compare genuine warnings to current retained baseline without a blanket pass.
3. Integration is source/compile proof only. The next matching linked image must
   uniquely define the body and clear_fp_regs, have no unresolved relevant symbol,
   preserve default compile macro and exact source hashes, and show live
   do_execveat -> Rust reset -> existing FP callback execution ordering. Optimizer
   inlining may remove named internal lock calls; verify body rather than strings.
4. A separately released real native exec must still prove caught/default/ignored
   handler and altstack behavior, plus ordinary completion/physical retirement.
   No process creation/wait acceptance, wholeM06, native or retirement credit is
   claimed by this source handoff or the already completed isolated bodytest.

Failure-family history carries forward: one cause-supported shared-table locking
correction has been prepared and body-tested by root. Preserve any production
failure, diagnose actual cause, and do not replay unchanged deterministic inputs.
Source owner is now QUIESCENT, no builds/tests/subprocesses/leases/runtime state.
