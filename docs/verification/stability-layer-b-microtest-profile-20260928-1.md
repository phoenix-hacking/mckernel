# Reusable Layer-B microtest profile 1

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the single reusable
unprivileged executable-microtest envelope required by `CONVERGENCE.md`. It
releases nothing unless an independent reviewer returns `PASS_LAYER_B` for
these exact command families, authority boundaries and initial input hashes.
It never authorizes root, a container, a module, a guest, hardware access,
production state, application acceptance or a production gate.

## Authority and disposable output

The dispatcher is the only execution owner. Work directory is exactly
`/home/holden/mckernel`. Every run uses a new absent directory below
`/home/holden/mckernel-work/scratch/stability-layer-b-microtest-<UTC>-<attempt>`.
The dispatcher creates only that directory plus `home/`, `tmp/`, `bin/` and
`logs/` beneath it, all mode 0700. Repository inputs are read-only to the
commands. All binaries, temporary files, command streams, statuses, resource
observations and the final manifest remain under that root until checkpointed.
Never reuse or partly clean a failed root.

Initial source bindings are:

| Lane | Path | SHA256 |
| --- | --- | --- |
| M02 | `scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/witness_owner.py` | `cd415301375a214e7f450b787c4832037e0fa046bbe17e4e6da8b7bc8f892232` |
| M02 | `scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/supervise.py` | `521a4d51225447424503446abdf8b4f11bb29380b618b8c3ff7a83c4e6c32e56` |
| M02 | `scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/oracle.py` | `7363f5a5401f32c1eb8efcd33acef8f1edc60a8d9a53d16e251fed0ba443f135` |
| M02 | `scripts/tests/test_collector_storage_fault_packet.py` | `b259ad30e1704580d14ff898dfdf9d70d7307f6c0eae51e1b95d157c72a58644` |
| M03 | `kernel/rust/tests/pending_free_inventory_harness_v1.py` | `50c8d0b72b0c65733e2b7b1326c0baf73430601910247770528430019f713766` |
| M03 | `kernel/rust/tests/pending_free_inventory_reference_v1.c` | `98011d27f8493614d31d2c141b851b5f1dab533f7f855a996490a5ca557543ce` |
| M03 | `kernel/rust/tests/pending_free_inventory_vectors_v1.rs` | `bf966b1226f4134609f565bb4e27d89ceff41a79fc842aeac7c8a05999668664` |
| M03 | `kernel/rust/tests/pending_free_inventory_v1.rs` | `746dc81ea27a45bdbb9ad00c37d2ad74a5d1f9e254943e4df34866a4274837fc` |

Changed candidate bytes may reuse only this same command and side-effect
envelope, with their new hashes recorded before execution. A command,
dependency, privilege, isolation, resource or side-effect change requires a
fresh independent profile review.

## Tools, environment and limits

Pinned tools are `/home/holden/anaconda3/bin/python3` 3.9.12,
`/usr/bin/python3` 3.8.10, `/usr/bin/gcc` 9.4.0,
`/home/holden/.cargo/bin/rustc` 1.60.0-nightly (`777bb86bc`), and
`/usr/bin/timeout` 8.30. Authenticate each absolute executable and version in
the run record. Each child receives only `LC_ALL=C`, `LANG=C`,
`PYTHONDONTWRITEBYTECODE=1`, `HOME=<root>/home`, `TMPDIR=<root>/tmp`, and
`PATH=/usr/bin:/bin`; stdin is `/dev/null`, umask is 077 and core dumps are
disabled.

Each command has a 60-second wall limit with TERM followed by KILL after five
seconds, 55 CPU seconds, 256 file descriptors, a 64-MiB output-file ceiling and
a 512-MiB address-space ceiling. Commands are sequential. Source inspection
shows at most one compiler/test parent and its bounded helper children at once;
the dispatcher must observe no more than eight processes in the command's new
session/process group and kill that entire group on timeout. The aggregate
campaign budget remains seven jobs/24 GiB; this profile consumes one job and at
most 512 MiB. Stop on the first unexpected status, timeout, resource breach,
input drift, write outside the disposable root or surviving group member.

