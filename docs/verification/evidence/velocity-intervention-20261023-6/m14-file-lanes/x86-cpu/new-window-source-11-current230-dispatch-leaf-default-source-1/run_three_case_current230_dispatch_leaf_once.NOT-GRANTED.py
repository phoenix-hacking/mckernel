#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CAPTURE=ROOT/'actual-fragment-configure-h990-1'
RESULT=ROOT/'ACTUAL-THREE-CASE-CONFIGURE-ENVELOPE.json'
BINDINGS=[{'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-11-current230-dispatch-leaf-default-source-1/candidate/kernel/CMakeLists.txt', 'sha256': 'a2451f574cf87b4ea5467303bc42684b72e63f7e3d352639998af682a25d1c2f', 'bytes': 25645}, {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-11-current230-dispatch-leaf-default-source-1/canonical-preimage.CMakeLists.txt', 'sha256': '507e1f058f8bc559f4d8b47eb5646d64aa7a20653bce89ad578a5af452ab7faa', 'bytes': 25435}, {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-11-current230-dispatch-leaf-default-source-1/check_paired_current230_dispatch_leaf.NOT-GRANTED.py', 'sha256': '59bf4b68fb932cca895a106eaa62e2545eaa431d65d2a515c79fb6719996c56d', 'bytes': 7272}, {'path': '/usr/bin/cmake', 'sha256': '2ca50a1cca357598eca86fced732989d89e741c12b233520a2ab22e4ce82e730', 'bytes': 11720064}, {'path': '/usr/bin/python3.8', 'sha256': '298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06', 'bytes': 5490456}]
ARGV=['/usr/bin/python3', '-I', '-B', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-11-current230-dispatch-leaf-default-source-1/check_paired_current230_dispatch_leaf.NOT-GRANTED.py', '--output', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-11-current230-dispatch-leaf-default-source-1/actual-fragment-configure-1']
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
def write(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def identity(row):
 p=Path(row['path']);a=p.stat();raw=p.read_bytes();b=p.stat()
 fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
 if any(getattr(a,k)!=getattr(b,k) for k in fields) or hashlib.sha256(raw).hexdigest()!=row['sha256'] or len(raw)!=row['bytes']:raise RuntimeError('bound source identity changed: '+str(p))
 return {k:getattr(b,k) for k in fields}
def main():
 begin=time.monotonic();joined=None;started=False
 try:
  if CAPTURE.exists() or RESULT.exists() or Path(ARGV[-1]).exists():raise RuntimeError('fresh outputs required; no replay')
  grant=json.loads((ROOT/'ROOT-GRANT.json').read_text())
  if grant['CPU']!=6 or grant['candidate_sha256']!='a2451f574cf87b4ea5467303bc42684b72e63f7e3d352639998af682a25d1c2f':raise RuntimeError('exact parent CPU6 current230 dispatch+leaf grant absent')
  before={r['path']:identity(r) for r in BINDINGS}
  if os.getuid()!=1000 or os.geteuid()!=1000 or 6 not in os.sched_getaffinity(0):raise RuntimeError('ordinary UID1000/availableCPU6 required')
  raw=HELPER.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=HELPER_SHA:raise RuntimeError('h990 helper binding differs')
  functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
  assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
  nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
  h={'__file__':str(HELPER)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),h)
  CAPTURE.mkdir(mode=0o700);os.chdir(ROOT);os.sched_setaffinity(0,{6});os.environ['LANG']=os.environ['LC_ALL']='C';os.environ['OMP_NUM_THREADS']=os.environ['RAYON_NUM_THREADS']='1'
  for number in h['STOP_SIGNALS']:signal.signal(number,h['stop'])
  for key,value in ((resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,15),(resource.RLIMIT_FSIZE,4<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(key,(value,value))
  command=dict(argv=ARGV,cwd=str(ROOT),purpose='Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Three compiler-free LANGUAGES NONE current230 dispatch+leaf paired-producer configure cases with copyerror defaultOFF.')
  write(CAPTURE/'profile.json',dict(CPU=6,jobs=1,AS=512<<20,CPU_seconds=15,wall_seconds=25,retirement_seconds=6,FSIZE=4<<20,NOFILE=256,core=0,authority='Parent exact a2451f57 signal_process paired-selector3case compiler-free grant',bindings=BINDINGS))
  write(CAPTURE/'command.json',command);write(CAPTURE/'identities-before.json',before)
  signal.setitimer(signal.ITIMER_REAL,max(.1,31-(time.monotonic()-begin)));started=True
  def limits():resource.setrlimit(resource.RLIMIT_CPU,(max(1,int(15-h['cpu_used']())),max(1,int(15-h['cpu_used']()))))
  joined=h['owned_capture'](command,CAPTURE,max(.1,25-(time.monotonic()-begin)),limits)
  write(CAPTURE/'whole-join.json',joined)
  if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error'] or joined['timed_out']:raise RuntimeError('first unexpected check result; preserve prefix')
  after={r['path']:identity(r) for r in BINDINGS};write(CAPTURE/'identities-after.json',after)
  if before!=after:raise RuntimeError('source identity changed during configure check')
  checks=json.loads((Path(ARGV[-1])/'RESULT.json').read_text())
  if checks['status']!='PASS_THREE_CURRENT230_DISPATCH_LEAF_PAIRED_PRODUCER_CONFIGURES' or checks['compiler_invoked'] is not False or len(checks['cases'])!=3:raise RuntimeError('checker result contract differs')
  report=dict(scope=command['purpose'].split(' Three ')[0],status='PASS_THREE_CURRENT230_DISPATCH_LEAF_PRODUCER_FRAGMENT_CONFIGURES',join=joined,check_result=checks,source_identities_unchanged=True,seconds=time.monotonic()-begin,CPU_seconds=h['cpu_used'](),CPU6_released=True,canonical_mutations=0,compiler=False,SDK=False,native=False,production_default_image=False)
  write(RESULT,report);print(json.dumps(dict(status=report['status'],seconds=report['seconds'],CPU_seconds=report['CPU_seconds'],result=str(RESULT),result_sha256=hashlib.sha256(RESULT.read_bytes()).hexdigest())))
 except BaseException as error:
  if not RESULT.exists():write(RESULT,dict(status='FAIL_STOP_PRESERVE_PREFIX',error=type(error).__name__+': '+str(error),join=joined,seconds=time.monotonic()-begin))
  raise
 finally:
  if started:signal.setitimer(signal.ITIMER_REAL,0)
if __name__=='__main__':main()
