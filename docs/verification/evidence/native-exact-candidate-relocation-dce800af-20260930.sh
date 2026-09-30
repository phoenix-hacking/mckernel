#!/usr/bin/env bash
# One-shot, fail-closed relocation of the exact scratch-5 candidate.
# This packet is prepared for a separately reviewed invocation; it must not be
# run by tests or by an unprivileged build dispatcher.
set -Eeuo pipefail
umask 077
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly C="$SCRATCH/mckernel-exact-candidate-dce800af-scratch-5"
readonly O="$SCRATCH/native-exact-build-output-dce800af-scratch-5"
readonly E="$SCRATCH/native-exact-build-evidence-dce800af-scratch-5"
readonly DEST_PARENT=/home/holden/mckernel-work/retained-exact-candidates
readonly DEST="$DEST_PARENT/mckernel-exact-candidate-dce800af-scratch-5"
readonly FAILURE=/home/holden/mckernel/docs/verification/evidence/native-exact-build-dce800af-scratch5-objtool-failure-20260930.json
readonly ARCHIVE="$SCRATCH/native-exact-build-failure-dce800af-scratch-5-20260930-1.tar"
readonly PREP_TERMINAL="$SCRATCH/native-exact-candidate-preparation-dce800af-scratch-5-terminal.json"
readonly REQUEST="$SCRATCH/native-exact-build-request-dce800af-scratch-5.json"
readonly MANIFEST="$SCRATCH/native-exact-inputs-dce800af-scratch-5.json"
readonly LOG="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930.log"
readonly TERMINAL="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930-terminal.json"
readonly INTENT="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930-intent.json"
readonly EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-lifecyclebinding-10.json"
readonly LOCK="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930.lock"
readonly SRC_DEV=1831 DEST_DEV=66306
readonly CANDIDATE_COMMIT=dce800af8c19d014ef509e102ca4f4b1c473e2ab
readonly IHK_COMMIT=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly FAILURE_SHA=ce4715d7c9178ffebdf780251a1fcba70642d7e46b9d5d44e132466b916bc867
readonly ARCHIVE_SHA=f8522be9649def629b04a93d065f3ab79a5c7acdd7a2f2f221b7d759384c5952
readonly PREP_RELEASE=b13f7065cc16bff1608a6f3d89ff65870400c3c6
readonly PREP_PACKET_SHA=c334449c9d1081911a0de951a3b130b4b06de24414da5755801687407698a996
readonly PREP_TERMINAL_SHA=2788c195965f7a12f92f1463065f70074ce48f2875d406fce2cfa293c6c9dcd9
readonly PREP_PACKET_PATH=docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-5.sh
readonly OVERLAY_SHA=cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7
readonly RESULT_SHA=7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77
readonly BASE_SHA=91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c
die(){ echo "FAIL-CLOSED: $*" >&2; exit 1; }
sha(){ /usr/bin/sha256sum -- "$1" | /usr/bin/awk '{print $1}'; }
[[ ${EUID:-1} -ne 0 ]] || die root-launch-prohibited
: "${RELOCATION_RELEASE_COMMIT:?set reviewed fetched relocation release}"
: "${RELOCATION_PACKET_SHA256:?set reviewed relocation packet blob hash}"
: "${RELOCATION_TEST_SHA256:?set reviewed relocation test blob hash}"
[[ "$RELOCATION_RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die release-format
for p in "$LOG" "$TERMINAL" "$INTENT" "$EXCLUSION"; do [[ ! -e "$p" && ! -L "$p" ]] || die output-exists; done
for p in "$C" "$O" "$E" "$FAILURE" "$ARCHIVE" "$PREP_TERMINAL" "$REQUEST" "$MANIFEST"; do [[ -e "$p" && ! -L "$p" ]] || die missing-preserved-input; done
[[ "$(sha "$FAILURE")" == "$FAILURE_SHA" ]] || die failure-hash
[[ "$(sha "$ARCHIVE")" == "$ARCHIVE_SHA" ]] || die archive-hash
exec 9>>"$LOCK"; /usr/bin/flock -n 9 || die relocation-busy
exec 8>"$LOG"
/usr/bin/python3 - "$C" "$O" "$E" "$FAILURE" "$ARCHIVE" "$PREP_TERMINAL" "$REQUEST" "$MANIFEST" "$DEST_PARENT" "$DEST" "$LOG" "$TERMINAL" "$INTENT" "$EXCLUSION" <<'PY'
import ctypes, datetime, fcntl, hashlib, json, os, pathlib, re, shutil, stat, subprocess, sys
C,O,E,FAILURE,ARCHIVE,PREP_TERMINAL,REQUEST,MANIFEST,DEST_PARENT,DEST,LOG,TERMINAL,INTENT,EXCLUSION=sys.argv[1:]
SRC_DEV,DEST_DEV=1831,66306
REPO='/home/holden/mckernel'; CANDIDATE='dce800af8c19d014ef509e102ca4f4b1c473e2ab'; IHK='3114d9e7101ad52030eb3effa849a5c108972a1f'
PREP_PACKET_PATH='docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-5.sh'
OVERLAY='host-kernel/exact-build/ihk-clear-host-pte-overlay.patch'; RESULT='ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c'
OVERLAY_SHA='cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7'; RESULT_SHA='7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77'; BASE_SHA='91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c'
def durable(path,data):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  off=0
  while off<len(data):
   n=os.write(fd,data[off:])
   if n<=0: raise OSError('short durable write')
   off+=n
  os.fsync(fd)
 finally: os.close(fd)
 d=os.open(str(pathlib.Path(path).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(d); os.close(d)
def under(root,p):
 return pathlib.Path(os.path.commonpath((str(root),str(p))))==pathlib.Path(root)
def inventory(root, expected_dev=None):
 root=pathlib.Path(root); out=[]; groups={}
 if not root.is_dir() or root.is_symlink(): raise RuntimeError('root-not-directory')
 for p in sorted([root]+list(root.rglob('*')),key=lambda x:str(x)):
  s=os.lstat(p); rel='.' if p==root else str(p.relative_to(root))
  if expected_dev is not None and s.st_dev!=expected_dev: raise RuntimeError('foreign-device-or-mount')
  mode=stat.S_IMODE(s.st_mode); row={'path':rel,'type':stat.filemode(s.st_mode)[0],'mode':mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'dev':s.st_dev}
  if stat.S_ISLNK(s.st_mode):
   target=os.readlink(p); resolved=(p.parent/target).resolve(strict=False)
   if not under(root,resolved): raise RuntimeError('unsafe-symlink')
   row['target']=target
  elif stat.S_ISREG(s.st_mode):
   h=hashlib.sha256();
   with open(p,'rb',buffering=0) as f:
    for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
   row['sha256']=h.hexdigest()
   key=(s.st_dev,s.st_ino)
   if s.st_nlink>1: groups.setdefault(key,[]).append(rel)
  out.append(row)
 for paths in groups.values():
  if len(paths)>1:
   anchor=min(paths)
   for row in out:
    if row['path'] in paths: row['hardlink_to']=anchor
 return out
def equal_inventory(a,b):
 def norm(rows):
  return [{k:v for k,v in x.items() if k not in {'dev','mtime_ns'}} for x in rows]
 return norm(a)==norm(b)
def mount_points(text,root):
 root=str(root).rstrip('/')
 for line in text.splitlines():
  left=line.split(' - ',1)[0].split()
  if len(left)>4:
   p=left[4].replace('\\040',' ').replace('\\011','\t')
   if p==root or p.startswith(root+'/'): return True
 return False
def proc_references(proc_root,targets):
 hits=[]
 for q in pathlib.Path(proc_root).glob('[0-9]*'):
  try:
   refs=[]
   for n in ('root','cwd','fd'):
    x=q/n
    if x.is_dir(): refs.extend(os.readlink(z) for z in x.iterdir() if z.is_symlink())
   maps=q/'maps'
   try:
    text=maps.read_text(errors='replace')
   except PermissionError: raise RuntimeError('unreadable-process-reference')
   if any(t in text for t in targets): refs.append(text)
   if any(any(str(v)==t or str(v).startswith(t+'/') for t in targets) for v in refs): hits.append(str(q))
  except FileNotFoundError: pass
  except PermissionError: raise RuntimeError('unreadable-process-reference')
 return hits
def safe_remove(root,dev,ino):
 p=pathlib.Path(root); par=os.open(str(p.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); fd=os.open(p.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=par)
 try:
  s=os.fstat(fd); ps=os.fstat(par)
  if (s.st_dev,s.st_ino)!=(dev,ino) or ps.st_dev!=dev: raise RuntimeError('root-identity-changed')
  def walk(d):
   for ent in os.scandir(d):
    z=ent.stat(follow_symlinks=False)
    if z.st_dev!=dev or stat.S_ISLNK(z.st_mode): raise RuntimeError('delete-symlink-or-mount')
    if stat.S_ISDIR(z.st_mode):
     c=os.open(ent.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=d)
     try: walk(c)
     finally: os.close(c)
     os.rmdir(ent.name,dir_fd=d)
    else: os.unlink(ent.name,dir_fd=d)
  walk(fd)
 finally: os.close(fd)
 os.rmdir(p.name,dir_fd=par); os.close(par)
def fsync_tree(root):
 for p in sorted([pathlib.Path(root)]+list(pathlib.Path(root).rglob('*')),key=lambda x:len(str(x)),reverse=True):
  if p.is_symlink(): continue
  fd=os.open(str(p),os.O_RDONLY|(os.O_DIRECTORY if p.is_dir() else 0)|os.O_NOFOLLOW)
  try: os.fsync(fd)
  finally: os.close(fd)
def rename_noreplace(src,dst,parent):
 pfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  libc=ctypes.CDLL(None,use_errno=True); fn=libc.renameat2; fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; fn.restype=ctypes.c_int
  if fn(pfd,os.fsencode(os.path.basename(src)),pfd,os.fsencode(os.path.basename(dst)),1)!=0:
   err=ctypes.get_errno(); raise OSError(err,os.strerror(err))
 finally: os.close(pfd)
def fail_if_active():
 if proc_references('/proc',[C,O,E,DEST]): raise RuntimeError('active-process-reference')
 ps=subprocess.run(['/usr/bin/ps','-eo','pid=,args='],check=True,text=True,capture_output=True).stdout
 if re.search(r'native[_-]rust[_-]exact|qemu-system|qemu-kvm|mcexec|docker build',ps): raise RuntimeError('active-build-or-guest')
 dp=subprocess.run(['/usr/bin/sudo','-A','/usr/bin/docker','ps','--no-trunc','--format','{{.ID}} {{.Names}}'],check=False,text=True,capture_output=True)
 if dp.returncode: raise RuntimeError('docker-census-failed')
 if any('mckernel-exact' in x for x in dp.stdout.splitlines()): raise RuntimeError('active-docker')
 if any(pathlib.Path(p).exists() for p in ('/run/lock/mckernel-build.lock','/run/mckernel-build.lease')): raise RuntimeError('active-lease')
def git(*args):
 env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PATH='/usr/bin:/bin',HOME='/nonexistent')
 return subprocess.run(['/usr/bin/git','-C',REPO,*args],env=env,check=True,text=True,capture_output=True).stdout.strip()
def main():
 parent=pathlib.Path(DEST_PARENT)
 for ancestor in (pathlib.Path('/home'),pathlib.Path('/home/holden'),pathlib.Path('/home/holden/mckernel-work')):
  if ancestor.is_symlink(): raise RuntimeError('destination-ancestor-symlink')
 parent.mkdir(mode=0o700,parents=False,exist_ok=True)
 if parent.is_symlink() or os.stat(C).st_dev!=SRC_DEV or os.stat(DEST_PARENT).st_dev!=DEST_DEV: raise RuntimeError('device-binding')
 if pathlib.Path(DEST).exists() or pathlib.Path(DEST).is_symlink(): raise RuntimeError('destination-exists')
 fail_if_active()
 source_ancestors=[]
 for ancestor in (pathlib.Path('/home'),pathlib.Path('/home/holden'),pathlib.Path('/home/holden/mckernel-work'),pathlib.Path('/home/holden/mckernel-work/scratch'),pathlib.Path(C)):
  s=os.lstat(ancestor)
  if stat.S_ISLNK(s.st_mode): raise RuntimeError('source-ancestor-symlink')
  source_ancestors.append((str(ancestor),s.st_dev,s.st_ino))
 if source_ancestors[-1][1]!=SRC_DEV or mount_points(open('/proc/self/mountinfo',errors='replace').read(),C): raise RuntimeError('source-mount')
 src_inv=inventory(C,SRC_DEV); src_ino=os.stat(C).st_ino
 fail=json.load(open(FAILURE));
 if fail.get('candidate_sha')!=CANDIDATE or fail.get('source_preparation',{}).get('candidate_root')!=C: raise RuntimeError('failure-provenance')
 if fail.get('archive',{}).get('sha256')!='f8522be9649def629b04a93d065f3ab79a5c7acdd7a2f2f221b7d759384c5952': raise RuntimeError('archive-provenance')
 if git('rev-parse','refs/remotes/origin/codex/local-native-staging-repair') != os.environ['RELOCATION_RELEASE_COMMIT']: raise RuntimeError('release-not-fetched')
 if git('cat-file','-t',os.environ['RELOCATION_RELEASE_COMMIT'])!='commit': raise RuntimeError('release-missing')
 env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PATH='/usr/bin:/bin',HOME='/nonexistent')
 blob=subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RELOCATION_RELEASE_COMMIT']+':docs/verification/evidence/native-exact-candidate-relocation-dce800af-20260930.sh'],env=env)
 if hashlib.sha256(blob).hexdigest()!=os.environ['RELOCATION_PACKET_SHA256']: raise RuntimeError('packet-binding')
 test_blob=subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RELOCATION_RELEASE_COMMIT']+':scripts/tests/test_native_exact_candidate_relocation_dce800af_20260930.py'],env=env)
 if hashlib.sha256(test_blob).hexdigest()!=os.environ['RELOCATION_TEST_SHA256']: raise RuntimeError('test-binding')
 prep_blob=subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RELOCATION_RELEASE_COMMIT']+':'+PREP_PACKET_PATH],env=env)
 if hashlib.sha256(prep_blob).hexdigest()!='c334449c9d1081911a0de951a3b130b4b06de24414da5755801687407698a996' or hashlib.sha256(pathlib.Path(PREP_TERMINAL).read_bytes()).hexdigest()!='2788c195965f7a12f92f1463065f70074ce48f2875d406fce2cfa293c6c9dcd9': raise RuntimeError('preparation-binding')
 if hashlib.sha256(pathlib.Path(C+'/'+OVERLAY).read_bytes()).hexdigest()!=OVERLAY_SHA or hashlib.sha256(pathlib.Path(C+'/'+RESULT).read_bytes()).hexdigest()!=RESULT_SHA: raise RuntimeError('overlay-result-binding')
 if subprocess.run(['/usr/bin/git','-C',C,'rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=CANDIDATE or subprocess.run(['/usr/bin/git','-C',C+'/ihk','rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=IHK: raise RuntimeError('commit-binding')
 if hashlib.sha256(subprocess.check_output(['/usr/bin/git','-C',C+'/ihk','show',IHK+':test/ihklib/whitebox/src/driver/mckernel/syscall.c'],env=env)).hexdigest()!=BASE_SHA: raise RuntimeError('base-binding')
 for p in (C,O,E,FAILURE,ARCHIVE,PREP_TERMINAL,REQUEST,MANIFEST):
  if pathlib.Path(p).is_symlink(): raise RuntimeError('preserved-input-symlink')
 scratch_path=str(pathlib.Path(C).parent)
 before_scratch=os.statvfs(scratch_path).f_bavail*os.statvfs(scratch_path).f_frsize
 before_host=os.statvfs(DEST_PARENT).f_bavail*os.statvfs(DEST_PARENT).f_frsize
 exfd=os.open(EXCLUSION,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(exfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  exclusion_data=(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-exclusion.v1','target':C,'owner_pid':os.getpid()},sort_keys=True)+'\n').encode(); off=0
  while off<len(exclusion_data):
   n=os.write(exfd,exclusion_data[off:])
   if n<=0: raise OSError('short exclusion write')
   off+=n
  os.fsync(exfd)
  durable(INTENT,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-intent.v1','source':C,'destination':DEST,'status':'COPYING'},sort_keys=True)+'\n').encode())
  pathlib.Path(DEST_PARENT).mkdir(mode=0o700,parents=True,exist_ok=True)
  tmp=DEST_PARENT+'/.mckernel-exact-candidate-dce800af-scratch-5.tmp-'+str(os.getpid())
  if pathlib.Path(tmp).exists(): raise RuntimeError('temporary-destination-exists')
  pathlib.Path(tmp).mkdir(mode=0o700)
  subprocess.run(['/usr/bin/rsync','-aHAX','--numeric-ids','--one-file-system','--links','--',C+'/',tmp+'/'],check=True)
  fsync_tree(tmp)
  if not equal_inventory(src_inv,inventory(tmp)): raise RuntimeError('copy-verification')
  check=subprocess.run(['/usr/bin/rsync','-acHAXni','--delete','--',C+'/',tmp+'/'],check=False,text=True,capture_output=True)
  if check.returncode!=0 or check.stdout or check.stderr: raise RuntimeError('rsync-verification')
  if inventory(C,SRC_DEV)!=src_inv: raise RuntimeError('source-mutated-during-copy')
  rename_noreplace(tmp,DEST,DEST_PARENT); d=os.open(DEST_PARENT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(d); os.close(d)
  if not equal_inventory(src_inv,inventory(DEST)): raise RuntimeError('rename-verification')
  if mount_points(open('/proc/self/mountinfo',errors='replace').read(),C): raise RuntimeError('source-mount-before-delete')
  current_ancestors=[]
  for name,dev,ino in source_ancestors:
   s=os.lstat(name)
   if (s.st_dev,s.st_ino)!=(dev,ino): raise RuntimeError('source-ancestor-changed')
   current_ancestors.append((name,s.st_dev,s.st_ino))
  if inventory(C,SRC_DEV)!=src_inv or os.stat(C).st_ino!=src_ino: raise RuntimeError('source-changed-before-delete')
  fail_if_active()
  durable(TERMINAL,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-deletion-start.v1','status':'VERIFIED_DESTINATION_DELETION_START','source':C,'destination':DEST},sort_keys=True)+'\n').encode())
  try: safe_remove(C,SRC_DEV,src_ino)
  except Exception as exc:
   if pathlib.Path(TERMINAL).exists(): pathlib.Path(TERMINAL).unlink()
   durable(TERMINAL,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-partial-failure.v1','status':'PARTIAL_DELETION_FAILURE','source':C,'destination':DEST,'error':repr(exc)},sort_keys=True)+'\n').encode())
   raise
  after_scratch=os.statvfs(scratch_path); after_host=os.statvfs(DEST_PARENT); rec={'schema':'mckernel.native-exact-candidate-relocation-dce800af.v1','status':'PASS','source':C,'destination':DEST,'source_device':SRC_DEV,'destination_device':DEST_DEV,'scratch_free_bytes_before':before_scratch,'scratch_free_bytes_after':after_scratch.f_bavail*after_scratch.f_frsize,'host_free_bytes_before':before_host,'host_free_bytes_after':after_host.f_bavail*after_host.f_frsize,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}
  durable(TERMINAL,(json.dumps(rec,sort_keys=True)+'\n').encode()); open(LOG,'a').write(json.dumps(rec,sort_keys=True)+'\n')
 finally: os.close(exfd)
main()
PY
