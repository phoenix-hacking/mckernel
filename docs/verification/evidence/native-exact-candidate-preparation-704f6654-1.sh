#!/bin/bash
set -Eeuo pipefail

# One-shot, preparation-only packet.  It creates and validates an exact source
# candidate.  It never calls Docker, acquires a lease, compiles, or runs a guest.
readonly SOURCE=/home/holden/mckernel
readonly SOURCE_GIT=/home/holden/mckernel/.git
readonly SOURCE_IHK_GIT=/home/holden/mckernel/.git/modules/ihk
readonly SHA=704f6654fe95819f7dfd0e4d3665dc44fab63561
readonly IHK_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly C=/dev/shm/mckernel-exact-candidate-704f6654-1
readonly B=/dev/shm/mckernel-exact-metadata-backup-704f6654-1
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly ME="$SCRATCH/native-exact-metadata-evidence-704f6654-1"
readonly LOG="$SCRATCH/native-exact-candidate-preparation-704f6654-1.log"
readonly M="$SCRATCH/native-exact-inputs-704f6654-1.json"
readonly R="$SCRATCH/native-exact-build-request-704f6654-1.json"
readonly O="$SCRATCH/native-exact-build-output-704f6654-1"
readonly E="$SCRATCH/native-exact-build-evidence-704f6654-1"
readonly LEASE="$SCRATCH/native-exact-build-lease-704f6654-1.json"
readonly ASSETS="$SCRATCH/native-exact-assets-16445ab2"
readonly IMAGE_RECEIPT=/home/holden/mckernel-exact-image-evidence-d0947e0c-1/image-receipt.json
readonly IMAGE_ID=sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d
readonly PLACEMENT="$SCRATCH/candidate-placement-observer-80b8c492-1.py"
readonly CLOSURE="$SCRATCH/source-git-closure-observer-80b8c492-1.py"
readonly PY=/usr/bin/python3
readonly GIT_ENV=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file /usr/bin/git)

readonly METADATA_SHA=b68a8b5d18a6642ef0043b791984e7a4ea2503a61b8d9153a781827a2277a10a
readonly MANIFEST_SHA=28112e13a9932796080d8183e66e493b1bf0655631413b42775af865798c1d3f
readonly OFFLINE_SHA=1e522a60a265cbd54f50f8856f2c1a8b2f140bd11e655d875f6db431f08a962b
readonly OWNER_SHA=a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155
readonly PLACEMENT_SHA=4fe5b7717a7ddc8694edaecc63d07f97a56460f8e692d3ebe2d682024dadbe8a
readonly CLOSURE_SHA=079482060e5d0b461d15a5d1ffeb7f5d96719d70b877125665df8df7c4bcd7f1
readonly IMAGE_RECEIPT_SHA=18225919a44e2c07e87a66711c8d1c9483d10e15da91fa5d7fcb7339ff888172

readonly -a TARGETS=("$C" "$B" "$ME" "$LOG" "$M" "$R" "$O" "$E" "$LEASE")

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

topology_check() {
    "$PY" -I -B - "$SCRATCH" "$C" "$B" "$ME" "$LOG" <<'PY'
import os, pathlib, sys
scratch, candidate, backup, evidence, log = map(pathlib.Path, sys.argv[1:])
def mount(path):
    best = None
    for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1); f = left.split(); mp = pathlib.PurePosixPath(f[4].replace('\\040',' '))
        if str(path) == str(mp): best = (mp, right.split()[0])
    return best
root = os.stat('/').st_dev; sm = mount(scratch); shm = mount('/dev/shm')
if sm is None or os.stat(scratch).st_dev == root: raise SystemExit('scratch is not distinct mountpoint')
if shm is None or shm[0] != pathlib.PurePosixPath('/dev/shm') or shm[1] != 'tmpfs': raise SystemExit('/dev/shm is not exact tmpfs')
for p in (candidate, backup):
    if p.parent != pathlib.Path('/dev/shm'): raise SystemExit('candidate parent is not /dev/shm')
