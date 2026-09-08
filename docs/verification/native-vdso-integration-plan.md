# Native vDSO adaptation

Source parent: `231c72167ddafc11392c375166d0d9b92a5ba174`, 2026-09-07.
The actual native and compat starts now deliver SCD_MSG_GET_VDSO_INFO over
port 503. This plan records the reuse boundary before implementing its service.

## Existing consumers

| Source and symbols | Treatment | Required adaptation |
| --- | --- | --- |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::{McctrlVdso,get_vdso_info}` | Retain its compatibility consumer; adapt its page enumeration and release-last reply sequence for native Linux. | Its bridge looks up `__vvar_page` and the old three-page layout, which the pinned native Linux no longer supplies. Its unchecked legacy mapping cannot serve the generation-owned native memory model. |
| `kernel/rust/syscall_policy.rs::{ArchVdso,arch_setup_vdso_body_result,arch_map_vdso_body_result}` | Reuse setup, container geometry and page-table callback sequencing. | Native Linux has six pages before the text, with separately backed generic and optional clock data; preserve holes and normal cache attributes. Keep the legacy 88-byte object intact. |
| `kernel/rust/syscall_policy.rs::calculate_time_from_tsc` | Retain the legacy branch; adapt the native branch against exact clock-layout evidence. | The native clock puts cycle_last at offset 8 and max_cycles at 16. Reading it through the old VsyscallGtodData would produce incorrect time. Unsupported hardware clock modes must use an explicit fallback. |
| `kernel/rust/x86_memory_helpers.rs::x86_vdso_packet_prepare_result` | Reuse packet preparation. | A versioned native descriptor must have a real Rust-owned allocation, rather than writing an extension beyond the C-owned 88-byte object. |
| `arch/x86_64/kernel/syscall.c::{vdso_get_vdso_info,vdso_map_global_pages}` | Preserve fallback bodies; replace selected execution bodies with Rust after direct equivalence coverage. | Reuse current channel, physical-address and page-table primitives while moving descriptor initialization/wait/publication into Rust. |
| `host-kernel/native-rust/smp_memory.rs::{checked_guest_queue,linux_boot_root}` and owned control channels | Extract only the reusable address/ownership checks; retain all started lifetimes. | Service arguments may be unaligned to pages or cross a page boundary. Validate their whole byte extent and exact OS generation, plus disjointness from active queues, before writing a reply. |

## Exact Linux boundary

The target remains Linux `6.12.0-211.44.1.el10_2` with the existing resolved
configuration and toolchain. This source includes generic vDSO data-store
backports: `include/vdso/datapage.h`, `lib/vdso/datastore.c`,
`arch/x86/include/asm/vdso/vsyscall.h` and `arch/x86/entry/vdso/vma.c` are the
authority, rather than a version-number assumption.

The current generated `vdso_image_64` has two text pages. Six reserved pages
precede it: generic time at -6 pages, time namespace at -5, RNG at -4,
architecture data at -3, pvclock at -2 and Hyper-V clock at -1. Initial namespace
mapping leaves its namespace hole unmapped, and this configuration has no
architecture data. Time and RNG pages are permanently owned and updated by
Linux. Optional pvclock/Hyper-V pages must come from Linux's existing exported
getters, with their lifetime and platform restrictions preserved.

Patch 0008 will expose the existing `vdso_image_64`, `vdso_k_time_data` and
`vdso_k_rng_data` symbols and their existing header declarations to Rust.
It adds no C function body or alternate implementation. The native adapter
will read those objects; Linux retains all updates and allocation ownership.
Compile an independent C witness against the exact configured headers and
retain generated bindings, symbol exports and kernel/module artifacts before
using this boundary in the service. Preserve the resolved configuration.

## Protocol and validation sequence

Use an explicit native boot capability for the new vDSO descriptor/clock layout.
Old native notes remain parseable; preparation must reject an incompatible peer
before allocating startup resources. Keep the existing 128-byte IKC packet and
message number. The new Rust-owned exchange uses a version/size check and
release/acquire completion. Validate the entire response before copying any
legacy-compatible prefix into the existing guest state. A zero-page reply or
clearing busy without usable Linux data is not a completed service.

First establish the exact Linux binding/export/layout boundary. Next implement
and test descriptor validation, physical ownership, page enumeration and guest
consumption using actual bodies, including failure and publication ordering.
Build C fallback, legacy Rust and native Rust images and native modules, then
repeat preparation and both actual-start ABIs with independent QMP captures of
the request, response, backing pages and next guest request. Preserve all first
failures. Successful vDSO service alone does not prove full status 3, sysfs,
mcctrl, asynchronous runtime dispatch, applications, native shutdown, full
Rust/assembly ownership or independent production acceptance.

The first exact-header witness passes all 44 values, including the 232-byte
clock and 512-byte, 64-aligned time structure. The first kernel rebuild fails
E0588 in unrelated Hyper-V MSI register unions reached through vDSO headers.
Retain that attempt and its generated bindings. The corrected patch follows
Linux's existing `rust/bindgen_parameters` rule for packed x86 MSI registers:
keep `hv_msi_address_register` and `hv_msi_data_register` opaque. Their C layout
and implementation stay unchanged, and the native vDSO adapter does not access
them. The actual vDSO structures remain fully generated and independently
witnessed. A new capture will reverse only the exact failed patch before
applying the corrected complete patch and rebuilding.
