# Current install-control stop — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This packet has not been executed. Its only prospective signal target is the
actual Root Python 3109451, birth 119988726, UID 0, PPID 3109448, comm python3,
under the retained caller 3109447 and sudo 3109448. No signal is sent to the
caller, sudo, Root server, watchers, native owners or any process group.

The source checks the exact retained caller/sudo/Root process chain, original
request/profile/argv and interpreter bytes, an expired original operation cap
while the weekly cap remains open, the exact 23-FD metadata baseline, one
thread, no target children, dead retained fd23 pidfd target, and absent nonce
operation/code names. A recheck occurs before any signal. It opens a real pidfd
for the exact root target, checks `/proc/self/fdinfo`, fd type and CLOEXEC, and
then uses only pidfd-directed TERM and, if necessary and still within the
reviewed expiry, KILL. Terminal means pidfd polling only: this helper is not the
process's direct parent and cannot prove a wait. It emits bounded captured DATA
for terminal and its own pidfd close disposition. Unknown pidfd custody is
retained; an ambiguous close is never retried. Killing Root necessarily closes
its 23 process descriptors; the source does not claim those descriptors prove
native cleanup or that the former pidfd target has been retired.

The original 4-GiB reservation, nonce, native12, V2 UNKNOWN 2 GiB, scratch21,
mutex27:4 and all evidence remain held. Root's existing caller must still obtain
its own direct sudo wait and Root session join and separately reconcile all
retained custody; this helper never releases that reservation.

The source-bound profile has argv `/usr/bin/sudo -A`, taskset CPU6, system
Python3, 64-MiB AS / 5-CPU-second / 128-FD limits, and an eight-second BOOTTIME
stop window with three seconds TERM grace. The exact literal and argv are in
`PROFILE.SOURCE-ONLY.json`. Root must bind fresh existing shared resources,
actual controller/weekly state, capture and independent operation review before
any execution. The stdout must be a fresh held regular capture; no sudo FD >=3
preservation, new privileged owner or password material is assumed.

After review, Root must generate and durably preserve an actual one-shot release
in canonical compact JSON plus newline, with exact keys and fixed values from
`control_stop.run`: status `REVIEWED_ONE_SHOT_OWNED_CONTROL_STOP`, scope
`ROOT_INSTALL_CONTROL_ONLY`, nonce and all three exact PID/birth bindings,
request/argv/diagnostic/profile hashes, native release false, native currentfree
null and reservation release false, plus actual `issued_boot_ns` and
`expires_boot_ns` no more than 30 seconds apart. Root supplies the release path
and SHA-256 as the profile's final two arguments; it must persist the one-shot
consumption and any uncertainty, and never replay after uncertain dispatch.
This release format is DATA bound to the Root session and independent review;
the status string or a same-user JSON alone is not authority.

Two focused synthetic edge-case tests are prepared at `test_control.py`; they
are unrun and mock pidfd metadata and close. Python 3.8.10 compiled all source
files to code objects. Independent review is required before Root can decide the
actual current-control stop; no physical action occurred in this packet.
