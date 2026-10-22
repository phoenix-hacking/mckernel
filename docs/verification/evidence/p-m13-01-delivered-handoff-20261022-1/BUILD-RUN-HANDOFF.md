# Delivered tested205 build/run handoff — P-M13-01

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is the actual concise handoff for the accepted **tested205-ff4f-current-host-c396-af234-6571-two-cpu-20261019** configuration. The delivered files provide instructions and retained artifact identities now; they do not grant execution or claim final whole-OS acceptance. Literal check: **“Publish concise build/run instructions and tested artifact identities.”** [The individual-check priority](/home/holden/mckernel/docs/verification/os-milestones-20260914/CONVERGENCE.md) permits this existing accepted profile; new candidate modules and whole-M13 closure are separate.

## Use the tested artifact set

[The delivered identity manifest](tested-artifact-identities.json) gives full retained paths, byte sizes and SHA-256 values. Keep every matching component:

| Component | SHA-256 |
| --- | --- |
| McKernel image | `ff4fca457e9ffe50dc4eca930c5f91faf317eeee15bf0c2907067cffa77b23bb` |
| ihk.ko | `c396958bfdb0f22036b469ea2a64e0a6b188b9619ee4105c7879483bb3b9790d` |
| ihk-smp-x86_64.ko | `af234fbcd09327a80e12396eebbfbcd30838f88a552fa13ba00a2728a761eeaa` |
| mcctrl.ko | `6571ac7eca13559d8bab65125d54facbbc65e84f815d4ff3fc77ec6aa1104972` |
| mcexec | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| native-boot | `4312f9a8f53d8db7b2b6be4c7d5e409f5c0f82cf8215728209be0f6ff4a5d5c5` |
| Rocky/Linux6.12 bzImage | `032653ee0661b059c325e2a0911a9d492805f1a889c4df515473d69a8be105bc` |
| base initramfs | `605d5c27c38d3c5e68dba2483bd782939aba7fcea13feb47cab7c3e0a2bb7abd` |
| Rust app0 | `024fa5620735622c684283df1a8270c2d7c78f62dd82d294c544f5eb3b197ac4` |
| Rust app1 | `1f51f0e3c8288bc05aabbc0309d1bf84abab1cbc6d8593c4ec7b1460b38163b7` |

This exact image/module/app pairing is already accepted in the [profile freeze](/home/holden/mckernel/docs/verification/evidence/current-host-pair-205-native-20261019-1/P-M00-01-SUPPORTED-PROFILE-FREEZE-REVIEW.json), [usable recipe](/home/holden/mckernel/docs/verification/evidence/current-host-pair-205-native-20261019-1/usable-profile-1/USABLE-TESTED-PROFILE-RECIPE.json), [matched manifest](/home/holden/mckernel/docs/verification/evidence/current-host-pair-205-native-20261019-1/usable-profile-1/MATCHED-IMAGE-MODULE-AND-APP-MANIFEST.json) and [current-module native review](/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-independent-review-20261019-1/ACTUAL-205-TWO-CPU-AND-RUST-PAIR-NATIVE-DIAGNOSTIC-REVIEW.json). The latter, rather than the SDK's earlier different-image ABI join alone, establishes tested205 compatibility. Current parent-pin SDK and SDK68 modules are not substitutes. Neither the current053d image nor corrected cbb04 candidate is this delivery; cbb04 has artifact/stage acceptance and pending native validation.

Profile: local x86_64 Linux control plane; QEMU 4vCPUs,8192MiB,two NUMA nodes; McKernel **two CPUs/128MiB**, assigned host CPUs1/2 and observed McKernel CPUs0/1. Network disabled. Heavy validation envelope: one build or guest at a time, four host CPUs/12GiB/no swap/512 tasks, existing aggregate-headroom and disk-floor checks. These are validation limits, not extra exercised McKernel capacity.

## Build recipe and provenance

No new build is required to use retained artifacts or repeat the already accepted M10 proof. [The exact tested205 M10 decision](/home/holden/mckernel/docs/verification/evidence/practical-recoverable-and-launch-record-literal-review-20261020-1/M10-EXIT-CONDITION.json) joins the clean FULL205 build (all16 commands exit0, one image MAKE, no adopted old compiled inputs) to the image and matching native replay. Rebuild instructions below describe the existing pinned recipe; any future build needs its own fresh admitted attempt and must retain its own outputs/failures.

Compute source is checkpoint `205410e43e19456ec98777dd6392940707061324` plus the exact materialization/request bindings in the identity manifest: materialization `a6c56023…`, derivative `46ef55bc…`, source manifest `d3495242…`, request `8b7b34ed…`; IHK `3114d9e7101ad52030eb3effa849a5c108972a1f`. Candidate `942c927b…` is explicitly **base_git_commit_only**, not the full built-source identity. Do not build today's dirty workspace and label it tested205.

