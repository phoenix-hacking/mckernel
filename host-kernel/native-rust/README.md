# Native Rust host-module staging

This directory is the production Rust-for-Linux staging area for the three project-owned host modules: `ihk.ko`, `ihk-smp-x86_64.ko`, and `mcctrl.ko`.

Linux remains the Rocky-derived control-plane kernel; only these project-owned host modules are conversion targets. Production link lists may contain Rust module objects, generated kernel metadata, kernel-provided objects, and separately reviewed architecture assembly where required. They may not contain project-authored C implementation bodies, compatibility shims, fallback archives, prebuilt C objects, or dispatch tables that execute the legacy C implementation.

Behavioral implementation is evidence-gated against `host-kernel/contracts/legacy-behavior-contract-f2eb7352.json`. Before any implementation gate is credited, the exact Rocky-derived `CONFIG_RUST` kernel must compile the module and the relevant acceptance tests must pass on immutable CI evidence.

## Unsafe and FFI ledger

Every reachable project Rust input and every explicit unsafe/FFI source site is
bound by `host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json`. The
ledger keeps a durable site ID separate from exact source and normalized
expression digests, and records the source `SAFETY:` comment, caller
obligations, context constraints, component owner, compiler-capture state, and
independent-review state. Validate the source-bound inventory with:

```sh
python3 scripts/native_rust_unsafe_ffi_ledger.py check
```

The check is deliberately not RS-011 credit. The checker's
`capture-compiler` mode is a later evidence hook for exact Kbuild `.cmd`, rustc
dep-info, object, compiler, and RS-001 platform-evidence digests. Until that
capture also includes compiler-expanded unsafe-operation spans and receives an
independent owner/security review, both the committed ledger and any compiler
closure capture remain `NOT_READY`.

## IHK OS registry foundation

The IHK provider now privately compiles `abi/x86_64.rs`, `ikc_queue.rs`,
`os_registry.rs`, `ikc_master.rs`, and `ihk_ioctl.rs`. The registry is an
allocation-free 64-slot state machine
with generation-tagged handles, rollback guards, reference leases, deterministic
errno mapping, and a fail-closed transition graph. The authoritative staging
manifest copies all five transitive sources to the paths named by the crate
root, so Rust dep-info must include them in the exact compiler closure.

The foundation does not expose create/destroy entry points, register character
devices, allocate kmsg storage, or call a legacy C implementation. Validate its
frozen-source contract and exact standalone Rust 1.92 fixture with:

```sh
python3 scripts/ihk_os_registry_check.py
python3 -m unittest -v scripts.tests.test_ihk_os_registry_check
```

This source validation remains `TODO` and credit-ineligible until the provider
callbacks, device publication/teardown, exact Kbuild, module load, runtime
behavior, and independent transition/errno review are complete.

## IHK scalar ioctl dispatcher foundation

The private `ihk_ioctl.rs` module decodes the exact legacy raw command numbers
for device create/destroy and the two OS-status aliases. It retains the x86_64
scalar provider argument, rejects destroy minors outside 0 through 63, prepares
rollback-safe registry transactions, preserves the legacy subset's errno and
direct-return semantics, and uses generation-tagged OS identities for status.
It performs no allocation, FFI, C dispatch, registration, or userspace copy.

An audit of the byte-exact Rocky Linux 6.12 Rust sources found ioctl-number
helpers and safe `UserSlice` copy wrappers, but no Rust `miscdevice`, `cdev`,
`file_operations`, or ioctl-callback registration layer. The dispatcher is
therefore not userspace reachable. It must not be wired through raw bindings or
hand-written unstable FFI; a supported kernel registration adapter is an
explicit blocker. Validate the frozen IHK behavior, exact Rocky API capture,
mutation defenses, and standalone Rust 1.92 fixture with:

```sh
python3 scripts/ihk_ioctl_dispatch_check.py
python3 -m unittest -v scripts.tests.test_ihk_ioctl_dispatch_check
```

Passing an unmodified exact Rocky source root through `--kernel-source` also
replays the full Rust-tree absence audit. This remains an IHK-005 `TODO`
checkpoint with no gate credit and no runtime create/destroy/status claim.

