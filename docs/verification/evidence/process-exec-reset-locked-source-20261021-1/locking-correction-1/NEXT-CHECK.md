Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Cause-supported correction EXEC-RESET-SHARED-SIGHAND-1. The original literal C,
original Rust candidate, original manifest and root actual-body-comparison-1 are
preserved in the parent directory. Root reports the original scalar comparison
PASS0/.188053286s for eight seeds; that never proved caller synchronization.

The original do_execveat loop can race a peer accepted CLONE_SIGHAND owner because
local preemption disable does not exclude the peer's do_sigaction. This corrected
Rust body uses the SAME SigCommon.lock and existing writer lock ABI around only
the 64 caught-handler loads/stores. It releases the lock before clear_fp_regs and
before alternate-stack fields change. Its stack-local actual aligned lock node
preserves the prior IRQ state. Existing nested preemption save/restore preserves
the exec caller's original disabled-preemption depth. No allocation, destruction,
reference transfer, new compute C, new assembly, registry or framework is added.

Candidate and activation patch remain private, unexecuted and unintegrated. The
existing C fallback is kept byte-for-byte with its original inherited defect;
no all-profile race-fix claim is made. Production selected Rust is the proposed
repair scope. Existing FP, altstack, process and CPU correctness paths remain.

Next ordinary check for dispatcher only, after review/profile admission:

    python3 /home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/locking-correction-1/run_actual_body_once.py /ABSOLUTE/NEW/OUTPUT /ABSOLUTE/REVIEWED/RUSTC

It hashes actual ABI+lock_helpers+spinlock_helpers before C compile/Rust test-link/
one exact body test. Actual lock bodies execute with host CPU callbacks replacing
hardware IRQ/preemption operations. Eight table seeds crossed with incoming IRQ0
and0x200 verify saveIRQ -> nested preempt -> handler reset complete by genuine
ticket release -> restoreIRQ -> FP callback -> altstack reset. The callback checks
one acquisition/release and one FP reset, restored original preemption depth1,
exact original IRQ flags, reset table before release and old altstack through FP.
Exact C parity retains the literal original fragment. Full-object checks permit
only handler pointers, three altstack fields and the real lock's first4 ticket
bytes to change; lock padding, refcount, masks, pending lists, Thread owners and
all other state remain unchanged. This is a functional finite lock/order test,
not real multicore execution, hardware IRQ proof, native exec or C retirement.

Independent review must accept the actual live caller/table lifetime, same-lock
choice and unlock-before-callback ordering before shared integration. Then root
must compile selected/fallback complete C with production headers and both full
Rust crate selections, prove link/default route and run a separately released
native exec case. Preserve any new failure and escalate after this one bounded
correction; no unchanged retry. SDK66 fixed capacity/provider blocker stays separate.

Source owner is QUIESCENT with no workload, subprocess, lease or runtime state.
