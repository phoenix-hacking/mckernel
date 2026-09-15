# Native lifecycle output-envelope source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-output-envelope-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to aggregate preflight-byte checkpoint commit
`d53375021ac1a358bba67048410aace471674615` and checkpoint JSON SHA256
`1efed111f50b8aa27e9fddaf52fd4b791de398002fc77fca82c5ce16deaea1b0`.
Preserve its recorded source hashes, the 135-case raw inventory, harness,
fixtures, ordinary/expected literals, artifact and output-oracle tests. Allow an
edit only to `scripts/tests/test_native_lifecycle_model.py`, adding the separate
`NativeLifecycleOutputEnvelopeTests` class. Keep both corpus flags and
`RAW_FULL_MATRIX_FROZEN` false.

Reuse the independently bound one-row literal R from the output-oracle packet;
do not derive it from model output. Its compact bytes B are exactly 192 bytes
with SHA256 `4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a`.
Define:

- `BASE = B + b"\n"`, exactly 193 bytes.
- `FIT = B + b" " * 1048383 + b"\n"`, exactly 1,048,576 bytes.
- `OVER = B + b" " * 1048384 + b"\n"`, exactly 1,048,577 bytes.

All three contain otherwise valid single-row JSON. Pin `MAX_OUTPUT == 1048576`;
do not alter a boundary constant to make the tests pass.

Mock `module.subprocess.run` with
`subprocess.CompletedProcess(command, returncode, stdout, stderr)`, where command
is exactly `["/model-not-executed"]`. Call the actual
`module.run(command, b"MODEL2 256 NONE\n")`. Add exactly these five named tests:

| Method | Injected `(returncode, stdout, stderr)` | Required first outcome |
| --- | --- | --- |
| `test_output_nonzero_status_before_parse` | `(1, BASE, b"")` | return-code/stderr assertion |
| `test_output_stderr_before_parse` | `(0, BASE, b"x")` | return-code/stderr assertion |
| `test_output_size_over_before_parse` | `(0, OVER, b"")` | `MAX_OUTPUT` assertion |
| `test_output_baseline_control` | `(0, BASE, b"")` | exact `[R]` |
| `test_output_exact_size_limit_control` | `(0, FIT, b"")` | exact `[R]` |

For every negative require exact built-in `AssertionError`, empty exception
arguments, and zero calls to wrapped `strict_bytes` and `validate_output_row`.
This proves rejection before parsing. For each positive require exactly one
parsing call and one `validate_output_row(R, 1)` call. Then require successful
`assert_oracle_match([R], actual, [R])`.

For every case assert the exact mocked subprocess call: input bytes,
`stdout=subprocess.PIPE`, `stderr=subprocess.PIPE`, timeout 10 and `check=False`.
Guard real `Popen`, build, compiler and raw-child entry points against calls.
Assert no child or output directory exists and no fixture byte changes. No
process exists to reap. This packet tests validation after `subprocess.run` has
already captured output; it does not prove bounded live memory, timeout cleanup
or stderr collection limits.

Run all five methods verbosely under the pinned Python 3.9.12 and 3.8.10
interpreters after source review. Require 5/5 each and retain exact commands,
version banners, exit codes and streams. Evidence uses ten members: the four
source files, unchanged oversized artifact, packet and review, manifest and two
verbose logs. Bind current source and interpreter hashes, three negatives, two
positives, exact sizes, the literal hash, unchanged raw count 135, mock-only
execution and every false gate. Preserve any failure separately.

Representative output row/event/control corruptions are already covered; the
remaining schema-field matrix stays deferred. Standalone serialized-output-size
rejection remains masked by conservative traversal charging. Concurrent artifact
metadata/content changes and live collection bounds require separate packets.
No raw-full-matrix, compiler, model, native, ABI, application or production
release follows.
