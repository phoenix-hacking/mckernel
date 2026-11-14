# M14 nonheld13 plus data32 private CMake integration

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only preparation, 2026-10-30. No canonical writes, Docker, privilege,
heavy build, guest or native work. Not production/default/native acceptance.

The exact preimage is the kernel CMake overlay of source-only SDK profile
`e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3`,
`nonheld-generic-arch-host-preparation-1/src/kernel/CMakeLists.txt`, SHA256
`812d1e5e016b9cde8fa71c211be93efdc5bfb49dd6b3685cded47d595f27dcf5`;
the corresponding data32 HOST source CMake file is byte-identical. The exact
private patch `integration.patch` SHA256
`85fc474fd94beb230d2756c584679573f7c9c3ad1c1fa25657c652e785f1784b`
produces CMake SHA256 `a44e68e1daf685bbe9b8aabc6143f47e469322eefbc1384f51904d5c94d06a06`.
This patch relies on the real Rust and paired C bodies already present in the
e6a effective source mounts; it does not create substitute stubs or import the
later held ptrace wakeup logger. `sources.stdout` records exact profile source
paths and hashes, including Rust policy `11d9d9e1...`, architecture C `b2db4dce...`,
generic C `4af4524b...` and aligned data module `e24e8adf...`. Retained HOST
objects and diagnostic evidence remain at their prior scope; no object is copied
or reclassified as a new SDK object here.

The new combined option is OFF by default. Under the explicit option it supplies
all nine e6a candidate Rust cfgs, six architecture C defines and three generic C
defines, plus the debug-constants dependency; it preserves prior standalone
constructor/forward selectors. It rejects unsupported Rust, architecture,
BUILD_TARGET, IRQ ABI, PERF and UBSAN combinations. It does not select held
ptrace wakeup, held generic or overlapping partial signal cfgs.

CMake preimage appends existing F06 architecture selectors earlier but later
replaces the source's COMPILE_DEFINITIONS with two baseline names. The successor
changes that later operation to APPEND only in explicit combined mode, retaining
the earlier F06 selectors in that mode; default-off keeps original assignment
behavior. Because this restores more pre-existing F06 selectors, independent
review of the complete resulting set and actual CMake/toolchain build is required.
Actual origin producer/config/source identity must be revalidated for any build.

Commands and results, from this directory:

```
python3 check.py > check.stdout 2>check.stderr
python3 verify_sources.py > sources.stdout 2>sources.stderr
patch --dry-run -p1 -d apply-check < integration.patch > patch-check.stdout 2>patch-check.stderr
```

CMake 3.25.1 matrix: default off, combined on, prior standalone options and six
unsupported combinations all pass. These tests execute extracted exact CMake
fragments with simulated previous source properties; they do not configure the
whole project. Static check verifies profile digest, exact CMake preimage, e6a
C/Rust selector pairs and relevant module source identities. Patch dry run passes
against the exact private preimage. The initial matrix also passed; its older
patch and stdout are preserved as `initial.integration.patch` and
`initial.check.stdout` before adding explicit BUILD_TARGET gating. No failures
occurred. No full configure, new typecheck, link, actual SDK artifact, original389
check or native qualification occurred; earlier HOST compile evidence remains
at its exact scope. Source maps, ownership, current identity and all physical
operation releases remain necessary.
