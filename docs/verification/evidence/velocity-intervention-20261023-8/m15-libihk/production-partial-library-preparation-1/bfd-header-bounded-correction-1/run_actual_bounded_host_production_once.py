"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One granted host whole-TU/library/CLI compile/link; CLI and devices never executed.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def check(v,m):
 if not v:raise RuntimeError(m)
raw=H.read_bytes();check(hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted capture source')
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
check(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'ordinary UID1000 CPU6')
limits_values=[(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]
for k,v in limits_values:check(resource.getrlimit(k)==(v,v),'exact limits')
check(os.environ.get('RUST_MIN_STACK')=='2097152','Rust stack2MiB')
check(Path.cwd()==D,'actual CWD')
ready=D/'HOST-BFD-BOUNDED-CORRECTION.COMMAND-VALIDATED.READY-NOT-GRANTED.json';check(hashlib.sha256(ready.read_bytes()).hexdigest()=='a45eb59586fd3101c5d7bddeb5f0aa6a29bf7b169a7b3f708c33ecae554facdb','frozen bounded correction')
binding=json.loads(ready.read_bytes());check(binding['recipe']['sha256']=='e6775e00e8c834d9f0b9c816843b70cbdfa748506988fbae3190f0e5dfa579bd' and binding['correction']['sha256']=='e1b22eaf17680366b8f3cd7135f9cbd4d2c7138c41e63371e3f398115af38939','selected exact source and recipe')
base=json.loads((D.parent/'REAL-TU-LIBRARY-CLI.EXECUTABLE-READY.NOT-GRANTED.json').read_bytes());x=dict(base,source=binding['correction'],recipe=binding['recipe'],commands=binding['commands']);old=json.loads(Path(x['predecessor']['path']).read_bytes())
refs=[x[k] for k in ('predecessor','source','Rust_actual_staticlib','CLI_source','CLI_build_adapter','CLI_actual_proof','CLI_contract','actual_IHK_config','recipe')]+[old[k] for k in ('original_C','selected_CMake','actual_CMake_cache','actual_link_recipe','Rust_source','Rust_memory')]
checked=[]
refs += [binding[k] for k in ('actual_host_header','actual_host_library','ABI_witness','preserved_source','first_actual_failure','stderr')]
for r in refs:
 b=Path(r['path']).read_bytes();check(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'current input '+r['path']);checked.append(r)
headers=[]
for name in ['ihk_host_user.h','ihklib.h','ihklib_private.h','ihk_rusage.h','affinity.h','status.h','ihk_monitor.h','ihk_debug.h']:
 p=Path('/home/holden/mckernel/ihk/linux/include/ihk')/name;b=p.read_bytes();a=p.stat();headers.append(dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),dev=a.st_dev,inode=a.st_ino))
