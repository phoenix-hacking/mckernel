"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Read-only exact failed smoke observation; no signals or cleanup."""
import base64,hashlib,json,os,stat,subprocess,time
from pathlib import Path
PID=3502874
START=52840587
ROOT=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/none-attach-smoke-1/p.owner-7247e16d234147afa148cd0ef24206d4')
assert os.geteuid()==0
def proc(pid):
 p=Path('/proc')/str(pid)
 try:b=(p/'stat').read_bytes()
 except FileNotFoundError:return None
 t=b.decode().rpartition(') ')[2].split();return {'pid':pid,'state':t[0],'ppid':int(t[1]),'pgid':int(t[2]),'sid':int(t[3]),'start':int(t[19])}
anchor=proc(PID)
if anchor is not None:assert anchor['start']==START,'anchor PID reused'
allrows=[]
for p in Path('/proc').iterdir():
 if p.name.isascii() and p.name.isdigit():
  x=proc(int(p.name))
  if x:allrows.append(x)
assert len(allrows)<=32768
selected={PID};change=True
while change:
 change=False
 for x in allrows:
  if x['sid']==PID or x['ppid'] in selected:
   if x['pid'] not in selected:selected.add(x['pid']);change=True
rows=[]
for x in allrows:
 if x['pid'] not in selected:continue
 q=Path('/proc')/str(x['pid']);before=proc(x['pid'])
 if before!=x:rows.append({'initial':x,'unstable':True});continue
 y={'initial':x}
 for name in ('cmdline','status','wchan'):
  try:
   with (q/name).open('rb') as f:raw=f.read(32769)
   assert len(raw)<=32768;y[name]=raw.decode('utf-8','replace')
  except FileNotFoundError:y[name]='ENOENT'
 try:y['exe']=os.readlink(q/'exe')
 except FileNotFoundError:y['exe']='ENOENT'
 y['after']=proc(x['pid']);rows.append(y)
rootmeta=ROOT.lstat();assert stat.S_ISDIR(rootmeta.st_mode) and not ROOT.is_symlink()
files=[];total=0
for q in sorted(ROOT.iterdir()):
 s=q.lstat();assert stat.S_ISREG(s.st_mode) and not q.is_symlink() and s.st_nlink==1
 assert len(files)<4096 and s.st_size<=2097152
 fd=os.open(q,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and (before.st_dev,before.st_ino)==(s.st_dev,s.st_ino)
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(2097153)
  after=os.fstat(fd)
 finally:os.close(fd)
 total+=len(raw);assert len(raw)<=2097152 and total<=2097152
 z=q.lstat();stable=all(getattr(s,k)==getattr(before,k)==getattr(after,k)==getattr(z,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'))
 files.append({'name':q.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'stable':stable,'base64':base64.b64encode(raw).decode()})
lock=Path('/run/lock/mckernel-development.lock').stat();assert (lock.st_dev,lock.st_ino)==(27,4)
commands=[]
for filter in ('name=^/mckernel-native-diagnostic-7247e16d234147afa148cd0ef24206d4$','label=mckernel.native-diagnostic.owner=7247e16d234147afa148cd0ef24206d4'):
 a=['/usr/bin/docker','--config=/dev/null','--host=unix:///var/run/docker.sock','ps','-aq','--no-trunc','--filter',filter];c=subprocess.run(a,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'});assert len(c.stdout)+len(c.stderr)<=65536
 commands.append({'argv':a,'returncode':c.returncode,'stdout':c.stdout.decode(),'stderr':c.stderr.decode()})
print(json.dumps({'scope':__doc__,'at_unix':time.time(),'anchor_before':anchor,'anchor_after':proc(PID),'processes':rows,'owner_root':str(ROOT),'owner_root_metadata':{'device':rootmeta.st_dev,'inode':rootmeta.st_ino,'uid':rootmeta.st_uid,'gid':rootmeta.st_gid,'mode':oct(rootmeta.st_mode)},'owner_files':files,'commands':commands,'mutex':[lock.st_dev,lock.st_ino],'proc_locks':Path('/proc/locks').read_text(),'mutations':0,'physical_clearance':False},sort_keys=True))
