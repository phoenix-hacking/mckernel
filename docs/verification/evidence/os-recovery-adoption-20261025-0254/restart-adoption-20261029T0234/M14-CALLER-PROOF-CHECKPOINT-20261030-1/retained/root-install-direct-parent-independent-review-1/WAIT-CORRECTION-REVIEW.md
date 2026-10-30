# Caller wait correction and operation review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. This is a scoped source and install-only operation review; no
privileged operation, nonce consumption, native run or gate release occurred.

The exact driver successor 1a42c4a660e719cd0b06f40b95eecb0b61305be4d9b8b592cfcc50fbc897ee10
differs from predecessor 1e6baa7f88f4d371c272312b8a159d5391913b8d572015257d90b9d5b1e13d4d
only by replacing three wait-result references with waited_pid. A nonterminal
WNOHANG=0 no longer overwrites the actual resource-input dictionary before
the next supervision pass. Existing direct-wait and UNKNOWN paths are retained.
Successor entry 31779722a7d57f486c3b5e2e22b44f0ac1b06fd29289f946bf784bd4ca73eb69
and profile c8a37081c472f0ebe529cbcb04d45034c5d22231f1fa2a74d42e4a36b67495b4
bind the new driver; successor manifest is
282f4489226b7e13f0d65b0ae3a5845c86b1a3636cdc65c7f65e34bb88a50175.

Root reports the distinct caller-wait-0001 synthetic regression PASS, one case,
exit 0, 0.06 seconds wall and 20020 KiB, with positive terminal and empty owned
group. It mocks the wait and resource observations; it is not a root operation.
Prior 15 integrated and nine helper cases remain their exact predecessor evidence.

The adjacent nine-field JSON rebinds the accepted Parent4/R2/child operation
review to this driver. Conditional operation-only lease retirement requires
the same full proof, capture, positive waits and disposition checks. Root must
still supply fresh actual usage, live controls and inherited caps, CPU6, real
resource/broker accounting, exclusive private reservation and capture, a fresh
nonce and positive caller-session join. Every unobserved or uncertain outcome
remains UNKNOWN and charged without replay. Native current-free remains UNKNOWN;
native12, V2 UNKNOWN 2 GiB, scratch21, mutex27:4, held exec work and all
native/source/effective-view gates remain in force.
