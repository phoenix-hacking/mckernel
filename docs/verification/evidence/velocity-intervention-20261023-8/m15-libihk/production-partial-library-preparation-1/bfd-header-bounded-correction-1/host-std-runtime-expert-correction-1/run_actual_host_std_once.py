"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One granted expert HOST-std compile + strict shared/publicCLI link. Never execute CLI.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,shlex,signal,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def need(v,m):
 if not v:raise RuntimeError(m)
raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','h990')
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
values=[(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]
need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6} and Path.cwd()==D,'actual ordinary UID CPU6 CWD')
need(os.environ.get('RUST_MIN_STACK')=='2097152','Rust2MiBstack')
for k,v in values:need(resource.getrlimit(k)==(v,v),'exact resource limit')
p=D/'HOST-STD-RUNTIME.EXECUTABLE-READY.NOT-GRANTED.json';b=p.read_bytes();need(hashlib.sha256(b).hexdigest()=='af411ed7d22d7ed13af1f09cde6e3295d5518b85707ed129fef9750bd404907c','selected expert operation');x=json.loads(b)
refs=[x[k] for k in ['source','preserved_root','unchanged_memory_module','genuine_C_object','original_failure']]
base=json.loads((D.parent.parent/'REAL-TU-LIBRARY-CLI.EXECUTABLE-READY.NOT-GRANTED.json').read_bytes())
refs += [base[k] for k in ['CLI_source','CLI_build_adapter','actual_IHK_config']]
for r in refs:
 b=Path(r['path']).read_bytes();need(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'exact source/provider '+r['path'])
