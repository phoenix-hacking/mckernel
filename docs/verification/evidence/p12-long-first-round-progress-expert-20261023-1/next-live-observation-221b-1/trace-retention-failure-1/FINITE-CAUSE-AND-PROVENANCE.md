Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The new failure is a round48 launch failure caused by a recorded continuing-service EBUSY, not a current trace-retention gate failure. The retained pair_stage=trace_retention is stale from successful round47: current48 reached discover/launch but never load/postflight/gate. Producer lowerbounds remain48 completed rounds/96 launches/255716059969ns mixed work; failed current641/642 are excluded.

First fatal is471.409831 errno-16, followed by WAIT-32 for641/642, worker reap_retained-71 and cleanup intents-71. Immediately preceding valid records are641/worker55430/delivery56465 invalidated0/completed0 at471.396136, procfsDELETE641/tid643 at471.405724, and641/worker55431/delivery56468 invalidated0/completed0 at471.407066. Peer642/worker55448/delivery56458 number228/route is the last reported peer call. None is identified as the failing packet: that message/type/response address/origin is not logged.

Exported snapshot1048474B is below1MiB read rejection boundary and cumulative retained11016561B is below256MiB. Early history is outside the exported window; physical ring rollover versus bounded READ_ALL selection is unknown. Current source does not execute trace retention after launch fails, so neither cap expansion nor identity/oracle relaxation is justified.

Selected collector142d55fb..., all17 sourcepins and reused actual Rust archive45a8d757... are bound to accepted compiled receipts; no ELF/archive rehash. Focused selectedSDK6 sourcepins match its2093 closure/input map. f439 Runtime.fail omits call origin, so metadata/zeroing/dispatch/pump errors share this line. One reachable syscall admission EBUSY is sysfs_memory ledger.conflicts(response_span,true); slot exhaustion is EAGAIN. It is not proven to be the actual failing predicate. Existing local EBUSY handling differs by boundary; no blanket retry or quarantine relaxation is proposed.

Root transferred diagnostic implementation to m14_actual_consumer_fix/service-ebusy-diagnostic-1. This lane stops at finite retained facts and source refs. No compiler/test/live/runtime/kernel/module/image/canonical operation was performed.
