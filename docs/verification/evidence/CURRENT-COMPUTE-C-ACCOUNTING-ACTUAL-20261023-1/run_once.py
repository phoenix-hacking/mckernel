"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,time
D=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,1073741824),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
bindings=json.loads((D/'INPUT-TOOL-AND-SOURCE-BINDINGS.json').read_bytes())
for row in bindings['tool_and_lookup_pins']:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
c.write(D/'FROZEN-DRIVER.json',{'path':str(D/'run_once.py'),'sha256':hashlib.sha256((D/'run_once.py').read_bytes()).hexdigest()})
started=time.monotonic();results=[];signal.setitimer(signal.ITIMER_REAL,126)
try:
 for name,argv in [('nm-version',['/usr/bin/nm','--version']),('addr2line-version',['/usr/bin/addr2line','--version']),('ownership-once',bindings['argv'])]:
  A=D/name;A.mkdir(mode=0o700);command={'argv':argv,'purpose':__doc__};c.write(A/'command.json',command);remaining=120-(time.monotonic()-started);assert remaining>0
  r=c.owned_capture(command,A,remaining,lambda:None);c.write(A/'RESULT.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,(name,r)
finally:signal.setitimer(signal.ITIMER_REAL,0)
r=json.loads((D/'symbol-language.json').read_bytes());assert r['image_sha256']==bindings['image']['expected_actual_tool_sha256'];assert r['schema']=='mckernel-symbol-source-attribution-v1'
C=[x for x in r['source_bytes'] if x['language']=='c'];assert sum(x['bytes'] for x in C)==r['language_bytes']['c']
final={'scope':__doc__,'status':'PASS_ACTUAL_CURRENT10972_SYMBOL_SOURCE_ATTRIBUTION','image_sha256':r['image_sha256'],'source_derivative':bindings['source_derivative'],'language_bytes':r['language_bytes'],'per_source_C_bytes':C,'scored_C_plus_Rust_bytes':r['scored_bytes'],'Rust_percent_of_C_plus_Rust':r['rust_percent'],'all_language_symbol_count':r['symbol_count'],'all_language_unique_span_count':r['unique_symbol_span_count'],'C_function_count':None,'metric':r['metric_scope'],'captures':results,'tool_report':{'path':str(D/'symbol-language.json'),'sha256':hashlib.sha256((D/'symbol-language.json').read_bytes()).hexdigest(),'bytes':(D/'symbol-language.json').stat().st_size},'source_and_tool_bindings':{'path':str(D/'INPUT-TOOL-AND-SOURCE-BINDINGS.json'),'sha256':hashlib.sha256((D/'INPUT-TOOL-AND-SOURCE-BINDINGS.json').read_bytes()).hexdigest()},'limitations':['Nonzero definedT/t spans aliasdeduplicated by address+size; symbol-start addr2line source suffix attribution, not all ELF executable PROGBITS.','C+Rust denominator excludes assembly/other; RustvsALL remainder is NOT C.','Unknown/header-origin/mixed-language inline code and padding are not resolved to C; keep other distinct.','CLI counts all-language symbols/spans only; no C-only function count computed or wrapper added.','commit field does not replace exact materialized source derivative above.','No runtime/hotpath coverage, full C retirement or M14/native acceptance claim.'],'CPU0_released':True,'intrinsic_image_hashes':1,'separate_big_artifact_hashes':0,'optional_linked_tool_runs':0,'root_Docker_guest_compiler_operations':0}
c.write(D/'ACTUAL-ACCOUNTING-RESULT.json',final);print(json.dumps({'status':final['status'],'language_bytes':r['language_bytes'],'C_sources':len(C),'CPU0_released':True}))
