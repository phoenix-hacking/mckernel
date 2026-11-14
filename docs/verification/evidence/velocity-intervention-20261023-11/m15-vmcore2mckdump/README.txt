Private vmcore2mckdump Rust successor — source ready, not executed
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

What is reused
The54-line shell program is retained byte-for-byte in reference/vmcore2mckdump.in. Existing executer/user/rust/ldump2mcdump_helpers.rs already supplies cmd_ldump2mcdump under --cfg ldump2_full_body. That producer and its BFD dump layout remain the format owner. The215-line vmcore2mckdump.rs ports the five-command Expect conversation into Rust using an ordinary PTY and baseline crash. It adds no BFD/ELF parser and embeds no custom shell/Tcl runtime.

Reference behavior and deliberate correction
The script runs uname before argument checks, ignores its status, accepts extra arguments after an empty third argument, maps x86_64 to x86, and exports the same four environment fields. Basic usage/input/architecture diagnostics are retained. Its final result depends only on output-file existence, so a stale or partial file can produce success even after Expect/crash failed. That observation remains in reference captures and is not an intended Rust oracle.

Root must choose the proposed correction: require all prompts, clean crash exit, an exact path-bound acknowledgment from the matching converter, and a fresh nonempty regular staging file before atomic publication. Pre-existing output bytes remain untouched on failure. Incomplete staging is retained separately with its path for evidence. The converter still owns output validity; a fresh/nonempty file or synthetic marker alone is no format proof.

Separate converter proposal
converter-ack.patch and ldump2mcdump_helpers.ack-candidate.rs are private proposals against the pinned existing Rust producer. Required metadata reads are checked before assume_init/use. Physical read failures retain the existing diagnostic and continued observations, but suppress success acknowledgment. Existing BFD write/close errors return before acknowledgment; missing required physchunks also blocks it. After successful close and buffer cleanup, one MCKERNEL_LDUMP2MCDUMP_SUCCESS <PATH> line is emitted/flushed. No dump section/layout/content encoder is changed. This patch has not compiled or run. converter-ack-contract.json gives its required fault matrix. The current pure-helper smoke is useful reuse, but does not prove this full-command delta.

The strict wrapper cannot be installed against the unmodified producer: it has no acknowledgment. Root must jointly review and qualify the producer and consumer, or choose a different explicit failure-status contract. No canonical source has changed.

Smallest next executable fixture
All22 cases are data in fixture/cases.json. The prepared driver compiles Rust and uses a synthetic crash PTY peer plus a uname stub, covering original CLI errors, command order/env, fragmented prompts, status/signal/EOF/timeout, missing/wrong acknowledgment, empty output, and preservation of old bytes. Payload bytes are explicitly not a real dump. Seven front-end comparisons use the actual original script before it reaches Expect. If actual Expect is absent, one separately labeled observation records stale-output success; it is not acceptance. Optional --with-reference-protocol requires real platform Expect and only binds the private crash path/short fixture timeout. No fake Tcl parser substitutes for it.

At preparation both /usr/bin/expect and /usr/bin/crash are absent. This is a real prerequisite for original-driver/native comparison. Original/native transcript bytes, PTY terminal modes and real dump validity remain unproven.

Proposed ordinary grant:1CPU,1GiB memory,64 tasks,160seconds wall (150seconds work plus bounded cleanup),64MiB private output,jobs1; no root/Docker/guest/custom devices. Ordinary PTY access, libc/libutil and the helper's unprivileged child-subreaper/self-children ownership join must be admitted. The driver captures/joins PTY peers even though they create separate sessions, refuses existing fixture-output and preserves original failures. Exact first command, only after controller grant:

/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-11/m15-vmcore2mckdump/fixture/run_fixture.py --execute --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc

No driver mode, compiler, subprocess fixture, PTY, converter or native operation has run. Only source/data checks ran: Python AST and JSON parsing, exact source snapshot comparisons, bounded source pins and private diff generation. Root owns publication/integration/grants. Source-reference hashes are in REFERENCE-PINS.json; originals need not be assumed identical to committed HEAD. Earlier ihkconfig/mcps packages remain frozen and unchanged. The original35 and M14 accounting remain unchanged.

CMake-selection-proposal.cmake replaces only this generated program's selector after joint acceptance, retains the same install path and depends on the existing producer. Coordinate that shared CMake file centrally with other user-tool lanes.
