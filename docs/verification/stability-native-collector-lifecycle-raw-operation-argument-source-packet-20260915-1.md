# Native lifecycle raw operation/argument source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-operation-argument-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to the accepted 113-case envelope checkpoint JSON SHA256
`19905ec7857fc6ae83524460f7f0aca3dc25caa4c271dfc0cf2b6850fb86be4a`
and its four recorded source hashes. Allow edits only to
`vectors.json::raw_invalid`, the matching harness inventory and focused source
tests. Preserve all 113 records, ordinary and expected literals, decoder logic,
models, mutants and artifacts. Keep both corpus flags and
`RAW_FULL_MATRIX_FROZEN` false.

Use the exact compact envelope and member order from the accepted authority/width
packet: vector name and coverage `raw-base`, capacity 256, seed `NONE`, and empty
pools, nested raw-invalid and mutants. There is no trailing newline. Let P be
`[1,0,1,1,1,0,1]` and T be `[1,0,1,1,1,1,1]`. Substitute their literal arrays;
no symbolic token appears in retained bytes. The exact unmutated operation arrays
are:

- P-base: `[1,"P_ALLOC",P,null,100,0,0,0]`; CAPTURE_END ID 2.
- T-base: the P allocation; `[2,"T_ALLOC",T,P,200,1,0,0]`; CAPTURE_END ID 3.
- A-base: the P allocation; `[2,"T_ALLOC",T,P,0,1,0,0]`;
  `[3,"TID_ASSIGN",T,null,200,0,0,0]`; CAPTURE_END ID 4.
- F-base: the P allocation; the unassigned T allocation from A-base;
  `[3,"ABORT",T,null,1,0,0,0]`;
  `[4,"RETIRE_BEGIN",T,null,0,0,0,0]`; CAPTURE_END ID 5.
- H-base: the T-base allocations; `[3,"TERMINAL",T,null,9472,37,0,1]`;
  CAPTURE_END ID 4.

Every CAPTURE_END has null subject and parent followed by four integer zeros.

## Exact 19 negatives

Each case starts from a fresh base and makes only the listed mutation.

| Name | Sole mutation | First `ValidationError` |
| --- | --- | --- |
| `raw-operation-id-overflow` | P operation 1 ID becomes 129 | `integer` |
| `raw-operation-id-fractional` | P operation 1 ID becomes 1.5 | `literal type` |
| `raw-main-flag-overflow` | T operation 2 field b becomes 2 | `thread arguments` |
| `raw-terminal-raw-overflow` | H operation 3 field a becomes 4294967296 | `integer` |
| `raw-terminal-status-overflow` | H operation 3 field b becomes 256 | `integer` |
| `raw-terminal-signal-overflow` | H operation 3 field c becomes 256 | `integer` |
| `raw-terminal-branch-zero` | H operation 3 field d becomes 0 | `integer` |
| `raw-terminal-branch-overflow` | H operation 3 field d becomes 5 | `integer` |
| `raw-unused-p-alloc-b` | P operation 1 field b becomes 1 | `unused argument` |
| `raw-unused-p-alloc-c` | P operation 1 field c becomes 1 | `unused argument` |
| `raw-unused-p-alloc-d` | P operation 1 field d becomes 1 | `unused argument` |
| `raw-unused-t-alloc-c` | T operation 2 field c becomes 1 | `thread arguments` |
| `raw-unused-t-alloc-d` | T operation 2 field d becomes 1 | `thread arguments` |
| `raw-unused-tid-assign-b` | A operation 3 field b becomes 1 | `unused argument` |
| `raw-unused-tid-assign-c` | A operation 3 field c becomes 1 | `unused argument` |
| `raw-unused-tid-assign-d` | A operation 3 field d becomes 1 | `unused argument` |
| `raw-unused-abort-b` | F operation 3 field b becomes 1 | `abort arguments` |
| `raw-unused-abort-c` | F operation 3 field c becomes 1 | `abort arguments` |
| `raw-unused-abort-d` | F operation 3 field d becomes 1 | `abort arguments` |

The first eight use coverage `['numeric-bounds',name]`; the remaining eleven use
`['unused-arguments',name]`. Each source is exact inline UTF-8 with the standard
exit-2, empty-stream, zero-model-call expectation. The fractional ID fails literal
expansion before integer validation. The cumulative raw count becomes 132.

## Positive controls and checks

Require decoder exit 0 and empty streams for exact P/T/A/F/H bases; main flag 0
and 1; H terminal raw 0 and 4294967295; status 0 and 255; signal 0 and 255; and
branches 1, 2, 3 and 4. Preserve the existing contiguous operation-ID 1-through-128
control. These controls establish decoder validity, not model-semantic success.

Tests independently construct compact bytes, preserve scalar spelling and include
targeted anti-conflation controls. Require the exact 19-name slice and 132-name
union, uniqueness, exact coverage and expectations, empty nested raw arrays,
ordinary disjointness and every listed first error. The exact first 113 lexical
record bytes, from the first opening brace through the 113th closing brace and
including intervening separators and whitespace, have SHA256
`0e0112f4463bba6f04d5b1b9ff5b8fa37f8a767bdde3f5b5dfddb92a256fb428`.
Read bytes before UTF-8 decoding, preserve this prefix exactly and retain the
LF-to-CRLF rejection control. The build tripwire observes 132 raw children with no
compiler, build or model call and no output directory. Preserve artifact, timeout,
stream-bound and cleanup checks.

Existing ID-zero/gap, PID/TID scalar, abort-bound and generic RETIRE_BEGIN unused
cases are not duplicated. Defer exhaustive scalar-per-position variants, other
generic-unused operations, remaining budgets and output/artifact matrices.
Terminal consistency, identity, lifecycle and ownership failures remain ordinary
literal-model obligations. No full-matrix, compiler, model, native, ABI,
application or production release follows.
