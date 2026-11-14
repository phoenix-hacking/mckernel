# Native lifecycle strict output-oracle source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-output-oracle-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to fetched checkpoint
`a11d04cc69ce694724fdd3801a91a836543a313a` and its exact source identities.
Allow edits only to `scripts/tests/fixtures/native-lifecycle-model-v1/harness.py`
and `scripts/tests/test_native_lifecycle_model.py`. Preserve raw inventory 133,
vectors, expected literals, artifact bytes, decoder semantics, models, corpus
flags and `RAW_FULL_MATRIX_FROZEN=false`.

Extract only the final three-way assertion in `main()` into:

```python
def assert_oracle_match(want, rust_rows, c_rows):
    assert rust_rows == want and c_rows == want and rust_rows == c_rows
```

Call this helper at the original assertion site. Do not move or bypass raw,
corpus, build or mutant gates. Keep `run()` and all output validators unchanged.

Use this independently written exact row R, not output from either model:

```json
[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,false,false,false,0]]
```

Its compact UTF-8 is exactly 192 bytes with SHA256
`4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a`.
Let E be `R[2][0]`, C be `R[5]`, B be those compact bytes, and baseline stdout be
`B + b"\n"`. Independently construct a normal expected-document envelope with
empty pools and `vectors:{"oracle":[R]}`. Real `expected_rows(document,"oracle")`
must equal literal `[R]`; neither implementation nor corrupted output supplies
the expectation.

## Exact 13 corruption cases

Each starts from a fresh literal copy.

| Name | Sole stdout mutation | First rejection |
| --- | --- | --- |
| `oracle-row-malformed-json` | B without final `]`, then LF | exact `ValidationError("invalid JSON")` |
| `oracle-row-missing` | empty bytes | oracle comparison assertion |
| `oracle-row-extra` | append a second compact R with ID 2 and empty events | oracle comparison assertion |
| `oracle-row-duplicate` | `B+LF+B+LF` | contiguous output-ID assertion |
| `oracle-event-malformed` | remove E's last field | event-arity assertion |
| `oracle-event-missing` | replace `R[2]` with `[]` | oracle comparison assertion |
| `oracle-event-extra` | append E copy with kind `"EXTRA"` | oracle comparison assertion |
| `oracle-event-duplicate` | append exact E copy | oracle comparison assertion |
| `oracle-control-malformed` | replace C with null | control-shape assertion |
| `oracle-control-missing` | remove R's final field | row-arity assertion |
| `oracle-control-extra` | append integer 0 to C | control-arity assertion |
| `oracle-control-duplicate` | append a second C as seventh row field | row-arity assertion |
| `oracle-control-value-corrupt` | change `C[0]` from 1 to 2 | oracle comparison assertion |

The duplicate-control case is an extra positional row field; the schema has no
control collection. Every assertion failure has exact built-in `AssertionError`
type and an empty message. These cases are oracle failures, not raw decoder exit-2
records or model result literals.

Mock `module.subprocess.run` to return
`CompletedProcess(command,0,stdout,b"")`, then invoke the real
`run(command,b"MODEL2 256 NONE\n")`. Assert the exact call, including input,
captured stdout/stderr, timeout 10 and `check=False`. For every schema-valid
corruption, require all three helper calls `(want,bad,good)`, `(want,good,bad)`
and `(want,bad,bad)` to fail against the independent literal. This detects a
helper that ignores either implementation; agreement between implementations
alone is insufficient.

Positive controls pass the exact baseline through both sides and repeat it without
the terminal LF. Require exact parsed `[R]` and successful helper comparison.
Maintain an exact 13-name inventory outside `RAW_REQUIRED`. Guard real
`subprocess.Popen`, build, compiler and raw-child entry points. Assert no real child
starts, no output directory appears and no fixture byte changes. This controlled
mock has no process to reap and supplies no subprocess-cleanup evidence.

After independent source approval, run the separate oracle test class verbosely
under pinned Python 3.9.12 and 3.8.10. Retain commands, exit codes, complete streams,
source/interpreter hashes, the fixed literal bytes/hash and packet/review. Source
verification must prove `main()` calls the helper at the unchanged gated site.

Defer expected-document corruption, individual process/thread-row field matrices,
remaining JSON/stream/status variants, real subprocess timeout/output-memory
behavior, model compilation and full corpus semantics. `run()` bounds captured
stdout only after completion; this packet does not prove bounded live capture.
No full-matrix, compiler, model, native, application or production release follows.
