# Direct root parent bounded correction — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The original parent successor and child predecessors remain unchanged. This
successor binds the independently preserved direct-child-successor-3 and the
unchanged reviewed parent_control.py from parent successor 1. It is not an
operation release; native/current-free/source exclusion and resource ownership
remain unchanged.

The only parent behavior change covers `fork_and_pin` raising after recording
an owned keeper pidfd but before assigning the returned tuple. On this failure,
the parent consults the existing UNKNOWN ChildRecord under its latch lock and
only uses its held pidfd after independent checks of the descriptor identity,
CLOEXEC and nonblocking flags, fdinfo PID, live direct parent, and a stable
observed birth. No identity is promoted to success and no numeric-PID signal is
used. A `PidfdVerificationError`, unavailable or drifting process/descriptor
identity, missing ownership or other uncertainty leaves the record UNKNOWN and
the parent does not use the handle. Recovered handles enter the existing
best-effort pidfd TERM/KILL and direct wait path. The external Root owner must
retain the actual operation resources when stop or join is unproved.

The former bootstrap's final serialization was verified by AST inspection to
already append an actual newline. Its production expression is unchanged; the
new synthetic fixture extracts that actual expression and checks exact emitted
bytes. The shared parent_control module remains bound to the original path and hash
in the corrected child loader. This candidate's
three Python files passed Python 3.8 AST parsing. No test, root, fork, signal,
pidfd or installation operation was run by this worker.

Root's existing `parent-control-0001` protocol tests remain valid only for
unchanged parent_control.py and need not be rerun. The proposed bounded changed
source check, after Root's light-test admission, is:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-2/test_parent_source.py TestProfile TestRecovery TestBootstrapBytes
```

The fixture mocks all root, fork, pidfd and signal operations. The exact source
closure and profile require independent review; Root separately supplies actual
operation review, fresh controls/usage, admission, no-replay nonce and retained
resource/capture ownership before any execution. The profile requires the
unprivileged invoking driver to narrow itself to CPU 6 before sudo and Root to
measure/admit the sudo frontend and monitor as host-control overhead.