if evidence.parent != scratch or log.parent != scratch: raise SystemExit('evidence parent is not scratch')
print('TOPOLOGY_PASS scratch_dev=%s shm_dev=%s' % (os.stat(scratch).st_dev, os.stat('/dev/shm').st_dev))
PY
}
topology_check
umask 0022
exec 3>&1 4>&2
"$PY" -I -B - "$LOG" <<'PY'
import os, sys
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
os.close(fd)
PY
exec >>"$LOG" 2>&1
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
echo "IHK_SHA=$IHK_SHA"
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
"${GIT_ENV[@]}" --git-dir="$SOURCE_GIT" cat-file -e "$SHA^{commit}"
"${GIT_ENV[@]}" --git-dir="$SOURCE_IHK_GIT" cat-file -e "$IHK_SHA^{commit}"

test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_build_candidate_metadata.py" | /usr/bin/awk '{print $1}')" = "$METADATA_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_build_input_manifest.py" | /usr/bin/awk '{print $1}')" = "$MANIFEST_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_build_offline.py" | /usr/bin/awk '{print $1}')" = "$OFFLINE_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/scripts/native_rust_exact_build_container_owner.py" | /usr/bin/awk '{print $1}')" = "$OWNER_SHA"
test "$(/usr/bin/sha256sum "$PLACEMENT" | /usr/bin/awk '{print $1}')" = "$PLACEMENT_SHA"
test "$(/usr/bin/sha256sum "$CLOSURE" | /usr/bin/awk '{print $1}')" = "$CLOSURE_SHA"
test "$(/usr/bin/sha256sum "$IMAGE_RECEIPT" | /usr/bin/awk '{print $1}')" = "$IMAGE_RECEIPT_SHA"

"$PY" -I -B - / /home/holden/mckernel-work/scratch /dev/shm <<'PY'
import os
import pathlib
import sys
floors = (16 << 30, 12 << 30, 4 << 30)
for raw, floor in zip(sys.argv[1:], floors):
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
' preparation-clone "$SOURCE" "$C" "$SHA" "$SOURCE_IHK_GIT" "$IHK_SHA"

"${ENV[@]}" "$PY" -I -B "$PLACEMENT" --candidate "$C" --source "$SOURCE" --main-sha "$SHA" --ihk-sha "$IHK_SHA"

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
metadata_residue() { /usr/bin/find /dev/shm -maxdepth 1 -mindepth 1 -name 'exact-metadata-*' -printf '%f\n' | /usr/bin/sort; }
residue_before=$(metadata_residue)
echo "METADATA_RESIDUE_BASELINE=$(printf '%s' "$residue_before" | /usr/bin/base64 -w0)"
"$PY" -I -B - /dev/shm <<'PY'
import os, sys
info = os.statvfs(sys.argv[1]); free = info.f_bavail * info.f_frsize
print("PRE_CONVERSION_SHM_FREE", free)
if free < (4 << 30): raise SystemExit("pre-conversion shm floor failed")
PY

umask 0022
"${ENV[@]}" "$PY" -I -B "$SOURCE/scripts/native_rust_exact_build_candidate_metadata.py" \
    --main "$C" --ihk "$C/ihk" --source-main "$SOURCE_GIT" --source-ihk "$SOURCE_IHK_GIT" \
    --backup "$B" --evidence "$ME" --main-sha "$SHA" --ihk-sha "$IHK_SHA"

test "$("$PY" -I -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$ME/receipt.json")" = PASS
residue_after=$(metadata_residue)
echo "METADATA_RESIDUE_AFTER=$(printf '%s' "$residue_after" | /usr/bin/base64 -w0)"
test "$residue_before" = "$residue_after"
"${ENV[@]}" "$PY" -I -B "$CLOSURE" --root "$SOURCE_GIT" --label source-main --expected "$main_digest"
"${ENV[@]}" "$PY" -I -B "$CLOSURE" --root "$SOURCE_IHK_GIT" --label source-ihk --expected "$ihk_digest"

