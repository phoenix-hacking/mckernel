# M01-B validator recovery expert packet62

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. Owner: delegated recovery design
expert. Defect: packet60 and its single bounded correction61 do not provide a
working byte validator and unambiguous fresh-root installation. This is the
required expert escalation of that same failure family, not a fresh retry budget.
Next check: independent `PASS_PACKET` on these exact bytes, followed by one
source-only root58 attempt and independent handoff review. That can unlock
consideration of a separately released compiled microtest. It releases no
compilation, Phase II, native/guest execution or acceptance credit.

The dispatcher supplied the final independent `FAIL_PACKET` findings for61 as
agent output: LF-terminated space/tab controls erroneously pass; text says four
controls although five are required; packet60/reviews56/58 are unpinned; live
START differs from packet52; absent-root ownership and precreated mode paths
make the staging sequence impossible; existing source destinations conflict
with exclusively-new installation; diagnostics lack a separate allowed root.
The dispatcher will retain this agent review additively at its checkpoint.
There is no invented review-file hash. Preserve both rejected packets and every
earlier failure, archive, authority and candidate byte.

## Authentication before any write

Paths in the first table are relative to `docs/verification/`. Authenticate
each listed SHA256 and the inherited packet52 authority closure before staging;
never replace a pin with the observed hash. Existing reviews release their
original roots only. None releases root58 without this packet's fresh review.

| Path | SHA256 |
| --- | --- |
| `stability-selected-retention-generic-row03-row12-expert-correction-packet-20260928-52.md` | `846605e3c35c48e65ff892ae65ec67182eee1c5e38a43f3d5e83e651aa968568` |
| `stability-selected-retention-generic-row03-row12-expert-correction-packet-review-20260928-52.json` | `827aa3d059eced6de524441acdc30cedd7482b44de9300bb86f3d46fe4a4df39` |
| `stability-selected-retention-generic-row03-row12-phase-i-handoff-review-failure-20260928-51.json` | `2913908f491eeac00cbd15921e4d797820ba1d7bfb3bd55f7367ca2195b1c448` |
| `stability-selected-retention-generic-row03-row12-phase-i-handoff-review-failure-20260928-53.json` | `0cc9d44de53411044a11a6d3f4f688377faa4cbcd01fff450a4e136c5cd0098c` |
| `stability-selected-retention-generic-row03-row12-capable-owner-reassignment-packet-20260928-54.md` | `3f83ae8f4f7d200c9f6f0ed1a8df335c244af84106db9ef9ad3f654ecd9556f0` |
| `stability-selected-retention-generic-row03-row12-capable-owner-reassignment-review-failure-20260928-54.json` | `7b45715fc3c078a753db3962f48a8b4a1d176752995531e8806f487a082cd6fa` |
| `stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-54.json` | `c516fdc8ef5e13a942e5bf87ba10d10b7bfe0f4de28e1570a0726d7e036d2b51` |
| `stability-selected-retention-generic-row03-row12-capable-owner-reassignment-correction-20260928-55.md` | `a39d721796f8695aadfdc6afec1950ff65063f9cbc9a1b822abe3a373aea0a47` |
| `stability-selected-retention-generic-row03-row12-capable-owner-reassignment-review-20260928-56.json` | `58d0a115b4f30ebbe0a664ca3bd222082a8d55bff60033cb75d5c9d2d87b77b5` |
| `stability-selected-retention-generic-row03-row12-false-failure-recovery-packet-20260928-57.md` | `834822fc61dc323a4955d3a23803ce1834dd0d73ff8fd6b429dac083dfccd8a2` |
| `stability-selected-retention-generic-row03-row12-false-failure-recovery-review-20260928-58.json` | `af7f4be043c98800a814e9b76e675adaa7381a68a1b99d08695e3aeb9fe46f3c` |
| `stability-selected-retention-generic-row03-row12-phase-i-source-review-20260928-59.json` | `5b1113f6c58c1d19a343e61fd0e9ee87471d0c7761a5d76b57dacffcd1a3ef89` |
| `stability-selected-retention-generic-row03-row12-validator-recovery-packet-20260928-60.md` | `4dc69511c0725e9045b6cee38035622118edec363d5fc39a42065638b8a9d126` |
| `stability-selected-retention-generic-row03-row12-validator-recovery-packet-correction-20260928-61.md` | `cb2349ece14586f23012a4910fa0a249c679ba407909404adf82f9a64a4ca0f5` |
| `stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.json` | `c678dfa6af9682cc97c584e1f6c6522fbc773b093b463892571cb53a5830bad4` |
| `evidence/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.tar.gz` | `8eabf2eb29512ce628da616ffe587bfa5d75775be2e783e55418f67e91d3a59a` |

