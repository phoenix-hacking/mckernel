"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Complete the explicitly granted Rust T/data U artifact observation; no new test."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.sched_setaffinity(0,{6})
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
cap=D/'ordinary-Rust-object-symbols-1';cap.mkdir(mode=0o700)
cmd={'argv':['/usr/bin/nm',str(D/'fixture-rust.o')],'purpose':__doc__,'profile_sha256':hashlib.sha256((D/'ACTUAL-ORDINARY-PROFILE.json').read_bytes()).hexdigest()};write(cap/'command.json',cmd)
j=owned_capture(cmd,cap,90,limits);write(cap/'whole-join.json',j);assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
rows=[x.split() for x in (cap/'stdout').read_text().splitlines()]
for name,kind in [('x86_init_text_map_kernel_start_bridge','T'),('x86_map_kernel_start_geometry','U')]:
 matches=[x for x in rows if x and x[-1]==name];assert len(matches)==1 and matches[0][-2]==kind,matches
print('PASS exact Rust leaf object: one T getter, one U immutable geometry witness; CPU6 released')
