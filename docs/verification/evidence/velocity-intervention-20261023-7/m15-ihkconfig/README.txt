Private M15-F06 ihkconfig Rust CLI successor
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source-ready candidate: ihkconfig.rs (Linux x86_64, no_std C-main object). No C/Rust compiler, CLI fixture, Docker, root command, guest or native operation has run. Python source parsing and a preparation-only case listing are the only executable checks so far. This is ready for the first compiler grant, not a PASS claim.

The 601-line current ihkconfig.c was chosen instead of the larger ihkosctl.c. Original CLI source is retained in reference/ihkconfig.c. The current pin has no readily identified Rust replacement; no history search was performed. Narrow private ihklib parsing/format helpers were ported into the Rust CLI so it imports only four public libihk functions. The verbatim C helper extracts are a test oracle only. Current libihk C remains an explicit temporary dependency. The CLI alone does not close C-free runtime acceptance.

Behavior retained
All original commands and the conditional KRM action are implemented. Preserve argument precedence, decimal/hex libc parsing, peculiar count-only validation, resource-list behavior, request structures, open/close/ioctl sequence, stdout/stderr diagnostics and return codes. The original has no special --help action. For negative handler returns, C startup preserves shell status modulo256. Unknown actions still open the device before reporting usage and return0 when the open succeeds. No new C production behavior is proposed.

Defined behavior requiring review
The C short-pread path prints indeterminate stack tail; Rust zero-fills it. The build-id path can print past its buffer if a provider omits NUL; Rust bounds it. The C query formatter can continue with a freed/null string on realloc failure; Rust stops with the existing result-string diagnostic and-1. Extreme signed-overflow paths have defined wrapping/terminating Rust behavior but no parity claim. These must receive a correctness-contract review instead of reproducing undefined C data. Three Rust-only fixture contracts are separated from the C equivalence matrix. Broader I/O failures, corrupt provider counts and extreme arithmetic are not newly accepted by this candidate.

Fixture prepared, not run
fixture/run_equivalence.py builds the original C CLI plus narrowly extracted original parsing helpers and a test-only ABI stub, then links the Rust object against the same stub. --wrap replaces open/close/ioctl/pread/pwrite/mmap/munmap and selected allocators; it never delegates device operations to real calls. Public libihk calls are test implementations. Both child argv[0] values are ihkconfig. The188-case matrix compares raw stdout, stderr, exit status and normalized syscall/public-ABI argument traces. It covers commands, malformed/help/unknown arguments, success and error paths, list parsers, counts, allocation failures and formatted-result growth. A separate optional KRM profile uses the same matrix.

Fresh ordinary host fixture grant requested
Suggested bounds: one CPU,1GiB memory,64 tasks,180seconds,64MiB private output; sequential compilers/jobs1; no root, devices, Docker or guest. The driver enforces180seconds total,60/30seconds per compile/link and2seconds per child. The normal/profile-specific paths and all command/output/trace/failure records are retained under private fixture-output/. Existing output is never overwritten. Host compiler paths were checked for existence only; the grant owner must qualify their versions/environment. First command:

/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-7/m15-ihkconfig/fixture/run_equivalence.py --execute --profile default --cc /usr/bin/cc --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc

Do not execute this until a fresh ordinary fixture profile is granted. After the default succeeds, the optional --profile both checks KRM separately, using an approved fresh output successor because the driver retains existing output. Host-stub PASS is not production link or native proof.

CMake proposal
CMake-selection-proposal.cmake replaces only the ihkconfig add_executable selector after review. It defaults to Rust on selected x86_64, requires rustc, and permits C only through an explicit comparison fallback. Existing target libraries/PIC/install settings remain. build_ihkconfig.py is build-time tooling that reads generated IHK config.h to supply BUILDID length after configure; it propagates the KRM cfg and builds a PIC object. It is needed because IHK computes BUILDID after adding its user subdirectory. Both files remain private proposals, and no IHK gitlink or canonical input has changed.

Next acceptance evidence
First obtain the compiler and host-stub results, retaining original failures. Independently review the three defined-behavior contracts and actual public ABI/layout against the deployed library. Then qualify default production object/selector/link closure and matched native functional commands/resource cleanup. Do not credit M15-F06 retirement or alter the practical35 denominator from this source candidate.

CONTRACT.json records exact source paths, command, case coverage, remaining debt and acceptance states. READY-FOR-ROOT.json is published only after all candidate files are complete; a later queue receipt is transport metadata only.
