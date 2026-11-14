# Independent perf ABI witness provenance review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only review; no generator, regression, comparator, compiler, guest or
native operation was executed for this review. No ABI, link, functional or M14
acceptance or physical execution release is conferred.

## Exact reviewed inputs

* `perf-abi-provenance-expert-1/prepare.py`: SHA-256
  `ee56647fdf644437da331cdfad810de37b36ec919db63459819400b8251c1798`.
* `perf-abi-provenance-expert-1/test_reproducibility.py`: SHA-256
  `fb03f93364c59af68e0c38482686456627c54bc858555e17caa5743efc7f3a5b`.
* `perf-abi-provenance-expert-1/compare_elf.py`: SHA-256
  `baa35735e39207dfc3772b88c82fc5b380695599003a01d709ef2bbe96d08d1a`.
* Corrected template `perf-abi-witness-coherent-correction-1/TARGET-CONTRACT.json`:
  SHA-256 `248c016333908972adb21538e5d2daf4a6b8705783da3d4a2fce7f29ae8c4dc1`.
* Corrected witness `f03_perf_entry_abi_witness.rs`: SHA-256
  `632d3ce6039f26c4995034798e30465f54ba36c1d5af0da2299bf98ff2021e0c`;
  witness-only patch SHA-256
  `cb71f19e839df9f039b0e816c8e34220055413586576fa81f0557f1fb02f7c1a`.
* Non-held selected source patch SHA-256
  `595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a`;
  C selector patch SHA-256
  `7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345`;
  C real-header witness SHA-256
  `212fbf03425ea1e883f01cd4132b3821cca224a015890cabeaf3fda95e80d8c0`.

## Findings and limits

The expert generator captures and hashes the corrected contract and bound
inputs, checks its 31 Rust scalar records and 13 callback slot/type/target
records against the selected entry, regenerates the witness and patch, and
requires their corrected hashes. Its successor deliberately derives a **new**
contract from the exact template, rebinding output paths and recording the
captured generator and comparator provenance. It does not claim byte-for-byte
reproduction of the template contract. C-expression and cross-language type
semantics are inherited from the pinned template and require independent actual
C/Rust verification, not just these Rust-record checks.

Inputs are captured from one descriptor with before/after identity, length and
metadata checks and hash verification; input hardlink aliases are rejected.
During `generate`, however, the generator captures its then-current on-disk
`__file__`; this alone does not prove that Python loaded those exact bytes.
Likewise the recorded comparator path does not prove that a later invocation
reads its captured bytes. An authorized invocation must bind the executed
program and later comparator to the captured hashes independently.

Input validation occurs before exclusive creation of a new output directory;
outputs use exclusive file creation. Failures return nonzero through unhandled
exceptions; later filesystem failure can leave a partial new directory, without
a success receipt, which must be retained and not reused. The generator does
not itself claim rollback or successful generation after an error.

The proposed regression source covers two generations, normalized successor
contract reproducibility, corrected witness and patch byte identity, pinned
input/hash drift, existing-output preservation and Rust field/callback drift.
It has not been executed. It does not cover post-reservation I/O failure,
hardlink alias, or a changed imported program file; those properties remain
unverified by that test source. Future execution needs an independently
reviewed profile and coordinator resource share.

The comparator remains the previously reviewed bounded 31-word comparison and
raw 13-slot relocation inventory. It does not establish callback target or type
equivalence, exact resolved link/provider uniqueness, generated-header
provenance, event ownership, functional/native behavior or acceptance. The C
and Rust witness objects must remain separate and excluded from production
links. Actual paired emitted flags and bound objects, scalar values, callback
ABIs and relocation targets, final link, functional behavior and native evidence
remain required under their applicable review and operation controls.
