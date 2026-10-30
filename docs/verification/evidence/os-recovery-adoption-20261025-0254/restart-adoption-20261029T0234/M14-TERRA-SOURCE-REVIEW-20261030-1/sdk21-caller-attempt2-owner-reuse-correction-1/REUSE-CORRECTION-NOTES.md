# Operation owner reuse: bounded source correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The previous `run()` raised inside its catch-all for any second invocation and
reset its local fork marker, incorrectly changing a prior uncertain ownership
state to DENIED_BEFORE_FORK. This successor claims the single-use instance under
a lock before admission and returns the existing state for every later call;
it does not call the backend or alter retained identities on reuse. A reentrant
call while fork is in flight reports FORK_OUTCOME_UNCERTAIN. The first run's
failure remains UNKNOWN_OWNERSHIP_RETAINED after the attempted fork.

The final-byte check record `synthetic-results-1/result.json` SHA256
89e231cf2d848f1c2bf14c8457d632b851462f2b90eb3bc1f1ce793f3c52674a
captures separate stdout/stderr, status 0 and source hashes for all five fake-only
suites. Sequential prior-UNKNOWN, prior denial, prior candidate and reentrant
in-flight fork cases passed; no additional physical owner was launched.

Review blockers remain: the watchdog decision lacks admission/service/weekly hold
checks; clock or stop callback exceptions can bypass UNKNOWN publication; owner
admission can go stale across callbacks; live health authentication and a real
independently running watchdog, direct-fork/private-group backend, held-GO
custody, descendant-retirement evidence and fresh operation release are absent.
The parent health hold remains unconditional. No group census alone proves
retirement, and no controller, observer, Docker, privileged, native/guest or
cleanup operation ran. This narrow correction is not an execution release.
