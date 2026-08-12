# Native Rust host-module staging

This directory is the production Rust-for-Linux staging area for the three project-owned host modules: `ihk.ko`, `ihk-smp-x86_64.ko`, and `mcctrl.ko`.

Linux remains the Rocky-derived control-plane kernel; only these project-owned host modules are conversion targets. Production link lists may contain Rust module objects, generated kernel metadata, kernel-provided objects, and separately reviewed architecture assembly where required. They may not contain project-authored C implementation bodies, compatibility shims, fallback archives, prebuilt C objects, or dispatch tables that execute the legacy C implementation.

Behavioral implementation is evidence-gated against `host-kernel/contracts/legacy-behavior-contract-f2eb7352.json`. Before any implementation gate is credited, the exact Rocky-derived `CONFIG_RUST` kernel must compile the module and the relevant acceptance tests must pass on immutable CI evidence.
