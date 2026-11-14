# Functional M14 validator owner lock-order correction

Status: SOURCE ONLY; UNREVIEWED; NOT RELEASED. Exact private sources and tests
are bound by `SOURCE-MANIFEST.json`; `SOURCE-DELTA.patch` is the adapter-only
change against `../expert-disposition-source-1`. All predecessors remain intact.

Constructor progression now acquires the operation lock before the session lock,
including duplicate adoption, pidfd acquisition, authentication and data
publication. It checks that the registered operation and descriptor records are
still live inside and after the configured-stop guards, and before and after data
publication. Revalidation likewise takes operation before session, checks the
sticky owner and both records before work and before returning data. UNKNOWN,
closed, or ambiguous custody cannot be accepted as a live session. The separate
close path retains the same outer operation lock and nested record order.

Synthetic tests target a reentrant UNKNOWN while pidfd guard restoration returns,
UNKNOWN contending with actual-adapter revalidation on another thread, and a
reentrant UNKNOWN before revalidation returns. They are prepared but UNRUN. The
previous six callback tests passed only under the prior exact source binding and
are not evidence for this changed adapter or its successor imports.

The diagnostic stdout DATA schema retains its explicit new 2 MiB serialization
limit. A byte limit does not bound elapsed output: a separately reviewed actual
external watchdog and capture owner are prerequisites. Existing collector,
profile, source-binding and effective-view refusals remain closed; no physical
source, graph, nonce, current-free, owner, execution or acceptance facts follow.

`/usr/bin/python3` 3.8.10 AST parsing passed 19 files and the three embedded loader
programs. No tests, fork, signals, pidfd syscall, root, mount or workload ran.
After independent review and Root admission, proposed synthetic checks must use
separate interpreter processes:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/lock-order-correction-1
/usr/bin/python3 -B -m unittest -v test_actual_close test_validator_consumer test_lock_order
/usr/bin/python3 -B -m unittest -v test_callback_handoff
```

These commands do not supply an operation or native execution release.