## IHK page-allocation attachment

The IHK provider now privately compiles `page_allocator.rs` followed by
`page_owner_registry.rs` through literal module edges in `ihk.rs`. The
authoritative staging manifest copies both files beside the crate root, and the
lifecycle, build-surface, host-input, and RS-011 audits bind the same exact
source closure. This attachment makes the safe, allocation-free foundations
visible to exact Kbuild compilation; it does not publish legacy allocation or
free exports and does not make either foundation runtime reachable.

Validate the frozen contracts and their exact Rocky Rust 1.92 fixtures with:

```sh
IHK_PAGE_ALLOCATOR_RUSTC=/path/to/rocky/rustc \
  python3 scripts/ihk_page_allocator_check.py --require-rustc
IHK_PAGE_OWNER_REGISTRY_RUSTC=/path/to/rocky/rustc \
  python3 scripts/ihk_page_owner_registry_check.py --require-rustc
```

IHK-006 remains `TODO` and credit-ineligible. An audited irqsave-equivalent
outer lock, pinned owner and teardown drain, six legacy adapters and consumer
migration, proof for the raw-address ABA limitation, exact module build/load
evidence, and allocator runtime, fault-injection, lockdep, KCSAN, fragmentation,
and leak evidence are still required.

## Single build-control authority

This directory contains Rust crate roots and their reviewed contracts only. It
must not contain a `Kconfig`, `Kbuild`, or `Makefile`; duplicate build-control
files previously used a different symbol family and could silently select a
different module graph.

The sole production definitions are `host-kernel/kbuild/Kconfig` and
`host-kernel/kbuild/Kbuild.in`, bound by
`host-kernel/kbuild/stage-manifest.json`.

The Kconfig authority is parsed as a closed grammar by
`scripts/native_rust_kconfig_policy.py`. Its menu requires `RUST`, `X86_64`,
and `MODULES && m` in that order; the provider has no symbol-level dependency,
and each consumer depends only on the provider. Hidden control flow, extra
symbols, implicit defaults, and alternate build-control sources fail closed.
The compiler-evidence fragment explicitly enables `CONFIG_MODULES=y` before
selecting all three native modules as `m`; this remains compiler evidence only
and does not make the production stage or any gate claim ready.

Check these constraints with:

```sh
python3 scripts/native_rust_build_surface_audit.py
```

## IHK IKC queue source foundation

The native IHK crate includes `abi/x86_64.rs` and `ikc_queue.rs` through
literal Rust module edges in `ihk.rs`.  They therefore compile as part of the
single `ihk.o` crate object selected by the authoritative Kbuild; the queue is
not a separate object or module.  The queue source binds the frozen x86_64
header layout, wrapping 64-bit counters, the legacy 128-full-retry behavior,
reserve/copy/publish ordering, corruption checks, and the sole local Rust
dequeue-owner rule.

The source foundation does not allocate or map an IKC queue, notify McKernel,
or own teardown.  It also does not prove that the exact Rocky kernel compiled
the module or that Linux and McKernel interoperate at runtime, so it cannot
earn IHK-008 credit.  Validate the source contract, with an explicit compiler
skip when no exact compiler is configured, using:

```sh
python3 scripts/ihk_native_queue_check.py
```

The exact Rocky native-module workflow supplies its installed Rust 1.92
compiler explicitly and adds `--require-rustc`, which makes compilation and
execution of the five-test fixture mandatory.

## mcctrl lifecycle foundation

The lifecycle contract preserves the frozen zero-parameter surface and exact
semantic module metadata: `name=mcctrl`, `license=GPL v2`, `depends=ihk`, with
no author, description, or version field. The dependency is not forged in
source. Kconfig requires the native IHK provider and the crate emits the
reviewed `MCKERNEL_IHK_V1` import-namespace declaration. The crate now imports
and performs a volatile read of the provider's
`ihk_provider_lifecycle_v1` anchor, leaving modpost to derive `depends=ihk`
from the real relocation. Exact Rocky 10.2 build and runtime evidence is still
required to prove the built relocation, provider refcount, and unload ordering.

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
