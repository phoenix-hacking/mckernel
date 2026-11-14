"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact root-granted three-command ordinary diagnostic; no CLI main or guest.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,os,resource,signal,stat,time
SELF=Path(__file__).resolve()
D=SELF.parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def need(ok,message):
 if not ok:raise ValueError(str(message))
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py')
_ACCOUNT=None
def check_campaign():
 global _ACCOUNT
 need(hashlib.sha256(GUARD.read_bytes()).hexdigest()=='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0','exact current actual guardian guard')
 if _ACCOUNT is None:
  spec=importlib.util.spec_from_file_location('installed_loader_actual_guard',GUARD);_ACCOUNT=importlib.util.module_from_spec(spec);spec.loader.exec_module(_ACCOUNT)
 return _ACCOUNT.guard()
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--grant',required=True);parser.add_argument('--grant-sha256',required=True);args=parser.parse_args()
packet=D/'LOADER-THREE-COMMANDS.NOT-RELEASED.json';need(hashlib.sha256(packet.read_bytes()).hexdigest()=='455a43daa524dee21cdeb2e91d4204fb855f9ed6601fb20fe9a9b2caf3548041','exact reviewed source packet')
graw=Path(args.grant).read_bytes();need(hashlib.sha256(graw).hexdigest()==args.grant_sha256,'actual Root grant bytes');actual_grant=json.loads(graw)
need(actual_grant.get('status')=='PASS_ROOT_ORDINARY_INSTALLED_LOADER_THREE_COMMANDS' and actual_grant.get('author')=='/root' and actual_grant.get('execution_count')==1,'actual one-shot Root ordinary loader grant')
need(actual_grant.get('packet')==dict(path=str(packet),sha256=hashlib.sha256(packet.read_bytes()).hexdigest()) and actual_grant.get('source')==dict(path=str(SELF),sha256=hashlib.sha256(SELF.read_bytes()).hexdigest()),'actual exact packet/source grant')
now=check_campaign();need(len(actual_grant['observed_clocks'])==3 and all(0<=n-o<120 for n,o in zip(now,actual_grant['observed_clocks'])) and actual_grant.get('ordinary_CPU6_reserved') is True,'fresh Root ordinary CPU6 reservation')

