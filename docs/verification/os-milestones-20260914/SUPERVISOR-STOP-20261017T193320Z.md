# Campaign stop — 2026-10-17 19:33:20 UTC

The campaign stopped on a service-side `cyberPolicy` error. Worker498255 and
server498257 are absent; state is stopped/non-retryable, exit23, campaign goal
paused, zero active turns, included usage33% (stop97%). This is not a kernel-test
failure or quota exhaustion. Preserve launcher state, dirty sources and evidence.
The [incident receipt](supervisor-stop-20261017T193320Z.json) identifies the sources.

Supervision was marked blocked at19:41UTC after revalidation across three goal
turns. Scheduled reviews are deferred; establish a fresh review cursor when the
service issue is resolved and supervision is resumed. The OS goal is incomplete.

Report a suspected false positive through Codex `/feedback`, using these actual
failure identities:

- Campaign: `01a149eb-f950-7f13-95a2-59dfc2918d49`.
- Failed worker: `/root/native_shutdown_epoch_impl`, thread
  `01a14a67-d895-7f02-b120-1d19bcc61b12`.
- Failed turn: `01a14b4b-882b-7580-9caa-c158f5852e42`.
- Event:19:33:20UTC; state finalized19:33:21UTC. Console is
  `.git/os-autopilot/runs/20261017T125242Z-c770a25d/console.log`.

The incident's launcher footer instead names interrupted reviewer
thread01a149ec/turn01a14b59. At incident checkpoint7c2b87de, `restart_advice` read
mutable `last_turn`, which later interruptions overwrote.

Preparation update2026-10-18: the local launcher now records `last_failure`
separately, tied to the error and run, and reports its worker/turn. For older
states, a unique failed worker can recover the identity without editing state.
Preview now surfaces paused policy stops. The two launcher modules'121offline
tests and36recovery/fresh-CLI tests passed; independent source review passed.
Shared AGENTS.md/startup instructions require functional OS scope in every task.
These local changes neither clear the service error nor start the campaign.

Official OpenAI documentation describes `/feedback` as the command for reporting
issues with diagnostics: [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli#send-feedback-with-feedback).
No account-access remedy or successful appeal is established. Resolve the service
issue before an autonomous retry; a fresh conversation is not a workaround.

Current read-only commands:

```bash
python3 -B /home/holden/mckernel/scripts/run_os_parallel.py
python3 -B /home/holden/mckernel/scripts/run_os_goal.py --progress
```

The first command is preview mode without `--run`, `--check` or `--fresh-session`.
It starts no inference/server. These commands grant no execution release.
The observed preview returned exit0, `inference_started=false` and no technical
launch blockers. Its paused-goal branch does not surface this policy stop, and
preview never contacts the service. That output is not service clearance.

Retained progress and prerequisites after service review:

- HEAD7c2b87def80c4b9a8d1b63cabcca60ba9d7d24f7 pushed/fetched;103changed blobs
  verified, including75fork capsule files. Existing completion baseline remains
  immutable;14accepted app behaviors,1/10public native cycles, all14milestones open.
- FPU derivative imagea0f50854/7,908,616bytes passed build/artifact review and
  guard/owner/eight-client retirement. Both process.c.o copies are retained at
  SHA166b1419/319,704bytes. Exact stopped container and common/shared records remain.
- Cleanup sourcecb772ff4 and16fixture tests passed and were published. Observer
  9d3250c7/proposal6159d286 have one read-only observation approval. Its nonce-bound
  output directory was absent after the stop: observation and cleanup did not run.
  Reauthenticate current boot/mount/ownership/capacity, run only the exact reviewed
  observer after renewed admission, then obtain separate cleanup execution review.
  No lease/lock unlink or raw container removal; scratch21 remains untouched.
- Post-reboot workload proposal3ae8090 preserves the reviewed d99/942 runtime
  inputs. It awaits accepted terminal cleanup/common release and fresh384MiB-reserved
  admission. Its source/host checks do not prove workload execution after reboot.
- AVX packet uses the new FPU image. Review requires strict nested JSON type
  comparison and a new stage preserving original metadata: the current stage
  has41unapproved mtime changes. Preserve the failed stage. The reported comparison
  correction still needs exact-byte review; no AVX guest result exists.
  Read-only diagnosis locates the drift in prepare_stage_correction1.py:39:
  rebuilding through the pinned stager writes new file mtimes, while its line46
  comparison excludes mtime. The next correction should patch only image/SMP
  payloads in original newc records, preserving original headers/metadata/order,
  then use unchanged build_overlay for the application. Require exactly three
  content deltas and equality of all other record metadata. No archive was changed
  by this diagnosis; the frozen failing stage and manifest remain intact.
- Fork v2 has63sources/11tools; composite closure9492bea4 is separate from real
  Git identity. Corrected final proposald13a3d47 fixes exactly three stale paths;
  review was interrupted. Require final review, predecessor release and fresh
  admission before Kbuild. No fork compiler or native activation result exists.
- Accepted guest checked-destruction/ACK tests622033e6 use transport adapters.
  Real host revoke/final-publication join, normal-child and post-LINK paths remain
  open. Preserve partial work; do not promote it to runtime acceptance.

Keep GPT-6.1 routing, four-CPU/12GiB/no-swap/512-task heavy limits, one heavy owner,
16/12GiB storage floors plus each packet's full reserve, and the97% usage stop.
The targeted unprivileged process census found no matching QEMU/Rust/compiler/
native-owner tasks; this is not Docker/root identity or cleanup admission.
