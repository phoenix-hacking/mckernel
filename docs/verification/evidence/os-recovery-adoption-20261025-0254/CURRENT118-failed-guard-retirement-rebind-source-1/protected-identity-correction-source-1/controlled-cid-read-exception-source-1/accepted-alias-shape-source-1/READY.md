Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The two concrete pre-effect identity defects are corrected together. The original
failed owner2232651/b103343097/FD4 remains untouched; there is no owner-retirement
or container-cleanup authority in this packet.

The original3fdb `file_identity` explicitly excludes atime. Its current caller,
profile and release add no atime predicate. Root explicitly authorized the same
ordinary-read method already used for fixed Python3.8, scoped only to the exact
retained root-owned CURRENT118 `OUTPUT/container.cid`. The callback clones the
authenticated original identity function into a private namespace, extends only
that exact read-flag condition, and leaves every original dev/inode/mode/UID/GID/
link/size/mtime/ctime/hash/bounded-regular/no-follow/FD-versus-linked-node/finally
check intact. No shared module/global flag or arbitrary fallback is changed.
No privileged metadata child, permission change or operator privilege is added.

The full read-only callback then exposed a separate publication-shape mismatch.
The first row is `FINITE-REVIEW-HANDOFF/physical.CHILD-STARTED.json`,514B,
dev66306/inode1206855,UID/GID1000,mode0400,nlink2. Its exact retained second name is
`physical.CHILD-STARTED.json.complete-source-2221578`, on the same inode and times.
Original published `handoff_common.py`1afec85a `atomic_json`42-57 opens the complete
source with O_EXCL/mode0400, writes+fsyncs, publishes via `os.link(tmp,path)` and
explicitly retains both names. The original actual Root publication and reviewer
bindings both pin this exact source. Thus this node's accepted contract is the
known two-name publication, while the historical generic nlink1 shape is inapplicable.

One fixed contract binds only six already-declared canonical/complete-source pairs
from that same accepted writer: physical/held CHILD-STARTED, physical/held COMPLETE,
PREWARM_READY and independent PASS. Each pair has exact names, original SHA/size,
dev/inode/mode/owner/link count and mtime/ctime. Its reader changes only the expected
link count from1 to exactly2 in a private clone of the original function and runs
all unchanged FD/read/hash/linked-node checks for both names. Any third name,
symlink, substituted inode, byte change or metadata/time drift refuses. The other
56 protected rows keep the historical shape checks. No file or alias is changed
or deleted. The original128MiB limit remains; all62 declared files fit it, including
the18401808B Rust object and10285416B image. No per-file limit increase is needed.

The used200fd90e release, failed2247306/2247305 positive joined1, stderr5027ce41,
original417/f3b failure and UNKNOWN first-client status remain preserved. The
earlier full-callback refusal is retained in ACTUAL-FULL-CALLBACK-REFUSAL-1.json;
the unselected privileged draft remains unchanged in the parent directory and
was never executed. No source gate is weakened to hide that history.

Validation:

-27 pure tests PASS under `/usr/bin/python3.8`, including all16 protocol tests,
  exact CID read-flag regression, every stable metadata/time field, bounded regular
  shape, original real publisher two-name fixtures, wrong alias/third-link/symlink
  refusal, and unchanged pidfd/lock/guard/transaction functions.
-Actual exact CID-only read PASS as UID/EUID/GID/EGID1000 under Python3.8:
  predecessor receipt26b6a6fb. This records an ordinary read of a root-owned CID,
  with all original stable fields unchanged.
-Actual FULL62 protected-input callback PASS under that same declared interpreter
  and UID, after actual guardian/earliest-cap checks: receipt4caf12c3. All six exact
  publication pairs and original other-file predicates passed before any target
  process query, pidfd, signal, lock action, Docker operation or cleanup. This
  source preflight creates no native/current-free acceptance or release.

`MINIMAL-CORRECTION-DIFF.patch` is against reviewed4ed5a02f. Kernel syscall434/424,
fdinfo binding, exit poll, same27:4 sequencing, quarantine, deferred stop sharing,
current six-controller denylist and parent actual-join contract remain unchanged.
The sole portable converterc895898a is reused.

Root next fills ROOT-RELEASE.TEMPLATE.NOT-AUTHORITY.json with the actual current
operation, fetched source checkpoint/publication, independent source and execution
reviews and fresh admission. The old release/output must never be replayed.
Only Root may execute the same CPU0/2GiB fixed command shape against this source in
a fresh namespace after that release. Same06:00Z/boot/credit caps apply. Completion
remains pending actual parent2232650/tool90401 join and fresh current proof;
the ordinary stopped container and all build artifacts remain retained.
