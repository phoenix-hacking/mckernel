#!/bin/bash
set -Eeuo pipefail

# Bounded correction for the completed disk-copy attempt.  This packet is
# source-reviewed only: it preserves the original failure before repairing the
# two destination Git indexes, performs validate-only provenance checks, and
# never builds, acquires a lease, deletes a root, or starts a guest.
readonly RELEASE_HASH=6603bc25f3c4b4f49a909fac73097a2d5f54b59d4da292868393e0a4b57030db
readonly SOURCE=/dev/shm/mckernel-exact-candidate-76ae20b5-1
readonly SOURCE_BACKUP=/dev/shm/mckernel-exact-metadata-backup-76ae20b5-1
readonly DEST=/home/holden/mckernel-work/scratch/mckernel-exact-candidate-76ae20b5-disk-1
readonly DEST_BACKUP=/home/holden/mckernel-work/scratch/mckernel-exact-metadata-backup-76ae20b5-disk-1
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly LOG="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-1.log"
readonly EVIDENCE="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-1-evidence"
readonly BUILD_EVIDENCE="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-1-build-evidence"
readonly OUTPUT="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-1-output"
readonly SOURCE_FINAL="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-source-final.json"
readonly DEST_FINAL="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-dest-final.json"
readonly SOURCE_FINAL_POST="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-source-final-post.json"
readonly DEST_FINAL_POST="$SCRATCH/native-exact-candidate-disk-copy-correction-76ae20b5-dest-final-post.json"
readonly REQUEST="$SCRATCH/native-exact-build-request-76ae20b5-disk-correction-1.json"
readonly LEASE="$SCRATCH/native-exact-build-lease-76ae20b5-disk-correction-1.json"
readonly ORIGINAL_REQUEST=/home/holden/mckernel-work/scratch/native-exact-build-request-76ae20b5-1.json
readonly ORIGINAL_REQUEST_SHA=a483f42764f27b9785ff1465d35fd22632c9a2535664868b8f81655e96044d4a
readonly MAIN_SHA=76ae20b523f57dee8e0fb1fb834caf5443f9f671
readonly IHK_SHA=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly SOURCE_ID=26:58679
readonly SOURCE_BACKUP_ID=26:69465
readonly DEST_ID=1831:4194306
readonly DEST_BACKUP_ID=1831:4204970
readonly DEST_INDEX_LIVE_PREFIX=c6424e95
readonly DEST_INDEX_RETAINED_PREFIX=5eb0ec6b
readonly DEST_IHK_INDEX_LIVE_PREFIX=ef0e589b
readonly DEST_IHK_INDEX_RETAINED_PREFIX=e46facca
readonly DEST_INDEX_LIVE_SHA256=c6424e950e0792d151156031cea7bd0e3e4409e86fbe4d71fb975b3b5f351bd0
readonly DEST_IHK_INDEX_LIVE_SHA256=ef0e589b930fcb74e50ac823213a32bd91ae8a25a4ec12d7ad77bb027548d3b3
readonly SOURCE_INDEX_SHA256=5eb0ec6bf2d5ed0d53e7ae3a932223addf0dc9f8cc80577cf2999fc3ae0533e5
readonly SOURCE_IHK_INDEX_SHA256=e46faccad76f30c24e2c3b20d786cf071b2ed8fa1c7cf4da906df4684f133ea2
readonly ORIGINAL_PACKET_SHA256=47ba9d86d96ff2bf5f70b5fa92282fa6d153255e49fd93e5210ce424b7b39ea2
readonly ORIGINAL_LOG_SHA256=87f2494a6bfb08339e587cfdbd19c47064b4ef7cfe3c0fbef0209b7af090820c
readonly SOURCE_INVENTORY_SHA256=e2a7cd887df743587dd05c9d9e63252829e4ad004f7954a143760b3af752190c
readonly DEST_INVENTORY_SHA256=6afcf2d1f260bc30b08f21ebf133af3cfc0a9410f3c69f0dfd221ecff4e4c2ba
readonly DERIVED_REQUEST_SHA256=60e530948104cb6d084fde56137b8662786fd383528080e15b7529616f697ce4
readonly PRIOR_DERIVED_REQUEST=/home/holden/mckernel-work/scratch/native-exact-build-request-76ae20b5-disk-1.json
readonly DEST_INDEX_LIVE_SIZE=1006644
readonly DEST_IHK_INDEX_LIVE_SIZE=153023
readonly DEST_IHK_INDEX_RETAINED_SIZE=152971
readonly DEST_INDEX="$DEST/.git/index"
readonly DEST_IHK_INDEX="$DEST/ihk/.git/index"
readonly SOURCE_INDEX="$SOURCE/.git/index"
readonly SOURCE_IHK_INDEX="$SOURCE/ihk/.git/index"
readonly PY=/usr/bin/python3
readonly -a GIT=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file GIT_OPTIONAL_LOCKS=0 /usr/bin/git)

