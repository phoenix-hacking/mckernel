# Linux collector loader-closure design — 2026-09-15

Status: **PASS_DESIGN_ONLY**. No build or execution is released.

The accepted collector seals only the main executable and correctly reports
`loader_closure_verified=false`. Its build evidence shows logical
`/lib64/ld-linux-x86-64.so.2` and `libc.so.6`, but retained loader copies/`ldd`
are build references rather than executed mappings. An interpreter or DSO can
change without changing the sealed main image.

A future Linux-only packet needs a parent-owned tracing state machine. Observe the
successful exec stop before interpreter userspace, then retain every syscall
entry/exit through termination. At exec, bind raw maps/auxv, PID/startticks, main
backing, interpreter mappings and monotonic time. Before each file-backed mmap,
retain the tracee descriptor's backing bytes/stat; after success verify mapping
device/inode, offset, protections and extent. Track munmap, mremap and protection
changes. Reject extra exec/fork/clone, unsupported ABI, trace loss and overflow.

Dynamic fixture barriers cover startup, dlopen and dlclose but observations cannot
trust printed markers. Expect main/interpreter/libc, a selected plugin only during
its independently observed loaded interval, and explicitly account for anonymous,
BSS, stack, vDSO/vvar. A separate minimal static assembly fixture must prove no
interpreter/dependencies in ELF and none observed through its traced lifetime.

Retain logical/canonical path, symlink/mount identity, device/inode, size/hash and
bytes separately. Bind loader configuration/search environment. Race negatives
replace/unlink interpreter or DSO before open, after open/before mmap, and after
mapping; old mapped deleted inodes remain attributed by descriptor/mapping facts.
In-place mutation invalidates immutability. Missing/wrong/unexpected/transient
loads, truncated evidence, access denial, lost stop and timeout fail closed.

Allow only new `linux-sealed-v1/loader-closure-v1/` contract/packet/preparation,
trace, dynamic/static/plugin fixtures, build/root/run/oracle sources and one
focused test. Independent tracing/terminal ownership review, exact builds,
capability probes and separate root review are mandatory. Eventual evidence is
limited to observed Linux fixture intervals; no native/McKernel/application or
production credit follows.
