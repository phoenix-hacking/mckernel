"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary current-checkpoint source materialization when root grants execution. No compiler/root/build.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}
assert Path('/home/holden/mckernel/.git/HEAD').read_text() == 'ref: refs/heads/codex/local-native-staging-repair\n'
assert Path('/home/holden/mckernel/.git/refs/heads/codex/local-native-staging-repair').read_text().strip() == None
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/CANONICAL-SOURCE-SUCCESSOR-BASIS.CHECKPOINT-PENDING.json').read_bytes()).hexdigest() == 'd8d7d5fa7d759dc2fb16ff08217e6af206100ef0b3c05cbfb25864bb8924e8a4'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-2/CANONICAL-INTEGRATION.json').read_bytes()).hexdigest() == '9dd178440cd0db7c08c6ca714c4f7dc2a2df8a11491946de28a11e3d9fdc8233'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/source-materialization-attempt-1/source-inputs.json').read_bytes()).hexdigest() == '77fd79cde7d48ceb65aaf9de2ff8be78005274f22031fe12c58d8309173c58a4'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/source-materialization-attempt-1/materialization-journal.jsonl').read_bytes()).hexdigest() == 'b5d9e8775d7c6a255262e1592a1724f27fb893b80b95d1cdf6073728b1111cf5'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-default-image-preparation-1/native_rust_exact_mckernel_image_offline.py').read_bytes()).hexdigest() == 'c5c35f04b3a86b1f3a3d0dc586e7165d1dba4968b4270fa51cb525907ebf0557'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-default-image-preparation-1/next-build-preparation-1/native_rust_exact_mckernel_image_container_owner.py').read_bytes()).hexdigest() == '1b819224eda96c9f516f699f6834b3353d4cea69c9b5c3ca1bdfb7a46363f12b'
assert hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-default-image-preparation-1/actual-pure-consumer-regressions-1/FINAL-ACTUAL-PURE-REGRESSION-RECEIPT.json').read_bytes()).hexdigest() == '89d41b44d23b6be5e29dd687367bac3bdc9000d71d4bc3d5f4bdf6b224b246b5'
cap=D/'source-materialization-capture-1';cap.mkdir(mode=0o700)
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+268435456+16777216,scratch_required=13631488000,MemAvailable=mem,root_reserved_memory=19*1073741824)
ns['write'](cap/'ACTUAL-PRE-CAPACITY.json',facts);assert facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'] and mem>=19*1073741824,facts
materializer=D/'materialize_union2_source.CPU7.py';validator=None
assert hashlib.sha256(materializer.read_bytes()).hexdigest()=='7eba2b0755aa056783e818c02a461aeba65291d7a24d2596b9498386c6d3f31a'
commands=[{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact currentCHECKPOINT_PENDING accepted11-union2 source materialization only.','argv':['/usr/bin/taskset','-c','7','/home/holden/anaconda3/bin/python3','-I','-B',str(materializer)]}]
ns['write'](cap/'commands.json',{'commands':commands,'materializer_sha256':'7eba2b0755aa056783e818c02a461aeba65291d7a24d2596b9498386c6d3f31a'})
(D/'source-materialization-1').mkdir(mode=0o700)
execution_start_ns=time.time_ns();begin=time.monotonic();initial=ns['cpu_used']();results=[]
for i,command in enumerate(commands,1):
 remaining_wall=90-(time.monotonic()-begin);remaining_cpu=60-(ns['cpu_used']()-initial);assert remaining_wall>0 and remaining_cpu>0
 child_cpu=max(1,int(remaining_cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 path=cap/str(i);path.mkdir(mode=0o700);ns['write'](path/'command.json',command)
 result=ns['owned_capture'](command,path,remaining_wall,limits);ns['write'](path/'whole-join.json',result);results.append(result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 if i==1:
  material=json.loads((D/'source-materialization-1/MATERIALIZATION-RESULT.json').read_text());assert material['source_manifest_canonical_sha256']=='9f74cbaf20e62c3e861794a0fde545264f67e48b6c8ae7d707c09db9f49af486'
whole=dict(scope=__doc__,execution_start_ns=execution_start_ns,execution_end_ns=time.time_ns(),results=results,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used']()-initial,compiler_build_native=None)
ns['write'](cap/'ACTUAL-WHOLE-JOIN.json',whole);print(json.dumps(whole,sort_keys=True))
