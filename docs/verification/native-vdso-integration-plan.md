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

That leaf-only opacity retry also fails: bindgen keeps explicit alignment on
the opaque unions, which still cannot be embedded in their packed parents.
Preserve the second failure and remove the additional opaque-type rules.
The next patch instead uses Linux's existing `__BINDGEN__` preprocessor mode
to omit only the private user-space helper-header inclusion at the end of
`include/vdso/datapage.h`. All actual vDSO data declarations remain visible;
normal C selects exactly the original implementation. Compare normal C
preprocessing before/after this patch, excluding source-position markers,
then repeat the layout witness and build. No layout or production C body is
rewritten to accommodate binding generation.

Kernel attempt 3 now passes normal C preprocessing equivalence, all 44 layout
values, the pinned kernel rebuild and the three existing prototype modules.
The original resolved configuration is unchanged and all three new data
exports are present. Add a read-only disposable Rust module fixture that uses
those actual exports, independently emits all 44 generated layout values,
checks the two-page ELF text and reads live sequence-protected coarse time
against Linux's own time API. It must verify updates and unchanged text across
module lifetimes, without responding to McKernel. Repeat the existing actual
control-connection captures with the rebuilt kernel; then implement the
versioned descriptor and real service described above.

The Rust fixture now compiles, imports the actual three Linux data symbols and
its time/sleep APIs, and passes ELF/no-SIMD checks. Its emitted layout agrees
byte-for-byte with the independent C witness for all 44 values. Prototype 5
also builds all three existing native modules against this rebuilt kernel.
The next guest uses the unchanged revision-2 McKernel image and boot/control
probe, plus two read-only fixture lifetimes before native resource assignment.
QMP will independently capture the Linux text/time/RNG pages, compare the text
hash with the actual module reads and check those pages remain outside assigned
McKernel memory. The service descriptor must still remain busy in this replay.

Preparation and both actual-start replays now pass. Every guest verifies two
read-only fixture lifetimes and 32 coherent samples against Linux time, then
captures the Linux text/time/RNG pages independently with QMP. Both McKernel
starts still complete the two control connections and deliver their first
vDSO request; the original 88-byte descriptor remains busy. The new Linux text
FNV64 is `c9b0bc0d04c8c91b`. That is the Linux vDSO text identity, separate from
the unchanged McKernel image identity in the previous control checkpoint.

All these TCG guests select `VDSO_CLOCKMODE_NONE` after Linux rejects the
unsynchronized TSC. The live fixture proves coherent coarse time, data updates
and exported object access, not an accelerated TSC clock. The native guest
must honor the current clock mode and preserve a valid fallback. Do not force
a TSC clocksource merely to advance boot. In particular, inspect
`kernel/rust/x86_vsyscall.rs`, the clock/gettimeofday/nanosleep wrappers in
`syscall_policy.rs` and `init.rs`'s local-time flags as well as the direct
`calculate_time_from_tsc` reader when adapting the clock path.

## Next native descriptor boundary

Use a separate Rust-owned, aligned native exchange with an explicit version,
size and completion status. A candidate 128-byte layout is: 64-bit busy;
32-bit version, byte size, signed status, text-page count, data-page count and
clock-layout ID; two 64-bit text physical addresses; six 64-bit data physical
addresses; four reserved 64-bit words. Keep the existing IKC packet/message
unchanged. The six data entries represent the exact negative page offsets
already witnessed; absent namespace/architecture pages stay unmapped. Map
ordinary time/RNG/clock RAM with ordinary cache attributes, not HPET attributes.

Advertise this additional capability with a new native boot-note revision;
the completed-read queue contract itself stays revision 2. Preserve parsing
of older notes and reject an incompatible native peer before startup-resource
allocation. On the guest, keep the C-owned 88-byte ArchVdso object within its
original bounds: copy only a validated compatible prefix into it if reusing
the existing setup/map bodies, and pass supplemental native data mappings
through an explicit internal mapping interface. Never append host writes to
that legacy object's allocation. Publish the complete response before a
release store of busy, and consume it with an acquire operation. Validate the
descriptor extent, generation, alignment, version, size and queue disjointness
before any host write. Native service implementation and its actual-body
failure/publication/mapping/time tests remain the next work.

The completed export/layout/live-data checkpoint is
`native-vdso-exports-checkpoint-20260907.json`: 34 retained artifacts include
both failed binding attempts, the passing kernel and module builds, all three
guest replays, compiler sources, helper scripts and independent captures.
All retained input/output identities and gzip round trips pass. This checkpoint
preserves the earlier control-channel results and does not complete the native
vDSO service or promote a production gate.

The first service implementation now shares the explicit descriptor and its
one-shot publication functions between the host and guest. Native boot note 3
requires both completed queue reads and generic vDSO consumption; notes 1/2
remain loadable but cannot prepare native startup. The host checks the whole
128-byte extent, exact OS generation and every active queue before responding.
Linux backing pages must remain outside all reserved McKernel extents.

