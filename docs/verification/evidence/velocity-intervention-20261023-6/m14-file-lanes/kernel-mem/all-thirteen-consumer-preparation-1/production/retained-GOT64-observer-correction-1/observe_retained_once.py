"""Functional OS/Rust only; no security testing. Retained-only all13 correction, no subprocess/compiler/link/test/object hashing."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,signal,time
N=Path(__file__).resolve().parent;P=N.parent;A=P/'actual-production-capture-1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def stop(signum,frame):raise RuntimeError('bounded retained observer stop '+str(signum))
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,stop)
os.umask(0o077);os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,8<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
signal.setitimer(signal.ITIMER_REAL,15)
try:
 failure=A/'FAILURE.json';assert sha(failure)=='0365f26a27773c3da490c1bd6273c5a99064ce1055942b6da624ecd9bf64849b';f=json.loads(failure.read_bytes());results=f['captures'];assert len(results)==11
 for i,r in enumerate(results):
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None
  assert json.loads((A/('%02d'%i)/'whole-join.json').read_bytes())==r
  for stream,m in r['captures'].items():assert sha(Path(m['path']))==m['sha256']
 ready=P/'EXECUTABLE-READY.NOT-EXECUTED.json';assert sha(ready)=='12d05d2bdf36892d19dab333700fcffe9d9b135d881f3f946e71942ed7ab16a5';plan=json.loads(ready.read_bytes());names=plan['target_exports']
 original=P/'observe_exact_production.py';assert sha(original)=='771e55e74fc978ea6333d675ec7ae19f883e457d72beca8b46bc5453a3cbc1b1'
 corrected=N/'observe_exact_production_corrected.py';assert sha(corrected)=='45be82ded0272cd721a5f6d30ec07f75a3ebf111aaff8b7ef12a906330a5b810'
 # Preserve every original frozen source/header/tool check; no pin relaxation.
 for row in plan['frozen_inputs']:
  assert sha(Path(row['path']))==row['sha256'],row['path']
 for name,m in f['durable_objects'].items():
  st=Path(m['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(m[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 spec=importlib.util.spec_from_file_location('observer',corrected);o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
 expected=json.loads((P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json').read_bytes());T,U,_=o.nm_sets(A/'01/stdout');assert set(T)==set(expected['expected_T']) and all(x==1 for x in T.values()) and U==set(expected['expected_U'])
 CT,CU,Crows=o.nm_sets(A/'06/stdout');assert not(set(names)&{n for t,n in Crows if t!='U'}) and 'mem_tlb_atomic_dec_bridge' in CU
 pp=(A/'03/stdout').read_text()
 for name in names:assert not re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',pp),name
 relocation=o.allocated_callback_relocations(P/'output-1/mem.c.o',names)
 PT,PU,_=o.nm_sets(A/'10/stdout');assert all(PT[x]==1 and x not in PU for x in expected['expected_T'])
 for name,m in f['durable_objects'].items():
  st=Path(m['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(m[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 receipt={'scope':__doc__,'status':'PASS_RETAINED_ACTUAL11_PRODUCTION_COMMANDS_AND_EXACT_GOT64_ALLOCATED_RELOCATION_OBSERVER_CORRECTION','original_FAIL':{'path':str(failure),'sha256':sha(failure)},'original_root_capture':{'path':str(P/'root-actual-production-1/RESULT.json'),'sha256':sha(P/'root-actual-production-1/RESULT.json')},'original_actual11_results':results,'original_durable_objects_unchanged_not_rehashed':f['durable_objects'],'actual_T':len(T),'actual_U':len(U),'all13_unique_RustT':True,'allpriorT_preserved':True,'all13_Cdefinitions_excluded':True,'exact_allocated_relocation':relocation,'partial_all3059_Rust_uniqueT_noU':True,'compiler_link_test_replays':0,'new_subprocesses':0,'object_hashes':0,'original_CPU_seconds':None,'CPU_unavailable_reason':'Original production receipt failed before CPU_seconds serialization; do not infer historical CPU from this retained observer.','original_child_wall_sum':sum(r['seconds'] for r in results),'observer_source':{'path':str(corrected),'sha256':sha(corrected)},'original_driver_recipe_observer_failure_preserved':True,'default_GCC14_finalimage_native':'OPEN','VMports_excluded':True,'whole_mem_file_retired':False}
 write(N/'FINAL-RETAINED-PRODUCTION-HANDOFF.json',receipt);print(json.dumps({'status':receipt['status'],'actual_T':len(T),'actual_U':len(U),'replays':0,'object_hashes':0}))
except BaseException as e:
 write(N/'CORRECTION-FAILURE.json',{'scope':__doc__,'error':repr(e),'STOP_expert_no_retry':True,'compiler_link_test_replays':0,'object_hashes':0});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
