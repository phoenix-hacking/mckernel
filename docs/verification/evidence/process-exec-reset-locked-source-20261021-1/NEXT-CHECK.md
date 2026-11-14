Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private source only. No command below was executed by this owner. No shared source,
CMake, Git, acceptance ledger, launcher, runtime or lease was changed. No live host
workload remains from this assignment.

Target: P-M06-01's actual successful exec state transition. The existing Rust
execve_body_result/execveat_body_result still forwards into do_execveat; this new
body ports only its caught-handler/FP/altstack commit fragment. It does not claim
fork, exec, wait, M06 completion, or Rust retirement. Root owns integration and
execution; no storage/ACK rewrite is proposed.

Candidate files:
- exec_reset_signal_state_current_v1.rs is the exact candidate body with imports
  for an isolated compile. kernel-activation.patch inserts the identical body
  into the existing syscall_policy module and selects it at the existing C call
  site under MCKERNEL_RUST_SYSCALL_POLICY_HELPERS. The fallback is verbatim, and
  its now fallback-only loop variable is guarded to avoid an unused warning.
- exec-reset-actual-body.rs includes the actual retained ABI module, executes the
  candidate, and compares it with the literal original C fragment. Eight seeds
  exercise all default/all ignored/all caught/mixed 64-entry tables. The FP
  callback checks order and exactly one call per body. Whole-object byte checks
  require every non-target field, sigstack padding, signal mask, table refcount,
  locks, pending lists and Thread fields to remain unchanged.
- exec-reset-c-reference.c uses a field-only C Thread wrapper; its original
  fragment is byte-for-byte retained. A Rust offset check binds the C action
  offset72 to the real ABI before either body runs. It does NOT prove production
  C Thread layout or caller concurrency. Real production-header and whole-crate
  checks remain necessary. No FP hardware state is exercised by its callback.

Next cheapest meaningful command, for ROOT to run only after ordinary profile
admission and quiescence requirements permit it:

    python3 /home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/run_actual_body_once.py /ABSOLUTE/FRESH/EVIDENCE-DIR /ABSOLUTE/REVIEWED/RUSTC

The runner requires a never-used output directory and hashes the real ABI,
candidate, literal C fragment and fixtures before three actual commands: gcc
-Werror compile, rustc -Dwarnings test-link, and one exact filtered Rust test.
It captures every argv/stdout/stderr/status and stops at the first failure.
The dispatcher must provide/review resource and CPU controls; this script grants
none. Preserve the first failure; one bounded correction then expert escalation.

After actual parity PASS: independently review this real caller's existing
signal-table mutation/concurrency contract, then apply the private patch only
through root integration. Preserve cpu.c/process.c fixes and all unrelated dirty
work. Compile current complete syscall C TU selected+fallback with production
headers and current native+legacy Rust crates. Require one linked definition,
callsite route and no unresolved clear_fp_regs dependency. Native exec app evidence
must later verify caught/default/ignored dispositions and altstack disable before
retirement credit. A body fixture is not an exec or fork runtime result.

Owned-fork activation stays separately blocked on the existing SDK66 fixed
14,159,970,304-byte scratch/modules gate. The accepted mcctrl6571 lacks adoption
provider; the existing opaque-MM + three Linux control wrapper/composite provider
candidate and compiler failure chain remain intact. Do not repeat unchanged
failed requests, relax the gate, resize/delete scratch or mix modules.
