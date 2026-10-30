# Private e6a F06 origin producer successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only. No full configure, compiler, container, native or guest execution.

The e6a base source lacks `scripts/derive_f06_origin.py` and
`scripts/f06_origin_command_profile.json`. This pair is needed by its CMake
source candidate. `predecessor/` preserves the retained CURRENT113 source
producer/profile bytes. `prepare.py` makes a private successor using exact e6a
profile `e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3`,
its exact architecture C compiler argv, and selected C source SHA256
`b2db4dce35ce2da311b71de284bcbf7aa739536cf1f81742aae9fd41c41b5ef9`.
The predecessor producer required `-c` as penultimate argument, whereas the e6a
command has six candidate defines between `-c` and final source. The successor
requires that exact six-define sequence and retains the original guards against
prefix-map, response-file, source-path and input-byte changes. The profile pins
the existing `/src/arch/x86_64/kernel/syscall.c` literal and the original header
SHA256 `7315ef758c56c4888242295ed9340b44f649d772b1315502acc49eb6105048dc`.
Inherited older evidence remains historical; the modified profile is new and
has no execution authority.

Candidate hashes:
- `scripts/derive_f06_origin.py`: `de056b87497da46e8210582e3bcc5859d5fc43725997da4522f7986ce99c8ae8`.
- `scripts/f06_origin_command_profile.json`: `2302057a7ab99f58060987dbca6f8e0033a11e6114a8fe49b77e07cf546f8144`.
- `test_origin.py`: `1e7141a6a41c2db51297f1b86faa37853ea5f893d48c3c2ccb0c23ed2f2b1050`.

Actual commands:

```
python3 prepare.py
python3 scripts/derive_f06_origin.py --profile scripts/f06_origin_command_profile.json --source src/arch/x86_64/kernel/syscall.c --output output
python3 test_origin.py
```

The source-only producer created the expected logical origin and clone CPUID
metadata lines 898/908. Generated Rust metadata SHA256
`71e4b0ab7f5ca612e4cd06bf2150e2e6b7b5e3e39717e466cfb626b1ce249a48`,
and generated origin header SHA256
`aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded`,
match the retained e6a generated inputs. Seven unit tests pass: accepted input,
changed profile/source/header, changed six-flag ordering, prefix map and changed
source origin. Outputs are retained in this directory. No producer/test failure.

This binds the existing e6a *manual* argv, not a future generated CMake compile
command. The producer runs during configure and cannot itself prove the command
that CMake later emits. Future use requires independent source/profile review,
actual generated command comparison before compilation, binding `/out/build`,
source identity/ABI and a fresh reviewed operation release. Full project
configure and native/provider behavior remain untested; no acceptance follows.
