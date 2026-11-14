# Native lifecycle output control-Boolean source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-output-control-boolean-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to output-registry Boolean checkpoint commit
`7e85efd10f8571528e2ddbbc3f9c7d01ce57e84b` and archive SHA256
`37effa1684a484bd1cf800d94dea9b2f6f385082e16891c8a3598d3158fb714c`.
The current source hashes are harness
`a4a18e905d238f0763a67e533a1c5a278a9fab3735b2b32a26464a603aecdc54`,
vectors
`651e053dd507347d3853f3e27a2b6e501c518d7123347fa161908a301fa962d7`,
expected
`86473f7b4027b9a06e064788d7ed41115b28705a62edc199879990310323a7f7`
and tests
`8e3029278f977fc244d865f67e44367796fa4f17586de5b707980ff7f8e9d11f`.
Allow only `scripts/tests/test_native_lifecycle_model.py`, adding
`NativeLifecycleOutputControlBooleanTests`. Preserve harness, fixtures, raw 136,
all existing tests and every false gate.

Use an independently handwritten copy of the accepted R1 compact JSON literal:
192 bytes, SHA256
`4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a`.
Do not derive it from a model, `expected_rows()` or `expected.json`. Its single
LF-terminated output stream is exactly 193 bytes.

Add exactly three negative methods, each starting from a fresh R1 and making one
control-array scalar mutation:

| Method | Sole mutation | Row bytes before LF |
| --- | --- | ---: |
| `test_output_control_overflow_integer_zero` | `[5][3]`: Boolean `false` to integer `0` | 188 |
| `test_output_control_ended_integer_zero` | `[5][4]`: Boolean `false` to integer `0` | 188 |
| `test_output_control_incomplete_integer_zero` | `[5][5]`: Boolean `false` to integer `0` | 188 |

For each negative, independently require the old suffix
`[1,1,0,false,false,false,0]]` to occur exactly once and its replacement suffix
to occur zero times before replacement. The respective exact replacement
suffixes are:

```text
[1,1,0,0,false,false,0]]
[1,1,0,false,0,false,0]]
[1,1,0,false,false,0,0]]
```

Require byte-for-byte equality between that fixed-token replacement and compact
serialization of the structural mutation. Prove exactly one structural
difference and exact built-in `bool` to `int` types. Do not rely only on decoded
object equality.

Each negative parses through one real `strict_bytes`, reaches one real
`validate_output_row(row, 1)`, visits one process validator and zero thread
validators, then first fails at the control Boolean assertion. Require the exact
built-in `AssertionError` type with empty arguments and no oracle comparison.
Parsing precedes row validation and process validation precedes rejection.

The fourth method is `test_output_control_boolean_positive_controls`. The R1
baseline passes real validation and comparison against its independently
declared literal. A separate handwritten complement changes the control suffix
to `[1,1,0,true,true,true,0]]`; its row is exactly 189 bytes and its terminated
stream is 190 bytes. Assert the three values are exact Booleans and both Boolean
endpoints pass. This is schema-only and makes no lifecycle-semantic claim.

For every invocation, mock only `subprocess.run` to return
`CompletedProcess(["/model-not-executed"], 0, supplied_bytes, b"")` for input
`b"MODEL2 256 NONE\n"`. Assert exact PIPE, timeout 10 and `check=False`
arguments. Guard `Popen`, build, compiler and raw-child with `RuntimeError` and
assert zero calls. Assert no output directory exists and preserve hashes of the
four current fixtures before and after every method.

Run the four methods under pinned Python 3.9.12 and 3.8.10 and require 4/4 each.
The immutable archive has ten members: manifest, four source files, oversized
artifact, this packet and its review, and two command-prefixed logs. Bind both
interpreter binaries, literal hashes, three-negative/two-positive-scenario
accounting, raw 136 and all false gates. Preserve failures separately.

Other output fields and shapes, nullable-key policy, terminal/snapshot
validation, live stream limits and final matrix reconciliation remain deferred.
No compiler, model, native, application or production release follows.
