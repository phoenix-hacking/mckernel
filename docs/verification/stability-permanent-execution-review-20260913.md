# Permanent-backpressure prerequisite execution review

This review authorizes a controlled **permanent-backpressure (mode 4)**
prerequisite run using the exact inputs bound by the accompanying JSON record.
It requires controller profile `owner-phase-v2`, payload profile
`runnable-thread-v1`, the reviewed mode-4 module build, and the unchanged
hard-profile baseline launcher, McKernel image and pinned Linux kernel selected
by the preparer. Catalog execution, the other two fault modes and production
acceptance remain disabled by this review.

The final preparer is SHA-256
`0b45f00a6ed72b8b55b25f27261650e14b32e43e398ee2005ffeb5a16ac78d82`;
the runner is
`35095ee65a57638c93179e20433c68ce9688978f201317a0b1cd98ab591ec50e`.
The released contract is byte-for-byte equal to the preserved draft,
SHA-256 `fa5bbb142f3842908eb0a71f9834f1f1477e57049feddeb6dbc6c717b4649f8c`.
The controller and payload remain the previously reviewed, compiled v2
controller and runnable-thread fixture. Their source and output identities are
bound separately in the record.

The original reviewed preparer `e64dc3` failed preparation attempt 1 before any
guest: it assumed a fresh `owner_parser_tests` count, while the mode-4 build
explicitly reused unchanged parser evidence. That failure, original source,
first independent review and corrective delta remain retained. The corrected
preparer verifies the exact prior build record and its single successful
`owner-parser-tests` collection, raw wait zero, completed cleanup, complete
untruncated streams and their hashes. It compares both original and mode-4
retained parser/test source bytes and records the reused 19-case proof
separately. The fresh-count path is unchanged. This is reuse of existing
infrastructure evidence, with no claim that those 19 cases ran again.

The mode-4 contract requires:

- The original delegated read of 16 bytes, selected worker, delivery, request
  arguments, response claim and actual OS generation remain bound across the
  complete phase observations.
- Response address access counts are 0, 1, 1 and 1 across BlockedRead,
  AcceptedReturn, Terminal and TerminalPlusFive. Payload-copy and release
  counts remain zero; the selected completion and original production timer
  remain retained. Both complete terminal inventories and counters match.
- At least one injected retry occurs, with no real send, publication or
  notification failure. Native runtime/application transport error is -110;
  actual RET is -71 with accepted bit 1 and value 16. These distinct results
  must remain separately recorded.
- RET leaves no earlier than `(original publication_since + 5) * 1e9` in the
  native monotonic clock and within the unchanged 15-second RET limit.
  Retries never reset the production timer. New admission fails with errno
  110. Original controller, cleanup, host and QEMU deadlines remain in force.
- The v2 controller observes the original launcher waitable with `WNOWAIT`,
  its original start ticks and both actual stream EOFs before Terminal. Both
  terminal application rows must be closed and quarantined. The complete
  inventory equality requirement is unchanged.
- PRE_INPUT physical evidence still requires status 0 and wake 2 before any
  input ACK. Terminal evidence requires the retained response with wake 1,
  status 0, result 16 and selected servicing TID. The physical comparator must
  independently prove original-request/ring binding, only allowed response
  field changes, no selected wake publication, and exact response equality
  five seconds later. Emergency capture never reads the selected response.

The preparer and runner continue rejecting modes 2 and 3. Their postpublication
collectors require separate review; an original response must never be reread
after publication or release. Injected EAGAIN does not verify an actually full
physical ring, which remains a separate gate.

Root's [compiled stack comparison](stability-permanent-stack-review-20260913-1.json)
reports the same seven measured module paths as hard module 3: worker/mailbox
5512 bytes, ioctl/mailbox 5832, worker/application rows 2992, ioctl/application
rows 3312, RET entry/leave 704 each and RET selection 560. Its exact record and
nine-member archive are hash-bound here. These are selected compiled paths.
The inherited direct initial Linux formatting prefix adds up to 797 bytes to
the relevant printing path; it stops before dynamic formatting callbacks.
Alternate printk formatting, console descendants, entry/lock/scheduler paths,
interrupts/NMIs and deeper RETURN handling remain outside the measured bound.
The 16384-byte Linux thread stack is not certified by these partial sums, and
this review supplies no runtime stack watermark.

Execution authorization is limited to collecting this prerequisite evidence
with successful source-bound preparation/preflight and the existing isolated
run controls. All original failures must remain unchanged. A fresh guest and
independent physical, provenance, raw-outcome and owner review are required
before any mode-specific acceptance decision. This publication makes no
transport, application or production acceptance claim and runs no compiler,
test helper or guest.

The [execution/source-retention record](stability-permanent-execution-review-20260913.json)
preserves complete candidate and independent review trees, the preparation
failure and correction, exact release-copy identities, and scoped build/stack
evidence. Older hard and draft artifacts remain immutable.
