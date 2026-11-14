#!/bin/bash
set -Eeuo pipefail

# One-shot, preparation-only packet.  It creates and validates an exact source
# candidate.  It never calls Docker, acquires a lease, compiles, or runs a guest.
readonly SOURCE=/home/holden/mckernel
readonly SOURCE_GIT=/home/holden/mckernel/.git
readonly SOURCE_IHK_GIT=/home/holden/mckernel/.git/modules/ihk
readonly SHA="${PREPARATION_CANDIDATE_SHA:?frozen candidate commit required}"
readonly EXPECTED_SHA=f021bdee206944fc9c68a3f1f2e0f6683a849435
readonly IHK_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly C="$SCRATCH/mckernel-exact-candidate-${SHA:0:8}-scratch-8"
readonly B="$SCRATCH/native-exact-metadata-backup-${SHA:0:8}-scratch-8"
readonly ME="$SCRATCH/native-exact-metadata-evidence-${SHA:0:8}-scratch-8"
readonly LOG="$SCRATCH/native-exact-candidate-preparation-${SHA:0:8}-scratch-8.log"
readonly M="$SCRATCH/native-exact-inputs-${SHA:0:8}-scratch-8.json"
readonly R="$SCRATCH/native-exact-build-request-${SHA:0:8}-scratch-8.json"
readonly O="$SCRATCH/native-exact-build-output-${SHA:0:8}-scratch-8"
readonly E="$SCRATCH/native-exact-build-evidence-${SHA:0:8}-scratch-8"
readonly LEASE="$SCRATCH/native-exact-build-lease-${SHA:0:8}-scratch-8.json"
readonly ASSETS="$SCRATCH/native-exact-assets-16445ab2"
readonly IMAGE_RECEIPT=/home/holden/mckernel-exact-image-evidence-d0947e0c-1/image-receipt.json
readonly OVERLAY="$C/host-kernel/exact-build/ihk-clear-host-pte-overlay.patch"
readonly OVERLAY_SHA=cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7
readonly OVERLAY_BASE_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly OVERLAY_RESULT_SHA=21a0d1eb1705c3ee597aed41358ba4c0a92d5f8c
readonly OVERLAY_BASE_BLOB_SHA=91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c
readonly OVERLAY_RESULT_BLOB_SHA=7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77
readonly IMAGE_ID=sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d
readonly PLACEMENT="$SOURCE/scripts/native_exact_candidate_placement_observer_20260929.py"
readonly TERMINAL="$SCRATCH/native-exact-candidate-preparation-${SHA:0:8}-scratch-8-terminal.json"
# Fresh runtime-blob checkpoint bound by the reviewed selfdigest-13 wrapper.
readonly EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-selfdigest-13.json"
readonly RELEASE="${PREPARATION_RELEASE_COMMIT:?independently reviewed fetched release commit required}"
readonly RELEASE_REF=refs/remotes/origin/codex/local-native-staging-repair
readonly CLOSURE="$SCRATCH/source-git-closure-observer-80b8c492-1.py"
readonly PY=/usr/bin/python3
readonly GIT_ENV=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file /usr/bin/git)

readonly METADATA_SHA=b68a8b5d18a6642ef0043b791984e7a4ea2503a61b8d9153a781827a2277a10a
readonly MANIFEST_SHA=9723cec5c36ad77e90d7619f1ad9fae3e193f1b92a9b152193f2c223b3453b38
readonly OFFLINE_SHA=1993f3ddcf0be925d53a966fad34bed40cb70d4202ac516f1fa6a9b9b81ba388
readonly OWNER_SHA=a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155
readonly IMAGE_OWNER_SHA=35bf9a502a8ab7ddc84cd24759ae47f162da205fb21d06b28d26c50e3e1fbedc
readonly RUNTIME_CHECKER_SHA=84f2eb8ac89175a6fd1f70ba0b614346eae5fbe358430c6b0ea44dabdccce17f
readonly WRAPPER_SHA="${PREPARATION_WRAPPER_SHA:?frozen wrapper hash required}"
readonly EXPECTED_WRAPPER_SHA=0b2eee3e23eea7156e3db6ff5d49c0eeefcd24d84cb8bccee55af6468be5f4a4
readonly HOST_RESERVE_BYTES=$((16 << 30))
readonly SCRATCH_RESERVE_BYTES=$((12 << 30))
# Measured lower bound from the prior exact candidate, plus explicit safety
# reserves for metadata, conversion journals, and a bounded emergency margin.
readonly CHECKOUT_ALLOC_BYTES=9235599360
readonly METADATA_OVERHEAD_BYTES=$((512 << 20))
readonly EMERGENCY_MARGIN_BYTES=$((1 << 30))
readonly PLACEMENT_SHA=e4cc1cbbd12e8c724715e6d5b419a96665eb310ed54154c17fe69efad91ca032
readonly CLOSURE_SHA=079482060e5d0b461d15a5d1ffeb7f5d96719d70b877125665df8df7c4bcd7f1
readonly IMAGE_RECEIPT_SHA=18225919a44e2c07e87a66711c8d1c9483d10e15da91fa5d7fcb7339ff888172

