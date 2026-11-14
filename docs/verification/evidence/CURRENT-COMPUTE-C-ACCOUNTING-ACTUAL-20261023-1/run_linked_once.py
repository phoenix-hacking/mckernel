"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,1073741824),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
W=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work');tool=Path('/home/holden/mckernel/scripts/mckernel_linked_text_ownership.py')
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(tool),'--image',str(W/'output/build/kernel/mckernel.img'),'--link-map',str(W/'output/build/kernel/mckernel.img.map'),'--rust-object',str(W/'output/build/kernel/rust/mckernel_rust.o'),'--source-commit','942c927b1ec93cc31284ff498455909d9bb2d0fc','--output',str(D/'linked-executable.json')]
A=D/'linked-ownership-once';A.mkdir(mode=0o700);c.write(A/'OPTIONAL-TOOL-BINDINGS.json',{'reason':'Conditional rootgrant optionaltool needed: actualsymbolreport classified779738B other and zeroRust dueunknown/CGUsource ratherthan.rs; qualify exactRustmap contribution, do not relabel remainderC.','tool_path':str(tool),'tool_sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256((D/'run_linked_once.py').read_bytes()).hexdigest(),'source_derivative':json.loads((D/'INPUT-TOOL-AND-SOURCE-BINDINGS.json').read_bytes())['source_derivative'],'intrinsic_hashes_only':True,'separate_shared_hashes':0})
command={'argv':argv,'purpose':__doc__};c.write(A/'command.json',command);signal.setitimer(signal.ITIMER_REAL,126)
try:r=c.owned_capture(command,A,120,lambda:None)
finally:signal.setitimer(signal.ITIMER_REAL,0)
c.write(A/'RESULT.json',r)
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,r
report=json.loads((D/'linked-executable.json').read_bytes());assert report['inputs']['image']['sha256']=='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2';assert report['inputs']['rust_object']['sha256']=='c282ce61bf89adedf844e74ba47b9c40ef1c7d1e70fcadc903b5b81f1609266a';assert report['inputs']['link_map']['sha256']=='cb5255c931aff1020a440251fe659a2faee07e77f809f1f7ecc87539befa816c'
print(json.dumps({'status':'PASS_ACTUAL_LINK_MAP_CROSSCHECK','Rust_executable_bytes':report['rust_executable_text_bytes'],'all_executable_bytes':report['total_executable_text_bytes'],'non_Rust_or_padding_NOT_C':report['non_rust_or_padding_executable_text_bytes'],'CPU0_released':True}))
