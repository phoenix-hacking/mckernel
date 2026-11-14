import os,json,time,hashlib,resource,subprocess
from pathlib import Path
B=Path(__file__).parent
I=B/'NATIVE-MACHINE-AND-CAPTURE-INDEX.json'
def digest(b):return hashlib.sha256(b).hexdigest()
assert digest(I.read_bytes())=='826c68e8495c376b6a0e691e4ef1bf53ae6aba68184e0dc5858fe46934e936c3'
x=json.loads(I.read_bytes());assert len(x['ordered_capture_steps'])==7
r=json.loads((B/'ROOT-SEVEN-REVIEW-REF.json').read_bytes());rb=Path(r['path']).read_bytes();assert digest(rb)==r['sha256']
assert resource.getrlimit(resource.RLIMIT_AS)==(-1,-1) and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1)
assert os.geteuid()==1000 and os.environ.get('SUDO_ASKPASS')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and not state.get('pause_reason') and state.get('stop_reason') is None and state['last_rate_limits']['primary']['usedPercent']<97
storage={}
for label,p,floor in [('host','/home/holden/mckernel',17179869184),('scratch','/home/holden/mckernel-work/scratch',12884901888)]:
 v=os.statvfs(p);free=v.f_bavail*v.f_frsize;assert free>=floor+671088640;storage[label]=free
mem=int(next(z.split()[1] for z in Path('/proc/meminfo').read_text().splitlines() if z.startswith('MemAvailable:')))*1024;assert mem>=17850957824
for p in x['all_21_fresh_capture_paths']:
 assert not os.path.lexists(p),p
 parent=Path(p).parent;st=parent.stat();assert parent.resolve()==parent and st.st_uid==1000 and st.st_gid==1000 and st.st_mode&4095==448
prepared=[]
for row in x['ordered_capture_steps']:
 ref=row['commands'];raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and digest(raw)==ref['sha256'];d=json.loads(raw);assert len(d['operations'])>1;prepared.append(d)
for ref in [x['native_parent_capture_source'],x['final_guard_source'],x['snapshot_bindings'],x['machinebase'],x['conditional_metadata']]:
 raw=Path(ref['path']).read_bytes();assert digest(raw)==ref['sha256'] and len(raw)==ref['bytes']
cfgref=x['final_guard_config'];cfgraw=Path(cfgref['path']).read_bytes();assert digest(cfgraw)==cfgref['sha256'] and len(cfgraw)==cfgref['bytes']
source_refs=[r for r in json.loads(cfgraw)['runtime_source_refs'] if 'root_manual_snapshot' in r['path']];assert len(source_refs)==3
for ref in source_refs:
 raw=Path(ref['path']).read_bytes();assert digest(raw)==ref['sha256'] and len(raw)==ref['bytes']
(B/'root-seven-admission.json').open('x').write(json.dumps({'timestamp':time.time(),'storage':storage,'mem_available':mem,'usage_percent':state['last_rate_limits']['primary']['usedPercent'],'latest_physical':x['capture_context_only']},indent=2)+'\n')
late={};rows=[];failure=None;started=time.time()
for row,d in zip(x['ordered_capture_steps'],prepared):
 name=row['name'];op=d['operations'][1];argv=list(op['argv_template'])
 if name=='final-guard':
  argv=[late['machine'] if a=='ACTUAL_MACHINE_SHA256' else late['snapshot'] if a=='ACTUAL_SNAPSHOT_SHA256' else a for a in argv]
 if name=='native-owner':assert late['guard']['allowed_argv']==argv and time.time()<late['guard']['expires_at_epoch']
 op['argv_template']=argv;data=(json.dumps(d,sort_keys=True,indent=2)+'\n').encode();p=B/('root-materialized-'+name+'.json');p.open('xb').write(data)
 invoke=list(row['invoke']);invoke[invoke.index('--commands-file')+1]=str(p);invoke[invoke.index('--commands-sha256')+1]=digest(data)
 if name!='native-owner':invoke=['/usr/bin/prlimit','--as=1073741824','--cpu=30','--']+invoke
 output=B/('root-'+name+'.stdout');error=B/('root-'+name+'.stderr');status=B/('root-'+name+'.status.json');child=B/('root-'+name+'.child.json')
 begin=time.monotonic();ts=time.time();c=None;pid=None;start=None;exc=None;rc=None
 try:
  with output.open('xb') as out,error.open('xb') as err:
   c=subprocess.Popen(invoke,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);pid=c.pid
   stat=Path('/proc/%d/stat'%pid).read_text();start=int(stat[stat.rfind(')')+2:].split()[19]);child.open('x').write(json.dumps({'pid':pid,'start':start,'argv':invoke,'timestamp':ts})+'\n');rc=c.wait()
 except BaseException as e:
  exc=repr(e)
  if c is not None:rc=c.wait()
 absent=False
 if pid is not None:
  try:os.killpg(pid,0)
  except ProcessLookupError:absent=True
 record={'returncode':rc,'pid':pid,'start':start,'direct_child_joined':c is not None and c.returncode is not None,'process_group_absent':absent,'observer_error':exc,'elapsed_seconds':time.monotonic()-begin,'started_at':ts,'finished_at':time.time(),'argv':invoke};status.open('x').write(json.dumps(record,indent=2)+'\n');rows.append({'name':name,'status_path':str(status),'returncode':rc,'elapsed_seconds':record['elapsed_seconds']})
 if rc!=0 or not absent or exc:failure=name;break
 inner=json.loads(Path(op['status_path']).read_bytes());assert inner['returncode']==0 and inner['direct_child_joined'] and inner['process_group_absent'] and not inner.get('observer_error')
 if name=='root-snapshot':
  produced=json.loads(Path(op['stdout_path']).read_bytes());late['snapshot']=produced['sha256'];assert digest(Path(produced['path']).read_bytes())==late['snapshot'];late['snapshot_path']=produced['path']
 if name=='assemble-machine':
  produced=json.loads(Path(op['stdout_path']).read_bytes());late['machine']=produced['sha256'];assert produced['path']==x['final_machine_path'] and produced['snapshot_sha256']==late['snapshot'] and digest(Path(produced['path']).read_bytes())==late['machine']
 if name=='final-guard':
  result=json.loads(Path(op['stdout_path']).read_bytes());raw=Path(result['path']).read_bytes();assert digest(raw)==result['sha256'];guard=json.loads(raw);assert guard['status']==result['status'] and guard['runtime_release'] is True and guard['execution_count']==1 and guard['allowed_argv']==result['allowed_argv'] and guard['expires_at_epoch']==result['expires_at_epoch'];late['guard']=result;assert result['allowed_argv']==x['allowed_owner_argv'];assert time.time()<result['expires_at_epoch']
final={'status':'PASS_WHOLE_JOINED_RELEASED_CHAIN' if failure is None else 'FAIL_STOPPED','failed_stage':failure,'rows':rows,'started_at':started,'finished_at':time.time()};(B/'root-seven-whole.json').open('x').write(json.dumps(final,indent=2)+'\n');print(json.dumps(final));raise SystemExit(0 if failure is None else 1)
