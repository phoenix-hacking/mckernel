"""ONE exact read-only post-effect quarantine observation. No lock acquisition or recovery."""
import base64,hashlib,json,os,stat,subprocess,time,types
from pathlib import Path
P=Path('/home/holden/mckernel-work/host-preparation/phase5-current-pass-image-terminal-20261020-1')
F=P/'finite-chain-preparation-1'
PID,START,PARENT=2069459,'30125126',2069456
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
OLD=Path('/home/holden/mckernel-work/host-preparation/phase5-image-postbuild-terminal-preparation-20261020-1/failure-case-1/holder-retirement-preparation-1/retire_exact_cleanup_holder.py');OLD_SHA='e042cec3d52c278ce9a200290a5904610f82202754580831fff30c3e9de31c2e'
ENGINE=P/'cleanup_pass_image.py';ENGINE_SHA='fdaacfcf2f4875a3e70d06a30dd109a7d603b59ecababce3a1d02863f50fa305'
RELEASE=F/'cleanup-execution-release.json';RELEASE_SHA='204ba1b010b1bcdf4651f643a23f101809dc1556ade4b7203344e453746b7cfc'
MAX=1<<20

def load(path,expected):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,'source differs'
 m=types.ModuleType('_readonly_'+path.stem);m.__file__=str(path);exec(compile(raw,str(path),'exec'),m.__dict__);return m

def full_file(path):
 # Same full stable-FD read contract as genuine current-root readback b760.
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_uid==before.st_gid==1000 and before.st_size<=MAX
  chunks=[];total=0
  while total<=before.st_size:
   part=os.read(fd,min(65536,before.st_size+1-total))
   if not part:break
   chunks.append(part);total+=len(part)
  raw=b''.join(chunks);after=os.fstat(fd);named=os.lstat(path)
  fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
  assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields) and len(raw)==after.st_size
  row=dict(path=str(path),device=after.st_dev,inode=after.st_ino,uid=after.st_uid,gid=after.st_gid,mode=oct(stat.S_IMODE(after.st_mode)),nlink=after.st_nlink,size=after.st_size,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns,sha256=hashlib.sha256(raw).hexdigest())
  return row,raw
 finally:os.close(fd)

def process(h,pid):
 fields=h.proc_stat(pid);status=dict(x.split(':',1) for x in h.proc_bytes('/proc/%d/status'%pid).decode().splitlines() if ':' in x);cmd=h.proc_bytes('/proc/%d/cmdline'%pid);exe=os.readlink('/proc/%d/exe'%pid);meta=os.stat('/proc/%d/exe'%pid)
 fds=[]
 for name in sorted(os.listdir('/proc/%d/fd'%pid),key=int):
  assert len(fds)<64
  path='/proc/%d/fd/%s'%(pid,name);s=os.stat(path);fds.append(dict(fd=int(name),target=os.readlink(path),dev=s.st_dev,ino=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,size=s.st_size))
 again=h.proc_stat(pid);assert again[19]==fields[19]
 return dict(pid=pid,starttime=fields[19],parent=int(fields[1]),state=fields[0],uid=status['Uid'].split(),gid=status['Gid'].split(),threads=int(status['Threads']),argv=[x.decode() for x in cmd.rstrip(b'\0').split(b'\0')],cmdline_sha256=hashlib.sha256(cmd).hexdigest(),exe=exe,exe_device=meta.st_dev,exe_inode=meta.st_ino,exe_size=meta.st_size,exe_sha256=h.file_identity(Path(exe))[0]['sha256'],fds=fds,children=h.proc_bytes('/proc/%d/task/%d/children'%(pid,pid)).decode(),tasks=sorted(os.listdir('/proc/%d/task'%pid)))

