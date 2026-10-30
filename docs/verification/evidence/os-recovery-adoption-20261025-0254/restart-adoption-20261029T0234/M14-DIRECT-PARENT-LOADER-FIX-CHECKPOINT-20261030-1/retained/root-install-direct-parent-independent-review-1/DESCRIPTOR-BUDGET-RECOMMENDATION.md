# Bounded descriptor exhaustion diagnosis

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. No tests or physical operations performed by this reviewer.

Actual direct-parent-child-0002 failed with EMFILE in direct_entry.verified()
while opening WAIT-INSTALL-CODE.py at the existing nofile=128. No cases ran.
It is not evidence of a Unix access error. The source opens root and each
ancestor with held_open() for every separate source, retaining all of them in
HELD. The same common ancestor chain is duplicated for each source. The
bootstrap, phase0.open_dir() and install_source_closure.open_exact() contain
related accumulating traversal patterns. Parent completion also holds the
23 independently verified file descriptors; the three process roles have
distinct FD tables after fork/exec and must be budgeted separately.

Minimal engineering direction: walk from a pinned starting directory with
descriptor-relative O_NOFOLLOW opens; pre-register each new FD under configured
stop deferral; check its identity and open its child before closing the old
temporary directory exactly once. Record uncertain close as UNKNOWN and never
retry a potentially reused number. Preserve all leaf/source descriptors needed
for execution, revalidation or ownership, especially the installer source FD,
and preserve operation, receipt, lease, pidfd and socket ownership. Recheck
named ancestor bindings at the later point that requires a live path claim;
holding an inode and proving a later path are different observations.

Use the existing nofile=128 light profile for a new non-replaying regression
that imports the real pinned loader with a fixed baseline of occupied FDs,
records live/peak counts, verifies the retained installer leaf and source
hashes, and injects open, close and deferred-stop failures. Exercise the actual
single-close UNKNOWN behavior. Separately measure realistic parent, keeper and
installer phase peaks at the unchanged production nofile=256, including the
proof leaves and inherited FDs. A mock or source count does not by itself
establish an actual production peak. Do not widen either limit or replay an
unchanged failure.
