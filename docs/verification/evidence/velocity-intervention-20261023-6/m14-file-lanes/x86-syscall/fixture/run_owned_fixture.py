"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse accepted owned_capture990807 for one root-granted ordinary actual C/Rust-body fixture; no root/container/guest.
"""
import ast,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent.parent;F=D/'fixture'
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'actual interpreter prerequisite before child'
assert len(sys.argv)==2 and sys.argv[1] in ('0','6','7'),'only root-granted existing ordinary profile CPU';cpu=int(sys.argv[1])
P=D/'sourcehandoff/EXACT-ACTUAL-BODY-FIXTURE.NOT-RELEASED.json';raw=P.read_bytes();assert hashlib.sha256(raw).hexdigest()=='5bc70e5b46c1704bc4cc37a09fdef038b549f78ca650400e6214f4b6612ceff5';plan=json.loads(raw)
for row in plan['sources'].values():
 raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes']
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';tree=ast.parse(raw);end=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.FunctionDef) and n.name=='owned_capture');ns={'__file__':str(H)};exec(compile(ast.Module(body=tree.body[:end+1],type_ignores=[]),str(H),'exec'),ns)
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=19*2**30
host=os.statvfs('/home/holden/mckernel-work');scratch=os.statvfs('/home/holden/mckernel-work/scratch');capacity=dict(MemAvailable=mem,HOST=host.f_frsize*host.f_bavail,scratch=scratch.f_frsize*scratch.f_bavail);assert capacity['HOST']>=140534349824 and capacity['scratch']>=13899923456
out=F/'actual-body-fixture-1';out.mkdir(mode=0o700);ns['write'](out/'PLAN.json',plan);ns['write'](out/'CAPACITY.json',capacity)
def limits():
 os.sched_setaffinity(0,{cpu})
 for k,v in [(resource.RLIMIT_AS,2147483648),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2097152)]:resource.setrlimit(k,(v,v))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
start=time.monotonic();rows=[];failure=None
for i,command in enumerate(plan['commands']):
 folder=out/('%02d-'%i+command['name']);folder.mkdir(mode=0o700);ns['write'](folder/'command.json',dict(scope=__doc__,argv=command['argv'],profile=dict(cpu=[cpu],AS=2147483648,CPU=60,wall=90,grace=6,FSIZE=33554432,NOFILE=256,core=0,stack=2097152)))
 signal.setitimer(signal.ITIMER_REAL,90);result=ns['owned_capture'](dict(argv=command['argv']),folder,90,limits);signal.setitimer(signal.ITIMER_REAL,0);ns['write'](folder/'RESULT.json',result);rows.append(dict(name=command['name'],capture=str(folder),result=result))
 if not (result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None):failure=command['name'];break
if failure is None:
 text=(Path(rows[2]['capture'])/'stdout').read_text();assert 'PASS_ARCH_PTRACE_SYSCALL_EVENT actual_vectors=588 null_vectors=21 store_event_reread=1 actual_context_ABI=1 default_Rust_entry=1 fallback_preserved=1' in text
 def symbols(path):
  result={}
  for line in path.read_text().splitlines():
   fields=line.split()
   if len(fields)>=2:result.setdefault(fields[-1],[]).append(fields[-2])
  return result
 obj=symbols(Path(rows[3]['capture'])/'stdout');linked=symbols(Path(rows[4]['capture'])/'stdout');assert obj.get('arch_ptrace_syscall_event')==['T'] and obj.get('ptrace_syscall_event')==['U'];assert linked.get('arch_ptrace_syscall_event')==['T'] and linked.get('ptrace_syscall_event')==['T']
report=dict(scope=__doc__,status='PASS' if failure is None else 'FAIL_STOPPED_FIRST_COMMAND',commands=rows,seconds=time.monotonic()-start,first_failure=failure,actual_signature_vectors=609 if failure is None else None,unique_Rust_public_definition=failure is None,existing_callee_trace_provider='C TESTONLY one-arg public ptrace_syscall_event provider; exact existing Rust helper used, no kernel signal/scheduler internals requalified',root=0,Docker=0,guest=0,fullkernel_crate=False,defaultimage_link=False,native_acceptance=False,CPU_released=cpu)
ns['write'](out/'ACTUAL-WHOLE-JOIN.json',report);print(json.dumps(dict(status=report['status'],commands=len(rows),first_failure=failure,seconds=report['seconds'],CPU_released=cpu),sort_keys=True));assert failure is None
