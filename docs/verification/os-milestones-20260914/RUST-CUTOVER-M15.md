# M15: custom host modules and integration runtime in Rust

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The user explicitly requires project-owned production runtime code to use Rust,
retaining the earlier reviewed-assembly allowance. Rocky/Linux-owned control-plane
code is explicitly permitted to remain C. This includes custom modules
loaded into Rocky Linux, executors, libraries and installed management/diagnostic
tools. M14 covers the supported McKernel compute kernel. M15 covers the remaining
custom runtime outside M14. Original35 functional checks, M14 and M15 are separate;
none implies completion of the others. No new broad soak or fuzz quota is added.

Use [rust-cutover-m15.json](rust-cutover-m15.json) as the worklist. The initial
[bounded target inventory](rust-cutover-m15-inventory-20261024.json) records current
selectors under the retained smp-x86 / Rust-user-tools=ON / QLMPI=OFF / UTI=OFF
configuration. It is not a complete final ELF or deployment manifest. Record
unknown ownership honestly and add any further selected custom runtime found.

## Actual SDK library link — 2026-10-24 18:38 UTC

The retained ten compiler-prefix commands plus five fresh SDK suffix commands pass.
The resulting `libihk.so` (SHA256 `546dbe7604e8911e36ae9c10f07dee0dc279ae88d1d4584a0da5d1232be6db6e`,
12,095,032 bytes) uniquely defines all70 required text and6 data providers. Strict
real-BFD linking and unresolved-provider checks pass. The prior diagnostic failure
remains preserved; its compiled archive was reused without recompilation or rehash.
Independent artifact review and normal physical retirement pass. Actual target
CMake default selection, CLI execution and matching native proof remain open.
[Retained proof](../evidence/m15-sdk-library-whole70-link-qualification-20261024-1/RETENTION.json).

## Existing Rust work is reused

The project already has native Rust module roots:

- [ihk.rs](../../../host-kernel/native-rust/ihk.rs): IHK host core.
- [ihk_smp_x86_64.rs](../../../host-kernel/native-rust/ihk_smp_x86_64.rs): SMP driver,
  with existing architecture assembly.
- [mcctrl.rs](../../../host-kernel/native-rust/mcctrl.rs): host process/control driver.

The Oct19 module artifact review records actual pinned-SDK Rust compilation,
strict source dependencies and module ABI. Its separate tested205 recipe joins
matching application/lifecycle and physical evidence. Reuse those results only
for their exact sources/artifacts. They do not establish current zero-project-C
ownership or full functionality. The retained upstream ihk C tree is not the
selected native Rust driver implementation. No driver rewrite is necessary merely
because that reference tree is still present.

Several user tools also already select Rust: sched_yield, ldump2mcdump, mcstat,
and the main mcinspect/eclair bodies. Their custom C adapters and transitive
project library dependencies remain part of M15. In particular, Rust mcstat still
links the currently C-selected libihk.

## Known selected project C outside M14

| Goal | Target / C source | Remaining work |
| --- | --- | --- |
| M15-F01 | mcctrl: host-kernel/native-rust/mcctrl_vm_write_compat.c | Three Linux MM wrappers; preserve exact pinned lock, tracing, seqcount and VMA semantics |
| M15-F02 | mcexec: executer/user/mcexec.c | Remaining C main/ABI/callback bodies around existing Rust orchestration |
| M15-F03 | mcinspect: executer/user/mcinspect_bfd_shim.c | Two BFD accessor wrappers around the existing Rust tool |
| M15-F04 | eclair: executer/user/eclair_bfd_shim.c | Two BFD accessor wrappers around the existing Rust tool |
| M15-F05 | libihk: ihk/linux/user/ihklib.c | Public library ABI and request/resource/lifecycle bodies; recover proven reusable Rust or implement |
| M15-F06 | ihkconfig: ihk/linux/user/ihkconfig.c | Management CLI/actions/errors and default Rust selection |
| M15-F07 | ihkosctl: ihk/linux/user/ihkosctl.c | OS-control CLI/actions/errors and default Rust selection |
| M15-F08 | ihkmond: ihk/linux/user/ihkmond.c | Monitoring/event/thread/kmsg ownership and default Rust selection |

These eight files are additional to M14's six compute C translation units. The
seven user-space source selections follow current CMake rules under a retained
configuration; their full current link/deployment closure remains to be joined.
Raw line counts include comments and fallbacks and are not an engineering score.
Historical ihklib_helpers.rs claims do not prove a current Rust libihk: the pinned
user-library selector is C, so reuse requires an identified source and ABI match.

The three module wrappers are individually tracked:

1. mckernel_inherited_mmap_write_lock.
2. mckernel_inherited_mmap_write_unlock.
3. mckernel_inherited_vma_start_write.

Pinned Linux6.12 has CONFIG_PER_VMA_LOCK and TRACING enabled and lacks a ready
Rust MM/static-key abstraction. down_write/up_write alone are not equivalent.
A private proposal must settle sequence-count/barrier/WRITE_ONCE and enabled
tracepoint/jump-label behavior against that exact configuration, using existing
Linux primitives or reviewed assembly where appropriate. Keep the working C
wrappers until the actual Rust successor qualifies. Moving the same C into the
Linux tree does not complete M15. A blocked wrapper does not stall other ports.

## Installed custom runtime programs

The all-custom-runtime requirement also covers these five installed programs,
which currently use shell or expect. Preserve their command, exit, diagnostics,
privilege, lifecycle and cleanup behavior in Rust successors:

- scripts/mcreboot-smp.sh.in.
- scripts/mcstop+release-smp.sh.in.
- scripts/eclair-dump-backtrace.exp.in.
- executer/user/vmcore2mckdump.in.
- executer/user/mcps.in.

The Python campaign launcher and build/test orchestration remain development
infrastructure. Existing fixtures and inactive C references can remain. This
classification must not be used to hide a program shipped as part of the OS.

## Boundary and acceptance

Unmodified Rocky/Linux APIs, legitimate third-party libc/BFD/libdwarf code and
generated Linux module metadata are recorded dependencies. Project-authored
runtime code remains in scope when staged into a kernel, vendor or generated
path. Generic platform support patches require provenance/boundary classification;
a path name alone supplies no exemption. The optional crash extension, QLMPI,
UTI and other configurations need explicit delivery dispositions. Disabled or
unassessed does not mean converted; no delivered custom component may be omitted.

For each live C body or runtime program require its Rust implementation, focused
behavior/ABI checks, actual production selection/link ownership and applicable
matching native proof. Calling Linux/libc APIs through FFI is allowed; calling
remaining project C implementation bodies is not final closure. Preserve current
functional code until a successor passes. Do not change the pinned platform,
resource limits or native execution authority through a source-only plan.

Four final joins remain open: a complete delivered-runtime ownership manifest;
actual C-free project module links under the pinned Rust-enabled kernel;
Rust executor/library/tool artifacts and their project dependency closure; and
matching module/application/lifecycle/resource-restoration behavior. Reuse matching
existing practical evidence and test the changed paths with the real new cohort.

No validated M15 completion percentage exists. Existing Rust modules and tools
are credited at their scoped evidence; new inventories and source proposals add
no native credit. Continue six M14 file owners and P12 alongside independent M15
source work. Group related changes and reuse compiled artifacts; avoid repetitive
whole-tree scans, hashing or packet preparation for ordinary edits in an existing
reviewed profile.
