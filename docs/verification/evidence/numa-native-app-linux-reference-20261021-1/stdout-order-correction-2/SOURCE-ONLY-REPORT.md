# Exact positional expected-order correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Practical supported OS/apps and active compute Rust/assembly migration remain
the scope. No semantic output, application source or success-oracle change.

The dispatcher reports the first retained checker passed once, exit0 in
0.060348122seconds, all9 vectors; the retained application was not rerun.
That successful stdout-order-correction-1 directory and the original failed
compile-reference-1 wrapper remain unchanged.

User tightening: no weakened/sorted assertions. This sibling copies the first
expected.stdout verbatim and changes exactly one checker expression: the
old-to-corrected order constraint now requires the exact single positional
replacement of `guards=1 neighbors=2 process=1` by
`neighbors=2 process=1 guards=1` to equal the full EXPECTED bytes. There is no
sorted assertion anywhere in this checker. The existing JSON `sort_keys=True`
only formats the result object and is not an assertion or oracle comparison.
Full source-derived byte equality, pinned input hashes, stderr/status/closure
checks and all9 comparator vectors are unchanged.

This is user-directed comparator implementation tightening after a passing
retained correction, not another failed production attempt. No checker,
compiler or application execution occurred for this sibling. No native or
retirement credit is claimed.

Next observation, only after dispatcher grant, uses the reviewed retained-only
CPU7/1GiB/30CPU/35wall envelope and a fresh dispatcher-owned result directory:

```sh
python3 /home/holden/mckernel-work/host-preparation/numa-native-app-consumer-20261021-1/stdout-order-correction-2/check_retained_reference.py
```

Expected: checker exit0, empty stderr, the same PASS retained-reference JSON
with9 vectors/116 stdout bytes and no compile/app rerun or native credit.
The checker reads parent evidence and creates no payload process. The parent
source/failed wrapper and first successful correction are preserved.
Only this sibling directory was written; no root/network/compiler/app/Git/
launcher/ownership operations or child agents. Stop at source handoff.