readonly -a TARGETS=("$C" "$B" "$ME" "$LOG" "$M" "$R" "$O" "$E" "$LEASE" "$TERMINAL" "$EXCLUSION")

if (( EUID == 0 )); then
    echo 'refusing root preparation' >&2
    exit 1
fi

# Refuse every existing or dangling target and every symlink ancestor before
# the durable log is opened.  The Python check also rejects aliases/overlaps.
"$PY" -I -B - "${TARGETS[@]}" <<'PY'
import os
import pathlib
import sys
paths = [pathlib.Path(value) for value in sys.argv[1:]]
for path in paths:
    if not path.is_absolute():
        raise SystemExit("non-absolute target: " + str(path))
    cursor = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        cursor /= part
        if os.path.lexists(str(cursor)) and cursor.is_symlink():
            raise SystemExit("symlink target component: " + str(cursor))
    if os.path.lexists(str(path)):
        raise SystemExit("target already exists or dangles: " + str(path))
resolved = [path.resolve(strict=False) for path in paths]
for index, left in enumerate(resolved):
    for right in resolved[index + 1:]:
        if left == right or left in right.parents or right in left.parents:
            raise SystemExit("target alias or overlap: %s %s" % (left, right))
PY

# Validate the later packet/helper release separately from the candidate source.
[[ $RELEASE =~ ^[0-9a-f]{40}$ ]]
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" rev-parse "$RELEASE_REF")" = "$RELEASE"
"${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" merge-base --is-ancestor "$SHA" "$RELEASE"
for bound in docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-8.sh scripts/native_exact_candidate_placement_observer_20260929.py scripts/native_rust_exact_disk_build_wrapper.py scripts/native_rust_exact_mckernel_image_container_owner.py scripts/native_rust_runtime_evidence.py; do
    test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$RELEASE:$bound" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$(/usr/bin/sha256sum "$SOURCE/$bound" | /usr/bin/awk '{print $1}')"
done
test "$(/usr/bin/readlink -f "$0")" = "$SOURCE/docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-8.sh"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_disk_build_wrapper.py" | /usr/bin/awk '{print $1}')" = "$WRAPPER_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_mckernel_image_container_owner.py" | /usr/bin/awk '{print $1}')" = "$IMAGE_OWNER_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_runtime_evidence.py" | /usr/bin/awk '{print $1}')" = "$RUNTIME_CHECKER_SHA"

