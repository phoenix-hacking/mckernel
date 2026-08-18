# Rust x86_64 Validation Progress

**Current completion: 100%**

This percentage is evidence-gated. It reaches 100% only after the current PR
head builds on Rocky/RHEL-family x86_64, boots McKernel, runs real programs
through `mcexec`, and shuts down cleanly.

Here, 100% means every gate in this Rocky 8.10 x86_64 smoke plan has passed.
It does not mean line/branch coverage, an all-Rust IHK stack, exhaustive kernel
correctness, Arm64 coverage, LA57/five-level paging coverage, or long-duration
stress coverage.

## Completion gates

| Gate | Weight | Status | Current evidence |
| --- | ---: | --- | --- |
| PR and scope audit | 5% | PASS | Draft PR #1 inspected; the recorded tree is pinned C IHK plus Rust McKernel, Rust-linked `mcctrl`, and Rust-linked `mcexec`. |
| Runner checks | 5% | PASS | Shell syntax, help, invalid-option, numeric-option, and cleanup-regression checks pass. |
| IHK compatibility | 5% | PASS | Forward check/apply, reverse check/apply, `git diff --check`, and clean pinned-IHK status pass at `3114d9e7101ad52030eb3effa849a5c108972a1f`. |
| `development` compatibility | 10% | PASS | Current `development` commit `7a779815cba07bacfeed5788acca31629e50a39a` is merged; GitHub reports the draft PR mergeable. |
| Rust source/toolchain | 10% | PASS | Exact pinned nightly compiles the three selected Rust objects; required symbols, no-SIMD scan, formatting, and variadic behavior checks pass. |
| Rocky complete build | 20% | PASS | Run `31358174445` (job `93361671964`) built every requested artifact on Rocky 8.10 at `1e7744e551c5af4894b87f84bb4269a4f5f0ae84`; the pinned compiler, no-SIMD, Rust linkage, and exact pinned-IHK source-profile audits all passed. |
| Host modules | 10% | PASS | Run `31358174445` loaded and used `ihk`, `ihk_smp_x86_64`, and `mcctrl` while McKernel was RUNNING, then proved the modules and McKernel device nodes were absent after shutdown. |
| McKernel boot | 15% | PASS | Hosted job `93362016101` reached `RUNNING`, emitted `IHK/McKernel started.` and `IHK/McKernel booted.`, consumed the master-channel ACK, and completed both host IKC connections. |
| Real `mcexec` programs | 10% | PASS | The hosted guest passed `/bin/true`, relative and absolute hostname, the deterministic 1 MiB workload, and `mcstat`; kmsg contains `prepared`, `schedule_process queued`, `enter_user`, `send_syscall`, and `offload_return`. |
| CI evidence and PR report | 10% | PASS | Run `31358174445` is fully green with build artifact `9051403164` and hosted artifact `9051531436`; this tracker records the runtime checkpoint, and PR #1 is the non-repository surface for the documentation-head replay metadata. |

The first hosted attempt earned no completion credit. Workflow run
`31288159829` (job `93180630285`) failed during container initialization after
three pull attempts with:

```text
manifest for rockylinux:8.10 not found: manifest unknown
```

No checkout or build command ran. The workflow now uses Rocky's own
`rockylinux/rockylinux:8.10` image pinned to multi-architecture digest
`sha256:e8a49c5403b687db05d4d67333fa45808fbe74f36e683cec7abb1f7d0f2338c6`
and asserts `ID=rocky` plus `VERSION_ID=8.10` before installing packages.

The second hosted attempt, run `31288499526` at
`df508bcbaf5867d50514dc7b156f918217439a03`, passed container initialization,
dependency installation, recursive checkout, the exact nightly check, and
development ancestry. It compiled all requested targets, including
`mckernel.img`, the three host modules, `mcexec`, and the deterministic
workload. The linkage gate then reported:

