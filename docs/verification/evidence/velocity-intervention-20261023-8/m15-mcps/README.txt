Private M15-P05 mcps Rust successor, lane2
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Actual shipped behavior
executer/user/mcps.in is ten lines. It ignores all user arguments and runs ${prefix}/bin/mcinspect --kernel=${MCKERNELDIR}/mckernel.img --ps. There are no independent ps/proc options, filtering or formatting to port. The existing mcinspect_helpers.rs mcps/mcinspect_mcps_body_result implementation continues owning enumeration and output. No process formatter was duplicated.

Source candidate
mcps.rs is a68-line no_std Linux x86_64 wrapper. libc posix_spawn and waitpid delegate to the existing mcinspect executable, inherit streams/environment and preserve ordinary child exit codes. Configured prefix/kernel paths are compile-time inputs. Missing-command/permission/directory errors have a C-locale diagnostic implementation for first comparison. The successor contains no custom shell runtime. The initial ihkconfig candidate is unchanged.

Honest remaining boundary
This is source ready for its first fixture, not complete behavior retirement. Exact Bash signal-death stderr is not implemented/accepted;23 prepared cases retain two signal parity cases that may expose differences. Keep those failures, then implement from actual evidence rather than marking a reduced matrix PASS. Legacy nonliteral configured paths, arbitrary invalid executable/shebang replacements, Bash ENOEXEC fallback, localized Bash diagnostics and fork/spawn resource-exhaustion behavior are not newly accepted. The CMake proposal requires literal paths and a valid installed mcinspect executable; root must review that supported-profile contract. The original script remains retained as the test oracle.

Concrete fixture
fixture/run_equivalence.py builds only the Rust object/executable and compares it with the original configured script using fixture/mcinspect_stub.py. The stub emits synthetic rows/header/empty/binary output, diagnostic bytes and selected exit statuses, records exact argv/environment/cwd/stdin, and can terminate itself for signal parity. No /proc, custom devices, native kernel or real McKernel image is accessed. Both programs run under the same logical invocation path so script diagnostics can compare. Only dynamic worker PID at the Bash diagnostic prefix is normalized; raw output is preserved.

Proposed fresh ordinary host grant
One CPU,1GiB memory,64 tasks,130seconds wall (120seconds work plus bounded cleanup),32MiB private output, jobs1. No root, Docker, guest or devices. The driver must admit child-subreaper mode for itself, own a fresh process group for every compiler/utility, capture results and verify complete group retirement. Unexpected descendants/timeouts fail and stop; unknown retirement retains ownership. Existing fixture-output is never overwritten. Qualify the installed compilers/environment under the fresh grant before executing:

/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-mcps/fixture/run_equivalence.py --execute --cc /usr/bin/cc --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc

Only Python preparation/AST checks have run, using the exact /usr/bin/python3 -I driver path. No C/Rust compiler, mcps/original script/mcinspect fixture, subreaper admission or native operation has executed. A first fixture result may be FAIL because signal diagnostics remain open; preserve it and correct only the demonstrated boundary.

Selector proposal
CMake-selection-proposal.cmake replaces only mcps configure/install selection with a Rust target and dependency on mcinspect. It removes the generated shell mcps from install(PROGRAMS), leaving vmcore2mckdump. The actual executer/user/CMakeLists.txt is shared with lane3 BFD work and must be integrated centrally. No canonical file has changed.

Library-owner forward
The next READY queue handoff also forwards case227_stage the frozen ihkconfig consumer's exact four public libihk functions and structs, recorded in CONTRACT.json. No private API changes are proposed. Temporary C libihk remains separate debt. Neither this candidate nor the host stub proves production link/native acceptance or changes the original35/M14 worklists.