topology_check() {
    "$PY" -I -B - "$PLACEMENT" "$SCRATCH" "$C" "$B" <<'PY'
import importlib.util, pathlib, sys
helper, scratch, candidate, backup = sys.argv[1:]
spec = importlib.util.spec_from_file_location('placement', helper)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
device, filesystem = module.placement(pathlib.Path(scratch), [pathlib.Path(candidate), pathlib.Path(backup)])
print("TOPOLOGY_PASS", device, filesystem)
PY
}
topology_check
umask 0077
exec 3>&1 4>&2
# Bash noclobber opens the actual logging descriptor with O_EXCL.
set -o noclobber
exec >"$LOG" 2>&1
set +o noclobber
"$PY" -I -B - "$LOG" <<'PY'
import os, sys
fd=os.open(sys.argv[1], os.O_WRONLY | os.O_NOFOLLOW)
try: os.fsync(fd)
finally: os.close(fd)
fd=os.open(os.path.dirname(sys.argv[1]), os.O_RDONLY | os.O_DIRECTORY)
try: os.fsync(fd)
finally: os.close(fd)
PY
finish() {
    local rc=$?
    trap - EXIT HUP INT TERM
    set +x
    echo "LIVE_CHILDREN=$(jobs -pr | /usr/bin/tr '\n' ' ')"
    echo "PREPARATION_PID=$$ PPID=$PPID PGID=$(/usr/bin/ps -o pgid= -p $$ | /usr/bin/tr -d ' ') SID=$(/usr/bin/ps -o sid= -p $$ | /usr/bin/tr -d ' ')"
    echo "TERMINAL_RC=$rc"
    echo "PREPARATION_RC=$rc"
    echo "PREPARATION_END_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "LOG_FINAL_FSYNC=PENDING"
    if "$PY" -I -B - "$LOG" <<'PY'
import os,sys
fd = os.open(sys.argv[1], os.O_WRONLY)
try: os.fsync(fd)
finally: os.close(fd)
PY
    then
        echo "LOG_FINAL_FSYNC=PASS" >&3
    else
        echo "LOG_FINAL_FSYNC=FAIL" >&4
        rc=74
    fi
    set +e
    "$PY" -I -B - "$TERMINAL" "$rc" "$$" "$LOG" <<'PY'
import hashlib, json, os, pathlib, sys
path, rc, pid, log = sys.argv[1:]
record = dict(schema='mckernel.native-exact-scratch-preparation-terminal.v1',
              returncode=int(rc), pid=int(pid),
              starttime=pathlib.Path('/proc/'+pid+'/stat').read_text().rsplit(')',1)[1].split()[19],
              boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              log=log, log_sha256=hashlib.sha256(pathlib.Path(log).read_bytes()).hexdigest())
with open(path, 'x') as stream:
    json.dump(record, stream, sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
fd=os.open(str(pathlib.Path(path).parent), os.O_RDONLY | os.O_DIRECTORY)
try: os.fsync(fd)
finally: os.close(fd)
PY
    local terminal_rc=$?
    if (( terminal_rc != 0 )); then rc=74; fi
    exit "$rc"
}
trap finish EXIT
on_signal() { local sig=$1; echo "TERMINAL_SIGNAL=$sig"; exit $((128 + sig)); }
trap 'on_signal 1' HUP
trap 'on_signal 2' INT
trap 'on_signal 15' TERM

echo 'SCHEMA=mckernel.native-exact-candidate-preparation-command.v1'
echo "PREPARATION_START_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "PACKET_SHA256=$(/usr/bin/sha256sum "$0" | /usr/bin/awk '{print $1}')"
echo "OWNER_PID=$$"
echo "OWNER_STARTTIME=$(/usr/bin/awk '{print $22}' "/proc/$$/stat")"
echo "SOURCE_SHA=$SHA"
test "$SHA" = "$EXPECTED_SHA"
echo "WRAPPER_SHA=$WRAPPER_SHA"
test "$WRAPPER_SHA" = "$EXPECTED_WRAPPER_SHA"
echo "IHK_SHA=$IHK_SHA"
echo "IHK_OVERLAY_SHA=$OVERLAY_SHA"
echo "IHK_OVERLAY_BASE_SHA=$OVERLAY_BASE_SHA"
echo "IHK_OVERLAY_RESULT_SHA=$OVERLAY_RESULT_SHA"
echo "IHK_OVERLAY_BASE_BLOB_SHA=$OVERLAY_BASE_BLOB_SHA"
echo "IHK_OVERLAY_RESULT_BLOB_SHA=$OVERLAY_RESULT_BLOB_SHA"
echo 'EXTERNAL_PREFLIGHT_REQUIRED=full ps plus /proc starttimes, all lease locations, and independently released unfiltered read-only docker ps; this packet does not perform or self-authorize it.'
set -x

readonly -a ENV=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1
    GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file)

