# Stage-test retention correction

The 18 staging tests now preserve the exact owned symlink and FIFO objects in
each failed-input fixture directory. Their journals retain lstat mode, type,
path and symlink target, and the tests check the objects remain in place after
the expected bounded rejection. They perform no unlink cleanup.

This supersedes the special-object cleanup paragraph in the first frozen
`harness.md` (SHA256
`3445618283ef4242d4053450cde18e5c746de2e84bec879cead12ba62a4cb9eb`).
That document and all native-harness inputs remain unchanged while root begins
their separately reviewed pinned validation. The original stage-test source
with cleanup is retained in the author and independent review captures.

Root's archive verifier handles these objects through lstat/readlink and tar
metadata without following symlinks or opening FIFOs. Preserve the complete
tree, including each special object, so the original negative fixture can be
restored exactly. No stage test has been imported or executed by the author.
