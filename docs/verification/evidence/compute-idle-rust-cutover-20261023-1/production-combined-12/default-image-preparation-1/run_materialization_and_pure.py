"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One authorized ordinary candidate12 source materialization. No compiler/root/build.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
cap=D/'materialization-and-pure-capture-1';cap.mkdir(mode=0o700)
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+268435456+16777216,scratch_required=13631488000,MemAvailable=mem,root_reserved_memory=19*1073741824)
ns['write'](cap/'ACTUAL-PRE-CAPACITY.json',facts);assert facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'] and mem>=19*1073741824,facts
materializer=D/'materialize_source.py';validator=D/'next-build-preparation-1/prepare_and_validate.py'
assert hashlib.sha256(materializer.read_bytes()).hexdigest()=='31f4f8e99eb09386b78dba93e981d1742011b04c39566032f0db9d03bcc7fff6'
assert hashlib.sha256(validator.read_bytes()).hexdigest()=='94c7f8962b5a0a002a39b98a1fe8a7f5ef98e56d6a7f1c43209ab329f5ac1ece'
commands=[{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact candidate12 source materialization only.','argv':['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(materializer)]},{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact candidate12 namespace/request derivation and one complete pure validator; never run/acquire.','argv':['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(validator)]}]
ns['write'](cap/'commands.json',{'commands':commands,'materializer_sha256':'31f4f8e99eb09386b78dba93e981d1742011b04c39566032f0db9d03bcc7fff6','validator_sha256':'94c7f8962b5a0a002a39b98a1fe8a7f5ef98e56d6a7f1c43209ab329f5ac1ece'})
(D/'source-materialization-attempt-1').mkdir(mode=0o700)
execution_start_ns=time.time_ns();begin=time.monotonic();initial=ns['cpu_used']();results=[]
for i,command in enumerate(commands,1):
 remaining_wall=120-(time.monotonic()-begin);remaining_cpu=60-(ns['cpu_used']()-initial);assert remaining_wall>0 and remaining_cpu>0
 child_cpu=max(1,int(remaining_cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 path=cap/str(i);path.mkdir(mode=0o700);ns['write'](path/'command.json',command)
 result=ns['owned_capture'](command,path,remaining_wall,limits);ns['write'](path/'whole-join.json',result);results.append(result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 if i==1:
  material=json.loads((D/'source-materialization-attempt-1/MATERIALIZATION-RESULT.json').read_text());assert material['source_manifest_canonical_sha256']=='8b2b3f20ccf8da69bbb64deedc7b222e23d00a1c83708486810a430d2fe9b692'
whole=dict(scope=__doc__,execution_start_ns=execution_start_ns,execution_end_ns=time.time_ns(),results=results,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used']()-initial,compiler_build_native=None)
ns['write'](cap/'ACTUAL-WHOLE-JOIN.json',whole);print(json.dumps(whole,sort_keys=True))
