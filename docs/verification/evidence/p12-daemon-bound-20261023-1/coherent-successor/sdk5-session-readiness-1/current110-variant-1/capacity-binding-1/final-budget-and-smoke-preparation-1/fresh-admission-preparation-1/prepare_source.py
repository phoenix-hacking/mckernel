"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source assembly only."""
import ast,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/final-budget-and-smoke-preparation-1/fresh-admission-preparation-1')
TOP=REPO.parent
N=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2')
OLD=N/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1/next-native-preparation-1/read_only_m05_HOST_admission.py'
TINY=TOP.parents[3]/'TINY-NONE-SDK5-EXECUTE-NEXT.NOT-RELEASED.json'
# Absolute stable tiny authority, not a fresh variant.
TINY=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/TINY-NONE-SDK5-EXECUTE-NEXT.NOT-RELEASED.json')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
tiny=json.loads(TINY.read_text());controller=Path(tiny['existing_controller']['path']);smoke=Path(tiny['existing_smoke']['path']);request=Path(tiny['existing_request']['path']);owner=Path(tiny['runtime_files']['native_diagnostic_container_owner.py']['path'])
physical=N/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1/next-native-preparation-1/actual-post-physical-1/INDEPENDENT-ACTUAL-PHYSICAL-ACCEPTANCE.json'
assert ref(physical)['sha256']=='1f3c183083e2bfc99f801d0c62f9f563404a699dcc37ede7eef2f37ceaf31c3b'
constants={}
for node in ast.parse(owner.read_bytes()).body:
 if isinstance(node,ast.Assign):
  for name in node.targets:
   if isinstance(name,ast.Name) and name.id in ('IMAGE','IMAGE_RECORD','IMAGE_RECORD_SHA256','EXTRA_READONLY','CGROUP'):
    constants[name.id]=ast.literal_eval(node.value)
