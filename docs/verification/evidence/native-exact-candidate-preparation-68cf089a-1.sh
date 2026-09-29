#!/bin/bash
set -Eeuo pipefail

# One-shot, preparation-only packet.  It creates and validates an exact source
# candidate.  It never calls Docker, acquires a lease, compiles, or runs a guest.
readonly SOURCE=/home/holden/mckernel
readonly SOURCE_GIT=/home/holden/mckernel/.git
readonly SOURCE_IHK_GIT=/home/holden/mckernel/.git/modules/ihk
readonly SHA=68cf089a22b0a0c034a7f1fcc695853fbf5c07eb
readonly IHK_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly C=/dev/shm/mckernel-exact-candidate-68cf089a-1
readonly B=/dev/shm/mckernel-exact-metadata-backup-68cf089a-1
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly ME="$SCRATCH/native-exact-metadata-evidence-68cf089a-1"
readonly LOG="$SCRATCH/native-exact-candidate-preparation-68cf089a-1.log"
readonly M="$SCRATCH/native-exact-inputs-68cf089a-1.json"
readonly R="$SCRATCH/native-exact-build-request-68cf089a-1.json"
readonly O="$SCRATCH/native-exact-build-output-68cf089a-1"
readonly E="$SCRATCH/native-exact-build-evidence-68cf089a-1"
readonly LEASE="$SCRATCH/native-exact-build-lease-68cf089a-1.json"
readonly ASSETS="$SCRATCH/native-exact-assets-16445ab2"
readonly IMAGE_RECEIPT=/home/holden/mckernel-exact-image-evidence-d0947e0c-1/image-receipt.json
readonly IMAGE_ID=sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d
readonly PLACEMENT="$SCRATCH/candidate-placement-observer-80b8c492-1.py"
readonly CLOSURE="$SCRATCH/source-git-closure-observer-80b8c492-1.py"
readonly PY=/usr/bin/python3

readonly METADATA_SHA=b68a8b5d18a6642ef0043b791984e7a4ea2503a61b8d9153a781827a2277a10a
readonly MANIFEST_SHA=28112e13a9932796080d8183e66e493b1bf0655631413b42775af865798c1d3f
readonly OFFLINE_SHA=1e522a60a265cbd54f50f8856f2c1a8b2f140bd11e655d875f6db431f08a962b
readonly OWNER_SHA=0a4386a9965a99e3b47a469f9f97a2d8180ceab91cdb53aeccd98d1fee04b72d
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

exec > >(/usr/bin/tee -a "$LOG") 2>&1
finish() {
    local rc=$?
    set +x
    echo "PREPARATION_RC=$rc"
    echo "PREPARATION_END_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit "$rc"
}
trap finish EXIT

echo 'SCHEMA=mckernel.native-exact-candidate-preparation-command.v1'
echo "PREPARATION_START_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "PACKET_SHA256=$(/usr/bin/sha256sum "$0" | /usr/bin/awk '{print $1}')"
echo "OWNER_PID=$$"
echo "OWNER_STARTTIME=$(/usr/bin/awk '{print $22}' "/proc/$$/stat")"
echo "SOURCE_SHA=$SHA"
echo "IHK_SHA=$IHK_SHA"
set -x

readonly -a ENV=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1
    GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file)

test "$SOURCE/.git" -ef "$SOURCE_GIT"
test -d "$SOURCE_IHK_GIT/objects"
test -d "$ASSETS"
test -f "$IMAGE_RECEIPT"
test ! -e "$LEASE" && test ! -L "$LEASE"
test "$(/usr/bin/git -C "$SOURCE" rev-parse HEAD)" = "$SHA"
/usr/bin/git -C "$SOURCE_GIT" cat-file -e "$SHA^{commit}"
/usr/bin/git --git-dir="$SOURCE_IHK_GIT" cat-file -e "$IHK_SHA^{commit}"

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

"${ENV[@]}" "$PY" -B "$PLACEMENT" --self-test
"${ENV[@]}" "$PY" -B "$CLOSURE" --self-test

"${ENV[@]}" /bin/bash -c '
set -Eeuo pipefail
umask 0022
/usr/bin/git -c protocol.file.allow=always clone --shared --no-checkout --no-recurse-submodules "$1" "$2"
/usr/bin/git -C "$2" -c core.hooksPath=/dev/null -c core.fsmonitor=false checkout --detach "$3"
/usr/bin/rmdir "$2/ihk"
/usr/bin/git -c protocol.file.allow=always clone --shared --no-checkout "$4" "$2/ihk"
/usr/bin/git -C "$2/ihk" -c core.hooksPath=/dev/null -c core.fsmonitor=false checkout --detach "$5"
' preparation-clone "$SOURCE" "$C" "$SHA" "$SOURCE_IHK_GIT" "$IHK_SHA"

"${ENV[@]}" "$PY" -B "$PLACEMENT" --candidate "$C" --source "$SOURCE" --main-sha "$SHA" --ihk-sha "$IHK_SHA"

