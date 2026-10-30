# F06 configure input/dependency matrix

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/evidence analysis and seven bounded small file reads. No kernel
root was copied or modified; no large unchanged tree was rehashed; no configure,
Kbuild, Docker, native, guest, privilege, controller or cleanup action occurred.

The retained affinity image request identifies `/out` as the historical host
root `/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output`.
Its inventory records 140,053 entries. Its `build/Makefile` includes the sibling
`/out/source/linux-6.12.0-211.44.1.el10_2/Makefile`, so binding only `/out/build`
is insufficient. The actual candidate mount, source/build identity, safe write
isolation and exclusive owner remain unknown; the retained tree is not authorized
for direct mutation. The 35.9-MB historical request was read for targeted entries
but not rehashed; its recorded historical digest `902f4822...` comes from the
retained actual-preparation binding, not a new current-byte assertion.

Seven stable individual reads totaling 1,165,927 bytes match their corresponding
historical inventory hashes: kernel.release, UTS header, .config, generated
build Makefile, generated autoconf.h, Linux source Makefile and pinned nightly
rustc. `SIX-FILE-OBSERVATIONS.json` SHA256
`f9a8681326a99a3ced1111ea5a217f41e761ed8af9d5fb2721769036b1395c20` and
`LINUX-SOURCE-MAKEFILE.OBSERVED.json` SHA256
`a0b3e39beaca89a232d3e83bb32b825df0fe8a4465691d3c79838a62d5ad47ca`
record the exact file paths, hashes and before/open/after identities. The release
and UTS strings both read `6.12.0-211.44.1.el10_2.mckernel1.x86_64`. These reads
do not establish the full 140,053-entry tree, freshness of every dependency,
quiescence, physical ownership, or an operation release.

The SDK's retained tool manifest `image-toolchain.json`, SHA256 `a68e02b3...`,
records expected image binaries: GNU Make `97539f22...`, GCC14 `2092e32f...`,
clang `48271e3f...`, GNU ld `825f11b6...`, lld `52029c7d...` and CMake
`a2ec9c59...`. Their full hashes and paths appear in `DEPENDENCY-MATRIX.json`.
They can bind historical target expectations, not current actual tools. This
manifest has no Python interpreter record; the host GCC14 tool was not found in
PATH during the prior analysis. The exact 6.12 Kbuild flags and transitive tool
closure remain unreviewed. The old CMake cache's `UNAME_R=5.15.0-139-generic`
differs from the observed 6.12 release; actual regenerated commands, codegen,
source origin and original389 must be checked rather than assuming equivalence.

The fixed 157-Rust-file retained observation is source-byte evidence at its
recorded time; it explicitly excludes enumeration, lease, quiescence and
independent review. `RUST-ROOT-STAT.OBSERVED.json` SHA256 `f13ad289...` records
that the root directory metadata currently matches that receipt; it proves no
current child bytes or membership.

`DEPENDENCY-MATRIX.json` SHA256
`db5a639b90e982a539ff13204665b4f1c135e27e3aa3fba79dbfe80b93afe19a` separates
these historical expectations, bounded observations and unresolved facts.
`PROFILE-OUT-ROOT.NOT-RELEASED.json` SHA256
`753885e0b86d55d66961c1eebd79b651b1996ff5ac25259fcd1d2d332dc0abec` is a
source-only profile correction: it records a required coherent `/out` parent
with both build and Linux source siblings instead of an incomplete `/out/build`
mount. Actual `/out` and `/work` mappings and every actual identity/release
field stay null. No mount, copy, mutation or workflow was created.

Next: independent review of a no-Docker, unprivileged isolation/owner strategy
that binds current full input identities and membership, the exact `/out` source
and build relationship, immutable/tool/output paths, Kbuild write scope,
process/timeout ownership and safe fresh ancestors. Historical values may be
used as expected targets only after actual matching observations. Separate
post-generation flags/include checks, original389, build and native gates remain
open; no runtime/default or C-retirement result is claimed.