test "$SOURCE/.git" -ef "$SOURCE_GIT"
test -d "$SOURCE_IHK_GIT/objects"
test -d "$ASSETS"
test -f "$IMAGE_RECEIPT"
test ! -e "$LEASE" && test ! -L "$LEASE"
test ! -e "$EXCLUSION" && test ! -L "$EXCLUSION"
"${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" cat-file -e "$SHA^{commit}"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" ls-tree "$SHA" -- ihk)" = "160000 commit $IHK_SHA	ihk"
"${GIT_ENV[@]}" --git-dir="$SOURCE_IHK_GIT" cat-file -e "$IHK_SHA^{commit}"

test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_build_candidate_metadata.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$METADATA_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_build_input_manifest.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$MANIFEST_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_build_offline.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$OFFLINE_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_disk_build_wrapper.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$WRAPPER_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_build_container_owner.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$OWNER_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_exact_mckernel_image_container_owner.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$IMAGE_OWNER_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" show "$SHA:scripts/native_rust_runtime_evidence.py" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$RUNTIME_CHECKER_SHA"
test "$(/usr/bin/sha256sum "$PLACEMENT" | /usr/bin/awk '{print $1}')" = "$PLACEMENT_SHA"
test "$(/usr/bin/sha256sum "$CLOSURE" | /usr/bin/awk '{print $1}')" = "$CLOSURE_SHA"
test "$(/usr/bin/sha256sum "$IMAGE_RECEIPT" | /usr/bin/awk '{print $1}')" = "$IMAGE_RECEIPT_SHA"

"$PY" -I -B - / /home/holden/mckernel-work/scratch "$HOST_RESERVE_BYTES" "$SCRATCH_RESERVE_BYTES" "$CHECKOUT_ALLOC_BYTES" "$METADATA_OVERHEAD_BYTES" "$EMERGENCY_MARGIN_BYTES" <<'PY'
import os
import pathlib
import sys
host_reserve, scratch_reserve, checkout, metadata, emergency = map(int, sys.argv[3:])
floors = (host_reserve + checkout + metadata + emergency,
          scratch_reserve + checkout + metadata + emergency)
for raw, floor in zip(sys.argv[1:3], floors):
    info = os.statvfs(raw)
    free = info.f_bavail * info.f_frsize
    print("RESOURCE_FREE", raw, free, "FLOOR", floor)
    if free < floor:
        raise SystemExit("resource floor failed: " + raw)
mem = None
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
    if line.startswith('MemAvailable:'):
        mem = int(line.split()[1]) * 1024
        break
print("MEMORY_AVAILABLE", mem, "FLOOR", 16 << 30)
if mem is None or mem < (16 << 30):
    raise SystemExit("memory floor failed")
PY

"${ENV[@]}" "$PY" -I -B "$PLACEMENT" --self-test
"${ENV[@]}" "$PY" -I -B "$CLOSURE" --self-test

