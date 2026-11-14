# M01-B validator recovery packet 60

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is an additive, source-only
recovery packet for the validator-only failure of root56. It preserves every
prior packet, root, failure and archive; it does not redesign packet52,
release compilation, execute a candidate, or release Phase II. One future
attempt is released only after an independent `PASS_PACKET` review.

## Exact retained inputs and candidate bytes

Bind packet52/54/55/57 and reviews 53/56/58, especially source review59
(`docs/verification/stability-selected-retention-generic-row03-row12-phase-i-source-review-20260928-59.json`), whose SHA256 must be
reauthenticated before work. The root56 failure record is
`docs/verification/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.json`, SHA256
`1fc20dcfec9b3413c40352ef68c531761c66ac371eb99dbec3bd7117dcf29afb`.
Its retained archive is
`docs/verification/evidence/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.tar.gz`, SHA256
`8eabf2eb29512ce628da616ffe587bfa5d75775be2e783e55418f67e91d3a59a`.
Preserve both byte-for-byte and retain the first failure. Root56 has no
handoff; the failure was only an invalid repository-mode `git diff --check`
invocation against an absolute scratch path.

The ten accepted candidate files are exactly these root56 paths (hashes are
SHA256 of retained bytes):

| mode | path | SHA256 |
|---|---|---|
| mode2 | `adapter.rs` | `a0e20bc5b3ac65897462222d5f03f39c569c89c8d0edbb59d959cebd7e82fe0c` |
| mode2 | `runner.rs` | `af9af80ad0bd31365e97989c31f8157bf72dbfeecad03f12b824bf2f2b5b94c8` |
| mode2 | `source/application_syscall.rs` | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` |
| mode2 | `source/smp_application_syscall.rs` | `a42b429e0af98d3e479c24239ee0d759c840b1d5920131da6b263ab944d7d2b4` |
| mode2 | `source/stability_phase.rs` | `fa05e2770fb1248b7f9d3e25fd3c0c3e1427f75fabb22edf696bf2f02ca1ee38` |
| mode3 | `adapter.rs` | `a0e20bc5b3ac65897462222d5f03f39c569c89c8d0edbb59d959cebd7e82fe0c` |
| mode3 | `runner.rs` | `af9af80ad0bd31365e97989c31f8157bf72dbfeecad03f12b824bf2f2b5b94c8` |
| mode3 | `source/application_syscall.rs` | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` |
| mode3 | `source/smp_application_syscall.rs` | `120629db1692fcef6b2a7c985f785ced99ba93aa3ab197b40a784516e6100d81` |
| mode3 | `source/stability_phase.rs` | `8a0923931b26ad0b0cd107b197259af25ecc068b215288d6b98a66e6de4fbad0` |

The fresh canonical absent root is exactly
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58`.
Recheck absence, canonical spelling and disjointness immediately before
creation. Reauthenticate all packet52 authorities, policy hashes, templates,
manifests, helper/records, source maps, inherited pins, archive members and
stager inverse reconstruction. Use precisely packet52's two reviewed stager
commands with only the output root changed to `...-58/mode2` and `...-58/mode3`.
Stage modes independently: no sibling/cross-mode reads, links, copies or
shared candidate bytes. Keep the five-file-per-mode edit boundary and packet52
all assertions, exact wake bytes, observer begin/end parsing, phase/mailbox
matrices, ownership, destruction-before-deallocation and cfg(not(test))
erasure requirements unchanged. On the first real failure write only the
six-field `phase-i-failure.txt` and stop; never repair in place.

## Scratch-compatible final validation

After reauthentication and candidate hash checks, replace only the invalid
repository `git diff --check` step with this explicit non-importing validator,
run as `python3 -B` with explicit argv (one invocation per file or the ten
paths in stable order):

```text
python3 -B -c 'import sys
for name in sys.argv[1:]:
    b=open(name,"rb").read()
    if b"\r" in b: raise SystemExit(f"CR:{name}")
    if any(line.endswith((b" ",b"\t")) for line in b.splitlines(keepends=True)):
        raise SystemExit(f"TRAILING:{name}")
    if not b.endswith(b"\n"): raise SystemExit(f"FINAL_LF:{name}")
    if b.endswith(b"\n\n"): raise SystemExit(f"EXTRA_EOF_BLANK:{name}")
print("PASS_WHITESPACE")' -- ten-candidate-paths-in-stable-order
```

The reviewed implementation must use the literal argv paths, not a shell glob,
imports, repository-relative substitution, candidate-generated code, or any
source execution. Expected status is zero and exactly `PASS_WHITESPACE`; each
negative control (CR, trailing space/tab, missing single final LF, extra EOF
blank line) must return nonzero with its named diagnostic. This validator is
byte-only and reads no sibling mode. Then repeat packet52 authentication,
reconstruction, cfg erasure, invariant, canonical membership, single-link and
bytecode checks; assert exactly 327 regular files, 51 source members per mode,
no symlinks/bytecode/extra paths, and no Phase-II files. Create the canonical
handoff only after every check passes, then stop for independent handoff review.

No compilation, runtime, guest/native execution, Phase II or acceptance credit
is permitted. Report this file's SHA256 and `git diff --check --` result (the
repository check is only for this packet file); do not edit existing evidence.
