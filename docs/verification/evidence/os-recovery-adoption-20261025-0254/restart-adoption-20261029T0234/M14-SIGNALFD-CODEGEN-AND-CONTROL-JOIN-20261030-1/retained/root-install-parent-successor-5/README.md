# Parent5 diagnostic successor — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The parent body is byte-for-byte `root-install-failure-data-correction-1`'s
source proposal. It adds bounded one-attempt failure DATA on the existing stderr
capture, including the keeper child callback's exception before exit. Unknown
state and all original stop, lease and DATA gates remain unchanged. The paired
bootstrap and profile bind these exact bytes and the unchanged child4/helper.

The original failed operation, its nonce and its 4-GiB UNKNOWN reservation remain
preserved; this source neither diagnoses nor fixes the keeper's underlying cause.
Root separately owns independent review and any fresh diagnostic admission. The
four failure-DATA source tests passed only for the byte-identical proposal; no
new test or physical operation was run in this composition.