"${ENV[@]}" /bin/bash -c '
set -Eeuo pipefail
umask 0022
git=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file /usr/bin/git)
"${git[@]}" -c protocol.file.allow=always clone --shared --no-checkout --no-recurse-submodules "$1" "$2"
"${git[@]}" --git-dir="$2/.git" --work-tree="$2" -c core.hooksPath=/dev/null -c core.fsmonitor=false checkout --detach "$3"
/usr/bin/rmdir "$2/ihk"
"${git[@]}" -c protocol.file.allow=always clone --shared --no-checkout "$4" "$2/ihk"
"${git[@]}" --git-dir="$2/ihk/.git" --work-tree="$2/ihk" -c core.hooksPath=/dev/null -c core.fsmonitor=false checkout --detach "$5"
' preparation-clone "$SOURCE_GIT" "$C" "$SHA" "$SOURCE_IHK_GIT" "$IHK_SHA"
test "$(/usr/bin/sha256sum "$OVERLAY" | /usr/bin/awk '{print $1}')" = "$OVERLAY_SHA"
for pair in "candidate_metadata:$METADATA_SHA" "input_manifest:$MANIFEST_SHA" "offline:$OFFLINE_SHA" "container_owner:$OWNER_SHA"; do
    name=${pair%%:*}; expected=${pair#*:}
    test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_$name.py" | /usr/bin/awk '{print $1}')" = "$expected"
done
"${ENV[@]}" "$PY" -I -B - "$C/ihk" "$OVERLAY" "$OVERLAY_BASE_SHA" "$OVERLAY_SHA" <<'PY'
import hashlib, pathlib, subprocess, sys
root, patch, base, expected = sys.argv[1:]
if subprocess.run(["/usr/bin/git", "-C", root, "apply", "--check", patch], check=False).returncode:
    raise SystemExit("clear_host_pte overlay does not apply to pinned IHK")
if hashlib.sha256(pathlib.Path(patch).read_bytes()).hexdigest() != expected:
    raise SystemExit("overlay hash mismatch")
print("IHK_OVERLAY_APPLY_CHECK PASS", base, expected)
PY

"${ENV[@]}" "$PY" -I -B "$PLACEMENT" --candidate "$C" --backup "$B" --scratch "$SCRATCH" --source "$SOURCE" --main-sha "$SHA" --ihk-sha "$IHK_SHA" --phase clean

closure_capture() {
    local root=$1 label=$2 output
    if ! output=$("${ENV[@]}" "$PY" -I -B "$CLOSURE" --root "$root" --label "$label"); then
        echo "closure producer failed: $label" >&2; return 1
    fi
    [[ $output =~ ^SOURCE_CLOSURE[[:space:]]+$label[[:space:]]+[1-9][0-9]*[[:space:]]+[0-9a-f]{64}$ ]] || { echo "invalid closure output: $output" >&2; return 1; }
    printf '%s\n' "$output"
}
main_closure=$(closure_capture "$SOURCE_GIT" source-main)
ihk_closure=$(closure_capture "$SOURCE_IHK_GIT" source-ihk)
read -r main_tag main_label main_count main_digest <<<"$main_closure"
read -r ihk_tag ihk_label ihk_count ihk_digest <<<"$ihk_closure"
test "$main_tag" = SOURCE_CLOSURE && test "$ihk_tag" = SOURCE_CLOSURE
echo "$main_tag $main_label $main_count $main_digest"
echo "$ihk_tag $ihk_label $ihk_count $ihk_digest"

# Recheck the emergency reserve immediately before transactional conversion.
topology_check
metadata_residue() { /usr/bin/find "$SCRATCH" -maxdepth 1 -mindepth 1 -name 'exact-metadata-*' -printf '%f\n' | /usr/bin/sort; }
residue_before=$(metadata_residue)
echo "METADATA_RESIDUE_BASELINE=$(printf '%s' "$residue_before" | /usr/bin/base64 -w0)"
"$PY" -I -B - / "$SCRATCH" "$HOST_RESERVE_BYTES" "$SCRATCH_RESERVE_BYTES" "$METADATA_OVERHEAD_BYTES" "$EMERGENCY_MARGIN_BYTES" <<'PY'
import os, sys
host_reserve, scratch_reserve, metadata, emergency = map(int, sys.argv[3:])
for raw, reserve in zip(sys.argv[1:3], (host_reserve, scratch_reserve)):
    required = reserve + metadata + emergency
    info = os.statvfs(raw); free = info.f_bavail * info.f_frsize
    print("POST_CLONE_FREE", raw, free)
    print("POST_CLONE_REQUIRED", raw, required)
    if free < required: raise SystemExit("post-clone reserve plus metadata floor failed: " + raw)
PY

test ! -e "$B" && test ! -L "$B"
test ! -e "$ME" && test ! -L "$ME"
umask 0022
"${ENV[@]}" "$PY" -I -B "$C/scripts/native_rust_exact_build_candidate_metadata.py" \
    --main "$C" --ihk "$C/ihk" --source-main "$SOURCE_GIT" --source-ihk "$SOURCE_IHK_GIT" \
    --backup "$B" --evidence "$ME" --main-sha "$SHA" --ihk-sha "$IHK_SHA"

test "$("$PY" -I -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$ME/receipt.json")" = PASS
residue_after=$(metadata_residue)
echo "METADATA_RESIDUE_AFTER=$(printf '%s' "$residue_after" | /usr/bin/base64 -w0)"
test "$residue_before" = "$residue_after"
"${ENV[@]}" /usr/bin/git -C "$C/ihk" apply "$OVERLAY"
test "$(${GIT_ENV[@]} --git-dir="$C/ihk/.git" --work-tree="$C/ihk" rev-parse HEAD)" = "$IHK_SHA"
test "$(${GIT_ENV[@]} --git-dir="$C/ihk/.git" --work-tree="$C/ihk" status --porcelain=1 --untracked-files=all)" = " M test/ihklib/whitebox/src/driver/mckernel/syscall.c"
test "$(${GIT_ENV[@]} --git-dir="$C/ihk/.git" --work-tree="$C/ihk" diff --binary | sha256sum | awk '{print $1}')" = "$OVERLAY_SHA"
test "$("${GIT_ENV[@]}" -C "$C/ihk" show "$OVERLAY_BASE_SHA:test/ihklib/whitebox/src/driver/mckernel/syscall.c" | sha256sum | awk '{print $1}')" = "$OVERLAY_BASE_BLOB_SHA"
test "$(sha256sum "$C/ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c" | awk '{print $1}')" = "$OVERLAY_RESULT_BLOB_SHA"
test "$(sha256sum "$C/scripts/native_rust_exact_mckernel_image_container_owner.py" | awk '{print $1}')" = "$IMAGE_OWNER_SHA"
test "$(sha256sum "$C/scripts/native_rust_runtime_evidence.py" | awk '{print $1}')" = "$RUNTIME_CHECKER_SHA"
"${ENV[@]}" "$PY" -I -B "$CLOSURE" --root "$SOURCE_GIT" --label source-main --expected "$main_digest"
"${ENV[@]}" "$PY" -I -B "$CLOSURE" --root "$SOURCE_IHK_GIT" --label source-ihk --expected "$ihk_digest"

