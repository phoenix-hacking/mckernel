Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private current119 integration rebases the existing runtime program proposal on
current canonical CMake. The top-level preimage remains e60b304f; the user CMake
preimage has changed. Only the original boot/backtrace consumer replacement and
single vmcore configure/include replacement are applied. All current mcexec
MCEXEC_USER_RUSTC/provider flags/build-id/install-component selection, BFD object
routing, ldump and mcps selections remain byte-for-byte outside those exact hunks.
The complete patch passes git apply --check against current canonical files.
No canonical sources or installedconsumer/root58 packets changed.

Eleven Rust/config bodies are reused exactly through FILEMAP.SOURCE-ONLY.json;
there is no new port. Three original selector designs retain defaults OFF and
independent explicit MCKERNEL_RUNTIME_TOOL_RUSTC. Each now adds that compiler to
its custom-command DEPENDS. Actual old generator output omitted the compiler as
a dependency; changing a qualified compiler could leave an old runtime executable.
The corrected generator graph includes the dependency for all three selectors.

Eight actual /usr/bin/cmake3.25.1 LANGUAGES NONE configurations ran on CPU0 with
one-job environment and AS2GiB/FS32MiB/NOFILE256/CORE0 limits. Default OFF configures
working reference scripts, missing compiler refuses ON, prior and fixed boot/
backtrace graphs distinguish the reproduced dependency defect, vmcore missing
producer refuses, and actual current converter source refuses for lacking ACK.
The final TEST_ONLY graph uses the exact retained ACK candidate plus fake target
leaves to inspect dependencies only. No compiler, target build, install, real
program, controller, SDK, Docker, root or native action ran. The inert compiler
file is deliberately nonexecutable. Generated mock targets grant no qualification.
All command argv, stdout, stderr and result are in generation-checks-1/.

After currentheavy work and actual current/ownership/resource admission, next is
fresh-output production SDK configure with boot/backtrace ON, vmcore OFF, then
cmake --build FRESH_BUILD --target mcreboot_rust_program mcstop_rust_program
eclair_backtrace_rust_program -- -j1 VERBOSE=1. NEXT-NAMED-TARGET-COMPILE.NOT-GRANTED.json
retains the exact prior accepted-cache commands and dependencies as a proposal;
Root must rebind the fresh output and this source closure in a genuine release.
Never run those programs for compiler validation. Existing boot8/eclair6 and
vmcore22 fixtures are retained at their original scopes. Runtime/native/default
acceptance stays open; vmcore still needs matched actual ACK producer plus its
behavior-contract and valid-dump checks.