The raw archive member
`m01b-generic-row03-row12-expert-correction-packet-20260928-56/phase-i-failure.txt`
has SHA256 `1fc20dcfec9b3413c40352ef68c531761c66ac371eb99dbec3bd7117dcf29afb`.
It is not the JSON record. The archive has 338 unique members, 327 regular
files, and otherwise only directories. Read archive data without extraction;
reject absolute/traversing/duplicate names, links and special members. Verify
the raw failure member and all ten candidate mappings below. Root56 remains
failed: its Git command exited128 before checking scratch whitespace. Review59
is source evidence only; no handoff or execution result exists for root56.

Retain packet52's full inherited pin closure (the 71 pins attested in review51),
packet29 and corrections31/34/36/39/42/45/48/49/50, historical handoffs and
archives, two complete source authorities, source map, stager inverse and
template bindings. Resolve each named historical artifact against its bound
path/hash in those immutable packets; do not silently omit a failed ancestor.
Correction34 is SHA256
`61dd037ef1363b63f35e7bd29c2bd3e3c6d2e594914f621cc90d6c7b399f451c`.
Correction36's canonical root field supplements its exact handoff schema.

Adopt the live campaign policies, all under `docs/verification/os-milestones-20260914/`:

| File | Live SHA256 |
| --- | --- |
| `GOAL.md` | `76c4f5d12e3f233c8dc4f8f1a77dd1f2eae9df2ff8fb9f4000ef5a2e94c0bcc3` |
| `START.md` | `30a90c799c3031014adcb87daf6e328ff360fae22ec8540f803563514b4c5509` |
| `CONVERGENCE.md` | `d211e7dcda735dc98c4557e6aead941d07fb595ffc6c2fdb0bd03317f8dc1eab` |
| `HANDOFF.md` | `265cd9997588f84d69f4fa9da00b9df9b7153bf9e94366b478639941e680a415` |

Packet52's START pin `6e4b28be2bc6d101da8538d1bb640ef98bccacea011487e750b1ed4ccff61c3a`
is historical provenance, not a demand to overwrite the current authorized
overlay. This packet explicitly supersedes that one live-policy comparison
with `30a90c79...`; retain the historical value and current overlay separately.
No other source, packet, fixture, release or policy pin is relaxed.

Direct staging input pins (paths relative to repository root):

| Path | SHA256 |
| --- | --- |
| `scripts/tests/prepare_stability_selected_retention.py` | `c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0` |
| `scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json` | `d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0` |
| `scripts/tests/fixtures/stability-selected-retention-v1/response-prepare.rs` | `38f5202ca358fc89cf440e4633cf6d98aa5549d550740da3acadd1fd040d8421` |
| `scripts/tests/fixtures/stability-selected-retention-v1/return-prepare.rs` | `3ea01848a34cbefd202de4947d4598b10ad55b298b170a60158b43ded840ac7c` |
| `scripts/tests/fixtures/stability-selected-retention-v1/cancel-guard.rs` | `39c75e46564da98a5d06d709bf31e309b46ba6bf2166a381d6f2e5354cdeb3e6` |
| `scripts/tests/fixtures/stability-selected-retention-v1/mailbox-retention.append.rs` | `b47f7f78f1b6d385a99de811eec46e7888f76219838fbeee1aff463d32d0a69a` |
| `scripts/tests/fixtures/stability-selected-retention-v1/phase-retention.append.rs` | `cf67a5c2b944c312e6467208ef3c87519be284a896a46dc23d598f7d3fbf5089` |
| `scripts/tests/fixtures/stability-published-hold-v1/send-gate.rs` | `dac2855ca19e587c33f7bd5a36c30c9090a6ea846f6dca90081abf0543228267` |

The pinned source manifest supplies each exact 51-member tree and every
member's size/hash, plus the following required authority records (absolute):