need(x['genuine_C_object']['sha256']=='71cc3021c3f550ae5dc1b87478837c0f8672e65569c4ebc59781b07e30ba23d6','retained actual Cobject')
outputs=['libihklib_host_cpu_memory.a','libihk.so','ihkconfig.production-consumer.o','ihkconfig.production-consumer']
for n in outputs:need(not (D/n).exists(),'fresh output '+n)
mem=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024
h=os.statvfs('/home/holden/mckernel-work');s=os.statvfs('/home/holden/mckernel-work/scratch');a=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,a.st_size-a.st_blocks*512)
capacity=dict(MemAvailable=mem,HOST_available=h.f_bavail*h.f_frsize,scratch_available=s.f_bavail*s.f_frsize,backing_bytes=a.st_size,backing_gap=gap)
need(mem>=19*2**30,'fresh19G aggregate');need(a.st_size==110*2**30 and capacity['HOST_available']>=16*2**30+gap+679477248+(128<<20) and capacity['scratch_available']>=12*2**30,'floors/full110gap/growth/emergency')
out=D/'root-actual-host-std-runtime-1';need(not out.exists(),'fresh whole capture');out.mkdir(mode=0o700)
ns['write'](out/'command.json',dict(scope=__doc__,operation_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),profile=x['profile'],source_refs=refs,capacity=capacity,CWD=str(D),argv=x['compile_argv'],driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
signal.setitimer(signal.ITIMER_REAL,90);started=time.monotonic()
def limits():
 os.sched_setaffinity(0,{6})
 for k,v in values:resource.setrlimit(k,(v,v))
def birth(pid):
 value=ns['process_start'](pid);print(json.dumps(dict(status='ACTUAL_HOST_STD_EXPERT_STARTED',pid=pid,start=value,CPU=6)),flush=True);return value
results={}
def command(name,argv,first=False):
 q=out/name;q.mkdir(mode=0o700);ns['write'](q/'command.json',dict(argv=argv));remaining=max(1,90-(time.monotonic()-started));r=ns['owned_capture'](dict(argv=argv),q,remaining,limits,started_reader=birth if first else ns['process_start']);ns['write'](q/'RESULT.json',r);results[name]=r;return r
positive=lambda r:r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None
def durable(name):
 ob={n:ns['hashed'](D/n,32<<20) for n in outputs if (D/n).exists()};ns['write'](out/name,ob);return ob
try:
 r=command('Rust-HOST-std-staticlib',x['compile_argv'],True)
 artifacts=durable('DURABLE-AFTER-COMPILER-BEFORE-POSTPROCESSORS.json')
 need(positive(r),'STOP first HOSTstd compiler failure')
 report=(out/'Rust-HOST-std-staticlib/stderr').read_text();rows=re.findall(r'^note: native-static-libs: (.+)$',report,re.M);need(len(rows)==1,'exact one actual native-static-libs report');flags=shlex.split(rows[0]);need(flags and all(re.fullmatch(r'-l[A-Za-z0-9_+.-]+',f) for f in flags),'bounded actual native library tokens')
 ns['write'](out/'ACTUAL-NATIVE-STATIC-LIBS.json',dict(native_static_libs=flags,source=str(out/'Rust-HOST-std-staticlib/stderr'),sha256=hashlib.sha256((out/'Rust-HOST-std-staticlib/stderr').read_bytes()).hexdigest()))
 argv=x['shared_link_argv_template'][:-1]+flags
 r=command('strict-shared-link',argv);artifacts=durable('DURABLE-AFTER-SHARED-LINK.json');need(positive(r),'STOP first strict shared link failure')
 r=command('existing-CLI-production-compile',x['CLI_compile_argv']);artifacts=durable('DURABLE-AFTER-CLI-COMPILE.json');need(positive(r),'STOP first existing CLI compile failure')
 r=command('existing-CLI-public-PIE-link',x['CLI_link_argv']);artifacts=durable('DURABLE-AFTER-CLI-LINK.json');need(positive(r),'STOP first existing CLI link failure')
 selected=json.loads((D.parent.parent/'PARTIAL-LIBRARY-SOURCE-AND-PROVIDERS.READY-NOT-GRANTED.json').read_bytes())['removed_C_definitions'];observed={}
 metadata={'C-object-defined':['/usr/bin/nm','--defined-only',x['genuine_C_object']['path']],'HOST-std-archive-defined':['/usr/bin/nm','-g','--defined-only',str(D/'libihklib_host_cpu_memory.a')],'shared-defined':['/usr/bin/nm','-D','--defined-only',str(D/'libihk.so')],'shared-undefined':['/usr/bin/nm','-D','--undefined-only',str(D/'libihk.so')],'CLI-undefined':['/usr/bin/nm','-D','--undefined-only',str(D/'ihkconfig.production-consumer')],'CLI-dynamic':['/usr/bin/readelf','-d',str(D/'ihkconfig.production-consumer')]}
 for name,argv in metadata.items():
  r=command(name,argv);need(positive(r),'STOP metadata failure '+name);observed[name]=(out/name/'stdout').read_text()
 counts=lambda text:{n:sum(line.split()[-1:]==[n] for line in text.splitlines()) for n in selected}
 need(all(v==0 for v in counts(observed['C-object-defined']).values()),'eleven old Cproviders excluded');need(all(v==1 for v in counts(observed['HOST-std-archive-defined']).values()),'eleven unique Rustarchive definitions');need(all(v==1 for v in counts(observed['shared-defined']).values()),'eleven unique shared definitions')
 need('rust_eh_personality' not in observed['shared-undefined'] and 'rust_begin_unwind' not in observed['shared-undefined'],'no unresolved Rust personality/panic provider');need('rust_eh_personality' in observed['HOST-std-archive-defined'],'genuine archive personality provider')
 for n in ['ihk_reserve_cpu','ihk_reserve_mem','ihk_get_num_os_instances','ihk_get_os_instances']:need(n in observed['CLI-undefined'],'exact four CLIimports')
 need('libihk.so' in observed['CLI-dynamic'] and '$ORIGIN' in observed['CLI-dynamic'],'public library ORIGIN binding')
 signal.setitimer(signal.ITIMER_REAL,0)
 result=dict(status='PASS_HOST_STD_REAL_RUNTIME_STRICT_SHARED_LIBRARY_AND_RUST_CLI_PUBLIC_LINK',scope=__doc__,results=results,artifacts=artifacts,native_static_libs=flags,source_refs=refs,API_definition_counts=counts(observed['shared-defined']),CLI_executed=False,CPU6_released=True,host_only=True,Rocky_default_native_credit=False,seconds=time.monotonic()-started)
 ns['write'](out/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(result))
except BaseException as exc:
 signal.setitimer(signal.ITIMER_REAL,0)
 result=dict(status='STOP_EXPERT_HOST_STD_FAILURE_NO_AUTHOR_RETRY',scope=__doc__,error=type(exc).__name__+': '+str(exc),results=results,CPU6_released=True,seconds=time.monotonic()-started)
 ns['write'](out/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(result));raise
