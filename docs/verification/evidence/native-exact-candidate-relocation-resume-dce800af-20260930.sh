#!/usr/bin/env bash
# Reviewed resume packet for the interrupted cross-filesystem relocation.
# It consumes the already populated temporary destination; it never recopies.
set -Eeuo pipefail
umask 077
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly C="$SCRATCH/mckernel-exact-candidate-dce800af-scratch-5"
readonly TMP=/home/holden/mckernel-work/retained-exact-candidates/.mckernel-exact-candidate-dce800af-scratch-5.tmp-557425
readonly DEST=/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-dce800af-scratch-5
readonly FAILURE=/home/holden/mckernel/docs/verification/evidence/native-exact-build-dce800af-scratch5-objtool-failure-20260930.json
readonly RELOCATION_FAILURE=/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-relocation-dce800af-copy-verification-failure-20260930.json
readonly ARCHIVE="$SCRATCH/native-exact-build-failure-dce800af-scratch-5-20260930-1.tar"
readonly PREP_TERMINAL="$SCRATCH/native-exact-candidate-preparation-dce800af-scratch-5-terminal.json"
readonly REQUEST="$SCRATCH/native-exact-build-request-dce800af-scratch-5.json"
readonly MANIFEST="$SCRATCH/native-exact-inputs-dce800af-scratch-5.json"
readonly BUILD_EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-lifecyclebinding-10.json"
readonly OLD_INTENT="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930-intent.json"
readonly OLD_EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-relocation-dce800af-12.json"
readonly OLD_LOG="$SCRATCH/native-exact-candidate-relocation-dce800af-20260930.log"
readonly LOG="$SCRATCH/native-exact-candidate-relocation-resume-dce800af-20260930.log"
readonly INTENT="$SCRATCH/native-exact-candidate-relocation-resume-dce800af-20260930-intent.json"
readonly TERMINAL="$SCRATCH/native-exact-candidate-relocation-resume-dce800af-20260930-terminal.json"
readonly DELETE_INTENT="$SCRATCH/native-exact-candidate-relocation-resume-dce800af-20260930-deletion-intent.json"
readonly EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-resume-dce800af-13.json"
readonly LOCK="$SCRATCH/native-exact-candidate-relocation-resume-dce800af-20260930.lock"
readonly SRC_DEV=1831 DEST_DEV=66306
readonly CANDIDATE_COMMIT=dce800af8c19d014ef509e102ca4f4b1c473e2ab
readonly IHK_COMMIT=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly FAILURE_SHA=ce4715d7c9178ffebdf780251a1fcba70642d7e46b9d5d44e132466b916bc867
readonly RELOCATION_FAILURE_SHA=0a98a1ea5c62bd80999fb73bdc1ab8b7a107f629d387933535b84dd2a39480a1
readonly ARCHIVE_SHA=f8522be9649def629b04a93d065f3ab79a5c7acdd7a2f2f221b7d759384c5952
readonly PREP_TERMINAL_SHA=2788c195965f7a12f92f1463065f70074ce48f2875d406fce2cfa293c6c9dcd9
readonly REQUEST_SHA=d0cdd1e89dd2bcd4f498bcf4b276b51842ad75f5cc2d57c3b62aa3f563c7b039
readonly MANIFEST_SHA=0b80c8adf00670816998099a182773479c59ba5766931d288ce11b68e9c074ce
readonly BUILD_EXCLUSION_SHA=ef89d2384f417e02c4ae41192726ac76601376e189f0325e1932384add02c7c6
readonly OLD_INTENT_SHA=6e3a0e0513f12fb1041f82bd65944e60ddcaaaca8fb4fcf41717a109e87b8318
readonly OLD_EXCLUSION_SHA=b280e78e0a663ef63c5ef7e082faea3c3c77b56d700bf00a8cce19bd1b08ceb1
readonly OLD_LOG_SHA=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
readonly PREP_RELEASE=b13f7065cc16bff1608a6f3d89ff65870400c3c6
readonly PREP_PACKET_PATH=docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-5.sh
export RESUME_OLD_INTENT_PATH="$OLD_INTENT" RESUME_OLD_EXCLUSION_PATH="$OLD_EXCLUSION" RESUME_OLD_LOG_PATH="$OLD_LOG"
die(){ echo "FAIL-CLOSED: $*" >&2; exit 1; }
sha(){ /usr/bin/sha256sum -- "$1" | /usr/bin/awk '{print $1}'; }
[[ ${EUID:-1} -ne 0 ]] || die root-launch-prohibited
: "${RESUME_RELEASE_COMMIT:?set reviewed fetched resume release}"
: "${RESUME_PACKET_SHA256:?set reviewed resume packet blob hash}"
: "${RESUME_TEST_SHA256:?set reviewed resume test blob hash}"
[[ "$RESUME_RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die release-format
for p in "$LOG" "$INTENT" "$TERMINAL" "$DELETE_INTENT" "$EXCLUSION"; do [[ ! -e "$p" && ! -L "$p" ]] || die output-exists; done
for p in "$C" "$TMP" "$FAILURE" "$RELOCATION_FAILURE" "$ARCHIVE" "$PREP_TERMINAL" "$REQUEST" "$MANIFEST" "$BUILD_EXCLUSION" "$OLD_INTENT" "$OLD_EXCLUSION" "$OLD_LOG"; do [[ -e "$p" && ! -L "$p" ]] || die missing-preserved-input; done
[[ "$(sha "$FAILURE")" == "$FAILURE_SHA" ]] || die failure-hash
[[ "$(sha "$RELOCATION_FAILURE")" == "$RELOCATION_FAILURE_SHA" ]] || die relocation-failure-hash
[[ "$(sha "$ARCHIVE")" == "$ARCHIVE_SHA" ]] || die archive-hash
[[ "$(sha "$PREP_TERMINAL")" == "$PREP_TERMINAL_SHA" ]] || die preparation-terminal-hash
[[ "$(sha "$REQUEST")" == "$REQUEST_SHA" ]] || die request-hash
[[ "$(sha "$MANIFEST")" == "$MANIFEST_SHA" ]] || die manifest-hash
[[ "$(sha "$BUILD_EXCLUSION")" == "$BUILD_EXCLUSION_SHA" ]] || die build-exclusion-hash
[[ "$(sha "$OLD_INTENT")" == "$OLD_INTENT_SHA" ]] || die old-intent-hash
[[ "$(sha "$OLD_EXCLUSION")" == "$OLD_EXCLUSION_SHA" ]] || die old-exclusion-hash
[[ "$(sha "$OLD_LOG")" == "$OLD_LOG_SHA" ]] || die old-log-hash
exec 9>>"$LOCK"; /usr/bin/flock -n 9 || die relocation-busy
exec 8>"$LOG"
/usr/bin/python3 - "$C" "$TMP" "$DEST" "$LOG" "$INTENT" "$TERMINAL" "$DELETE_INTENT" "$EXCLUSION" "$RELOCATION_FAILURE" <<'PY'
import ctypes,datetime,fcntl,hashlib,json,os,pathlib,re,stat,subprocess,sys
C,TMP,DEST,LOG,INTENT,TERMINAL,DELETE_INTENT,EXCLUSION,RELOCATION_FAILURE=sys.argv[1:]
SRC_DEV,DEST_DEV=1831,66306; SOURCE_ID=(1831,5242884); TMP_ID=(66306,47736554)
REPO='/home/holden/mckernel'; CANDIDATE='dce800af8c19d014ef509e102ca4f4b1c473e2ab'; IHK='3114d9e7101ad52030eb3effa849a5c108972a1f'
PACKET='docs/verification/evidence/native-exact-candidate-relocation-resume-dce800af-20260930.sh'; TEST='scripts/tests/test_native_exact_candidate_relocation_resume_dce800af_20260930.py'
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
def under(root,p): return pathlib.Path(os.path.commonpath((str(root),str(p))))==pathlib.Path(root)
def inventory(root,dev=None):
 root=pathlib.Path(root); rows=[]; groups={}
 if not root.is_dir() or root.is_symlink(): raise RuntimeError('root-not-directory')
 for p in sorted([root]+list(root.rglob('*')),key=str):
  s=os.lstat(p); rel='.' if p==root else str(p.relative_to(root))
  if dev is not None and s.st_dev!=dev: raise RuntimeError('foreign-device-or-mount')
  row={'path':rel,'type':stat.filemode(s.st_mode)[0],'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'dev':s.st_dev}
  if stat.S_ISLNK(s.st_mode):
   row['target']=os.readlink(p)
   if not under(root,(p.parent/row['target']).resolve(strict=False)): raise RuntimeError('unsafe-symlink')
  elif stat.S_ISREG(s.st_mode):
   h=hashlib.sha256();
   with open(p,'rb',buffering=0) as f:
    for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
   row['sha256']=h.hexdigest(); key=(s.st_dev,s.st_ino)
   if s.st_nlink>1: groups.setdefault(key,[]).append(rel)
  rows.append(row)
 for paths in groups.values():
  if len(paths)>1:
   for row in rows:
    if row['path'] in paths: row['hardlink_to']=min(paths)
 return rows
def equal(a,b):
 def norm(rows):
  out=[]
  for x in rows:
   row={k:v for k,v in x.items() if k not in {'dev','mtime_ns'}}
   if x['type']=='d': row.pop('size',None)
   out.append(row)
  return out
 return norm(a)==norm(b)
def mount_points(text,root):
 root=str(root).rstrip('/')
 for line in text.splitlines():
  fields=line.split(' - ',1)[0].split()
  if len(fields)>4:
   p=fields[4].replace('\\040',' ').replace('\\011','\t')
   if p==root or p.startswith(root+'/'): return True
 return False
def safe_remove(root,dev,ino):
 p=pathlib.Path(root); par=os.open(str(p.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); fd=os.open(p.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=par)
 try:
  s=os.fstat(fd)
  if (s.st_dev,s.st_ino)!=(dev,ino): raise RuntimeError('root-identity-changed')
  def walk(d):
   for e in os.scandir(d):
    z=e.stat(follow_symlinks=False)
    if z.st_dev!=dev: raise RuntimeError('delete-foreign-device-or-mount')
    if stat.S_ISLNK(z.st_mode): os.unlink(e.name,dir_fd=d)
    elif stat.S_ISDIR(z.st_mode):
     c=os.open(e.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=d)
     try: walk(c)
     finally: os.close(c)
     os.rmdir(e.name,dir_fd=d)
    else: os.unlink(e.name,dir_fd=d)
  walk(fd)
 finally: os.close(fd)
 os.rmdir(p.name,dir_fd=par); os.close(par)
def privileged_references(targets):
 hits=[]
 for target in targets:
  if not pathlib.Path(target).exists(): continue
  r=subprocess.run(['/usr/bin/sudo','-A','/usr/bin/lsof','-nP','-w','+D',target],check=False,text=True,capture_output=True)
  if r.returncode not in (0,1) or r.stderr.strip() or (r.returncode==1 and r.stdout.strip()): raise RuntimeError('privileged-reference-census-failed')
  if r.returncode==0 and r.stdout.strip(): hits.append(target)
 return hits
def rename_noreplace(src,dst,parent):
 p=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); libc=ctypes.CDLL(None,use_errno=True); f=libc.renameat2; f.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; f.restype=ctypes.c_int
 try:
  if f(p,os.fsencode(os.path.basename(src)),p,os.fsencode(os.path.basename(dst)),1): raise OSError(ctypes.get_errno(),'renameat2')
 finally: os.close(p)
def active():
 q=subprocess.run(['/usr/bin/ps','-eo','pid=,args='],check=True,text=True,capture_output=True).stdout
 if re.search(r'native[_-]rust[_-]exact|qemu-system|qemu-kvm|mcexec|docker build',q): raise RuntimeError('active-build-or-guest')
 if any(pathlib.Path(x).exists() for x in ('/run/lock/mckernel-build.lock','/run/mckernel-build.lease')): raise RuntimeError('active-lease')
 d=subprocess.run(['/usr/bin/sudo','-A','/usr/bin/docker','ps','--no-trunc','--format','{{.ID}} {{.Names}}'],check=False,text=True,capture_output=True)
 if d.returncode or d.stderr.strip(): raise RuntimeError('docker-census-failed')
 if any('mckernel-exact' in line for line in d.stdout.splitlines()): raise RuntimeError('active-docker')
def git(*args):
 env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PATH='/usr/bin:/bin',HOME='/nonexistent')
 return subprocess.run(['/usr/bin/git','-C',REPO,*args],env=env,check=True,text=True,capture_output=True).stdout.strip()
def append_log(data):
 b=data if isinstance(data,bytes) else data.encode(); off=0
 while off<len(b):
  n=os.write(8,b[off:])
  if n<=0: raise OSError('short log write')
  off+=n
 os.fsync(8)
def require_hash(path,expected):
 h=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
 if h!=expected: raise RuntimeError('local-byte-binding')
def main():
 if pathlib.Path(DEST).exists() or pathlib.Path(DEST).is_symlink(): raise RuntimeError('destination-exists')
 if (os.stat(C).st_dev,os.stat(C).st_ino)!=SOURCE_ID or (os.stat(TMP).st_dev,os.stat(TMP).st_ino)!=TMP_ID: raise RuntimeError('identity-binding')
 if pathlib.Path(TMP).is_symlink(): raise RuntimeError('temporary-symlink')
 for p in (C,TMP):
  if not pathlib.Path(p).is_dir(): raise RuntimeError('missing-tree')
 ancestor_paths=('/home','/home/holden','/home/holden/mckernel-work','/home/holden/mckernel-work/scratch',C,'/home/holden/mckernel-work/retained-exact-candidates',TMP)
 ancestor_ids=[]
 for p in ancestor_paths:
  s=os.lstat(p)
  if stat.S_ISLNK(s.st_mode): raise RuntimeError('ancestor-symlink')
  ancestor_ids.append((p,s.st_dev,s.st_ino))
 mounts=open('/proc/self/mountinfo',errors='replace').read()
 if mount_points(mounts,C) or mount_points(mounts,TMP): raise RuntimeError('nested-mount')
 if git('rev-parse','refs/remotes/origin/codex/local-native-staging-repair')!=os.environ['RESUME_RELEASE_COMMIT']: raise RuntimeError('release-not-fetched')
 if git('cat-file','-t',os.environ['RESUME_RELEASE_COMMIT'])!='commit': raise RuntimeError('release-missing')
 require_hash(REPO+'/'+PACKET,os.environ['RESUME_PACKET_SHA256']); require_hash(REPO+'/'+TEST,os.environ['RESUME_TEST_SHA256'])
 env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PATH='/usr/bin:/bin',HOME='/nonexistent')
 for path,key in ((PACKET,'RESUME_PACKET_SHA256'),(TEST,'RESUME_TEST_SHA256')):
  blob=subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RESUME_RELEASE_COMMIT']+':'+path],env=env)
  if hashlib.sha256(blob).hexdigest()!=os.environ[key]: raise RuntimeError('release-blob-binding')
 if hashlib.sha256(subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RESUME_RELEASE_COMMIT']+':docs/verification/evidence/native-exact-candidate-relocation-dce800af-copy-verification-failure-20260930.json'],env=env)).hexdigest()!='0a98a1ea5c62bd80999fb73bdc1ab8b7a107f629d387933535b84dd2a39480a1': raise RuntimeError('failure-record-release-binding')
 if subprocess.run(['/usr/bin/git','-C',C,'rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=CANDIDATE: raise RuntimeError('candidate-commit-binding')
 if subprocess.run(['/usr/bin/git','-C',C+'/ihk','rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=IHK: raise RuntimeError('ihk-commit-binding')
 failure=json.load(open(RELOCATION_FAILURE))
 if failure.get('status')!='FAIL_COPY_VERIFICATION_BEFORE_RENAME_OR_DELETE' or failure.get('preserved_source',{}).get('identity')!='1831:5242884' or failure.get('preserved_temporary_copy',{}).get('identity')!='66306:47736554': raise RuntimeError('failure-record-provenance')
 active()
 if privileged_references([C,TMP,DEST]): raise RuntimeError('active-process-reference')
 if any(os.statvfs(p).f_bavail*os.statvfs(p).f_frsize < floor+512*1024**2 for p,floor in ((str(pathlib.Path(C).parent),12*1024**3),(str(pathlib.Path(DEST).parent),16*1024**3))): raise RuntimeError('insufficient-capacity-floor')
 for p,dev,ino in ((os.environ.get('RESUME_OLD_INTENT_PATH'),1831,57586),(os.environ.get('RESUME_OLD_EXCLUSION_PATH'),1831,57585),(os.environ.get('RESUME_OLD_LOG_PATH'),1831,57584)):
  if not p: raise RuntimeError('old-artifact-binding-missing')
  s=os.lstat(p)
  if (s.st_dev,s.st_ino)!=(dev,ino): raise RuntimeError('old-artifact-identity')
 exfd=os.open(EXCLUSION,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(exfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ex=(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-exclusion.v1','source':C,'temporary':TMP,'owner_pid':os.getpid()},sort_keys=True)+'\n').encode(); off=0
  while off<len(ex):
   n=os.write(exfd,ex[off:])
   if n<=0: raise OSError('short exclusion write')
   off+=n
  os.fsync(exfd); xdir=os.open(str(pathlib.Path(EXCLUSION).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(xdir); os.close(xdir)
  durable(INTENT,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-intent.v1','source':C,'temporary':TMP,'destination':DEST,'status':'VERIFYING_PRESERVED_COPY'},sort_keys=True)+'\n').encode())
  src=inventory(C,SRC_DEV); tmp=inventory(TMP,DEST_DEV)
  if not equal(src,tmp): raise RuntimeError('copy-verification')
  check=subprocess.run(['/usr/bin/rsync','-acHAXni','--delete','--',C+'/',TMP+'/'],capture_output=True,text=True)
  if check.returncode or check.stdout or check.stderr: raise RuntimeError('rsync-verification')
  if inventory(C,SRC_DEV)!=src: raise RuntimeError('source-mutated-during-resume')
  if (os.stat(TMP).st_dev,os.stat(TMP).st_ino)!=TMP_ID or inventory(TMP,DEST_DEV)!=tmp: raise RuntimeError('temporary-mutated-during-resume')
  parent=str(pathlib.Path(DEST).parent); rename_noreplace(TMP,DEST,parent)
  pfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(pfd); os.close(pfd)
  try:
   if (os.stat(DEST).st_dev,os.stat(DEST).st_ino)!=TMP_ID or not equal(src,inventory(DEST,DEST_DEV)): raise RuntimeError('rename-verification')
   active()
   if privileged_references([C,DEST]): raise RuntimeError('active-process-reference-before-delete')
   if inventory(C,SRC_DEV)!=src or not equal(src,inventory(DEST,DEST_DEV)): raise RuntimeError('tree-changed-before-delete')
   for p,dev,ino in ancestor_ids[:-1]:
    s=os.lstat(p)
    if stat.S_ISLNK(s.st_mode) or (s.st_dev,s.st_ino)!=(dev,ino): raise RuntimeError('ancestor-changed-before-delete')
   if mount_points(open('/proc/self/mountinfo',errors='replace').read(),C): raise RuntimeError('source-mount-before-delete')
   durable(DELETE_INTENT,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-deletion-start.v1','source':C,'destination':DEST,'status':'VERIFIED_DESTINATION_DELETION_START'},sort_keys=True)+'\n').encode())
   try: safe_remove(C,SRC_DEV,SOURCE_ID[1])
   except Exception as exc:
    durable(TERMINAL,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-partial-failure.v1','status':'PARTIAL_DELETION_FAILURE','source':C,'destination':DEST,'error':repr(exc)},sort_keys=True)+'\n').encode()); raise
   rec={'schema':'mckernel.native-exact-candidate-relocation-resume-dce800af.v1','status':'PASS','source':C,'destination':DEST,'resume_namespace':'resume-dce800af-13','entry_count':len(src),'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}
   data=(json.dumps(rec,sort_keys=True)+'\n').encode(); durable(TERMINAL,data); append_log(data)
  except Exception as exc:
   if not pathlib.Path(TERMINAL).exists(): durable(TERMINAL,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-post-rename-failure.v1','status':'POST_RENAME_FAILURE','source':C,'destination':DEST,'source_present':pathlib.Path(C).exists(),'error':repr(exc)},sort_keys=True)+'\n').encode())
   raise
 finally: os.close(exfd)
main()
PY
