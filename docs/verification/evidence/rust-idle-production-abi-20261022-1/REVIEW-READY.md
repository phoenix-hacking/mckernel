# Actual production-header idle scan ABI prerequisite

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Functional supported-profile OS plus actual live compute-C retirement into Rust
and reviewed assembly. Owner: /root/rust_idle_scan_port. The only writes in this
lane are in this private directory; shared source/Git/image state is unchanged.

First candidate PASS with /usr/bin/gcc 9.4.0 under CPU0 / 1 GiB address space /
20 CPU seconds / 30 wall seconds. commands.json contains all exact invocations;
all stdout/stderr/status files, source, dependency capture, object, symbols,
disassembly and rodata output are retained. result.json is machine-readable.
No failed candidate or bounded correction occurred. No 80-case suite repeated.

The TU includes actual live production process.h, sched_helpers.h and cls.h, with
the exact selected bridge and its three static assertions extracted from the
integrated process.c. Input source hashes and HEAD are in input-manifest.json.
Consumed compiler/header inputs are hashed in consumed-input-sha256.json; every
recorded input was rechecked unchanged after compilation.

Reused the existing accepted new205 generated root referenced by the retained
phase4 new205-real-C-template.json. Its config.h hash matches the retained
sha256 da78d6a8c94b274adad3159b1cc373b00e5de7fea6cc2ae7955a700078db6b2f.
The retained exact production process.c command is preserved in the manifest.
Host-recipe-adaptation.json records precise changes: retained production defines
and include order with /src and /work/output/build mapped to real host roots,
matching host compiler system-header path, and the small extracted probe TU plus
-Werror/dependency output. Build directories and generated inputs were read only.

Real headers satisfy static assertions: thread.status has C int type and width4,
status offset4184, sched_list4328, spin_sleep4356, thread size5568, list.next0,
list size16, LP64 pointers, PS_RUNNING1 and CPU_STATUS_RUNNING2. Object disassembly
contains the actual helper call with running=1, status offset0x1058 and list
offset0x10e8, and the conditional CPU-status=2 store. No FP/SIMD instructions were
observed. This is the same read-only exact-equality bridge previously reviewed;
lock placement and existing accepted CPU/process fixes remain unchanged.

Limits: this qualifies the actual production-header ABI prerequisite under the
retained generated configuration and host compiler. Host GCC9.4 is distinct from
the production container GCC14.3.1; it is not the full process.c translation unit,
whole-crate/image build, final link, native run or Rust-path retirement proof.
No root, Docker, guest, new launcher, ownership/lease cleanup or reserved576MiB
mutation occurred. The accepted cbb04 image remains unchanged. Root owns the next
reviewed production-compiler/image observation and integration acceptance.
