# McKernel native OS lifecycle handoff

Paused at the user's request on 2026-09-07 to continue on a machine with more resources. No further implementation or verification is running locally. GitHub Actions continue independently.

The implementation is published in phoenix-hacking/mckernel, branch `codex/rocky-rust-validation`, commit `24a151fef5b9fcf303fdbb8cf9762340cd4100fd`, tree `578d9ea8a484694d5c0c73f03afec38527faad41`. PR #1 is draft, open and unmerged. The implementation worktree was clean at handoff.

```sh
git clone --branch codex/rocky-rust-validation https://github.com/phoenix-hacking/mckernel.git
cd mckernel
git submodule update --init --recursive
git rev-parse HEAD
```

The current increment implements native unbooted OS creation, two status aliases, shared-open leases, busy destruction, module pinning, device removal and minor reuse. Each instance owns its Linux device and contiguous zeroed 4 MiB kmsg allocation. The first exact build at c7e7c413 failed because empty lockdep bindings crossed FFI declarations and private-module items used public visibility. Commit 24a151fe fixes those errors without suppressing compiler lints.

Verified: all 196 focused checks passed without skips; the full local suite passed 2,288 tests with 186 explicit skips; the hosted suite passed 2,288 tests with 168 skips. The 41-case adapter fixture and all four hosted syscall-probe simulation methods passed. Both configuration-review jobs and both snapshot test jobs passed within their bounded scopes. The compatibility build passed; its actual guest run is in progress.

The next action is to inspect these existing runs before changing source or launching duplicate builds:

- Native build and guest: https://github.com/phoenix-hacking/mckernel/actions/runs/34072696813
- Independent PR native build: https://github.com/phoenix-hacking/mckernel/actions/runs/34072696599
- Independent push native build: https://github.com/phoenix-hacking/mckernel/actions/runs/34072694105
- Compatibility build and guest: https://github.com/phoenix-hacking/mckernel/actions/runs/34072696554

If native compilation fails, record its first diagnostic in kernel.log before unrelated changes. If it passes, retrieve the original build/runtime artifacts, verify their GitHub digest and size, and run the unchanged native_rust_runtime_evidence.py public verifier against a clean checkout of this exact commit. Review the original initramfs and all four x86_64/i386 OS lifecycle receipts: three creates and destroys per probe, two load cycles, twelve creates and twelve destroys per trace. The retained review runner documents the exact arguments and checks. Do not execute the freestanding ioctl or poweroff helpers on the host; they are for disposable guests or the syscall simulator.

The custom native target is the locked Rocky Linux 10.2-derived 6.12.0-211.44.1.el10_2 source and exact Red Hat Rust 1.92.0 toolchain. The working compatibility oracle remains Rocky 8.10. Linux stays the host control plane. Only ihk.ko, ihk-smp-x86_64.ko and mcctrl.ko are conversion targets; preserve the current McKernel image, tools and C oracle.

Frozen source/platform metadata jobs failed on already known repository hash changes; do not relax the locks. License capture lists 115,269 unresolved items. Native CPU/NUMA resource assignment/restoration, image loading/boot/shutdown, IKC, mcctrl services and release qualification remain. The native initramfs does not boot a McKernel image. The tracker is unchanged at 350/10,000 (3.50%), 6 PASS, 1 IN_PROGRESS and 123 TODO. No native guest success or release readiness is claimed at this handoff.

See native-os-24a151fe.json for exact validation counts, input identities, run states and evidence archive identity. The evidence archive retains the first failed compiler artifact, prior-candidate compatibility artifacts and reviews, current hosted diagnostics and local regression results. It contains no completed current-head native build/runtime artifact because those runs were still in progress when work was paused.