p=json.loads(packet.read_text());need(actual_grant.get('profile')==p['profile'],'exact granted profile')
reserved=actual_grant.get('aggregate_reserved_memory_bytes')
need(type(reserved) is int and p['profile']['AS_bytes']<=reserved<=p['profile']['aggregate_memory_ceiling_bytes']==23259332608,'actual shared reservation including this job within current invocation ceiling')
need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'nonroot CPU6 grant')
for kind,n in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,128<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:need(resource.getrlimit(kind)==(n,n),'exact granted profile')
need(hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','exact h990')
functions={'need','write','hashed','stop','members','cpu_used','process_start','terminal_unreaped','wait_terminal','owned_capture'};constants={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(H.read_text()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={'__file__':str(H),'__name__':'granted_f4d_loader_h990'};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns);write=ns['write']
def inputs():
 rows=[]
 for r in p['inputs']:
  supplied=Path(r['path']);resolved=Path(r['resolved_path']);need(supplied.resolve(strict=True)==resolved,'same resolved input')
  fd=os.open(resolved,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size==r['bytes'] and a.st_mode==r['mode'],'input type/size/mode')
   h=hashlib.sha256();size=0
   while True:
    block=os.read(fd,65536)
    if not block:break
    size+=len(block);need(size<=r['bytes'],'input grew');h.update(block)
   b=os.fstat(fd);c=resolved.lstat();need(all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in ns['FIELDS']) and size==r['bytes'] and h.hexdigest()==r['sha256'],'exact stable input')
   rows.append(dict(r,identity={k:getattr(b,k) for k in ns['FIELDS']}))
  finally:os.close(fd)
 return rows
def capacity():
 def free(q):s=os.statvfs(q);return s.f_bavail*s.f_frsize
 mem=int(next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')).split()[1])*1024
 result={'HOST_free_bytes':free(D),'scratch_free_bytes':free('/home/holden/mckernel-work/scratch'),'MemAvailable_bytes':mem,'HOST_floor_plus_fullgrowth_bytes':17<<30,'scratch_floor_bytes':12<<30,'HOST_memory_reserve_plus_job_bytes':(4<<30)+(512<<20)}
 need(result['HOST_free_bytes']>=17<<30 and result['scratch_free_bytes']>=12<<30 and mem>=(4<<30)+(512<<20),'fresh granted capacity')
 return result
before=inputs();capacity_before=capacity();output=Path(p['output_root']);cwd=Path(p['required_empty_trusted_cwd']);need(not output.exists(),'fresh output root');os.umask(0o077);output.mkdir(mode=0o700);cwd.mkdir(mode=0o700);need(not list(cwd.iterdir()) and not cwd.is_symlink(),'fresh empty trusted cwd');os.chdir(cwd);need(Path.cwd()==cwd,'actual chdir before Popen')
# The command environment is pinned clean for readelf too. Loader commands use
# their own exact env -i argv, preserving all granted argument bytes.
os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',TZ='UTC')
grant={'scope':__doc__.splitlines()[0],'actual_root_grant':dict(path=str(Path(args.grant).resolve()),sha256=args.grant_sha256),'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256(SELF.read_bytes()).hexdigest(),'h990_sha256':hashlib.sha256(H.read_bytes()).hexdigest(),'profile':p['profile'],'capacity_before':capacity_before,'inputs_before':before,'actual_cwd':str(Path.cwd()),'actual_affinity':sorted(os.sched_getaffinity(0)),'actual_limits':{str(k):resource.getrlimit(k) for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_NOFILE,resource.RLIMIT_CORE]}}
write(output/'ROOT-GRANT.json',grant);results=[]
for n in ns['STOP_SIGNALS']:signal.signal(n,ns['stop'])
started=time.monotonic();signal.setitimer(signal.ITIMER_REAL,45)
try:
 for row in p['commands']:
  check_campaign()
  need(time.monotonic()-started<45,'aggregate work deadline')
  need(not list(cwd.iterdir()),'trusted cwd stays empty')
  cap=Path(row['capture_directory']);cap.mkdir(mode=0o700)
  cmd={'argv':row['argv'],'cwd':str(Path.cwd()),'scope':row['purpose'],'argc':len(row['argv']),'index':row['index']};write(cap/'command.json',cmd)
  result=ns['owned_capture'](cmd,cap,max(0.001,45-(time.monotonic()-started)),lambda:None);write(cap/'status.json',result);results.append({'command':cmd,'result':result})
  if not (result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and not result['error'] and not result['retirement_error']):break
finally:signal.setitimer(signal.ITIMER_REAL,0)
check_campaign();after=inputs();need(before==after,'all declared actual inputs unchanged');need(not list(cwd.iterdir()),'empty cwd preserved');after_capacity=capacity()
passed=len(results)==3 and all(r['result']['returncode']==0 and r['result']['direct_child_joined'] and r['result']['group_absent'] and not r['result']['error'] and not r['result']['retirement_error'] for r in results)
report={'scope':__doc__.splitlines()[0],'status':'THREE_COMMANDS_EXIT0_CAPTURED_REVIEW_PENDING' if passed else 'FIRST_FAILURE_STOPPED_NO_RETRY','commands':results,'command_count':len(results),'whole_wall_seconds':time.monotonic()-started,'total_cpu_seconds':ns['cpu_used'](),'inputs_unchanged':before==after,'capacity_after':after_capacity,'actual_cwd':str(Path.cwd()),'cwd_empty':not list(cwd.iterdir()),'profile':p['profile'],'native_acceptance':False,'executor_main_executed':False,'artifact_mutation':False,'interpretation':'Raw ELF/loader output pending exact dependency/version/path review; rc0 is not a new native/default/wholeABI acceptance.'};write(output/'WHOLE-JOIN.json',report);print(json.dumps({'status':report['status'],'commands':len(results),'wall_seconds':report['whole_wall_seconds'],'CPU_seconds':report['total_cpu_seconds']}));raise SystemExit(0 if passed else 1)
