Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Round0 reached load, postflight and gate. The retained FAILURE reports app0_trace_oracle, Rust Failure::Pair(-5), ownership_complete1, rounds0/launches0/trace_bytes0. There are two ABORT records and a complete97303B declared failure trace with saved1 and no export error. No successful ND_PAIR/progress/report is present.

The new host trace explicitly logs KMSG eventfd_type101/count1..16/subscribers0. No continuing-service error, unserviced request or application_wait failure record appears in the prefix. Both visible cleanup intents have errno0. This is observed improvement at the typed notification path, not native/session acceptance.

App0 is pid257/cpu0. Its ACKtoken4/errno0, retirementtoken1015/errno-11 at37.137613 and leaderdelete at37.139682 are inside the exported failure trace. Its final retirementtoken1016/errno0 at38.082705 is a later live console line, after traceEND and the secondABORT. App1pid258/cpu1 has finalretirementtoken1006/errno0 at37.081727 inside the exported trace. No raw stdout/stderr or ND_PAIR app report is exported in this prefix. Source reaches app0_trace_oracle after the exact app stream/identity oracle has succeeded; distinguish that implication from directly retained output bytes.

The precise gate diagnosis now belongs to p12_first_round_predictor. The strict gate's first snapshot is not retained here; later exported snapshot and subsequent console line must not be conflated with it. This lane supplies source/line evidence and stops without a live query, gate change, replay or acceptance claim.
