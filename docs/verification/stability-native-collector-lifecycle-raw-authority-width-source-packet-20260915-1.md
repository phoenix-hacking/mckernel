# Native lifecycle raw authority/width source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-authority-width-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Allow changes only to `vectors.json::raw_invalid`, matching raw inventories in
`harness.py`, and focused tests in `test_native_lifecycle_model.py`. Preserve all
ordinary vectors, expected literals, model sources, nine original raw records and
the oversized artifact. Keep `RAW_FULL_MATRIX_FROZEN=false`.

Every new payload uses the exact envelope
`{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{},
"vectors":[{"name":"raw-base","coverage":["raw-base"],"event_capacity":256,
"seed":"NONE","operations":OPS}],"raw_invalid":[],"mutants":{}}`, serialized
compactly. Let P be `[1,0,1,1,1,0,1]` and T be `[1,0,1,1,1,1,1]`. The exact
unmutated operation arrays are:

- P-base: `[[1,"P_ALLOC",P,null,100,0,0,0],
  [2,"CAPTURE_END",null,null,0,0,0,0]]`.
- T-base: P-base operation 1, then
  `[2,"T_ALLOC",T,P,200,1,0,0]` and
  `[3,"CAPTURE_END",null,null,0,0,0,0]`.
- A-base: P-base operation 1, then
  `[2,"T_ALLOC",T,P,0,1,0,0]`,
  `[3,"TID_ASSIGN",T,null,200,0,0,0]` and
  `[4,"CAPTURE_END",null,null,0,0,0,0]`.
- F-base: P-base operation 1, then
  `[2,"T_ALLOC",T,P,0,1,0,0]`,
  `[3,"ABORT",T,null,1,0,0,0]`,
  `[4,"RETIRE_BEGIN",T,null,0,0,0,0]` and
  `[5,"CAPTURE_END",null,null,0,0,0,0]`.

P and T above are substituted as their literal seven-integer arrays; no symbolic
token appears in retained bytes.

Add exactly these 19 unique cases:

- Authority coverage: `raw-authority-retire-{a,b,c,d}` independently sets that
  field of F-base operation 4 (`RETIRE_BEGIN`) to integer 1;
  `raw-authority-extra-operation-field` appends ninth field `"E"` to F-base
  operation 4; `raw-authority-extra-vector-field` adds member `"authority":"E"`
  to the F-base vector object; and `raw-authority-unknown-operation` replaces only
  F-base operation 4's name with `"SET_AUTHORITY"`.
- Width/type coverage: `raw-pid-{zero,int32-overflow,negative,u64-overflow,
  integral-float,fractional-float,boolean,string,null}`;
  `raw-tid-alloc-int32-overflow`; and
  `raw-tid-assign-{zero,int32-overflow}`.

Each PID case replaces only P-base operation 1 field `a`, respectively with
`0`, `2147483648`, `-1`, `18446744073709551616`, `1.0`, `1.5`, `true`, `"100"`
and `null`. The allocation-TID case replaces only T-base operation 2 `a` with
`2147483648`. Assigned-TID cases replace only A-base operation 3 `a` with `0` and
`2147483648` respectively.

The first seven use coverage `["forged-authority",name]`; the remaining twelve use
`["pid-tid-width",name]`. Every source is exact inline UTF-8 and every expectation
is harness exit 2, empty streams and zero model calls. The shared integer validator
is exercised with `-1`, `2^64`, `1.0`, `1.5`, boolean, string and null at PID; only
distinct lower/upper PID/TID bounds are repeated. This proves shared-validator
coverage, not every-position mutation coverage.

Positive exit-0/empty-stream controls use P-base PID 1/2147483647, T-base allocated
TID 0/1/2147483647, A-base assigned TID 1/2147483647, and every unmodified base.
Tests require exact 19-name slice and 28-name cumulative inventory, unique coverage,
unchanged original nine, empty nested raw cases and disjoint ordinary mappings.
Each negative has one mutation; `1.0` must not normalize to integer 1. Existing
cleanup/tripwire tests remain and expect 28 raw child calls.

No whole matrix, model source, compiler, native, ABI, application or production
credit follows from this packet.
