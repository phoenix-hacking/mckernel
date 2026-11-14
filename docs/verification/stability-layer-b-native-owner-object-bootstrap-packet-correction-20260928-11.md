# Layer-B native-owner object bootstrap correction 11

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the single bounded
correction to packet10. It binds packet10 SHA256
`b65c345bc8b15e6043bf0ae728d23e0cba895dcfbf3ad383160011094900acbd`
and its failure review at
`docs/verification/stability-layer-b-native-owner-object-bootstrap-packet-review-failure-20260928-10.json`.
Everything in packet10 remains unchanged except the include-root inventory rule
replaced below. No compilation, systemd operation, linking or owner execution is
released until the combined exact packet passes fresh independent review.

## Non-following include inventory

Walk each of packet10's three explicit include roots using `lstat` semantics.
Never follow a symlink while recursively enumerating a directory. Deduplicate
overlapping spelled entries by `(device,inode)` only after retaining every
spelling. For every regular file record spelling, canonical path, type, mode,
UID/GID, size and SHA256. For every symlink record spelling, literal target,
each resolution hop, final canonical path if resolvable, and whether that final
object is within an approved root.

A symlink whose final target is a directory outside all approved roots is an
`EXCLUDED_EXTERNAL_DIRECTORY_LINK`. Record it in the baseline, but do not descend
through it and do not hash its target tree. Its mere existence is not preflight
failure. Broken links and symlink loops are also recorded and not followed; they
become failure only if the compiler reports them as an actual prerequisite or
the controlled include search otherwise consumes them.

After a resolved compile, parse the dependency file exactly as packet10
requires. For every spelled prerequisite, reconstruct and retain its complete
component-by-component symlink resolution. Reject the attempt if any prerequisite:

- traverses an `EXCLUDED_EXTERNAL_DIRECTORY_LINK`;
- resolves outside all three approved roots, other than the exact source;
- is absent from the non-following preflight baseline under its approved-root
  spelling or changed in type, identity, size or SHA256;
- is broken, cyclic, duplicated incompatibly, or omitted from the post-check.

Thus unconsumed Python/NumPy, OCaml, MPI, Clang or other external directory links
may coexist in `/usr/include`, but no header reached through them can be silently
excluded. Do not expand the approved roots in this attempt. Retain the complete
excluded-link inventory and the consumed-prerequisite resolution table as
evidence. The `.d` file remains preprocessor prerequisite evidence rather than
a general file-open trace; all other packet10 limitations remain explicit.

This correction makes no claim about compile success. It preserves packet10's
single submission, exact compiler argv, active/exited capture, immediate stop,
independent cleanup budget, group kill/reconciliation, ET_REL-only inspection,
first-failure retention and non-releases without modification.
