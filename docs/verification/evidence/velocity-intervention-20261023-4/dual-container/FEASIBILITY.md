# Concurrent P12 and M14 compile/link feasibility

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**NO-GO with the unchanged M14 owner. Conditional GO for one private CPU6, 4GiB, pids128, -j1 compile/link container after one exact build-only exception is independently reviewed.** Do not delay or interrupt the running SDK8 LONG. This plan grants no native guest execution.

The saved live caps retain heavy_jobs=1, seven aggregate build jobs and22.525852GiB planning memory. os_goal_resources.py/START.md already permit reviewed isolated light Docker overlap; neither changes container limits or provides a compile-only owner switch. Candidate14 has the pure source/default-consumer driver prepared. Its current request uses jobs4,12GiB aggregate, immutable image41778f1f..., and a sole-heavy image owner. Extra Docker alone does not solve its admission conflict.

| Lane | CPUs | RAM | Tasks | Ownership |
|---|---|---|---|---|
| Existing P12 LONG |2-5,4CPU|12GiB, no extra swap|512|Existing sole-heavy/native owner; controller7|
| Proposed M14 compile/link only |6,1CPU|-j1,4GiB, no extra swap|128|Separate private HOST compile lease; controller6|
| Other ordinary work |0|Shared remaining allowance|Existing bounds|No new compiler on6|

Keep CPU7 for control and P12 cpuset unchanged. First finish/directly join m14_actual_consumer_fix and explicitly reassign its CPU6 grant. Taking0,6/6GiB/-j2 offers unmeasured benefit and consumes foreground observer capacity; it is not selected.

At 2026-10-23T21:38:34Z, ordinary/proc filesystem reads found MemAvailable=25.501GiB, allowed CPUs=[0, 2, 3, 4, 5, 6, 7], HOST free=157.643GiB, scratch free=13.133GiB, remaining sparse backing gap=14.751GiB. This is planning evidence, not launch admission. Require fresh MemAvailable >=24GiB conservatively: P12 max12 + M14 max4 + P12-controller allowance2 + M14-controller allowance2 + host reserve4. This intentionally does not subtract already resident P12 pages. Container tmpfs/pagecache is included in its4GiB; HOST output/cache and source are disk backed. Stop additional local compiler work rather than multiplying per-agent memory shares. Preserve existing packet disk reservations, full remaining sparse gap, capture/output/emergency budgets and16/12GiB HOST/scratch floors.

## Exact coupling that must change

The candidate14 private owner calls acquire_heavy_operation(request,"image") at run entry before validation; its shared contract accepts only build/image/guest and takes scratch/mckernel-heavy-operation.lock. LIMITS, RESOURCE_ARGS, effective-profile verification and request aggregate checks still require4CPU2-5/12GiB. The older guarded_execute additionally acquires /run/lock/mckernel-development.lock for the entire image build. That permanent dev27:ino4 mutex and all P12/native ownership must stay intact. Do not unlink tokens, rename a running owner, or run a second native guard.

Prepare a **private successor of the existing image owner**, pinned to this one reviewed compile/link exception. Replace only its resource/admission classification with a private HOST O_EXCL compile-only lease and explicit24GiB shared-capacity check. Retain fresh common/output ownership and exact identity/retirement checks. Do not globally add a skip-lock flag or raise heavy_jobs. The independent review must explicitly accept that this bounded build is outside the native/heavy reservation; without that acceptance the old exclusion remains decisive and the build waits. No changes to live P12 or canonical/state controls are needed or authorized by this preparation.

## Smallest next preparation

Starting source: /home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/next-build-preparation-1/native_rust_exact_mckernel_image_container_owner.py. Starting request: /home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/next-build-preparation-1/image-request.PREPARED.json. Existing driver: /home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/native_rust_exact_mckernel_image_offline.py. Its jobs argument already accepts1 and its targets are production Rust object then mckernel.img, using the retained kernel/toolchain inputs; no full Linux rebuild is necessary. Preserve native_fork_owned_transaction=True as a compile-time product selection, not a native launch.

Create the five PENDING files listed in FEASIBILITY.json: private successor owner, successor request, exact profile, operation/argv, and ordinary capture. Set matching requested **and inspected** profile to1CPU6/4GiB/pids128/no extra swap/jobs1. Pin all existing candidate14 source/GCC14 image/toolchain/kernel inputs as readonly; sole writable bind is a fresh HOST work root here, including private output/cache/evidence. No scratch writes, writable shared cache, IHK/QEMU/module/device controls, source integration or native execution. Keep existing source/ABI/default-link/artifact checks.

Reuse the existing990807ab... owned_capture lifecycle used by run_selected_consumer.py, with a separately reviewed whole-image compiler deadline rather than its90-second selected-TU limit. The precise proposed owner argv and Docker resource fragment are in FEASIBILITY.json; they reference PENDING files and are **not executable releases**. No new universal runner/framework is needed, but an unchanged existing operation cannot launch this safely.

Review must bind exact successor owner/request/driver/profile/argv/capture hashes, live P12 identity, CPU6 handoff, fresh shared memory/storage headroom, readonly mount allowlist, private lease and terminal/container removal proof. Only then may the coordinator launch this one compile/link lane while retaining P12 as sole native/heavy owner. Unexpected failure retains its separate evidence/lease and stops the new lane; no automatic retry or P12 interruption.

If review is not ready promptly, keep ordinary productionRust/GCC9 progress and defer full GCC14/default image until LONG normal terminal plus physical acceptance. No Docker, root command, probe, test, build, guest, cleanup, resize or live-control mutation was performed for this feasibility task.
