"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One granted ordinaryCPU6 tencommand original/candidate actualbody fixture; no root/Docker/guest/native claim.
"""
import ast,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'actual interpreter prerequisite before child'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in n.targets)];ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
p=D/'EXACT-TARGET-FIXTURE-COMMANDS.NOT-RELEASED.json';assert hashlib.sha256(p.read_bytes()).hexdigest()=='878be247b455f4e454ee9053729d88f363ed22929fbfe2a0cc446598f693cfc9';plan=json.loads(p.read_bytes())
for row in [plan['source'],*plan['inputs'].values()]:
 raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes']
out=D/'actual-target-body-fixture-1';out.mkdir(mode=0o700);ns['write'](out/'FROZEN-COMMANDS.json',plan)
def limits():
 os.sched_setaffinity(0,{6})
 for key,value in [(resource.RLIMIT_AS,2147483648),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
started=time.monotonic();results=[];failure=None
for i,command in enumerate(plan['commands']):
 folder=out/('%02d-'%i+command['name']);folder.mkdir(mode=0o700);ns['write'](folder/'command.json',dict(scope=__doc__,argv=command['argv'],profile=dict(CPU=[6],AS=2147483648,CPU_seconds=60,wall=90,grace=6,FSIZE=33554432,NOFILE=256,core=0)))
 signal.setitimer(signal.ITIMER_REAL,90)
 result=ns['owned_capture'](dict(argv=command['argv']),folder,90,limits)
 signal.setitimer(signal.ITIMER_REAL,0);ns['write'](folder/'RESULT.json',result);results.append(dict(name=command['name'],result=result))
 if not (result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None):failure=command['name'];break
 if command['name'].startswith('run_'):
  text=(folder/'stdout').read_text();assert text.startswith('PASS_')
  diagnostics=[line for line in text.splitlines() if line.startswith('P12_LONG_SNAPSHOT_ERROR ')]
  assert all(len(line.encode())+1<=255 for line in diagnostics),diagnostics
if failure is None:
 for mode in range(4):
  old=next(out.glob('*-run_0_'+str(mode))) ;new=next(out.glob('*-run_1_'+str(mode)))
  original=(old/'stdout').read_text();candidate=(new/'stdout').read_text();stripped=''.join(line for line in candidate.splitlines(True) if not line.startswith('P12_LONG_SNAPSHOT_ERROR '));assert original==stripped,mode
report=dict(scope=__doc__,status='PASS' if failure is None else 'FAIL_STOPPED_FIRST_UNEXPECTED_COMMAND',seconds=time.monotonic()-started,command_count=len(results),commands=results,first_failure=failure,original_candidate_output_identical_after_removing_error_only_diagnostic_lines=failure is None,parser_line_includingLF_at_most255=True,actual_kernel_cause=None,controlled_providers='snapshot/time/save explicitly controlled; exact original/candidate bodies and actual ordinaryfileIO executed',CPU6_released=True,root=0,Docker=0,guest=0,native_acceptance=False)
ns['write'](out/'ACTUAL-WHOLE-JOIN.json',report);print(json.dumps(dict(status=report['status'],seconds=report['seconds'],commands=len(results),first_failure=failure,CPU6_released=True),sort_keys=True));assert failure is None
