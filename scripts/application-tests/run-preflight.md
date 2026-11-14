# Metadata-only application runner entry point

`run.py` now implements the planned CLI as a **preflight only**. It cannot launch
a process or invoke a guest backend, and it has no execution override. Every
report has `execution_status: NOT_RUN`, `backend_implemented: false`, and false
application/transport/production acceptance. Even a fully eligible synthetic
metadata bundle produces top-level BLOCKED. This does not change any original
catalog, packet, oracle, drafting report or runtime gate.

The public function is:

```text
preflight(inputs_path, *, case_id, attempt_dir, profile, mode) -> report
```

The CLI accepts `--inputs`, `--case`, `--attempt`, `--profile baseline-root-1cpu`
and `--mode differential-guest`. It returns code 2 for a retained BLOCKED
preflight and code 1 for failure; it never returns a successful execution result.
Standard argparse help/argument handling is separate from preflight status.
All paths must refer to actual reviewed inputs; explanatory placeholders are
not runnable manifests. There is no request to execute this command as an
application test in this source-only implementation phase.

The attempt directory must be absolute and canonical with an existing canonical
parent. Creation is exclusive; an existing path or symlink is not reused. Invalid
attempt paths raise before writing into them. After creation, validation errors
retain the available capture and a FAIL report. Storage errors that prevent
publication propagate to the caller; they cannot grant release or silently
overwrite a prior report. The parent must capture CLI output and immediately
log any unexpected first failure using the established workflow.

An attempt contains the exact request, source and input copies under `inputs/`,
an original-to-retained `retention-index.json`, and `report.json`. The source
copies include this entry point, the existing runtime-contract module and the
unchanged catalog. Original manifests are copied byte-for-byte, including their
original absolute references. They are not rewritten to resemble executed or
local provenance. The index is the explicit mapping for later restoration and
review; the retained copies do not form a separately authorized runnable bundle.

Capture follows the runtime schema's declared selected-input, capability,
execution-packet, oracle and proof-artifact references. Compiler-binding and
other opaque proof blobs are retained without recursively interpreting fields
inside them as paths. This scope does not prove the complete compiler closure,
installed guest root, effective isolation, actual loader mappings or the truth
of a capability claim. The backend integration map names those separate seams.

The fixed initial capture bounds are 256 reference uses (including repeated
references) and 95 MiB aggregate distinct-path declared bytes, including the
runner's own source/catalog. Repeated references reuse the retained bytes and
parsed manifest; the use bound also limits later validator work. Every regular
artifact also obeys the existing less-than-95-MiB per-file bound; manifests are
at most 4 MiB. Lower aggregate availability can reject an otherwise eligible
bundle and must be reviewed explicitly, not bypassed by a CLI flag. Data is
streamed in 64-KiB chunks. Symlinks, FIFOs, directories, stale byte/hash claims,
conflicting claims for one path, changed files, and bound overflows fail closed.
A failed partial copy remains retained with its actual bytes/hash. A detected
growth byte beyond the declared size is explicitly marked as observed but not
retained; that capture cannot be complete. Files and directories are fsynced
before a successful preflight function return.

The implementation uses `load_runtime_bundle` and `validate_case` without
modifying either. The loader consumes the retained root bundle, so a temporary
replacement of the original root cannot substitute different metadata while
leaving a valid final hash. Nested references preserve their original paths
and frozen hashes. It rechecks all original and retained byte identities after
the validator returns. The existing loader still supplies duplicate/nonfinite
JSON rejection, exact catalog binding, one-to-three-case selection, source and
oracle review requirements, finite resource bounds and required capability
gates. No missing or unsupported capability becomes PASS. Dependencies and
unsupported predicates remain blocked under the existing contract. Any nested
metadata PASS is explicitly scoped to eligibility and cannot change the
top-level execution block.

The twelve source-only tests in `scripts/tests/test_application_run.py` use the
existing synthetic metadata fixture, never an ELF or module capable of running.
They cover an eligible-but-blocked bundle with exact retained bytes, missing/
blocked/unsupported/disabled gates, unselected cases and unsupported predicates,
raw malformed JSON retention, exclusive/path-safe attempts, real FIFO rejection,
stale inputs including a change after validation and a temporary original-bundle
swap restored before final rehash, stale capability binding,
increased limits, capture bounds including repeated-reference work, and the exact
CLI with no execution switch.
Process-launch functions are guarded against calls. Every toy input, attempt,
source copy and CLI result remains under printed TMPDIR paths; none are deleted
automatically. The parent owns their future pinned execution and its evidence.

Actual execution requires the separately reviewed backend/guest collector,
preparation schema, paired Linux/McKernel evidence, payload-versus-launcher
observations, original fault gates and an explicit packet release. Those remain
unimplemented here. Do not wire `supervisor.run_supervised` into this entry point
without that additional reviewed integration.
