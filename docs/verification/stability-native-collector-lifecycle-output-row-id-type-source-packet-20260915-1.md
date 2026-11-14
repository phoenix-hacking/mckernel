# Native lifecycle output row-ID type source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-output-row-id-type-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to capture-closure source checkpoint commit
`e8461482535f43e8c38fd36bf91e7e074fe6d493` and archive SHA256
`b03594749e77866ad8e0c1bc4abf7e09050e2147f6ff00e24353084f1740c989`.
The current source hashes are harness
`d4e097b8920a299ce730d0546b476a3cf2c0c96282b925133d133edbac91cb52`,
vectors
`18dfdae2efc515c79da0cb49c20080d613fd3bd45f1c79b1839904352bb35846`,
expected
`8f8ffb64b4a254f74174e291a84305738e3b54ee2ec9962eecd7cc510a79c80e`
and tests
`419294ea48edd3bcfbb64b5e5ce568000e6c9d261558e1410f5ad0d156ca73c1`.
Allow only `scripts/tests/test_native_lifecycle_model.py`, adding
`NativeLifecycleOutputRowIdTypeTests`. Preserve every fixture, current test,
ordinary 44, raw 137, the first-137 lexical SHA256
`3f833ae7e954445215f2632b8575b8bcbfe507867fc53e9fe2b41b62c50cffd9`
and every false gate.

Independently handwrite this compact R1 row; do not obtain it from a model,
`expected_rows()` or fixture expansion:

```json
[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,false,false,false,0]]
```

Each stream is its row bytes followed by exactly one LF. Add exactly these three
methods:

| Method | Sole fixed-token replacement | Row/stream bytes | Row SHA256 |
| --- | --- | ---: | --- |
| `test_output_row_id_positive_control` | none | 192/193 | `4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a` |
| `test_output_row_id_boolean_true` | `[1,"OK",` → `[true,"OK",` | 195/196 | `a2e87b36e2721a0b6fe65cbe760ceaa36117e8a3387931dce0f175d94c6783a6` |
| `test_output_row_id_integral_float` | `[1,"OK",` → `[1.0,"OK",` | 194/195 | `ede0e731f1cd76cda959b6ebc14cec1ef0fbb4ac44e8bd3392196089ba32c1fd` |

For each negative require the original token exactly once and replacement token
absent before mutation. Independently change only decoded element zero; assert
exact original/replacement built-in types, exactly one type-aware structural
difference, and compact-byte equality between structural mutation and fixed-token
replacement. Bind every size and hash. Boolean `true` and integral float `1.0`
both reject because `integer()` requires exact built-in `int`, not equality or
subclass membership.

Wrap the real helpers to prove negative ordering: one `strict_bytes`, then one
`validate_output_row(row, 1)`, then one `integer(value, 1, 128)` and exact
`ValidationError("integer")`. Require no process, thread, nullable-key or oracle
call. Check the rejected integer argument's exact type because mock equality
would conflate `true`, `1.0` and `1`. The positive parses and validates, visits
one process validator and zero thread validators, then calls the oracle helper
once against the independently decoded R1 literal.

Mock only `subprocess.run` to return
`CompletedProcess(["/model-not-executed"], 0, stream, b"")`. Require exactly:

```python
run(["/model-not-executed"], input=b"MODEL2 256 NONE\n",
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    timeout=10, check=False)
```

Guard `Popen`, compiler, build and raw-child with `RuntimeError`; assert zero
calls, no output directory, and the four fixture hashes unchanged before/after
every method. Run only this class under pinned Python 3.9.12 and 3.8.10,
requiring 3/3 each and command-prefixed logs. Preserve any original failure.

The immutable archive has ten members: manifest, four source files, oversized
artifact, this packet and its review, and two logs. Bind interpreter, member and
literal hashes plus ordinary 44/raw 137. This is post-capture mock-only output
schema evidence. It executes no live subprocess, compiler, model or native code,
proves no capture-closure semantics and grants no application or production
credit. Other output fields and the full raw/output matrices remain deferred.
