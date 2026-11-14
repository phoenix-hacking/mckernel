"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Accepted VM-current-union h990/profile/headroom/durable loop; frozen union3 commands.
Requires separate ROOT execution grant; preparation does not execute this file.
"""
from pathlib import Path
import ast,collections,hashlib,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent
PINNED_METADATA={'EXACT-COMBINED-PRODUCTION-COMMANDS.NOT-EXECUTED.json': '1baaa22e4526e1773d8d0a4d11d790b750b1ea77c9d9acd886a8b9a087776b7d', 'EXACT12-SOURCE-MANIFEST.json': '8ac0b5ba4371035a61eb99e325e51ae7894056afe2e5955118d233a4f6648810', 'FULL78-SOURCE-MANIFEST.json': '9c8fcc6eef468b357202ea650e8945edade5cdecb4e2da559a00c420361e2102'}
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
assert hashlib.sha256(H.read_bytes()).hexdigest()==HELPER_SHA
# Same accepted actual-body extraction as existing ordinary campaign drivers.
# Top-level product/main code is never imported or executed.
tree=ast.parse(H.read_bytes(),str(H))
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture','cpu_used'}
assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
selected=[]
for node in tree.body:
 if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in names or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in node.targets):selected.append(node)
assert {x.name for x in selected if isinstance(x,ast.FunctionDef)}==names
c={'__file__':str(H),'__name__':'accepted_capture_functions_only'}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(H),'exec'),c)
# Prechild global/profile/readiness bindings, before any Popen.
assert c['stopping'] is False and c['STOP_SIGNALS']=={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
for n in c['STOP_SIGNALS']:signal.signal(n,c['stop'])
os.umask(0o077);os.chdir(D);assert Path.cwd().resolve()==D.resolve()
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
A=D/'root-actual-union3-production-1';A.mkdir(mode=0o700);results=[];durable={};begin=time.monotonic();source_binding=[]
try:
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for name,digest in PINNED_METADATA.items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
 p=json.loads((D/'EXACT-COMBINED-PRODUCTION-COMMANDS.NOT-EXECUTED.json').read_bytes())
 manifest=json.loads((D/'EXACT12-SOURCE-MANIFEST.json').read_bytes());full=json.loads((D/'FULL78-SOURCE-MANIFEST.json').read_bytes())
 assert len(manifest['files'])==12 and full['count']==len(full['sources'])==78 and len(p['commands'])==18
 rows={x['path']:x for x in full['sources']}
 for row in manifest['files']:rows[row['postimage']['path']]=row['postimage']
 for path,row in rows.items():
  actual=c['hashed'](Path(path),4<<20);assert actual['sha256']==row['sha256'] and actual['size']==row['bytes'],path;source_binding.append(actual)
 assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-2/PINNED-TOOLS.json').read_bytes()).hexdigest()=='155e788fd1c48b8e6c3b621a50afdaa745582f47daa5d35164435d7fdff159b5'
 tools=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-2/PINNED-TOOLS.json').read_bytes())
 tool_bindings=[]
 for row in tools['tools']:
  actual=c['hashed'](Path(row['resolved']['path']),2<<20);assert actual['sha256']==row['resolved']['sha256'],row;tool_bindings.append(actual)
 c['write'](A/'PRECHILD-SOURCE-AND-TOOLS.json',{'source_binding':source_binding,'tools':tool_bindings,'capture_helper':HELPER_SHA,'metadata':PINNED_METADATA,'driver':c['hashed'](Path(__file__),1<<20),'interpreter':sys.executable,'version':sys.version,'actual_CWD':str(Path.cwd()),'CPU':sorted(os.sched_getaffinity(0)),'RUST_MIN_STACK':os.environ['RUST_MIN_STACK']})
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 facts={'memory_available':mem,'memory_required':25501368320,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'reserves_preserved':679477248,'CPU':6,'root_grant_required':True}
 c['write'](A/'HEADROOM.json',facts);assert bs.st_size==110<<30 and mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required'],facts
 (D/'output-1').mkdir(mode=0o700);assert not (D/'mckernel_rust.union.o').exists()
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,cmd in enumerate(p['commands']):
  assert Path(cmd['cwd']).resolve()==D.resolve() and Path.cwd().resolve()==D.resolve()
  C=A/('%02d'%i);C.mkdir(mode=0o700);c['write'](C/'command.json',cmd)
  if i<=6:
   target=Path(next(a.split('=',1)[1] for a in cmd['argv'] if a.startswith('--emit=obj='))) if i==0 else Path(cmd['argv'][cmd['argv'].index('-o')+1]);assert not target.exists()
  remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c['owned_capture'](cmd,C,remaining,lambda:None);c['write'](C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None,r
  if i<=6 or i==14:
   target=Path(next(a.split('=',1)[1] for a in cmd['argv'] if a.startswith('--emit=obj='))) if i==0 else Path(cmd['argv'][cmd['argv'].index('-o')+1])
   durable[str(target)]=c['hashed'](target,32<<20);c['write'](A/('DURABLE-OBJECT-%02d.json'%i),{'artifact':durable[str(target)],'actual_source_binding':source_binding,'commands_completed':i+1,'before_symbol_oracles':True})
 # Consume actual completed NM captures; no product/import execution.
 all_T=[];all_U=set();all_defined=set();per_object=[]
 for i in range(7,14):
  T=[];U=set();defined=set()
  for line in (A/('%02d'%i)/'stdout').read_text().splitlines():
   f=line.split()
   if len(f)<2:continue
   kind,name=f[-2:]
   if kind=='T':T.append(name)
   if kind=='U':U.add(name)
   elif kind.isupper():defined.add(name)
  assert len(T)==len(set(T)),(i,'duplicateT');all_T+=T;all_U|=U;all_defined|=defined;per_object.append({'capture':i,'T':sorted(T),'U':sorted(U),'strong_defined':sorted(defined)})
 assert len(all_T)==len(set(all_T)),'duplicate strong text definitions across selected objects'
 PT=[];PU=set()
 for line in (A/'15/stdout').read_text().splitlines():
  f=line.split()
  if len(f)<2:continue
  kind,name=f[-2:]
  if kind=='T':PT.append(name)
  if kind=='U':PU.add(name)
 assert len(PT)==len(set(PT)) and set(PT)==set(all_T),'partial strong text closure'
 assert PU==all_U-all_defined,'partial unresolved strong-definition difference'
 # Recheck stable source/object identities; no shared binary/evidence rescans.
 for row in source_binding+tool_bindings+list(durable.values()):
  st=Path(row['path']).lstat();assert all(getattr(st,k)==row[v] for k,v in [('st_dev','device'),('st_ino','inode'),('st_size','size'),('st_mtime_ns','mtime_ns'),('st_ctime_ns','ctime_ns')]),row['path']
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_UNION3_COMBINED78_SIX_WHOLE_C_STRONG_SYMBOL_AND_PARTIAL_CLOSURE_ONLY','captures':results,'durable_objects':durable,'source_binding':source_binding,'per_object_actual_symbols':per_object,'actual_partial_T':sorted(PT),'actual_partial_U':sorted(PU),'wall_seconds':time.monotonic()-begin,'CPU_seconds':c['cpu_used'](),'CPU6_released':True,'perlane_allocated_ABI_oracles':'Separate inherited suffix predicates not newly executed in this minimal18-command queue. No perlane/default/native acceptance inferred.','native_default_GCC14_final_image':None,'canonical_integration':None}
 c['write'](A/'ACTUAL-WHOLE-JOIN.json',receipt);print(json.dumps({'status':receipt['status'],'commands':len(results),'wall_seconds':receipt['wall_seconds'],'CPU6_released':True}))
except BaseException as exc:
 c['write'](A/'FAILURE.STOP.json',{'scope':__doc__,'error':repr(exc),'captures':results,'durable_objects':durable,'STOP_no_retry':True,'CPU6_released':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
