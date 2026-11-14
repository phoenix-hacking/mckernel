"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact finite read-only admission capture; no compiler/build/guest/owner launch.
"""
import ast,hashlib,json,os,resource,time,signal
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
packet=D/'READONLY-ADMISSION-ARGV.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.json';raw=packet.read_bytes();assert hashlib.sha256(raw).hexdigest()=='3b1e48fee83945393154ea66f5e39528d56a11b3dcd5bfa579c68256c94ee986'
commands=json.loads(raw);commands=commands['read_only_admission_commands']+[commands['namespace_observation']]
assert len(commands)==5 and commands[3]['argv']==['/usr/bin/sudo','-A','/usr/sbin/losetup','--list','--json','--associated','/home/holden/mckernel-work/scratch.ext4']
assert all('sudo' not in ' '.join(c['argv']) for i,c in enumerate(commands) if i!=3)
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}
cap=D/'actual-readonly-admission-capture-1';cap.mkdir(mode=0o700)
ns['write'](cap/'SOURCE-ARGV-BINDING.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','helper_sha256':'990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','packet_sha256':'3b1e48fee83945393154ea66f5e39528d56a11b3dcd5bfa579c68256c94ee986','runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'commands':commands})
started_epoch=time.time();begin=time.monotonic();initial_cpu=ns['cpu_used']();results=[]
for i,command in enumerate(commands,1):
 remaining_wall=60-(time.monotonic()-begin);remaining_cpu=30-(ns['cpu_used']()-initial_cpu)
 assert remaining_wall>0 and remaining_cpu>0
 child_cpu=max(1,int(remaining_cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 path=cap/str(i);path.mkdir(mode=0o700);ns['write'](path/'command.json',command)
 result=ns['owned_capture'](command,path,remaining_wall,limits);ns['write'](path/'receipt.json',result);results.append(result)
 assert ns['cpu_used']()-initial_cpu<=30 and time.monotonic()-begin<=60
 ns['need'](result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,'stop first failed read-only command: '+repr(result))
assert ns['cpu_used']()-initial_cpu<=30 and time.monotonic()-begin<=60
ns['write'](cap/'ACTUAL-READONLY-RESULT.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','results':results,'started_at_epoch':started_epoch,'finished_at_epoch':time.time(),'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used']()-initial_cpu,'admission_or_build_acceptance':None})
print(json.dumps({'capture':str(cap),'commands':len(results),'seconds':time.monotonic()-begin},sort_keys=True))
