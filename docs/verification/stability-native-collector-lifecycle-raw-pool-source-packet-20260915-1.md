# Native lifecycle raw pool source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-pool-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to key/domain checkpoint JSON SHA256
`e7721d955c3eb4f2451795b75acf3f51a18d6071cd81b1ad26bcd43a1dd4f244`
and its exact current source hashes. Allow changes only to
`vectors.json::raw_invalid`, the matching harness inventory and focused source
tests. Preserve all 88 accepted records, ordinary/expected literals, decoder
semantics, models, mutants and artifacts. Keep both corpus flags and
`RAW_FULL_MATRIX_FROZEN` false.

Use compact envelope `D(POOLS,OPERATIONS)`:

```json
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":POOLS,"vectors":[{"name":"pool-base","coverage":["pool-base"],"event_capacity":256,"seed":"NONE","operations":OPERATIONS}],"raw_invalid":[],"mutants":{}}
```

`E` means literal `[1,"CAPTURE_END",null,null,0,0,0,0]`, `O` means literal
`[E]`, `I` means literal `{"arg":0}` and `R` means literal `{"pool":"O"}`.
Every retained payload substitutes actual JSON; no recipe token appears.

## Exact 22 negatives

| Name | Exact POOLS and OPERATIONS | First `ValidationError` message |
| --- | --- | --- |
| `raw-pool-map-array` | `D([],O)` | `pools` |
| `raw-pool-empty-definition-name` | `D({"":0},O)` | `invalid input` |
| `raw-pool-reference-missing-field` | `D({}, {"args":[]})` | `pool reference` |
| `raw-pool-reference-extra-field` | `D({"O":O},{"pool":"O","extra":0})` | `pool reference` |
| `raw-pool-reference-name-integer` | `D({"O":O},{"pool":0})` | `pool reference` |
| `raw-pool-args-null` | `D({"I":I},{"pool":"I","args":null})` | `pool arity` |
| `raw-pool-required-args-omitted` | `D({"I":I},{"pool":"I"})` | `pool arity` |
| `raw-pool-nonzero-arity-excess` | `D({"I":I},{"pool":"I","args":[O,O]})` | `pool arity` |
| `raw-pool-placeholder-negative` | `D({"U":{"arg":-1}},O)` | `placeholder` |
| `raw-pool-placeholder-boolean` | `D({"U":{"arg":true}},O)` | `placeholder` |
| `raw-pool-placeholder-integral-float` | `D({"U":{"arg":0.0}},O)` | `placeholder` |
| `raw-pool-placeholder-string` | `D({"U":{"arg":"0"}},O)` | `placeholder` |
| `raw-pool-placeholder-extra-field` | `D({"U":{"arg":0,"extra":0}},O)` | `pool reference` |
| `raw-pool-placeholder-unbound` | `D({}, {"arg":0})` | `placeholder` |
| `raw-pool-unused-unknown-reference` | `D({"U":{"pool":"MISSING"}},O)` | `unknown pool` |
| `raw-pool-unused-self-cycle` | `D({"U":{"pool":"U"}},O)` | `pool cycle or dependency depth` |
| `raw-pool-unused-arity-excess` | `D({"I":I,"U":{"pool":"I","args":[O,O]}},O)` | `pool arity` |
| `raw-pool-unused-mutual-cycle` | `D({"A":{"pool":"B"},"B":{"pool":"A"}},O)` | `pool cycle or dependency depth` |
| `raw-pool-unused-dependency-33-leaf-first` | `D(C33,O)` | `pool dependency depth` |
| `raw-pool-unused-dependency-33-root-first` | `D(reverse(C33),O)` | `pool dependency depth` |
| `raw-pool-unused-syntax-depth-33` | `D({"U":L33},O)` | `pool depth` |
| `raw-pool-expanded-byte-budget-over` | `D({"D":{"arg":1}},{"pool":"D","args":[S174736,O]})` | `expanded literal budget` |

Every record has coverage `['pool-validation',name]`, exact inline UTF-8 and the
standard exit-2/empty-stream/zero-model-call expectation. These names are distinct
from accepted referenced unknown-pool/direct-cycle/zero-arity-excess records and
bring the cumulative raw count to 110.

`C32` is the ordered map `P00:0`, then `P01:{"pool":"P00"}` through
`P31:{"pool":"P30"}`. `C33` adds `P32:{"pool":"P31"}`. `reverse` reverses
serialization order only. These have 32/33 definitions, not edges. `L32`/`L33`
are exactly 32/33 nested arrays around integer zero. `S174736` is exactly that
many ASCII `x` characters. Retained JSON contains all literal members/brackets/
characters, not construction labels.

## Positive controls and checks

Require exit 0 with empty streams for: `D({"O":O},R)`; the same with empty args;
nested caller scope `D({"I":I,"A":{"pool":"I","args":[{"arg":0}]}},
{"pool":"A","args":[O]})`; unused arity-three pool
`D({"U":{"arg":2}},O)`; C32 in both member orders; `D({"U":L32},O)`; and
the D expansion document with exactly 174735 `x` characters. The first two are
existing positive coverage; six controls are new.

Current expansion accounting is `12*N+322`: N=174735 costs 2,097,142 and leaves
10; N=174736 would cost 2,097,154 and first crosses the 2,097,152 budget. The
inputs are exactly 175,020 and 175,021 bytes, below the 1-MiB input cap, and the
fit path uses 23 nodes. This covers traversal accounting including a discarded
argument, not serialized-output or node-budget limits.

Tests independently construct exact compact bytes, require the 22-name slice and
110-name union, exact coverage/expectations and named first-error messages. Pin
the first 88 lexical record bytes to
`40e35683740716530f59cf73e573b03c6bda7bca7d9db4b35b4e17f47fbe1834`,
preserving earlier guards and newline substitution controls. The build tripwire
observes 110 children and no build/compiler/model/output action. Preserve artifact
and timeout/output cleanup. Run only both focused decoder lanes after source review.

Deferred: expansion node/aggregate/name budgets, actual expanded depth, exact-zero
and non-ASCII accounting, remaining args/placeholders/long graphs, broader raw/key
closure, semantic precedence and output-oracle/artifact matrices. No full-matrix,
compiler, model, native, ABI or acceptance release follows.