```text
error: .../mcexec.c.o does not import required Rust-path symbol:
mcexec_finish_main_image_body
```

That expectation was wrong: the compiled C `main` shim imports only
`mcexec_main_body`; Rust `mcexec_main_body` directly calls Rust
`mcexec_finish_main_image_body`. Both Rust definitions remain mandatory in the
Rust object and final binary. The run uploaded artifact `9030640799` with
digest `sha256:bc9b0b3acbbde635b4160c928972e40b0c4114a7e7d543d116813e5019cc121d`.
No build completion credit is awarded until the corrected linkage gate and
source audit pass together. Installation and runtime use are proved separately
inside the disposable guest.

The third hosted attempt, run `31290334197` at
`c032b38c8df5691a206f60059843100bd26a9689`, passed Rocky initialization,
dependency installation, recursive checkout, the pinned nightly check,
development ancestry, all production builds, the kernel/module no-SIMD scan,
and Rust linkage across McKernel, `mcctrl`, and `mcexec`. The source-retirement
audit then found that the recorded, intentionally C IHK submodule built these
three host utilities, each discovered through both `compile_commands.json` and
CMake `build.make` metadata:

```text
ihk/linux/user/ihkconfig.c
ihk/linux/user/ihkosctl.c
ihk/linux/user/ihkmond.c
```

The parent tracker records later Rust full-body retirement work that is absent
from pinned IHK commit `3114d9e7101ad52030eb3effa849a5c108972a1f`. The Rocky
profile now names only those three additional C boundary paths, alongside its
existing exact IHK core/IKC exemptions. The audit still rejects an invalid,
unused, or otherwise unlisted compiled source. Run `31290334197` uploaded
artifact `9031218315` with digest
`sha256:a4804e2aa270da0b4b15a65edf0d82bbc6c5bb044cd7b222e278ae7e29de50a7`.
No completion credit was awarded at that point; the fresh passing run is
recorded below.

The fourth hosted attempt, run `31290918282` at
`dc14f5b161da0d21bfc1d92e3920d6199dcf2817`, passed the complete Rocky 8.10
build lane. It built `mckernel.img`, `ihk.ko`, `ihk-smp-x86_64.ko`,
Rust-linked `mcctrl.ko`, Rust-linked `mcexec`, and the deterministic workload;
the recorded Rust objects passed no-SIMD checks, the final artifacts passed
the Rust entry/handoff linkage checks, and the source-retirement audit accepted
exactly the nine pinned-IHK profile exemptions with no residual compiled
retired C. Artifact `9031569420` has digest
`sha256:4cc10d0777bd1063f79c18269c1dd47285c88e12fa0b35b032d2ca107b080888`.
This earns the 20% Rocky-build gate and moves current completion to 55%. The
dependent hosted QEMU job `93189707196` completed with failure before any
guest command ran: SSH did not become ready within 900 seconds and the serial
log remained empty. The backing image still matched its pinned checksum and
the evidence artifact was uploaded as `9031891754`, digest
`sha256:77f1c829d349c8ec5bc9b7986063ed3964988b4d9838046dd9b9fe28fddf422a`.
No host-module, McKernel-boot, or userspace credit is awarded, so completion
remains 55%.

The failed QEMU command exposed the NoCloud seed with
`if=virtio,media=cdrom`. QEMU's virtio-blk device is disk-only and does not
support CD-ROM devices. The next candidate exposes the CIDATA-labelled seed
as a read-only virtio disk and explicitly boots the first hard disk. A bounded
local TCG reproduction then proved that the exact checksum-pinned Rocky image,
q35 machine, SeaBIOS, virtio system disk, and even the old seed syntax reach
the Rocky 4.18.0-553 kernel and ttyS0. Therefore the unsupported seed media
type is corrected but is not claimed as the cause of the hosted zero-byte
serial log. The remaining differentiator is the hosted KVM/host-CPU path.

