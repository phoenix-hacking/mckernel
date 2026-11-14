M15-F07 private ihkosctl Rust successor — ready for first compiler/fixture grant
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Implementation
223-line no_std Linux x86_64 Rust CLI replaces the874-line original program's complete action dispatcher: load/boot/shutdown, alloc/legacy reserves, assign/release, IKC get/set, queries, kargs/kmsg/clear, interrupts/raw ioctl, and configured dump options/time/default filename. Current original C is retained exactly. Existing ihkconfig C-main/ABI/diagnostic patterns and the owned-process helper are reused. No library parser/sysfs API is duplicated;13 current libihk exports remain the shared-library owner's responsibility.

Provider handoff
ABI-CONSUMERS.json gives the exact3 public and10 private declarations and request types for background case227_stage. Formatters must return allocations compatible with libc free; parsers receive caller-owned arrays and publish counts. The CLI uses actual current headers, keeps capacity/layout/return contracts, and proposes no private API changes. Current C libihk can supply the ABI temporarily; that remains M15 library debt and does not establish full Rust runtime closure. Actual Rust exported-provider/link closure is unknown until the owner/root verifies it.

Behavior
Preserve original usage/action/index/open precedence, diagnostic text (including typos), default load pathname, resource formats, weird intr/unknown-action return0 behavior, shell modulo256 exit statuses, and GNU getopt_long dump permutation/time behavior. ENABLE_MEMDUMP and BUILDID capacity follow generated IHK config.h through build_ihkosctl.py. Existing link/PIC/install settings remain under the selector proposal.

Explicit corrections, not hidden parity
Original get ikc_map can free indeterminate pointers after early failures and leaks its fd. Rust initializes requests and closes the owned descriptor; raw comparison traces retain the one added close, normalized only for the labeled observable-parity check. reserve_cpu now handles failed allocation and frees its request. buildid/sysfs string buffers terminate within bounds. kmsg keeps the API capacity but adds a sentinel byte, avoiding the original ret==capacity overwrite. Five undefined C paths are Rust-only proposed-correctness tests; the C oracle is never executed on them. Root must review these resource/defined-behavior changes separately from output/exit/ioctl parity.

Concrete executable fixture, not run
The186-case comparison matrix covers every action, argument errors, help/unknown behavior, resource/IKC syntax, all status labels, query counts, dump options/clock errors, ioctl/library failures and relevant allocation failures. Original private C parser/formatter bodies are retained verbatim as a shared test oracle; synthetic public/sysfs providers and --wrap device calls prevent real device/dump work. Comparing both CLIs against shared C helpers does not prove Rust library-provider parity. Five additional Rust-only cases cover the corrections above. Default is ENABLE_MEMDUMP=ON; optional no-memdump/both profiles need a separately granted retained successor.

First exact command, only after a fresh ordinary root grant:

/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/m15-ihkosctl/fixture/run_equivalence.py --execute --profile default --cc /usr/bin/cc --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc

Proposed profile:1 freshly assigned ordinary CPU,1GiB memory,64 tasks,160seconds wall (150seconds work plus bounded cleanup),64MiB private output,jobs1; no root/Docker/guest. No CPU slot is reserved. The existing owned-process helper admits unprivileged child-subreaper mode, captures each process, joins all owned descendants, retains failures and refuses existing fixture-output. No automatic retry.

Only AST/JSON/source-data checks have run. No driver mode, compiler, subprocess fixture, device, Docker, root, guest or native workload executed. Original C plus five header snapshots/pins are in REFERENCE-PINS.json. Source/library/selector/production link/native proof remain open. Root owns integration and publication; earlier ihkconfig/mcps/vmcore packages and original35/M14 remain unchanged. CMake proposal is private and must be coordinated centrally with the shared libihk/ihkconfig selector work.
