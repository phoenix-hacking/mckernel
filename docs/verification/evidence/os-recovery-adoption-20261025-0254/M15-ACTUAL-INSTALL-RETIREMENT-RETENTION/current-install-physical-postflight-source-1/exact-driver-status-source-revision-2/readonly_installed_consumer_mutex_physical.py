"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact installed-consumer read-only physical postflight; no cleanup or workload.
"""
from pathlib import Path
import hashlib,json,os,fcntl,types
MANIFEST={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/binder-successor-source-1/actual-copy7-late-bound-1/current-install-physical-postflight-source-1/EXACT-INSTALLED-CONSUMER-POSTFLIGHT.INPUTS.json', 'bytes': 56340, 'sha256': '938254ab695590e6ec5e18f7ff5b471c405e6b10ba2c1413ebc6bce016112d0f'}
raw=Path(MANIFEST['path']).read_bytes();assert len(raw)==MANIFEST['bytes'] and hashlib.sha256(raw).hexdigest()==MANIFEST['sha256']
x=json.loads(raw)
def need(v,m):
 if not v:raise RuntimeError(m)
need(os.getuid()==os.geteuid()==0,'authenticated root postflight')
source=Path(x['cleanup_source']['path']).read_bytes();need(hashlib.sha256(source).hexdigest()==x['cleanup_source']['sha256'],'retained read-only engine')
m=types.ModuleType('_m15_install_readonly');m.__file__=x['cleanup_source']['path'];exec(compile(source,m.__file__,'exec'),m.__dict__)
for ref in x['refs']:
 row=m.observe_identity(Path(ref['path']));need(row['size']==ref['bytes'] and row['sha256']==ref['sha256'],'exact retained input:'+ref['path'])
v=json.loads(m.read_bounded(Path(x['receipt']['path'])));driver=json.loads(m.read_bounded(Path(x['driver_receipt']['path'])))
need(v['status']==v['build_status']=='PASS' and v['retired'] is True and v['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE','actual successful normal owner')
need(v['terminal_container_retained'] is False and v['cleanup_separately_required'] is False,'default normal removal; no separate cleanup')
need(v['container_id']==x['container_id'] and v['container_name']==x['container_name'] and v['owner_nonce']==x['nonce'],'exact installed container')
need(v['driver_receipt']==driver and driver['status']=='PASS_SELECTED_SDK_FOUR_INSTALL_THREE_LOADER_ONLY' and len(driver['commands'])==4 and driver['loader_checks']==3 and driver['CLI_executed'] is False,'actual four install/loader command results')
need(v['client_count']==14 and v['postflight']['all_clients_reaped'] is True and v['postflight']['container_absent'] is True,'actual14normalclients and removal')
for name in ('shared_record','common_record','operation_lease'):
 need(v[name]['pid']==x['owner_pid'] and v[name]['starttime']==x['owner_starttime'],'exact owned record birth:'+name)
for group in v['client_group_checks']+v['admission_client_group_checks']:
 need(group['empty'] is True and group['surviving_members']==[] and 'error' not in group,'retained normal client groups closed')
for role,count,key in [('owner',14,'client_group_checks'),('admission',1,'admission_client_group_checks')]:
 wanted={(c['status']['path'],c['pid']) for c in x['clients'] if c['role']==role}
 got={(g['status_path'],g['pid']) for g in v[key]};need(got==wanted and len(got)==count,'exact closed client status set')
 for g in wanted:
  status=json.loads(m.read_bounded(Path(g[0])));need(status['state']=='exited' and status['exit_code']==0 and status['pid']==g[1],'exact client terminal status')
for row in driver['commands']:
 z=row['result'];need(z['returncode']==0 and z['direct_child_joined'] and z['group_absent'] and z['closed_streams'] and z['error'] is None and z['retirement_error'] is None and z['timed_out'] is False and z['remaining_group_members']==z['unexpected_group_members']==[] and type(z['start']) is int and z['start']>0,'actual four inner command births/joins')
 for ref in z['captures'].values():
  q=Path(x['request']['candidate_root'])/'output'/str(Path(ref['path']).relative_to('/work/output'))
  got=m.observe_identity(q);need(got['size']==ref['size'] and got['sha256']==ref['sha256'],'actual inner command capture bytes')
m.RELEASE=json.loads(m.read_bounded(Path(x['prior_mount_release']['path'])));m.BOOT_ID=x['request']['boot_id'];m.OWNER_PID=x['owner_pid'];m.OWNER_START=x['owner_starttime'];m.WAITER_PIDS=tuple(c['pid'] for c in x['clients'])
m.CONTAINER=x['container_id'];m.CONTAINER_NAME=x['container_name'];m.OWNER_NONCE=x['nonce']
need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m.BOOT_ID,'actual current boot')
lock=m.observe_identity(m.ROOT_LOCK);need((lock['device'],lock['inode'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'],lock['size'])==(27,4,0,0,'0o644',1,0),'permanent27:4mutex')
key=f"{os.major(lock['device']):02x}:{os.minor(lock['device']):02x}:{lock['inode']}";need(not [l for l in Path('/proc/locks').read_text().splitlines() if key in l.split()],'root mutex free before read')
fd=os.open(m.ROOT_LOCK,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
try:
 need((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(27,4),'held27:4FD');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 m.validate_mount()
 paths=set(x['generic_absence_paths'])|{x['request']['common_exclusion_path'],x['request']['lease_path'],'/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'}
 for path in paths:need(not os.path.lexists(path),'owned/exclusion path present:'+path)
 need(not m.census(),'installed CID/name/nonce still present')
 files=[]
 for container_path,ref in driver['artifacts'].items():
  q=Path(x['request']['candidate_root'])/'output'/str(Path(container_path).relative_to('/work/output'))
  row=m.observe_identity(q)
  need(all(row[k]==ref[k] for k in ('device','inode','uid','gid','mode','size','nlink','sha256')),'installed artifact identity/hash drift')
  files.append(row)
 need(len(files)==4,'four installed artifacts')
 # Preserve exact terminal ownership archive/release and every closed client record.
 for ref in x['refs']:
  row=m.observe_identity(Path(ref['path']));need(row['size']==ref['bytes'] and row['sha256']==ref['sha256'],'retained evidence postflight')
 for path in paths:need(not os.path.lexists(path),'post-observation ownership path present:'+path)
 need(m.observe_identity(m.ROOT_LOCK)==lock,'root mutex unchanged')
 print(json.dumps(dict(scope=__doc__,status='PASS_M15_INSTALLED_CONSUMER_MUTEX_HELD_CURRENT_PHYSICAL',manifest=MANIFEST,owner=dict(pid=x['owner_pid'],starttime=x['owner_starttime']),container_absent=dict(id=x['container_id'],name=x['container_name'],nonce=x['nonce']),root_lock=lock,absence_paths=sorted(paths),owner_clients=14,admission_clients=1,client_births=None,installed_artifacts=files,inner_command_births=[dict(pid=r['result']['pid'],start=r['result']['start']) for r in driver['commands']],proc=m.PROCESS_REPORTS[-1],artifact_native_acceptance=False),sort_keys=True))
finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