pins=[ref(TINY),ref(TOP/'EXACT-POSITIVE-BUDGET.PROPOSED.json'),ref(physical),tiny['existing_controller'],tiny['existing_smoke'],tiny['existing_request'],tiny['actual_Python38_wait_consumer_fixture'],tiny['existing_exact_future_operation'],*tiny['runtime_files'].values(),ref(OLD),ref(Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/source/long_transport.py')),ref(Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'))]
config=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',pins=pins,tiny=tiny,budget=ref(TOP/'EXACT-POSITIVE-BUDGET.PROPOSED.json'),physical=ref(physical),predecessor=ref(OLD),controller=ref(controller),growth=pins[-2],owner_constants=constants)
(D/'QUERY-INPUTS.json').write_text(json.dumps(config,indent=2,sort_keys=True)+'\n')
(D/'accepted_m05_query.preimage.py').write_bytes(OLD.read_bytes())
# Copy exact accepted bounded read-only run body and stable filepin body.
oldtree=ast.parse(OLD.read_bytes());ctr=ast.parse(controller.read_bytes())
run=ast.get_source_segment(OLD.read_text(),next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='run'))
filepin=ast.get_source_segment(controller.read_text(),next(n for n in ctr.body if isinstance(n,ast.FunctionDef) and n.name=='filepin'))
source='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact fresh read-only admission for existing tiny NONE operation. No execution release.
No signals, daemon creation, storage mutation or owner cleanup. Transient mutex flock only.
"""
import ast,fcntl,hashlib,importlib.util,json,os,resource,stat,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
CONFIG_SHA=CONFIG_DIGEST
ENGINE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/matched-image-terminal-preparation-1/bound-matched-image-terminal-source-2/cleanup_pass_image.py')
ENGINE_SHA='59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
def need(v,m):
 if not v:raise RuntimeError(m)
RUN_BODY
FILEPIN_BODY

def inputs():
 raw=(D/'QUERY-INPUTS.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,'exact query input binding')
 return json.loads(raw)

def parent_fact(path):
 fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  a=os.fstat(fd);children=os.listdir(fd);b=os.fstat(fd);c=os.lstat(path)
  fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_mtime_ns','st_ctime_ns')
  need(all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in fields),'stable prepared smoke parent')
  return dict(dev=a.st_dev,ino=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=stat.S_IMODE(a.st_mode),directory=stat.S_ISDIR(a.st_mode),children=children)
 finally:os.close(fd)

def validate(f,c,growth):
 need(f['uid']==f['euid']==0 and f['affinity']==[0],'root query CPU0')
 need(f['proc']['status']=='COMPLETE' and f['proc']['failure'] is None and f['proc']['publishers']==[] and len(f['proc']['snapshots'])==2,'complete publisher-free census')
 need(f['physical']['status']=='PASS_ACTUAL_PHYSICAL_RETIREMENT_ONLY' and f['physical']['nonce']=='efb4312b2dc644519320ccc24fa1219c' and f['physical']['absence_verified'] is True and f['physical']['lease_retained'] is False and f['physical']['root_mutex']==[27,4],'latest positive physical receipt')
 p=f['parent'];need(p['directory'] and p['uid']==p['gid']==1000 and p['mode']==0o700 and p['children']==[],'fresh private smoke parent exists empty UID1000 mode700')
 need(not any(f['output_paths_exist'].values()),'fresh capture owner and attempt paths absent')
 need(not any(f['ownership_paths_exist'].values()),'exact SDK image launcher ownership paths absent')
 need(f['lock']==[27,4,0,0,1] and f['locks']==[] and f['lock_acquired'] is True,'stable permanent mutex27:4 available')
 need(f['docker_running']=='' and all(v=='' for v in f['docker_identities'].values()),'no competing container or current nonce identity')
 need(f['server']['Version']=='26.1.3' and f['docker_info']['ServerVersion']=='26.1.3' and f['daemon_binding']['mode']=='none' and f['daemon_binding']['source_package']=='docker.io-app=26.1.3-0ubuntu1~20.04.1' and f['daemon_binding']['container_source_sha256']=='6ed6a9d2a3a32ecf6cbb91eaefdb5925c1316e8ea35e0856b7bb85530d143739','source-supported exact daemon NONE version')
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
 need(os.sched_getaffinity(0)=={0},'root query CPU0')
 source_pins=[]
 for row in c['pins']:
  fact=filepin(Path(row['path']),2**20);need(fact['sha256']==row['sha256'] and fact['size']==row['bytes'],'exact source/input pin');source_pins.append(fact)
 budget=json.loads(Path(c['budget']['path']).read_bytes());admission=budget['capacity_admission_proposal']
 physical=json.loads(Path(c['physical']['path']).read_bytes())
 growth_spec=importlib.util.spec_from_file_location('accepted_current110_growth',c['growth']['path']);growth=importlib.util.module_from_spec(growth_spec);growth_spec.loader.exec_module(growth)
 raw=ENGINE.read_bytes();need(hashlib.sha256(raw).hexdigest()==ENGINE_SHA,'accepted census source')
 code=next(ast.literal_eval(n.value) for n in ast.parse(raw).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets))
 start=Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
 proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'p12-tiny-none-current-live-admission-20261023-1',str(os.getpid()),start]))
 sd=Path(c['tiny']['existing_smoke']['path']).parent;parent=sd/'p'
 parent_info=parent_fact(parent)
 outputs={str(p):os.path.lexists(p) for p in [sd/'actual-capture-1',sd/('p.owner-'+c['tiny']['nonce']),parent/('attempt-'+c['tiny']['nonce'])]}
 # Exact lease/exclusion list inherited unchanged from accepted M05 query.
 leases=LEASE_PATHS
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
  for filt in ['id='+physical['container_id'],'name=^/mckernel-native-diagnostic-'+physical['nonce']+'$','label=mckernel.native-diagnostic.owner='+physical['nonce'],'name=^/mckernel-native-diagnostic-'+c['tiny']['nonce']+'$','label=mckernel.native-diagnostic.owner='+c['tiny']['nonce']]:
   identities[filt]=run(['/usr/bin/docker','ps','-aq','--no-trunc','--filter',filt])
  server=json.loads(run(['/usr/bin/docker','version','--format','{{json .Server}}']))
  info=json.loads(run(['/usr/bin/docker','info','--format','{{json .}}']))
  # NONE availability is bound to accepted exact source/version; no create/log request.
  transport_tree=ast.parse(Path(c['tiny']['runtime_files']['long_transport.py']['path']).read_bytes())
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
  required=validate(f,c,growth)
 finally:os.close(fd)
 return f,required

def main():
 need(len(sys.argv)==2 and filepin(Path(__file__).resolve(),65536)['sha256']==sys.argv[1],'exact query digest argv')
 c=inputs();f,required=collect(c)
 print(json.dumps(dict(scope=__doc__,status='PASS_FRESH_READ_ONLY_P12_TINY_NONE_ADMISSION',observations=f,required=required,at_unix=time.time(),mutation=False,transient_mutex_released=True,execution_release=False,native_acceptance=False),sort_keys=True))
if __name__=='__main__':main()
'''
lease=next(ast.literal_eval(n.value) for n in oldtree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='paths' for t in n.targets))
source=source.replace('CONFIG_DIGEST',repr(ref(D/'QUERY-INPUTS.json')['sha256'])).replace('RUN_BODY',run).replace('FILEPIN_BODY',filepin).replace('LEASE_PATHS',repr(lease))
(D/'read_only_p12_tiny_HOST_admission.py').write_text(source)
REPO.mkdir(parents=True,exist_ok=True)
for name in ['QUERY-INPUTS.json','accepted_m05_query.preimage.py','read_only_p12_tiny_HOST_admission.py']:(REPO/name).write_bytes((D/name).read_bytes())
print(json.dumps({'source':ref(D/'read_only_p12_tiny_HOST_admission.py'),'config':ref(D/'QUERY-INPUTS.json'),'budget':config['budget'],'physical':config['physical']},indent=2))
