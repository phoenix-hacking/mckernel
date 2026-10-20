import os,json,time,hashlib,resource,subprocess
from pathlib import Path
B=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-two-rounds-20261019-1/stage-preparation-1/native-packet-1')
I=B/'FINAL-SEVEN-ROOT-CALL-DATA.json'
assert hashlib.sha256(I.read_bytes()).hexdigest()=='7d8ff31b86fe65aea157aedcf97bf12434cb2c165e366070deee319bf14b9448'
x=json.loads(I.read_bytes());assert len(x['steps'])==7
R=B/'ROOT-SEVEN-REVIEW-REF-1.json';review=json.loads(R.read_bytes());rbytes=Path(review['path']).read_bytes();assert hashlib.sha256(rbytes).hexdigest()==review['sha256']
assert resource.getrlimit(resource.RLIMIT_AS)==(-1,-1) and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1)
assert os.geteuid()==1000 and os.environ.get('SUDO_ASKPASS')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and not state.get('pause_reason') and state['last_rate_limits']['primary']['usedPercent']<97
storage={}
for label,p,floor in [('host','/home/holden/mckernel',17179869184),('scratch','/home/holden/mckernel-work/scratch',12884901888)]:
 v=os.statvfs(p);free=v.f_bavail*v.f_frsize;assert free>=floor+671088640;storage[label]=free
mem=int(next(z.split()[1] for z in Path('/proc/meminfo').read_text().splitlines() if z.startswith('MemAvailable:')))*1024;assert mem>=17850957824
for parent in x['capture_parents']:
 st=Path(parent['path']).stat();assert (st.st_dev,st.st_ino,st.st_uid,st.st_gid,st.st_mode&4095)==(parent['device'],parent['inode'],parent['uid'],parent['gid'],int(parent['mode'],8) if isinstance(parent['mode'],str) else parent['mode'])
for p in x['fresh_capture_and_actual_command_paths']:assert not os.path.lexists(p),p
prepared=[]
for row in x['steps']:
 ref=row['template'];raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];d=json.loads(raw);assert d['operations'][1]['argv_template']==row['argv_template'];prepared.append(d)
(B/'root-seven-admission-1.json').open('x').write(json.dumps({'timestamp':time.time(),'storage':storage,'mem_available':mem,'usage_percent':state['last_rate_limits']['primary']['usedPercent'],'scope':'Exact reviewed7row chain; sole heavy slot/current native physical12002 predecessor; actual snapshot and guard preserve full live predicates.'},indent=2)+'\n')
late={};rows=[];failure=None;started=time.time()
for row,d in zip(x['steps'],prepared):
 name=row['name'];op=d['operations'][1];argv=list(row['argv_template'])
 if name=='machine-assembly':argv[-1]=late['snapshot']
 if name=='final-guard':
  argv[argv.index('--machine-sha256')+1]=late['machine'];argv[argv.index('--snapshot-sha256')+1]=late['snapshot']
 if name=='native-owner':
  assert late['guard']['allowed_argv']==argv and time.time()<late['guard']['expires_at_epoch']
 op['argv_template']=argv;data=(json.dumps(d,sort_keys=True,indent=2)+'\n').encode();p=Path(row['materialized_command_data']);p.open('xb').write(data)
 invoke=list(row['caller_argv_template']);invoke[invoke.index('--commands-sha256')+1]=hashlib.sha256(data).hexdigest()
 if name!='native-owner':invoke=['/usr/bin/prlimit','--as=1073741824','--cpu=30','--']+invoke
 output=B/('root-seven1-'+name+'.stdout');error=B/('root-seven1-'+name+'.stderr');status=B/('root-seven1-'+name+'.status.json');child=B/('root-seven1-'+name+'.child.json')
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
 inner=json.loads(Path(row['status']).read_bytes());assert inner['returncode']==0 and inner['direct_child_joined'] and inner['process_group_absent'] and not inner.get('observer_error')
 if name=='LAST-snapshot':
  produced=json.loads(Path(row['stdout']).read_bytes());assert produced['path']==x['snapshot_output'];late['snapshot']=produced['sha256'];assert hashlib.sha256(Path(produced['path']).read_bytes()).hexdigest()==late['snapshot']
 if name=='machine-assembly':
  result=json.loads(Path(row['stdout']).read_bytes());late['machine']=result['sha256'];assert hashlib.sha256(Path(x['final_machine_output']).read_bytes()).hexdigest()==late['machine']
 if name=='final-guard':
  result=json.loads(Path(row['stdout']).read_bytes());raw=Path(result['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==result['sha256'];actual_guard=json.loads(raw);assert actual_guard['status']==result['status'] and actual_guard['runtime_release'] is True and actual_guard['execution_count']==1 and actual_guard['allowed_argv']==result['allowed_argv'] and actual_guard['expires_at_epoch']==result['expires_at_epoch'];late['guard']=result;assert result['allowed_argv']==x['native_allowed_argv'];assert time.time()<result['expires_at_epoch']
final={'status':'PASS_WHOLE_JOINED_RELEASED_CHAIN' if failure is None else 'FAIL_STOPPED','failed_stage':failure,'rows':rows,'started_at':started,'finished_at':time.time()};(B/'root-seven-whole-1.json').open('x').write(json.dumps(final,indent=2)+'\n');print(json.dumps(final));raise SystemExit(0 if failure is None else 1)