| Path | SHA256 |
| --- | --- |
| `/home/holden/mckernel-work/scratch/stability-published-hold-module-20260913-postpublish-notify-1/record.json` | `3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48` |
| `/home/holden/mckernel-work/scratch/stability-transport-fault-module-20260913-recoverable-backpressure-1/record.json` | `11de2af873b88fe6afb19749195294b10b41879b6f0e99e97b95065cf25de968` |
| `/home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-2/held/record.json` | `8191c433b65769d4f8d89106f0978b4e6aa8de379b777eb0d06a8100bbae114e` |
| `/home/holden/mckernel/docs/verification/stability-selected-retention-source-authority-20260915.json` | `868d6a90b8acd56b7cf1c3b61884c76abad605a1a6c31215607b098a99da73e1` |

## Literal lifecycle and separate diagnostic ownership

After independent release only, the dispatcher assigns one source owner an
exclusive lease on these two previously absent canonical roots:

```text
/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58
/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62
```

Call them R and D in prose only. D is outside R and every retained root. It may
contain only `authentication.json`, `installation.json`, `validation.json`,
`controls.json`, `cr.bin`, `space.bin`, `tab.bin`, `missing-lf.bin`,
`extra-blank.bin`, `mode2-stage.stdout`, `mode2-stage.stderr`,
`mode3-stage.stdout`, `mode3-stage.stderr`. These are diagnostic evidence,
never candidate members or Phase-II evidence. Record commands as literal argv,
statuses and exact stdout/stderr bytes (hex where needed) in those JSON files;
include all input hashes, member mappings, and pre/post destination identities.
Use exclusive creation; no overwrite of retained diagnostics. In-memory records
can be finalized once per filename. On failure retain completed records and
report any unfinished record in dispatcher capture; never fill it with success.

Order is mandatory:

1. Authenticate the inputs read-only. Check `lexists(R)==False` and
   `lexists(D)==False`, canonical spelling, canonical nonsymlink parents,
   disjointness, dispatcher ownership/lease and sufficient scratch space.
   Absence has no owner/mode to check. If either root exists, stop without
   touching it; report the preflight failure to the dispatcher.
2. Set umask077. Create R and D themselves, each once with mode0700. Now verify
   lstat reports owner equal to the source owner's effective UID, directories
   mode0700, canonical paths and disjoint identities. Never precreate mode2 or
   mode3. A mkdir race or ownership mismatch stops the attempt.
3. Run the following commands sequentially from `/home/holden/mckernel`. Before
   each command require its mode output path absent. Capture into D only.
   The reviewed stager itself creates that mode and its subdirectories.

```text
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2 --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2 --mode postpublish-notify
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-3/held/source --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3 --mode recoverable-backpressure
```

4. Require both exit0 and `PREPARED_NOT_COMPILED_NOT_EXECUTED` records. Verify
   independently each 161-file staged mode, its 51 source/original/diff sets,
   six inputs, helper, record, inverse reconstruction and exact membership.
   Save before-install source sizes/hashes from each authenticated record.
   No adapter or runner exists yet; total candidate count is322.
5. Install each mode's five authenticated archive members using the mapping
   below. This is the only candidate write after staging. Read a member solely
   from that mode in the pinned archive; never read/copy/include/link candidate
   bytes from the sibling mode or root56 working directory. Authenticate archive
   hash and member data before opening the destination. Do not use extractall.
   Repeated equal hashes do not permit sharing a destination inode or buffer
   between mode installations; reopen/revalidate the archive for the second mode.
6. The three `source/` destinations already exist. Require regular single-link
   owner-local files, authenticate their current bytes against their own stager
   record, open with `O_RDWR|O_NOFOLLOW`, compare fstat with pre-open lstat
   (device/inode/owner/link count/size), reread/hash before replacement, then
   replace contents of that same descriptor and truncate to exact new length.
   Handle short writes; fsync, close, reopen read-only without following links,
   and verify exact bytes/hash, owner and link count. This is intentional
   replacement of three fresh staged files, not exclusive creation of them.
   Preserve `originals/`, `diffs/`, helper, inputs and record bytes unchanged.
