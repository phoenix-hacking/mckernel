#!/bin/bash
set -Eeuo pipefail

# Fresh validation-only recovery after the retained copy/correction failures.
# This packet never repairs or deletes either tree and never builds or acquires
# a lease. The copy-time inventory, not the corrupt tmpfs tree, is authoritative.
readonly RELEASE_HASH=f0a625768a4d10c6bf42794cc502148c5bac6b13683f5c3bb37138a4f922f303
readonly ROOT=/home/holden/mckernel-work/scratch
readonly REPO=/home/holden/mckernel
readonly CANDIDATE="$ROOT/mckernel-exact-candidate-76ae20b5-disk-1"
readonly BACKUP="$ROOT/mckernel-exact-metadata-backup-76ae20b5-disk-1"
readonly TMPFS=/dev/shm/mckernel-exact-candidate-76ae20b5-1
readonly REL=docs/verification/evidence/stability-linux-collector-storage-fault-v2-source-review-input-20260916-57.tar.gz
readonly LOG="$ROOT/native-exact-candidate-disk-validation-76ae20b5-2.log"
readonly OUT="$ROOT/native-exact-candidate-disk-validation-76ae20b5-2-output"
readonly EVIDENCE="$ROOT/native-exact-candidate-disk-validation-76ae20b5-2-evidence"
readonly REQUEST="$ROOT/native-exact-build-request-76ae20b5-disk-validation-2.json"
readonly LEASE="$ROOT/native-exact-build-lease-76ae20b5-disk-validation-2.json"
readonly PRE="$ROOT/native-exact-candidate-disk-validation-76ae20b5-2-pre.json"
readonly POST="$ROOT/native-exact-candidate-disk-validation-76ae20b5-2-post.json"
readonly SOURCE_INV="$ROOT/native-exact-candidate-disk-copy-76ae20b5-source.json"
readonly PRIOR_REQUEST="$ROOT/native-exact-build-request-76ae20b5-disk-1.json"
readonly FAILURE_RECORD="$REPO/docs/verification/evidence/stability-native-exact-candidate-disk-copy-failures-76ae20b5-20260929-1.json"
readonly PY=/usr/bin/python3
readonly -a GIT=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file GIT_OPTIONAL_LOCKS=0 /usr/bin/git)

if (( EUID == 0 )); then echo 'refusing root validation' >&2; exit 1; fi
if [[ "$RELEASE_HASH" == RELEASE_HASH_REQUIRED ]]; then echo TEMPLATE_ONLY >&2; exit 78; fi
"$PY" -I -B - "$LOG" "$OUT" "$EVIDENCE" "$REQUEST" "$LEASE" "$PRE" "$POST" <<'PY'
import os,sys
for path in sys.argv[1:]:
    if os.path.lexists(path): raise SystemExit('fresh target exists: '+path)
