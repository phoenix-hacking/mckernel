# QMP capacity successor: independent source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
**Accept the frozen source for root-granted ordinary regression tests.** This is
not test acceptance, a runtime release, kernel/application acceptance or P12
credit. No tests, compiler, root, guest, cleanup or release action was performed
by this reviewer. The sole fix author's candidate was not modified.

## Actual failure and evidence limit

The exact SDK8 attempt63bd result reports ordinary QMP transcript overflow during
lifecycle; terminal quit then hit the same ordinary cap. QMP evidence capture
also failed its24MiB serialized-file limit. The actual QMP transcript file does
not exist because that writer rejected the encoding before opening the file.
Consequently actual transcript row counts, raw bytes and encoded expansion
beyond those thresholds are unavailable; this review does not invent them.
Retained serial diagnostics contain364 completed progress records, ending at
round363/728 launches and2008.862221651 seconds of reported mixed work. These
are failed-run diagnostics only: no partial-hour, whole-test or kernel-pass
credit. See RETAINED-FAILURE-FACTS.json.

## Frozen source acceptance

Reviewed the final SOURCE-READY marker, all six selected source postimages and
the added existing-suite test source. All seven byte identities match that
marker. The first patch was superseded by these final postimages.

The selected LONG profile passes32MiB ordinary raw,128MiB ordinary serialized
and1,048,576 ordinary row limits explicitly from runner through backend factory
to QmpSession. The raw2MiB, encoded8MiB and4096-row reserves remain finite.
The first record exceeding an ordinary budget is appended before failure;
hard reserve checks prevent unbounded retention. Encoded accounting matches
the final serializer's sorted-key/default-separator format, including list
brackets and comma-space delimiters. It operates only when an encoded limit is
configured. Default short raw8MiB/file24MiB/2-second behavior remains selected,
without per-row JSON accounting work.

Terminal quit temporarily enters the existing bounded recovery mode, handles
only existing exact-ID stale replies, and restores the prior recovery state
in finally on success or exception. Original lifecycle failure priority and
independent process retirement stay intact. Hard-reserve exhaustion still
fails explicitly; the change does not trim/coalesce rows to obtain acceptance.

The LONG writer and owner readback use136MiB consistently. Writer serialization
and exclusive file publication have their own10-second alarm after QEMU
retirement is attempted; no cleanup control budget is consumed. Owner QMP
regular-file read, hashing and strict list parsing have a separate10-second
alarm only after positive container absence and lock release. The existing
alarm refuses an ambient timer and restores the signal handler. No polling
interval, deadline, response identity, malformed-response check or acceptance
oracle is relaxed.

## Capacity and memory

The final author's conservative model uses156064 status transactions for the
full7800-second inner allowance at unchanged50ms polling, including64 control
transactions. At192 raw bytes per pair plus1MiB startup, modeled raw traffic is
31,012,864 bytes, below32MiB. With twice raw bytes plus96 bytes of metadata per
record, modeled encoded traffic is91,990,018 bytes, below128MiB. Nominal312128
rows leave over3.35 times headroom under the ordinary row cap. This is a stated
status-only traffic envelope, not a claim that arbitrary1MiB responses or all
possible byte fragmentation must complete. Finite byte/row limits still fail
closed when their envelope is exceeded.

Legal pending capture maxima join as384MiB serial +136MiB QMP +12MiB other
streams +32MiB metadata =564MiB, below640MiB shared capture, leaving76MiB.
The shared increase is128MiB and is reflected in4224MiB logical growth. The
384MiB per-file limit still covers the QMP artifact. Fresh resource admission
must use these new values; predecessor4096MiB/512MiB admission is insufficient.

Row caps bound fragmented-read object amplification independently of raw_hex.
The author's conservative per-phase models are1526MiB inner serialization and
1494MiB owner readback, conditional on the exact64-bit CPython row/metadata
assumptions. On the normal-success path serialization follows positive QEMU
reap; owner parse strictly follows container absence/release. The diagnostic
also attempts QMP capture after uncertain reaping to preserve failure evidence.
That failure case must retain the physical hold and account for possible
8GiB guest plus roughly1.5GiB serializer coexistence inside the12GiB admission,
including the remaining interpreter/QEMU overhead. This is source/resource
reasoning, not an observed peak or proof that uncertain processes retired.

One meaningful assumption remains for the ordinary fixture: the proposed test
interpreter resolves to Python3.9, while the512-byte decoded-row allowance
includes distinct key strings and may be tight for that interpreter's dict
layout. The new exact-interpreter fixture must decide this. A failure requires
a coherent documented memory-bound/model correction, retaining the meaningful
oracle and all rows; no result is assumed here.

## Required next evidence and root-owned boundaries

Run the source author's small extended QMP suite under a fresh ordinary grant
with the actual assigned CPU/resource/capture bindings. It covers raw and
encoded exact boundaries, retained first-over-budget records, finite row and
hard reserves, cleanup quit with stale exact-ID replies, recovery-state
restoration on error, short-path behavior, exact LONG propagation, full-wall
capacity arithmetic and target-interpreter memory assumptions. Existing
lifecycle/owner regressions remain relevant to writer/readback and original
failure priority. This review grants no execution and does not assert tests
passed.

After those checks, root must materialize a fresh coherent source cohort and
namespace/nonce, roll the source/owner/runner/profile/validator pins, rebind
HOST output/capture geometry and admit the extra128MiB growth against actual
floors and sparse backing obligations. The candidate intentionally retains
predecessor immutable namespace/source pins and is not directly a runnable new
owner. Retained attempt63bd and its source/release remain immutable.

Only the root's normal physical retirement and fresh independently reviewed
LONG release can authorize the unchanged kernel/image/modules/collector/apps/
oracles run. This source fix changes harness capacity and bounded terminal
control only. No new kernel/module changes or shortened/accumulated time credit
are authorized by this review.
