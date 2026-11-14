"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded artifact-reader correction; compile already passed and is not replayed.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
P=D/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='fec9f0a8b15458db657088b8b80fa1dd3f226c26bf0e35e775158b84f8444c19'
p=json.loads(P.read_text());argv=p['argv'];emit=argv[-2];assert emit.startswith('--emit=obj=');obj=Path(emit[len('--emit=obj='):]);assert obj.is_absolute()
compiler_join=json.loads((D/'actual-fullcrate-compiler-capture-1/whole-join.json').read_text())
assert compiler_join['returncode']==0 and compiler_join['direct_child_joined'] and compiler_join['group_absent'] and compiler_join['closed_streams'] and not compiler_join['error'] and not compiler_join['retirement_error']
assert all(sha(Path(r['private']['path']))==r['private']['sha256'] for r in p['source_inputs'].values())
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.sched_setaffinity(0,{6})
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
cap=D/'actual-fullcrate-nm-capture-correction1';cap.mkdir(mode=0o700);before=sha(obj)
command={'argv':['/usr/bin/nm','-g',str(obj)],'purpose':__doc__,'profile_sha256':sha(D/'ACTUAL-FULLCRATE-PROFILE.json'),'compiler_not_replayed':True};write(cap/'command.json',command)
j=owned_capture(command,cap,90,limits);write(cap/'whole-join.json',j);assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
rows=[x.split() for x in (cap/'stdout').read_text().splitlines()];symbols={}
for name,kind in [('x86_init_text_map_kernel_start_bridge','T'),('x86_map_kernel_start_geometry','U'),('x86_init_normal_set_large_bridge','T')]:
 matches=[x for x in rows if x and x[-1]==name];assert len(matches)==1 and matches[0][-2]==kind,matches;symbols[name]=matches
assert sha(obj)==before
write(D/'ACTUAL-FULLCRATE-RESULT.json',{'scope':__doc__,'status':'PASS_ACTUAL_PRIVATE_PRODUCTION_FULLCRATE_OBJECT_ONLY','profile':json.loads((D/'ACTUAL-FULLCRATE-PROFILE.json').read_text()),'source_inputs_unchanged':True,'source_input_count':len(p['source_inputs']),'object':hashed(obj,32<<20),'symbols':symbols,'compiler_join':compiler_join,'nm_join':j,'compiler_not_replayed':True,'bounded_observer_failure':str(D/'postcompile-observer-failure-1.json'),'canonical_normal_large_bridge_preserved':True,'default_kernel_link':False,'native':False,'whole_file_retirement':False,'CPU6_released':True})
print('PASS existing compiled production Rust object: one textmap T/no U, one geometry U, canonical normal-large T retained; compiler not replayed; CPU6 released')