No command may use network sockets, credentials, sudo/root/setuid, namespaces,
mounts, containers, devices, modules, repository launchers, `prepare.py`,
payloads, McKernel/native runtime, guests or external mutable state. Ordinary
local `fork`/`exec`, pipes, Unix socketpairs, `/dev/null`, repository reads and
disposable-root writes are the entire allowed side-effect set. Inspect the
process group and changed-path manifest after each command.

## Exact command families and required results

The resource wrapper is exactly:

```text
/usr/bin/timeout --signal=TERM --kill-after=5s 60s /usr/bin/prlimit --cpu=55 --as=536870912 --nofile=256 --fsize=67108864 --core=0 -- <command>
```

The dispatcher supplies the sanitized environment above without a shell.
Evidence capture outside the child argv may write its stdout, stderr, return
status and timestamps to `<root>/logs/<command-id>.*`; it may not transform the
streams or retry a failure.

M02 first runs the two focused tests together under Python 3.9, then the complete
137-test class under Python 3.9 and Python 3.8:

```text
/home/holden/anaconda3/bin/python3 -B -m unittest scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_real_child_descriptor_remaps_preserve_abi_and_close_leaks scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests.test_acquisition_sequence_and_live_identity_ownership
/home/holden/anaconda3/bin/python3 -B -m unittest scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests
/usr/bin/python3 -B -m unittest scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests
```

Each must exit zero and end in `OK`; the reported counts must be 2, 137 and 137.
The descriptor test must exercise real fork/exec fd 1/198 aliasing, initially
closed standard descriptors and inherited-sentinel closure. The acquisition
test's offset/gap/duplicate/reorder, failed-create-ID and cross-role live-inode
mutations must all reject. Any skip, expected failure, unexpected warning or
repository-byte change fails the profile.

M03 runs the exact harness once under Python 3.9:

```text
/home/holden/anaconda3/bin/python3 -B kernel/rust/tests/pending_free_inventory_harness_v1.py --execute
```

The harness's only compiler argv are:

```text
/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -O2 /home/holden/mckernel/kernel/rust/tests/pending_free_inventory_reference_v1.c -o <temporary-output>/pending_free_inventory_reference_v1
/home/holden/.cargo/bin/rustc --edition=2021 -C panic=abort /home/holden/mckernel/kernel/rust/tests/pending_free_inventory_v1.rs -o <temporary-output>/pending_free_inventory_v1
```

It executes both binaries once for each selector, in this order:
`empty`, `capacity-zero`, `capacity-exact`, `capacity-exceeded`,
`count-mismatch`, `count-overflow`, `duplicate-id`, `foreign-id`, `null-link`,
`dangling-link`, `one-sided-link`, `malformed-sentinel`, `foreign-cycle`,
`wrong-mode`, `invalid-page-count`, `page-count-overflow`,
`misaligned-extent`, `foreign-extent`, `overlapping-extent`,
`stale-generation`, `concurrent-mutation`, `valid-single`, `valid-two`.
Expected statuses are respectively
`-22,-28,0,-28,-22,-75,-22,-22,-22,-22,-22,-22,-22,-22,-22,-75,-22,-22,-22,-22,-22,0,0`.
Every binary invocation must exit zero and print exactly four pipe-separated
fields `selector|status|before_hash|after_hash`, with equal hashes. The harness
must exit zero with exactly
`PASS_PENDING_FREE_INVENTORY|executed=46|selectors=23|programs=2|state_hashes=equal`.

## Evidence, cleanup and scope

Record the profile hash, HEAD, all input and tool hashes/versions, absolute argv,
environment keys, limits, start/end times, status, raw stdout/stderr, peak process
count and memory where observable, pre/post repository status, output-tree
type/mode/size/SHA256 manifest, and the no-residual-process result. Preserve a
failed root and first-failure record unchanged. After a complete passing record
is committed and its fetched blobs verify, a later cleanup may remove only the
disposable root under the existing retention procedure.

A pass proves only Layer-B behavior of these finite candidates. M02 still needs
independent full-source review, conditional compiler review and later root/native/
guest qualification. M03 remains a finite private model that must be mapped to
production pending-free helpers, ABI, TLB acknowledgement and quarantine
ownership. Neither result changes application, language, production-gate or
whole-OS acceptance counters.
