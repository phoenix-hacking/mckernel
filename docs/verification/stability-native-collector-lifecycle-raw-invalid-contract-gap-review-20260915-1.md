# Native lifecycle raw-invalid contract gap review 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-invalid-contract-gap-review`
Disposition: `RAW_INVALID_SPEC_GAPS_ONLY`

This independent plain-text audit ran no parser, pool expansion, tests, compiler,
model, native code or guest. `vectors.json` currently has an empty `raw_invalid`
object and the harness never consumes it, so no malformed-input acceptance exists.

Each raw case must carry a name, coverage labels, exact input bytes, validation
target and the literal result `stage=harness`, exit 2, empty stdout/stderr and zero
model invocations. It must not fabricate a model `SCHEMA` output row. Required
families include forged authority fields/operations; PID/TID and every full-key
integer boundary/type; key shape/domain and parent errors; operation ID/count;
argument, enum, capacity, version and flag types; document/vector/operation object
shape; duplicate keys; malformed, nonfinite, NUL and trailing bytes; and invalid
pool names, references, placeholders, cycles, depth and expansion.

Legal width boundaries stay positive ordinary cases. Revoked references, unknown
full identities, wrong subject domain and a schema-valid wrong terminal formula
remain semantic vectors with `REF`, `KEY`, `STATE` and `STATUS` respectively.
Malformed model output belongs to oracle validation, not raw input rejection.

Three rules remain unfrozen: the `raw_invalid` record/entry-point schema and how a
hash-bound external 1,048,577-byte artifact is represented; whether omitted pool
`args` is canonical and how excess arguments are rejected; and separate coverage
accounting for raw cases versus ordinary vector/model expectations. These rules
must be corrected before materialization. The current rejected Rust/C attempt-1
models cannot establish MODEL2 outcomes.

No raw-invalid source, whole-corpus review, build, native collection, ABI,
application or production gate is released by this review.
