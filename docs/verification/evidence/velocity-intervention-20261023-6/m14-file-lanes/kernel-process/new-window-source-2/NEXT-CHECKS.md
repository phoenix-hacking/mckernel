Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private patch retires three selected C callback/provider bodies:
`process_default_ncpus_bridge`, `process_release_thread_profile_bridge` and
`process_release_profile_bridge`. It reuses the existing Rust CPU-info layout and
profile providers. All original C bodies remain under the fallback selection.

The Rust functions live in a leaf module, so the existing outer FFI declarations
and callers retain their exact types without duplicate Rust definitions. The
exported C symbols retain their names. The CPU getter is the existing exported
platform getter; no new C provider/getter is introduced. Original logical source
line locations are restored around each fallback so later tracked allocation
and logging locations retain their previous `__LINE__` values.

After root's new ordinary CPU grant, reuse the admitted fullcrate metadata command
from new-window-source-1/real-abi-correction-1, refreshing the current full source
snapshot and overlaying this exact private process_helpers postimage. Check once
with the existing `--cfg enable_profile` and once with that pair removed; every
other production cfg/ABI stays fixed. This exercises real Rust provider types
and both branches of the former C `PROFILE_ENABLE` condition. Do not replay the
old14 mock fixture or claim its behavior proof for these new bodies.

The actual C-header/Rust ABI table should add `IhkMcCpuInfo` size/alignment/ncpus
and `Process.profile`/`Process.nr_processes` offsets and scalar widths. Select the
actual CPU-info C type from `<ihk/cpu.h>`/the current production include closure;
keep the real provider's Rust `ap::IhkMcCpuInfo` rather than a mock struct. The
source consts bind its existing40-byte,8-byte-aligned layout and count offset0.

Compile current selected and fallback process consumers, then confirm the three
selected C definitions disappear and the actual Rust object supplies each once.
Preserve all other current undefined symbols/provider debt. Independent review
must confirm accumulation/print-before-free order, profile-disabled no-op behavior
and unchanged callback lifecycle ownership before root integrates this batch.
Native/current-default image proof remains required for whole-file retirement.

Canonical CPU-local `resource_set` offset7912 and B7's candidate offset7976 remain
separate. This patch reads neither CPU-local layout and imports no B7 ABI changes.
