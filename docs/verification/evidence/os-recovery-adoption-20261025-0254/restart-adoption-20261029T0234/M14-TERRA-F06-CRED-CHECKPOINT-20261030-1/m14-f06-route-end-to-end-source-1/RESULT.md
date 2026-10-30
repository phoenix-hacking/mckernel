# M14 F06 origin route source-only end-to-end checks

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No whole-project configure, kernel compilation, Docker, privilege, guest or native
operation. The fixture runs the exact route, producer invocation and generated
CMake include extracted from private routed CMake source SHA256 `f3495884...`
using `cmake -P` 3.25.1 in separate private directories.

`python3 run.py` executed three distinct cases, with per-case exact argv, working
folder, exit, raw stdout/stderr, original and copied source/header/producer/
profile SHA256, wrapper SHA256 and all generated-file hashes retained in each
`COMMAND-RESULT.json` and aggregate `MANIFEST.json` SHA256
`7ed6b8c102c999c4838bfaea7302fbcd61bfdee997152209cd495e19c531a4c1`.

- OFF with retained predecessor C, producer and profile: exit 0; generated and
  included five origin files.
- ON with exact guarded C and guarded producer/profile: exit 0; generated and
  included five origin files.
- ON with retained predecessor C and guarded producer/profile: expected exit 1;
  producer rejected the exact source hash, CMake reported the failure and no
  generated files appeared. Full stderr is retained.

The positive cases generated identical clone metadata SHA256
`71e4b0ab7f5ca612e4cd06bf2150e2e6b7b5e3e39717e466cfb626b1ce249a48` and
origin header SHA256 `aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded`.
Other generated file hashes differ because each case has a distinct physical
source/output directory; the manifest records them separately. `run.py` SHA256
`96aba023c20384b2a6100ede3086f4c9e00b62b8975a4af6a3de627ce5086d48`.
No unexpected case failure occurred and no initial evidence was overwritten.

The test extracts a bounded CMake fragment and uses copies of retained inputs; it
does not prove actual full-project generated compiler argv, compile-time macro
state, transitive include closure, `/out/build` identity, linked providers,
original389 oracle, resource ownership or native behavior. All independent
review, source quiescence and operation-release prerequisites remain open.
