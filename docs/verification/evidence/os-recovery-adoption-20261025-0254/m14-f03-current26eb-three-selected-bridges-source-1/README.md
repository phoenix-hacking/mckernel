Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Three real selected26eb residual callbacks are ready for Root's bounded HOST
qualification queue. The accepted351b652e syscall object has75 allocated FUNCs
and contains all three exact names; no old96 frontier is used.

| Current C callback | Existing Rust provider | Required C selector |
| --- | --- | --- |
| ptrace_wakeup_find_thread_bridge | f03_ptrace_io_find | MCKERNEL_RUST_F03_WAKEUP_FIND |
| ptrace_wakeup_thread_unlock_bridge | f03_ptrace_io_unlock | MCKERNEL_RUST_F03_WAKEUP_UNLOCK |
| thread_exit_waitq_wake_bridge | f03_exit_notify_wake | MCKERNEL_RUST_F03_EXIT_WAITQ_WAKE |

The first two Rust providers are already exported/selected in26eb; their
existing find/unlock bodies are unchanged. The third provider already exists
and is used by the Rust exit-notify path. Its only Rust change is
cfg_attr(f03_exit_waitq_wake_selected_candidate,no_mangle). No wrapper, function
body, wait queue algorithm, lock, reference, cleanup or C data object is added.

candidate/kernel/syscall.c contains exactly three reversible alias/extern
guards; the genuine C fallback bodies remain byte-for-byte. Explicit#line
restoration preserves later source coordinates. The exit-waitq location has
two original logical contexts:4493 with existing offload/helper/dispatch scope,
4500 without that prior reset. The guard restores each context explicitly.
The two ptrace locations follow an unconditional original reset. __FILE__ is
never overridden. All unrelated C bytes remain exact. The private policy copy
changes only the one export attribute, with no shared/canonical writes.

Root centrally appends the three C selectors and one new Rust cfg inside the
existing supported CMake branch. The already-active
f03_ptrace_io_find_selected_candidate and
f03_ptrace_io_unlock_selected_candidate remain required. There is no new module
or source file for production. Linux6.12/x86_64, non-UBSAN, non-DCFA and current
lock ABI scope remain unchanged; genuine NOCACHE stays undefined. F06 owns
disjoint arch callbacks; the shared policy/CMake merge remains Root-owned.

The prepared HOST fixture includes the exact three original C callbacks and
their actual selected alias branches, plus the unchanged Rust function bodies.
Only find_thread, thread_unlock and waitq_wakeup are substituted with explicit
typed scalar/identity mocks. Genuine process/waitq/lock/list headers and retained
actual Rust ABI/layout types supply19 cross-language words and six C signature
assertions. Planned cases are90 find pairs (signed TGID/TID and null/real return
pointers),3 unlock identities and3 valid waitq identities with unchanged bytes.
No actual lookup, thread lock, wait-list, wake/schedule, kernel, reference,
current-stack or native action occurs in that fixture.

Source and exact-plan verification passed:

```sh
Q=/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f03-current26eb-three-selected-bridges-source-1
taskset -c 0 prlimit --as=2147483648 --cpu=30 --core=0 -- timeout 60s python3 -B "$Q/verify_source.py"
```

FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json contains the complete three literal
argv vectors, SHA pins, C flags/include paths, fresh output and exact expected
stdout. Rust1.92/GCC9 are the existing HOST ABI tools, not the production
Rust1.95/GCC14 toolchain. Root may bind that fixed tuple into the existing
reviewed finite capture/account supervisor after a real ordinary CPU6 grant;
there is no new controller or execution release here. Use one job, AS2GiB,
CPU60/wall90 per command, FSIZE64MiB/core0 within existing aggregate limits.
Create future-host-output-1 only through Root's actual granted preparation.
Stop on first failure and retain any successful prefix; do not replay it.

Actual compiler/HOST result/grant/first-compiler/blocked timestamps remain NULL.
The expected production change is75→72 selected C functions and one new public
export of an existing Rust function; import changes are not accepted in advance.
Default/link/native proofs and original find/unlock/waitq lifetime/locking/
scheduler contracts remain open. No whole-file retirement is claimed.

The first source-only preparation error used kernel/include/list.h. Its exact
failure is retained; the one correction pins the genuine lib/include/list.h
already selected by the existing GCC include path. No compiler or assertion
correction was made.