def main():
 assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
 h=load(OLD,OLD_SHA);m=load(ENGINE,ENGINE_SHA);raw=RELEASE.read_bytes();assert hashlib.sha256(raw).hexdigest()==RELEASE_SHA;r=m.parse(raw);obs=r['observation']
 assert h.proc_bytes('/proc/sys/kernel/random/boot_id',128).decode().strip()==BOOT
 child=process(h,PID);parent=process(h,PARENT);assert child['starttime']==START and child['parent']==PARENT and child['uid']==child['gid']==['0']*4 and child['threads']==1 and child['children'].strip()==''
 assert str(ENGINE) in child['argv'] and RELEASE_SHA==hashlib.sha256(raw).hexdigest()
 outer_fields=h.proc_stat(parent['parent']);outer=dict(pid=parent['parent'],starttime=outer_fields[19],parent=int(outer_fields[1]),state=outer_fields[0])
 paths=[('transaction_mutex',m.MUTEX),('plan',m.PLAN),('journal',m.JOURNAL),('capture',m.CAPTURE),('quarantine',m.QUARANTINE),('common_archive',m.archive_paths()[0]),('shared_archive',m.archive_paths()[1])]
 files={};kept={}
 for role,path in paths:
  fd,data=full_file(path);files[role]=dict(fd=fd,raw_base64=base64.b64encode(data).decode());kept[role]=data
 assert files['quarantine']['fd']['sha256']=='72ba2ee2d4ab7a686beeabb1925affbef05e5f7cc72c54fc26c4ca66ef8e83ec'
 locks_raw=h.proc_bytes('/proc/locks',MAX);locks=[];wanted={(0,27,4),(os.major(files['transaction_mutex']['fd']['device']),os.minor(files['transaction_mutex']['fd']['device']),files['transaction_mutex']['fd']['inode'])}
 for line in locks_raw.decode().splitlines():
  words=line.split();words=[x for x in words if x!='->'];assert len(words)==8
  major,minor,inode=words[5].split(':')
  if (int(major,16),int(minor,16),int(inode)) in wanted:locks.append(words[1:])
 absent=[]
 for path in (m.LEASE,m.ATTEMPT,m.SHARED):
  try:s=os.lstat(path);absent.append(dict(path=str(path),absent=False,device=s.st_dev,inode=s.st_ino,mode=s.st_mode))
  except FileNotFoundError:absent.append(dict(path=str(path),absent=True,errno=2))
 checks={}
 def check(name,fn):
  try:checks[name]=dict(passed=bool(fn()))
  except BaseException as e:checks[name]=dict(passed=False,error_type=type(e).__name__,message=str(e)[:1024])
 plan=m.parse(kept['plan']);journal=kept['journal'];rows=[m.parse(x) for x in journal.splitlines()];plan_sha=m.digest(m.canonical(plan))
 def journal_valid():
  assert kept['plan']==m.canonical(plan)+b'\n' and plan['release_sha256']==m.digest(m.canonical(r)) and len(rows)==8
  legal=[(e,i) for i in range(2) for e in ('before_exchange','after_exchange','release','after_release')];previous=plan_sha
  for seq,(row,(event,index)) in enumerate(zip(rows,legal)):
   body=dict(event=event,index=index,sequence=seq,plan_sha256=plan_sha,previous=previous,plan_identity=[files['plan']['fd']['device'],files['plan']['fd']['inode']]);wanted=dict(body,hash=m.digest(m.canonical(body)));assert row==wanted and journal.splitlines(keepends=True)[seq]==m.canonical(wanted)+b'\n';previous=row['hash']
  return True
 check('exact_eight_event_journal_no_complete',journal_valid)
 def archives_valid():
  for role,path in [('common_archive',m.ATTEMPT),('shared_archive',m.SHARED)]:
   old=next(x for x in obs['retained_exclusions'] if x['path']==str(path));now=files[role]['fd'];assert all(now[k]==old[k] for k in ('device','inode','uid','gid','mode','nlink','size','sha256'))
  return True
 check('original_two_record_archive_identities',archives_valid)
 selected=[m.observe_identity(Path(x['path'])) for x in obs['selected_files']];inventories={str(root):m.metadata_inventory(root) for root in (m.OUTPUT,m.EVIDENCE)}
 check('all_selected_78_unchanged',lambda:selected==obs['selected_files'])
 check('both_complete_inventories_unchanged',lambda:inventories==obs['inventories'])
 case=m.parse(m.read_bounded(P/'PASS-CASE-STATIC.json'));objects=[m.observe_identity(Path(x)) for x in case['finite_unique_paths']];meta_ref=next(x for x in obs['selected_files'] if x['path'].endswith('/new-object-metadata.json'));original=m.parse(m.read_bounded(Path(meta_ref['path'])))
 check('all_finite_74_unchanged',lambda:objects==original['objects'])
 m.RELEASE=r;m.DEVICE=obs['root']['device'];m.CANDIDATE=Path(json.loads(m.read_bounded(m.REQUEST))['source_root']);m.PROTECTED=obs['selected_files']
 check('actual_protected_files',lambda:(m.protected_files() is None))
 check('actual_mount_binding',lambda:(m.validate_mount() is None))
 preserved=[]
 for root in (m.OUTPUT,m.EVIDENCE):
  pfd,_=m.directory(root.parent);fd=os.open(root.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=pfd)
  try:
   s=os.fstat(fd);old=obs['inventories'][str(root)][0];assert(s.st_dev,s.st_ino,s.st_nlink,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(old['device'],old['inode'],old['nlink'],1000,1000,0o700)
   if root==m.EVIDENCE:
    terminal=next(x for x in obs['selected_files'] if x['path']==str(m.TERMINAL));m.read_at(fd,m.TERMINAL.name,(terminal['sha256'],terminal['inode'],terminal['size']),expected_device=old['device'])
   named=os.stat(root.name,dir_fd=pfd,follow_symlinks=False);assert(s.st_dev,s.st_ino)==(named.st_dev,named.st_ino);preserved.append(dict(path=str(root),device=s.st_dev,inode=s.st_ino,nlink=s.st_nlink,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),terminal_checked=root==m.EVIDENCE))
  finally:os.close(fd);os.close(pfd)
 command=['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--type','container',r['observation']['target']['container_id']]
 cp=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},timeout=30,check=False);assert len(cp.stdout)<=MAX and len(cp.stderr)<=MAX
 docker=dict(argv=command,returncode=cp.returncode,stdout_base64=base64.b64encode(cp.stdout).decode(),stderr_base64=base64.b64encode(cp.stderr).decode(),direct_child_joined=True)
 for role,path in paths:assert full_file(path)[0]==files[role]['fd']
 assert h.proc_stat(PID)[19]==START and h.proc_bytes('/proc/sys/kernel/random/boot_id',128).decode().strip()==BOOT
 print(json.dumps(dict(status='READ_ONLY_POST_EFFECT_QUARANTINE_STATE',epoch=time.time(),boot_id=BOOT,holder=child,parent=parent,outer=outer,engine_sha256=ENGINE_SHA,release_file_sha256=RELEASE_SHA,release_canonical_sha256=m.digest(m.canonical(r)),files=files,plan=plan,journal_events=rows,plan_sha256=plan_sha,matched_lock_rows=locks,lock_report_sha256=hashlib.sha256(locks_raw).hexdigest(),active_name_states=absent,checks=checks,selected_files=selected,inventories=inventories,finite_objects=objects,preserved_directory_fd_checks=preserved,container_inspect=docker,mutation_performed=False,mutex_acquired=False,signals_sent=0,original_inner_failure_cause_recovered=False,terminal_completion_claim=False),sort_keys=True))
if __name__=='__main__':main()
