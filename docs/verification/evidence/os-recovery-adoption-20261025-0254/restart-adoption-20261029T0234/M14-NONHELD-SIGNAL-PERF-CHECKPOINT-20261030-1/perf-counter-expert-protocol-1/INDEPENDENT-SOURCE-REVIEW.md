# Independent source review: perf microtest expert owner

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **NOT_RELEASED; EXTERNAL WATCHDOG AND DESCENDANT-CUSTODY CONDITIONS OPEN**. This is a source-only review. No test, compiler, process experiment, physical workload or native execution was performed, and this record does not authorize one. Preserve the earlier failed candidates and their reviews.

## Reviewed final bytes

- `owner_candidate.py`: SHA-256 `8441d0409bad876298ef6d4401a0edb355a94cc02f521d19bee660ce489f1cbc`.
- `test_owner_faults.py`: SHA-256 `be3329f4af1edc76a829ce79f432ae2df95b2cb8f4fae6b356d22be4b24ba1d4`.

## Findings

The proposed owner materially addresses the two previous source failure families. A gated worker waits for a positive GO before input staging or command launch. The owner checks the timeout session/group anchor and the worker's parent, group, session, process start identity and executable, persists the group record, and rechecks immediately before GO. EOF or absent GO does not authorize staging. The worker's stage barrier uses `waitid(WNOWAIT)` and a same-group census, and requires the compiler leader to be exited with no other same-group family members, including zombies, before joining it and starting the fixture. Exception and identity paths retain UNKNOWN rather than claim successful cleanup. These statements are source observations, not executed fault or kernel process evidence.

The outer timeout remains a concrete blocker. The 175-second GNU timeout is started only after the owner performs its own environment and resource setup, tool hashing, scratch root creation and fsynced reporting. It cannot bound a blocked setup, its own `Popen`, or owner-side `/proc` and evidence writes. The separate timeout session also means that merely timing out or killing the owner is not proof that the worker group retired. The code delegates outer caller custody but does not bind an independently reviewed external watchdog, its 180-second window, process identity, evidence, signal and retirement protocol. Fresh operation admission must resolve that custody, including UNKNOWN handling, before execution. The extra timeout family and all limits must be reviewed against the exact admitted profile; no automatic permission follows from this record.

The pre-fixture and final censuses inspect process-group membership, not all descendants that could change process group or session. Positive retirement consequently depends on a separately established no-escape property of the exact pinned compiler/linker families, or an independently reviewed broader owned-descendant observation. Stage membership also checks the fixed anchor and worker PIDs are present; it does not establish the anchor is live at the barrier. Reconcile those conditions before treating a census as proof of complete stage retirement.

The prepared fault tests are unexecuted and mock source functions. They exercise intended handshake, EOF, descendant-census and termination decisions at the function level; they do not establish real OS fork/exec timing, timeout behavior, process-group non-escape, signal delivery or cleanup. Every unproven join and uncertain outcome remains UNKNOWN. The existing clean environment, pinned inputs/toolchain, CPU and aggregate shares, limits, floor checks, disjoint output, captures and fresh coordinator admission remain applicable.
