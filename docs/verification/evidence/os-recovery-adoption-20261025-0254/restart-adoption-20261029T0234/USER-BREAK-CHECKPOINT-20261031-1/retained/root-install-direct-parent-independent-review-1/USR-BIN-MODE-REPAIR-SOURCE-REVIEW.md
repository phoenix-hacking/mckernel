# Targeted /usr/bin mode repair source review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source review only; no chmod, privileged operation, native action or
release. The standing user authorization for necessary narrow access repair
applies; actual one-shot admission and resource/custody checks remain separate.

R3 stderr records keeper 3121868/birth 120224750 reporting the fixed
`directory ancestry is not root controlled` failure before lease handoff.
Retained metadata observes /usr/bin root:root mode 0777, device 66306 inode
1048578, under the observed ext4 mount; / and /usr are root:root 0755. This
supports the specific intended 0777-to-0755 correction. No claim of an
installed output or a recorded keeper direct-wait follows from the error.

Frozen manifest 504dc9698cb056a334c356105aad79fc90e4978b6db7512af733e369934f6667
binds mode_repair.py 2d2dc33884f82deca9ad00b37d8d36e0298b282126110c0158e370ef9818287c,
ENTRY.py a4e1835083c27bd5086fa502dfd69037cf55aebd2e476d9c2b84c1d412c664ab,
and profile 6ad22ac2c10001dbc72aa48f515be96fbf5c56e09d1de02a75515d56e9c68729.
Source walks /, usr and bin with no-follow directory FDs, checks exact observed
device/inode/UID/GID/mode/times, absent access and default ACLs, namespace and
mount binding, and the live R3 owner chain. It publishes and fsyncs intent,
rechecks metadata and controls, makes one fchmod on the held target to 0755,
fsyncs and verifies named and separately opened readbacks. Interruption or
failure is UNKNOWN, with no automatic retry or rollback. Other directories
are not mutated by this source.

The three prepared mock tests cover identity/mode, ACL absence and ambiguous
descriptor close. They do not exercise the actual repair() call or its fchmod
and publication failure boundaries. A targeted mocked sequence for intent
before the single validated fchmod and injected precheck/fchmod failure is
needed before the physical one-shot. No test was run by this reviewer.

Root must independently confirm fresh controls, current R3 child/job count and
owner identities, namespace/mount/ACL and inode facts, actual shared-reservation
and sudo overhead, an exclusive capture, and a separately reviewed one-shot.
The old dfd operation's UNKNOWN four-GiB, R3 current ownership, native12,
V2 UNKNOWN two-GiB, scratch21 and mutex27:4 remain held. A successful mode
repair would not itself release any operation, prove a keeper wait, or grant
native/source-view acceptance.
