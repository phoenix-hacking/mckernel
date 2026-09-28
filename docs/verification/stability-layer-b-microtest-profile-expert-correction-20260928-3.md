# Layer-B profile expert correction 3 — archive binding and shutdown ownership

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the one expert repair
required by `stability-layer-b-microtest-profile-review-failure-20260928-2.json`.
It supersedes only the runner, retained-root binding, shutdown ownership and
interrupted-M03 evidence clauses of correction 2. Profile 1's prohibitions,
finite scope, and zero acceptance credit remain normative. No semantic test,
import, compiler invocation, or runtime execution was performed while preparing
this candidate; only Python AST parsing and whitespace/diff checks are recorded.

## Exact candidate and archive authentication

The only dispatcher entry point is the following exact command, from repository
root, with an absent output root whose parent already exists:

```text
/home/holden/anaconda3/bin/python3 -B scripts/tests/run_layer_b_microtests_v1.py --output /home/holden/mckernel-work/scratch/stability-layer-b-microtest-20260928-3
```

Before it creates that root or starts any command, the runner authenticates every
repository input carried forward from correction 2, then authenticates this exact
retained archive and its three exact, regular-file members without extraction:

| Input | SHA256 | Exact consumed member |
| --- | --- | --- |
| `docs/verification/evidence/stability-linux-collector-root-success-20260915-2.tar.gz` | `ad7c670311f6756cf64610e1d3e0dbdcdb026f86857c8461c3295cc34c17a721` | n/a |
| fixture | `9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725` | `stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/fixture` |
| request | `e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716` | `stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/request.bin` |
| selected inputs | `6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d` | `stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/selected-inputs.json` |

The test module opens those exact archive names through its fixed `ROOT_PREFIX`.
`input-authentication.json`, written after the output root is created, retains
the archive/member names and observed hashes. Archive or member drift stops before
any command and creates no output root.

Candidate hashes are:

| Path | SHA256 |
| --- | --- |
| `scripts/tests/run_layer_b_microtests_v1.py` | `09eeadf5986981c254d4f3fcfd2cf8e8dc18640b547cfc5b5f9d2c068d97bd9b` |
| `kernel/rust/tests/pending_free_inventory_harness_v1.py` | `95098a30d43596b3a80be9f0e56ecd4bb13e0514254d60207953be313fca89f1` |
| `kernel/rust/tests/pending_free_inventory_reference_v1.c` | `2755ba19e0d7083895daf82f815aca84090a0231d46c119bab93248467490aa6` |
| `kernel/rust/tests/pending_free_inventory_v1.rs` | `26d1528f296979683850a846bb7a600a451a75a51db50f4d0900e9bdddc6b742` |
| `kernel/rust/tests/pending_free_inventory_vectors_v1.rs` | `bf966b1226f4134609f565bb4e27d89ceff41a79fc842aeac7c8a05999668664` |

The runner's repository binding has been updated to the new harness hash. The
runner is intentionally not self-hashed: its exact hash is bound by this profile
and must be verified by the dispatcher before launch.

## Exact released command families and unchanged bounds

After authentication, the runner creates mode-0700 `home`, `tmp`, and `logs`,
uses `LC_ALL=C`, `LANG=C`, `PYTHONDONTWRITEBYTECODE=1`, `PATH=/usr/bin:/bin`, and
only disposable `HOME`/`TMPDIR`, then executes these three commands sequentially:

```text
/home/holden/anaconda3/bin/python3 -B -m unittest scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_real_child_descriptor_remaps_preserve_abi_and_close_leaks scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_acquisition_sequence_and_live_identity_ownership
/usr/bin/python3 -B -m unittest scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_real_child_descriptor_remaps_preserve_abi_and_close_leaks scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_acquisition_sequence_and_live_identity_ownership
/home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/kernel/rust/tests/pending_free_inventory_harness_v1.py --execute --output <root>/m03
```

Each command gets a new session, no stdin, umask 077, core 0, CPU 55 seconds,
NOFILE 256, FSIZE 64 MiB, AS 512 MiB, wall limit 60 seconds, at most eight
observed exact-session processes, aggregate observed RSS at most 512 MiB and
observable disposable-root data at most 256 MiB. Commands remain one aggregate
campaign job and are not containers, guests, root, native runtime, network,
module, payload, `prepare.prepare`, or production execution. The full M02 class
remains unreleased.

## Exact-session ownership and failure retention

For every successful child spawn, the runner durably records a `STARTING` command
record before launch and then records direct-child PID, session ID, and Linux
startticks before monitoring. Its `finally` path runs for normal completion,
test/resource failure, output-observation failure, `SIGTERM`, and `SIGINT`.
It sends TERM to the exact session process group and every observed exact-session
member, requires two empty `/proc` observations, sends KILL if needed, requires
two further empty observations, and directly reaps the original child. All
signal, member, observation, PID/session/startticks, return-status and final
residual observations are retained in the terminal command JSON. A leader that
has exited while descendants retain its session is a failure and is cleaned before
the runner returns failure. Only a disappearing filesystem/proc entry during
observation is tolerated; other observation errors invoke emergency group KILL,
direct-child reap and a retained incomplete-cleanup failure rather than abandoning
the child.

The main runner converts an original error into durable `failure.json` and
`failure.txt` only after the command terminal record; it does not retry. The
outer runner remains the final process owner for all three sessions.

For M03 specifically, the harness writes `<command>.start.json` with its full
argv/timestamp before it forks each compiler/vector command, then updates that
record with the child PID. `SIGTERM`/`SIGINT` writes durable `failure.json` and
`failure.txt`; the interrupted command's terminal record is explicitly
`UNOBSERVED` if its status was not returned. It deliberately does not TERM/KILL
its compiler/vector child: the outer exact-session supervisor owns final cleanup.
Raw stdout and stderr stay in their individual files; completed evidence and
binaries are never deleted.

## Required review and remaining scope

An independent Layer-B reviewer must inspect the complete current diffs, archive
member/name binding, command-start durability, signal/reap behavior and static
results before returning `PASS_LAYER_B`. A pass would release only these four
focused M02 tests and 46 finite M03 executions. It grants no `PASS_SOURCE`,
application case, production/language gate, root/native/guest, ABI, TLB or
external-qualification credit. Any first run failure is retained admission
evidence; any command, source hash, archive member, limit, process topology or
side-effect change requires a new review.