PY
exec 3>&1 4>&2
umask 0022
set -C; exec 5>"$LOG"; set +C
exec 1>&5 2>&1
finish() {
    local rc=$?
    trap - EXIT HUP INT TERM
    echo "VALIDATION_RC=$rc"
    echo "LIVE_CHILDREN=$(jobs -pr | /usr/bin/tr '\n' ' ')"
    echo "VALIDATION_END_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo LOG_FINAL_FSYNC=PENDING
    if "$PY" -I -B -c 'import os; os.fsync(5)' 5>&5; then echo LOG_FINAL_FSYNC=PASS >&3; else echo LOG_FINAL_FSYNC=FAIL >&4; rc=74; fi
    exit "$rc"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

/usr/bin/mkdir -m 0700 "$OUT" "$EVIDENCE" "$OUT/build" "$EVIDENCE/build"
"$PY" -I -B - "$CANDIDATE" "$BACKUP" "$TMPFS/$REL" "$CANDIDATE/$REL" "$REPO/$REL" "$EVIDENCE" "$REQUEST" "$PRIOR_REQUEST" "$FAILURE_RECORD" <<'PY'
import hashlib,json,os,pathlib,stat,sys
cand,backup,corrupt,disk,repo,evidence,request,prior,failure=map(pathlib.Path,sys.argv[1:])
for path,identity in ((cand,(1831,4194306)),(backup,(1831,4204970))):
    st=path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(st.st_mode) or (st.st_dev,st.st_ino)!=identity: raise SystemExit('disk root identity differs '+str(path))
def read_exact(path):
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1: raise SystemExit('unsafe file '+str(path))
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC); opened=os.fstat(fd); h=hashlib.sha256(); chunks=[]
    key=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if key(opened)!=key(before): raise SystemExit('opened identity differs '+str(path))
    with os.fdopen(fd,'rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''): h.update(chunk); chunks.append(chunk)
        after=os.fstat(stream.fileno())
    final=path.lstat()
    if key(after)!=key(before) or key(final)!=key(before): raise SystemExit('file changed during read '+str(path))
    return before,h.hexdigest(),chunks
checks=(
 ('/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-disk-copy-correction-76ae20b5-1.sh','431e26b1d2c5acb2c4c0c586b3f3bcbd1dea88e51ac5bdf57613fe774cd7f2d3'),
 ('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-correction-76ae20b5-1.log','b55411a9259806c99391988216117943984b68bfe826e2eb81cf237de0d482d9'),
 ('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-correction-76ae20b5-source-final.json','5d7f6c035d03518349512d7818a2d00d28213c2e0f3f04f3325632c7536efd71'),
 ('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-correction-76ae20b5-dest-final.json','842f4522c0ff318aee68cb3387eca604e435f06aef334e125c7d2c6897d526ae'),
 ('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-76ae20b5-source.json','e2a7cd887df743587dd05c9d9e63252829e4ad004f7954a143760b3af752190c'),
 ('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-76ae20b5-dest.json','6afcf2d1f260bc30b08f21ebf133af3cfc0a9410f3c69f0dfd221ecff4e4c2ba'),
 ('/home/holden/mckernel-work/scratch/native-exact-build-request-76ae20b5-disk-1.json','60e530948104cb6d084fde56137b8662786fd383528080e15b7529616f697ce4'),
 (str(failure),'f4ee6d4c458243c566a5c29fcc0023475d16df78170e111dfc110ddae51ca304'))
for raw,expected in checks:
    if read_exact(pathlib.Path(raw))[1] != expected: raise SystemExit('bound evidence hash differs '+raw)
st,digest,chunks=read_exact(corrupt)
if (st.st_dev,st.st_ino,st.st_size,stat.S_IMODE(st.st_mode),st.st_uid,st.st_gid,st.st_mtime_ns,st.st_ctime_ns)!=(26,61269,40004941,0o644,1000,1000,1790718828650569056,1790718828650569056): raise SystemExit('corrupt archive identity differs')
if digest!='192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c': raise SystemExit('corrupt archive bytes differ')
sealed=evidence/'corrupt-tmpfs-archive.bin'; fd=os.open(str(sealed),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as stream:
    for chunk in chunks: stream.write(chunk)
    stream.flush(); os.fsync(stream.fileno())
sealed_st,sealed_digest,_=read_exact(sealed)
if sealed_digest!=digest or sealed_st.st_size!=st.st_size: raise SystemExit('sealed corrupt archive differs')
for path in (disk,repo):
    if read_exact(path)[1] != 'dbe24f5b7cdd94f9ba2f9846073b6b2cd6e5f00ffca55f4ce99d4343261b5100': raise SystemExit('authenticated archive differs '+str(path))
meta={'schema':'mckernel.tmpfs-divergence-seal.v1','source':str(corrupt),'device':st.st_dev,'inode':st.st_ino,'size':st.st_size,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'sha256':digest,'zero_based_offset':37352801,'observed_byte_hex':'bb','authenticated_byte_hex':'3b'}
fd=os.open(str(evidence/'corrupt-tmpfs-archive.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream: json.dump(meta,stream,sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
data=json.loads(prior.read_text()); data.update(source_root=str(cand),driver_path=str(cand/'scripts/native_rust_exact_build_offline.py'),output_root=str(evidence.parent/(evidence.name.replace('-evidence','-output'))/'build'),evidence_root=str(evidence/'build'),lease_path='/home/holden/mckernel-work/scratch/native-exact-build-lease-76ae20b5-disk-validation-2.json',memory_allocation_roots=[str(cand),str(backup)],origin_request_sha256='60e530948104cb6d084fde56137b8662786fd383528080e15b7529616f697ce4')
fd=os.open(str(request),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream: json.dump(data,stream,sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
for path in (evidence,evidence.parent):
    fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
PY

set +e
gzip_error=$(/usr/bin/gzip -t "$EVIDENCE/corrupt-tmpfs-archive.bin" 2>&1)
gzip_rc=$?
set -e
test "$gzip_rc" -eq 1
case "$gzip_error" in
  *'invalid compressed data--crc error'*) echo EXPECTED_CORRUPT_GZIP_FAIL ;;
  *) echo "unexpected corrupt gzip result: $gzip_error" >&2; exit 1 ;;
esac
/usr/bin/gzip -t "$CANDIDATE/$REL"
/usr/bin/gzip -t "$REPO/$REL"
test "$("${GIT[@]}" -C "$REPO" show 76ae20b523f57dee8e0fb1fb834caf5443f9f671:"$REL" | /usr/bin/sha256sum | /usr/bin/awk '{print $1}')" = dbe24f5b7cdd94f9ba2f9846073b6b2cd6e5f00ffca55f4ce99d4343261b5100
"${GIT[@]}" -C "$REPO" show 76ae20b523f57dee8e0fb1fb834caf5443f9f671:"$REL" | /usr/bin/gzip -t

inventory() {
    "$PY" -I -B - "$1" "$2" "$3" <<'PY'
import hashlib,json,os,pathlib,stat,sys
out=pathlib.Path(sys.argv[1]); labels=sys.argv[2].split(','); roots=[pathlib.Path(x) for x in sys.argv[3].split(',')]; rows=[]; snapshots=[]
def identity(st): return [st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_nlink,st.st_uid,st.st_gid,st.st_mtime_ns,st.st_ctime_ns]
def same(a,b,name):
    if identity(a)!=identity(b): raise SystemExit('entry changed '+name)
def walk(root,label,dirfd,rel):
    initial=os.fstat(dirfd); rows.append({'root':label,'path':str(rel),'type':'dir','mode':stat.S_IMODE(initial.st_mode),'uid':initial.st_uid,'gid':initial.st_gid,'mtime_ns':initial.st_mtime_ns}); snapshots.append({'root':label,'path':str(rel),'identity':identity(initial)})
    for name in sorted(os.listdir(dirfd),key=os.fsencode):
        child=rel/name; before=os.stat(name,dir_fd=dirfd,follow_symlinks=False); row={'root':label,'path':str(child),'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,'gid':before.st_gid,'mtime_ns':before.st_mtime_ns}
        if stat.S_ISDIR(before.st_mode):
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirfd)
            try: same(before,os.fstat(fd),str(child)); walk(root,label,fd,child); same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(child))
            finally: os.close(fd)
            continue
        if stat.S_ISREG(before.st_mode):
            if before.st_nlink!=1: raise SystemExit('hardlinked file '+str(child))
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dirfd); h=hashlib.sha256()
            with os.fdopen(fd,'rb') as stream:
                same(before,os.fstat(stream.fileno()),str(child))
                for chunk in iter(lambda:stream.read(1048576),b''): h.update(chunk)
                same(before,os.fstat(stream.fileno()),str(child))
            same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(child)); row.update(type='file',size=before.st_size,sha256=h.hexdigest())
        elif stat.S_ISLNK(before.st_mode):
            target=os.readlink(name,dir_fd=dirfd); same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(child))
            try: (root/child).resolve(strict=True).relative_to(root)
            except (OSError,RuntimeError,ValueError): raise SystemExit('escaping, dangling, or cyclic symlink '+str(child))
            row.update(type='symlink',size=before.st_size,target=target)
        else: raise SystemExit('special file '+str(child))
        rows.append(row); snapshots.append({'root':label,'path':str(child),'identity':identity(before)})
    same(initial,os.fstat(dirfd),str(rel))
for label,root in zip(labels,roots):
    if root.is_symlink() or not root.is_dir(): raise SystemExit('invalid root '+str(root))
    root=root.resolve(strict=True); initial=root.lstat(); fd=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: same(initial,os.fstat(fd),str(root)); walk(root,label,fd,pathlib.Path('.')); same(initial,os.fstat(fd),str(root)); same(initial,root.lstat(),str(root))
    finally: os.close(fd)
raw=(json.dumps({'schema':'mckernel.exact-tree-inventory.v2','roots':labels,'rows':rows,'snapshots':snapshots},sort_keys=True,separators=(',',':'))+'\n').encode(); fd=os.open(str(out),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
PY
}
compare_retained() {
    "$PY" -I -B - "$SOURCE_INV" "$1" <<'PY'
import json,sys
old=json.load(open(sys.argv[1]))['rows']; new=json.load(open(sys.argv[2]))['rows']
for row in old:
    if row['root']=='source': row['root']='candidate'
if old!=new: raise SystemExit('disk inventory differs from authenticated copy-time source')
if len(new)!=10751: raise SystemExit('unexpected inventory row count')
PY
}
inventory "$PRE" candidate,backup "$CANDIDATE,$BACKUP"
compare_retained "$PRE"

GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 "$PY" -I -B - "$CANDIDATE" "$REQUEST" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/'scripts'))
import native_rust_exact_build_container_owner as owner
owner.provenance.ENV=dict(owner.provenance.ENV,GIT_OPTIONAL_LOCKS='0')
owner.BuildOwner(json.load(open(sys.argv[2]))).validate(); print('PASS_VALIDATE_ONLY')
PY
test "$("${GIT[@]}" -C "$CANDIDATE" rev-parse HEAD)" = 76ae20b523f57dee8e0fb1fb834caf5443f9f671
test "$("${GIT[@]}" -C "$CANDIDATE/ihk" rev-parse HEAD)" = 3114d9e7101ad52030eb3effa849a5c108972a1f
inventory "$POST" candidate,backup "$CANDIDATE,$BACKUP"
/usr/bin/cmp -s "$PRE" "$POST"
compare_retained "$POST"
"$PY" -I -B - "$ROOT" "$OUT" "$EVIDENCE" <<'PY'
import os,sys
for path in sys.argv[1:]:
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
PY
test ! -e "$LEASE" && test ! -L "$LEASE"
echo PASS_DISK_VALIDATION