if (( EUID == 0 )); then echo 'refusing root correction' >&2; exit 1; fi
if [[ "$RELEASE_HASH" == RELEASE_HASH_REQUIRED ]]; then echo TEMPLATE_ONLY >&2; exit 78; fi
"$PY" -I -B - "$LOG" "$EVIDENCE" "$BUILD_EVIDENCE" "$OUTPUT" "$REQUEST" "$LEASE" "$SOURCE_FINAL" "$DEST_FINAL" "$SOURCE_FINAL_POST" "$DEST_FINAL_POST" <<'PY'
import os,sys
for raw in sys.argv[1:]:
    if os.path.lexists(raw): raise SystemExit('fresh output exists: '+raw)
PY
exec 3>&1 4>&2
umask 0022
set -C
exec 5>"$LOG"
set +C
exec 1>&5 2>&1
finish() { local rc=$?; trap - EXIT; echo "CORRECTION_RC=$rc"; echo "LIVE_CHILDREN=$(jobs -pr | /usr/bin/tr '\n' ' ')"; echo "CORRECTION_END_UTC=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"; echo LOG_FINAL_FSYNC=PENDING; if "$PY" -I -B -c 'import os; os.fsync(5)' 5>&5; then echo LOG_FINAL_FSYNC=PASS >&3; else echo LOG_FINAL_FSYNC=FAIL >&4; rc=74; fi; exit "$rc"; }
trap finish EXIT

"$PY" -I -B - "$SOURCE" "$SOURCE_BACKUP" "$DEST" "$DEST_BACKUP" "$EVIDENCE" "$BUILD_EVIDENCE" "$LOG" "$REQUEST" "$SOURCE_FINAL" "$DEST_FINAL" "$SOURCE_FINAL_POST" "$DEST_FINAL_POST" <<'PY'
import hashlib, json, os, pathlib, shutil, stat, sys
source, source_backup, dest, dest_backup, evidence, build_evidence, log, request, *outs = map(pathlib.Path, sys.argv[1:])
for p in (source, source_backup, dest, dest_backup):
    if p.is_symlink() or not p.is_dir(): raise SystemExit('invalid root '+str(p))
output=pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-correction-76ae20b5-1-output')
for p in (evidence,build_evidence,output):
    if p.exists() or p.is_symlink(): raise SystemExit('output already exists '+str(p))
    p.mkdir(mode=0o700)
    os.fsync(os.open(str(p.parent), os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
for p in (request, *outs):
    if p.exists() or p.is_symlink(): raise SystemExit('output already exists '+str(p))
if (source.stat().st_dev,source.stat().st_ino) != (26,58679): raise SystemExit('source identity drift')
if (source_backup.stat().st_dev,source_backup.stat().st_ino) != (26,69465): raise SystemExit('backup identity drift')
if (dest.stat().st_dev,dest.stat().st_ino) != (1831,4194306): raise SystemExit('destination identity drift')
if (dest_backup.stat().st_dev,dest_backup.stat().st_ino) != (1831,4204970): raise SystemExit('destination backup identity drift')

def safe_file(path):
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1: raise SystemExit('unsafe file '+str(path))
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    opened=os.fstat(fd)
    if (opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns)!=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns): raise SystemExit('identity drift '+str(path))
    chunks=[]; remaining=opened.st_size+1
    while remaining:
        chunk=os.read(fd,min(1048576,remaining))
        if not chunk: break
        chunks.append(chunk); remaining-=len(chunk)
    after=os.fstat(fd); os.close(fd); data=b''.join(chunks)
    if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)!=(opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns): raise SystemExit('file changed during read '+str(path))
    final=path.lstat()
    if (final.st_dev,final.st_ino,final.st_size,final.st_mtime_ns,final.st_ctime_ns)!=(opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns): raise SystemExit('path changed during read '+str(path))
    if len(data)!=opened.st_size: raise SystemExit('short read '+str(path))
    return st,data