The next candidate runs q35 with `graphics=off`, which redirects SeaBIOS and
GRUB to the captured serial port. A 60-second preflight records verified QEMU
PID state, CPU ticks, serial-byte growth, and QMP `query-status` plus
`query-cpus-fast`. This will distinguish a KVM/vCPU stall from a later Rocky
boot or networking failure without another 900-second blind wait. It earns no
credit until the hosted guest reaches SSH and the full runtime chain passes on
the published head.

The fifth workflow run, `31296009940` at
`5cdb2040ccadd4745ba8b8fbf0cb119d88b952cd`, passed the Rocky build again.
Its first hosted attempt failed in ephemeral KVM preparation before image
download; rerunning the failed job reached QEMU. Attempt 2 job `93201600353`
verified the dated Rocky image, started four KVM vCPUs, completed QMP
`query-status`/`query-cpus-fast`, and captured 1,512 serial bytes. SeaBIOS then
reported:

```text
Booting from Hard Disk...
Boot failed: not a bootable disk
...
No bootable device.
```

SSH expired after 900 seconds and no guest command ran. Evidence artifact
`9033351686` has digest
`sha256:7a67687d8c63f2cc06c6e23edf5d93903fbeba2c3763a0580f2c18b02dfd7c20`.
The backing image still matched SHA-256
`e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14`,
the overlay was removed, and the verified QEMU process exited. No module,
boot, userspace, or cleanup-restoration credit is awarded.

The failure was an overlay-construction bug, not a Rocky image defect. QEMU
8.2.2's JSON `qemu-img info` output lists a nested child with
`"format": "file"` before the top-level `"format": "qcow2"`. The wrapper's
first-match `sed` therefore passed `-F file` when creating the overlay, making
QEMU expose the qcow2 container bytes as raw guest sectors. The corrected
parser reads the anchored top-level human `file format:` field and fails closed
if it is absent. Against the exact pinned image, the resulting overlay reports
`backing-filename-format: qcow2`, its first 4 MiB of virtual disk content
byte-match the backing image, and a bounded QEMU 8.2.2 TCG probe reaches GRUB
and the Rocky 4.18.0-553 kernel. This is focused harness evidence only; the
published hosted retry remains authoritative and completion remains 55%.

Before that retry, the candidate was hardened against false-positive runtime
results. It now proves the assigned CPU and memory exactly match the request
and that no IHK reserve remains, rechecks `RUNNING` after all workloads, scans
the final McKernel kmsg for fatal signatures, and verifies IRQ affinities,
temporary irqbalance state, and validation processes after shutdown. Raw
McKernel kmsg, Linux dmesg, resource, package/repository, toolchain, and runtime
artifact-hash evidence is copied out of the guest and independently verified
by SHA-256 on the hosted runner. These checks earn no percentage until the
complete published-head workflow passes.

## Fresh commands and results

