# Current10972 one-pass residual-C symbol inventory

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**PARTIAL SOURCE ATTRIBUTION:** the authorized single processing pass completed
successfully, but unknown/compile-unit-only locations dominate. The report
identifies431 C-attributed unique symbol spans totaling38243 bytes. This is NOT
the complete remaining compute-C amount, a source-level function count, or
runtime coverage. No whole-image Rust percentage is established.

Exact image hash, measured by the existing build_report ONCE:
10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2,
matching the selected accepted image. No map/object/second attribution pass,
source audit, recursive input hash, compilation, root, Docker, guest, runtime,
canonical planning edit or Git operation occurred. Only this new evidence
directory and matching private HOST directory were written.

| Source label returned by the existing method | Unique C symbol spans | C-attributed bytes |
| --- | ---: | ---: |
| syscall.c |236|19452|
| mem.c |89|8617|
| memory.c |48|4295|
| process.c |27|3556|
| cpu.c |31|2323|
| Total identified C spans |431|38243|

Labels are retained exactly as returned; basenames alone do not establish the
full original translation-unit path. The C-only inventory retains every unique
(integer address,size), names/aliases and source label, ranked by source bytes
then function-span size. There are431 raw C symbol names in these431 spans.
This does not silently treat all4246 symbols as C functions.

Of3867 unique nonzero T/t spans:

- 3247 spans/652139 bytes return unknown source `??`.
- 189 spans/127599 bytes return only
`mckernel_rust.8afe63fe1da445c1-cgu.0`; the existing suffix classifier correctly
leaves that label `other`, rather than assigning it to Rust without .rs metadata.
- No .rs, .S/.s/.asm or header-origin paths are identified in this pass. This is
an attribution limit, NOT evidence that the image has zero Rust/assembly/header
code. There are197 duplicated alias spans among the raw4246 symbols; span
deduplication leaves3867 unique spans. No conflicting alias attribution occurred.

Raw module language_bytes are C38243, Rust0, assembly0, other779738. Its existing
rust_percent field consequently reflects a zero numerator over a C+Rust-only
38243-byte scored denominator. That value is UNINFORMATIVE about whole-image
language ownership; do not publish it as 0% Rust or as whole-kernel conversion.
All817981 unique sized text-symbol bytes are not all executable ELF bytes, and
no instruction-level ownership or mixed-language inline resolution is implied.

Both host tools returned zero with empty stderr. Their inability to provide
complete source labels is observed; its precise cause is not diagnosed here.
No automatic version/profile change, alternate addr2line, repeated ELF hashing,
second pass or broadened workload followed. The additive interpretation remains
PARTIAL even though the wrapper's mechanical pass status is PASS. A future
separately authorized metadata-method decision must resolve source attribution
before any complete remaining-C or full language split is claimed.

## Executed command and single-pass binding

```text
/usr/bin/taskset -c 6 /usr/bin/prlimit --as=1073741824 --cpu=60 --fsize=33554432 --nofile=256 --core=0 -- /usr/bin/timeout --signal=TERM --kill-after=5s 120s /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/compute-c-inventory-20261023-1/inventory_once.py
```

One ordinary CPU6 lane,1GiB AS,60CPU,120wall plus5s TERM grace,32MiB per-file,
nofile256/core0; no limits or profile were changed. Actual outer command exit0,
direct unified-exec session70127 completed; wrapper elapsed6.187763985013589s.
Raw ordinary stdout/stderr and every child argv/stdout/stderr/status/timing are
retained. Stderr is empty. Exactly ONE build_report and ONE attribute_symbols
invocation occurred. The wrapper retains and ranks that SAME returned list;
it never invokes a second nm/addr2line processing pass. It intentionally skips
the existing optional Git-HEAD lookup (commit=NULL, explicit note) under this
lane's no-Git instruction; producer derivative identities are retained separately.

SOURCE-TOOL-BINDINGS.json records actual source/tool identities:

| Input | Actual SHA256 / version |
| --- | --- |
| inventory_once.py |534aa9dd0470dd9232cc41bb289cf9fa7cf323018f195091ee56dd9b7efab606|
| scripts/mckernel_text_ownership.py |a6418f32b83d27af2321d67afbb72dfce1a72bf83cd488a93df1d42815291c1c|
| /usr/bin/nm → x86_64-linux-gnu-nm |5fb0dd8acc18e3f348ed0acbcada0580dbdddd1eb5de3c8323613af13580032b; GNU Ubuntu2.34|
| /usr/bin/addr2line → x86_64-linux-gnu-addr2line |6a987dbf2b8223f6cce43bb4f3a8c803053dcfe451f2f0740fd272bfcc3b6b3f; GNU Ubuntu2.34|

The selected source root is
/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/source-materialization-1/materialized-source.
Preserved producer source manifest28a6c1dededda19d2da07279f9a59d542996ae77bd96d176567cc86f0c5a8459,
derivative5cffcc1b23dc5ca377baa055aab0417b0daac7ddcac0e2281903260f0ebd79e3,
materializationd7e24b4c0d3174b3479e33796d712d439444bae82902482448890b9d8142d43d.
Base Git942c927b1ec93cc31284ff498455909d9bb2d0fc is historical producer context,
not a replacement for the derivative/materialization. Existing accounting input
authority is seven-check-closure-20261022-1/CURRENT-COMPUTE-C-ACCOUNTING-20261023-1.md.

Raw results in the matching HOST directory include symbol-language.json,
SAME-PASS-ATTRIBUTED-SYMBOLS.json, C-ONLY-SOURCE-RANKED-INVENTORY.json and RESULT.json.
They are retained in the new bounded evidence archive alongside this interpretation.
No coverage, acceptance, retirement count, milestone or whole-image percentage
is changed by this measurement. Preserve all original inputs and results.
