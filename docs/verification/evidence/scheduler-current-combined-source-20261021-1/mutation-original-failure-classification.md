# First mutation fixture failure classification

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: FAIL_STOPPED_PRESERVE_ALL, confirmed. The first mutation fixture ran
two successful object compilations, then its third command (host link) exited1.
The16-case executable was never run: zero mutation comparison cases passed.
Three recorded command rows are not three successful commands or a fixture pass.

Exact link stderr states that actual-c.o's main at actual.c:57 has an undefined
reference to __inline_memset; collect2 reports ld exit1. The retained362-byte
stderr SHA256 is `798601aac871fac6452fabfdb689471b713dee99e1ddc237c7d325a40f828707`.
That location is fixture initialization, not the extracted scheduler mutation.
Classify this as the fixture/kernel-header inline-memset provider linkage family;
the trace supplies no C/Rust mutation semantic result. Do not change either
actual mutation body, validator, case, expected byte result or production source
to make the comparison link.

Rust object PID2376681/start34827766 and C object PID2376688/start34827772 each
exited0 with empty stderr. Link PID2376691/start34827781 exited1. All three rows
record direct joins, absent groups, closed streams and no ownership/capture/
retirement/timeout errors. The runner stopped with cases=null and three rows.
Outer PID2376680/start34827758 exited1 in0.3056455749901943s, also positively
joined with absent group/closed streams and no retirement error. All original
objects, commands, raw diagnostics, failed result and captures remain retained.

One failed candidate is now consumed in scheduler-mutation-actual-body-parity.
At most ONE bounded fixture-provider correction may be reviewed in a fresh
prefix and granted separately, preserving the original packet/failure and
unchanged source/oracle. No unchanged replay. If that bounded correction fails,
preserve it and escalate the concrete family rather than iterate automatically.
The separate seven-case caller result is unaffected. No full-crate/native/default
activation, linked production ownership or compute-C retirement is established.

This reviewer read the exact retained result, link stderr and outer closure;
no candidate, compiler, test, privileged command or shared-source edit was run.
