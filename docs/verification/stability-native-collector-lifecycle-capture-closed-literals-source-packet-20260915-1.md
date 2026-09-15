# Native lifecycle capture-closed literal source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-capture-closed-literals-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this packet to checkpoint commit
`d2aa1a4b40a43949d038e481c0380974c4cc6e3d`, capture-closed policy SHA256
`8a2ab78dc54aee28f79ff5178e6f7cb88611db9c8d336ad4a7d8e785daf5ee52`
and policy-review SHA256
`db1011ee03afc678f2a9685d52e49535e9d514907322ee0ca1e2d81d69267685`.
The bound source hashes are harness
`722b6b59b175090be518c55a655cd95024facaa3c539d0e9dabbc0ea2c3985d0`,
vectors
`1dfc7105093fe618f4bbb758af9bf92fc31795120ca4e70625a43272e8f69ae9`,
expected
`86473f7b4027b9a06e064788d7ed41115b28705a62edc199879990310323a7f7`
and tests
`7c20c39de57fd0548737049700492dfd66de9d1b8aa5f471b60295a00ccf739b`.
Preserve the oversized artifact at SHA256
`9a6384d7058b15fa74ef39f6bd6e5745a1fbec565abb06491714704d3d88e07c`.

This packet authorizes only six independently written compact input and full
output literals, their ordinary inventory membership, and exact source tests.
It does not authorize adapting or running either model. The current Rust model
at SHA256
`0bd333c42890bb6692041ad8d69765da8bf90d6c073004b6a382e56d57741ead`
and C reference at SHA256
`3bbb640edf2712fe00c757216311accadd3acd185d47f6c5ba5427acd6277714`
remain rejected MODEL1 sources and are outside the write set. No compiler,
model, raw-child, native, guest or application execution is released.

## Exact source write set

Allow changes only to:

- `scripts/tests/fixtures/native-lifecycle-model-v1/vectors.json`
- `scripts/tests/fixtures/native-lifecycle-model-v1/expected.json`
- `scripts/tests/fixtures/native-lifecycle-model-v1/harness.py`
- `scripts/tests/test_native_lifecycle_model.py`

Preserve every existing pool member, mapping, literal, mutant, raw 137 case,
artifact and false gate. Add exactly these six ordinary vector names:

```text
end-after-complete-end
end-after-incomplete-end
operation-after-end
wrong-key-after-end
launcher-loss-after-end
teardown-fail-after-end
```

Add all six names to `ORDINARY_REQUIRED`; ordinary inventory changes from 38 to
44. The six expanded documents contain exactly 88 operations/output steps.
Every added vector has exact `event_capacity: 256`, exact `seed: "NONE"`, and
exact coverage `["capture-closed", "<vector-name>"]` using its own name as the
second string.
Pool references must remain independent entries: the complete-state prefix is
the sixteen separate input references `L01` through `L16`, and the matching
output prefix is the sixteen separate expected references `B01` through `B16`.
Do not add a nested `BASE16`, concatenate pool members, or derive expected rows
from either model.

## Five complete-prefix witnesses

For each of the following vectors, expand input references `L01` through `L16`
in order and append the indicated seventeenth operation:

| Vector | Exact operation 17 |
| --- | --- |
| `end-after-complete-end` | `[17,"CAPTURE_END",null,null,0,0,0,0]` |
| `operation-after-end` | `[17,"REF_ADD",[1,0,1,1,1,1,1],null,0,0,0,0]` |
| `wrong-key-after-end` | `[17,"REF_ADD",[2,0,1,1,1,1,1],null,0,0,0,0]` |
| `launcher-loss-after-end` | `[17,"LAUNCHER_LOSS",null,null,0,0,0,0]` |
| `teardown-fail-after-end` | `[17,"TEARDOWN_FAIL",[1,0,1,1,1,1,1],null,0,0,0,0]` |

For each, expand expected references `B01` through `B16` in order and append
this identical, independently handwritten full row:

```json
[17,"CLOSED",[],[[[1,0,1,1,1,0,1],null,100,"Retired",0,"N",[9472,37,0,4],0,[1,0,1,1,1,1,1],false,false,false,[[1,0,1,1,1,0,1],[9472,37,0,4],0]]],[[[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,true,"Retired",0,"N",[9472,37,0,1],0,[[1,0,1,1,1,1,1],[9472,37,0,1],0]]],[16,16,0,false,true,true,0]]
```

This row proves `CLOSED`, no emitted event, unchanged sorted full process/thread
snapshots and counters, `ended=true`, `incomplete=true`, and no additional event
attempt. The wrong-key operation is schema-valid and proves closure precedence
over capture-key validation. Launcher loss and teardown failure after closure do
not emit or attempt their events.

## Incomplete-prefix witness

`end-after-incomplete-end` has this exact three-operation input document:

```json
[[1,"P_ALLOC",[1,0,1,1,1,0,1],null,100,0,0,0],[2,"CAPTURE_END",null,null,0,0,0,0],[3,"CAPTURE_END",null,null,0,0,0,0]]
```

Its expected document is existing `B01` followed by these independently
handwritten rows:

```json
[2,"OK",[[1,2,2,"CAPTURE_END",null,null,null,null,[0,0,0,0,0],1,2]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[2,2,0,false,true,true,0]]
```

```json
[3,"CLOSED",[],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[2,2,0,false,true,true,0]]
```

This proves that the first end is `OK` and irrevocably closes even with a live
row, while its already-true incomplete latch, registries and all seven control
fields remain unchanged on the second end.

## Exact tests and release conditions

Add one `NativeLifecycleCaptureClosedLiteralTests` class. It must use independent
handwritten copies of the six names, suffix operations and full rows above; it
must not import calculated expected rows from a model. Require:

- exact six-name and input/expected mapping equality;
- sixteen separate `L01`–`L16` and `B01`–`B16` references in the five prefixes;
- exactly 88 expanded operations and 88 expanded output rows across the slice;
- byte/structure equality against the independently handwritten full rows;
- full sorted process/thread snapshots and all seven exact control fields;
- zero event and zero counter/attempt deltas on every `CLOSED` row;
- schema-valid wrong-capture input and `CLOSED` precedence;
- complete-first-end `false` to `true` incomplete delta, and no state delta after
  the already-incomplete first end;
- fixture-size exact cap after materialization plus before/after fixture hashes;
- compiler, build, model-process and raw-child tripwires proving zero calls.

Add two test-only malformed-after-end controls proving whole-document schema
validation remains first. Name the methods
`test_unknown_operation_after_end_is_schema_rejected` and
`test_boolean_capture_after_end_is_schema_rejected`. Each document uses the
fixture's pools, empty `raw_invalid` and `mutants`, and one vector with exact
capacity 256, seed `NONE`, coverage `["capture-closed", "schema-first"]`, the
sixteen separate `L01` through `L16` references, and respectively this exact
operation 17:

```json
[17,"UNKNOWN",null,null,0,0,0,0]
```

```json
[17,"REF_ADD",[true,0,1,1,1,1,1],null,0,0,0,0]
```

Serialize each compactly and invoke `decoder_mode()` in-process with controlled
byte stdin and captured stdout/stderr. Require returned status 2, both captured
streams empty, and zero calls to
`subprocess.run`, `subprocess.Popen`, `raw_child`, `build`, `compiler` and
`run`. In a separate direct `decode_raw_document()` assertion on the same bytes,
require exact `ValidationError` messages `operation identity` and `integer`,
respectively. Do not launch the decoder child. These controls do not enter ordinary
inventory, raw inventory or the 88-step accounting.

Run only this new class under pinned Python 3.9.12 and 3.8.10, requiring all
methods to pass under both. The immutable evidence archive must have ten
members: manifest, four source files, oversized artifact, this packet and its
review, and two command-prefixed logs. Bind both interpreter binaries, final
source hashes and sizes, six-vector/88-step/44-ordinary/raw-137 accounting, both
rejected model hashes, zero model/compiler/native execution and all false gates.
Preserve every failure separately.

Passing literal tests is source evidence only. It grants no model agreement,
semantic execution, application acceptance or production credit. The other
five lifecycle decision families and the full output/raw matrices remain
unresolved.