```text
GitHub Actions run 31358174445 at
  1e7744e551c5af4894b87f84bb4269a4f5f0ae84
result: PASS (workflow conclusion success)
Rocky build job: 93361671964 PASS
hosted Rocky QEMU/mcexec job: 93362016101 PASS
protected job: 93362016742 SKIPPED by design; the hosted lane is the required gate
Rocky image: 2,065,760,256 bytes; sha256:e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14
QEMU acceleration: KVM
build artifact: 9051403164 (5,171,495 bytes)
build artifact digest: sha256:1e720d7d8ead54050bf8f5791d0ee22cba3d17f6ddfc0c932d807da948e61bf9
hosted artifact: 9051531436 (206,359 bytes)
hosted artifact digest: sha256:36d368427c9ba8eb58195195009d31d479439896a8c89efbf20318672f4c684e

runtime: McKernel RUNNING; IHK/McKernel started.; IHK/McKernel booted.
live modules: ihk, ihk_smp_x86_64, mcctrl
assignment: CPU 1; memory 536870912@0; residual CPU/memory reserves none
mcexec: /bin/true PASS; hostname PASS; absolute hostname PASS
deterministic workload: mckernel-rust-smoke: OK bytes=1048576 sum=133693440
handoff markers: prepared; schedule_process queued; enter_user; send_syscall; offload_return
workload kmsg delta: lines=1031 sha256=baf0a12f3fb6be403d12cbfa7c8d972109d289c9f3e3f6dfc794f6bb3c24a22d
mcstat: PASS
post-workload status: RUNNING
McKernel fatal scan: clean lines=1054
McKernel fatal-scan digest: sha256:77bd108fb524e0e144835b367b64e671becc821ae31fbabd1f55929a4ff3d6f5
Linux dmesg delta fatal scan: clean lines=54
Linux dmesg-delta digest: sha256:a7a525f93f013b414735be9ad399b77ef5b5436bc75d18d4a3388dd0a87b84b9
runtime provenance: files=4 sha256=258c49e683f8478ee37a8c3efb9e36ebffc02f8179d9e7b3188f63a6bea76195
raw evidence: files=13 manifest_sha256=d959913f61026704f94355dec278dccc758225ed12fb135b41291c6f8e6a2c90
serial evidence: 64,118 bytes; guest evidence: 289,161 bytes
shutdown: mcstop+release PASS
restoration: SELinux enforcing; CPUs 0-3; vm.swappiness 30; irqbalance active;
             29 IRQ-affinity entries restored
cleanup: modules none; device nodes none; validation processes none;
         temporary irqbalance state none; guest overlay removed; QEMU exited
backing image: unchanged
completion: 100%
```

