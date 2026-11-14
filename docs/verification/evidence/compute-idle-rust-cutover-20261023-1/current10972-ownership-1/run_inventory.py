"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,time
E=Path(__file__).resolve().parent
D=Path('/home/holden/mckernel-work/host-preparation/current10972-compute-ownership-20261023-1')
R=Path('/home/holden/mckernel');SCOPE=__doc__
W=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work')
SOURCE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/source-materialization-1/materialized-source')
def write(p,value):
 with p.open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def identity(p):
 s=p.stat();return dict(path=str(p),dev=s.st_dev,inode=s.st_ino,mode=s.st_mode,nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def main():
 start=time.monotonic();os.sched_setaffinity(0,{6})
 for k,v in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,128<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 helper=R/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';raw=helper.read_bytes();assert sha(raw)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 tree=ast.parse(raw);nodes=[]
 for node in tree.body:
  if isinstance(node,(ast.Import,ast.ImportFrom)):nodes.append(node)
  elif isinstance(node,ast.FunctionDef) and node.name in {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}:nodes.append(node)
  elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in node.targets):nodes.append(node)
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,120)
 prep=json.loads((E/'PREPARED-COMMAND.json').read_text());script=Path(prep['script']['path']);assert sha(script.read_bytes())==prep['script']['sha256']
 for row in prep['tool_bindings']:
  assert sha(Path(row['path']).read_bytes())==row['sha256']
 for row in prep['artifact_authorities']:
  assert identity(Path(row['path']))==row['fresh_stat']
 assert os.statvfs(D).f_bavail*os.statvfs(D).f_frsize>=16*2**30+(16<<20)
 assert os.statvfs('/home/holden/mckernel-work/scratch').f_bavail*os.statvfs('/home/holden/mckernel-work/scratch').f_frsize>=12*2**30
 cap=D/'inventory-capture-1';cap.mkdir(mode=0o700);write(cap/'command.json',prep)
 joined=ns['owned_capture'](prep,cap,115,lambda:None);write(cap/'whole-join.json',joined)
 result=dict(scope=SCOPE,status='FAIL_FIRST_INVENTORY_RETAINED',whole_join=joined,error=None,report=None,seconds=None)
 try:
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error']
  for row in prep['artifact_authorities']:assert identity(Path(row['path']))==row['fresh_stat']
  report=D/'symbol-language.json';data=json.loads(report.read_text());assert data['image_sha256']=='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'
  result.update(status='PASS_ONE_TIME_CURRENT10972_SYMBOL_START_ATTRIBUTION',report=dict(path=str(report),bytes=report.stat().st_size,sha256=sha(report.read_bytes())),language_bytes=data['language_bytes'],source_bytes=data['source_bytes'],symbol_count=data['symbol_count'],unique_symbol_span_count=data['unique_symbol_span_count'],source_derivative=prep['source_derivative'],limitations=['Alias-deduplicated nonzero T/t symbol spans, attributed by symbol-start addr2line source suffix; excludes unsized/gap/padding text.','Assembly/other are not C. Header-origin/inlined/mixed-language code may classify as other or symbol-start source.','C-only function counts not reported by existing CLI; all-symbol counts are not C function counts.','Current10972 image only; newer canonical memory/idle ports are not installed. No language-retirement or native-coverage credit.'])
 except BaseException as exc:result['error']=repr(exc)
 result['seconds']=time.monotonic()-start;result['combined_cpu_seconds']=ns['cpu_used']();write(D/'RESULT.json',result)
 for p in [D/'RESULT.json',D/'symbol-language.json']+list(cap.iterdir()):
  if p.exists():
   target=E/('inventory-capture-1' if p.parent==cap else '.')/p.name;target.parent.mkdir(exist_ok=True)
   with target.open('xb') as f:f.write(p.read_bytes())
 signal.setitimer(signal.ITIMER_REAL,0)
 print(json.dumps({k:result.get(k) for k in ('status','error','seconds','combined_cpu_seconds','language_bytes','symbol_count','unique_symbol_span_count','report')}))
if __name__=='__main__':main()
