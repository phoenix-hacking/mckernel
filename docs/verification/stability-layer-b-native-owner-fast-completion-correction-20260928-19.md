# Layer-B fast-completion bounded correction 19

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. Bind packet18 SHA256
`f30561ea725dfd5afb3ecfef43c24d46b3f98c0e4b8c2dbd95dbc894e2df3375`
and its `FAIL_FAST_COMPLETION_PACKET` review. All packet18 requirements remain
unchanged except the exact corrections below. No command is released until the
combined bytes pass fresh independent review.

## Lossless command-boundary authority

The pre-submit evidence retains the literal systemd-run argv as a JSON string
array, including each complete `--property=ExecStartPre=...` as one element.
Exact argument boundaries are established by that retained array, the pinned
systemd-run binary and the reviewed systemd v245 property parser/append semantics.
`systemctl show` is not a lossless argv oracle: use `ExecStartPre` and `ExecStart`
only to confirm the two ordered rendered commands, the unchanged rendered main
command and their statuses. Never claim that its space-joined rendering proves
argument boundaries. Any retained literal-argv mismatch, parser-version/hash
mismatch, missing/extra/reordered rendered command or unexpected status fails
before marker publication.

## Exact barrier timings and publication semantics

Change the first pre-command to the literal single property argv element
`--property=ExecStartPre=/usr/bin/sleep 20` and change the existing service
property to `--property=TimeoutStartSec=40s`. The second pre-command remains the
literal single element
`--property=ExecStartPre=/usr/bin/test -f R/logs/identity-bound.json`.
The 60-second observation deadline remains measured from immediately before the
single `--no-block` submission. A late observer is allowed to fail closed before
gcc; it is never retried.

After retaining the valid start-pre identity response, raw mapping and pending
marker, run exactly these operations in order, each with raw argv/streams/status
and monotonic start/end retained:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/sync -f R/logs
/usr/bin/timeout --signal=TERM --kill-after=1s 1s /usr/bin/mv --no-clobber R/logs/identity-bound.pending.json R/logs/identity-bound.json
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/sync -f R/logs
```

Before each command require that its nominal timeout plus one-second kill
allowance fits entirely before the observation deadline. Failure, timeout or
insufficient remaining time before rename leaves the marker unpublished and
enters cleanup. Marker publication occurs at the atomic rename, not at the
post-rename sync. An ambiguous/timed-out rename or any post-rename sync failure
must assume the marker may be published and gcc may have started: latch failure,
query the prebound identity and enter the same independent 30-second cleanup,
including group kill on ambiguity and recursive original-path reconciliation.
Never repeat rename, recreate a pending marker or submit again.

The first pre-rename `sync -f` is a syncfs operation over the filesystem
containing the closed raw identity/mapping files and pending marker. The second
sync makes the renamed directory entry durable; its success is evidence-only,
not the instant of authorization. Verify both source and destination marker
paths immediately before rename: pending is the exact prehashed regular file,
destination is absent, both parents are the exact mode-0700 root/log directory,
and neither path has a symlink component.

Packet18's identity predicate, exact compiler command, terminal predicates,
failure classification, cleanup, provenance/object inspection and non-releases
remain unchanged. This correction releases no compile, link, owner, M02/M03,
guest or acceptance operation by itself.
