# Python 3.8 pidfd compatibility: source-only checkpoint

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status **SOURCE ONLY, UNTESTED, NO OPERATION RELEASE**. This is a separate delta
on `fork-handoff-expert-1` and `adapter-readiness-expert-1`; both remain preserved.
Its exact 13-file manifest is `SHA256SUMS`. The actual source directory is under
`DISPATCHER-MAX-PREFERRED-20261030-1`, not `DISPATCHER-SOL-MAX-20261030-1`.

`/usr/bin/python3` resolves to root-owned `/usr/bin/python3.8`, version 3.8.10,
SHA256 `298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06`.
Read-only feature inspection found no `os.pidfd_open`, `signal.pidfd_send_signal`
or `os.waitstatus_to_exitcode`; the signal-mask APIs and CLOCK_BOOTTIME exist.
This establishes Python API availability only, not kernel syscall availability.

`pidfd_compat.py` feature-detects native pidfd APIs and otherwise uses explicitly
typed `CDLL(None).syscall`, with errno, only for Linux x86_64 with 64-bit pointers
and longs. Local root-owned `/usr/include/x86_64-linux-gnu/asm/unistd_64.h`
SHA256 `698d4666c969b0b4d0bed328b4a4f3cab765ec1a9948e0f14751f0ce56d91535`
and `/usr/src/linux-headers-5.15.0-139-generic/arch/x86/include/generated/uapi/asm/unistd_64.h`
SHA256 `c7517b327a3d37a8ff6fea9476fc7a691e2dc124730797f45f257ddc07a46882`
independently give pidfd_open 434 and pidfd_send_signal 424. No numeric-PID
signal fallback exists. CLOEXEC and requested nonblocking state are checked; a
post-open verification error carries the actual FD to retained UNKNOWN custody.
The portable wait-status conversion accepts only terminal exited/signalled states;
it is not evidence of descendant retirement.

The guarded fork path, adapter, guarded union receiver and watchdog use the explicit
module rather than globally monkeypatching `os`. The root loader pins the module
and `runtime_binding.py`; explicit manifest-supplied runtime path/hash, root-controlled
executable ancestry, an immutable root-owned executable and actual process identity are
required. The watchdog, supervisor, owner and validator must bind the same reviewed
runtime. No user-writable Anaconda interpreter is selected. Whether the actual system
binary satisfies the existing immutable-root bootstrap policy was not checked or
changed; root must independently provide and admit a suitable exact binary.

The old expert tests that directly patch missing `os.pidfd_open` remain frozen and
are not valid unchanged under Python 3.8. This delta's synthetic fork tests mock the
explicit compatibility module instead. `test_pidfd_mock.py` mocks native wrappers,
libc and fd flags; `test_deferred_fork.py` mocks fork, signal and pidfd module calls.
They have not been run. After independent review and a fresh approved ordinary-user
profile, each may be run from this directory with `/usr/bin/python3 -s -E -S -B`;
root must bind exact source/dependency hashes, private output root, CPU/RAM/wall
limits and process retirement before doing so.

`test_pidfd_self.py` is a **separate proposed actual unprivileged host check**: it
opens a pidfd for its own process, checks `/proc/self/fdinfo` identity and CLOEXEC,
then sends signal 0 through the pidfd and closes its own FD. It creates no child,
does not touch a native owner or controller, and has NOT been executed. It still
requires its own reviewed profile and fresh actual admission. ENOSYS, EPERM,
verification errors or uncertain retirement are not passes and must be retained.

Static `/usr/bin/python3 -s -E -S -B` compile-only syntax passed for all 13 files;
no module import, fixture, actual pidfd syscall, signal, fork, root operation,
container, mount or native action was run. Actual controls, current-free, root
bootstrap install, source quiescence, physical ownership and workload admission
remain open; no existing gate is changed.
