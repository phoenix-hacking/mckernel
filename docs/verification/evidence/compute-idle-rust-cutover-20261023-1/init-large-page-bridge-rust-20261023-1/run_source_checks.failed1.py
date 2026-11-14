"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.chdir(D);os.sched_setaffinity(0,{6})
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
commands=[['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'verify_source_patch.py')],['/bin/bash','-n','postimage/kernel/rust/tests/run_equivalence.sh'],['/usr/bin/tar','-czf','source-and-object-snapshots.tar.gz','preimage','postimage','whole-crate','mckernel_rust.o']]
results=[]
for i,argv in enumerate(commands):
 cap=D/('source-check-'+str(i+1));cap.mkdir(mode=0o700);cmd={'argv':argv,'purpose':__doc__};write(cap/'command.json',cmd);j=owned_capture(cmd,cap,90,limits);write(cap/'whole-join.json',j);results.append(j)
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],j
write(D/'source-check-results.json',{'scope':__doc__,'status':'PASS','results':results});print('PASS finite source reversal, bash syntax and source/object retention archive')
