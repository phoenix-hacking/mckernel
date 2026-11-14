# Known control join and failure observer review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source/evidence review only; no signal, cleanup, operation or native
release was performed by this reviewer.

Retained control-stop actual-1/RESULT.json reports pidfd terminal for root
Python 3109451/birth 119988726, kill_used=false, helper pidfd VERIFIED_CLOSED,
and stop-helper terminal exit 0 with empty temporary group. The separate
ROOT-CALLER-JOIN.ACTUAL.json records session 94281 joined, caller group empty,
and sudo direct wait status 256. CALLER-TERMINAL.json reports zero-byte stdout,
verified-closed captures and missing full DATA; sudo status is nonzero. These
facts retire only the documented known control processes. They do not identify
the earlier keeper birth, prove the root install succeeded, release the
original four-GiB operation reservation, or establish native current-free.

Failure proposal SOURCE-BOUND.json
208510b4a417e736dd6e3d05c2359975a13bee9adaf2d55f415b69c30d197d81,
root_parent.proposal.py 4acd57e90c1c38fc505960fcef34942e06ca5d7d62b7c8b2942f1aa16497d548,
adds bounded best-effort stderr DATA for fixed exception messages, role/stage
and observed identity, while preserving UNKNOWN and the existing stop/custody
path. Arbitrary exception text is redacted. It can expose exceptions in the
child callback and parent failure paths but cannot guarantee all first causes:
deferred_fork.py runs _restore(True) before entering the callback and exits 127
on failure, and phase0 catches post-mutation errors and waits internally rather
than propagating them. A missing failure note has no success meaning.

Role correction FROZEN-SOURCE.json
f3360a0520629e647042b439726d4b86687548a53f744d33ab7cdcfa936db564,
driver aca962cdc97cf710688424aaa922d02a472a52dec138ba43e65639dcead6a807,
requires the exact Python argv prefix for root/keeper/installer, preventing
the sudo argv containing the same -c literal from being classified as Python.
The actual source-test-runs/failure-data-role-0001 result reports five relevant
mock tests PASS (four reporting and one role), exit 0 and empty owned group.
These are synthetic source checks, not proof the failed attempt's unseen cause.

Any new candidate and its real resource plan require their own exact review
and fresh admission. The old operation's UNKNOWN four GiB remains in the
aggregate in addition to native12, V2 UNKNOWN two GiB, and any new operation.
No replay of the old nonce or release of scratch21, mutex27:4, source/effective
view or native holds follows.