def check_hash(path,expected):
    if hashlib.sha256(safe_file(path)[1]).hexdigest() != expected: raise SystemExit('bound hash mismatch '+str(path))
for path,expected in ((pathlib.Path('/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-disk-copy-76ae20b5-1.sh'),'47ba9d86d96ff2bf5f70b5fa92282fa6d153255e49fd93e5210ce424b7b39ea2'),(pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-76ae20b5-1.log'),'87f2494a6bfb08339e587cfdbd19c47064b4ef7cfe3c0fbef0209b7af090820c'),(pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-76ae20b5-source.json'),'e2a7cd887df743587dd05c9d9e63252829e4ad004f7954a143760b3af752190c'),(pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-candidate-disk-copy-76ae20b5-dest.json'),'6afcf2d1f260bc30b08f21ebf133af3cfc0a9410f3c69f0dfd221ecff4e4c2ba'),(pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-build-request-76ae20b5-disk-1.json'),'60e530948104cb6d084fde56137b8662786fd383528080e15b7529616f697ce4')): check_hash(path,expected)
check_hash(source/'.git/index','5eb0ec6bf2d5ed0d53e7ae3a932223addf0dc9f8cc80577cf2999fc3ae0533e5'); check_hash(source/'ihk/.git/index','e46faccad76f30c24e2c3b20d786cf071b2ed8fa1c7cf4da906df4684f133ea2')
check_hash(dest/'.git/index','c6424e950e0792d151156031cea7bd0e3e4409e86fbe4d71fb975b3b5f351bd0'); check_hash(dest/'ihk/.git/index','ef0e589b930fcb74e50ac823213a32bd91ae8a25a4ec12d7ad77bb027548d3b3')
def seal(name, path):
    st,data=safe_file(path)
    target=evidence/name
    fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    meta={'path':str(path),'device':st.st_dev,'inode':st.st_ino,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'sha256':hashlib.sha256(data).hexdigest()}
    write_sidecar(name+'.json',meta)
    return meta
