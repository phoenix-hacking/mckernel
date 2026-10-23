"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/default-image-successor-1')
SCOPE=__doc__
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def main():
 start=time.monotonic();os.sched_setaffinity(0,{0})
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 helper=R/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'
 raw=helper.read_bytes();assert sha(raw)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 tree=ast.parse(raw,str(helper));nodes=[]
 for node in tree.body:
  if isinstance(node,(ast.Import,ast.ImportFrom)):nodes.append(node)
  elif isinstance(node,ast.FunctionDef) and node.name in {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}:nodes.append(node)
  elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in node.targets):nodes.append(node)
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,90)
 op=json.loads((E/'MATERIALIZATION-COMMAND.PREPARED.json').read_text());assert sha((E/'MATERIALIZATION-COMMAND.PREPARED.json').read_bytes())=='a53aa8f443e25d7e8947fee9663a68a16e3e5f4b6d2d2c15572099611e3a39e7'
 bind=json.loads((E/'SOURCE-BINDING-DELTA.json').read_text());command={'purpose':SCOPE+' Exact private source materialization; no compiler.','argv':op['argv'],'shell':False}
 # Bind the saved script against its pre-execution metadata receipt.
 pin=op['materializer'];assert ref(E/'materialize_source.py')==pin
 host=os.statvfs(N);scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 assert host.f_bavail*host.f_frsize>=16*2**30+(272<<20) and scratch.f_bavail*scratch.f_frsize>=12*2**30
 cap=N/'materialization-capture-1';cap.mkdir(mode=0o700)
 write(cap/'command.json',dict(command,source_pin=pin,helper=ref(helper),operation=ref(E/'MATERIALIZATION-COMMAND.PREPARED.json')))
 write(cap/'capacity.json',dict(scope=SCOPE,host_available_bytes=host.f_bavail*host.f_frsize,scratch_available_bytes=scratch.f_bavail*scratch.f_frsize,host_source_growth_max_bytes=256<<20,capture_extra_bytes=16<<20))
 dest=N/'source-materialization-attempt-1';dest.mkdir(mode=0o700)
 joined=ns['owned_capture'](command,cap,84,lambda:None);write(cap/'whole-join.json',joined)
 result=dict(scope=SCOPE,status='FAIL_FIRST_MATERIALIZATION_RETAINED',whole_join=joined,static_request=None,seconds=None,error=None)
 try:
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error']
  material=ref(dest/'source-inputs.json');assert material['sha256']==bind['predicted_source_manifest_sha256']
  assert time.monotonic()-start<80,'insufficient combined grant for request derivation'
  delta=json.loads((E/'REQUEST-FIELD-DELTA.json').read_text());old=Path(delta['base_static_request']['path']);raw=old.read_bytes();assert ref(old)==delta['base_static_request'];static=json.loads(raw)
  before=json.loads(raw);static.update(delta['new_named_fields'])
  roots=static['memory_allocation_roots'];old_source='/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-4/default-image-successor-1/source-materialization-attempt-1/materialized-source';old_attempt=old.parent/'pinned-full-image-attempt-1';new_attempt=N/'pinned-full-image-attempt-1'
  mapping={old_source:str(dest/'materialized-source'),str(old_attempt/'owner-work'):str(new_attempt/'owner-work'),str(old_attempt/'owner-evidence'):str(new_attempt/'owner-evidence')}
  assert all(p in roots for p in mapping)
  static['memory_allocation_roots']=[mapping.get(p,p) for p in roots]
  assert {k for k in static if static[k]!=before[k]}==set(delta['new_named_fields'])|{'memory_allocation_roots'}
  assert all(static[k] is None for k in ('source_identity','disk_identity','backup_identity')) and static['disk_admission']['host_device'] is None and static['disk_admission']['scratch_device'] is None
  encoded=(json.dumps(static,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(encoded)<32<<20
  path=N/'image-request.STATIC-DATA.json'
  with path.open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
  assert path.read_bytes()==encoded
  result.update(status='PASS_MATERIALIZATION_AND_INCREMENTAL_STATIC_REQUEST_ONLY',materialization=ref(dest/'MATERIALIZATION-RESULT.json'),source_manifest=material,static_request=ref(path),request_changed_fields=sorted(set(delta['new_named_fields'])|{'memory_allocation_roots'}),unchanged_all_other_request_fields=True)
 except BaseException as exc:result['error']=repr(exc)
 result['seconds']=time.monotonic()-start;result['combined_cpu_seconds']=ns['cpu_used']();assert result['seconds']<=90 and result['combined_cpu_seconds']<=60
 write(N/'MATERIALIZATION-AND-REQUEST-RESULT.json',result)
 # Copy finite evidence only; source and 26.5MB static request stay private.
 for source in [N/'MATERIALIZATION-AND-REQUEST-RESULT.json',dest/'MATERIALIZATION-RESULT.json',dest/'admission.json']+list(cap.iterdir()):
  if source.exists():
   target=E/('materialization-capture-1' if source.parent==cap else 'materialization-result-1')/source.name;target.parent.mkdir(exist_ok=True)
   with target.open('xb') as f:f.write(source.read_bytes())
 print(json.dumps({k:result.get(k) for k in ('status','error','seconds','combined_cpu_seconds','source_manifest','static_request')}))
 signal.setitimer(signal.ITIMER_REAL,0)
if __name__=='__main__':main()
