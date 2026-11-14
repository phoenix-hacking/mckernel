# NUMA retained-reference expected-order correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Practical supported OS/apps and active compute Rust/assembly cutover remain the
scope. This packet changes no application, kernel, production oracle, release,
ownership record or earlier evidence. Only this new directory was written.

Status: source-only bounded correction prepared; checker has NOT been executed.
No compile/app replay, native execution, acceptance or C-retirement credit.

## Exact defect and source derivation

`../numa_interval_app.rs` declares a single `const PASS` at line14. Its full
bytes have `mask=1 neighbors=2 process=1 guards=1 bytes=12288`, in that order.
The final `write_all(PASS)` and `flush()` emit precisely that constant only after
all `consume` checks and successful unmap. The source proposal's exact stdout
paragraph independently specifies that same order. `expected.stdout` transcribes
that full constant including its sole final LF; it was derived from source,
not relaxed to match arbitrary captured output.

The failed top-level `../compile-reference-1/whole.json` instead contains
`mask=1 guards=1 neighbors=2 process=1 bytes=12288` in `expected_stdout_hex`.
Its retained actual hex/capture have the source-declared order. The strings have
the same fields/values and differ only in the position of the `guards=1` token.
The supervisor's expected value is the faulty boundary. No change to the Rust
application is justified. The original FAIL record remains authoritative history.

The original record reports successful compile, actual Linux normal exit37,
raw normal-status encoding9472, empty stderr and positive closure/release. These
are retained observations, not a new run or a reclassification performed here.
The application assertions are untouched: actual allowed-node witness; nine
policy queries; three target points with full meaningful mask checks; before/
after process and both distinguishable neighbor policies; output sentinels;
all12288 volatile byte checks; exactly one unmap with success required. DEFAULT
mask handling and all unsupported/error-as-failure behavior are unchanged.

## Proposed next observation after dispatcher grant

Use the reviewed ordinary CPU6, one job, 1GiB profile with no root/module/guest/
network/production execution. Fresh admission and aggregate resource checks are
dispatcher-owned; this source packet does not grant execution. The check reads
small retained files, creates no payload process and needs no compiler. Capture
its stdout/stderr/status under a fresh dispatcher-owned observation directory.
Proposed direct command, inside that profile with a bounded10second supervisor:

```sh
python3 /home/holden/mckernel-work/host-preparation/numa-native-app-consumer-20261021-1/stdout-order-correction-1/check_retained_reference.py
```

The checker pins the existing source/proposal/failed whole/captures by SHA256,
extracts the sole source literal using a deliberately narrow grammar, and
requires full-byte agreement with the independently transcribed expected file.
It then compares the retained stdout/stderr, status, timeout, errors and positive
closure to that full oracle. It refuses changed source or evidence. No sorting,
token comparison, field omission or wildcard is used for the success comparison.
A sorted-token check solely constrains the old-to-corrected change to field
ordering; exact byte equality remains mandatory for all success output.

The checker also has9 focused comparator vectors: one positive and8 negatives
(old wrong order, missing LF, extra LF, missing neighbor field, incorrect query
count, nonempty stderr, exit0, signal-style negative exit). Proposed success is
one JSON result with `PASS_RETAINED_LINUX_REFERENCE_EXPECTED_ORDER_CORRECTION`,
`regression_vectors=9`, `stdout_bytes=116`, `compile_or_app_rerun=false` and
`native_or_retirement_credit=false`, process exit0 and empty stderr. Any exception,
changed hash, mismatch, timeout or nonzero status fails. This source-only report
does not claim those vectors or the retained comparison have passed.

The original compiler/application are not to be rerun to resolve this defect.
This consumes the one bounded correction for candidate1's expected-order family;
any failed correction requires focused expert escalation, not another patch or
unchanged retry. A later native guest still requires current linked-image and
ABI proof, separate release and unchanged strict application/runtime oracles.

## Input and correction identities

All SHA256 values were read without executing the proposed checker/payload:

| Relative path under parent packet | SHA256 |
| --- | --- |
| `numa_interval_app.rs` | `0863c1e9ef2c3777f6ac9baeab33283afeac99b5d5ea374546ee6b24be886936` |
| `ORACLE-AND-PROPOSAL.md` | `404adb9c987884a6f5ede4eac6ed40d1d9bf3bdb551756c30585dbb24f311927` |
| `independent-review-1/ROOT-RECORDED-CORRECTED-SOURCE-AND-ORDINARY-ELIGIBILITY-2.json` | `4cd9b1282138faebff102a716c99a213c8845544e33482643b22bc42c54fe5e8` |
| `independent-review-1/ROOT-RECORDED-SOURCE-ORACLE-DECISION-1.json` | `2038b269953872e551032e0d7ba1fc69b87247c9dca6f6c78aef1184dc2d62f1` |
| `compile-reference-1/whole.json` | `0ce8675b23e20c3f7309d2c26bbd3e3e803be1e4731e58dc313626813d085e4b` |
| `compile-reference-1/02-linux-reference/stdout` | `ba0adb908f3f118b325873878bcc336107b8953e9b7a7f9e9e5abd8f37931bf2` |
| `compile-reference-1/02-linux-reference/stderr` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `stdout-order-correction-1/expected.stdout` | `ba0adb908f3f118b325873878bcc336107b8953e9b7a7f9e9e5abd8f37931bf2` |
| `stdout-order-correction-1/check_retained_reference.py` | `55480cdf5b9d81ddd41b3e3fc2d9a878d32e989a25f7dd1ee2d51ffd1f9733b4` |

Stop condition reached: concrete expected-byte data, narrowly source-bound
checker/regression source and command proposal prepared for review. No recursive
agents, questions, Git, leases, launcher edits or service requests were used.
