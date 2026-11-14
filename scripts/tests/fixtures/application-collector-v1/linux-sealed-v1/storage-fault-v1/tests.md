# Storage-fault-v2 source tests

This is source-only infrastructure. It does not release a build or root run.

- Bind the exact collector, packet, header, generated source and complete diff.
- Require guard value one, selectors 0–6, target-only operation adapters and no
  global syscall replacement.
- Require packet schedules 22/10/17/22/17/22/17 below the hard bound 32.
- Validate READY sequence zero and exactly one RELEASE; ordinary records begin
  at one and receive durable ACKs.
- Validate distinct BEFORE/AFTER/BIND acquisition schemas and legitimate reuse
  of retired numeric descriptors.
- Prove collector-origin REAP, three EOF, CLEANUP_READY, CLEANUP_FINAL and one
  bounded SETUP record before report creation for post-fork selectors, with none
  fabricated for pre-fork selectors. SETUP carries all 48 child words, collector-held
  cwd, stdout/stderr FIFO and executable-backing identities, seals and leader birth;
  the oracle requires exact joins (not synthetic device/inode constants).
- For report-absent selector 4, independently bind request, selected input, decoded
  argv/env, events, exact retained executable bytes, stdout/stderr/setup and the
  complete SETUP/child/REAP cleanup join.
- Prove selector 2/6 retains exactly `41435251303030` and its independent hash.
- Prove fresh-root rejection is stable and leaves all existing bytes unchanged.
- Bind the supervisor, owner and oracle source bytes in preparation. Mock its
  SIGCHLD/subreaper sentinel, exclusive owner wait, one-MiB dual pipe caps,
  identity-safe direct/adopted retirement, 5/220/22/248/33-second arithmetic,
  exact result union and publication rollback without launching a process.
- Require the outer raw supervisor wait to be exact integer zero before any
  evidence read, then join its captures, owner-result/witness/error hashes,
  owner PID/birth/wait, terminal empty scans and ECHILD before owner semantics.
- Start every oracle negative from a fresh valid fixture and mutate one distinct
  field: selector/wait; sequence/seam; identity/hashes/nonce; prefix; report
  presence/durability; EOF/reap/ECHILD/cleanup; first versus secondary failure;
  journal truncation/extra/oversize; and file/parent fsync state.
- Mock compiler, build, root, collector and payload execution. Passing these
  checks earns no storage-fault, application or production acceptance.
