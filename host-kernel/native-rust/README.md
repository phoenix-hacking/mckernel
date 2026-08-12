# Native Rust host-module staging

This directory is the production Rust-for-Linux staging area for the three project-owned host modules: `ihk.ko`, `ihk-smp-x86_64.ko`, and `mcctrl.ko`.

Linux remains the Rocky-derived control-plane kernel; only these project-owned host modules are conversion targets. Production link lists may contain Rust module objects, generated kernel metadata, kernel-provided objects, and separately reviewed architecture assembly where required. They may not contain project-authored C implementation bodies, compatibility shims, fallback archives, prebuilt C objects, or dispatch tables that execute the legacy C implementation.

Behavioral implementation is evidence-gated against `host-kernel/contracts/legacy-behavior-contract-f2eb7352.json`. Before any implementation gate is credited, the exact Rocky-derived `CONFIG_RUST` kernel must compile the module and the relevant acceptance tests must pass on immutable CI evidence.

## Single build-control authority

This directory contains Rust crate roots and their reviewed contracts only. It
must not contain a `Kconfig`, `Kbuild`, or `Makefile`; duplicate build-control
files previously used a different symbol family and could silently select a
different module graph.

The sole production definitions are `host-kernel/kbuild/Kconfig` and
`host-kernel/kbuild/Kbuild.in`, bound by
`host-kernel/kbuild/stage-manifest.json`. Check this invariant with:

```sh
python3 scripts/native_rust_build_surface_audit.py
```

## mcctrl lifecycle foundation

The lifecycle contract preserves the frozen zero-parameter surface and exact
semantic module metadata: `name=mcctrl`, `license=GPL v2`, `depends=ihk`, with
no author, description, or version field. The dependency is not forged in
source. Kconfig requires the native IHK provider and the crate emits the
reviewed `MCKERNEL_IHK_V1` import-namespace declaration, while a real symbol
import remains blocked until the native provider has a supported exported ABI
anchor.
Only modpost may derive `depends=ihk` from that future real import.

The frozen module owns mcexec binfmt registration, but the selected Linux 6.12
Rust kernel crate has no safe `linux_binfmt` registration API. That ownership
therefore remains blocked under `MCC-013`; this lifecycle foundation neither
registers binfmt nor emits the legacy success messages that would imply it did.

Validate these fail-closed constraints with:

```sh
python3 scripts/mcctrl_native_lifecycle_check.py
```

The source-only result is never MCC-001 gate credit. Supplying `--module`
additionally requires exact built metadata and deterministic diagnostics, but
Rocky 10.2 build, load, and unload evidence is still required separately.
