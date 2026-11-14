# Root actual input and ownership recipe

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This source packet does not start an operation. The selected parent4 successor extends parent3 with early stdout binding and
the full DATA handoff. The same sudo command creates the actual root parent. No pre-existing privileged owner is assumed.

Before invoking the driver, Root obtains an independent operation review of the
exact R2 proposal and source packet. The exact review JSON required by the source
contains `status=PASS_ACTUAL_INSTALL_ONLY`, scope `ROOT_CODE_INSTALL_ONLY`, the
actual R2 SHA-256, actual driver SHA-256, exact parent and child manifest
SHA-256, `native_release=false`, `native_currentfree=null`, and the reviewed
`retire_operation_only` boolean. Its bytes are sealed by phase zero and bind the
actual direct-role model. Root chooses and retains that actual review; a JSON
status or hash by itself is not authority. The driver also requires direct parent
PID 2996005 with birth 118034116 and UID 1000, the existing Root session.

Root supplies a fresh bounded actual-values JSON with the exact keys checked by
`fresh_values`: version 1; actual included `weekly_used_percent` and its UTC-ns
observation (less than 100%, age at most 30 seconds); evidence SHA-256; actual
`service_status=NO_NEW_REJECTION`; `sampled_boot_ns`; live controls/capacity
hashes; actually reserved additional bytes and sudo/frontend/monitor reservation
and currently observed bytes; exact system interpreter SHA-256; the five actual
BOOT/MONO/UTC, phase-one and receipt expiry values in ns; join/capture reserve,
TERM/KILL/join graces; and the reviewed retirement boolean. Root obtains these
from actual usage, controller and resource observations. No sample JSON or
quota/clock/owner values are fabricated in this packet.

Both operation and individual deadlines must be inside each inherited clock cap,
inside fresh-now +180 seconds, and leave more than 75 seconds; the phase-one
and receipt expiries are ordered within the operation cap. The driver rechecks
actual current controller/capacity identities and journals, outer Root PID/birth,
usage freshness, host >=16 GiB, scratch >=12 GiB, MemAvailable >=24 GiB and the
aggregate 18 GiB plus actual other reservations <=22.5447 GiB. The 4-GiB
operation reservation covers three 1-GiB address-space ceilings and a separately
accounted sudo/frontend/monitor reserve up to 1 GiB; the observed host-control
usage may not exceed its reservation. Root must account actual process-tree
control overhead and include it in its capture; no claim that sudo adds no
processes is made. Fresh SOFT/HARD caps and the real controls remain binding.

The driver narrows its own affinity to CPU 6, samples a fresh nonce once, rejects
the preserved earlier nonce, and creates an exclusive private Root-session
reservation directory with durable request, argv, capture and PREEXEC records.
It remains resident as the unprivileged caller and starts exactly one direct sudo
child using the pinned DeferredFork/pidfd custody path. The actual stdout capture
device and inode are passed in the reviewed argv and checked by the root
bootstrap before source loading, child fork or root mutation. The root parent/keeper/installer socket,
lease, pidfds and process births are created after sudo; no preserved FD >=3 is
assumed. The resident caller keeps the actual sudo pidfd, polls only that owned subtree,
durably records separately observed root-parent/keeper/installer PID/birth and
group identities, and directly waits its own sudo child. It closes and hashes
its capture writers once after that wait, and parses the two full-proof and
lease-disposition DATA records against its independent capture inode and role
observations. It never treats absence as termination or uses numeric signaling.
The external Root session still owns the charged 4-GiB reservation and must
positively join the caller through its actual session API, independently review
the recorded proof, capture and terminal disposition, and perform the separately
reviewed operation-only retirement. Driver PID/birth in PREEXEC is not a
substitute for future root identities. Lost
or failed observation, timeout, signal, partial handoff or unjoined process is
UNKNOWN; keep the reservation and all actual custody, never replay that nonce.

Example call shape after review and actual input exist, using Root's own direct
server child and a fresh private 0700 Root-session reservation parent:

```
exec /usr/bin/python3 -I -B -c CALLER_ENTRY_LITERAL --actual-values ACTUAL --actual-values-sha256 ACTUAL_SHA256 --operation-review REVIEW --operation-review-sha256 REVIEW_SHA256 --reservation-parent PRIVATE_PARENT --execute
```

CALLER_ENTRY_LITERAL is the exact bytes in `CALLER-ENTRY.py`, as an argv
element, and is embedded in `CALLER-PROFILE.SOURCE-ONLY.json`. It verifies and
executes the exact hashed driver bytes in the same process. Root must construct
argv without evaluating the literal as shell code.
The command is a proposed invocation, not execution approval. Root supplies the
session supervision and preserves inherited askpass without reading or
printing its contents. Scratch21, mutex27:4, native12, V2 UNKNOWN 2 GiB and
native current-free UNKNOWN stay held; no SDK mount, kernel/module, guest or
native operation follows from this packet.

Caller and host-control RSS are point-sampled while role identities are being
observed; they are not a continuous measurement or proof of a real peak. The
existing 1-GiB host-control reserve includes the 512-MiB caller allowance and
remaining measured/planned sudo/frontend overhead.
