# Caller nonterminal wait correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This source-only successor preserves the frozen caller 39e7, parent4, R2 proposal,
helper and all existing results. The sole driver change names the `waitpid`
return `waited_pid`, so WNOHANG returning zero cannot overwrite the independently
supplied actual resource-input dictionary before the next supervision pass.
The direct wait, capture, resource checks and UNKNOWN handling are unchanged.

The entry and profile point at this exact new driver. The prior operation review
binds the older driver; an independent reviewer must bind these changed bytes
before any actual operation. Existing parent4, R2 and helper bindings are reused,
not reapproved by this packet. No test, sudo, root or workload was run here.
System Python 3.8.10 compiled the three Python sources to code objects.

After Root's existing light-test admission, the single new mock regression is:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-caller-wait-correction-1/test_wait_nonterminal.py
```

It drives the actual `supervise` function with mocked ready pidfd, waitpid zero
then terminal, resource observation and capture, and asserts the actual input
mapping survives both passes. Previously passed tests are not rerun by this
command. No native acceptance, current-free or operation release is implied.
