# Engineering throughput report

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The user's target is at least1.95times the frozen baseline of **qualified integration
packages per hour**. The live baseline is
`docs/verification/os-milestones-20260914/ENGINEERING-VELOCITY-BASELINE-20261025-0542.json`:
two independently accepted current-object packages during04:12:42–05:12:42UTC,
or2/hour. Target3.9/hour means at least two comparable packages in each30-minute
window. The source helper's historical two-step/30-minute example is not the live
baseline. Snapshot windows and late review reports overlap; they are not substituted
for a nonoverlapping measurement period.

The existing coordinator is the sole writer of
`docs/verification/os-milestones-20260914/engineering-velocity-events.jsonl`.
Append events during the existing review and normal job handling. Each fixed
semantic package/stage is declared before its next work starts. Keep its ID across
retries. Accepted stages require an actual receipt. Repeated acceptance adds zero;
reopening subtracts one. Compiler commands, test vectors, source-only publication,
metadata and behavior-only fixtures do not count in this integration metric.
The normal engineering review continues to report useful behavior/source work.

Example event shapes, using actual timestamps and proof paths:

```json
{"event":"declare","package":"m15.executor.supported-target","stage":"SDK","at":1792908000}
{"event":"start","package":"m15.executor.supported-target","stage":"SDK","at":1792908001,"ready_at":null,"first_compiler_at":null}
{"event":"accept","package":"m15.executor.supported-target","stage":"SDK","at":1792908100,"proof":"actual/acceptance.json"}
{"event":"reopen","package":"m15.executor.supported-target","stage":"SDK","at":1792908200,"reason":"actual/regression.json"}
```

Several ready contracts are already declared in the live ledger. Use them instead
of redeclaring. Declaration grants no execution authority. Preserve exact workload
admission, command bindings, resource grants, ownership and retirement checks.
Allowed scoring stages are `current_object`, `default`, `SDK` and `native`.
Shared work counts once. Do not split packets to inflate throughput or delay a
longer useful native/default job to improve the metric. Compare stage mix and
complexity; this rate describes integration throughput, not every engineering task.
Default/native/file closures with zero baseline are reported as absolute counts.

Read a completed interval, with actual epoch values:

```sh
python3 -B scripts/os_velocity/report_velocity.py \
  --ledger docs/verification/os-milestones-20260914/engineering-velocity-events.jsonl \
  --current-start ACTUAL_WINDOW_START --current-end ACTUAL_WINDOW_END
```

Use completed30-minute buckets anchored at the baseline plan's
`intervention_started_at`; never a future end time. Inspect two consecutive full
observed buckets before claiming sustained improvement. Early observation means
collecting data, not a demonstrated speedup. Missing ready/first-compiler times
remain null; do not replace them with file modification times.

A sustained95% claim additionally requires an explicit quality event covering
both buckets, with `comparable_scope`, `no_splitting` and
`no_native_default_slowdown` all true. The coordinator's assertion is reviewable
judgment, not independent proof. Retain regressions and report changed work mix.
The reporter reads one small ledger; it starts no service, workload or monitor and
does not scan or hash evidence. The existing thirty-minute steering loop continues.
