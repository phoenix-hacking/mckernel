Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded source correction for first actual21/23 mcps result. Original candidate, fixture-output, raw stderr and whole-join history are unchanged.
Rust adds libcstrsignal and notifications for the two observed foreground-child wait statuses. Runtime child PID and invocation name are used; the command representation is the original script line10, not a test fixture payload. No new subprocess or signal-disposition change.
All23 original cases, original Bash source and stub are copied byte-for-byte. Existing BASE resolves to this additive directory, which supplies new source/output bindings. No test/normalization/oracle changes.
This is not all-profile signal parity: SIGINT/SIGQUIT/SIGPIPE/other signals, ignored/blocked signal inheritance, parent-directed signals, core-dump messages and non-C locale remain unqualified. Root must retain that boundary even if all23 later pass.
No compiler/fixture/root/Docker/guest/device execution occurred for this correction. No new grant has been consumed.
Next exact argv after a separate CPU0 grant:
/usr/bin/python3 -I /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-mcps/signal-diagnostic-correction-1/fixture/run_equivalence.py --execute --cc /usr/bin/cc --rustc /home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc
