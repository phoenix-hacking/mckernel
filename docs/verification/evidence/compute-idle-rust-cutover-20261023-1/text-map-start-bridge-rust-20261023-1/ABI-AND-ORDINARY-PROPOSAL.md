Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Scope: functional OS/apps plus separate active M14 Rust/reviewed-assembly cutover.

This is a private implemented source candidate. No compile, test, root operation,
heavy build, guest, target-register instruction or acceptance ran. CPU6 remains
reserved to the normal-cleanup guard; this packet does not request or consume it.

The finite live-source check finds the original C function still present and its
Rust `init_text_area` default consumer still calling it. The adjacent `_end`
bridge is outside this change. Existing CMake PUBLIC selection and Rust module
ownership remain unchanged. Canonical/frozen candidate5/6/LONG inputs are untouched.

`MAP_KERNEL_START` is not a portable architecture literal. Root CMake derives it
from the selected host kernel's MODULES_END minus8MiB, then kernel CMake supplies
the resulting `-DMAP_KERNEL_START=...UL`. The bounded existing Rust x86-memory/ABI
scope has no shared Rust constant or data export for it; another C getter returns
the same macro. Delegating the new getter to that function would retain a C body.
The new immutable unsigned-long witness carries the existing build value into
Rust using the module's existing `link_name` static-data pattern. It is declarative
C build geometry only, not C executable functionality or an invented numeric
address. PUBLIC C defines that data, Rust defines the original getter symbol;
non-PUBLIC C retains the byte-exact original getter and defines no witness.

The Rust body reads the witness's64-bit value, not its address. No mutable state,
allocation, user-pointer access, panic path, new layout or ownership transfer is
introduced. Existing `CULong=u64` is used. The real current arch-memory.h and
IHK types plus GCC9 width/type assertions provide the fixture's ABI expectations.
Integer-to-pointer-to-integer round trip checks preserve all address bits without
accessing the pointer. No x86 address is hardcoded in production Rust.

The private broad harness replaces only this getter's duplicate function stub
with an immutable data witness retaining its exact previous fixture value. It
checks the Rust getter against that witness, changes the getter expectation from
U to T and adds U for the witness. The overall undefined count and all other
symbols/tests remain unchanged. No monolithic harness run is proposed here.
`verify_source_delta.py` supplies an exact finite reverse comparison for the
three production/harness files; it has not been run during source preparation.

After an explicit root ordinary grant, the smallest useful profile is the
existing Rust1.92/GCC9, one CPU6 job, AS2GiB/CPU60/wall90+6/FSIZE32MiB/NOFILE256/
core0, RUST_MIN_STACK2MiB, with the unchanged990807 owned-capture helper and signal
handlers. No new profile, CPU grant, heavy operation or root guest is implied.

Compile one extracted actual Rust export object. Compile/link/run the original-C
versus PUBLIC Rust fixture for the existing host-profile address and finite
unsigned-long boundaries (0,1,bit31,bit32,bit63,max); no benchmark or random inputs.
The same Rust object is reused, ensuring the value cannot be hardcoded in Rust.
Compile/run one non-PUBLIC fallback fixture. Compile PUBLIC and fallback consumer
objects against the selected actual fragment/header; bind the PUBLIC C object
and Rust object with ld-r and inspect exactly one T getter plus one R geometry,
no unresolved getter or geometry, no C duplicate. Fallback must retain local t
getter and no witness. Run the finite source reverse check and bash-n only.

Default current full-crate and kernel linked-artifact/native acceptance remain
open. Any later full-crate compile must reuse an independently admitted profile
and actual complete source closure; Rust1.92 leaf-object success is not that proof.
The declarative geometry data remains a C-source item until the build geometry
is generated directly for Rust in a separately reviewed change; do not report a
whole C file, whole image or native path as retired from this packet.
