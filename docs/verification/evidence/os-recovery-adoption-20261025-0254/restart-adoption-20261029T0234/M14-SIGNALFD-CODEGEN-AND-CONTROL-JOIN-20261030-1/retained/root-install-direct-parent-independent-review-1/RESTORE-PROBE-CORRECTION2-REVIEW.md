# Deferred child restore probe correction 2

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Scoped source/profile review only; no test, real fork, root or native
operation was performed by this reviewer.

Manifest 0514167ca9adcbab25b5ea6ab9a5e60fcff20d870fb3eaba86f05eca9e374c25
binds probe 3b927a1b7773762ef6ec40e5b3dddfb219c310530b5e418d3b8a704ab8d6b872,
profile dfab3052f0493587ae2a1465bd2b067c2ad7756a366969e9bc752354f28b38ed
and six mock tests 310d0e153d9e375fef508cf50ece4ce0745e775f2c65a2458c464d0503695b0f.

The child closes its own inherited gate writer once before callback reporting,
so withholding GO allows EOF. The parent verifies actual live child
PID/birth/parent, pidfd identity and CLOEXEC while the child is gated; it
publishes and fsyncs bounded PRE_GO custody before sending GO. Guard, identity,
or publication failure prevents GO. The verified pidfd is closed only after
positive pidfd terminal and direct terminal wait; uncertain outcomes enter the
retained UNKNOWN path without numeric signaling or retry.

Scoped source/profile PASS for the exact one-child UID1000 ordinary-profile
probe, conditional on the six mock checks, fresh resource/control admission,
exclusive capture and actual external owner/join. This is a test of the
hash-pinned restore body under the specified mask and handlers, not evidence of
the earlier root keeper's actual failure. If PRE_GO publication itself fails,
that output cannot supply the child identity. The external owner must preserve
actual live custody and the 512-MiB allocation on any incomplete evidence;
timeout --foreground does not establish descendant termination. Existing
original UNKNOWN four-GiB, native12, V2 UNKNOWN two-GiB, scratch21, mutex27:4,
native current-free and all physical gates remain unchanged.
