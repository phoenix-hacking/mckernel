Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

CAUSE AND ORIGINAL CONTRACT: original accepted FP manifest27f5ff33 and its
execution proposal both require stdout/stderr4096 and explicitly select the
ND_FUTEX4096 collector profile. Original oracle fixes254 bytes/exit0/stderr0;
it does not replace that capture bound. Current C020 was compiled with
-DND_PROCESS_EXEC_WAIT, whose existing source selects1024. The adopted FP
manifest4096 is correct; the selected collector profile is wrong. Original
actual692 result FAIL_STREAM_ACCOUNTING/mckernel_application_executed:false,
manifest, raw report, stdout/oracle and all failed evidence remain unchanged.
No retrospective1024 normalization or wholeprotocolPASS is proposed.

ACTUAL PARTIAL ONLY: ACTUAL-FP-TRACE-AND-BEGIN-PARTIAL-CHECK.json405e9ca6 records
unchanged f368 _check_syscall_trace(serial,pid255,True,False) PASS, genuine ACK3
and retirement51=-11/52=0, exact FP254/exit0/EOF/procfs values. The independently
requested original F04 file/proof scope decision belongs to Root/reviewer; this
source packet supplies no file/native/protocol acceptance. Synthetic4096 model
controls in ACCOUNTING-TEST.stdout are clearly separate, never altered captures.

MINIMAL GENUINE REPAIR: compile the SAME pinned current C020 sourceb3fc in its
already-existing -DND_FUTEX profile. ZERO C source/body changes, no kernel/module/
payload rebuild. It selects original4096 cap/8192 frame and existing bounded
write_all publication. Every other conditional use is a shared
ND_FUTEX || ND_PROCESS_EXEC_WAIT branch: same FPargv/env/cwd, 10s payload limit,
allow_oversubscribe boot, helper/cleanup/procfs behavior. Existing profile
exclusion checks remain. Native BEGIN0/EOF/accounting/oracle checks stay intact.

QUALIFICATION-RECIPE.NOT-GRANTED.json freezes exact commands/tool/source pins.
It proposes ONE production collector compile (argvSHA c365c371), one exact-source
inert frame-fixture compile (fee8c436) and one HOST-only literal-consumer test
(98d8d798). Root must explicitly grant the ordinary batch/slot; none ran here.
Root may select the required collector command and separately authorize the two
focused fixture commands, retaining completed prefixes. Do not execute the
collector main on HOST: it contains guest module/bootstrap operations. The
fixture includes exact source, renames its main and calls ONLY frame() on inert
structs; static assertions enforce4096/8192. It checks original254 frame,1025B
without1024truncation, oversized-frame rejection and truncation reporting. The
Python runner uses exact pinned consumer statements and NEVER runs collector main.

Proposed limits: CPU6/job1/AS2GiB/CPU60s/FSIZE64MiB/core0/wall90 each, Root's
existing admission/supervisor and fixed account/resource/cutoff checks. Create
fresh output-PENDING-ROOT only under actual grant. First failure stops; no
unchanged/passed-prefix replay. Preserve actual argv/status/streams/CPU/RSS/wall/
all direct and parent joins. No compiler or guest authority is supplied here.

AFTER genuine new collector artifact/fixture qualification and independent scope
review: reuse existing native_diagnostic_overlay.py46d41bc0 build_overlay API
on the ALREADY26eb basee03f3e00. New collector requires fresh overlay init record;
no image/base/payload/module rebuild or image-record derivation is needed. Keep
base13,308,071B/image26eb and original4096 FP contract. Source-only continuation
API/input details are in OVERLAY-CONTINUATION.NOT-GRANTED.json. Bind actual new
collector/overlay/final-map metadata, validate real f368 and every readonly export
BEFORE any future fresh clock. Newly qualified output/template/review must name
ND_FUTEX and actual new binary; old C020 binary/helper-profile qualification is
not silently reused as that artifact proof.

Any later full-protocol guest requires Root's fresh namespace/CAPTURE/unusednonce,
latest actual typed physical clearance, exact independent execution review and
once-only Root grant. It cannot reuse692/86 or old staging/grants. All policy,
TTL, caps, EOF, bytes, oracle, trace and positive BEGIN0 guards remain unchanged.
Do not run an unchanged guest to rediscover this known stream-accounting mismatch.
