# Install-only actual preparation (source draft)

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This packet is source-only and has no execution release. It consumes the exact
`root-install-resource-admission-1/RESOURCE-ADMISSION.PROPOSED.json` digest
`967e90918dae189ecc92fcec4da6d16bf1894235ce4d8a85858c3c3ced04089b`;
that document is a proposal, not an operation admission. No root operation,
nonce consumption, installation or source freeze has been performed.

`prepare_install.py` expects fresh actual values and an independently reviewed
operation-review file, both selected by Root. The proposed actual-values JSON
schema is the exact key set in `bind_actual`: version 1, status
`ROOT_ONE_SHOT_ACTUAL_VALUES`, proposal and operation-review SHA-256, fresh
observation and expiry in BOOTTIME nanoseconds, actual included-only usage and
UTC observation, service status, the four bounded BOOT/MONO/UTC/phase-one and
receipt-expiry clocks, join/escalation reserves, the actual owner-release value
and its canonical SHA-256, other committed memory bytes, and external-watchdog
process identity. These values are DATA; their text or hash does not confer
approval. Root must obtain the real actual usage, review, issuer-owned intent,
nonce custody, live control facts and available external owner separately.
The owner-release keys and their exact constraints are in phase-zero `run`;
they are not generated here. Uncertain or consumed nonces may never be retried.
The preparer fails closed on missing/stale actuals or changed actors/controls,
and checks live storage/memory and exact profile prefix and entry bytes. It
writes an exclusive caller-owned attempt directory with canonical stdin, exact
argv, source bindings and caller identity; it does not write under `/var/lib`.
The attempt directory itself is the exclusive unprivileged consumption marker.

Preparation syntax, once Root supplies actual files and review, and after source
review, with a fresh private 0700 caller-owned existing output parent:

```
/usr/bin/python3 -I -B PREPARER --actual ACTUAL_FILE --actual-sha256 ACTUAL_SHA256 --operation-review REVIEW_FILE --operation-review-sha256 REVIEW_SHA256 --output-parent PRIVATE_DIR
```

Replace `PREPARER` with this directory's absolute `prepare_install.py` path.
The exact root argv and stdin are written to the private attempt directory.
The command does not start sudo. `--execute` is deliberately closed: the
operation review is pending, and the source adapter is not a live owner. No
new grant or claim of current-free, native acceptance, source exclusion,
effective mount view, or zero remaining descendants follows from this packet.

`external_watchdog_adapter.py` is a proposed adapter for an already admitted,
root-owned process and root-owned per-operation journal, using a caller pidfd
and authenticated Unix peer. It adds no process and preserves UNKNOWN on
observation loss. Its event loop must be supplied by an actual existing owner;
none is known to be instantiated. It does not stop an outside-group keeper,
does not itself validate the authority of a review file, and must not be called
an established bounded watchdog or a release. The existing root GNU timeout
covers the installer group, but not the outside keeper. A separately reviewed
actual mechanism that retains the operation OFD/resources and handles bounded
keeper supervision is still missing; if it cannot prove completion, UNKNOWN
must persist. Source hashes, proc liveness, UID-1000 caller, a JSON status, and
this proposed adapter are not substitutes for that mechanism. The root owner
must use trusted loaded module bytes, actual independent review and controlled
journal custody; those bindings have not been independently verified here.

Next: review this exact source and Root's operation proposal, establish the real
external keeper/owner capability without a new ungranted role, then bind fresh
usage, actual one-shot intent and review. Only an independently reviewed
successor can release the closed execution path. The caller must capture any
failure/uncertainty and retain its nonce, lease and resource ownership.
