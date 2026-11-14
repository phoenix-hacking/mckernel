# Exact owned control-process stop review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. The companion conditional review is not the source's fresh one-shot
release and is not evidence that any process was signaled or retired.

The exact source rechecks the existing Root session, caller, sudo and target
PID/birth/UID/parent chain, the target's full selected argv and Python inode and
hash, the single-thread/no-child condition, the retained diagnostic FD set
and absent nonce output paths. It opens a new pidfd and independently checks
its fdinfo target before any signal, then sends TERM and, when needed, KILL
through that pidfd only. A terminal pidfd observation is explicitly separate
from the outside sudo direct wait and caller-session join. Successful close of
the helper's own pidfd is attempted once; uncertain close is never retried.

The post-signal wait is limited to eight boot-clock seconds, but the whole
helper has no guaranteed wall bound. On uncertainty with a retained pidfd the
helper intentionally stays alive; Root must retain its actual session/custody
and charge the already held reservation if it cannot be positively joined.
The target's exit closes its own FDs. It does not establish what happened to
the earlier pidfd target, prove historical absence or release the original
operation. The original four-GiB reservation, native12, V2 UNKNOWN 2 GiB,
scratch21, mutex27:4, native current-free and all native holds remain intact.

Root must supply the source's separately reviewed fresh one-shot release,
current controls/usage, rechecked process/resource conditions, CPU6 and a real
exclusive capture. Account any new sudo frontend/monitor inside the existing
host-control share and helper work inside the existing operation budget; no
extra concurrency or budget follows. Root remains responsible for actual
helper, sudo child and caller-session waits. Missing identity, output, terminal
or join evidence stays UNKNOWN; never replay the original nonce.

Root reports source-test-runs/control-stop-source-0001/RESULT.json PASS for two
mocked pidfd-target and ambiguous-close cases, exit 0 and empty owned group,
0.05 seconds wall and 18332 KiB. They do not execute real pidfd signaling.