```text
bash -n scripts/rocky-rust-validation.sh \
  scripts/qemu-rocky-rust-validation.sh \
  scripts/qemu-mckernel-guest.sh \
  scripts/ihk-module-load-smoke.sh
result: PASS

rustfmt +nightly-2026-02-19 --edition 2021 --check kernel/rust/numparse.rs
result: PASS

actionlint -config-file .github/actionlint.yaml \
  .github/workflows/rust-x86_64-validation.yml
result: PASS (actionlint 1.7.12; all 14 embedded Bash blocks also pass `bash -n`)

scripts/qemu-rocky-rust-validation.sh \
  --image unused --disk-size invalid
result: expected exit 2; invalid disposable-disk size rejected before QEMU

scripts/qemu-mckernel-guest.sh \
  --image unused --disk-size invalid
result: expected exit 2; invalid disposable-disk size rejected before image or QEMU probing

scripts/qemu-mckernel-guest.sh \
  --image unused --guest-evidence-dir relative
result: expected exit 2; non-absolute guest evidence path rejected before QEMU

GitHub Actions run 31288159829 at
  b54e69c6bc3309e8a719b645832c8c37cdc853e1
result: FAILURE during `Initialize containers`
command: docker pull rockylinux:8.10 (three attempts)
error: manifest for rockylinux:8.10 not found: manifest unknown
checkout/build/boot: SKIPPED
artifacts: none
completion: unchanged at 35%

GitHub Actions run 31290334197 at
  c032b38c8df5691a206f60059843100bd26a9689
result: FAILURE during the source-retirement audit after all builds and Rust linkage passed
error: strict Rust build compiles retired source-retirement rows: 6
unique paths: ihkconfig.c, ihkosctl.c, ihkmond.c from the pinned C IHK boundary
artifact: 9031218315
artifact digest: sha256:a4804e2aa270da0b4b15a65edf0d82bbc6c5bb044cd7b222e278ae7e29de50a7
boot: SKIPPED because hosted-boot-smoke needs a successful rocky-build
completion: unchanged at 35%

GitHub Actions run 31290918282, Rocky build job 93187780126, at
  dc14f5b161da0d21bfc1d92e3920d6199dcf2817
result: PASS
artifacts: mckernel.img, ihk.ko, ihk-smp-x86_64.ko, mcctrl.ko, mcexec,
           deterministic workload, plus recorded build evidence
gates: pinned Rocky/compiler PASS; development ancestry PASS; no-SIMD PASS;
       Rust linkage PASS; exact pinned-IHK source profile PASS
artifact: 9031569420
artifact digest: sha256:4cc10d0777bd1063f79c18269c1dd47285c88e12fa0b35b032d2ca107b080888
completion: 55%

GitHub Actions run 31290918282, hosted QEMU job 93189707196, at
  dc14f5b161da0d21bfc1d92e3920d6199dcf2817
result: FAILURE before guest SSH or any guest command
qemu: KVM/q35/host CPU, 4 vCPUs, 6144M, 24G disposable overlay
error: guest SSH did not become ready within 900s
serial.log: 0 bytes
guest-command.log: not created
backing image checksum: PASS
artifact: 9031891754
artifact digest: sha256:77f1c829d349c8ec5bc9b7986063ed3964988b4d9838046dd9b9fe28fddf422a
module load / McKernel boot / mcexec: NOT RUN
completion: unchanged at 55%

GitHub Actions run 31296009940, hosted attempt 1 job 93201346414, at
  5cdb2040ccadd4745ba8b8fbf0cb119d88b952cd
result: FAILURE in ephemeral KVM preparation before image download
artifact: 9032991394
artifact digest: sha256:bd4dde345fa1cc12b31366c2f26870a8bb58ad88537322488e1223f0faf1013a
module load / McKernel boot / mcexec: NOT RUN
completion: unchanged at 55%

GitHub Actions run 31296009940, hosted attempt 2 job 93201600353, at
  5cdb2040ccadd4745ba8b8fbf0cb119d88b952cd
Rocky build: PASS
QEMU/QMP: PASS through verified KVM process, four live vCPUs, and firmware serial
result: FAILURE before SSH; SeaBIOS reported `No bootable device.`
serial.log: 1512 bytes
guest-command.log: not created
backing image checksum: PASS; disposable overlay removed; QEMU exited
artifact: 9033351686
artifact digest: sha256:7a67687d8c63f2cc06c6e23edf5d93903fbeba2c3763a0580f2c18b02dfd7c20
root cause: qemu-img JSON parser selected nested child format `file` instead
            of top-level image format `qcow2`, producing an invalid overlay chain
module load / McKernel boot / mcexec: NOT RUN
completion: unchanged at 55%

corrected overlay construction against the exact checksum-pinned Rocky image
result: PASS; qemu-img reports `backing-filename-format: qcow2`; the first
        4 MiB of overlay virtual content byte-match the base image; bounded
        QEMU 8.2.2 TCG reaches GRUB and Rocky kernel 4.18.0-553
completion: unchanged at 55% (local guest-boundary diagnosis only)

checksum-pinned Rocky image under QEMU 8.2.2 TCG/q35/SeaBIOS with the original
  virtio seed command, bounded to 180s
result: PASS through firmware, GRUB, Rocky kernel, ttyS0 enablement, virtio
        vda/vdb discovery, root UUID discovery, and root mount
serial.log: 32544 bytes
kernel: 4.18.0-553.el8_10.x86_64
completion: unchanged at 55% (local guest-boundary diagnosis only)

the same image with q35,graphics=off, bounded to 30s
result: PASS; SeaBIOS, `Booting from Hard Disk`, GRUB, the Rocky kernel menu,
        and its one-second countdown were captured on ttyS0
serial.log: 2389 bytes
completion: unchanged at 55% (diagnostic-harness proof only)

scripts/qemu-mckernel-guest.sh --image <pinned-rocky-image> --accel tcg \
  --memory 2048M --cpus 2 --disk-size 24G --timeout 300 \
  --log-dir <fresh-temp-dir> --dry-run
result: PASS; command contains q35,graphics=off, QMP, explicit bootindex=1 for
        the Rocky OS disk, bootindex=2 for the read-only virtio seed disk, and
        no conflicting global boot order or media=cdrom; disposable overlay
        removed by the verified cleanup path

the same updated wrapper without --dry-run in the Codex execution sandbox
result: BLOCKED before firmware; this sandbox denies AF_UNIX socket creation,
        so QEMU could not create the requested QMP socket (`EPERM`). A bounded
        direct QEMU 8.2.2 parse/start check without QMP remained alive until its
        three-second timeout with both explicit virtio-blk boot indexes. This
        environment restriction earns no credit; the hosted Ubuntu runner is
        the authoritative QMP/KVM/runtime gate.

synthetic source-retirement build metadata containing the six existing
pinned-IHK core/IKC C paths plus ihkconfig.c, ihkmond.c, and ihkosctl.c
result: PASS; compiled_non_allowlisted_c=0, compiled_retired_c=0,
        compiled_source_profile_exemptions=9

the same synthetic metadata plus unlisted retired kernel/init.c
result: expected exit 1
error: strict Rust build compiles retired source-retirement rows: 1

curl -fsSL \
  https://hub.docker.com/v2/repositories/rockylinux/rockylinux/tags/8.10
result: tag=8.10
        digest=sha256:e8a49c5403b687db05d4d67333fa45808fbe74f36e683cec7abb1f7d0f2338c6
        amd64=sha256:f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e

cc -O2 -std=c11 -Wall -Wextra -Werror \
  scripts/smoke/mcexec-rust-smoke.c -o mcexec-rust-smoke
./mcexec-rust-smoke
result: mckernel-rust-smoke: OK bytes=1048576 sum=133693440

git diff --check
result: PASS
```

