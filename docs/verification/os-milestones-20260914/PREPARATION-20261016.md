# Prepared autonomous parallel run

Preparation only: the saved dispatcher remains paused/stopped on thread
`01a0a312-8c59-7c80-93de-0b64adde646b`, with no active children. HEAD and the
local origin tracking ref remain `42fde3aae0572022324fe9090793a5166059993b`.
All existing dirty work and evidence are retained. No build, guest, campaign,
cleanup transaction or execution release was run. The CLI settings check starts
only a temporary local app server and makes no model calls.

The user will run this command when ready to authorize autonomous execution:

```bash
python3 -B /home/holden/mckernel/scripts/run_os_parallel.py --run
```

Preview and settings-only checks are also available:

```bash
python3 -B /home/holden/mckernel/scripts/run_os_parallel.py
python3 -B /home/holden/mckernel/scripts/run_os_parallel.py --check
```

The entry point reuses the existing launcher, saved objective, watcher, usage
guards and selected models. It defaults to no time cutoff, chooses the measured
maximum child pool, and verifies the effective CLI configuration before resume.
This host admits **12 children / 7 aggregate host jobs / 24 GiB planning RAM**,
leaving 4 GiB measured RAM headroom. This is a ceiling for useful disjoint lanes,
not a requirement to manufacture twelve jobs. All local work shares that budget.
One heavy operation remains serialized under its reviewed 4-CPU/12-GiB/no-swap/
512-task profile. No guest concurrency or larger privileged profile is released.
Actual inference availability, quota and eventual throughput remain untested.

The known queued hold is
`20261017T021032370649Z-e1d9b3466e7c4dcfb8838159453e3bf2`. Its exact original
bytes remain pending. `PARALLEL-RESUME.md` reconciles that previous stop only
when the user invokes `--run`; it is supplied in `thread/resume` before goal
activation, including if the old message is delivered later. A SHA-256 argument
pins that instruction across preflight and automatic recovery. Unknown pending
instructions, uncertain delivery, active turns, held launcher/development locks,
present saved PIDs, mount/control drift or inadequate capacity refuse launch.
The wrapper does not write launcher-owned state or bypass execution reviews.

Read-only scratch21 observations and the cleanup DRAFT are in
`../evidence/os-preparation-20261016/scratch21-live.json` and
`../evidence/os-preparation-20261016/scratch21-cleanup-review.json`.
The full container ID is
`e1f6dd145149c026c46adb82c3f3addb9e3c9e2a12b0d71a6813f00895220ea9`,
owner nonce `1439909012a04cf789981b951b34d399`, exited/PID 0/status 1/non-OOM.
All five checkpoint-bound failure digests and 40 owner-evidence entries were
observed. The process census reports no heavy/owner publisher and the preserved
root development lock `27:4` has no holder. The request lease is absent.

Scratch is `/dev/loop36`, ext4 UUID
`2a5768c8-718d-4914-bdc0-6b32c5a92a52`, rw,nodev,nosuid. Both exclusions retain
their original bytes and inodes **57687/57688**, on live device **1828** rather
than historical **1831**. Current boot ID is
`7bfc5687-6c04-4d15-84eb-b92ab9a55dcb`. These are observations, not future release
authority. Refresh them immediately before any later cleanup review/release:

```bash
python3 -B /home/holden/mckernel/scripts/inspect_scratch21_cleanup.py --live
```

That observer contains no removal or release code. The cleanup transaction is
still a blocker: implement the DRAFT's scratch21-specific exit-1/profile/evidence
bindings, current UUID/boot/device identity, root-lock lifetime and crash-safe
archival transaction. The referenced scratch18 executor is an algorithm reference;
its old paths/device/boot/exit-zero policy are unsuitable. Test disposable crash,
drift and uncertainty cases, publish/fetch exact code, then obtain independent
source/execution reviews. No valid cleanup `--execute` command exists yet.
Never raw-remove the container, unlink the locks or replay scratch21.

Source changes are reviewable in
`../evidence/os-preparation-20261016/source-authority-review.patch` and its JSON.
Staging now binds the actual v6 constructor, shutdown scalar callback type and
callback header; lifecycle binds the current runtime contract. The ledger's
stage-manifest lock and self-digest are corrected without claiming acceptance.
Build-surface audit, staging integrity and lifecycle source checks pass;
**121 staging/lifecycle tests pass**. The staging gate retains four original
readiness blockers. **74 offline launcher/entry-point tests pass**, including
the initial resume note, digest drift, queue preservation, lease admission and
existing watcher/transport behavior. The actual settings-only preflight confirms
12 children, depth 1, existing models and the injected shared build environment.

RS-011 still refuses `os_runtime.rs:199`: the new shutdown-v6 extern function
type lacks its own nearby SAFETY binding. Its test module also eagerly discovers
sources and refuses import there. Initial and bounded-correction failures are
retained and logged in `kernel.log`; do not repeat them unchanged. An expert must
review the safety contract and changed unsafe/FFI inventory, preserve durable IDs
and pending review/compiler statuses, and rebind all affected authorities before
the full source/test sequence can pass. Do not weaken discovery or mark it ready.

After that correction, run each source check in order and stop on failure:

```bash
python3 -B scripts/native_rust_build_surface_audit.py
python3 -B scripts/rocky_rust_staging.py --check
python3 -B scripts/ihk_native_lifecycle_check.py
python3 -B scripts/native_rust_unsafe_ffi_ledger.py check
python3 -B -m unittest -f scripts.tests.test_rocky_rust_staging scripts.tests.test_ihk_native_lifecycle_check scripts.tests.test_native_rust_unsafe_ffi_ledger
```

Fresh scratch22 needs accepted scratch21 cleanup and reviewed, pushed/fetched
source commit/tree identities first. Create a new preparation adapter/request/
candidate/output/evidence/lease namespace; none exists or is released now. Bind
the new exact delta and inherited defaults explicitly (scratch19 failed on a
stale Python default), preserve the target owner's pinned scratch18 operational
exclusion slot (scratch20 failed there), and remeasure UUID/device/capacity.
Authenticate all 486 shared evidence inputs across retained scratch15/16/17/18/
20/21: expected initial link count is six only if the fresh census proves it,
then seven after scratch22 materialization. Never hard-code those counts without
the alias census. Canonically validate the new owner/request; the preparation
request must remain non-executable. Independent prepared-artifact review and a
new one-shot heavy-build release follow; scratch21 authority cannot transfer.

After a new accepted artifact, prepare/review `signal.mask-restore`, exact stdout
`handled=1 observed_blocked=1 restored=1\n`, exit 0, with fresh result/teardown.
Parallel source lanes may advance fork ownership, shutdown and other ready work
with disjoint write sets while these dependencies are repaired. Full acceptance
still requires all original contracts, soaks, platform/hardware and external
qualification. Counts remain 3 builds, 12 bounded diagnostic passes, 0/273 formal
applications, 6/130 production gates and 0/7 languages; the OS is incomplete.
