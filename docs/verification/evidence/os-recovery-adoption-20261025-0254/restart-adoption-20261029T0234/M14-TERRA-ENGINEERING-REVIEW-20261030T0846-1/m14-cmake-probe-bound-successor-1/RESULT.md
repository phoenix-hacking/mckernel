# F06 configure probe: bound make and complete private patch

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation and isolated `cmake -P` tests with fake make and synthetic
ELF only. No full-project configure, real Kbuild, Docker, privilege, guest,
native, controller or cleanup operation ran. Independent review is required.

`complete-original.patch`, SHA256
`01f3d94dab8afb03b51de1723de1501e4e45845e439096538ed3a332f18508b4`,
is a single patch against the original e6a root CMake preimage SHA256
`e60b304fd38bd2dcddd4f7f8c6217bf887bacfc997741e7aed321dd9222899da`.
It includes the complete exact contents of both new verifier scripts. A private
`patch --dry-run -p1` against that original root passed. The resulting root
CMake SHA256 is `439642a3215a05f9ace7a9e3443e1b5acfdcf6565e1342e28e8d254281706729`.
The guarded architecture source and kernel/CMake route are separate, previously
prepared inputs; this root patch does not silently include or select them.

Explicit combined ON mode rejects any generator other than Unix Makefiles,
requires an absolute SHA256-bound make executable and successful `GNU Make`
version output, binds both verifier source hashes, and uses isolated Python
`-I -B` while the adapter compiles the exact hashed sibling verifier source.
The generated Makefile invokes the same absolute make path for nested Kbuild,
not a second `make` resolved from PATH. Its original KBUILD_MAKE_FLAGS must
match an explicit expected list and its expanded form; actual CC/LD binaries,
make, Python, environment, identities and the caller-supplied expected hashes
must still be independently bound and reviewed. The retained e6a cache lists
`CC=/usr/bin/clang;LD=/usr/bin/ld.lld`; that historical value is not a current
toolchain admission. ON requires explicit matching UNAME_R and expected map,
checks actual kernel release/UTS, captures CMake's own make RESULT_VARIABLE,
and rejects failed/missing/incorrect probe output before using the map.

The ON preflight runs before the original temporary-directory removal, but it
cannot establish freshness or exclusive ownership. The external execution
owner must prove a fresh exclusive build root before **entry to CMake**, and
retain exact process identities, timeout/interruption outcomes and kernel
build-tree write isolation. The default OFF route preserves the original nested
Makefile and probe commands; static checks and prior fixtures retain those exact
fragments. No prior native owners or unknowns are cleared.

`python3 -B test_bound_successor.py` passed 11 isolated cases: success, Ninja,
wrong make hash, wrong Kbuild flags, non-GNU make, each verifier mismatch,
make failure with a present output, missing output, wrong map and wrong kernel
release. Negative preflight tests confirmed the pre-entry sentinel remains before
any fake make/version call where applicable. `python3 -B test_bound_flags.py`
passed two extra cases: correctly expanded clang/lld flag pair and rejection of
an inconsistent expansion. It checks the generated nested Makefile uses the
same fake executable path. Per-case commands, exits and output hashes are in
`checks-successor/MANIFEST.json` SHA256
`d08cce2479369a5086ecc89aca22a001769903ee4bdbf41eacbc7256da9d04ba` and
`checks-flags/MANIFEST.json` SHA256
`7577653048a687f7a24347b04cb4ed77e7e7f7e49ab873585365633bcaec1948`.
The first bound patch, its 10-case manifest and original owner patch/tests remain
under `preimage/` and the predecessor directories. No unexpected test failure.

The configure-time adapter calls only the ELF value check. The separate retained
post-generation verifier must still check actual CMakeCache/compile_commands
UNAME_R, KERNEL_DIR and generated MAP_KERNEL_START/KERNEL_RAM_VADDR, alongside
actual compiler origin, complete include/definition closure and the original389
oracle. It is not automatically wired here. Full source/tool/environment identity,
`/out/build`, resource admission, independent execution release, actual configure,
compile/link/native and C retirement remain open.