Compute environment is the exact image `sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5`, pinned Rust1.95.0-nightly(c04308580), GCC14.3.1, clang/LLD21.1.8, binutils2.41, CMake3.31.8 and Make4.4.1. The toolchain manifest/lock hashes and source/driver request authority are recorded in [tested-artifact-identities.json](tested-artifact-identities.json). Linux `/out/build` and its matching headers/generated configuration are the unchanged pinned dependency. Reuse these dependencies where the accepted recipe permits; an arbitrary installed compiler/header tree is not equivalent.

Inside that admitted build environment, source is `/src`, generated output is `/work/output/build`, dependency is `/out/build`, Rust is `/nightly/bin/rustc`. The actual accepted configure and image commands were:

```sh
/usr/bin/cmake -S /src -B /work/output/build -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Debug -DBUILD_TARGET=smp-x86 -DKERNEL_DIR=/out/build -DENABLE_PERF=ON -DENABLE_RUSAGE=ON -DENABLE_LINUX_WORK_IRQ_FOR_IKC=ON -DRUSTC=/nightly/bin/rustc -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DENABLE_RUST_KERNEL=ON -DENABLE_RUST_IHK_MODULE_HELPERS=ON -DENABLE_RUST_USER_TOOLS=ON -DMCKERNEL_HOST_IRQ_ABI=linux-6.12 '-DKBUILD_MAKE_FLAGS=CC=/usr/bin/clang;LD=/usr/bin/ld.lld' -DCMAKE_MAKE_PROGRAM=/usr/bin/make -DCMAKE_LINKER=/usr/bin/ld -DCMAKE_AR=/usr/bin/ar -DCMAKE_RANLIB=/usr/bin/ranlib -DCMAKE_NM=/usr/bin/nm -DCMAKE_OBJCOPY=/usr/bin/objcopy -DCMAKE_READELF=/usr/bin/readelf -DGIT_EXECUTABLE=/usr/bin/git

/usr/bin/cmake --build /work/output/build --target mckernel.img -j4
```

Both commands use cwd `/src`; receipt environment hash is `32b2734ac7207c8317d8e807903d112334910a72acacd31d684b2d4cbcdb46e9`. These two commands summarize the recipe: **use the pinned image driver**, which also generates and checks the real-header CPU/process/syscall/native+legacy-crate/layout fixtures. [exact-command-reference.json](exact-command-reference.json) preserves **all16 original argv/cwd/phase/result rows**, source/request/driver pins and the original outer dispatch command. The historical output roots/releases are consumed and must not be rerun.

The matching three modules have their **separate accepted build**, using module candidate `257ba169b58eebd066281020999ec760bfc2f4e0`, 60-file closure `f7183ef9cd8aa032dede3822357219c811664ba2d365e0c0f9486b90a90c3970`, reviewed kmsg/mailbox deltas, and image `sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d`. Their exact make request, clean environment and command are also delivered in the command reference. At cwd `/out/build`, the actual pinned make argv is:

```sh
/usr/bin/env -i KBUILD_BUILD_HOST=rocky-10.2-x86_64 'KBUILD_BUILD_TIMESTAMP=Tue, 11 Aug 2026 07:40:34 +0000' KBUILD_BUILD_USER=mckernel KBUILD_BUILD_VERSION=1 SOURCE_DATE_EPOCH=1786434034 PATH=/usr/bin:/bin LANG=C LC_ALL=C TZ=UTC BASH_ENV= ENV= GNUMAKEFLAGS= MAKEFILES= MAKEFLAGS= MAKEOVERRIDES= MFLAGS= LD_LIBRARY_PATH= LD_PRELOAD= HOME=/candidate/home TMPDIR=/candidate/tmp /usr/bin/make -C /out/source/linux-6.12.0-211.44.1.el10_2 O=/out/build M=/candidate/modules ARCH=x86_64 LLVM=1 LOCALVERSION=-211.44.1.el10_2.mckernel1.x86_64 KBUILD_BUILD_HOST=rocky-10.2-x86_64 'KBUILD_BUILD_TIMESTAMP=Tue, 11 Aug 2026 07:40:34 +0000' KBUILD_BUILD_USER=mckernel KBUILD_BUILD_VERSION=1 SOURCE_DATE_EPOCH=1786434034 --jobserver-style=pipe -j2 modules
```

Use its pinned SDK driver/request, with `/out` and `/inputs` read-only and `/candidate` the reviewed writable build area. The `HOME=/candidate/home` and other environment entries above belong to the isolated historical build argv, not host-shell setup instructions. All three outputs and their Linux release/vermagic/ABI must match. [The accepted module build](/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-independent-review-20261019-1/CURRENT-HOST-PAIR-ACTUAL-THREE-MODULE-ARTIFACT-REVIEW.json) and [ABI record](/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-independent-review-20261019-1/CURRENT-HOST-PAIR-ACTUAL-THREE-MODULE-ABI-JOIN.json) retain the compiler/source proof; do not silently rebuild or replace this tuple while claiming its native results.