read -r main_tag main_label main_count main_digest < <("${ENV[@]}" "$PY" -B "$CLOSURE" --root "$SOURCE_GIT" --label source-main)
read -r ihk_tag ihk_label ihk_count ihk_digest < <("${ENV[@]}" "$PY" -B "$CLOSURE" --root "$SOURCE_IHK_GIT" --label source-ihk)
test "$main_tag" = SOURCE_CLOSURE && test "$ihk_tag" = SOURCE_CLOSURE
echo "$main_tag $main_label $main_count $main_digest"
echo "$ihk_tag $ihk_label $ihk_count $ihk_digest"

# Recheck the emergency reserve immediately before transactional conversion.
"$PY" -I -B - /dev/shm <<'PY'
import os, sys
info = os.statvfs(sys.argv[1]); free = info.f_bavail * info.f_frsize
print("PRE_CONVERSION_SHM_FREE", free)
if free < (4 << 30): raise SystemExit("pre-conversion shm floor failed")
PY

"${ENV[@]}" "$PY" -B "$SOURCE/scripts/native_rust_exact_build_candidate_metadata.py" \
    --main "$C" --ihk "$C/ihk" --source-main "$SOURCE_GIT" --source-ihk "$SOURCE_IHK_GIT" \
    --backup "$B" --evidence "$ME" --main-sha "$SHA" --ihk-sha "$IHK_SHA"

test "$("$PY" -I -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$ME/receipt.json")" = PASS
if /usr/bin/find /dev/shm -maxdepth 1 -mindepth 1 -name 'exact-metadata-*' -print -quit | /usr/bin/grep -q .; then
    echo 'metadata staging remains' >&2
    exit 1
fi
"${ENV[@]}" "$PY" -B "$CLOSURE" --root "$SOURCE_GIT" --label source-main --expected "$main_digest"
"${ENV[@]}" "$PY" -B "$CLOSURE" --root "$SOURCE_IHK_GIT" --label source-ihk --expected "$ihk_digest"

test "$(/usr/bin/git -C "$C" rev-parse HEAD)" = "$SHA"
test "$(/usr/bin/git -C "$C/ihk" rev-parse HEAD)" = "$IHK_SHA"
test -z "$(/usr/bin/git -C "$C" status --porcelain=1 --untracked-files=all)"
test -z "$(/usr/bin/git -C "$C/ihk" status --porcelain=1 --untracked-files=all)"
test ! -e "$C/.git/objects/info/alternates"
test ! -e "$C/.git/commondir"
test ! -e "$C/ihk/.git/objects/info/alternates"
test ! -e "$C/ihk/.git/commondir"
/usr/bin/git -C "$C/ihk" cat-file -e "$IHK_SHA^{commit}"
test "$(/usr/bin/git -C "$C" show f2eb735212e6ab0494e638497e80d9ae78b2848e:CMakeLists.txt | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = e60b304fd38bd2dcddd4f7f8c6217bf887bacfc997741e7aed321dd9222899da
test "$(/usr/bin/git -C "$C" show f2eb735212e6ab0494e638497e80d9ae78b2848e:kernel/include/syscall.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = 758353cfee780c8ba95038947eebbbbfbd5d8cf571f9cb8ccc1558b723a6ece8
test "$(/usr/bin/git -C "$C" show f2eb735212e6ab0494e638497e80d9ae78b2848e:executer/include/uprotocol.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = 1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69
test "$(/usr/bin/git -C "$C" show f2eb735212e6ab0494e638497e80d9ae78b2848e:executer/kernel/mcctrl/mcctrl.h | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = f57a0a6d7e0b0a07cf3ffabd9c88953bed4ae5a2cb8d68d13af5ffe30afaa8d8
"${ENV[@]}" "$PY" -B "$C/scripts/x86_64_shared_abi.py" --repo-root "$C" --check

"${ENV[@]}" "$PY" -B "$C/scripts/native_rust_exact_build_input_manifest.py" \
    --repo "$C" --assets "$ASSETS" --output "$M" --candidate-sha "$SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_input_manifest.py" | /usr/bin/awk '{print $1}')" = "$MANIFEST_SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_offline.py" | /usr/bin/awk '{print $1}')" = "$OFFLINE_SHA"
test "$(/usr/bin/sha256sum "$C/scripts/native_rust_exact_build_container_owner.py" | /usr/bin/awk '{print $1}')" = "$OWNER_SHA"

"${ENV[@]}" "$PY" -I -B -c '
import json, pathlib, sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/"scripts"))
import native_rust_exact_build_offline as driver
manifest=json.load(open(sys.argv[3]))
driver.verify_inputs(root,sys.argv[2],pathlib.Path(sys.argv[4]),manifest,driver.Runner())
print("VERIFY_INPUTS PASS")
' "$C" "$SHA" "$M" "$ASSETS"

/usr/bin/mkdir --mode=0755 "$O" "$E"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"

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
request=json.load(open(sys.argv[2])); instance=owner.BuildOwner(request); instance.validate()
print(json.dumps({"status":"PASS_VALIDATE_ONLY","measurement":instance.measurement},sort_keys=True))
' "$C" "$R"

test ! -e "$LEASE" && test ! -L "$LEASE"
test -z "$(/usr/bin/find "$O" -mindepth 1 -print -quit)"
test -z "$(/usr/bin/find "$E" -mindepth 1 -print -quit)"
echo PASS_PREPARATION_VALIDATE_ONLY
