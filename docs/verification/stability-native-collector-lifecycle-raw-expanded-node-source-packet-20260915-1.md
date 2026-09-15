# Native lifecycle raw expanded-node source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-expanded-node-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to the accepted 132-case operation/argument checkpoint JSON
SHA256 `86390058e2328ec52e58b640e350ee60cb1763405996656c39574af377e31341`
and its recorded source hashes. Allow edits only to `vectors.json::raw_invalid`,
the matching harness inventory and focused source tests. Preserve all 132 raw
records, ordinary and expected literals, decoder logic, models, mutants and
artifacts. Keep both corpus flags and `RAW_FULL_MATRIX_FROZEN` false.

Use the pool packet's exact compact `D(POOLS,OPERATIONS)` envelope with vector
name and coverage `pool-base`, capacity 256, seed `NONE`, empty nested raw-invalid
and mutants, the established top-level member order and no trailing newline.
Substitute these actual JSON values:

- `O` is `[[1,"CAPTURE_END",null,null,0,0,0,0]]`.
- `Z` is one array of exactly 255 integer zeros.
- `A(R)` is one array of exactly 1,019 copies of `{"pool":"Z"}`, followed by
  exactly R integer zeros.
- `POOLS` is `{"D":{"arg":1},"Z":Z}` in that member order.
- `OPERATIONS` is `{"pool":"D","args":[A(R),O]}`.

Materialize every member, reference and zero. No construction token appears in
retained JSON. Add exactly one negative:

| Name | R | First `ValidationError` |
| --- | ---: | --- |
| `raw-pool-expanded-node-budget-over` | 239 | `expanded literal budget` |

Its coverage is `['pool-validation','raw-pool-expanded-node-budget-over']` and
its expectation is the standard harness exit 2, empty streams and zero model
calls. The cumulative inventory becomes 133.

The exact positive `positive-pool-expanded-node-budget-fit` is the same document
with R equal to 238. It requires decoder exit 0 with empty streams and is built
only in the focused test. The negative differs solely by its final appended zero.

Expansion traversal consumes `23 + 1019*257 + R` nodes: each Z reference visits
its reference, its 255-element array and 255 integers. The positive consumes
exactly 262,144 nodes and the negative attempts node 262,145. Their conservative
byte charges are respectively 524,563 and 524,565, below 2,097,152; maximum
recursive expansion depth is four, and pool preflight consumes only 257 nodes per
accounting pass. The compact inputs are exactly 14,523 and 14,525 bytes, below the
1-MiB document cap; the separate 65,536-byte bound applies to decoder output
streams. The negative first fails `ExpansionBudget.take()` while copying the final
zero through D's sole placeholder, which selects its second argument; it cannot
reach operation count or model semantics.

Tests independently construct exact compact bytes, compare the retained negative,
check the named first error and positive child outcome, and may inspect a fresh
positive budget for zero remaining nodes and 1,572,589 remaining bytes. Require
the exact one-name slice and 133-name union, uniqueness, coverage, expectation,
nested-empty raw arrays and ordinary disjointness. The exact first 132 lexical
records, from the first opening brace through the 132nd closing brace including
intervening separators and whitespace, have SHA256
`37d212189d28e761b8ea978c8fdce4ff60e4c06e26ca4f6f316e1be8ab9a3930`.
Read bytes before UTF-8 decoding, preserve this prefix and all earlier guards, and
retain the LF-to-CRLF rejection control. The build tripwire observes 133 raw
children with no compiler, build or model call and no output directory. Preserve
artifact, timeout, output and cleanup checks.

This does not duplicate accepted byte-budget, dependency-depth or syntax-depth
cases. Aggregate preflight budgets, expanded-depth boundaries, exhaustive scalar
and key positions, semantic/oracle work and artifact faults remain deferred. Pool
name bytes are not charged by the current budget; traversal charging also masks a
standalone serialized-output-size rejection. Do not invent negative expectations
for either. No full-matrix, compiler, model, native, ABI, application or production
release follows.
