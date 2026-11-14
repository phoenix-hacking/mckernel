#!/bin/bash
set -Eeuo pipefail

# One-shot copy/validation packet. It never deletes a source, invokes Docker,
# compiles, acquires a build lease, or runs a guest.
readonly RELEASE_HASH=448246856c1abdeb140704f6ecba8f063a24292b976cc4e2ab95eab38de3d2c6
readonly SOURCE=/dev/shm/mckernel-exact-candidate-76ae20b5-1
readonly SOURCE_BACKUP=/dev/shm/mckernel-exact-metadata-backup-76ae20b5-1
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly DEST="$SCRATCH/mckernel-exact-candidate-76ae20b5-disk-1"
readonly DEST_BACKUP="$SCRATCH/mckernel-exact-metadata-backup-76ae20b5-disk-1"
readonly LOG="$SCRATCH/native-exact-candidate-disk-copy-76ae20b5-1.log"
readonly SOURCE_INVENTORY="$SCRATCH/native-exact-candidate-disk-copy-76ae20b5-source.json"
readonly SOURCE_POST_INVENTORY="$SCRATCH/native-exact-candidate-disk-copy-76ae20b5-source-post.json"
readonly DEST_INVENTORY="$SCRATCH/native-exact-candidate-disk-copy-76ae20b5-dest.json"
readonly DEST_POST_INVENTORY="$SCRATCH/native-exact-candidate-disk-copy-76ae20b5-dest-post.json"
readonly REQUEST="$SCRATCH/native-exact-build-request-76ae20b5-disk-1.json"
readonly OUTPUT="$SCRATCH/native-exact-build-output-76ae20b5-disk-1"
readonly EVIDENCE="$SCRATCH/native-exact-build-evidence-76ae20b5-disk-1"
readonly LEASE="$SCRATCH/native-exact-build-lease-76ae20b5-disk-1.json"
readonly MANIFEST="$SCRATCH/native-exact-inputs-76ae20b5-1.json"
readonly ORIGINAL_REQUEST="$SCRATCH/native-exact-build-request-76ae20b5-1.json"
readonly RECEIPT="$SCRATCH/native-exact-metadata-evidence-76ae20b5-1/receipt.json"
readonly PREPARATION_LOG="$SCRATCH/native-exact-candidate-preparation-76ae20b5-1.log"
readonly SUCCESS=/home/holden/mckernel/docs/verification/evidence/stability-native-exact-candidate-preparation-success-76ae20b5-20260929-1.json
readonly RAW=/home/holden/mckernel/docs/verification/evidence/stability-native-exact-candidate-preparation-success-raw-76ae20b5-20260929-1.tar.gz
readonly MAIN_SHA=76ae20b523f57dee8e0fb1fb834caf5443f9f671
readonly IHK_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly OVERLAY_PATH=test/ihklib/whitebox/src/driver/mckernel/syscall.c
readonly OVERLAY_SHA=cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7
readonly OVERLAY_RESULT_SHA=7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77
readonly MANIFEST_SHA=5c893b1af09e0728aed3c220ab3811d3f1047d013a83e59f05c762db43e9ce75
readonly ORIGINAL_REQUEST_SHA=a483f42764f27b9785ff1465d35fd22632c9a2535664868b8f81655e96044d4a
readonly RECEIPT_SHA=9de0ec645b9852ec22a308c556e1f3bbf95da09306c792a7ecd16685acee4883
readonly PREPARATION_LOG_SHA=cc095274b39bf1d6b1f33df8a619d73cb91efc94c8c0f5f75783b386af7811d3
readonly SUCCESS_SHA=9a1a4b0c6e98b9b09ef934962dbcd9dac7ed3d23e90104c1561d6a4953cc348c
readonly RAW_SHA=d62620632de5b5fa9ed32937779a9a51c0b72f6347c9142c442614d77c37e703
readonly PY=/usr/bin/python3
readonly -a GIT=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file /usr/bin/git)
readonly -a TARGETS=("$DEST" "$DEST_BACKUP" "$LOG" "$SOURCE_INVENTORY" "$SOURCE_POST_INVENTORY" "$DEST_INVENTORY" "$DEST_POST_INVENTORY" "$REQUEST" "$OUTPUT" "$EVIDENCE" "$LEASE")

if (( EUID == 0 )); then echo 'refusing root copy' >&2; exit 1; fi
if [[ "$RELEASE_HASH" == RELEASE_HASH_REQUIRED ]]; then echo 'TEMPLATE_ONLY' >&2; exit 78; fi

