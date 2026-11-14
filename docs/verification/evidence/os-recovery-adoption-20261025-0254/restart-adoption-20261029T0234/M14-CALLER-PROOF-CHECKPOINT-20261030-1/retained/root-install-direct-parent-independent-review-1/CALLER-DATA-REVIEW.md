# Full caller DATA handoff source review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source-only; no tests, root actions, launch, install or release.

Reviewed SOURCE-BOUND.json
0cdd473570b461fd4d7e10d8b4c3993ff7b2f8a6de534a42cba8f5d4cb55d319,
data_output.py 6e1197061e4c7f99abcea965c6b1fd6beb18556497174ed38e725dbbeeef3b22,
and parent-data.patch aff0db5ac3b78f00b3b54e4b8b2ea80b7d4ffef6bf1a58c44bc09704c8c6c732.

The proposal journals the complete proof, emits bounded full DATA to a regular
stdout and fsyncs it before the one operation-lease close. It publishes a
separate disposition afterward. A short write or fsync failure leaves UNKNOWN,
does not retry, and does not close the lease on a failed full handoff. After a
confirmed close, a later failure reports or retains VERIFIED_CLOSED/UNKNOWN
without re-closing. Root parent PID/birth and successful keeper direct wait and
installer direct wait/pidfd terminal are represented as producer DATA; caller
observation and actual session join remain independent requirements.

Integration condition: the helper's writable regular fd1 check occurs only at
the late FULL write, and its two calls compare identity only within each write.
The parent bootstrap needs to precheck fd1 before fork or mutation and retain
its real device/inode for both FULL and DISPOSITION. The caller must compare
that capture identity to the independent prelaunch CAPTURE record. Ensure
bootstrap output and caller parser agree on the exact number of records.
The configured alarm and original caps give best-effort ordinary interruption;
uninterruptible I/O remains UNKNOWN under the actual caller reservation.

test_data_output.py 79c5013e0967266fbe28e42b79ef89d2e8d4b1c409b1ed76706615d8383d5119
and test_parent_data_order.py 500b3fa2df7495a901e1698c0e2c8fdaa5c3eb10de57fb24b28b9e86f2e848ac
are mock-based and suitable for the existing ordinary CPU6/512MiB/128-FD
profile with Python -B. They have not been run here and do not prove real
stdout, sudo descriptor inheritance, filesystem durability or process joins.
