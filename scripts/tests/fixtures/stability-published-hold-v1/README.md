# Published completion hold, private source candidate v1

This new verification overlay supplies the missing acknowledged AcceptedReturn
hold for modes 2 (`postpublish-notify`) and 3 (`recoverable-backpressure`). It is
source only. No author imports, staging runs, compilation, tests or guests have
run. It does not authorize execution or grant application, transport, physical
ring, ownership, stack, or production acceptance. The original mode 1 and 4
fixture, stager, compiled modules, contracts and evidence remain unchanged.

The frozen design is
`docs/verification/stability-accepted-prefix-hold-draft-20260913.md`. The actual
single-packet-thread source proof is retained in
`/tmp/stability-selected-send-single-owner-review-20260913-9gpi_2di`.
Root owns the separate `owner-return-poll-v1` candidate: raw `running`, incomplete
or malformed `/proc/.../syscall` samples must remain UNKNOWN. This overlay does
not repair or reuse the old v2 polling report as authoritative RET evidence.

## State, owners and clock

One selection exists per fresh verification module, with no reset path. The
selected `Delivery` serial refers to the original immutable Request. The new
Mailbox helper verifies the real worker, pid, CPU, requester, read number/fd/
length, completion state, and actual Completion ownership claim (OS generation,
ledger serial/index and physical response span). It copies
`call.publication_since` and never initializes it or reads response memory.
The source-bound full owner/physical join still checks the original target and
all six request arguments, along with the native and launcher identities.
Live-hold operations separately reject original Entry closed, needs-cleanup or
quarantined state and a closed/quarantined selected Mailbox. Global transport
health is insufficient to authorize an application that is already retiring.

The states are 0 unselected, 1 armed, 2 accepted pending, 4 emitting, 5 held ready,
and 3 released. `accepted_selected()` is still called only after successful
selected Completion preparation, while slots is held. The end-pump hook first
checks the selected Runtime's actual OS generation, then acquires the observer
Permit. It briefly locks slots and waits for the ordinary production timeout
scan to have supplied `Some(timer)`. `None` leaves state 2 and emits nothing.

With `Some(timer)`, it verifies runtime/transport health and the original claim,
checks the original deadline, and changes 2 to 4 under slots. It then emits one
complete AcceptedReturn snapshot outside all production guards. It reacquires
slots briefly, rechecks that same completion/claim and exact timer, checks the
deadline again, and changes 4 to 5. The bounded READY line is printed after
unlocking, before Permit drops. Subsequent pumps do not emit another accepted
snapshot. No host wait, sleep, user copy or log formatting occurs under slots;
no host wait spans Permit. Existing transport-to-slots ordering is preserved:
the release path takes slots only and never acquires transport afterward.

This refines the design's single held state into EMITTING=4 and HELD_READY=5.
The ready scalar commit occurs under slots before READY formatting; Permit
prevents any query/release from observing it until that logging call completes.
This preserves the externally visible ready boundary without formatting under
slots or adding another owner.

The retained source proves there is exactly one Packets thread per Runtime and
that it is the only caller of `publish_syscalls`/`Remote::publish_syscall`. Thus
its selected send cannot overlap its own accepted snapshot. The extra state 4
also makes the count boundary explicit under the existing slots lock: any
selected callback after that transition uses HOST_HOLD_CALLS, including a future
overlapping caller. A future new caller still invalidates the retained source
proof and requires review; this state is not blanket concurrency acceptance.

Before state 4, deferred sends increment the original phase barrier counter and
the old fault wrapper's barrier counter together. In states 4 and 5 they instead
increment only the new host-hold counter, then return -11 before any fault
attempt, real send, publication, or notification. The host-hold counter saturates
at the explicit evidence limit 1,000,000; an additional call latches -75. This
limit is a new verification evidence budget, not a production timeout or an
existing policy. It cannot restore health, reset the timer or grant acceptance.
After state 3 the real wrapper always runs, even if later observation invalidates
verification. The barrier never re-arms.

The production timer is coarse native seconds. The sole deadline remains
`(original_timer + 5) * 1,000,000,000`, with checked overflow. Every ready/status/
release check uses native monotonic time and the copied original timer. Release
in mode 3 additionally requires strictly more than 2,000,000,000 ns remaining;
its unchanged two-second injected backpressure still begins at the first real
post-release fault attempt. This reserve is necessary, not a guarantee that
later scheduling, logging, or ring availability will permit timely recovery.
Actual successful callback end must precede the original deadline. Native and
host overall deadlines are separate; QMP pause does not reset either contract.

