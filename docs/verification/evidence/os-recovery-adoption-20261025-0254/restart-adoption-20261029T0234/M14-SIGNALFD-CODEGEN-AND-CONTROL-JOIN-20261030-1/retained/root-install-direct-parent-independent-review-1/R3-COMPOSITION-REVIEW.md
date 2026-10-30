# Parent5 and R3 diagnostic composition review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Scoped source review only; no test, root operation, fresh nonce,
admission or native/source-view gate release by this reviewer.

Parent5 manifest c263dbe6bf124a3c0a62f9bd5bf200c9ef9fdea2bd71367847e07cd4c7a1f55c
binds root parent 4acd57e90c1c38fc505960fcef34942e06ca5d7d62b7c8b2942f1aa16497d548,
byte-identical to the reviewed failure-data proposal. Its bootstrap
96f4c1496230b4de86a2edf2bfcd6318c9df0c2ddf9d57b5ee8ca04a31c61cda
binds that body and unchanged child/helper. Its 22-argument parent profile
contains the exact bootstrap bytes.

R3 manifest 0bf6efc6c37f4494aced75bf56f2375c1eec814e3076999ecc8c4adc68b879a8
binds caller 26773c48196cd134cbd74d71681a95520bf43b6c5657e75acfcd648b0ee1f66e,
entry babeea4528e631241582d6b71cb84d924dc4f6b42453dd6d1ebe3a5e25e59f1b,
and proposal 1d6014fefb67529626bf4f1c49153dbab52e55700a4474762f0eac4f812041d7.
The caller entry in its profile is byte-identical to the source. The caller
preserves the reviewed role and wait fixes, excludes both retained old nonces,
requires additional_reserved_bytes >= 4 GiB, and rejects a total above the
22.5447 GiB shared ceiling. With exactly 4 GiB retained, native12 + V2 UNKNOWN2
+ old UNKNOWN4 + new operation4 = 22 GiB, leaving about 0.5447 GiB for other
separately charged reservations. Fresh actual accounting and broker overhead
are still required.

The diagnostic objective is best-effort. The selected child callback cannot
report an exception from deferred_fork._restore(True) before the callback is
entered, and phase0 may catch a post-mutation exception internally. A missing
note has no success meaning, and the old keeper's first cause stays UNKNOWN.
The four failure-DATA and one role mock cases are predecessor evidence only;
the R3 resource mock was not run by this reviewer. The known old control
processes were joined, but the old operation and its 4 GiB remain UNKNOWN.

No source defect identified within this composition scope. The planned real
unprivileged restoration reproduction, independently reviewed fresh actual
admission, new nonce, real caller/session custody and all existing source,
effective-view, native/current-free and physical gates remain separate.
