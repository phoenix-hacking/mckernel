# CURRENT119 exact artifact retention

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

`CURRENT119-EXACT-NEW-ARTIFACTS-AND-BUILD-RECORDS.tar.gz` retains the four actual
compiled outputs (Rust object, two C objects, image759fe1cb), linker map/link.d,
worker/producer results, eight command streams, plan, actualprofile and bounded
build/Rootjoin records. It contains28 verified regular members totaling30,614,447B.
Compressed size6,895,580B; SHA256
`f649def476c467d55e601415bc99d6b35e4234179d331084531a2c26a8c8d596`.

`MEMBERS-AND-REPRODUCTION-REFERENCES.json` lists exact member byte hashes and
existing source/cohort/config/toolchain/SDK21/profile/origin references. The eight
retained qualified original object references are preserved there; their empty
bind placeholders are excluded. The manifest itself is also inside the archive.

`ARCHIVE-READBACK.ACTUAL.json` records a complete decompressed member/hash readback
and a second exact comparison of every selected original after archival. All
originalHOST files, outputs, source, SDKs and failures remain in place unchanged.
Archive work usedCPU0/jobs1/AS2GiB and took1.220s; no compiler, Docker, native,
cleanup, chmod or cache mutation occurred. This adds no acceptance credit.

To inspect or restore later, verify the archive hash, list it with `tar -tzf`,
then extract only into a fresh ordinary directory. Original absolute paths and
restoration member mapping are in the manifest; never overwrite a current tuple
or substitute retained placeholder files for the eight qualified objects.