The guest owns its native exchange separately and copies only the original
88-byte prefix into ArchVdso after full validation. Existing setup/map bodies
are reused through an explicit supplemental-page slice. Normal RAM mappings
cover RNG and any exported PV/HV pages while leaving the namespace and
architecture holes unmapped. Native setup failures stop boot instead of being
ignored. The new native reader uses the witnessed generic-overflow layout and
the actual x86 Linux arithmetic, including backward-TSC clamping and overflow.
Public clock syscalls read a supported Linux mode or forward through the
existing syscall transport. Legacy local-time flags stay disabled in this
native path; CPU-accounting calibration is retained. Internal boot/timer
readers may use coherent Linux coarse time when TSC is unavailable. These are
explicit fallbacks, not proof of accelerated clocks or completed offload.

Service-tests attempt 1 passes eight protocol/mapping/clock tests, 128
cross-page concurrent exchanges with canaries, all malformed request bytes,
77,824 exact pinned Linux arithmetic comparisons, and the existing three
image/loader/startup policy fixtures. The original Linux arithmetic bodies
are extracted unchanged from the pinned source for the independent C oracle.
The native and legacy images, Linux adapter build, supplemental mapping
callbacks and actual cross-kernel service still require verification.

Service-tests attempt 2 adds the complete original C arch_map_vdso body and
complete production Rust mapping bodies with only their primitive callbacks
replaced by a recorded trace. All 144 legacy cases agree, including each
callback failure. Native tests verify all optional page combinations, exact
physical/virtual addresses, ordinary cache attributes, unmapped holes and
pre-mutation rejection. Native prototype 8 now compiles all three modules and
passes exact layout/ELF/no-SIMD checks. Attempts 6/7 preserve the Rust kernel
API and unreachable-pub failures; their fixes do not change the wire contract.
Next rebuild the three images and run actual preparation/start captures.

## Verified service checkpoint, 2026-09-07 local date

Image attempt 12 exposed missing standalone slice-panic and `bcmp` dependencies
in the descriptor codec. The fixed-word iteration and checked storage access
preserve the wire bytes without introducing a C runtime. Source-check attempts
3/4 pass the protocol, arithmetic and mapping coverage after that change.
Attempt 4 also executes the production host ownership adapter: stale owners,
whole-extent failures, every queue alias and reserved Linux-page overlap are
rejected before writes, while a valid cross-page response preserves canaries.

All three images build in attempt 13. Prototype 9 builds the final host codec
and all three modules, with exact layout witnesses and ELF/no-SIMD checks.
The native image has boot note revision 3, SHA-256
`c37e6e7d30e09079003bcb9ed80baf27acc18f9d60d472e79826629b01a62e80`,
entry `0xfffffffffe846c00` and loaded-window FNV `aa6419ab7afa5442`.
The actual loader validates all three new images and the preserved revision-1
and revision-2 native images. Both preparation ABIs pass over two module
lifetimes, including 32 forced allocation failures, old-capability rejection
before startup and complete unstarted resource restoration.

Both actual-start ABIs now complete the real vDSO service. Independent QMP
captures verify all 128 descriptor bytes against the actual Linux pages, guest
validation state 2, the original 88-byte object, the 32,768-byte container,
24,576-byte text offset and disabled legacy local-time flags. The time pointer
uses the captured direct-map base and Linux time-page physical address.
McKernel reports `vdso is enabled` and sends its next real setup request.

That request is `SCD_MSG_SYSFS_REQ_SETUP` (0x40). Its payload uses
`body.sysfs.sysfs_arg1` at packet byte 24, rather than the traditional vDSO
argument at byte 40. The first startup capture failed because it used the wrong
union member; its normal/emergency evidence is preserved. Corrected native and
compat captures both pass, including ownership/disjointness of the 1,056-byte
setup request and its separate 4 KiB data page. Busy at request byte 1,052
remains one, accurately identifying the next unimplemented host service.

See `native-vdso-service-checkpoint-20260907.json` for all 47 retained artifacts,
four preserved failures, source/compiled-input bindings and passing archive
round trips. All four source checks retain the exact formatted compiler inputs;
attempts 1-3 did not retain every original pre-format byte and make no such
verification claim. Attempt 4 additionally retains every original Rust input.

This completes the vDSO setup exchange at the native boot boundary. Actual
application PTE use is still untested; supplemental mapping evidence comes
from the production-body callback fixtures. TCG still uses clock mode NONE;
accelerated TSC/PV/Hyper-V clocks and encrypted memory are unverified, and
high-resolution forwarding needs the continuing runtime service loop. BOOT
still returns -110/Failed with started owners retained at the pending sysfs
request. Next reuse and adapt the existing Rust sysfs setup/dispatch bodies,
then complete continuing host services, full status 3, applications and native
shutdown. Declared integration, complete Rust/assembly ownership and independent
production acceptance remain separate unfinished requirements.
