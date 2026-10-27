"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UID1000 exact reviewed SDK owner through existing990 capture; no query FD inheritance.
"""
from pathlib import Path
import json,hashlib,types,resource,os,time,importlib.util,subprocess
A=Path(__file__).resolve().parent;E=A.parent
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
assert subprocess.check_output(['git','-C','/home/holden/mckernel','rev-parse','HEAD'],text=True).strip()==json.loads((A/'SDK-HEAD-BINDING.json').read_bytes())['commit']
policy=E/'scratch-growth-final-copy-close-source-1/recover_growth_custody.py';assert hashlib.sha256(policy.read_bytes()).hexdigest()=='04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a'
spec=importlib.util.spec_from_file_location('actual_account_guard',policy);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);g.check_account_state(json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes()),time.time())
live=json.loads((A/'LIVE-CURRENT.json').read_bytes());now=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)];assert all(0<=n-live['clock'][k]<120 for n,k in zip(now,['wall','monotonic','boot']));assert all(n<e for n,e in zip(now,g.CUTOFFS))
closed=json.loads((A/'QUERY-HOLDER.NORMAL-CLOSE.json').read_bytes());assert closed['fd_closed'] is True and closed['lock_un_called'] is False;assert not Path('/proc/'+str(closed['holder']['pid'])).exists()
assert not [r for r in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in r.split()]
base=json.loads((A/'PREQUERY-BUNDLE.json').read_bytes());reqref=base['request'];req=json.loads(Path(reqref['path']).read_bytes());release=A/'ACTUAL-REVIEWED-RELEASE.json';raw=release.read_bytes();rel=json.loads(raw);assert rel['execution_release'] is True and rel['nonce']==req['nonce'] and rel['request']=={k:reqref[k] for k in ['path','sha256']}
owner=E/'sdk7-142g-consumer-successor-source-1/daemon_sdk_owner.142G-SOURCE-ONLY.py';assert hashlib.sha256(owner.read_bytes()).hexdigest()=='999713a7b4dafa034232d997872132642358aa80029244ad27e571efbf1664ee'
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(owner),'--request',reqref['path'],'--request-sha256',reqref['sha256'],'--release',str(release),'--release-sha256',hashlib.sha256(raw).hexdigest()]
source=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
m=types.ModuleType('owned_sdk_capture');m.__file__=str(source);exec(compile(raw,str(source),'exec'),m.__dict__);P=A/'SDK-CAPTURE';P.mkdir(mode=0o700)
def limits():
 os.sched_setaffinity(0,{2,3,4,5});resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864))
command=dict(argv=argv,scope=__doc__.splitlines()[0]);(A/'SDK-COMMAND.EXACT.json').write_text(json.dumps(command,indent=2)+'\n');start=time.time();result=m.owned_capture(command,P,min(req['timeout']+120,int(g.CUTOFFS[0]-time.time()-300)),limits);result['started_wall']=start;result['finished_wall']=time.time();result['capture_helper_sha256']='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
with (A/'SDK-WHOLE-JOIN.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['pid','returncode','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out','seconds']}),flush=True)