7. For `adapter.rs` and `runner.rs` require absence, then create independent
   files with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW`, mode0600. Write all bytes,
   fsync/close and perform the same post-install checks. Never link/reflink,
   rename another root's inode or leave temporary paths inside R. All ancestor
   directories stay canonical, nonsymlink, owner-local under the exclusive lease.
   Record all ten mappings and pre/post stat/hash data in D/installation.json.
   Each mode now has163 regular files and the complete R has326.
8. Run the validator/self-tests and all inherited static checks below. Create
   the canonical handoff only after they pass, then stop for independent review.

Trusted, reviewed `python3 -B` standard-library snippets may implement byte
authentication, archive reads, installation, controls and handoff serialization.
They may not import/execute candidate code, the archived helper, any repository
module or generated source. The only repository script execution exception is
the two pinned source stager commands above. No shell glob decides membership.

## Exact archive member mapping

Every archive member is the literal prefix
`m01b-generic-row03-row12-expert-correction-packet-20260928-56/` followed by the
table's complete suffix. Its sole destination is the literal root R followed
by `/` and that same suffix. No other mapping or member installation is allowed.

| Suffix (archive and destination) | SHA256 |
| --- | --- |
| `mode2/adapter.rs` | `a0e20bc5b3ac65897462222d5f03f39c569c89c8d0edbb59d959cebd7e82fe0c` |
| `mode2/runner.rs` | `af9af80ad0bd31365e97989c31f8157bf72dbfeecad03f12b824bf2f2b5b94c8` |
| `mode2/source/application_syscall.rs` | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` |
| `mode2/source/smp_application_syscall.rs` | `a42b429e0af98d3e479c24239ee0d759c840b1d5920131da6b263ab944d7d2b4` |
| `mode2/source/stability_phase.rs` | `fa05e2770fb1248b7f9d3e25fd3c0c3e1427f75fabb22edf696bf2f02ca1ee38` |
| `mode3/adapter.rs` | `a0e20bc5b3ac65897462222d5f03f39c569c89c8d0edbb59d959cebd7e82fe0c` |
| `mode3/runner.rs` | `af9af80ad0bd31365e97989c31f8157bf72dbfeecad03f12b824bf2f2b5b94c8` |
| `mode3/source/application_syscall.rs` | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` |
| `mode3/source/smp_application_syscall.rs` | `120629db1692fcef6b2a7c985f785ced99ba93aa3ab197b40a784516e6100d81` |
| `mode3/source/stability_phase.rs` | `8a0923931b26ad0b0cd107b197259af25ecc068b215288d6b98a66e6de4fbad0` |

## Byte validator with executable self-tests

Use this exact trusted program. `b.split(b"\n")` removes each LF before testing
space/tab; CR is checked separately. Empty input fails final-LF. Embedded empty
lines remain valid; an extra blank final line fails. The in-memory positive and
five negative assertions exercise the same function used for file arguments.
No `--` token or placeholder path is accepted or stripped.

```bash
python3 -B -c 'import sys
def check(b):
    if b"\r" in b: return "CR"
    if any(line.endswith((b" ", b"\t")) for line in b.split(b"\n")): return "TRAILING"
    if not b.endswith(b"\n"): return "FINAL_LF"
    if b.endswith(b"\n\n"): return "EXTRA_EOF_BLANK"
    return None
assert check(b"x\ny\n") is None
assert check(b"x\n\ny\n") is None
for data, expected in ((b"x\r\n", "CR"), (b"x \n", "TRAILING"), (b"x\t\n", "TRAILING"), (b"x", "FINAL_LF"), (b"x\n\n", "EXTRA_EOF_BLANK")):
    assert check(data) == expected
if len(sys.argv) < 2: raise SystemExit("NO_INPUT")
for name in sys.argv[1:]:
    with open(name, "rb") as source: problem = check(source.read())
    if problem: raise SystemExit(problem + ":" + name)
print("PASS_WHITESPACE")' \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2/adapter.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2/runner.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2/source/application_syscall.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2/source/smp_application_syscall.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode2/source/stability_phase.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3/adapter.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3/runner.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3/source/application_syscall.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3/source/smp_application_syscall.rs \
  /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-58/mode3/source/stability_phase.rs
