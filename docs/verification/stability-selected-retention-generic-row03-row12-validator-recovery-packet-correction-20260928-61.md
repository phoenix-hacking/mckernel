# M01-B validator recovery packet 61 — bounded correction

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the single additive
correction after the validator-recovery failure of packet 60. It preserves
packet 60, packet 52 and every original root, attempt and failure. It grants
no compilation, Phase II, runtime, or acceptance credit. At most one fresh
source-only attempt may be considered, and only after an independent
`PASS_PACKET` review of this exact file.

## Immutable inputs and failure identity

Reauthenticate the directly consumed packet52 authorities and all inherited
pins before creating anything: packet52 and its review/correction records,
packets 53/54/55/57, reviews 56/58, and source review 59. The exact source
review input is
`docs/verification/stability-selected-retention-generic-row03-row12-phase-i-source-review-20260928-59.json`,
SHA256 `5b1113f6c58c1d19a343e61fd0e9ee87471d0c7761a5d76b57dacffcd1a3ef89`.
The retained root56 failure JSON is
`docs/verification/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.json`,
SHA256 `c678dfa6af9682cc97c584e1f6c6522fbc773b093b463892571cb53a5830bad4`.
The raw six-field `phase-i-failure.txt` member inside that failure is pinned
separately at SHA256
`1fc20dcfec9b3413c40352ef68c531761c66ac371eb99dbec3bd7117dcf29afb`.
These are different objects and must be recorded under separate labels; never
use the raw member hash as the JSON-record hash. The retained archive is
`docs/verification/evidence/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.tar.gz`,
SHA256 `8eabf2eb29512ce628da616ffe587bfa5d75775be2e783e55418f67e91d3a59a`.
Preserve all three byte-for-byte and preserve the original failure.

The failure was validator recovery only: root56 did not receive a handoff
because an absolute scratch path was passed to repository `git diff --check`.
This correction may replace that one check with a byte-only validator, but may
not reinterpret the failure as a source or build failure.

## Fresh root and authenticated installation

The only allowed future root is the fresh absent directory
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58`.
Immediately before creation, verify absence, canonical spelling, ownership,
mode 0700, and disjointness from every retained root. Do not reuse or repair
root56. Authenticate the root56 archive member paths and bytes against the
archive SHA and the ten pinned candidate hashes from packet60. The archive is
the authority: select each member by its exact archive pathname, verify its
member hash, and install it into root58 as a newly created regular file using
an authenticated byte stream. Do not install from an unbound working-tree
path.

Create exactly two isolated mode roots, `root58/mode2` and `root58/mode3`,
with fresh regular single-link files. Each mode receives precisely its five
packet52 files; no hard links, symlinks, reflinks, sibling reads, cross-mode
copies, shared candidate bytes, or shared staging paths are allowed. The
archive-to-file mapping and post-install SHA256 for every member must be
recorded before validation. The standard-library allowance from packet52 is
unchanged: the validator may use the pinned system Python standard library,
but may not import candidate code or execute generated/source code.

Use packet52's two reviewed stager commands, changing only the output roots
to `...-58/mode2` and `...-58/mode3`; retain packet52's exact wake bytes,
observer begin/end parsing, mailbox/phase matrices, ownership,
destruction-before-deallocation, `cfg(not(test))` erasure, inverse
reconstruction, canonical membership, and single-link assertions. The
five-file edit boundary remains strict. No compile, link, test binary,
guest/native execution, Phase II file, or runtime action is permitted.

## Correct byte-only whitespace validation

Run one `python3 -B -c` invocation with literal absolute argv paths in stable
order. Parse `sys.argv[1:]` directly; do not open, treat, or strip a literal
`--`, and do not use a shell glob, shell expansion, import of candidate code,
repository substitution, or generated code. The validator must check bytes:

```text
python3 -B -c 'import sys
for name in sys.argv[1:]:
    b = open(name, "rb").read()
    if b"\r" in b: raise SystemExit(f"CR:{name}")
    lines = b.splitlines(keepends=True)
    if any(line.endswith((b" ", b"\t")) for line in lines):
        raise SystemExit(f"TRAILING:{name}")
    if not b.endswith(b"\n"): raise SystemExit(f"FINAL_LF:{name}")
    if b.endswith(b"\n\n"): raise SystemExit(f"EXTRA_EOF_BLANK:{name}")
print("PASS_WHITESPACE")' \
  /absolute/root58/mode2/adapter.rs ... /absolute/root58/mode3/source/stability_phase.rs
```

The actual invocation must contain all ten literal paths and no `--` token.
Require status zero and exactly `PASS_WHITESPACE`. Run four disposable
negative controls, each in a separate fresh regular file, proving nonzero
diagnostics for CR, a trailing space, a trailing tab, missing final LF, and
an extra EOF blank line. A control's expected failure is diagnostic only; any
failure or ambiguity in the ten candidate files ends the attempt immediately.
Do not conflate controls with candidate validation.

## Counts, handoff, and failure semantics

Before handoff, assert exactly **326 regular files** in the complete root58
tree; after adding this packet's canonical handoff record, assert exactly
**327 regular files**. Also require 51 source members per mode, no symlinks,
no bytecode, no extra paths, and no Phase-II files. A count mismatch is an
attempt-ending failure, not a diagnostic control. The handoff may be created
only after all packet52 authentication, archive-member binding, byte hashes,
mode isolation, validator, negative controls, reconstruction, invariant,
cfg-erasure, canonical-membership, regular-file, and single-link checks pass.
Then stop for independent handoff review; the handoff itself cannot grant
acceptance.

On the first real failure, write only packet52's six-field
`phase-i-failure.txt`, retain exact command/status/paths and stop. Preserve
the fresh root and archive; never repair in place. Record diagnostic-control
results separately from attempt-ending failures. The absent-root check,
archive authentication, and all candidate bytes must remain independently
reproducible. Report this packet's SHA256 and `git diff --check --` result
for this packet only; do not edit existing evidence or any other file.