Pinned compiler: `rustc 1.95.0-nightly (c04308580 2026-02-18)` from
`nightly-2026-02-19`. Production-flag object results:

| Object | SHA-256 | Result |
| --- | --- | --- |
| `mckernel_rust.o` | `408fc2ef755ca0ad188e17d65497c3c24239ce0ce59b24a880833461353bf030` | Required entry/host symbols and no-SIMD gate pass. |
| `mcctrl_helpers.o` | `91a4b57d63b4ed44c3ba0c2d1959accb86a9152646f454b0f15a788856ad54e4` | Required module/control symbols and no-SIMD gate pass. |
| `mcexec_helpers.o` | `1bd472ba5fcacde678ffcb3983004d4e51faea7c6d0fcf0d51a8347fb59526ef` | Required main/image/syscall-loop symbols pass. |

A focused native variadic harness resolved `snprintf` and `sscanf` to the Rust
object and passed dynamic width/precision, promoted integer classes, pointer,
`%n`, and scan-back cases with `numparse-va-smoke: OK`.

## Completion and final checkpoint

Run `31358174445` is the fully green runtime code checkpoint. It satisfies every
weighted gate above and establishes 100% completion for this defined Rocky
8.10 x86_64 smoke plan.

The commit containing this paragraph is intentionally documentation-only
relative to runtime head
`1e7744e551c5af4894b87f84bb4269a4f5f0ae84`. No workflow, script, Rust,
C, assembly, linker, patch, submodule, or build-input file changes in that
closeout commit. The complete workflow must pass again on that exact
documentation head; PR #1 records the replay run, job, artifact, and digest
identifiers without creating a self-referential third repository checkpoint.

The result validates the exercised Rocky 8.10 x86_64 QEMU/KVM acceptance path:
one reserved McKernel CPU, boot and IKC handshake, basic `mcexec` syscall
offload, the deterministic Rust workload, and status, cleanup, and integrity
checks. The 100% label retains the scope stated at the top of this file; it is
not a claim of semantic equivalence for unexercised architectures, CPU counts,
devices, syscalls, or workloads, nor of exhaustive correctness, all-Rust IHK,
Arm64 coverage, LA57/five-level paging coverage, or long-duration stress
coverage.
