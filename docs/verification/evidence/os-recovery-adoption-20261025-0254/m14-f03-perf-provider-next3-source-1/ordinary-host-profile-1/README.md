# F03 perf3 ordinary profile

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/profile preparation only. No compiler, test, guard, admission, resource
observation, harness, Docker, native or canonical action was performed.

This packet reuses source READY4cecde9b and exact original seven-command recipe
aac12d50. The two new wrappers, existing atomic bridge, original C fallback bodies,
Rust fixture and driver remain unchanged. Expected results remain exactly872 C/Rust
pairs,1744 single-call traces,ABI16 and three selected callbacks.

The four C witnesses now include exact declaration slices from original production
perfctr.h and x86 atomic.h. The original conditional uint64_t/u32 init signature is
retained; default supported x86 uses unsigned int. The public callback continues to
accept unsigned long and Rust explicitly narrows to u32, matching original C.
The same original typed selector assertions and atomic size8/align8/offset0
assertions compile against those actual header declarations. This narrow real
header witness does not claim whole-header preprocessing or PMU execution.
Three fallback witnesses use neither selector macro, policy only and callback only.

Seven commands use the unchanged6e98 ordinary CPU6 runner. Exact original compiler
arguments are retained with fresh private outputs, the real-header witness path,
and `/usr/bin/env TMPDIR=<fresh leaf output>` preceding the first six commands.
The pinned env tool puts compiler/linker temporary files in the reserved HOST
output location. The runner creates this leaf before its first command. All argv
executables/cwd/output paths are absolute; output and capture roots are distinct
and initially absent. Original sources and old output names are never modified.

Full output reservation is8GiB. Its5760MiB enumerated planning components cover
six64MiB final artifact slots,32 Rust temporary slots,12 GCC compile temporary
slots,8 linker/driver temporary slots,all14 outer64MiB streams,64MiB control and
qualification records,64MiB filesystem metadata and1GiB emergency margin. Rounding
to8GiB adds2432MiB. This deliberately reserves whole streams despite the capture
helper rejecting streams above32MiB and original leaf proposals of16KiB. Per-file
FSIZE is not an aggregate cap. These are conservative planning slots for fixed
pinned ordinary tools/sources, not a universal compiler output-count guarantee or
new quota. Existing admission requires HOST16GiB plus this entire8GiB reservation;
scratch12GiB, memory,one-heavy,aggregate7jobs/21.6619GiB and fixed clocks remain.
Root's actual current observations and fresh grant remain mandatory and unset.

`REUSED-TOOL-HEADER-HELPER-CLOSURE.json` binds the existing Rust1.92/GCC9/80system
header/helper closure and statically extends ELF dependencies only for env,nm and
readelf. No compiler, preprocessor,ldd or tool execution was used to derive it.

`check_profile_source.py` is provided **unrun**, as requested. It uses only retained
runner source/profile APIs and pure binding/arithmetic checks. It never calls
runner main, account guard, admission, limits or resources. The preparation script
ran only to materialize source/JSON and validate exact inputs; its result is
retained. A first missing auxiliary preimage path failed before fixture/profile
output. That failure and script remain preserved; one bounded correction reads
original EXACT-PREIMAGES pins and copies the five exact unchanged auxiliary
reference files privately. No callback, expected result or algorithm was altered.

`qualify_retained.py` is provided **unrun** for Root after seven successful commands.
It binds the actual consumed grant/profile, exact argv, all7 return0/positivejoin/
group-absence/closedstream records, empty diagnostics and the unchanged stdout.
Read-only nm/readelf checks require three unique Rust boundary definitions, three
selected C undefined references and64-bit pointer relocations, exact existing
atomic export reuse,readonly128B ABI16,only three inert endpoint references from
Rust and original three local C functions in all three fallback objects. It never
compiles or reruns the harness. Fresh qualifier output preserves the actual batch.

Root command templates contain literal profile digest and original runner path;
actual grant/digest remain null. No old grant/nonce or prior HOST result is reused.
Matching production default object/link and applicable native coverage remain
separate and OPEN. No new per-helper native gate or retirement claim is introduced.
