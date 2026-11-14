from pathlib import Path
import json,os,resource,signal,sys,time,types,hashlib
Q=Path(__file__).resolve().parent
OUT=Q/'actual-check-3';assert OUT.is_dir()
def write(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def ref(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
os.sched_setaffinity(0,{7});assert os.sched_getaffinity(0)=={7}
free={}
for name,path,floor in [('host','/home/holden/mckernel',16<<30),('scratch','/home/holden/mckernel-work/scratch',12<<30)]:
 st=os.statvfs(path);available=st.f_bavail*st.f_frsize;assert available>=floor+679477248+(64<<20);free[name]=available
# UUID observed by the fixed read-only findmnt command before the unit.
write(OUT/'CONTINUATION-GRANT-AND-FLOORS.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','cpu':7,'AS':1<<30,'CPU_seconds':30,'wall_seconds':35,'FSIZE':64<<20,'NOFILE':256,'CORE':0,'free':free,'scratch_uuid':'2a5768c8-718d-4914-bdc0-6b32c5a92a52','time_ns':time.time_ns()})
hp=Path('/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/guest-control-consumer-1/current-fullcrate-owner-1/owned_capture_helpers.py');assert ref(hp)['sha256']=='7834a85da04a3667b86365ec6340a55580b560248dd23fec84e673acc31bea90'
h=types.ModuleType('accepted_owned_capture');h.__file__=str(hp);exec(compile(hp.read_bytes(),str(hp),'exec'),h.__dict__)
h.CENSUS_SOURCE=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py');assert ref(h.CENSUS_SOURCE)['sha256']==h.CENSUS_SHA
for sig in h.STOP_SIGNALS:signal.signal(sig,h.stop)
commands=[]
def capture(name,argv):
 path=OUT/name;path.mkdir(mode=0o700);command={'argv':argv,'cwd':str(Q)};write(path/'command.json',command)
 def limits():
  os.sched_setaffinity(0,{7})
  for key,value in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
 result=h.owned_capture(command,path,35,limits,started_reader=h.process_start);write(path/'owned-result.json',result);commands.append({'name':name,'result':ref(path/'owned-result.json')})
 assert result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['unexpected_group_members'],result
 assert result['returncode']==0,(name,result)
 return result
logs=OUT/'logs';assert logs.is_dir();os.environ['M05_OBSERVATION_OUTPUT']=str(logs)
capture('body-run',[str(OUT/'body'),'--test-threads=1'])
capture('decoder',['/home/holden/anaconda3/bin/python3','-B',str(Q/'test_decoder.py'),str(logs)])
write(OUT/'RESULT.json',{'status':'PASS_PRIVATE_ACTUAL_RUST_SHUTDOWN_OBSERVATION_AND_DECODER_ONLY','compile_result':ref(OUT/'compile/owned-result.json'),'commands':commands,'native_runs':0,'SDK_builds':0,'production_integration':False,'public_ABI_changes':0})
print(json.dumps({'status':'PASS_PRIVATE_ACTUAL_RUST_SHUTDOWN_OBSERVATION_AND_DECODER_ONLY','commands':len(commands),'evidence':str(OUT)}))
