"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted single bounded62ABI genuine-prototype suffix correction; no prefix replay.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import signal
import time

D=Path(__file__).resolve().parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def check(row):assert pin(Path(row['path']))==row,row

def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
manifest_path=D/'SOURCE-COMPOSITION-HANDOFF.json';m=json.loads(manifest_path.read_text())
for key in ['C','policy','aggregate','C_diff','policy_diff','proposed_commands']:check(m[key])
for row in m['sources']:check(row['private'])
for row in m['actual_headers']+m['existing_witnesses']:check(row)
recipe=json.loads((D/'PROPOSED-FULLCRATE-C-TU-COMMANDS.NOT-GRANTED.json').read_text());check(recipe['tool_profile_reference'])
prior=json.loads(Path(recipe['tool_profile_reference']['path']).read_text());check(prior['tools_metadata'])
tools=json.loads(Path(prior['tools_metadata']['path']).read_text())
for row in tools['tools']+prior['extra_tool_bindings']:check(row['resolved'])
helper=Path(tools['capture_helper']['path']);assert pin(helper)['sha256']==tools['capture_helper']['sha256']
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(helper.read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
correction_path=D/'BOUNDED-ABI-DECLARATION-CORRECTION.SOURCE-ONLY.json'
assert pin(correction_path)['sha256']=='f26a3507972c54f1d7fd788063c803a0d5789234ab949bcdb1159d8a7b8f0b4b'
correction=json.loads(correction_path.read_text())
for key in ['first_failure','original_C','original_aggregate','corrected_aggregate','unchanged_runtime_C','unchanged_runtime_policy']:check(correction[key])
O=D/'actual-source3-ABI-correction-output-1';O.mkdir(mode=0o700)
CAP=D/'actual-source3-ABI-correction-capture-1';CAP.mkdir(mode=0o700)
os.environ['TMPDIR']=str(O);os.environ['RUST_MIN_STACK']='2097152'
os.sched_setaffinity(0,{6});os.chdir(O)
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
commands=[correction['command']]
commands[0]['cwd']=str(O)
commands[0]['purpose']=SCOPE+' Exact original prototype visibility before unchanged62ABI; prefix not replayed.'
records=[];begin=time.monotonic()
try:
 write(CAP/'profile.json',dict(scope=SCOPE,authority='Root explicit CPU6 onejob only62ABI correction f26a3507; shared30CPU/45wall; three passing prefix retained.',CPU=6,jobs=1,AS=2<<30,shared_CPU=30,shared_wall=45,retirement=6,FSIZE=32<<20,NOFILE=256,STACK=2<<20,core=0,helper=pin(helper),driver=pin(Path(__file__)),manifest=pin(manifest_path),prefix_replayed=False,correction=pin(correction_path)))
 for command in commands:
  assert ns['cpu_used']()<30
  cap=CAP/command['label'];cap.mkdir(mode=0o700);write(cap/'command.json',command)
  remaining=45-(time.monotonic()-begin);assert remaining>0
  def limits():
   os.sched_setaffinity(0,{6})
   for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,max(1,int(30-ns['cpu_used']()))),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
  joined=ns['owned_capture'](command,cap,remaining,limits);write(cap/'whole-join.json',joined)
  records.append(dict(label=command['label'],command=pin(cap/'command.json'),join=joined))
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],joined
 assert ns['cpu_used']()<=30
 result=dict(scope=SCOPE,status='PASS_CURRENT_F03_SOURCE3_CORRECTED_62ABI_SUFFIX_PREFIX_REUSED',records=records,CPU6_released=True,canonical_edits=False,strict_partial=False,default=False,native=False,file_retired=False,CPU_seconds=ns['cpu_used'](),wall_seconds=time.monotonic()-begin,outputs=[pin(p) for p in sorted(O.iterdir()) if p.is_file()])
 write(D/'ACTUAL-SOURCE3-ABI-CORRECTION-RESULT-1.json',result)
 print(json.dumps(dict(status=result['status'],receipt=pin(D/'ACTUAL-SOURCE3-ABI-CORRECTION-RESULT-1.json'),CPU6_released=True)))
except BaseException as exc:
 result=dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_NO_UNCHANGED_RETRY',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(r['join']['direct_child_joined'] and r['join']['group_absent'] and r['join']['closed_streams'] for r in records))
 write(D/'ACTUAL-SOURCE3-ABI-CORRECTION-FAILURE-1.json',result)
 print(json.dumps(dict(status=result['status'],error=result['error'],CPU6_released=result['CPU6_released'],receipt=pin(D/'ACTUAL-SOURCE3-ABI-CORRECTION-FAILURE-1.json'))));raise
