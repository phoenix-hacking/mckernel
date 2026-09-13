# Initial reviewed runtime contracts

`runtime_contracts.py` validates immutable metadata and evaluates a small
independent oracle. It launches nothing. Its `PASS` results describe either
`runtime-contract-metadata` or `independent-oracle`; every result explicitly has
`application_acceptance: false`. Actual same-binary pinned Linux execution,
McKernel identities/routes, fault gates, resource accounting, QMP recovery and
the final execution release still require their own reviewed implementation and
evidence. A printed success marker or matching Linux output cannot establish
those facts. No original catalog, packet, report or release is changed here.

## Python interface

- `load_runtime_bundle(path)` returns validated metadata or raises
  `ContractError`. Reload immediately before each attempt; retain the bundle
  and every input it references. This is not permission to execute its packet.
- `validate_case(bundle, case_id)` returns `PASS`, `FAIL` or `BLOCKED`, scoped to
  metadata eligibility. Unselected cases and unimplemented predicates block.
- `evaluate_case(bundle, case_id, collection_report, *, evidence=None)` checks
  the supported independent oracle. The reserved `evidence` argument currently
  contributes no acceptance or provenance. A different future evaluator must
  explicitly review and implement those assertions.
- `verify_artifact(reference)`, `load_json(path)` and `strict_json_bytes(data)`
  expose the same bounded artifact/JSON checks for the future backend.

JSON must be UTF-8, at most 4 MiB, without duplicate keys, NaN, infinities or
overflowing float representations. Integers are bounded to signed-negative or
unsigned-positive 64-bit values. Artifact references are exactly
`{"path": "/absolute/canonical/file", "size": 123, "sha256": "64 lowercase hex digits"}`.
The file must be regular, have no symlink path components, remain stable during
streamed hashing, and be smaller than 95 MiB. Large evidence must use the
existing split-archive reconstruction convention rather than raise this bound.

Known objects reject extra fields. Collection reports retain their supervisor
fields; only the documented relevant fields contribute to oracle evaluation.
Manifests are content identities, not a substitute for reviewing their claims.
Unit-test fixtures exercising these schemas are never capability evidence.

## Noncyclic manifest binding

Every manifest below has `schema_version: 1` and its exact `kind`. Write each
artifact once under a fresh version/attempt name. The binding order is selected
inputs → capabilities → reviewed packet → bundle; no manifest hashes itself.

The `runtime-bundle` has three artifact references:
`selected_inputs`, `capabilities`, and `execution_packet`.

The `selected-inputs` manifest has:

- `source`: `commit` (40- or 64-digit Git hex identity), `dirty_diff` artifact
  (an empty file for a clean tree), and `compiler_bindings` artifact containing
  the retained reviewed compiler/source identity report.
- `artifacts`: `linux_kernel`, `mckernel_image`, `launcher`, `compiler`, and
  `native_modules`. The first four are artifact references; `native_modules`
  is exactly three references named `ihk.ko`, `ihk-smp-x86_64.ko`, `mcctrl.ko`.
- `profile`: `profile_id: "baseline-root-1cpu"`, `network: "none"`, payload
  `uid: 0`, `gid: 0`, `groups: [0]`, `umask` as four octal digits, and the exact
  literal `qemu_argv` array with an absolute executable. Include these fixed
  resource fields, using the catalog's names and units:
  `container_cpus: [2,3,4,5]`, `container_memory_bytes: 12884901888`,
  `container_swap_bytes: 0`, `container_tasks: 512`, `linux_vcpus: 4`,
  `linux_memory_bytes: 8589934592`, `mckernel_cpus: 1`,
  `mckernel_memory_bytes: 134217728`. This initial implementation supports only
  this profile; new topology/identity profiles need separately reviewed code.
- `payloads`: an object keyed by exactly the packet's selected case IDs. Each
  entry has `source` and `executable` artifact references, absolute guest
  `executable_path`, literal `argv`, explicit `env` object, absolute guest
  `cwd`, `interpreter` artifact or null, `dsos` artifact list, and `stdin`
  artifact or null (`/dev/null`). The retained executable artifact path and its
  guest execution path may differ; executable bytes must match. `argv[0]` is
  independent of the execution path, preserving `['app','A','','B']` exactly.

The `runtime-capabilities` manifest contains `selected_inputs_sha256` and
`capabilities`. Each named capability must occur in the unchanged catalog and
have `state: "verified" | "blocked" | "unsupported"`, a nonempty `contract`,
and an `evidence` artifact list. Blocked/unsupported entries also require a
nonempty `reason`; they never enable successful-use cases. Verified entries
require nonempty reviewed passing evidence.

