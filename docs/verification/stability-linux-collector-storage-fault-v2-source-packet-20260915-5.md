# Linux collector storage-fault v2 source packet 5

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-source`
Disposition: `SOURCE_PACKET_OWNER_IDENTITY_DRAFT_ONLY`

This additive correction supersedes only the owner-identity binding omitted from
packet 2 SHA256
`0feaad14f408acf806fb391195e519a16de60cc41ffdb24cd9721ea432b90089`.
Packets 1–4 otherwise remain effective. No execution is authorized.

Add exact top-level OWNER_RESULT key `owner` with exact keys
`pid,startticks`. Both are positive integers. Before socket creation or fork,
the owner reads `/proc/self/stat` twice through independent opens and requires
the same PID/startticks; the PID must equal `getpid()`. It retains this bound
identity in the result. After fork, each accepted collector identity read must
have PPID equal to `owner.pid`; `collector.ppid` equals the same value. READY
release requires those joins. The oracle requires exact equality across owner,
collector, all relevant identity/cleanup records and packets. A changed owner
PID/startticks, changed collector PPID or omitted initial binding is a distinct
negative. This is retained process evidence, not proof that a historical `/proc`
entry remains live during offline validation.