test "$("${GIT_ENV[@]}" --git-dir="$C/.git" --work-tree="$C" rev-parse HEAD)" = "$SHA"
test "$("${GIT_ENV[@]}" --git-dir="$C/ihk/.git" --work-tree="$C/ihk" rev-parse HEAD)" = "$IHK_SHA"
test -z "$("${GIT_ENV[@]}" --git-dir="$C/.git" --work-tree="$C" status --porcelain=1 --untracked-files=all)"
test -z "$("${GIT_ENV[@]}" --git-dir="$C/ihk/.git" --work-tree="$C/ihk" status --porcelain=1 --untracked-files=all)"
test ! -e "$C/.git/objects/info/alternates"
test ! -e "$C/.git/commondir"
test ! -e "$C/ihk/.git/objects/info/alternates"
test ! -e "$C/ihk/.git/commondir"
"${GIT_ENV[@]}" --git-dir="$C/ihk/.git" cat-file -e "$IHK_SHA^{commit}"
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

umask 0022
/usr/bin/mkdir --mode=0755 "$O" "$E"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"

umask 0022
"$PY" -I -B - "$R" "$C" "$SHA" "$M" "$ASSETS" "$O" "$E" "$LEASE" "$B" "$IMAGE_RECEIPT" "$IMAGE_ID" "$OFFLINE_SHA" <<'PY'
import hashlib, json, pathlib, sys
(out, root, sha, manifest, assets, build_out, evidence, lease, backup,
 image_receipt, image_id, driver_sha) = sys.argv[1:]
def digest(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
request = {
    "candidate_sha": sha, "image_id": image_id,
    "image_receipt": image_receipt, "image_receipt_sha256": digest(image_receipt),
    "input_manifest": manifest, "input_manifest_sha256": digest(manifest),
    "driver_path": str(pathlib.Path(root)/"scripts/native_rust_exact_build_offline.py"),
    "driver_path_sha256": driver_sha, "source_root": root, "assets_root": assets,
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

"$PY" -I -B - "$C" "$B" <<'PY'
import os, pathlib, sys
def allocated(root):
    total=0
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            path=pathlib.Path(base)/name
            if not path.is_symlink(): total += path.lstat().st_blocks*512
    return total
candidate=allocated(sys.argv[1]); backup=allocated(sys.argv[2]); required=candidate+backup+(12<<30)
print("ALLOCATED", candidate, backup, "AGGREGATE_REQUIRED", required, "LIMIT", 24<<30)
if required > (24<<30): raise SystemExit("aggregate allocation limit exceeded")
for raw, floor in (("/dev/shm",4<<30),("/",16<<30),("/home/holden/mckernel-work/scratch",12<<30)):
    info=os.statvfs(raw); free=info.f_bavail*info.f_frsize
    print("POST_PREP_FREE",raw,free,"FLOOR",floor)
    if free < floor: raise SystemExit("post-preparation resource floor failed: "+raw)
PY

test ! -e "$LEASE" && test ! -L "$LEASE"
"${ENV[@]}" "$PY" -I -B -c '
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/"scripts"))
import native_rust_exact_build_container_owner as owner
if pathlib.Path(owner.__file__).resolve() != (root/"scripts/native_rust_exact_build_container_owner.py").resolve(): raise SystemExit("owner identity mismatch")
if pathlib.Path(owner.provenance.__file__).resolve() != (root/"scripts/native_rust_exact_build_offline.py").resolve(): raise SystemExit("owner provenance identity mismatch")
request=json.load(open(sys.argv[2])); instance=owner.BuildOwner(request); instance.validate()
print(json.dumps({"status":"PASS_VALIDATE_ONLY","measurement":instance.measurement},sort_keys=True))
' "$C" "$R"

test ! -e "$LEASE" && test ! -L "$LEASE"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"
echo PASS_PREPARATION_VALIDATE_ONLY
