"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root CPU6 full Rust object and strict two-C union; preserve actual broader U sets.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import shutil
import signal
import time

D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
U=D/'current-process8-union-1';U.mkdir(mode=0o700)
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def check(row):assert pin(Path(row['path']))['sha256']==row['sha256'],row

def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
def need(v,message):
 if not v:raise ValueError(message)
manifest=json.loads((D/'SOURCE-COMPOSITION-HANDOFF.json').read_text())
for row in manifest['sources']:check(row['private'])
assert pin(R/'kernel/rust/process_helpers.rs')['sha256']=='4efa2509c37189b57b5236ea65d6df707a36358a748a2886d5ba66afe9f86ace'
assert pin(R/'kernel/process.c')['sha256']=='120f75ec367ff01a7b3928714bbc95d56053594ea0d9e360f4f6ad33a87e1eb1'
source=U/'source';shutil.copytree(D/'source',source)
shutil.copyfile(R/'kernel/rust/process_helpers.rs',source/'kernel/rust/process_helpers.rs')
source_bindings=[pin(source/row['relative']) for row in manifest['sources']]
process_root=R/'docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-process/new-window-source-5'
process_hand=json.loads((process_root/'ACTUAL-OBJECT-HANDOFF.json').read_text());check(process_hand['result'])
process_recipe=json.loads((process_root/'actual-object-first-1/EXACT-TRACKED-OBJECT-FIRST.json').read_text())
process_obj=Path(process_hand['objects']['process.c.o']['path']);check(process_hand['objects']['process.c.o'])
first=json.loads((D/'ACTUAL-SOURCE3-COMPILE-FIRST-FAILURE-1.json').read_text())
assert [r['join']['returncode'] for r in first['records'][:3]]==[0,0,0]
C=Path(first['records'][1]['command']['path']);Ccmd=json.loads(C.read_text());f03_obj=Path(Ccmd['argv'][-1])
assert Ccmd['argv'][1]=='-DMCKERNEL_RUST_F03_IO_DIAGNOSTICS'
assert pin(source/'kernel/rust/syscall_policy.rs')['sha256']=='9251397ea66b36cf6989da51112d1c2ffb10f9a3dccd63922a87e75f0c211c5e'
ABIresult=json.loads((D/'ACTUAL-SOURCE3-ABI-CORRECTION-RESULT-1.json').read_text())
ABIcmd=json.loads(Path(ABIresult['records'][0]['command']['path']).read_text());abi_obj=Path(ABIcmd['argv'][-1])
for row in ABIresult['outputs']:check(row)
recipe=json.loads((D/'PROPOSED-FULLCRATE-C-TU-COMMANDS.NOT-GRANTED.json').read_text());check(recipe['tool_profile_reference'])
prior=json.loads(Path(recipe['tool_profile_reference']['path']).read_text());check(prior['tools_metadata'])
tools=json.loads(Path(prior['tools_metadata']['path']).read_text())
for row in tools['tools']+prior['extra_tool_bindings']:check(row['resolved'])
helper=Path(tools['capture_helper']['path']);check(tools['capture_helper'])
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(helper.read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
check(prior['exact_ABI_reader'])
abi_ns={'Path':Path,'_fail':need};exec(Path(prior['exact_ABI_reader']['path']).read_text(),abi_ns)
O=U/'output-1';O.mkdir(mode=0o700);CAP=U/'capture-1';CAP.mkdir(mode=0o700)
os.environ['TMPDIR']=str(O);os.environ['RUST_MIN_STACK']='2097152';os.sched_setaffinity(0,{6});os.chdir(O)
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
rust_cmd=json.loads(json.dumps(recipe['commands'][0]))
rust_cmd['argv']=[a.replace(str(D/'source'),str(source)).replace(str(D/'output-proposed-1'),str(O)) for a in rust_cmd['argv']]
commands=[('00-current-full-Rust-object',rust_cmd['argv']),('01-strict-current-process-syscall-Rust-partial',['/usr/bin/ld','-r',str(O/'mckernel_rust.o'),str(f03_obj),str(process_obj),'-o',str(O/'current-union.partial.o')])]
for label,path in [('Rust',O/'mckernel_rust.o'),('F03',f03_obj),('F02',process_obj),('partial',O/'current-union.partial.o')]:commands.append(('02-symbols-'+label,['/usr/bin/nm','-S',str(path)]))
records=[];symbol_text={};begin=time.monotonic()
try:
 write(U/'ACTUAL-UNION-BINDINGS.json',dict(scope=SCOPE,authority='Root explicit current union codegen/strict partial CPU6 onejob AS2GiB sharedCPU60 wall90+6.',source_bindings=source_bindings,process_current=pin(R/'kernel/rust/process_helpers.rs'),processC_current=pin(R/'kernel/process.c'),process_result=process_hand['result'],selectedF03_object=pin(f03_obj),selectedF03_command=pin(C),selected_process_object=pin(process_obj),selected_process_recipe=pin(process_root/'actual-object-first-1/EXACT-TRACKED-OBJECT-FIRST.json'),ABI_object=pin(abi_obj),helper=pin(helper),driver=pin(Path(__file__)),AS=2<<30,CPU=6,jobs=1,shared_CPU=60,shared_wall=90,retirement=6,FSIZE=32<<20,FD=256,stack=2<<20,core=0))
 for label,argv in commands:
  cap=CAP/label;cap.mkdir(mode=0o700);command=dict(scope=SCOPE,purpose=SCOPE+' '+label,argv=argv,cwd=str(O));write(cap/'command.json',command)
  remaining=90-(time.monotonic()-begin);assert remaining>0 and ns['cpu_used']()<60
  cpu_remaining=max(1,int(60-ns['cpu_used']()))
  def limits():
   os.sched_setaffinity(0,{6})
   for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,cpu_remaining),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
  joined=ns['owned_capture'](command,cap,remaining,limits);write(cap/'whole-join.json',joined);records.append(dict(label=label,command=pin(cap/'command.json'),join=joined))
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],joined
  if label.startswith('02-symbols-'):symbol_text[label[len('02-symbols-'):]]=(cap/'stdout').read_text()
 def symbols(text):
  result={}
  for line in text.splitlines():
   row=line.split()
   if len(row)>=2:result.setdefault(row[-1],[]).append(row[-2])
  return result
 maps={label:symbols(text) for label,text in symbol_text.items()}
 f03=manifest['existing_supported_exports_preserved']+manifest['new_runtime_exports'];f02=process_recipe['target_symbols']
 witness={}
 for own,targets in [('F03',f03),('F02',f02)]:
  for target in targets:
   assert maps['Rust'].get(target)==['T'],('Rust unique',target,maps['Rust'].get(target))
   assert maps['partial'].get(target)==['T'],('partial unique',target,maps['partial'].get(target))
   assert not [k for k in maps[own].get(target,[]) if k.upper()!='U'],('own C definition',target,maps[own].get(target))
   witness[target]=dict(Rust=maps['Rust'][target],partial=maps['partial'][target],ownC=maps[own].get(target,[]))
 rust_words=abi_ns['_f06_exact_abi_words'](O/'mckernel_rust.o','f03_subset_Rust_ABI',20)
 C_words=abi_ns['_f06_exact_abi_words'](abi_obj,'f03_subset_C_ABI',20)
 assert rust_words==C_words,(rust_words,C_words)
 Usets={label:sorted(name for name,kinds in syms.items() if 'U' in kinds) for label,syms in maps.items()}
 defined=set(name for label in ['Rust','F03','F02'] for name,kinds in maps[label].items() if any(k.upper()!='U' for k in kinds))
 expected=sorted(set(Usets['Rust']+Usets['F03']+Usets['F02'])-defined)
 result=dict(scope=SCOPE,status='PASS_CURRENT_FULL_RUST_F03_F02_STRICT_UNION_39_EXPORTS_20ABIWORDS',records=records,bindings=pin(U/'ACTUAL-UNION-BINDINGS.json'),exports=witness,F03_count=len(f03),process_count=len(f02),ABI_Rust_words=rust_words,ABI_C_words=C_words,broader_U_exact_sets=Usets,expected_partial_U_from_inputs=expected,unexpected_U_added=sorted(set(Usets['partial'])-set(expected)),unexpected_U_removed=sorted(set(expected)-set(Usets['partial'])),outputs=[pin(p) for p in sorted(O.iterdir()) if p.is_file()],CPU6_released=True,canonical_edits=False,production_image=False,native=False,file_retired=False,CPU_seconds=ns['cpu_used'](),wall_seconds=time.monotonic()-begin)
 write(U/'ACTUAL-CURRENT-UNION-RESULT.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(U/'ACTUAL-CURRENT-UNION-RESULT.json'),CPU6_released=True)))
except BaseException as exc:
 result=dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(r['join']['direct_child_joined'] and r['join']['group_absent'] and r['join']['closed_streams'] for r in records))
 write(U/'ACTUAL-CURRENT-UNION-FIRST-FAILURE.json',result);print(json.dumps(dict(status=result['status'],error=result['error'],receipt=pin(U/'ACTUAL-CURRENT-UNION-FIRST-FAILURE.json'),CPU6_released=result['CPU6_released'])));raise
