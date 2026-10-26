Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Mediated actual runner complete. Existing exact owner735 Docker-client prefix is
/usr/bin/sudo -A /usr/bin/docker --host=unix:///var/run/docker.sock for build run
and own-CID terminal inspect only. Profile + new rootgrant + independent review
must all explicitly bind this exact prefix/root_docker_client_only. Host wrapper,
host runner and container compiler remain UID1000. No group/rootless fallback or
root container. Existing SUDO_ASKPASS inheritance is used; credential bytes are
never read or recorded. All previous CPU2-5/12GiB/noSwap/pids512/noNet/dropcaps/
no devices/ROinputs/RWoutputs/exact3argv constraints remain.

Old native cleanup is accepted by exactf597854a; coexistence is removed. One new
ordinary root bootstrap holds the verified free permanent27:4, without Docker or
compiler calls. No independent build execution review is needed merely to collect
that ordinary live holder fact. The single actual independent build review occurs
AFTER Root binds actual ready/resources/exports and BEFORE any Docker action.

Root fills HOLDER-BOOTSTRAP.TEMPLATE.NOT-GRANTED.json with /root, a new nonce,
the existing permanent mutex pathname and a fresh handshake directory (parent
already exists), preserving exact source/profile/worker/clearance references.
Then the concrete command is:

    /home/holden/anaconda3/bin/python3 -I -B hold_and_run_build_only.py --bootstrap-grant ACTUAL_ROOT_HOLDER_BOOTSTRAP_GRANT.json

The holder opens only the exact27:4 read-only fd, takes nonblocking sole flock
(refuses a busy record), verifies actual kernel full-EOF row, writes HOLDER.READY.json
with actual PID/birth/FD/device/inode and waits. It never replaces/unlinks the mutex.

Root now uses ready.holder verbatim in resource_authority.reservation_holder,
references ready as reservation_ready_record, sets reservation_kind to
PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE, binds current real RAM/PID/CPU/floors and
the acceptedf597 clearance. Fill the exact UID1000-readable RO-export proof. Root
obtains ONE exact independent build execution release covering all those refs,
source/profile/worker, sudo-client prefix, output root and nonce. Root issues the
new matching build grant. Finally Root exclusively/atomically writes:

    ROOT-BUILD-GRANT.READY.json = {"author":"/root", "nonce":ACTUAL_NONCE, "grant":EXACT_ACTUAL_BUILD_GRANT_REFERENCE}

inside the actual handshake directory. The holder runs only the fixed runner
argv and retains its CLOEXEC fd through positive runner join. A joined runner
with no launch claim, or an exact stopped/Pid0 local container proof, permits
closing this newly owned fd. Any uncertain child/container preserves the fd and
QUARANTINE.json for Root; no blind kill, native cleanup or grant replay.

Source checks:28 pure/mocked changed tests PASS on CPU2/onejob/2GiB. No actual
mutex acquisition, sudo/Docker/container/compiler/native action ran in this lane.
Actual resource/readability and reviewed execution remain pending. No new default/
native/file/C-retirement credit. Existing producer/panic/logger/ELF/link.d and
matching native gates remain; Source38 GNU_RETAIN stays OPEN.
