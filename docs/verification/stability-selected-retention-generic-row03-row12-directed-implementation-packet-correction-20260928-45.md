# M01-B packet29 correction45 — complete mode-2 source authority path

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction addresses
only attempt44's missing supplied mode-2 source path. Authenticate packet29 and
corrections31/34/36/39/42, `PASS_PACKET` review43 SHA256
`a173b29370b77886b067693282bfc4b1a09f5c0dce626bd8d131c066d18655d8`,
attempt44 raw failure SHA256
`f3cdf239225b053ac42d058a4abb0357216708fc5a019d3f7000aae1ed04181b`,
and its immutable archive SHA256
`de032f2e45e8defefdbdeafe04d469bdd9f544fd51fb00696a7c8b5d4d47b697`.
Attempts 41 and 44 and their archives remain immutable.

The packet's mode-2 record remains exactly
`/home/holden/mckernel-work/scratch/stability-published-hold-module-20260913-postpublish-notify-1/record.json`,
SHA256 `3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`,
size 176401, status `PASS_BUILD_ONLY`, mode `postpublish-notify`. That record path
is not a source directory and does not authenticate a sibling `source/` path.

For mode 2 only, supersede the absent attempt44 source argument with the existing
authority directory:

```text
/home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2
```

Before staging, require that canonical path to be a mode-0700 directory owned by
the current unprivileged user, with exactly the 51 flat regular `.rs` members in
`scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json`
(manifest SHA256
`d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0`,
size 19839), no missing/extra member, symlink, directory, FIFO or other type, and
every exact manifest size/SHA256. In particular require:
`application_syscall.rs` SHA256
`83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92`
size 17343, `smp_application_syscall.rs` SHA256
`4f7611fca376aacddf80be2dacef0928f5e6c8506c692f0154680f93dfeaa5d4`
size 36879, and `stability_phase.rs` SHA256
`041b7e983132745e64aed003e745600f7e8573ed19a8ead57a4f4fecda888131`
size 16600. The mode-3 hashes `b18b...13ee2` and `d81b...d4ea` must never appear
as mode-2 substitutions.

After independent `PASS_PACKET`, one source-only attempt may invoke exactly:

```text
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2 --output <fresh-absolute-mode2-root> --mode postpublish-notify
```

The new packet must bind one absent fresh attempt root and the exact corresponding
mode-3 authority independently. Source and output canonical paths must be disjoint.
The existing stager's `mkdir(exist_ok=False)`, member/type/size/hash validation,
no-bytecode rule and first-failure preservation remain mandatory. Stop without a
retry on any authority or staging mismatch.

This correction does not modify the historical source map, construct a replacement
tree, copy the proposed eight-file mode-3 set, authorize attempt45 by itself, or
release Phase II, compilation, runtime, guest, native backing, application,
production-gate or whole-OS acceptance. All other inherited packet requirements
remain normative, including independent complete handoff review before Phase II.
