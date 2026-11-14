# Prepared actual self-exec signal-reset case

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source preparation only. No compile, test, root, guest, lock, runtime census,
artifact audit or acceptance occurred in this lane. Shared/frozen sources were
not modified. Owner: /root/native_exec_reset_oracle_prepare. Root owns integration,
execution/profile approval, Git and acceptance. Evidence lives in this directory.

## Real caller and activation

`arch/x86_64/kernel/include/syscall_list.h:61` handles nr59 as execve (nr322
execveat at168). `kernel/syscall.c:7321` -> `execve_body_result` ->
`syscall_execveat_bridge:7314` -> `do_execveat:7105`. The actual Rust bridge
`kernel/rust/syscall_policy.rs:22590` preserves the existing do_execveat caller.
After host phase1 nr59/arg0=1 at syscall.c7151, replacement VM setup,
clear_host_pte, and phase2 nr59/arg0=2 at7241 succeed, syscall.c7255 invokes
`exec_reset_signal_state_current_v1`. Source definition22525 now serializes
disposition writes through SigCommon's writer lock, preserves default/ignored,
unlocks before clear_fp_regs, then disables the thread altstack. Shared mask is
not reset. `kernel/CMakeLists.txt:339` enables the selected Rust syscall-policy
definition. Root's accepted four-object compiler33 is source/object evidence;
final linked/default-selected new image and actual exec are still required.
Historical policy-off C branch at syscall.c7257 remains unlocked and preserved.

## Exact host prerequisite, separate from SDK66 fork activation

Reuse existing accepted launcher33f source/artifact/dependency records; no
recompile or duplicate artifact audit was performed. Source:
`../numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-successor-preparation-1/mcexec_helpers.sentinel-corrected.rs`
sha256 da71f31656ccfc58a79c4dcca01f9c6742135c292b213b7d86113ebddc4cae0a.
Its SYS_EXECVE dispatch2853 calls act_execve2441, phase1 at2191 and phase2 at2340.
Accepted artifact33f and 16 C/Rust +348 Rust/C linked consumers are recorded in
`../numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-artifact-acceptance-1/ROOT-RECORDED-INDEPENDENT-LAUNCHER-ARTIFACT-ACCEPTANCE-1.json`.

**Blocking predicate:** `host-kernel/native-rust/mcctrl_process.rs:568-589`
routes every active delivery's MCEXEC_UP_TRANSFER to TID_TRANSFER (zero-delivery
initial image loading follows a different path). `smp_application_syscall.rs:323`
transfer_tids requires direction0 AND request.tid_buffer at362.
`application_syscall.rs:158-169` tid_buffer requires request.number()==186.
Exec's nr59 phase1 executable descriptor transfer therefore returns -22;
phase2's FROM_REMOTE descriptor copy additionally has direction1, also rejected.
The selected launcher supports exec protocol but its corresponding native host
delivery-transfer provider is not implemented for exec. Existing image loading,
gettid success and other apps cannot prove this provider exists.

Self-exec requires no fork, child owner, CREATE_PPD or SDK66 owned-fork
activation. Its genuine host gate is delivery-owned, bounded exec descriptor and
ELF-section transfer in both directions, with retained response/physical owners,
current worker/delivery verification, executable-close handling and real RET.
Do not relax tid_buffer globally, bypass ownership, use initial-image loading as
live exec evidence, or treat ENOSYS/EINVAL as success. Matching released host
modules implementing that provider and separate native execution release remain
necessary. SDK66 storage gate stays blocked and unchanged.

## App and independent oracle

`practical_exec_signal_reset.rs` is a single no_std/no_main Rust app using raw
Linux x86-64 syscalls. Only assembly is a five-instruction _start shim and
three-instruction rt_sigreturn stub; independent assembly/ABI review is required
before execution release. No libc/std/runtime initialization precedes observation.
The first invocation installs caught SIGUSR1, ignored SIGUSR2, default SIGWINCH,
mask2560 and 65536-byte altstack, then queries every setup fact. It self-execs
through real syscall59 with argv=[absolute-self-path,"--after-exec"] and empty
envp. New-image entry first queries all selected facts and only emits its exact
success line if caught->default, ignored/default persist, mask2560 persists,
altstack flags2/sp0/size0. Any syscall failure or exec return exits101 with a
failure diagnostic. Success exit37. No unsupported result passes. No children.

Independent expected stream is frozen in expected.stdout and oracle.json before
any compiler run. test_linux_reference.py adapts the existing qualified
scripts/tests/test_practical_process_exec_wait.py capture/timeout/ELF/reference
machinery: compile, inspect static EXEC x86-64 ELF, actual Linux selfexec, exact
stdout/stderr/exit37. It does not infer expected bytes from execution. This is
an ordinary reference observation, not actual McKernel acceptance. Existing
strict native stream/exit verifier can consume the same frozen files later;
no new native harness is introduced. Reuse owning supervisor retirement logic.

## Next executable observation and stop condition

After root grants the existing ordinary unprivileged reusable profile: one
compile/Linux reference under CPU6 <=1GiB, separate private fresh HOME/TMPDIR and
output root, no network/children except compiler+timeout's owned subprocesses.
Keep current aggregate grants; do not overlap a quiescence/census. Set
PRACTICAL_EXEC_RESET_EVIDENCE to a fresh profile output directory and
PRACTICAL_EXEC_RESET_RUSTC to the profile's pinned Rust compiler absolute path;
execute `python3 test_linux_reference.py`. Proposed timeout9s/kill1s through
existing capture. No claim that this proposal is an execution release.

The first failed candidate gets one bounded correction with original evidence
retained; repeated same-family failure escalates. Existing native exec-host
provider gap is unattempted, not a failed candidate to replay. Source case may
advance through compile/Linux independently; native run stops at missing host
provider/new linked selected image/release. No new image build is authorized by
this preparation. No source-catalogue or native acceptance credit.
