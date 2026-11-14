Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

PASS: real current selected C/ASM plus updated whole Rust launcher link on HOST.
The actual CMake selection MCEXEC_RUST_HELPERS and IHK_IKC_USE_LINUX_WORK_IRQ /
PROFILE_ENABLE defines are preserved. Real current mcexec.c and archdep.S were
compiled fresh; no retained old C object, mock bridge or replacement C code.
The updated whole actual Rust object is copied byte-exactly from root's accepted
1.818s full Rust compile. Its source postimage is9901615a. Original inputs and
private copies/hashes are in INPUTS.json. No shared edits or runtime launch.

Result: results/result.json; elapsed1.143186647s across8supervised commands:
Ccompile, ASMcompile, archive, final link,3nm inventories, readelf. Every command
COMPLETED/exited0/cleanup_complete=true; no active host child. C/ASM/link stderr
are all0bytes; no failed candidate and no bounded correction. Real C source
mcexec_exit_cmd_servers_bridge/mcexec_exit_process_bridge definitions resolve
the Rust caller; act_execve/act_execve_phase2/transfer_image each uniquely defined
in the final ELF and owned by the actual Rust object. --no-undefined final link
checks link-time symbol closure including resolved host dynamic imports. ELF
version and NEEDED data are retained; static nm is not runtime invocation proof.

Resource execution (one invocation):
/usr/bin/timeout --signal=TERM --kill-after=2s 30s /usr/bin/taskset -c 0 /usr/bin/prlimit --as=1073741824:1073741824 --cpu=20:20 --fsize=33554432:33554432 --core=0:0 --nofile=256:256 -- python3 /home/holden/mckernel-work/host-preparation/p-m06-01-selected-launcher-link-prerequisite-20261022-1/run-host-link.py
Every argv/env/result and closed stdout/stderr capture is in results/*/request.json
and report.json, collected by existing project application-tests/supervisor.py.

HOST LIMITATIONS, explicit: Ubuntu GCC9.4/binutils2.34/libc2.31/libnuma2.0.12,
NOT the pinned production container compiler/sysroot. Host librt.a/libnuma.so/
libpthread and libc startup objects are explicitly selected; actual complete
link input trace is results/link/stdout.bin and map mcexec.map. Read HOST-TOOLS
and *stdout for exact installed package versions. The source config is copied
exactly from accepted retained generated config da78d6a8 (BUILDID3114d9e), not
claimed to match current native module BUILDID or frozen SDK68/cbb04 runtime.
The Linux6.12 generated version header is copied from the previously source-bound
accepted SDK basis3cc5d7cf, without host uname or fabricated version substitution.
Cdepfile mcexec.c.o.d records actual source/system header closure; host libc
headers explicitly differ from production SDK. No production/native acceptance.

Recipe adjustments for this diagnostic only: rebind container /src and generated
include paths to private source tree, preserve exact accepted config/version
bytes; replace /usr/lib64 paths with explicit actual host x86_64-linux-gnu paths;
omit original optional linker --dependency-file flag unsupported by host ld2.34,
and replace its evidence role with real linker -t trace/map. The rpath placeholder
is not needed for explicit system host libraries and is omitted. None of these
change source macro selection. No automatic system/package installation.

Next executable gate: independently released pinned production actual CMake
build, using the same new Rust postimage and authentic generated config/header
closure, ENABLE_RUST_USER_TOOLS=ON, ARCH=x86_64, intended pinnedRUSTC and matching
module BUILDID, then cmake --build <fresh-reviewed-configured-build> --target
mcexec -j2. Require unique same symbols, resolved real bridges and linked ELF
with pinned system dependencies; copy this host executable into no guest.
Separately build/link the matching current ExecClaimGroup/ExecDelivery/ABI20+21
host module sources under existing SDK review. Production link and current
native selfexec199B/emptyerr/37 remain unproven. P-M06-01 needs selected235B
process/exec/wait app after authentic CREATE_PPD/aliasrevocation/finalACK gates.
No mockbody or hostcompiler result substitutes for those actual application gates.
Preserve uncertain child/VM/CPU credits and response claims; no ACK/free invented.
