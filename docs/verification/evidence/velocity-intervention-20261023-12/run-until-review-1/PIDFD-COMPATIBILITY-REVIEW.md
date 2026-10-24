# Pidfd platform compatibility: narrow independent review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
**Accept this compatibility source delta for one fresh ordinary offline suite.**
The foreground parent must join an actual full-suite PASS and an actual own-PID
signal0 observation through these reviewed wrappers before any controller arm.
This reviewer executed no imports, tests, syscalls, signals, models or runtime
actions. Background included-only authority is not changed by this review.

The frozen packet is
`fd28d66e4d93e3154bbd3d89e09b909c6997a7a0925b0d88f094a46f7343ea54`.
All five private and three canonical pins match. Product bridge hash is
`a7a0749fdc84debc73fff69022d409b420de228450e625555524c4b4863ee81f`;
finite adapter remains `a74411302daab86d7845c771d34c4cdbb13e4ed4292656ecf26a6e9fba7f3b56`;
test source is `2962a311135125164e8baad2184f15ad081617c46c408764a61a638b66e93329`.

AST comparison against before-pidfd-compat confirms that every existing product
function except stop_worker is unchanged. That function only replaces the two
missing builtin calls with wrappers; its fresh birth/PPID check and finally-close
ownership remain unchanged. Exactly three helpers are added. The previously
accepted deadline, clock latch, child lifecycle, credit accounting, current
startup note and handoff classification are reused without another audit.

Callable Python builtins are preferred independently for open and send. When
missing, fallback is restricted to Linux x86_64 with64-bit pointers. The libc
syscall return and number are c_long; PID, fd and signal are c_int; flags are
c_uint zero; siginfo is a c_void_p NULL. Numbers434 and424 match the inspected
local asm/unistd_64.h and the parent's retained real self-syscall receipt.
CDLL(None,use_errno=True), errno reset and immediate get_errno preserve failed
calls as OSError. No raw numeric-PID signal fallback is present.

The wrapper accepts the production signal.SIGTERM IntEnum through c_int, as
well as signal0. A successful pidfd open is closed once on normal send, rejected
identity or send error. Failed open does not signal or close an unknown fd.
Unsupported architecture is refused before loading/calling the syscall entry.
No campaign or native PID was opened or signaled by this review.

The six new source fixtures check builtin preference, exact typed open/send
arguments including SIGTERM and signal0, errno propagation for both operations,
unsupported architecture refusal, close on success/identity mismatch/send error,
and no signal/close after open failure. Together with the retained cases the
source declares30 offline tests; they have not been run by this reviewer.

The earlier assertion correction changes only an incidental hold-message
substring requirement to a truthy hold record. Exact original-triplet equality,
no signal, no Popen and STOP_DEADLINE assertions remain. The original23-PASS/
1-wording-FAIL evidence and sources are archived; this is not a weakened
ownership or deadline oracle.

The earlier foreground raw-syscall self receipt proves platform availability,
not these wrapper functions. SOURCE-READY now supplies a separate foreground
command that imports the exact reviewed bridge, verifies this packet, opens a
pidfd for that observation process itself, sends signal0 through the wrapper,
reads CLOCK_BOOTTIME and closes the descriptor in finally. Root must retain that
new actual wrapper receipt after the full updated offline suite passes. No
campaign/native signal, guest action, billing change or inference is part of
that capability check.

Actual foreground arming remains under the current user's window authorization
and root's existing identity/lease/permit controls. The background root may run
offline fixtures within its authority but must not enable prepaid transitions.
No canonical source, current launcher or healthy LONG was changed here.
