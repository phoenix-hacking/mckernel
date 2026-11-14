# Native return and narrow fault recovery design, 2026-09-09

Status: implementation in progress; no new application acceptance.

Before editing, review selected the existing Rust X86UserContext/ProcessVm ABI,
checked-copy bridges and signal consumer, and pinned Linux 6.12 sources
arch/x86/include/asm/sighandling.h and arch/x86/kernel/signal_64.c. Linux permits
only FIX_EFLAGS changes on restoration (0x50dd5); other flag bits come from the
trusted current context. Native McKernel will retain its fixed user selectors,
validate saved RIP/RSP against the current VM and the canonical lower half,
and validate everything before committing normal register/mask/stack state.
Unmapped but canonical user addresses remain ordinary user faults on return.
The complete copied frame is consumed once. Negative saved RAX values remain
legitimate syscall results, separate from a bad-frame error.

Existing kernel #GP handling panics for kernel CS, and existing assembly
__ex_table entries have no located recovery consumer. Reuse the actual saved
interrupt-register ABI, but do not pretend that emitted tables supply fault
recovery. A small native-only Rust module owns two exact instruction/recovery
pairs: a no-fault u32 source load for the futex locked reread, and XRSTOR from a
validated aligned kernel copy. Architecture assembly calls its dispatcher
before ordinary #PF/#GP processing, accounting or locking. It accepts only
kernel CS, traps13/14 and those precise instruction addresses; it writes
-EFAULT into saved RAX and the paired continuation into saved RIP. Every other
fault takes the unchanged existing path. Legacy/fallback builds do not select
the module or hooks. No broad kernel-fault suppression is introduced.

The u32 helper is not an authorization check: its caller validates the complete
user span and prefaults outside futex hash locks. The locked reread cannot sleep;
a subsequent unmap yields EFAULT. Its output is a valid kernel-owned pointer.
The XRSTOR caller owns allocation, full checked copy, actual CPU feature/MXCSR
validation, freeing and process-local badframe termination. Its output/status
must never be discarded. The separate FP review records those dependencies.

Required evidence: controlled exact dispatch tests, ordinary valid load,
assembly call-site/native selection checks, all four guest image profiles,
actual benign signal/FP/restart and futex/clone guest fixtures, original four
application modes and both complete control regressions. Controlled dispatch
tests alone do not prove actual trap delivery or application isolation. The
full Linux extended signal xstate metadata ABI remains an explicit later gate.

Image2 identified six newly unused legacy signal extern declarations after native consumer selection. Root now applies the same inverse native cfg already protecting their sole call site. No provider, legacy path or native behavior changes; warning settings remain unchanged.
The same selection cleanup applies to two timeout log event constants whose only users are in the preserved legacy futex branch; no logger or warning suppression added.
