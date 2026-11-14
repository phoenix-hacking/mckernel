M15-F08 private ihkmond Rust daemon — source ready, not executed
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Full body
The Rust candidate implements the daemon CLI/defaults, daemonization, libudev mcos add/remove loop, hungup polling worker, kmsg notification/lease worker, file-ring/syslog path, repeated add/remove, and partial-setup/error cleanup. It uses Rust threads/Arc/Mutex/Condvar and baseline Linux/libudev FFI; no custom runtime C callback or shell body remains. Only two shared-library APIs are consumed: ihklib_device_open(int) and ihk_os_get_eventfd(int,int), both returning owned fds. ABI-CONSUMERS.json records exact request layouts and ownership for case227_stage/root. Actual Rust provider link closure is not yet verified.

Reference bugs are not silently mirrored
The C daemon detaches workers that reference stack state, does not stop/join them, leaks received udev devices, double-closes the monitor-owned fd, and can leave a kmsg lease after partial failure. Rust uses joined cooperative stop and scoped owners. Worker/epoll failure now reaches the supervisor. Failed lease release is attempted once, logged with its dev/OS/handle identity and marked unrestored; it is not retried or called cleanup PASS. SIGINT/SIGTERM request controlled shutdown; SIGKILL still needs external ownership/recovery.

The selected profile remains one OS (OS0/dev0). Rust validates mcos0 instead of the reference node+4 misparse/unchecked index. Normal kmsg bytes, slot naming, facility/LOG_INFO and line pacing are retained. Oversized reads and consumed-slot holes use explicit chronological/full-read corrections instead of the reference data loss. These changes are separately labeled in CONTRACT.json. The optional redirect body is Rust too, but its actual native branch remains unqualified.

Concrete first fixture
The22 daemon scenarios include8 defined original-C startup/CLI comparisons, full Rust add/status/remove/stop, two generations, active stop, each worker disabled, configured facility, partial main setup, kmsg endpoint/epoll/read failures and unreleasable handle observation. A separate entry invokes actual retained C kmsg file/syslog helpers and compares the Rust helper's normal bytes. A Rust-only oversized-read case tests preservation. Unsafe original detached cleanup is not used as an acceptance oracle.

The synthetic backend is thread-safe and runs real Rust threads against fake device/udev/epoll endpoints plus private actual ring files. It checks closed fds, reference/handle counts, duplicate closes, exact log bytes and final task count1. The C reference's resource defects remain visible as observations. A forced release failure deliberately reports an outstanding handle and no restoration claim. There is no real daemon fork, libudev/netlink, custom-device, kernel, syslog service or native acceptance from these mocks.

Exact first command, only after a fresh root ordinary grant:

/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/m15-ihkmond/fixture/run_fixture.py --execute --cc /usr/bin/cc --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc

Proposed profile:1 fresh controller-assigned ordinary CPU,1GiB memory,64 tasks,190seconds wall (180seconds work plus bounded cleanup),64MiB private output,jobs1. No CPU reserved; no root/Docker/guest/PTY. The already prepared owned-process helper admits unprivileged child-subreaper/self-child joins, captures every job and retains original failures. Existing fixture-output is never overwritten; no automatic retries.

Only source/AST/JSON/data checks ran. No compiler, driver mode, subprocess, daemon, thread fixture, device or native operation executed. Root must use actual compiler feedback, then match production provider/build/link and real daemon/OS/logging lifecycle proof. Full64-slot wrap/long-line combinations and optional profiles remain unqualified. Default selection/install proposal preserves the ihkmond target and sbin basename, depends on matched libihk plus platform libudev, and excludes every test helper/mock. Root coordinates the shared CMake integration. Earlier ihkconfig/mcps/vmcore/ihkosctl packages remain frozen; original35/M14 counts are unchanged.
