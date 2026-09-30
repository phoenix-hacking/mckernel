#!/usr/bin/env bash
# Reviewed resume packet for the interrupted cross-filesystem relocation.
# It consumes the already populated temporary destination; it never recopies.
set -Eeuo pipefail
umask 077
readonly SCRATCH=/home/holden/mckernel-work/scratch
readonly C="$SCRATCH/mckernel-exact-candidate-c658175a-scratch-7"
readonly TMP=/home/holden/mckernel-work/retained-exact-candidates/.mckernel-exact-candidate-c658175a-scratch-7.tmp-relocation-15-retry1
readonly DEST=/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-c658175a-scratch-7
readonly FAILURE=/home/holden/mckernel/docs/verification/evidence/native-exact-build-c658175a-scratch7-runtime-self-digest-failure-20260930.json
readonly RELOCATION_FAILURE=/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-relocation-c658175a-archive-path-failure-20260930.json
readonly WRONG_ARCHIVE="$SCRATCH/native-exact-build-failure-c658175a-scratch-7-20260930-1.tar"
readonly ARCHIVE="$SCRATCH/native-exact-build-failure-c658175a-scratch-7-retry1-20260930-1.tar"
readonly PREP_TERMINAL="$SCRATCH/native-exact-candidate-preparation-c658175a-scratch-7-retry1-terminal.json"
readonly REQUEST="$SCRATCH/native-exact-build-request-c658175a-scratch-7-retry1.json"
readonly MANIFEST="$SCRATCH/native-exact-inputs-c658175a-scratch-7-retry1.json"
readonly BUILD_EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-runtimeblob-12.json"
readonly OLD_INTENT="$SCRATCH/native-exact-candidate-preparation-c658175a-scratch-7-terminal.json"
readonly OLD_EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-runtimeblob-12.json"
readonly OLD_LOG="$SCRATCH/native-exact-candidate-preparation-c658175a-scratch-7.log"
readonly LOG="$SCRATCH/native-exact-candidate-relocation-c658175a-scratch7-retry1-20260930.log"
readonly INTENT="$SCRATCH/native-exact-candidate-relocation-c658175a-scratch7-retry1-20260930-intent.json"
readonly TERMINAL="$SCRATCH/native-exact-candidate-relocation-c658175a-scratch7-retry1-20260930-terminal.json"
readonly DELETE_INTENT="$SCRATCH/native-exact-candidate-relocation-c658175a-scratch7-retry1-20260930-deletion-intent.json"
readonly EXCLUSION="$SCRATCH/native-exact-candidate-operational-exclusion-relocation15-retry1.json"
readonly LOCK="$SCRATCH/native-exact-candidate-relocation-c658175a-scratch7-retry1-20260930.lock"
readonly SRC_DEV=1831 DEST_DEV=66306
readonly CANDIDATE_COMMIT=c658175ae1831e2caef6ecf59730a272f1324645
readonly IHK_COMMIT=3114d9e7101ad52030eb3effa849a5c108972a1f
readonly FAILURE_SHA=5cbb715b9f0b99e82f9df36b3c5641ce6fdc83499594d606398a1732ee617c84
readonly PREP_TERMINAL_SHA=99e4f0bf1f52f72a77233d5561b32f13de2eed9c4053efeb25a410ff74466ac4
readonly REQUEST_SHA=7a0a654c353f63e7680245f04d92dd361086abbe29e9e024e0ea42122faad826
readonly MANIFEST_SHA=e63cd03b1bf914e563d48e8b268c9aaebd4f04b99e59a3eb018c49daae9470a3
readonly BUILD_EXCLUSION_SHA=9859dc32c9781a96ba6c0b6f86d14ae8fbf4af61ba0c838169b45ff53336997e
readonly OLD_INTENT_SHA=a9bf9967a1dd78cd64d3cf0ba168af5eb4359533e08f75dd3e518a0b854f87b1
readonly OLD_EXCLUSION_SHA=9859dc32c9781a96ba6c0b6f86d14ae8fbf4af61ba0c838169b45ff53336997e
readonly OLD_LOG_SHA=47344ca5a5652821e7e77f3ca041c06c5424ef5496ac946e16d105d0d525982f
readonly RELOCATION_RELEASE_COMMIT=${RELOCATION_RELEASE_COMMIT:?reviewed fetched release required}
readonly RELOCATION_PACKET_PATH=docs/verification/evidence/native-exact-candidate-relocation-c658175a-scratch7-20260930.sh
export PRIOR_INTENT_PATH="$OLD_INTENT" PRIOR_EXCLUSION_PATH="$OLD_EXCLUSION" PRIOR_LOG_PATH="$OLD_LOG"
die(){ echo "FAIL-CLOSED: $*" >&2; exit 1; }
sha(){ /usr/bin/sha256sum -- "$1" | /usr/bin/awk '{print $1}'; }
[[ ${EUID:-1} -ne 0 ]] || die root-launch-prohibited
: "${RELOCATION_RELEASE_COMMIT:?set reviewed fetched resume release}"
: "${RELOCATION_PACKET_SHA256:?set reviewed resume packet blob hash}"
: "${RELOCATION_TEST_SHA256:?set reviewed resume test blob hash}"
: "${RELOCATION_ARCHIVE_SHA256:?set exact retained archive sha256}"
: "${RELOCATION_FAILURE_SHA256:?set committed archive-path failure sha256}"
[[ "$RELOCATION_RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die release-format
[[ "$RELOCATION_ARCHIVE_SHA256" =~ ^[0-9a-f]{64}$ ]] || die archive-sha-format
[[ "$RELOCATION_FAILURE_SHA256" =~ ^[0-9a-f]{64}$ ]] || die failure-sha-format
if [[ ! -e "$ARCHIVE" && ! -L "$ARCHIVE" ]]; then
  readonly ARCHIVE_TMP="$ARCHIVE.tmp-relocation-15-retry1"
  [[ ! -e "$ARCHIVE_TMP" && ! -L "$ARCHIVE_TMP" ]] || die archive-temp-exists
  /usr/bin/tar --format=posix -cf "$ARCHIVE_TMP" -C "$SCRATCH" \
    "native-exact-build-output-c658175a-scratch-7-retry1" \
    "native-exact-build-evidence-c658175a-scratch-7-retry1" \
    "native-exact-build-request-c658175a-scratch-7-retry1.json" \
    "native-exact-inputs-c658175a-scratch-7-retry1.json" \
    "native-exact-candidate-preparation-c658175a-scratch-7-retry1-terminal.json" \
    "native-exact-candidate-operational-exclusion-runtimeblob-12.json" \
    -C /home/holden/mckernel "docs/verification/evidence/native-exact-build-c658175a-scratch7-runtime-self-digest-failure-20260930.json"
  /usr/bin/sync -f "$ARCHIVE_TMP"
  /usr/bin/mv -T --no-target-directory "$ARCHIVE_TMP" "$ARCHIVE"
fi
[[ "$(sha "$ARCHIVE")" == "$RELOCATION_ARCHIVE_SHA256" ]] || die archive-hash
for p in "$LOG" "$INTENT" "$TERMINAL" "$DELETE_INTENT" "$EXCLUSION"; do [[ ! -e "$p" && ! -L "$p" ]] || die output-exists; done
for p in "$C" "$FAILURE" "$RELOCATION_FAILURE" "$WRONG_ARCHIVE" "$ARCHIVE" "$PREP_TERMINAL" "$REQUEST" "$MANIFEST" "$BUILD_EXCLUSION" "$OLD_INTENT" "$OLD_EXCLUSION" "$OLD_LOG"; do [[ -e "$p" && ! -L "$p" ]] || die missing-preserved-input; done
[[ "$(sha "$FAILURE")" == "$FAILURE_SHA" ]] || die failure-hash
[[ "$(sha "$RELOCATION_FAILURE")" == "$RELOCATION_FAILURE_SHA256" ]] || die relocation-failure-hash
[[ "$(sha "$WRONG_ARCHIVE")" == "c046cb5572a7ef102f6069c330f256c3a89d95e8dccdbc284e0a3f95469bda54" ]] || die wrong-archive-hash
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
SRC_DEV,DEST_DEV=1831,66306; SOURCE_ID=(1831,6684719); TMP_ID=None
REPO='/home/holden/mckernel'; CANDIDATE='c658175ae1831e2caef6ecf59730a272f1324645'; IHK='3114d9e7101ad52030eb3effa849a5c108972a1f'
PACKET='docs/verification/evidence/native-exact-candidate-relocation-c658175a-scratch7-20260930.sh'; TEST='scripts/tests/test_native_exact_candidate_relocation_c658175a_scratch7_20260930.py'
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
 if (os.stat(C).st_dev,os.stat(C).st_ino)!=SOURCE_ID: raise RuntimeError('identity-binding')
 if pathlib.Path(TMP).exists() or pathlib.Path(TMP).is_symlink(): raise RuntimeError('temporary-exists')
 pathlib.Path(TMP).mkdir(mode=0o700)
 try:
  cp=subprocess.run(['/usr/bin/rsync','-aHAX','--numeric-ids','--delete','--',C+'/',TMP+'/'],capture_output=True,text=True)
  if cp.returncode or cp.stderr: raise RuntimeError('cross-fs-copy-failed')
  if (os.stat(TMP).st_dev,os.stat(TMP).st_ino)[0] != DEST_DEV: raise RuntimeError('temporary-device')
 except Exception:
  safe_remove(TMP,DEST_DEV,os.stat(TMP).st_ino); raise
 ancestor_paths=('/home','/home/holden','/home/holden/mckernel-work','/home/holden/mckernel-work/scratch',C,'/home/holden/mckernel-work/retained-exact-candidates',TMP)
 ancestor_ids=[]
 for p in ancestor_paths:
  s=os.lstat(p)
  if stat.S_ISLNK(s.st_mode): raise RuntimeError('ancestor-symlink')
  ancestor_ids.append((p,s.st_dev,s.st_ino))
 mounts=open('/proc/self/mountinfo',errors='replace').read()
 if mount_points(mounts,C) or mount_points(mounts,TMP): raise RuntimeError('nested-mount')
 if git('rev-parse','refs/remotes/origin/codex/local-native-staging-repair')!=os.environ['RELOCATION_RELEASE_COMMIT']: raise RuntimeError('release-not-fetched')
 if git('cat-file','-t',os.environ['RELOCATION_RELEASE_COMMIT'])!='commit': raise RuntimeError('release-missing')
 require_hash(REPO+'/'+PACKET,os.environ['RELOCATION_PACKET_SHA256']); require_hash(REPO+'/'+TEST,os.environ['RELOCATION_TEST_SHA256'])
 env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PATH='/usr/bin:/bin',HOME='/nonexistent')
 for path,key in ((PACKET,'RELOCATION_PACKET_SHA256'),(TEST,'RELOCATION_TEST_SHA256')):
  blob=subprocess.check_output(['/usr/bin/git','-C',REPO,'show',os.environ['RELOCATION_RELEASE_COMMIT']+':'+path],env=env)
  if hashlib.sha256(blob).hexdigest()!=os.environ[key]: raise RuntimeError('release-blob-binding')
 if subprocess.run(['/usr/bin/git','-C',C,'rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=CANDIDATE: raise RuntimeError('candidate-commit-binding')
 if subprocess.run(['/usr/bin/git','-C',C+'/ihk','rev-parse','HEAD'],env=env,check=True,text=True,capture_output=True).stdout.strip()!=IHK: raise RuntimeError('ihk-commit-binding')
 failure=json.load(open(RELOCATION_FAILURE))
 if failure.get('candidate_sha')!=CANDIDATE or failure.get('phase')!='phase-0-before-compilation': raise RuntimeError('failure-record-provenance')
 if failure.get('execution',{}).get('lease_absent') is not True and failure.get('retained_evidence',{}).get('lease_absent') is not True: raise RuntimeError('terminal-lease-tombstone-missing')
 active()
 if privileged_references([C,TMP,DEST]): raise RuntimeError('active-process-reference')
 if any(os.statvfs(p).f_bavail*os.statvfs(p).f_frsize < floor+512*1024**2 for p,floor in ((str(pathlib.Path(C).parent),12*1024**3),(str(pathlib.Path(DEST).parent),16*1024**3))): raise RuntimeError('insufficient-capacity-floor')
 for p in (os.environ.get('PRIOR_INTENT_PATH'),os.environ.get('PRIOR_EXCLUSION_PATH'),os.environ.get('PRIOR_LOG_PATH')):
  if not p or not pathlib.Path(p).is_file(): raise RuntimeError('prior-artifact-binding-missing')
 exfd=os.open(EXCLUSION,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(exfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ex=(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-exclusion.v1','source':C,'temporary':TMP,'owner_pid':os.getpid()},sort_keys=True)+'\n').encode(); off=0
  while off<len(ex):
   n=os.write(exfd,ex[off:])
   if n<=0: raise OSError('short exclusion write')
   off+=n
  os.fsync(exfd); xdir=os.open(str(pathlib.Path(EXCLUSION).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(xdir); os.close(xdir)
  durable(INTENT,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-intent.v1','source':C,'temporary':TMP,'destination':DEST,'archive':ARCHIVE,'archive_sha256':os.environ['RELOCATION_ARCHIVE_SHA256'],'status':'VERIFYING_PRESERVED_COPY'},sort_keys=True)+'\n').encode())
  src=inventory(C,SRC_DEV); tmp=inventory(TMP,DEST_DEV)
  if not equal(src,tmp): raise RuntimeError('copy-verification')
  check=subprocess.run(['/usr/bin/rsync','-acHAXni','--delete','--',C+'/',TMP+'/'],capture_output=True,text=True)
  if check.returncode or check.stdout or check.stderr: raise RuntimeError('rsync-verification')
  if inventory(C,SRC_DEV)!=src: raise RuntimeError('source-mutated-during-resume')
  if os.stat(TMP).st_dev!=DEST_DEV or inventory(TMP,DEST_DEV)!=tmp: raise RuntimeError('temporary-mutated-during-copy')
  parent=str(pathlib.Path(DEST).parent); rename_noreplace(TMP,DEST,parent)
  pfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(pfd); os.close(pfd)
  try:
   if os.stat(DEST).st_dev!=DEST_DEV or not equal(src,inventory(DEST,DEST_DEV)): raise RuntimeError('rename-verification')
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
   rec={'schema':'mckernel.native-exact-candidate-relocation-c658175a-scratch7.v1','status':'PASS','source':C,'destination':DEST,'archive':ARCHIVE,'archive_sha256':os.environ['RELOCATION_ARCHIVE_SHA256'],'resume_namespace':'relocation-15','entry_count':len(src),'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}
   data=(json.dumps(rec,sort_keys=True)+'\n').encode(); durable(TERMINAL,data); append_log(data)
  except Exception as exc:
   if not pathlib.Path(TERMINAL).exists(): durable(TERMINAL,(json.dumps({'schema':'mckernel.native-exact-candidate-relocation-resume-post-rename-failure.v1','status':'POST_RENAME_FAILURE','source':C,'destination':DEST,'source_present':pathlib.Path(C).exists(),'error':repr(exc)},sort_keys=True)+'\n').encode())
   raise
 finally: os.close(exfd)
main()
PY
