# Native lifecycle output registry-Boolean source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-output-registry-boolean-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to commit `78be836aded0861c0286cf5c83e622b15afc0b70`
and these current sources: harness SHA256
`a4a18e905d238f0763a67e533a1c5a278a9fab3735b2b32a26464a603aecdc54`,
vectors SHA256
`651e053dd507347d3853f3e27a2b6e501c518d7123347fa161908a301fa962d7`,
expected SHA256
`86473f7b4027b9a06e064788d7ed41115b28705a62edc199879990310323a7f7`
and test SHA256
`b2cdf1f7fb4709ea9aa1e4040c0e4a644b1e354abf6f09607b5745f9e40beec9`.
Allow only `scripts/tests/test_native_lifecycle_model.py`, adding
`NativeLifecycleOutputRegistryBooleanTests`. Preserve harness, fixtures, raw 136,
all existing tests and every false gate.

Use two independently handwritten compact JSON rows, separated and terminated by
LF. R1 is the accepted 192-byte row with SHA256
`4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a`.
R2 is exactly this 287-byte literal with SHA256
`98eced08c345fee134d0326fc57bfec3ba7448b45230b8ece2e2c5b6f81a8183`:

```json
[2,"OK",[[1,2,2,"THREAD_ALLOC",[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,[0,0,0,0,0],1,2]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,[1,0,1,1,1,1,1],false,true,true,null]],[[[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,true,"Allocated",1,"E",null,0,null]],[2,2,0,false,false,false,0]]
```

The complete baseline is exactly 481 bytes. Do not generate either literal from
models, `expected_rows()` or `expected.json`.

Add exactly four negative methods, each starting from a fresh baseline and
changing one R2 JSON scalar:

| Method | Sole mutation | First rejection |
| --- | --- | --- |
| `test_output_process_bool9_integer_zero` | `[3][0][9]`: `false` to integer `0` | process Boolean-triple assertion |
| `test_output_process_bool10_integer_one` | `[3][0][10]`: `true` to integer `1` | process Boolean-triple assertion |
| `test_output_process_bool11_integer_one` | `[3][0][11]`: `true` to integer `1` | process Boolean-triple assertion |
| `test_output_thread_main_integer_one` | `[4][0][4]`: `true` to integer `1` | thread Boolean assertion |

Require exact built-in `AssertionError` with empty arguments, not
`ValidationError` or an oracle-comparison failure. Compact serialization checks
must prove each sole mutation and preserve Boolean-versus-integer spelling. Wrap
the real field validators: every process negative reaches two process calls and
zero thread calls; the thread negative reaches two process calls and one thread
call. Both JSON lines parse before row validation. Assert no oracle comparison is
reached.

The fifth method is `test_output_registry_boolean_positive_controls`. The
baseline passes real `run()` validation and comparison against its independent
two-row literal. A separate schema-only complement changes R2's four registry
Boolean values from `false,true,true,true` to `true,false,false,false`, retaining
actual Boolean types; it passes validation against that explicitly declared
literal. This proves both Boolean endpoints, not lifecycle semantics.

For every call, mock only `subprocess.run` to return
`CompletedProcess(command, 0, supplied_bytes, b"")`; command is
`["/model-not-executed"]` and input is `b"MODEL2 256 NONE\n"`. Assert exact
PIPE, timeout 10 and `check=False` arguments. Guard `Popen`, build, compiler and
raw-child with `RuntimeError` and assert zero calls. No child exists; claim no
process-cleanup coverage. Preserve fixture hashes before and after.

Run the five methods under pinned Python 3.9.12 and 3.8.10 and require 5/5 each.
The immutable archive has ten members: manifest, four source files, oversized
artifact, packet/review and two command-prefixed logs. Bind interpreter binaries,
literal hashes, four-negative/two-positive accounting, raw 136 and all false
gates. Preserve failures separately.

Control Booleans, other output fields/shapes, live stream limits and final matrix
reconciliation remain deferred. No compiler, model, native, application or
production release follows.
