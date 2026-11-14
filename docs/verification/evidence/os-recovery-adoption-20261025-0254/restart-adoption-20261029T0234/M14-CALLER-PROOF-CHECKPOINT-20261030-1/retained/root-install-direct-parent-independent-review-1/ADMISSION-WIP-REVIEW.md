# Direct install admission preparation: WIP review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. This reviews the draft observed in root-install-parent3-admission-
preparation-1, not a frozen final version or release. No workload, test, root,
installation, mounting or native operation was performed by this reviewer.

The R2 proposal retains native/current-free and V2 ownership UNKNOWN, budgets
three operation roles together at 4 GiB, and requires real sudo/frontend/monitor
overhead within that shared allowance and fresh resource/control values.
The code-based per-role FD allowance distinguishes partial observed peaks
from unmeasured production paths. This is planning, not a measured full-operation
peak, additional native authority, or an excuse to widen RLIMIT_NOFILE.

The draft preparer records durable exclusive reservation, request, argv,
capture identities and PREEXEC before exec; its reservation explicitly says
that actual later sudo/root PID and birth remain to be observed. PREEXEC alone
is no proof of later process-tree custody. An executable binding for the real
Root caller to observe and join the direct session, bind actual process
identities and capture, and retain the reservation on missing evidence has
not yet been supplied. No additional privileged owner is inferred.

The parent run() holds the complete verified operation proof, but serve()
returns only status, nonce and lease/native fields; the bootstrap emits that
summary. Its full proof is journaled under the operation's root-private 0700
directory. The documented UID1000 caller capture cannot reconcile actual
keeper/installer identities or inspect that proof from the summary. Supply a
bounded captured full verified result with actual parent identity, or an
equivalent real readable proof channel; preserve UNKNOWN after capture failure.

After a source successor is frozen, review its exact hashes and actual owner
binding. Separately materialize fresh real controls, current resources and
admission under the existing one-shot rules. No automatic operation release
follows from this WIP review or the earlier mock tests.