outputs=['ihklib.remaining.o','libihk.so','ihkconfig.production-consumer.o','ihkconfig.production-consumer']
for name in outputs:check(not (D/name).exists(),'fresh output '+name)
out=D/'root-actual-host-production-bounded-1';check(not out.exists(),'fresh capture')
mem=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024
host=os.statvfs('/home/holden/mckernel-work');scratch=os.statvfs('/home/holden/mckernel-work/scratch');a=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,a.st_size-a.st_blocks*512)
capacity=dict(MemAvailable=mem,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_bytes=a.st_size,backing_allocated=a.st_blocks*512,full_backing_gap=gap,emergency=679477248,HOST_output_growth=128<<20)
check(mem>=19*2**30,'fresh19GiB memory headroom');check(capacity['HOST_available']>=16*2**30+gap+679477248+(128<<20),'HOST floor+full110gap+growth+emergency');check(capacity['scratch_available']>=12*2**30,'scratch floor');check(a.st_size==110*2**30,'110GiB basis')
out.mkdir(mode=0o700)
profile=dict(scope=__doc__,CPU=6,AS=2<<30,CPU_seconds=60,wall=90,grace=6,FSIZE=32<<20,FD=256,core=0,stack=2<<20,RUST_MIN_STACK=2097152)
command=dict(argv=['/bin/bash',x['recipe']['path']]);ns['write'](out/'command.json',dict(scope=__doc__,profile=profile,command=command,ready=x['recipe'],CWD=str(D),capacity=capacity,source_inputs=checked,headers=headers,driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
signal.setitimer(signal.ITIMER_REAL,90)
def limits():
 os.sched_setaffinity(0,{6})
 for k,v in limits_values:resource.setrlimit(k,(v,v))
def actual_started(pid):
 birth=ns['process_start'](pid)
 print(json.dumps(dict(status='ACTUAL_BOUNDED_HOST_PRODUCTION_STARTED',pid=pid,start=birth,CPU=6)),flush=True)
 return birth
r=ns['owned_capture'](command,out,90,limits,started_reader=actual_started);signal.setitimer(signal.ITIMER_REAL,0);ns['write'](out/'RESULT.json',r)
# Durable output identities precede all metadata postprocessors, including on failure.
artifacts={n:ns['hashed'](D/n,32<<20) for n in outputs if (D/n).exists()};ns['write'](out/'DURABLE-OBJECTS.json',artifacts)
positive=r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None
if not positive:
 print(json.dumps(dict(status='STOP_FIRST_HOST_PRODUCTION_FAILURE',result=r,artifacts=artifacts,CPU6_released=True)));raise SystemExit(1)
selected=old['removed_C_definitions'];observed={}
commands={'remaining-C-defined':['/usr/bin/nm','--defined-only',str(D/'ihklib.remaining.o')],'Rust-archive-defined':['/usr/bin/nm','-g','--defined-only',x['Rust_actual_staticlib']['path']],'shared-defined':['/usr/bin/nm','-D','--defined-only',str(D/'libihk.so')],'CLI-undefined':['/usr/bin/nm','-D','--undefined-only',str(D/'ihkconfig.production-consumer')],'CLI-dynamic':['/usr/bin/readelf','-d',str(D/'ihkconfig.production-consumer')]}
for name,argv in commands.items():
 p=out/name;p.mkdir(mode=0o700);v=ns['owned_capture'](dict(argv=argv),p,15,limits);ns['write'](p/'RESULT.json',v);check(v['returncode']==0 and v['direct_child_joined'] and v['group_absent'] and v['closed_streams'] and v['error'] is None and v['retirement_error'] is None,'metadata wholejoin '+name);observed[name]=(p/'stdout').read_text()
counts=lambda text:{n:sum(line.split()[-1:]==[n] for line in text.splitlines()) for n in selected}
check(all(v==0 for v in counts(observed['remaining-C-defined']).values()),'removed eleven C providers')
check(all(v==1 for v in counts(observed['Rust-archive-defined']).values()),'unique actual Rust providers')
check(all(v==1 for v in counts(observed['shared-defined']).values()),'unique shared providers')
for n in x['public_Rust_required_from_CLI'] if 'public_Rust_required_from_CLI' in x else old.get('public_Rust_required_from_CLI',[]):check(n in observed['CLI-undefined'],'CLI public import '+n)
for n in ('ihk_reserve_cpu','ihk_reserve_mem','ihk_get_num_os_instances','ihk_get_os_instances'):check(n in observed['CLI-undefined'],'four public imports')
check('libihk.so' in observed['CLI-dynamic'] and '$ORIGIN' in observed['CLI-dynamic'],'actual private library and ORIGIN')
ns['write'](out/'ACTUAL-PROVIDER-AND-PUBLIC-LINK-RESULT.json',dict(status='PASS_HOST_REAL_TU_PARTIAL_RUST_LIBRARY_AND_EXISTING_RUST_CLI_PUBLIC_LINK',result=r,artifacts=artifacts,selected_providers=selected,C_definitions=counts(observed['remaining-C-defined']),Rust_definitions=counts(observed['Rust-archive-defined']),shared_definitions=counts(observed['shared-defined']),CPU6_released=True,CLI_executed=False,host_only=True,Rocky_default_library_native_qualification=False,remaining_C_bytes=Path(x['source']['path']).stat().st_size))
print(json.dumps(dict(status='PASS_HOST_REAL_TU_PARTIAL_RUST_LIBRARY_AND_EXISTING_RUST_CLI_PUBLIC_LINK',seconds=r['seconds'],CPU6_released=True,artifacts=artifacts)))