def write_sidecar(name,obj):
    target=evidence/name; fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: json.dump(obj,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
def dir_meta(path):
    st=path.lstat()
    if not stat.S_ISDIR(st.st_mode): raise SystemExit('not directory '+str(path))
    return {'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
def fsync_parent(path):
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)

# Preserve the original changed destination bytes and metadata before repair.
for label,path in (('dest-index',dest/'.git/index'),('dest-ihk-index',dest/'ihk/.git/index')): seal(label,path)
for label,path in (('dest-git-dir',dest/'.git'),('dest-ihk-git-dir',dest/'ihk/.git')):
    write_sidecar(label+'.json',{'path':str(path),'metadata':dir_meta(path)})
for label,path in (('source-index',source/'.git/index'),('source-ihk-index',source/'ihk/.git/index')): seal(label,path)
for label,path in (('source-git-dir',source/'.git'),('source-ihk-git-dir',source/'ihk/.git')):
    write_sidecar(label+'.json',{'path':str(path),'metadata':dir_meta(path)})
for name in ('dest-index','dest-ihk-index','source-index','source-ihk-index'):
    check_hash(evidence/name, {'dest-index':'c6424e950e0792d151156031cea7bd0e3e4409e86fbe4d71fb975b3b5f351bd0','dest-ihk-index':'ef0e589b930fcb74e50ac823213a32bd91ae8a25a4ec12d7ad77bb027548d3b3','source-index':'5eb0ec6bf2d5ed0d53e7ae3a932223addf0dc9f8cc80577cf2999fc3ae0533e5','source-ihk-index':'e46faccad76f30c24e2c3b20d786cf071b2ed8fa1c7cf4da906df4684f133ea2'}[name])
fd=os.open(str(evidence),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
fd=os.open(str(evidence.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)

def restore(src,dst):
    sealed='source-ihk-index' if src.parent.parent.name == 'ihk' else 'source-index'
    _,data=safe_file(evidence/sealed); meta=json.loads((evidence/(sealed+'.json')).read_text()); dstst=dst.lstat()
    if not stat.S_ISREG(dstst.st_mode) or dstst.st_nlink != 1: raise SystemExit('destination index unsafe '+str(dst))
    live_hash=hashlib.sha256(safe_file(dst)[1]).hexdigest()
    key='ihk/index' if dst.parent.parent.name == 'ihk' else 'index'
    expected={'index':'c6424e950e0792d151156031cea7bd0e3e4409e86fbe4d71fb975b3b5f351bd0','ihk/index':'ef0e589b930fcb74e50ac823213a32bd91ae8a25a4ec12d7ad77bb027548d3b3'}[key]
    if live_hash != expected: raise SystemExit('destination live index hash drift '+str(dst))
    fd=os.open(str(dst),os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        opened=os.fstat(fd)
        if (opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns)!=(dstst.st_dev,dstst.st_ino,dstst.st_size,dstst.st_mtime_ns,dstst.st_ctime_ns): raise SystemExit('destination identity changed '+str(dst))
        os.ftruncate(fd,0); view=memoryview(data)
        while view:
            n=os.write(fd,view); view=view[n:]
        os.fchmod(fd,meta['mode']); os.fchown(fd,meta['uid'],meta['gid'])
        os.utime(fd,ns=(meta['mtime_ns'],meta['mtime_ns'])); os.fsync(fd)
    finally: os.close(fd)
    after=dst.lstat()
    if after.st_size != meta['size'] or hashlib.sha256(safe_file(dst)[1]).hexdigest() != meta['sha256']: raise SystemExit('restored index verification failed '+str(dst))
    fsync_parent(dst)
def restore_dir(label,dst):
    s=json.loads((evidence/(label+'.json')).read_text())['metadata']; fd=os.open(str(dst),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); opened=os.fstat(fd); d=dst.lstat()
    if (opened.st_dev,opened.st_ino,opened.st_mode,opened.st_mtime_ns,opened.st_ctime_ns)!=(d.st_dev,d.st_ino,d.st_mode,d.st_mtime_ns,d.st_ctime_ns): raise SystemExit('directory identity changed '+str(dst))
    os.fchmod(fd,s['mode']); os.fchown(fd,s['uid'],s['gid']); os.utime(fd,ns=(s['mtime_ns'],s['mtime_ns'])); os.fsync(fd); os.close(fd); fsync_parent(dst)
restore(source/'.git/index',dest/'.git/index'); restore(source/'ihk/.git/index',dest/'ihk/.git/index')
restore_dir('source-git-dir',dest/'.git'); restore_dir('source-ihk-git-dir',dest/'ihk/.git')
for p in (dest/'.git/index',dest/'ihk/.git/index',dest/'.git',dest/'ihk/.git'): safe_file(p) if p.name=='index' else dir_meta(p)
for p in (evidence,):
    fd=os.open(str(p),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
orig=pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-build-request-76ae20b5-disk-1.json')
request_data=json.loads(orig.read_text()); request_data.update(source_root=str(dest),driver_path=str(dest/'scripts/native_rust_exact_build_offline.py'),output_root=str(output),evidence_root=str(build_evidence),lease_path='/home/holden/mckernel-work/scratch/native-exact-build-lease-76ae20b5-disk-correction-1.json',memory_allocation_roots=[str(dest),str(dest_backup)],origin_request_sha256='60e530948104cb6d084fde56137b8662786fd383528080e15b7529616f697ce4')
fd=os.open(str(request),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'w') as f: json.dump(request_data,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
fsync_parent(log); fsync_parent(request)
PY

inventory() {
  "$PY" -I -B - "$1" "$2" "$3" <<'PY'
import hashlib,json,os,pathlib,stat,sys
out=pathlib.Path(sys.argv[1]); labels=sys.argv[2].split(','); roots=[pathlib.Path(x) for x in sys.argv[3].split(',')]
if len(labels) != len(roots): raise SystemExit('inventory label/root count differs')
rows=[]; snapshots=[]
def identity(st):
    return [st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_nlink,st.st_uid,st.st_gid,st.st_mtime_ns,st.st_ctime_ns]
def same(left,right,what):
    if identity(left) != identity(right): raise SystemExit('entry changed '+what)
def walk(root,label,dirfd,rel):
    before_dir=os.fstat(dirfd)
    rows.append({'root':label,'path':str(rel),'type':'dir','mode':stat.S_IMODE(before_dir.st_mode),'uid':before_dir.st_uid,'gid':before_dir.st_gid,'mtime_ns':before_dir.st_mtime_ns})
    snapshots.append({'root':label,'path':str(rel),'identity':identity(before_dir)})
    for name in sorted(os.listdir(dirfd),key=os.fsencode):
        childrel=rel/name; before=os.stat(name,dir_fd=dirfd,follow_symlinks=False)
        row={'root':label,'path':str(childrel),'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,'gid':before.st_gid,'mtime_ns':before.st_mtime_ns}
        if stat.S_ISDIR(before.st_mode):
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirfd)
            try:
                same(before,os.fstat(fd),str(childrel)); walk(root,label,fd,childrel)
                same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            finally: os.close(fd)
            continue
        if stat.S_ISREG(before.st_mode):
            if before.st_nlink != 1: raise SystemExit('hardlinked file '+str(childrel))
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dirfd); h=hashlib.sha256()
            with os.fdopen(fd,'rb') as f:
                same(before,os.fstat(f.fileno()),str(childrel))
                for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
                same(before,os.fstat(f.fileno()),str(childrel))
            same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            row.update(type='file',size=before.st_size,sha256=h.hexdigest())
        elif stat.S_ISLNK(before.st_mode):
            target=os.readlink(name,dir_fd=dirfd)
            same(before,os.stat(name,dir_fd=dirfd,follow_symlinks=False),str(childrel))
            try: (root/childrel).resolve(strict=True).relative_to(root)
            except (OSError,RuntimeError,ValueError): raise SystemExit('escaping, dangling, or cyclic symlink '+str(childrel))
            row.update(type='symlink',size=before.st_size,target=target)
        else: raise SystemExit('special file '+str(childrel))
        rows.append(row); snapshots.append({'root':label,'path':str(childrel),'identity':identity(before)})
    same(before_dir,os.fstat(dirfd),str(rel))
for label,root in zip(labels,roots):
    if root.is_symlink() or not root.is_dir(): raise SystemExit('invalid root '+str(root))
    root=root.resolve(strict=True); initial=root.lstat(); fd=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        same(initial,os.fstat(fd),str(root)); walk(root,label,fd,pathlib.Path('.'))
        same(initial,os.fstat(fd),str(root)); same(initial,root.lstat(),str(root))
    finally: os.close(fd)
payload={'schema':'mckernel.exact-tree-inventory.v2','roots':labels,'rows':rows,'snapshots':snapshots}
raw=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode(); fd=os.open(str(out),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
PY
}
inventory "$SOURCE_FINAL" candidate,backup "$SOURCE,$SOURCE_BACKUP"
inventory "$DEST_FINAL" candidate,backup "$DEST,$DEST_BACKUP"
"$PY" -I -B - "$SOURCE_FINAL" "$DEST_FINAL" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]));
if a['rows'] != b['rows']: raise SystemExit('portable inventories differ')
PY
"${GIT[@]}" -C "$DEST" rev-parse HEAD >/dev/null
"${GIT[@]}" -C "$DEST/ihk" rev-parse HEAD >/dev/null
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 "$PY" -I -B - "$DEST" "$REQUEST" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root/'scripts'))
import native_rust_exact_build_container_owner as owner
owner.provenance.ENV=dict(owner.provenance.ENV,GIT_OPTIONAL_LOCKS='0')
r=json.load(open(sys.argv[2])); owner.BuildOwner(r).validate(); print('PASS_CORRECTION_VALIDATE_ONLY')
PY
inventory "$SOURCE_FINAL_POST" candidate,backup "$SOURCE,$SOURCE_BACKUP"
inventory "$DEST_FINAL_POST" candidate,backup "$DEST,$DEST_BACKUP"
cmp -s "$SOURCE_FINAL" "$SOURCE_FINAL_POST"; cmp -s "$DEST_FINAL" "$DEST_FINAL_POST"
"$PY" -I -B - "$SOURCE_FINAL_POST" "$DEST_FINAL_POST" <<'PY'
import json,sys
if json.load(open(sys.argv[1]))['rows'] != json.load(open(sys.argv[2]))['rows']: raise SystemExit('post-validation inventories differ')
PY
"$PY" -I -B - "$SCRATCH" <<'PY'
import os,sys
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
PY
echo PASS_DISK_COPY_CORRECTION_VALIDATE_ONLY
