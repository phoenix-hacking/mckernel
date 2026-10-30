# Deferred child restore probe review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source-only review of probe d5ef6e3baffe5bbcfbb7df3730726f37434752472d205d43b85217ba1b253a3c
and profile 6ba27b67ad24019964e94cc531789f426ee349ddac49a6c6a189c9acfec6a239.
No test or process was launched by this reviewer.

NO-GO for this exact source:

1. Lines 137–138 send the child's gate byte after callback DATA without first
   requiring successful parent pidfd capture and identity verification.
   fork_and_pin can fail while the child still reaches the callback.
2. Line 160 closes the child pidfd even if terminal and direct wait are not
   positively observed. An unjoined child must remain UNKNOWN with actual
   owner/handle retained; uncertain close is never retried.
3. Child PID/birth are emitted only in the final result. If the foreground
   timeout or configured stop interrupts before then, the external owner
   cannot rely on the output to identify the actual child. Emit a bounded
   pre-GO child identity and verified-pin disposition before allowing the
   child to proceed; report incomplete pin truthfully and retain UNKNOWN.

The probe loads the hash-pinned production DeferredFork and uses a reporting
subclass around the same _restore body, with SIGALRM blocked and configured
handlers set. Its result would be a scoped UID1000 reproduction, not proof of
the earlier root keeper's failure. The profile's timeout --foreground does not
prove descendant termination. Original UNKNOWN four-GiB and all native
ownership remain held; any successor needs its own bounded source review.
