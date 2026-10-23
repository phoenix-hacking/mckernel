"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixture-only alias GCC9 link and actual execution; reuse retained Rust object.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time
P=Path(__file__).resolve().parent;D=P.parent
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
os.chdir(D);os.environ['RUST_MIN_STACK']='2097152'
binding=P/'PRE-EXECUTION-SOURCE-AND-OBJECT-BINDING.json';assert hashlib.sha256(binding.read_bytes()).hexdigest()=='9a32814326142fcb34eed591f5bb565eb2a4e5ea53d7edb166efeebfdbb628c5'
bind=json.loads(binding.read_text());assert hashlib.sha256((D/'fixture.c').read_bytes()).hexdigest()==bind['fixture_after_sha256']
obj=ns['hashed'](D/'fixture-rust.o',32<<20);assert obj['sha256']==bind['Rust_object']['sha256'] and obj['inode']==bind['Rust_object']['identity']['st_ino'] and obj['mtime_ns']==bind['Rust_object']['identity']['st_mtime_ns'] and obj['ctime_ns']==bind['Rust_object']['identity']['st_ctime_ns']
for rel,pin in bind['inputs'].items():
 if rel!='fixture.c':assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin['sha256']
cap=P/'actual-owned-capture-1';cap.mkdir(mode=0o700)
host=os.statvfs(P);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks);mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+16777216,scratch_required=13631488000,MemAvailable=mem,root_reserved_memory=19*1073741824)
ns['write'](cap/'ACTUAL-PRE-CAPACITY.json',facts);assert facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'] and mem>=19*1073741824,facts
commands=[{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. ExistingGCC9fixturelinkwithaliasonly; retainedRustobject,noRustcompile.','argv':['/usr/bin/gcc-9','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',str(D/'fixture.c'),str(D/'fixture-rust.o'),'-Wl,--gc-sections','-o',str(P/'fixture')]},{'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. OnceactualC/Rustfunctionalparityfixture; originalassertions/oraclesunchanged.','argv':[str(P/'fixture')]}]
ns['write'](cap/'commands.json',{'commands':commands,'cwd':str(D),'Rust_object':obj,'alias_source_sha256':bind['fixture_after_sha256'],'Rust_recompile':False})
begin=time.monotonic();start_ns=time.time_ns();initial=ns['cpu_used']();results=[]
for i,command in enumerate(commands,1):
 remaining=90-(time.monotonic()-begin);cpu=60-(ns['cpu_used']()-initial);assert remaining>0 and cpu>0;child_cpu=max(1,int(cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 out=cap/str(i);out.mkdir(mode=0o700);ns['write'](out/'command.json',command)
 result=ns['owned_capture'](command,out,remaining,limits);ns['write'](out/'whole-join.json',result);results.append(result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 if i==1:ns['write'](cap/'ACTUAL-ELF-BINDING.json',ns['hashed'](P/'fixture',32<<20))
assert (cap/'2/stdout').read_text().startswith('clear_range actual-C/Rust ok cases=241920 digest=')
after=ns['hashed'](D/'fixture-rust.o',32<<20);assert after==obj
whole=dict(scope=__doc__,results=results,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used']()-initial,start_ns=start_ns,end_ns=time.time_ns(),Rust_object_unchanged=after,actual_output=(cap/'2/stdout').read_text(),Rust_recompile=False,native=False)
ns['write'](cap/'ACTUAL-WHOLE-JOIN.json',whole);print(json.dumps(whole,sort_keys=True))