```

Candidate expectation is exit0, stdout exactly `PASS_WHITESPACE\n`, stderr empty.
For disk controls, create exactly the following five fresh0600 single-link
files in D with the literal bytes shown (Python byte notation, not text escapes).
Run the identical `python3 -B -c` program five more times, each with exactly
one argv path from this table replacing all ten candidate path arguments.
In each run require exit1, empty stdout, and stderr exactly the diagnostic
prefix plus `:` plus that literal path plus LF. Retain actual bytes/statuses
in D/controls.json; these expected rejections are not candidate failures.

| Literal sole file argument | Bytes | Diagnostic prefix |
| --- | --- | --- |
| `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62/cr.bin` | `b"x\r\n"` | `CR` |
| `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62/space.bin` | `b"x \n"` | `TRAILING` |
| `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62/tab.bin` | `b"x\t\n"` | `TRAILING` |
| `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62/missing-lf.bin` | `b"x"` | `FINAL_LF` |
| `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-validator-diagnostics-20260928-62/extra-blank.bin` | `b"x\n\n"` | `EXTRA_EOF_BLANK` |

The source-owner must check lstat/open identity and regular/single-link owner
properties before and after the validator and bind its read bytes to the
candidate hashes; no concurrent writer is permitted. A failed self-test,
unexpected control result, IO error or candidate diagnostic is a first real
failure. Do not correct either validator or candidate in place.

## Static invariants and canonical handoff

Repeat packet52's complete source matrix independently for each mode: generic
fallible Vec without an element Default bound; actual fresh observer begin/end
capture and strict field parsing; fixture/observer address totals1/0,2/1,3/2;
the exact Claim/metadata/request identity; complete baseline/phase/mailbox and
post-destruction/post-drain comparisons; sole ownership; Box destruction before
deallocation evidence; wake-none Err(-71), row03 invalid-125 lifetime, real row12
transitions; length128 wake bytes with LE0x14 at8 and requester70 at24; callbacks
checked even though zero sends are expected; unique metadata-only post-store
hook; no post-publication backing/pointer/span read; cfg(not(test)) exact erasure
to each mode's own authenticated staged source. Preserve the unchanged actual
observer and every production signature/branch/request/wake byte.

Repeat authority/template/helper/record/source authentication, inverse diff
reconstruction, candidate hashes, canonical membership and bytecode checks.
Require exactly326 regular owner-local single-link files before handoff, exactly
51 source members in each mode, and only packet29/31/34/36 Phase-I directories
and members. No symlinks, shared inodes, extras, failure file or Phase-II file
may be present. D must remain disjoint and is never included in this count.

Then create R/phase-i-handoff.json exclusively, using correction34's exact schema
plus correction36's `root` field, set to the full literal R path above. Mode order
is mode2 then mode3; each members array has51 entries sorted by basename, with
actual name/size/SHA256; adapter, runner and each original staging record are
hash-bound. No diagnostic/control keys or other schema changes are allowed.
Serialize `json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"`
as UTF-8. Verify readback bytes, schema, hashes and root, then require exactly327
regular single-link files. Bind the raw handoff size/hash externally in D's
validation record and dispatcher evidence. Stop for independent handoff review.

At the first real failure after root creation, stop mutations except creating
R/phase-i-failure.txt with correction31's six LF-terminated fields in this order:
`status=FAIL_PHASE_I`, `mode=<mode2|mode3|global>`, `stage=<bounded stage>`,
`expected=<exact invariant>`, `observed=<exact diagnostic>`,
`action=PRESERVE_PARTIAL_ROOT_NO_RETRY`. Values contain no newline/credential.
Preserve partial roots and original failure bytes; do not retry/repair/clean up.
If failure is discovered after creating the handoff, preserve it as failed
unaccepted evidence and report to the dispatcher; do not claim PASS or create
the mutually exclusive early-failure file. Dispatcher archival records that
post-write failure. Preflight failures before owning R are dispatcher records
only and never justify modifying an existing root.

No project compile/link, test binary, source payload, container, sudo/root,
network, native or guest operation belongs to this packet. The design author
may write only this new packet and run read-only hashes, byte-validator
self-tests and repository `git diff --check --` for this packet. Future writes
listed above remain conditional on independent release. The observed validator
behavior is infrastructure evidence, not executed McKernel behavior.

## Design-time observations

Read-only checks on2026-09-28 authenticated all42 direct table rows, including
the ten archived candidate members and all four live policies. Both proposed
roots were absent. The exact validator program above, with the ten literal
root56 paths substituted solely for read-only design validation, exited0 and
printed exactly `PASS_WHITESPACE` plus LF. Its two positive and five negative
in-memory assertions passed; future five on-disk control subprocesses are still
required and were not run. No stager, fresh-root creation or installation ran.
Repository `git diff --check --` for this owned packet exited0. Because the
packet is newly untracked, a supplemental `git diff --no-index --check
/dev/null <this-packet>` exited1 for the new-file difference with no whitespace
diagnostic. These are packet/validator checks, not candidate execution.
