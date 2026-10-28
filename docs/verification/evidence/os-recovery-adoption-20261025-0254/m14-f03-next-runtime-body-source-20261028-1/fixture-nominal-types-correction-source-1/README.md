Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One bounded fixture-only correction after preserved original C compiler failure.
The actual kernel typedef and do_mmap declaration use intptr_t/uintptr_t/off_t;
the original mock used nominally different long/unsigned long types. Their x86
machine ABI is unchanged, but GCC correctly rejects the mismatched declaration.
This successor copies only the driver, using the exact original provider typedef
and genuine do_mmap signature. Parent production C/Rust patches and all fixture
oracles remain unchanged. Relative include paths select exact parent originals.

The Rust object already compiled with rc0 and empty diagnostics; the two-command
suffix links that exact object and runs the unchanged ABI18/160-pair oracle.
Neither suffix command is executed or granted here. Original source/plan/grant,
failed command and captured diagnostics remain preserved. The failure concerns
the fixture and does not qualify kernel behavior or add native/default credit.