test "$("${GIT_ENV[@]}" --git-dir="$C/.git" --work-tree="$C" rev-parse HEAD)" = "$SHA"
test "$("${GIT_ENV[@]}" --git-dir="$C/ihk/.git" --work-tree="$C/ihk" rev-parse HEAD)" = "$IHK_SHA"
# The reviewed nested overlay intentionally makes the superproject report a
# dirty gitlink.  Admit no main-tree change while checking the nested tree
# exactly below.
test -z "$("${GIT_ENV[@]}" --git-dir="$C/.git" --work-tree="$C" status --porcelain=1 --untracked-files=all --ignore-submodules=dirty)"
test "$(${GIT_ENV[@]} --git-dir="$C/ihk/.git" --work-tree="$C/ihk" status --porcelain=1 --untracked-files=all)" = " M test/ihklib/whitebox/src/driver/mckernel/syscall.c"
test ! -e "$C/.git/objects/info/alternates"
test ! -e "$C/.git/commondir"
test ! -e "$C/ihk/.git/objects/info/alternates"
test ! -e "$C/ihk/.git/commondir"
"${GIT_ENV[@]}" --git-dir="$C/ihk/.git" cat-file -e "$IHK_SHA^{commit}"
test "$(${GIT_ENV[@]} --git-dir="$C/ihk/.git" --work-tree="$C/ihk" diff --binary | sha256sum | awk '{print $1}')" = "$OVERLAY_SHA"
test "$("${GIT_ENV[@]}" -C "$C/ihk" show "$OVERLAY_BASE_SHA:test/ihklib/whitebox/src/driver/mckernel/syscall.c" | sha256sum | awk '{print $1}')" = "$OVERLAY_BASE_BLOB_SHA"
test "$(sha256sum "$C/ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c" | awk '{print $1}')" = "$OVERLAY_RESULT_BLOB_SHA"
test "$("${GIT_ENV[@]}" --git-dir="$C/.git" show f2eb735212e6ab0494e638497e80d9ae78b2848e:CMakeLists.txt | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = e60b304fd38bd2dcddd4f7f8c6217bf887bacfc997741e7aed321dd9222899da
test "$("${GIT_ENV[@]}" --git-dir="$C/.git" show f2eb735212e6ab0494e638497e80d9ae78b2848e:kernel/include/syscall.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = 758353cfee780c8ba95038947eebbbbfbd5d8cf571f9cb8ccc1558b723a6ece8
test "$("${GIT_ENV[@]}" --git-dir="$C/.git" show f2eb735212e6ab0494e638497e80d9ae78b2848e:executer/include/uprotocol.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = 1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69
test "$("${GIT_ENV[@]}" --git-dir="$C/.git" show f2eb735212e6ab0494e638497e80d9ae78b2848e:executer/kernel/mcctrl/mcctrl.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = f57a0a6d7e0b0a07cf3ffabd9c88953bed4ae5a2cb8d68d13af5ffe30afaa8d8
"${ENV[@]}" "$PY" -I -B "$C/scripts/x86_64_shared_abi.py" --repo-root "$C" --check

