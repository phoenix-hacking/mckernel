# Native lifecycle raw key/domain source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-key-domain-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to the accepted 58-case checkpoint JSON SHA256
`101e90e7609ae09c398f19665e06ee6463d334fa1883d222c94d7f6255011fef`.
Its four source hashes must match the current working fixture before mutation.
Allow edits only to `vectors.json::raw_invalid`, the matching harness inventory
and focused `test_native_lifecycle_model.py` tests. Preserve decoder semantics,
all 58 accepted records, ordinary literals, models, mutants and artifacts. Both
corpus flags and `RAW_FULL_MATRIX_FROZEN` remain false.

Use the exact compact envelope and literal P/T/A/F bases from
`stability-native-collector-lifecycle-raw-authority-width-source-packet-20260915-1.md`.
Every case begins with a fresh base, changes only the named occurrence, preserves
member order and has no trailing newline. `opN` identifies the operation whose
first field is `N`; only key-component indices are zero-based.

## Exact 30-case slice

| Names | Sole mutation | Intended first rejection |
| --- | --- | --- |
| `raw-key-{capture,os-generation,application,process,exec}-zero` | P op1 subject indices `{0,2,3,4,6}` become `0` | required-nonzero key |
| `raw-key-slot-{negative,u64-overflow,boolean,fractional,string,null}` | P op1 subject[1] becomes `{-1,18446744073709551616,true,1.5,"1",null}` | integer; fractional first fails expansion literal type |
| `raw-process-subject-thread-domain` | P op1 subject[5] becomes `1` | process allocation |
| `raw-thread-subject-process-domain` | T op2 subject[5] becomes `0` | thread allocation |
| `raw-subject-{null,scalar,short,long}` | P op1 subject becomes `{null,"P",[1,0,1,1,1,0],[1,0,1,1,1,0,1,1]}` | subject shape |
| `raw-thread-parent-{null,scalar,short,long}` | T op2 parent becomes the same four replacements | key shape |
| `raw-thread-parent-thread-domain` | T op2 parent[5] becomes `1` | key domain |
| `raw-process-unexpected-parent` | P op1 parent becomes literal P | process allocation |
| `raw-tid-assign-unexpected-parent` | A op3 parent becomes literal P | unexpected parent |
| `raw-capture-{subject,parent}` | P op2 indicated null field becomes literal P | capture-wide subject |
| `raw-capacity-{boolean,overflow}` | P vector `event_capacity` becomes `{true,257}` | integer |
| `raw-abort-stage-{zero,overflow}` | F op3 `a` becomes `{0,256}` | bounded integer |

The first two table rows use coverage `['full-key',name]`, the next eight use
`['domain-parent-shape',name]`, and the final two use
`['numeric-bounds',name]`. Every record uses exact inline UTF-8 and expectation
`{"stage":"harness","exit_code":2,"stdout_hex":"","stderr_hex":"","model_invocations":0}`.
These 30 unique names bring the cumulative raw inventory to 88. Do not add
operation-ID aliases: accepted `raw-id-zero` and `raw-id-gap` already cover them.

## Positive controls and tests

Require exit 0 and empty streams for every exact unmodified base; capacity 0/256;
abort stage 1/255; slot 0/u64 maximum; each required instance component 1/u64
maximum; process thread component 0 and thread instance component 1/u64 maximum.
When a positive changes a repeated key component, change its subject and parent
copies consistently. Decoder validity does not imply model-semantic acceptance.

Independently construct and compare exact compact bytes for all negatives. Retain
boolean/integer/float anti-conflation controls. Assert the exact 30-name slice,
88-name union, coverage, expectations, uniqueness, empty nested raw lists and
ordinary disjointness. Preserve the existing first-28 guard and pin the first 58
lexical record bytes through the 58th closing brace to SHA256
`bf14431f328af1b37777352fa70a24055e7824f0b2fd721c386debb1e4c57741`,
using raw bytes before UTF-8 decoding and an LF-to-CRLF rejection control. Verify
ordinary content against the accepted archive.

The build tripwire must observe exactly 88 raw children, no compiler/build/model
call and no output directory. Preserve artifact and timeout/output retirement
tests. After source review, retain both interpreter commands, streams, binary and
source hashes.

Deferred: full per-component key type coverage; remaining operation-ID types and
bounds; main flag, terminal bounds and dedicated unused arguments; pool, remaining
envelope, artifact and output-oracle matrices; semantic identity, parent,
lifecycle, ownership and precedence vectors. This slice does not freeze the raw
matrix or release compilation, model/native execution, ABI or acceptance.
