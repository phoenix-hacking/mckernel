# Actual selected memory TU ordinary check passed

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The dispatcher-granted CPU0 check passed on its first attempt. The complete
reviewed `arch/x86_64/kernel/memory.c` postimage compiled with host
GCC9.4.0, the frozen supported defines and accepted generated headers.
All C clear-range argument size/alignment/field-offset and memory-object flag
witnesses compiled. The actual preprocessed translation unit selects the
external Rust callback declaration and excludes both original C definitions.

`nm -u` reports exactly one undefined `x86_clear_old_action_bridge` import.
`readelf -rW` records three `R_X86_64_GOT64` relocations to that callback, at
offsets `0xeb9`, `0x1029` and `0x13b2`. The selected object defines neither
the original C `clear_range_old_action` nor the C output adapter. Its SHA256 is
`92fca3c160f7ba3917a67b36651d68bb0e69ad2d0f5e70ee59a26c2a03e48bc4`.
The compiler's captured stderr is empty. No129,888-vector fixture replay or
bounded correction was needed.

The exact accepted helper990807ab captured creator PID3524038/start53139231.
It returned0, joined the direct child, found the entire group absent and
closed both streams. Error and retirement_error are null. Capture wall time
was0.835879181seconds; whole measured CPU was0.896532seconds. The CPU0 grant
was released immediately after the positive join.

This is ordinary host GCC9 selected-source ABI/preprocessor/relocation proof.
Its compiler/builtin include differ from pinned GCC14. Production Rust crate,
default final image ownership, real `phys_to_page` provider and matching native
clear/free-range behavior remain open. `NEXT-CONSUMER-COMMANDS.json` retains
those exact pinned follow-up observations. Canonical memory, the accepted
image10972 and its build output remain unchanged.

`ORDINARY-SELECTED-MEMORY-RESULT-1.json` retains the actual joined result.
`ACTUAL-ORDINARY-EVIDENCE-BINDING.json` binds wrapper, check, commands, named
tools and the139,445-byte raw archive. Archive SHA256:
`4c897394a36a4f322b20e67b8afbc92679d5320208b5ea4a624c95502027fdb8`.
It includes exact argv, preprocessed TU, object, symbol/relocation output,
streams and statuses. This does not close M14-F05/M14-05-03 or practical35.