umask 0022
"${ENV[@]}" "$PY" -I -B -c '
import pathlib, sys
root = pathlib.Path(sys.argv[1]); scripts = root / "scripts"
sys.path.insert(0, str(scripts))
import native_rust_exact_build_input_manifest as manifest
if pathlib.Path(manifest.__file__).resolve() != (scripts / "native_rust_exact_build_input_manifest.py").resolve(): raise SystemExit("manifest identity mismatch")
if pathlib.Path(manifest.provenance.__file__).resolve() != (scripts / "native_rust_exact_build_offline.py").resolve(): raise SystemExit("manifest provenance identity mismatch")
raise SystemExit(manifest.main(sys.argv[2:]))
' "$C" --repo "$C" --assets "$ASSETS" --output "$M" --candidate-sha "$SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_input_manifest.py" | /usr/bin/awk '{print $1}')" = "$MANIFEST_SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_offline.py" | /usr/bin/awk '{print $1}')" = "$OFFLINE_SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_container_owner.py" | /usr/bin/awk '{print $1}')" = "$OWNER_SHA"

"${ENV[@]}" "$PY" -I -B -c '
import json, pathlib, sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/"scripts"))
import native_rust_exact_build_offline as driver
if pathlib.Path(driver.__file__).resolve() != (root/"scripts/native_rust_exact_build_offline.py").resolve(): raise SystemExit("driver identity mismatch")
manifest=json.load(open(sys.argv[3]))
driver.verify_inputs(root,sys.argv[2],pathlib.Path(sys.argv[4]),manifest,driver.Runner())
print("VERIFY_INPUTS PASS")
' "$C" "$SHA" "$M" "$ASSETS"

umask 0077
/usr/bin/mkdir --mode=0700 "$O" "$E"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"

umask 0022
"$PY" -I -B - "$R" "$C" "$SHA" "$M" "$ASSETS" "$O" "$E" "$LEASE" "$B" "$IMAGE_RECEIPT" "$IMAGE_ID" "$OFFLINE_SHA" "$OVERLAY" "$OVERLAY_SHA" "$OVERLAY_BASE_SHA" "$OVERLAY_RESULT_SHA" "$OVERLAY_BASE_BLOB_SHA" "$OVERLAY_RESULT_BLOB_SHA" "$EXCLUSION" "$OWNER_SHA" <<'PY'
import hashlib, json, pathlib, sys
(out, root, sha, manifest, assets, build_out, evidence, lease, backup,
 image_receipt, image_id, driver_sha, overlay, overlay_sha, overlay_base, overlay_result, overlay_base_blob, overlay_result_blob, exclusion, owner_sha) = sys.argv[1:]