## Run the exact applications through the reviewed owner

Within the tested guest, the app commands are:

```sh
cd /case/two-app/work0
COKERNEL_PATH=/apps PAIR_CPU=0 PATH=/usr/bin:/bin /bin/mcexec -t 1 -c 0 0 /apps/app0

cd /case/two-app/work1
COKERNEL_PATH=/apps PAIR_CPU=1 PATH=/usr/bin:/bin /bin/mcexec -t 1 -c 1 0 /apps/app1
```

The existing pair collector launches these with overlap, exact argv/env/cwd/CPU assignments and unchanged manifest oracles; do not replace it with sequential manual invocations and claim the overlap result. Expected: app0 stdout387B, app1 stdout254B, both stderr empty/exit0, each within10000ms, complete streams with no discard/truncation, actual McKernel CPUs0/1, final procfs empty and positive process retirement. Original observed overlap1.620779456s and two actual launches are retained; this handoff performs zero new launches.

For a future host invocation:

1. Reuse the recipe's exact image, three modules, apps/oracles, base, native-boot, launcher and six pinned runtime source files. A changed source, tuple or configuration needs its corresponding compatibility/result joins. The original accepted owner argv and all seven actual command-data rows are preserved in [exact-command-reference.json](exact-command-reference.json) as **consumed historical reference only**.
2. Choose a **fresh admitted empty parent and fresh nonce**. Bind these into the existing accepted owner API. The argv shape below is instructional; angle-bracket slots must be real fresh admitted values, not literal shell input:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B
/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/native_diagnostic_container_owner.py
--attempt-parent <FRESH_ADMITTED_EMPTY_PARENT>
--nonce <FRESH_ADMITTED_NONCE_HEX32>
--owner-sha256 5ab04f3bb41b21d52f3f567169c519a0837419fa12f9ec2897f1b1b116f8860a
--manifest /home/holden/mckernel-work/scratch/cp205m-261019-1/manifest.json
--manifest-sha256 4aa72c2a5a759bda71c4a0e8e33499068261346113ec2c9fd19d4669b3f8e41d
```

3. Complete actual owner/runner/full-parent/expanded AF_UNIX metadata preflight, static caller/capture closure and the independent fresh execution release/admission. Bind the actual latest positive physical predecessor separately from component SDK/ABI identities; a historical physical result is not live clearance. Take the genuine **≤60-second** snapshot only after static closure. Preserve current service/usage/ownership/resource gates, same10000-credit ledger, Scratch21, permanent27:4 and the unanswered reserve576 proposal.
4. Use the existing **seven-step direct-owner capture route**: LAST-snapshot → machine assembly → final guard → native owner → readback1 → readback2 → readback3. Exact per-step argv/caller templates, historical command data, profiles and success conditions are delivered in the command reference. Freshly bind release/snapshot/capture hashes and paths; never replay old machine-release, nonce, attempt/capture names or output slots. `guard.allowed_argv` must equal owner argv exactly, without an added outer kill/CPU/address-space cap. Do not directly execute an inner guest command to bypass this route.
5. Only after positive owner retirement, perform the three bounded readbacks; exclude qmp.sock from the attempt tar. Retain raw stdout/stderr/exit/wait, timeouts/errors, PID/start identities, serial/debugcon, app results and owner/all-client/QEMU/container/lease receipts. Obtain independent application-semantic and physical disposition before reuse. On failure preserve the first evidence and stop the affected batch; guest disposal alone supplies no native resource-restoration proof.

Current runtime is not newly admitted by this handoff. Fresh admission naturally expires; this does not erase the retained recipe/results or require a duplicate run to deliver instructions.

## Scope and known limitations

The published [P-M13-02 capability statement](/home/holden/mckernel/docs/verification/evidence/p-m13-02-capability-statement-20261022-1/CAPABILITY-STATEMENT.md) supplies supported/unsupported behavior and exact separate historical/current/candidate buckets. Keep its limits: live compute C in `cpu.c`, `process.c` and remaining process/scheduling paths is active, and whole Rust conversion remains unfinished. Source inventory is not a conversion score. Existing accepted Rust/compiler/native proofs remain preserved; SDK68 changes have no current-module/native acceptance from source/unit tests alone. This tested205 handoff does not require adopting those untested modules.

Baseline **25/35 literal practical checks** is preserved; whole M13, P-M13-03 final correctness/ownership review and whole practical-OS completion remain open. Current cbb04 M07 native proof, M05 complete restoration/cycle obligations, M06 process behavior, changed ABI/ownership boundaries and matched M12 budgets remain separate. Original failures and unsupported results remain unchanged. Only focused independent review and dispatcher publication/adoption can close P-M13-01; no counter changes are made here.