"$PY" -I -B - "${TARGETS[@]}" <<'PY'
import os,pathlib,sys
paths=[pathlib.Path(x) for x in sys.argv[1:]]
for p in paths:
    if not p.is_absolute(): raise SystemExit('non-absolute target: '+str(p))
    q=pathlib.Path(p.anchor)
    for part in p.parts[1:]:
        q/=part
        if os.path.lexists(str(q)) and q.is_symlink(): raise SystemExit('symlink target component: '+str(q))
    if os.path.lexists(str(p)): raise SystemExit('target already exists: '+str(p))
resolved=[p.resolve(strict=False) for p in paths]
for i,a in enumerate(resolved):
    for b in resolved[i+1:]:
        if a==b or a in b.parents or b in a.parents: raise SystemExit('target overlap')
PY

for pair in "$MANIFEST:$MANIFEST_SHA" "$ORIGINAL_REQUEST:$ORIGINAL_REQUEST_SHA" "$RECEIPT:$RECEIPT_SHA" "$PREPARATION_LOG:$PREPARATION_LOG_SHA" "$SUCCESS:$SUCCESS_SHA" "$RAW:$RAW_SHA"; do
    path=${pair%%:*}; expected=${pair##*:}
    test "$(/usr/bin/sha256sum "$path" | /usr/bin/awk '{print $1}')" = "$expected"
done
test "$("${GIT[@]}" -C "$SOURCE" rev-parse HEAD)" = "$MAIN_SHA"
test "$("${GIT[@]}" -C "$SOURCE/ihk" rev-parse HEAD)" = "$IHK_SHA"
test -z "$("${GIT[@]}" -C "$SOURCE" status --porcelain=1 --untracked-files=all --ignore-submodules=dirty)"
test "$("${GIT[@]}" -C "$SOURCE/ihk" status --porcelain=1 --untracked-files=all)" = " M $OVERLAY_PATH"
test "$("${GIT[@]}" -C "$SOURCE/ihk" diff --binary | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$OVERLAY_SHA"
test "$(/usr/bin/sha256sum "$SOURCE/ihk/$OVERLAY_PATH" | /usr/bin/awk '{print $1}')" = "$OVERLAY_RESULT_SHA"
test "$(/usr/bin/stat -c %a "$SOURCE/ihk/$OVERLAY_PATH")" = 644
test "$(/usr/bin/stat -c '%d:%i' "$SOURCE")" = 26:58679
test "$(/usr/bin/stat -c '%d:%i' "$SOURCE_BACKUP")" = 26:69465

exec 3>&1 4>&2
umask 0022
set -C
exec 5>"$LOG"
set +C
exec 1>&5 2>&1
finish() {
    local rc=$?
    trap - EXIT HUP INT TERM
    set +x
    echo "LIVE_CHILDREN=$(jobs -pr | /usr/bin/tr '\n' ' ')"
    echo "COPY_RC=$rc"
    echo "COPY_END_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo 'LOG_FINAL_FSYNC=PENDING'
    if "$PY" -I -B -c 'import os; os.fsync(5)' 5>&5
    then echo 'LOG_FINAL_FSYNC=PASS' >&3; else echo 'LOG_FINAL_FSYNC=FAIL' >&4; rc=74; fi
    exit "$rc"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
echo 'SCHEMA=mckernel.native-exact-candidate-disk-copy.v1'
echo "PACKET_SHA256=$(/usr/bin/sha256sum "$0" | /usr/bin/awk '{print $1}')"
echo "OWNER_PID=$$ OWNER_STARTTIME=$(/usr/bin/awk '{print $22}' /proc/$$/stat)"
set -x
STAGE=$(/usr/bin/mktemp -d -p "$SCRATCH" .mckernel-exact-copy-76ae20b5-XXXXXXXX)
/usr/bin/chmod 0700 "$STAGE"
readonly STAGE
readonly PARTIAL="$STAGE/candidate"
readonly PARTIAL_BACKUP="$STAGE/backup"
readonly STAGE_ID="$(/usr/bin/stat -c '%d:%i' "$STAGE")"
echo "STAGE=$STAGE STAGE_ID=$STAGE_ID"

"$PY" -I -B - "$SCRATCH" "$SOURCE" "$SOURCE_BACKUP" <<'PY'
import os,pathlib,sys
scratch=pathlib.Path(sys.argv[1]); roots=[pathlib.Path(x) for x in sys.argv[2:]]
if scratch.stat().st_dev == pathlib.Path('/').stat().st_dev: raise SystemExit('scratch not distinct')
need=sum(sum(e.stat(follow_symlinks=False).st_blocks*512 for b,ds,fs in os.walk(r,followlinks=False) for e in [*(os.scandir(b))] if not e.is_symlink()) for r in roots)
free=os.statvfs(str(scratch)).f_bavail*os.statvfs(str(scratch)).f_frsize
print('COPY_CAPACITY',need,free)
if free-need < (12<<30): raise SystemExit('scratch post-copy floor failed')
PY

inventory() {
    "$PY" -I -B - "$1" "$2" "$3" <<'PY'
import hashlib,json,os,pathlib,stat,sys
out=pathlib.Path(sys.argv[1]); labels=sys.argv[2].split(','); roots=[pathlib.Path(x) for x in sys.argv[3].split(',')]
rows=[]; snapshots=[]
def identity(st):
    return [st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_nlink,st.st_uid,st.st_gid,st.st_mtime_ns,st.st_ctime_ns]
def same(left,right,what):
    if identity(left) != identity(right): raise SystemExit('entry changed '+what)
def walk(root,label,dirfd,rel):
    dir_before=os.fstat(dirfd); row={'root':label,'path':str(rel),'type':'dir','mode':stat.S_IMODE(dir_before.st_mode),'uid':dir_before.st_uid,'gid':dir_before.st_gid,'mtime_ns':dir_before.st_mtime_ns}; rows.append(row); snapshots.append({'root':label,'path':str(rel),'identity':identity(dir_before)})
    names=sorted(os.listdir(dirfd),key=os.fsencode)
    for name in names:
        childrel=rel/name; before=os.stat(name,dir_fd=dirfd,follow_symlinks=False); mode=stat.S_IMODE(before.st_mode)
        row={'root':label,'path':str(childrel),'mode':mode,'uid':before.st_uid,'gid':before.st_gid,'mtime_ns':before.st_mtime_ns}
        if stat.S_ISDIR(before.st_mode):
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirfd)
            try: same(before,os.fstat(fd),str(childrel)); walk(root,label,fd,childrel); same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            finally: os.close(fd)
            continue
        if stat.S_ISREG(before.st_mode):
            if before.st_nlink != 1: raise SystemExit('hardlinked file '+str(childrel))
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dirfd); h=hashlib.sha256()
            with os.fdopen(fd,'rb') as f:
                same(before,os.fstat(f.fileno()),str(childrel))
                for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
                same(before,os.fstat(f.fileno()),str(childrel))
            same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            row.update(type='file',size=before.st_size,sha256=h.hexdigest())
        elif stat.S_ISLNK(before.st_mode):
            target=os.readlink(name,dir_fd=dirfd); same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            try: resolved=(root/childrel).resolve(strict=True); resolved.relative_to(root)
            except (OSError,RuntimeError,ValueError): raise SystemExit('escaping, dangling, or cyclic symlink '+str(childrel))
            row.update(type='symlink',size=before.st_size,target=target)
        else: raise SystemExit('special file '+str(childrel))
        rows.append(row); snapshots.append({'root':label,'path':str(childrel),'identity':identity(before)})
    same(dir_before,os.fstat(dirfd),str(rel))
for label,root in zip(labels,roots):
    if root.is_symlink() or not root.is_dir(): raise SystemExit('invalid root '+str(root))
    root=root.resolve(strict=True); initial=root.lstat(); fd=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: same(initial,os.fstat(fd),str(root)); walk(root,label,fd,pathlib.Path('.')); same(initial,os.fstat(fd),str(root)); same(initial,root.lstat(),str(root))
    finally: os.close(fd)
payload={'schema':'mckernel.exact-tree-inventory.v2','roots':labels,'rows':rows,'snapshots':snapshots}
raw=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode(); fd=os.open(str(out),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
PY
}

inventory "$SOURCE_INVENTORY" source,backup "$SOURCE,$SOURCE_BACKUP"
test "$(/usr/bin/stat -c '%d:%i' "$STAGE")" = "$STAGE_ID"
/usr/bin/cp -a --no-clobber --reflink=never -- "$SOURCE" "$PARTIAL"
/usr/bin/cp -a --no-clobber --reflink=never -- "$SOURCE_BACKUP" "$PARTIAL_BACKUP"
inventory "$DEST_INVENTORY" source,backup "$PARTIAL,$PARTIAL_BACKUP"
"$PY" -I -B - "$SOURCE_INVENTORY" "$DEST_INVENTORY" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
if a['rows'] != b['rows']: raise SystemExit('copy inventory differs')
PY
inventory "$SOURCE_POST_INVENTORY" source,backup "$SOURCE,$SOURCE_BACKUP"
/usr/bin/cmp -s "$SOURCE_INVENTORY" "$SOURCE_POST_INVENTORY"
"$PY" -I -B - "$PARTIAL" "$PARTIAL_BACKUP" <<'PY'
import os,pathlib,stat,sys
for root in map(pathlib.Path,sys.argv[1:]):
    dirs=[]
    for base,names,files in os.walk(root,topdown=True,followlinks=False):
        dirs.append(pathlib.Path(base))
        for name in files:
            p=pathlib.Path(base)/name
            if p.is_symlink(): continue
            fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
    for p in reversed(dirs):
        fd=os.open(str(p),os.O_RDONLY|os.O_DIRECTORY); os.fsync(fd); os.close(fd)
PY
inventory "$DEST_POST_INVENTORY" source,backup "$PARTIAL,$PARTIAL_BACKUP"
/usr/bin/cmp -s "$DEST_INVENTORY" "$DEST_POST_INVENTORY"
test "$(/usr/bin/stat -c '%d:%i' "$STAGE")" = "$STAGE_ID"
"$PY" -I -B - "$PARTIAL" "$DEST" "$PARTIAL_BACKUP" "$DEST_BACKUP" "$STAGE" "$SCRATCH" <<'PY'
import ctypes,errno,os,sys
libc=ctypes.CDLL(None,use_errno=True); renameat2=libc.renameat2; renameat2.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; renameat2.restype=ctypes.c_int
for source,dest in ((sys.argv[1],sys.argv[2]),(sys.argv[3],sys.argv[4])):
    if renameat2(-100,os.fsencode(source),-100,os.fsencode(dest),1):
        value=ctypes.get_errno(); raise OSError(value,os.strerror(value),dest)
for parent in sys.argv[5:]:
    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
PY

test "$("${GIT[@]}" -C "$DEST" rev-parse HEAD)" = "$MAIN_SHA"
test "$("${GIT[@]}" -C "$DEST/ihk" rev-parse HEAD)" = "$IHK_SHA"
test -z "$("${GIT[@]}" -C "$DEST" status --porcelain=1 --untracked-files=all --ignore-submodules=dirty)"
test "$("${GIT[@]}" -C "$DEST/ihk" status --porcelain=1 --untracked-files=all)" = " M $OVERLAY_PATH"
test "$("${GIT[@]}" -C "$DEST/ihk" diff --binary | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = "$OVERLAY_SHA"

/usr/bin/mkdir --mode=0755 "$OUTPUT" "$EVIDENCE"
"$PY" -I -B - "$ORIGINAL_REQUEST" "$REQUEST" "$DEST" "$DEST_BACKUP" "$OUTPUT" "$EVIDENCE" "$LEASE" "$ORIGINAL_REQUEST_SHA" <<'PY'
import json,os,pathlib,sys
source,out,dest,backup,build,evidence,lease,origin_sha=sys.argv[1:]
d=json.load(open(source)); d.update(source_root=dest,driver_path=str(pathlib.Path(dest)/'scripts/native_rust_exact_build_offline.py'),output_root=build,evidence_root=evidence,lease_path=lease,memory_allocation_roots=[dest,backup],origin_request_sha256=origin_sha)
raw=(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode(); fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
PY
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 "$PY" -I -B - "$DEST" "$REQUEST" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/'scripts'))
import native_rust_exact_build_container_owner as owner
r=json.load(open(sys.argv[2])); checked=owner.BuildOwner(r); checked.validate()
if checked.measurement['memory_allocation_memory_backed_bytes'] != 0: raise SystemExit('disk candidate still memory-backed')
if checked.measurement['aggregate_memory_required'] != 12*(2**30): raise SystemExit('unexpected aggregate')
print('PASS_DISK_COPY_VALIDATE_ONLY',json.dumps(checked.measurement,sort_keys=True))
PY
test ! -e "$LEASE" && test ! -L "$LEASE"
"$PY" -I -B - "$SCRATCH" <<'PY'
import os,sys
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
PY
echo PASS_DISK_COPY_VALIDATE_ONLY
