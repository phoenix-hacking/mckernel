"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One authorized ordinary candidate6 source materialization. No compiler/root/build.
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
materializer=D/'materialize_source.py';assert hashlib.sha256(materializer.read_bytes()).hexdigest()=='9d5875313b1c5ab0d036631183bf7d2886ce6549e7c243b7667de55d852125d3'
cap=D/'materialization-capture-1';cap.mkdir(mode=0o700)
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
needhost=17179869184+gap+16106090496+377487360+679477248+268435456+16777216;needscratch=12884901888+67108864+679477248
facts={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','HOST_available':host.f_bavail*host.f_frsize,'scratch_available':scratch.f_bavail*scratch.f_frsize,'backing_size':back.st_size,'backing_blocks':back.st_blocks,'backing_dev':back.st_dev,'backing_inode':back.st_ino,'full_sparse_gap':gap,'HOST_required':needhost,'scratch_required':needscratch,'memory':mem,'root_declared_aggregate_reservation_bytes':19*1073741824,'actual_capacity_acceptance':None}
ns['write'](cap/'ACTUAL-PRE-COPY-CAPACITY.json',facts)
assert facts['HOST_available']>=needhost and facts['scratch_available']>=needscratch and mem['MemAvailable']>=19*1073741824,facts
out=D/'source-materialization-attempt-1';out.mkdir(mode=0o700)
command={'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact accepted candidate6 source materialization only.','argv':['/usr/bin/taskset','-c','0','/usr/bin/python3','-I','-B',str(materializer)]}
ns['write'](cap/'command.json',command)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
result=ns['owned_capture'](command,cap,90,limits);ns['write'](cap/'whole-join.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
print(json.dumps(result,sort_keys=True))
