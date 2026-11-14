"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary current-checkpoint source materialization when root grants execution. No compiler/root/build.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
D=Path(__file__).resolve().parent
ROOT_APPLY_PUBLICATION_COMMIT=None
assert ROOT_APPLY_PUBLICATION_COMMIT is not None
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
assert Path('/home/holden/mckernel/.git/HEAD').read_text() == 'ref: refs/heads/codex/local-native-staging-repair\n'
assert Path('/home/holden/mckernel/.git/refs/heads/codex/local-native-staging-repair').read_text().strip() == ROOT_APPLY_PUBLICATION_COMMIT
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/FROZEN81-ONE-CMAKE-SELECTION.SOURCE-AUTHORITY.json').read_bytes()).hexdigest() == '732b74fd572debaedfb2a224f312d76945daa7c535a1ad3efd2c6059a429a86c'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/ROOT-ACTUAL-EXACT14-INTEGRATION.json').read_bytes()).hexdigest() == 'b753e9d6d443386ef2a2075698e423cb9ce6e02a1fc1a61571dcac927f2803e6'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/CURRENT81-ONE-CPU-CFG-CLOSURE.NOT-ACTUAL.json').read_bytes()).hexdigest() == 'e275a8b4bdb3497ccfa7d96390d5330dec69ae7db1689cbf5320d0e3e92f09a5'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/source-materialization-cfg-only-attempt-1/source-inputs.json').read_bytes()).hexdigest() == 'a94adc2f84f2b0078735891bf1a3e28adcf4641f2d1d4160bfaadc2ec0a249f4'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/source-materialization-cfg-only-attempt-1/materialization-journal.jsonl').read_bytes()).hexdigest() == '788c9d171800441eedbcc6a029945dc3e507a8247e8de489eaae8d043f1709e7'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/materialize_frozen81_one_CMake.CPU6.NOT-EXECUTED.py').read_bytes()).hexdigest() == '83ce4a6e341d90082f6a489d97d78e32e1be381c33c49706f6a62a120b133ab3'
cap=D/'source-materialization-native-owned-selection-capture-attempt-1';cap.mkdir(mode=0o700)
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+268435456+16777216,scratch_required=13631488000,MemAvailable=mem,root_admission_minimum_memory=25501368320,workload_planning_memory=21206401024,HOST_control_reserve_memory=4294967296,planning_only_no_durable_lease=True)
ns['write'](cap/'ACTUAL-PRE-CAPACITY.json',facts);assert facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'] and mem>=25501368320,facts
materializer=D/'materialize_frozen81_one_CMake.CPU6.NOT-EXECUTED.py';validator=None
assert hashlib.sha256(materializer.read_bytes()).hexdigest()=='83ce4a6e341d90082f6a489d97d78e32e1be381c33c49706f6a62a120b133ab3'
commands=[{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact current81 canonical18 plus three real Rust leaves source materialization only.','argv':['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(materializer)]}]
ns['write'](cap/'commands.json',{'commands':commands,'materializer_sha256':'83ce4a6e341d90082f6a489d97d78e32e1be381c33c49706f6a62a120b133ab3'})
(D/'source-materialization-native-owned-selection-attempt-1').mkdir(mode=0o700)
execution_start_ns=time.time_ns();begin=time.monotonic();initial=ns['cpu_used']();results=[]
for i,command in enumerate(commands,1):
 remaining_wall=90-(time.monotonic()-begin);remaining_cpu=60-(ns['cpu_used']()-initial);assert remaining_wall>0 and remaining_cpu>0
 child_cpu=max(1,int(remaining_cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 path=cap/str(i);path.mkdir(mode=0o700);ns['write'](path/'command.json',command)
 result=ns['owned_capture'](command,path,remaining_wall,limits);ns['write'](path/'whole-join.json',result);results.append(result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 assert ns['cpu_used']()-initial<=60 and time.monotonic()-begin<=90,{'phase':'after-positive-whole-join','CPU_seconds':ns['cpu_used']()-initial,'seconds':time.monotonic()-begin,'retirement_grace_seconds':6}
 if i==1:
  material=json.loads((D/'source-materialization-native-owned-selection-attempt-1/MATERIALIZATION-RESULT.json').read_text());assert material['source_manifest_canonical_sha256']=='65321d3c3e6663d9e7cc516e50b221f9814492843df01ad7e553b30a0de1690d'
whole=dict(scope=__doc__,execution_start_ns=execution_start_ns,execution_end_ns=time.time_ns(),results=results,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used']()-initial,compiler_build_native=None)
assert ns['cpu_used']()-initial<=60 and time.monotonic()-begin<=90,{'phase':'immediately-before-success-publication','CPU_seconds':ns['cpu_used']()-initial,'seconds':time.monotonic()-begin,'retirement_grace_seconds':6}
ns['write'](cap/'ACTUAL-WHOLE-JOIN.json',whole);print(json.dumps(whole,sort_keys=True))
