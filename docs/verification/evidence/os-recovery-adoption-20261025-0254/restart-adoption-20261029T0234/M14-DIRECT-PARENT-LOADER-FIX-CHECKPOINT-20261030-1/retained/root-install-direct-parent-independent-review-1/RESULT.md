# Direct install parent and child focused review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only review. No execution, test, root, install, native operation or
admission. The independent caller's actual reservation remains necessary.

Reviewed parent frozen source manifest FROZEN-SOURCE.json (055414d...),
root_parent.py ac14d51077081666d283a899748117e73665c5d1f68a8683745c152637374f81,
BOOTSTRAP.py 2603905f5b44dd5f3caf5d6d17e5e27585eb35d1b973a2ec485e783be0694478,
profile 75011886c2593e34aa423df6a4bb0db9b804106a3cc497aeb25ac403eb3310c4;
child SOURCE-BOUND.json 7dcb607af2a8727923bf8960a5147c4df0ca820724ea3be88b62744f51c4beea,
entry e4de5d1022ac5cabe269355d7d5d75f143dd2e6913ff5bc48b7d780dca59c9e5
and issuer 37fa89049de7167e276c3e1dc424454288a1033ed1b7c4bac1ca8a068af3ef92.

NO-GO pending the bounded correction:

1. Parent fork_and_pin can retain an actual keeper pidfd and then fail before
   tuple assignment (for example, while reading birth). Parent error handling
   uses only local keeper_fd/keeper_pid, which remain None, and never tries
   stopping/joining a usable retained handle. Use the preowned child record
   when its pidfd is positively verified. Unknown pidfd disposition and an
   absent handle remain UNKNOWN; never fall back to numeric PID signals.
2. Child _stop_unhanded checks only record.pidfd is non-None. The shared
   fork helper also stores PidfdVerificationError.fd in that field, then marks
   the record UNKNOWN. Distinguish a verified pidfd from this retained but
   unverified descriptor before signaling; retain the latter UNKNOWN without
   using it. Exercise the real exception boundary in a mock regression.
3. BOOTSTRAP.py's final DATA record appends source literal '\\n' (two
   backslashes) rather than a newline byte, so the captured line protocol is
   malformed. Verify the actual emitted bytes in a regression.

Positive source findings: seqpacket uses per-message SCM_CREDENTIALS rather
than pre-fork SO_PEERCRED. The corrected child transfers an installer pidfd
before READY, checks pidfd and parent channel while awaiting READY, and uses
canonical-byte comparisons for the ACK. Parent holds the transferred same-OFD
lease, compares its inode with the sealed release, independently checks GO and
result, waits for keeper and requires installer terminal evidence. A configured
alarm supplies best-effort ordinary interruption; uninterruptible I/O and
unobserved death remain UNKNOWN against the actual external reservation. This
is not proof of global descendants, native current-free, cleanup, or release.

Test suitability: parent test_parent_source.py e40095a36dfb9b0a7df9c01a7640d05affcbd3d14dd8ec3752b39bf91d76abf2
TestProfile (one) and TestRetirement (three) are mock/read-only cases. Child
test_direct_model.py 04dfd3bfba69170e25b3147252e0e81ea94cec61f6d633ece2d2c0129b250d80
(six) and test_direct_ack.py 64e2243030ab11ada5e94a202b2aa722e899a7644668ef1db2c281c869d3bd85
(seven) are suitable for ordinary CPU6/512MiB, Python -B: the latter performs
real bounded reads/hash checks of pinned local source and uses pthread_sigmask,
but tests do not create real children, use pidfds, send signals, or run root.
These tests are unrun here and do not cover the failure cases above.
