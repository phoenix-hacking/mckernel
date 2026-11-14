# F06 full-configure probe verifier: private successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only verifier and isolated synthetic tests. No real Kbuild, full configure,
Docker, module load, guest, native, privilege, controller or cleanup occurred.
This verifier is not wired into CMake and grants no execution authority.

Independent review found that the first verifier identified the symbol, while
original CMake reads the first `.data` bytes; those are not necessarily equal.
The reviewed finding is addressed by a bounded correction: the verifier requires
one `.data` match for the original grep pattern, the unique global 8-byte object
`MAP_KERNEL_START` at offset zero of that writable allocated section, no nonempty
relocation section targeting it, and bytes matching the caller's exact expected
16-hex value. It also requires a real generated `compile_commands.json` row for
exact `/src/arch/x86_64/kernel/syscall.c` with one matching
`-DMAP_KERNEL_START=<expected>UL` and `-DKERNEL_RAM_VADDR=<expected>`, and actual
CMakeCache `UNAME_R` and `KERNEL_DIR` matching the explicit inputs. `kernel.release`
and `utsrelease.h` must both match that release. The exact release is intentionally
unbound pending the matching retained Linux build identity; the old e6a cache's
5.15 value and Rocky 6.12 source version must not be silently equated.

The verifier requires the caller's actual make status string `0` and explicit
module/release/header/cache/compile-command paths tied to the stated build and
kernel directories; it rejects a symlink at each input file. These checks do not
authenticate the status string, owner, parent directories, creation freshness,
external inputs, or full include closure. The current root CMake does not retain
make's RESULT_VARIABLE, so a separately reviewed source/owner change must capture
its actual wait status; a string supplied without that proof is insufficient.
The verifier runs after generated CMake output exists and cannot retroactively
make configure's Kbuild side effects safe. Exact tool/environment and kernel
config/physical source identities, fresh output ownership, reviewed Kbuild
write/isolation scope and fresh operation release remain required. It deliberately
rejects any relocation targeting the whole data section, a conservative bound
that may reject a future valid object pending review.

`python3 test_probe.py` returned 0: 36 synthetic tests passed. They cover valid
ELF and actual CLI output; failed make despite an existing module; missing or
mismatched kernel release/UTS/cache; wrong generated map/kernel flags, duplicate
flags/commands; duplicate or nonzero-offset data symbol, relocation; wrong ELF
class/endian/machine/binding/string table; truncated input and mismatched input
roots. All stderr is retained. They do not execute real Kbuild or configure.
`python3 inspect_retained.py` read the historical e6a `driver.ko` only and
confirmed its actual profile-bound SHA256
`0c5c6d38362e859db21c28cba14101e8bc62119d4b33f5e38820294196444ff6` and raw
symbol value `0xfffffffffe800000`; this is historical, not the candidate probe.

The first read-only retained-object inspection failed because its hand-entered
expected SHA expanded a shortened prefix incorrectly. Original stderr is retained
as `retained-probe.initial.stderr`. One correction derives the full expected
hash directly from the exact e6a profile; the corrected inspection passes. The
initial pre-review verifier and 16-test results remain as `verify_probe.initial.py`,
`test_probe.initial.py` and `test.initial.stderr`.

Hashes:

- `verify_probe.py`: `157e2bd952f07c70a867fa9bd78165ac364c21d87f7dc32e3ecc482c191f7ca7`.
- `test_probe.py`: `ff7c20438ce5c64d170bb20d4a4bfb409e1ec43f604860dc2204bac221df83e0`.
- `test.stderr`: `97aa48e46cb01df80431587a0884f881c72aae1c06cd1ad8928bdcbb3d48e64c`.
- `inspect_retained.py`: `c7c24f611ee9ce1166fe74af3269894040c5017e4d8cf068d41df552ecdb8836`.

Independent review must assess this successor and its exact potential integration
before use. No generated flags, production link, native behavior or retirement is
claimed by the local fixtures.
