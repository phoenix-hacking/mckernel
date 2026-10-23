"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact fresh read-only admission for selected LONG operation. No execution release.
No signals, daemon creation, storage mutation or owner cleanup. Transient mutex flock only.
"""
import ast,fcntl,hashlib,importlib.util,json,os,resource,stat,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
CONFIG_SHA = '5fe8bfb085a5f8737aa45a61a068072d3a83aab38c26a5243a3b4af3e92f48ef'
ENGINE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/matched-image-terminal-preparation-1/bound-matched-image-terminal-source-2/cleanup_pass_image.py')
ENGINE_SHA='59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
def need(v,m):
 if not v:raise RuntimeError(m)
def run(a):
 p=subprocess.run(a,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
 if p.returncode or p.stderr or len(p.stdout)>4*1024**2:
  sys.stderr.write(json.dumps(dict(argv=a,returncode=p.returncode,stdout_bytes=len(p.stdout),stderr=p.stderr[:65536].decode('utf-8','replace'),stderr_total_bytes=len(p.stderr)))+'\n')
  raise RuntimeError('bounded read-only command')
 return p.stdout.decode()
def filepin(path,cap):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=cap,'bounded regular single-link input')
        h=hashlib.sha256();n=0
        while True:
            raw=os.read(fd,1048576)
            if not raw:break
            n+=len(raw);need(n<=cap,'input grew past cap');h.update(raw)
        after=os.fstat(fd);named=os.lstat(path)
        fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
        need(n==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields),'stable file identity')
        return dict(path=str(path),size=n,sha256=h.hexdigest())
    finally:os.close(fd)

def inputs():
 raw=(D/'QUERY-INPUTS.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,'exact query input binding')
 return json.loads(raw)

def parent_fact(path):
 fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  a=os.fstat(fd);children=os.listdir(fd);b=os.fstat(fd);c=os.lstat(path)
  fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_mtime_ns','st_ctime_ns')
  need(all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in fields),'stable prepared HOST LONG parent')
  return dict(dev=a.st_dev,ino=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=stat.S_IMODE(a.st_mode),directory=stat.S_ISDIR(a.st_mode),children=children)
 finally:os.close(fd)

def validate_output_path_policy(f,c):
 # Historical retained evidence is required present, never a fresh output.
 expected_old='/home/holden/mckernel-work/native-runs/l12a1/p.owner-'+c['prior_failed_nonce']
 need(c['retained_previous_owner_evidence_paths']==[expected_old] and
      c['retained_previous_owner_retirement_authority']==c['physical'] and
      c['physical']['sha256']=='591cdb070b8f6cfe18a9903a69e3603a5590f737c12e478fc01833d9a5cef01f',
      'exact retained historical owner policy and retirement authority')
 need(f['retained_previous_owner_evidence']=={expected_old:True},'required retained historical owner evidence present')
 parent=Path(c['operation']['HOST_parent']);nonce=c['operation']['nonce']
 expected_new={c['operation']['capture_directory'],str(parent.with_name(parent.name+'.owner-'+nonce)),
               str(parent/('attempt-'+nonce)),c['operation']['future_release_path'],c['operation']['future_request_path']}
 need(set(f['output_paths_exist'])==expected_new and not expected_new.intersection({expected_old}),
      'exact new output path inventory excludes historical evidence')
 need(all(type(v) is bool for v in f['output_paths_exist'].values()) and
      not any(f['output_paths_exist'].values()),'fresh LONG capture owner attempt and unpublished release/request paths absent')

def validate(f,c,growth):
 need(f['uid']==f['euid']==0 and f['affinity']==[7],'root query CPU7')
 need(f['proc']['status']=='COMPLETE' and f['proc']['failure'] is None and f['proc']['publishers']==[] and len(f['proc']['snapshots'])==2,'complete publisher-free census')
 need(f['physical']['verdict']=='PASS_ACTUAL_CANCELLED_LONG_PHYSICAL_RETIREMENT_AND_CURRENT_POSTJOIN' and f['physical']['current_live_postjoin']['state']=='CANCELLED_LONG_POSITIVELY_RETIRED' and f['physical']['current_live_postjoin']['nonce']==c['prior_failed_nonce'] and f['physical']['current_live_postjoin']['owner_lease_retained'] is False and f['physical']['current_live_postjoin']['container_absent'] is True and f['physical']['current_live_postjoin']['permanent_mutex_device_inode']==[27,4] and f['physical']['current_live_postjoin']['mutex_free'] is True and f['physical']['current_live_postjoin']['shared_paths_absent']==8,'actual cancelled LONG positive physical/current postjoin')
 p=f['parent'];need(p['directory'] and p['uid']==p['gid']==1000 and p['mode']==0o700 and p['children']==[],'fresh private HOST LONG parent exists empty UID1000 mode700')
 validate_output_path_policy(f,c)
 need(not any(f['ownership_paths_exist'].values()),'exact SDK image launcher ownership paths absent')
 need(f['lock']==[27,4,0,0,1] and f['locks']==[] and f['lock_acquired'] is True,'stable permanent mutex27:4 available')
 need(f['docker_running']=='' and all(v=='' for v in f['docker_identities'].values()),'no competing container or current nonce identity')
 need(f['server']['Version']=='26.1.3' and f['server']['GitCommit']=='26.1.3-0ubuntu1~20.04.1' and f['docker_info']['ServerVersion']=='26.1.3' and f['daemon_binding']['mode']=='none' and f['daemon_binding']['source_package']=='docker.io-app=26.1.3-0ubuntu1~20.04.1' and f['daemon_binding']['container_source_sha256']=='6ed6a9d2a3a32ecf6cbb91eaefdb5925c1316e8ea35e0856b7bb85530d143739','source-supported exact daemon NONE version')
 need(f['image_ok'] is True and f['mounts_ok'] is True,'accepted image and exact readonly mount prerequisites')
 need(f['cgroup']==c['owner_constants']['CGROUP'],'unchanged reviewed cgroup profile')
 need(f['allowed_container_cpus'] is True and f['memory_available']>=int(16.2158*2**30),'fresh CPU2-5 and aggregate available memory')
 need(f['launcher_phase']=='running' and f['launcher_stop_reason'] is None,'launcher active')
 need(f['backing']['inode']==47468427 and f['backing']['size']==110*2**30 and f['backing']['regular'] and f['backing']['canonical'] and f['backing']['host_device']==f['HOST_device'] and f['HOST_device']!=f['scratch_device'],'exact110GiB HOST backing identity')
 need(f['mount']==[dict(target='/home/holden/mckernel-work/scratch',uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52')] and f['uuid_device']==f['scratch_device'] and f['loop_backing']=='/home/holden/mckernel-work/scratch.ext4','fresh UUID loop backing identity')
 required=growth.require_growth(f['admission'],f['HOST_available'],f['scratch_available'],f['backing']['gap'])
 need(required=={'host_required_bytes':140534349824,'scratch_required_bytes':13899923456},'exact positive budgetd91d arithmetic')
 return required

def collect(c):
 need(os.getuid()==os.geteuid()==0,'authenticated root read-only query')
 need(os.sched_getaffinity(0)=={7},'root query CPU7')
 source_pins=[]
 for row in c['pins']:
  fact=filepin(Path(row['path']),2**20);need(fact['sha256']==row['sha256'] and fact['size']==row['bytes'],'exact source/input pin');source_pins.append(fact)
 budget=json.loads(Path(c['budget']['path']).read_bytes());admission=budget['capacity_admission_proposal']
 physical=json.loads(Path(c['physical']['path']).read_bytes())
 growth_spec=importlib.util.spec_from_file_location('accepted_current110_growth',c['growth']['path']);growth=importlib.util.module_from_spec(growth_spec);growth_spec.loader.exec_module(growth)
 raw=ENGINE.read_bytes();need(hashlib.sha256(raw).hexdigest()==ENGINE_SHA,'accepted census source')
 code=next(ast.literal_eval(n.value) for n in ast.parse(raw).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets))
 start=Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
 proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'p12-LONG-current-live-admission-20261023-1',str(os.getpid()),start]))
 sd=Path(c['operation']['controller']['path']).parent;parent=Path(c['operation']['HOST_parent'])
 g_parent=growth.output_parent(str(parent),fresh=True)
 parent_info=parent_fact(parent)
 outputs={str(p):os.path.lexists(p) for p in [Path(c['operation']['capture_directory']),parent.with_name(parent.name+'.owner-'+c['operation']['nonce']),parent/('attempt-'+c['operation']['nonce']),Path(c['operation']['future_release_path']),Path(c['operation']['future_request_path'])]}
 # Retained prior-owner evidence is pinned by physical591c; only prospective outputs require absence.
 # Exact lease/exclusion list inherited unchanged from accepted M05 query.
 leases=['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json']
 lock=Path('/run/lock/mckernel-development.lock').stat();key='%02x:%02x:%d'%(os.major(lock.st_dev),os.minor(lock.st_dev),lock.st_ino)
 locks=[l for l in Path('/proc/locks').read_text().splitlines() if key in l.split()]
 fd=os.open('/run/lock/mckernel-development.lock',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:
  need((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(27,4),'stable27:4 FD');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();scratch=Path('/home/holden/mckernel-work/scratch');device=scratch.stat().st_dev;host_device=sd.stat().st_dev
  uuid=Path('/dev/disk/by-uuid/2a5768c8-718d-4914-bdc0-6b32c5a92a52').stat();need(stat.S_ISBLK(uuid.st_mode),'UUID block device')
  host=os.statvfs(sd);other=os.statvfs(scratch)
  mount=json.loads(run(['/usr/bin/findmnt','-J','-o','TARGET,UUID','-T',str(scratch)]))['filesystems']
  identities={}
  for filt in [kind+nonce+suffix for nonce in (c['operation']['nonce'],c['prior_failed_nonce']) for kind,suffix in [('name=^/mckernel-native-diagnostic-','$'),('label=mckernel.native-diagnostic.owner=','')]]:
   identities[filt]=run(['/usr/bin/docker','ps','-aq','--no-trunc','--filter',filt])
  server=json.loads(run(['/usr/bin/docker','version','--format','{{json .Server}}']))
  info=json.loads(run(['/usr/bin/docker','info','--format','{{json .}}']))
  # NONE availability is bound to accepted exact source/version; no create/log request.
  transport_tree=ast.parse(Path(c['operation']['runtime_files']['long_transport.py']['path']).read_bytes())
  daemon=next(ast.literal_eval(n.value) for n in transport_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DAEMON_ALLOCATION_BINDING' for t in n.targets))
  image=json.loads(run(['/usr/bin/docker','image','inspect',c['owner_constants']['IMAGE']]))
  need(filepin(Path(c['owner_constants']['IMAGE_RECORD']),2**20)['sha256']==c['owner_constants']['IMAGE_RECORD_SHA256'],'accepted image record pin')
  retained=json.loads(Path(c['owner_constants']['IMAGE_RECORD']).read_bytes());need(len(image)==len(retained)==1,'exact image records');image=image[0];retained=retained[0]
  mounts=[Path('/home/holden/mckernel'),scratch,*[Path(p) for p in c['owner_constants']['EXTRA_READONLY']]]
  mount_facts=[dict(path=str(p),resolved=str(p.resolve(strict=True)),mode=p.stat().st_mode) for p in mounts]
  state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
  cpus=Path('/sys/devices/system/cpu/online').read_text().strip();online=set()
  for item in cpus.split(','):
   ends=item.split('-');online.update(range(int(ends[0]),int(ends[-1])+1))
  f=dict(uid=os.getuid(),euid=os.geteuid(),affinity=sorted(os.sched_getaffinity(0)),proc=proc,physical=physical,parent=parent_info,output_paths_exist=outputs,ownership_paths_exist={p:os.path.lexists(p) for p in leases},lock=[lock.st_dev,lock.st_ino,lock.st_uid,lock.st_gid,lock.st_nlink],locks=locks,lock_acquired=True,docker_running=run(['/usr/bin/docker','ps','-q','--no-trunc']),docker_identities=identities,server=server,docker_info=info,daemon_binding=daemon,image_ok=image.get('Id')==c['owner_constants']['IMAGE'] and image.get('Architecture')=='amd64' and image.get('Os')=='linux' and image.get('Config')==retained.get('Config') and image.get('RootFS')==retained.get('RootFS'),mounts_ok=all(r['path']==r['resolved'] for r in mount_facts),mount_facts=mount_facts,cgroup={p:Path(p).read_text().strip() for p in c['owner_constants']['CGROUP']},allowed_container_cpus={2,3,4,5}<=online,memory_available=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024,launcher_phase=state['phase'],launcher_stop_reason=state['stop_reason'],backing=dict(inode=bs.st_ino,size=bs.st_size,allocated=bs.st_blocks*512,gap=max(0,bs.st_size-bs.st_blocks*512),regular=stat.S_ISREG(bs.st_mode),canonical=Path('/home/holden/mckernel-work/scratch.ext4').resolve(strict=True)==Path('/home/holden/mckernel-work/scratch.ext4'),host_device=bs.st_dev),HOST_device=host_device,scratch_device=device,uuid_device=uuid.st_rdev,loop_backing=Path('/sys/dev/block/%d:%d/loop/backing_file'%(os.major(device),os.minor(device))).read_text().strip(),mount=mount,HOST_available=host.f_bavail*host.f_frsize,scratch_available=other.f_bavail*other.f_frsize,admission=admission,source_pins=source_pins)
  f['retained_previous_owner_evidence']={p:os.path.lexists(p) for p in c['retained_previous_owner_evidence_paths']}
  required=validate(f,c,growth)
 finally:os.close(fd)
 return f,required

def main():
 need(len(sys.argv)==2 and filepin(Path(__file__).resolve(),65536)['sha256']==sys.argv[1],'exact query digest argv')
 c=inputs();f,required=collect(c)
 print(json.dumps(dict(scope=__doc__,status='PASS_FRESH_READ_ONLY_P12_LONG_ADMISSION',observations=f,required=required,at_unix=time.time(),mutation=False,transient_mutex_released=True,execution_release=False,native_acceptance=False),sort_keys=True))
if __name__=='__main__':main()
