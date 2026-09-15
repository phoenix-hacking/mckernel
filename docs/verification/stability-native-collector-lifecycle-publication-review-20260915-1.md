# Native collector lifecycle publication review 1

Date: 2026-09-15
Task: `M02-C-native-collector-lifecycle-publication`
Reviewed commit: `ac28cafecfbfd5cfd933de3c5d0ec0b5004e1f89`
Disposition: `FAIL_DESIGN_FREEZE`

The lifecycle producer prerequisite can be scoped, but the native collector ABI
cannot be frozen. This independent review changes no source, performs no build or
execution, and leaves native collection, application acceptance and production
credit closed.

Birth must distinguish allocation, successful publication and rollback. A main
thread allocated in `host_prepare_process_body_result` can fail and be destroyed
before scheduling; its numeric TID is installed only in
`host_schedule_process_request_result`. `do_fork` assigns a TID before later
fallible setup and host clone completion. A nonreused instance identity must be
allocated before exposure. Successful birth must publish before `runq_add_thread`,
with explicit abort accounting if an earlier preparation state was published.
Neither `create_thread` nor numeric-TID assignment alone is an authoritative hook.

`terminate()` misses ordinary thread-only exit. `do_exit` records a thread status
and exits while siblings remain alive. Group termination records group/current
thread status, and its already-exited branch copies group status into later exiting
threads. The producer needs distinct process-terminal and thread-terminal records
covering all paths under lifecycle serialization; a group event cannot fabricate
simultaneous sibling retirement. Preserve raw terminal value, source branch and
classification. `terminate_status_result` encodes `((rc & 255) << 8) | (sig &
255)`; that is not proof of an observed guest wait result.

Retirement occurs at actual reference-count-zero destruction, not at terminal,
`finalize_process`, or each `release_thread` call. `process_release_thread_body_result`
destroys only at zero; main-thread storage can survive until
`process_release_process_body_result`, and a finalized zombie can await its parent.
The producer must capture immutable identity before destruction and publish
accurately scoped completion afterward using retained storage. It must include
direct destruction of prepared-but-unscheduled failures.

Available host identity domains include Linux PID-object identity, OS
slot/generation, application cleanup token, worker token and delivery serial.
Guest process/thread incarnation, exec instance and authoritative binding to the
producer-side application token remain absent. Typed domains, numeric attributes
and explicit nonreuse/overflow rules are required; pointers and reusable proxy
TIDs are insufficient.

Existing host SCHEDULE publication has no reply and precedes guest scheduling.
WAIT/RETURN ordering and the bounded diagnostic trace cannot prove completeness.
The prerequisite packet must define retained storage surviving launcher departure,
sequence allocation and commit ordering, release/acquire consumption, sticky
overflow/loss, explicit capture end and clock domains without unsafe allocation or
blocking under lifecycle locks.

The next packet is limited to producer states, ownership and failure vectors for
preparation abort, late clone failure, immediate child exit, TID reuse, thread-only
exit, concurrent group exit, retained references/zombies, launcher loss and buffer
exhaustion. Loader/transient mapping and stream attribution remain separate open
contracts.