## Private 256-byte little-endian protocol

The candidate replaces the isolated phase module with version 2 and command
`0xc100f502`. Compat requests are rejected with -95. It does not add a public
production ABI. Modes 1/4 and private version 1 use their original module bytes.

Input bytes 0..64 retain the original fields: u32 version at 0, u32 operation at
4, u32 OS slot at 8, i32 positive launcher pid at 12, then u64 OS generation,
strict next ioctl sequence, nonce low, nonce high, delivery serial and ledger
serial at offsets 16, 24, 32, 40, 48 and 56. OS is below 64; generation, sequence
and the combined nonce are nonzero. Selection requires zero delivery/ledger;
all later requests match the actual immutable selection and bound nonce.

Operations 1 SELECT_BLOCKED, 6 QUERY, 7 ACCEPTED_STATUS and 8 RELEASE_ACCEPTED
are shared. Mode 2 alone permits 2 TERMINAL and 3 TERMINAL_PLUS_FIVE; mode 3 alone
permits 4 RECOVERY and 5 AFTER_EIGHT_HELLO. Full snapshots are strictly ordered
BlockedRead sequence 1, AcceptedReturn sequence 2, Terminal/Recovery sequence 3,
and TerminalPlusFive/AfterEightHello sequence 4. Diagnostic queries do not emit
snapshots. Accepted status returns sequence 2 only for a healthy exact live
completion, held state, and matching unexpired timer.
Before held state, operation 7 returns -11 in states 1, 2 and 4; after release
it returns -116. A prior verification failure remains an error. A dispatched
pending-status reply consumes its ioctl sequence and supplies the complete
defined output; the controller may poll with a fresh next-sequence query.

Nonrelease inputs require every byte 64..256 zero. Release requires u64 accepted
snapshot sequence 2 at 64, u64 UART capture sequence 2 at 72, a nonzero raw
32-byte ACK SHA256 at 80..112, and zero 112..256. The accepted and UART sequences
are separate spaces, each frozen to 2 for this profile. The digest is retained
as four little-endian words only for transport/logging. The kernel does not
validate the host manifest or infer QMP success from nonzero digest bytes.

After successful parse, Permit, request validation and acquisition of the actual
Started runtime, the ioctl consumes its sequence immediately before dispatch.
A dispatched release claims one atomic release attempt before state/health/
timer checks. Any dispatched release error invalidates verification; no later
release can succeed. A successful release changes 5 to 3 under slots and
records one commit before the selected sender can reacquire that lock. Input
copy precedes native guards; output copy follows Permit/production guard drop.
Copyout failure cannot undo dispatch or publication. Never replay a dispatched
sequence. Fresh next-sequence QUERY/ACCEPTED_STATUS polling is allowed; a
dispatched RELEASE is never submitted again, even with a new sequence. Early
errors before dispatch leave the userspace request buffer intact.

Output preserves bytes 0..64 and rewrites every byte 64..256, including the old
input digest area. Fields are: snapshot u64 at 64; signed errno as i64 at 72;
selected application/worker/delivery/ledger serial/index/response start/end at
80..136; selected pid/cpu/requester/OS as 32-bit values at 136..152; generation
at 152; stage at 160; accepted sequence at 168; terminal timestamp at 176;
signed verification errno at 184; old barrier count at 192; consumed request
sequence at 200; original timer seconds at 208; exact 0/1 timer-present flag at
216; held-ready native timestamp at 224; host-hold count at 232; ioctl native
entry timestamp at 240; output-observation timestamp at 248. All remaining
fields are u64. A zero timer is valid when the separate presence bit is one.
The last timestamp precedes userspace copyout and is not a copyout completion.
Successful SELECT/full terminal/recovery snapshots return their actual sequence
at 64; QUERY success returns 0; ACCEPTED_STATUS and RELEASE success return 2.
Every dispatched error returns 0 at 64, the actual error at 72 and the consumed
sequence at 200, with all remaining output fields still defined. A zero error
snapshot field does not prove that a failed full observation emitted no lines;
retain its original raw output. Only pending-status polling is expected to
produce repeated dispatched -11 replies without full observations.

