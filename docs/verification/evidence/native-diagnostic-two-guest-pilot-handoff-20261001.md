# Two-guest diagnostic pilot handoff — 2026-10-01

Status: **reviewed for diagnostic-only use**. The first four two-guest runs
reported `DIAGNOSTIC_PASS`; all summaries set `application_acceptance: false`.
They do not grant formal application, production-gate, or whole-OS acceptance.

Source for each row: `/home/holden/mckernel-work/scratch/dual-guest-<ID>/summary.json`. The SHA-256 values identify the exact scratch summaries read for this handoff.

| ID | Two reported cases | Pair phase (s) | Summary SHA-256 |
|---|---|---:|---|
| `kq8d_z5l` | `startup.argv-empty` × 2 | 38.773 | `177e27ef2e37b750b18f1109b96278965e78725c6181dbf9deee7be8bbb80030` |
| `mgykqibk` | `baseline.core.memory`, `baseline.core.files` | 39.159 | `b860949b28039346555aba0207162109d0829b7c961f91cdb3dc438845c8bf0e` |
| `w4ah3pqr` | `baseline.core.threads`, `diagnostic.native-ultra-futex` | 41.170 | `9b8ed7ceed50691498ac239213663d2567e9868548af8e06bb15757a628fb519` |
| `s36rblwx` | `baseline.core.signals`, `startup.argv-empty` | 39.364 | `10d7f7f56ab3dd14aeb8564ca1ad1e7b51cd80af3cdca32beb1441e07a920b1c` |

Resource profile: each summary records disjoint host CPU sets `2,3` and `4,5`, mapped to four distinct physical cores. The pilot configuration uses two CPUs and a 7 GiB/no-swap, 256-task container limit per guest, with a four-vCPU, 6 GiB, two-NUMA-node guest profile. Preflight snapshots show about 31.1 GB available host memory, 38.9 GB free repository storage, and 34.2 GB free scratch storage; these are **not peak-use measurements**.

The four measured pair phases total 158.466 seconds for eight guest results, or about **3.03 guest results/minute during the pair phase**. `concurrent_guest_seconds` starts before guest attach and ends after result inspection; it excludes setup and cleanup. There is no serial control here, so this is not an end-to-end throughput or speedup claim.

Handoff caveat: pilot safety fixes and independent review remain ongoing. Preserve the scratch summaries and per-guest result files for review; do not promote these diagnostic passes into formal acceptance or use them to close resource, timeout, ownership, or cleanup safety questions.

After the cleanup, input-binding, log-cap and positive-overlap changes, a fifth
startup/signals pair passed at `dual-guest-vxg5lb71/summary.json` (SHA-256
`0adfa4fea41454ef7ecc15b6cec322407875b914178aaaf5b7e9b18788fc5572`).
Its Docker state intervals overlapped for **38.191 seconds** of a 38.764-second
pair phase. Both exact CIDs exited 0/non-OOM, produced `PROTOCOL_PASS` with
`application_acceptance: false`, and were removed after the run. The new source
also hashes both manifests and all four Python runtime files before and after
the guests, verifies exact bind sources/destinations, and caps Docker logs and
guest file size. These are stronger diagnostic controls, not formal release.

The subsequent source-sealed revision passed another startup/signals pair at
`dual-guest-3lgmesb0/summary.json` (SHA-256
`54e250de49e60323577d22da049546fb0089c8c9d2c5abce554c32a361661793`).
It recorded **38.803 seconds of actual Docker-state overlap** in a
39.843-second pair phase. The four runtime Python files were copied, hashed,
made root-owned/read-only, and executed from that private source directory;
the summary contains both original and runtime-source SHA-256 maps. Both
guests returned diagnostic PASS and their containers are absent. The pilot
also now requires exactly two guests and rejects host PID/IPC namespaces or
added capabilities. The remaining operational caveat is an indefinitely hung
Docker `create`: the owner keeps its lock while waiting so an in-flight daemon
create cannot appear after cleanup. This does not establish a formal execution
release, peak resource measurement, or application acceptance.

The next revision moved the four runtime files **and both manifests** to an
exact root-owned, mode-0555 directory under sticky `/run/lock`, with each file
root-owned/mode-0444. The two containers mount that directory read-only and
execute its runner against its manifest copies. A fresh startup/signals pair
passed at `dual-guest-_v1mu8cd/summary.json` (SHA-256
`5680a8f5242e786d621cd08445781c74fffa4c49e5d7bfce441edf1041ddffbb`),
with **38.070 seconds of measured overlap** in a 40.642-second pair phase;
both owned containers were removed. Manifest-referenced kernel/guest artifacts
remain at their validated original paths and are not copied into the sealed
directory. This is therefore still bounded diagnostic evidence, not formal
acceptance or proof against malicious concurrent mutation of those artifacts.

Final independent read-only re-review found no remaining concrete P1
false-PASS or started-guest stranding blocker for diagnostic-only use. It
explicitly limits that conclusion to quiescent manifest-referenced artifacts;
the sealed code/manifests do not make those referenced bytes immutable. A hung
Docker `create` is fail-closed but can retain the development lock indefinitely.
The autonomous campaign was restarted and given these restrictions by live
instruction. Do not count the pilot replays as new formal M0* credit.