def digest(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
request = {
    "candidate_sha": sha, "image_id": image_id,
    "operational_exclusion_path": exclusion,
    "launcher_aggregate_memory_gib": "16.2158",
    "owner_path": str(pathlib.Path(root)/"scripts/native_rust_exact_build_container_owner.py"),
    "owner_path_sha256": owner_sha,
    "provenance_path": str(pathlib.Path(root)/"scripts/native_rust_exact_build_offline.py"),
    "provenance_path_sha256": driver_sha,
    "limits": {"NanoCpus":4000000000,"CpusetCpus":"2-5","Memory":12884901888,
               "MemorySwap":12884901888,"PidsLimit":512,"NetworkMode":"none"},
    "image_receipt": image_receipt, "image_receipt_sha256": digest(image_receipt),
    "input_manifest": manifest, "input_manifest_sha256": digest(manifest),
    "driver_path": str(pathlib.Path(root)/"scripts/native_rust_exact_build_offline.py"),
    "driver_path_sha256": driver_sha, "source_root": root, "assets_root": assets,
    "ihk_overlay_path": overlay, "ihk_overlay_sha256": overlay_sha,
    "ihk_overlay_base_sha": overlay_base, "ihk_overlay_result_sha": overlay_result,
    "ihk_overlay_base_blob_sha256": overlay_base_blob,
    "ihk_overlay_result_blob_sha256": overlay_result_blob,
    "output_root": build_out, "evidence_root": evidence,
    "host_measure_root": "/", "scratch_measure_root": "/home/holden/mckernel-work/scratch",
    "memory_allocation_roots": [root, backup], "lease_path": lease,
    "timeout": 19800, "host_floor": 17179869184, "scratch_floor": 12884901888
}
path = pathlib.Path(out)
with path.open("x", encoding="utf-8") as stream:
    json.dump(request, stream, sort_keys=True, separators=(",",":")); stream.write("\n")
    stream.flush()
    import os; os.fsync(stream.fileno())
print("REQUEST_SHA256", digest(path))
PY

"${ENV[@]}" "$PY" -I -B "$PLACEMENT" --candidate "$C" --backup "$B" --scratch "$SCRATCH" --source "$SOURCE" --main-sha "$SHA" --ihk-sha "$IHK_SHA" --phase overlay --overlay-sha "$OVERLAY_SHA" --result-sha "$OVERLAY_RESULT_BLOB_SHA"
"$PY" -I -B - / "$SCRATCH" "$HOST_RESERVE_BYTES" "$SCRATCH_RESERVE_BYTES" "$METADATA_OVERHEAD_BYTES" "$EMERGENCY_MARGIN_BYTES" <<'PY'
import os, pathlib, sys
host_reserve, scratch_reserve, metadata, emergency = map(int, sys.argv[3:])
for raw, reserve in zip(sys.argv[1:3], (host_reserve, scratch_reserve)):
    floor = reserve + metadata + emergency
    info=os.statvfs(raw); free=info.f_bavail*info.f_frsize
    print("POST_PREP_FREE",raw,free,"FLOOR",floor)
    if free < floor: raise SystemExit("post-preparation reserve plus metadata floor failed: "+raw)
mem=int(pathlib.Path('/proc/meminfo').read_text().split('MemAvailable:',1)[1].split()[0])*1024
print("POST_PREP_MEMORY_AVAILABLE",mem)
if mem < 16<<30: raise SystemExit("post-preparation memory floor failed")
PY

test ! -e "$LEASE" && test ! -L "$LEASE"
"${ENV[@]}" "$PY" -I -B -c '
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/"scripts"))
import native_rust_exact_build_container_owner as owner
if pathlib.Path(owner.__file__).resolve() != (root/"scripts/native_rust_exact_build_container_owner.py").resolve(): raise SystemExit("owner identity mismatch")
if pathlib.Path(owner.provenance.__file__).resolve() != (root/"scripts/native_rust_exact_build_offline.py").resolve(): raise SystemExit("owner provenance identity mismatch")
request=json.load(open(sys.argv[2])); instance=owner.BuildOwner(request); instance.validate()
measurement=instance.measurement
rows=measurement["memory_allocation_roots"]
if {row["path"] for row in rows} != set(request["memory_allocation_roots"]): raise SystemExit("incomplete memory measurement")
if any(row["filesystem"] not in ("ext4","xfs") or row["memory_effect_bytes"] != 0 for row in rows): raise SystemExit("memory-backed allocation")
if measurement["memory_allocation_memory_backed_bytes"] != 0: raise SystemExit("nonzero memory allocation")
from decimal import Decimal
if measurement["aggregate_memory_required"] > int(Decimal("16.2158")*(2**30)): raise SystemExit("launcher aggregate exceeded")
if owner.LIMITS != request["limits"]: raise SystemExit("reviewed owner profile differs")
print(json.dumps({"status":"PASS_VALIDATE_ONLY","measurement":measurement},sort_keys=True))
' "$C" "$R"

test ! -e "$LEASE" && test ! -L "$LEASE"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"
test ! -e "$EXCLUSION" && test ! -L "$EXCLUSION"
echo PASS_PREPARATION_VALIDATE_ONLY