The future C client must verify all output fields, identities, request echo,
sequences, defined types and monotonic bounds, not merely errno. Pre-Permit busy
-11 may be retried only when the entire 256-byte buffer equals the original
request and independent operation policy permits it. In particular a release
request has a nonzero tail, so the original version-1 all-zero-tail test is
incorrect. Once a release ioctl is submitted, the conservative host/client
policy treats publication as possible even if the response is ambiguous.

## New bounded observation records and external gates

Original owner/RET/PHASE/FAULT records keep their frozen schemas. Each full
phase additionally has exactly one STABILITY_HOLD_COUNTS version=1 between the
FAULT counts and PHASE END. It records mode, phase sequence, stage, timer
presence/value, host-hold calls, release commits, release-attempt flag,
verification errno and native time. Accepted counts are sampled in state 4;
the subsequent STABILITY_HOLD_READY records accepted sequence, nonce, timer,
held timestamp and later native time. The strict future join must require one
ready event and match these to the complete accepted envelope and ioctl reply.

Every dispatched release emits one STABILITY_HOLD_RELEASE version=1 outside
production locks. It records mode, ioctl/accepted/UART sequences, nonce, all
four ACK words, errno, commit count, copied timer, and native begin/end bounds.
These bound the attempt, not the exact scalar transition. Real send output can
interleave after commit and before the ioctl log/copyout. Preserve raw order and
timestamps; never infer a stronger ordering from line position alone. Unknown,
missing, duplicate, truncated, overflowing or contradictory hold records must
fail the new join. Existing parsers ignore this prefix and cannot independently
close this new profile's hold protocol.

The future controller needs an ACCEPTED_RETURN UART transaction after querying
healthy held status and independently locating the original blocked RET worker.
Host QMP must capture the original 40-byte response and actual ring while held,
confirm only source-permitted prepared-prefix changes, verify no selected wake
publication, resume and verify running, durably retain the manifest, then ACK
the exact identities/sequences/digest. Host latches release-possible BEFORE its
first ACK send attempt; controller latches it BEFORE release ioctl submission.
Partial/error/timeout on either side may follow peer receipt or native commit.
Every later normal, emergency or final capture must forbid original-response
reads, even if the local operation reports failure. Terminal mode 2 and healthy
mode 3 observe postpublication state without reading the released response.

These native labels do not prove physical bytes, ring capacity, guest identity,
worker provenance, host task/UART/QMP handling, or payload outcomes. Mode 2 also
needs explicit original selected call/tag absence after its successful send;
mode 3 needs natural exact payload PASS/exit37 and eight independent later HELLO
launches in the same healthy OS. The existing synthetic -11 injection supplies
no physical-full-ring credit. Native RET result and timing remain authoritative
over the separately corrected host polling observation.

## Isolated staging and remaining validation

`prepare_stability_published_hold.py --source COMPOSED --output FRESH --mode
postpublish-notify` (or `recoverable-backpressure`) expects the complete flat
Rust-only result of the original owner, phase and fault/RET stagers. Root must
bind that input to reviewed production/compiler source. This new stager checks
the exact frozen phase module/appendices and complete selected-mode send
appendix, replaces only those phase appendices/module and the send barrier
block, and copies the entire tree to FRESH/source. It preserves exact original
bytes, helper/templates, all diffs and identities, verifies inverse edits, and
rechecks every input. It rejects modes 1/4, mixed/modified original fixtures,
already-held input, symlinks/special files, noncanonical/nested roots, non-Rust
members, excess files/bytes, CRLF, ambiguous hooks and observed input mutation.
Its bounds are 128 files, 8 MiB/file, 64 MiB combined. Outputs are never reused
or cleaned after failure. The final stage record grants no execution authority.
A bounded source read is retained and identified before CRLF, UTF-8 or aggregate
budget validation. An aggregate-budget failure may therefore retain one extra
triggering member of at most 8 MiB, without accepting it into the staged tree.

The additive inline boundaries preserve the original ten role/service splits
and isolate the new phase snapshot/command/accepted helpers. A new pinned
compiler build and actual native stack-chain measurement remain mandatory.
Old module frame measurements cannot prove these new paths. Linux entry,
formatting callbacks, console paths, interrupts and dynamic edges remain scoped
residuals rather than a whole-Linux static certificate.

`negative-cases.json` specifies focused tests against these exact source
interfaces. Root owns implementation/execution of the harness and all pinned
staging/build/negative tests, independent review, C/UART/QMP composition, and
contained guests. No tests have run in this source lane.
