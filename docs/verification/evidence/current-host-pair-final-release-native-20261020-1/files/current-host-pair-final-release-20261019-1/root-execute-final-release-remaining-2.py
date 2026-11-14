import os,json,time,hashlib,resource,subprocess
from pathlib import Path
Q=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-final-release-20261019-1')
I=Q/'NATIVE-MACHINE-AND-CAPTURE-INDEX.json'
assert hashlib.sha256(I.read_bytes()).hexdigest()=='91edb9bcb8056d8b36ed1306622fb2853c9e5b185089818df7fc46ee75e75956'
D=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-final-release-independent-review-20261019-1/EXACT-EIGHT-STAGE-FINAL-RELEASE-CAPTURE-REVIEW.json')
assert hashlib.sha256(D.read_bytes()).hexdigest()=='581d67ead4fd4f84715d5b35e6f4e9eace1ce458343656b607831f568d9a19f1'
x=json.loads(I.read_text()); rows=x['ordered_capture_steps']; assert len(rows)==8
assert resource.getrlimit(resource.RLIMIT_AS)==(-1,-1) and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1)
assert os.geteuid()==1000 and os.environ.get('SUDO_ASKPASS')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
assert state['phase']=='running' and not state.get('pause_reason') and state['last_rate_limits']['primary']['usedPercent']<97
storage={}
for name,p,floor in [('host','/home/holden/mckernel',17179869184),('scratch','/home/holden/mckernel-work/scratch',12884901888)]:
 v=os.statvfs(p); n=v.f_bavail*v.f_frsize; assert n>=floor+671088640;storage[name]=n
