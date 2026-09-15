# Native lifecycle capacity contract gap review 1

Date: 2026-09-15
Task: `M02-C-lifecycle-capacity-contract-gap-review`
Disposition: `CAPACITY_SPEC_GAPS_ONLY`

This was a bounded, independent plain-text review. It performed no JSON import or
expansion, test, compilation, model execution, native execution or guest run.

The frozen correction map states limits of two applications, four processes,
eight threads and 128 operations, but exact application/process/thread boundary
literals are not yet source-ready. There is no `APP_ALLOC` operation, and the
contract does not define whether `P_ALLOC` admits an application, the precise
application identity, global versus per-application/per-process row counts,
whether occupancy survives retirement, second-application domain constraints,
or the `LIMIT` result and validation precedence.

The narrow correction must state that successful `P_ALLOC` admits its qualified
application identity; define that identity and parent/domain constraints; count
all retained process and thread rows globally; retain application occupancy; and
return `LIMIT` before registry, reference, storage or event mutation. Separate
vectors must then isolate a third application, fifth process and ninth thread.
Their failed operation emits no event, preserves all rows and only latches
incompleteness.

The 128-operation boundary is document validation, not a semantic `LIMIT` row.
A 129-operation document must exit 2 with empty stdout and stderr and zero model
invocations. The current harness does not yet provide that clean raw-invalid entry
path, so the negative cannot be materialized honestly.

The existing `LOST_MAX` vector checks lost-counter saturation only. A separate
`ATTEMPTS_MAX` vector is required: capacity 256, a single `CAPTURE_END`, and exact
control `[18446744073709551615,0,18446744073709551615,true,true,true,0]` with no
retained event. This uses the already declared seed and needs a distinct required
vector name.

No capacity literal, source packet, build, native collection, ABI, application or
production gate is released by this review.