Every referenced `capability-evidence` JSON has `status` from
`PASS | FAIL | BLOCKED | NOT_RUN`, `review_status: "REVIEWED"`, the exact
`selected_inputs_sha256`, `capability` name, and a nonempty `artifacts` list of
hashed original proof files. A verified capability requires every evidence
record to say PASS and match the exact input hash. Reviewing a capability means
reviewing its underlying proof, not setting these flags in isolation.

The `execution-packet` contains `packet_id`, positive integer `version`,
`catalog_sha256` matching the unchanged local catalog, `selected_inputs_sha256`,
`capabilities_sha256`, `mode: "differential-guest"`, boolean
`execution_enabled`, `review_status: "REVIEWED" | "PENDING"`, and `cases`.
`cases` is one to three unique known catalog IDs, each represented by an object:

```json
{
  "case_id": "startup.argv-empty",
  "source": {"path": "/work/reviewed/source.c", "size": 123, "sha256": "..."},
  "oracle": {"path": "/work/reviewed/oracle.json", "size": 456, "sha256": "..."},
  "review_status": "REVIEWED",
  "assertions_reviewed": true,
  "parameters_reviewed": true,
  "limits": {"all original case limit fields": "use their actual typed values"}
}
```

This example's hashes/limits are explanatory placeholders, never executable
input. Supply every original catalog limit, using integers and the exact CPU
set; no value can exceed the catalog and all infrastructure values must match
the selected profile. Source bytes must match the payload source. A source
review must establish actual operations, all catalog assertions and parameter
vectors, independent expectations, instruction requirements and resource bounds.
The original immutable draft reports alone do not satisfy this review.

The library derives prerequisites from the unchanged catalog, including all
global gates. Packets cannot remove them. `execution_enabled: false`, pending
review, incomplete assertion/parameter review, or any required missing/blocked/
unsupported capability yields BLOCKED. Successful negative-feature contracts
are outside the initial oracle subset; unsupported does not silently become PASS.
Cases with nonempty catalog `depends_on` also remain BLOCKED until a reviewed
case-acceptance evidence evaluator is implemented. Verified feature capabilities
do not erase those prior-case requirements.

## Independent oracle and collected result

An `independent-oracle` manifest contains `case_id`, positive `version`,
`source_sha256`, `review_status: "REVIEWED" | "PENDING"`, `wait_status`,
`stdout`, `stderr`, and `predicates`.

Supported wait predicates are exactly `{"kind":"exited","code":0}` (codes
0–255) or `{"kind":"signaled","signal":11}` (signals 1–64). The collector's
original numeric `waitpid` status must confirm the predicate. A normal exit
143 does not satisfy SIGTERM; textual diagnostics never replace raw status.

Each stream supports either:

- `{"kind":"exact-bytes","hex":"4100420a"}`: all bytes, including NUL and
  newlines, must match exactly; hex has no whitespace.
- `{"kind":"json-equals","value":{"argc":4,"argv":["app","A","","B"]}}`:
  one complete strictly parsed JSON value must match the frozen value and
  types. Key serialization order/whitespace do not matter; booleans, integers,
  floats and strings are distinct. Duplicate fields or trailing records fail.

`predicates` must be empty for initial eligibility. Nonempty predicates, unknown
stream predicate kinds or unsupported wait kinds produce BLOCKED. No embedded
Python, shell, expression evaluation, arbitrary normalization, implicit errno
allowlist or output-derived expectation is supported.

Evaluation requires the supervisor's integer `schema_version: 1`,
`status: "COMPLETED"`, true
`cleanup_complete`, exact argv/executable-path/environment/cwd/identity/stdin,
the frozen executable hash/size, bounded finite collection deadlines, and
consistent decoded/raw terminal wait status. Each stream must have EOF, no
truncation or discarded bytes, exact byte counters, a limit no larger than the
packet, and a verified artifact matching the independent expectation.
Identity IDs, artifact sizes and byte counters must be plain integers, never
booleans. The finite monotonic fields `payload_monotonic_started`,
`payload_monotonic_deadline` and `payload_completion_observed_monotonic` must
prove completion was observed between start and deadline; the deadline must
equal start plus the declared payload timeout. A late observation fails even
when the original raw status is exit zero.

Collector statuses such as TIMED_OUT, OUTPUT_LIMIT, ORPHANED_DESCENDANTS,
CLEANUP_ERROR, LAUNCH_ERROR and SUPERVISOR_ERROR are collection outcomes, not
capability evidence statuses. They cannot satisfy the initial oracle. Even a
passing oracle still requires the actual pinned-Linux comparison and separately
verified McKernel launch/thread/route/cleanup evidence before OS acceptance.