mem=dict(s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines());assert int(mem['MemAvailable'].split()[0])*1024>=17179869184
for key in ['proposal','conditional_metadata','machinebase','snapshot_adapter_bindings','snapshot_projection','snapshot_data_packet','final_guard_source','final_guard_config','preclock_review','native_parent_capture_source']:
 r=x[key]
 if isinstance(r,dict) and 'path' in r and 'sha256' in r:
  b=Path(r['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'],key
commands=[]
for row in rows:
 r=row['commands'];b=Path(r['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256']; d=json.loads(b);o=d['operations'][1]
 if row['name']=='final-guard':
  for key in ['stdout_path','stderr_path','status_path']:d['operations'][1][key]=d['operations'][1][key]+'.retry2'
 if row['name'] in ['root-snapshot','assemble-machine']:
  commands.append(d);continue
 for k in ['stdout_path','stderr_path','status_path']:
  p=Path(o[k]);assert p.parent.is_dir() and not p.exists(),str(p)
 commands.append(d)
(Q/'root-native-admission-2.json').write_text(json.dumps({'status':'PASS_FRESH_COORDINATOR_ADMISSION','timestamp':time.time(),'storage':storage,'usage_percent':state['last_rate_limits']['primary']['usedPercent'],'controller_as_cpu':'unlimited','metadata_outer_as_cpu':[1073741824,30],'latest_physical':'7d869a4f69a7d840a14bd18b4638f0a5043354ac246a1d5c57adf9e23f75001c','scope':'Reviewed lifecycle native chain; snapshot engine and exact guard retain every live admission/ownership check.'},indent=2)+'\n')
previous=json.loads((Q/'assemble-machine.stdout').read_text());late={'ACTUAL_FINAL_MACHINE_SHA256':previous['sha256'],'ACTUAL_MACHINE_SHA256':previous['sha256'],'ACTUAL_SNAPSHOT_SHA256':previous['snapshot_sha256']}; results=[]; started=time.time(); failed=None
for row,original in zip(rows[2:],commands[2:]):
 name=row['name'];d=json.loads(json.dumps(original));op=d['operations'][1]; argv=op['argv_template']; actual=[late.get(a,a) for a in argv]
 invoke=list(row['invoke'])
 if actual!=argv:
  op['argv_template']=actual;b=(json.dumps(d,sort_keys=True,indent=2)+'\n').encode();p=Q/('root-retry2-'+name+'-bound-DATA.json');p.open('xb').write(b)
  invoke[invoke.index('--commands-file')+1]=str(p);invoke[invoke.index('--commands-sha256')+1]=hashlib.sha256(b).hexdigest()
 if name!='native-owner':invoke=['/usr/bin/prlimit','--as=1073741824','--cpu=30','--']+invoke
 stdout=Q/('root-lifecycle-retry2-'+name+'.stdout');stderr=Q/('root-lifecycle-retry2-'+name+'.stderr');status=Q/('root-lifecycle-retry2-'+name+'.status.json');child=Q/('root-lifecycle-retry2-'+name+'.child.json')
 ts=time.time(); begin=time.monotonic();err=None;pid=None;start=None;p=None
 try:
  with stdout.open('xb') as out,stderr.open('xb') as e:
   p=subprocess.Popen(invoke,stdout=out,stderr=e,start_new_session=True);pid=p.pid
   raw=Path('/proc/%d/stat'%pid).read_text();start=int(raw[raw.rfind(')')+2:].split()[19]);child.open('x').write(json.dumps({'pid':pid,'start':start,'argv':invoke,'timestamp':ts})+'\n')
   rc=p.wait()
 except BaseException as e:
  err=type(e).__name__+': '+str(e)
  if p is not None:rc=p.wait()
  else:rc=None
 absent=False
 if pid is not None:
  try:os.killpg(pid,0)
  except ProcessLookupError:absent=True
 record={'returncode':rc,'pid':pid,'start':start,'direct_child_joined':p is not None and p.returncode is not None,'process_group_absent':absent,'observer_error':err,'elapsed_seconds':time.monotonic()-begin,'started_at':ts,'finished_at':time.time(),'argv':invoke}
 status.open('x').write(json.dumps(record,sort_keys=True,indent=2)+'\n');results.append({'name':name,'status_path':str(status),'returncode':rc,'elapsed_seconds':record['elapsed_seconds']})
 if rc!=0 or not absent or err:failed=name;break
 inner=json.loads(Path(op['status_path']).read_text())
 if inner['returncode']!=0 or not inner['direct_child_joined'] or not inner['process_group_absent'] or inner.get('observer_error'):failed=name;break
 if name=='assemble-machine':
  a=json.loads(Path(op['stdout_path']).read_text());late['ACTUAL_FINAL_MACHINE_SHA256']=a['sha256'];late['ACTUAL_SNAPSHOT_SHA256']=a['snapshot_sha256']
  raw=Path(a['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['sha256'];m=json.loads(raw);snapshot_ref=m['fresh_live_preflight'];assert snapshot_ref['sha256']==a['snapshot_sha256'];assert hashlib.sha256(Path(snapshot_ref['path']).read_bytes()).hexdigest()==a['snapshot_sha256']
 if name=='final-guard':
  g=json.loads(Path(op['stdout_path']).read_text());gb=Path(g['path']).read_bytes();assert hashlib.sha256(gb).hexdigest()==g['sha256'];gr=json.loads(gb);assert g['status']==gr['status'] and gr['runtime_release'] is True and gr['execution_count']==1;assert g['allowed_argv']==commands[3]['operations'][1]['argv_template'];assert time.time()<g['expires_at_epoch']
 if name=='readback-3':late['ACTUAL_CLOSED_READBACK3_SHA256']=inner['streams']['stdout']['sha256']
final={'status':'PASS_WHOLE_JOINED_RELEASED_CHAIN' if failed is None else 'FAIL_STOPPED','started_at':started,'finished_at':time.time(),'failed_stage':failed,'rows':results,'scope':x['scope']}
(Q/'root-native-pipeline-2.json').open('x').write(json.dumps(final,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':final['status'],'failed_stage':failed,'rows':results},sort_keys=True))
raise SystemExit(0 if failed is None else 1)
