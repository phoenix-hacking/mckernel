# Native lifecycle artifact I/O cleanup source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-artifact-io-cleanup-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to the accepted 133-case expanded-node checkpoint JSON SHA256
`c2ac5a4859571088ae5f6699f50bfd6a100ab0a025f07bd060803dbfb9042031`
and its exact source hashes. Edit only
`scripts/tests/test_native_lifecycle_model.py`, adding a separate
`NativeLifecycleArtifactFaultTests` class. Do not change the harness, vectors,
expected literals, artifact, models or gates. The raw inventory remains 133 and
both corpus flags and `RAW_FULL_MATRIX_FROZEN` remain false.

Use the unchanged accepted `raw-oversized-document` artifact description and
exercise the actual `artifact_bytes()` function. Before installing mocks, retain
the real `os.open`, `os.close`, `os.fstat` and `os.read` callables. For each
negative, inject exactly one `OSError(errno.EIO, "injected artifact I/O")` at the
specified operation:

| Test method | Exact injected operation | Required result |
| --- | --- | --- |
| `test_artifact_component_open_eio` | `os.open("tests", ..., dir_fd=...)` | propagate exact error; current directory descriptor closes |
| `test_artifact_leaf_open_eio` | final `os.open("oversized-document.json", ...)` | propagate exact error; final directory descriptor closes |
| `test_artifact_initial_fstat_eio` | first artifact-descriptor `os.fstat` | propagate exact error; artifact descriptor closes; no read |
| `test_artifact_read_eio` | first artifact-descriptor `os.read` | propagate exact error; artifact descriptor closes |
| `test_artifact_final_fstat_eio` | second artifact-descriptor `os.fstat`, after reading completes | propagate exact error; artifact descriptor closes; return no bytes |

Every injected call occurs exactly once. Assert exact exception class, errno EIO
and message; these are I/O cleanup tests, not decoder exit-2 cases. Track each
successful descriptor acquisition and close chronologically, including descriptor
number reuse. Every acquisition has exactly one matching close and the outstanding
set is empty on normal return or exception. Use the saved real `fstat` to prove
each recorded descriptor is closed with exact EBADF.

If an assertion observes a leaked descriptor, retain the test failure before a
`finally` recovery closes only descriptors still owned by the test. Recovery
cannot convert the assertion to success.

The sixth method, `test_artifact_positive_control`, performs one unmodified call.
It returns exactly 1,048,577 bytes with SHA256
`9a6384d7058b15fa74ef39f6bd6e5745a1fbec565abb06491714704d3d88e07c`,
opens the leaf once and leaves no outstanding descriptors.

For every method guard `subprocess.Popen`, `subprocess.run`, harness `raw_child`,
`build`, compiler entry and model `run` with unexpected-call failures and final
`assert_not_called`. No child, compiler, model, output directory or fixture-file
mutation is allowed. Read-only descriptor acquisition is the sole exercised
resource lifetime.

After independent source approval, run this class alone under the pinned Python
3.9.12 and 3.8.10 interpreters. Each lane must pass all six named methods. Retain
verbose commands, interpreter versions and binary hashes, exit codes and complete
streams. The evidence manifest binds the current four source hashes, artifact
size/hash, packet/review and two logs. Preserve any failed attempt and its exact
injection site. Label the scope `ARTIFACT_IO_CLEANUP_CHECKS_ONLY` and claim no raw,
model, compiler, native, application or production acceptance.

Existing checks already cover size/hash/path metadata rejection, symlinks,
single-open success, child timeout and stdout-overflow reaping. Defer selector
setup/close faults, stderr and child-exit variants, artifact metadata races and
nonregular files, and expected-output oracle corruption. `run()` has a separate
subprocess/output lifetime; this packet does not validate it.
