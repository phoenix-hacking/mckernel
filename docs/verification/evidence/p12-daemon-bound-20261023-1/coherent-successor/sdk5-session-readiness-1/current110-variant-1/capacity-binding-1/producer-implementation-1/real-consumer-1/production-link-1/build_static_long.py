"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual static Linux PID1 LONG collector link; no execution of the resulting ELF.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/production-link-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
a=D/'attempt-1';a.mkdir()
for p in D.iterdir():
 if p.is_file():(a/p.name).write_bytes(p.read_bytes())
def ref(p):
 b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
h.write(a/'SOURCE-BINDINGS.json',{'scope':__doc__,'sources':[ref(p) for p in a.iterdir() if p.is_file()]})
os.sched_setaffinity(0,{7});os.environ['RUST_MIN_STACK']='2097152';os.chdir(a)
for k,v in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(k,(v,v))
gcc='/usr/bin/gcc-9';rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
seed=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/candidate/pair_collector.c')
flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_THREADS','-DND_PAIR_LAUNCH_EXPANSION']
commands=[('rust-staticlib',[rust,'--edition=2021','--crate-type=staticlib','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort',str(a/'pair_long_static.rs'),'-o',str(a/'libpair_long.a')]),
('actual-static-LONG-ELF',[gcc,*flags,'-DND_PAIR_LONG',str(a/'pair_collector.c'),str(a/'libpair_long.a'),'-Wl,--gc-sections','-o',str(a/'pair-long-collector')]),
('selected-LONG-preprocessor',[gcc,*flags,'-DND_PAIR_LONG','-E','-P',str(a/'pair_collector.c'),'-o',str(a/'long.i')]),
('default-TEN-preprocessor',[gcc,*flags,'-E','-P',str(a/'pair_collector.c'),'-o',str(a/'default.i')]),
('original-seed-preprocessor',[gcc,*flags,'-E','-P',str(seed),'-o',str(a/'seed.i')]),
('ELF-readelf',['/usr/bin/readelf','-h','-l','-d',str(a/'pair-long-collector')]),
('ELF-defined-symbols',['/usr/bin/nm','--defined-only',str(a/'pair-long-collector')]),
('ELF-undefined-symbols',['/usr/bin/nm','-u',str(a/'pair-long-collector')])]
results=[]
for label,argv in commands:
 capture=a/label;capture.mkdir();command={'argv':argv,'cwd':str(a),'purpose':__doc__,'shell':False};h.write(capture/'command.json',command)
 joined=h.owned_capture(command,capture,90,lambda:None);h.write(capture/'result.json',joined);results.append({'label':label,'whole_join':joined})
 if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:break
status='PASS_COMMANDS' if len(results)==len(commands) and all(r['whole_join']['returncode']==0 for r in results) else 'FAIL_STOP_FIRST_FAILURE'
checks={}
if status=='PASS_COMMANDS':
 try:
  default=(a/'default.i').read_bytes();seed_bytes=(a/'seed.i').read_bytes();assert default==seed_bytes,'default preprocessed TEN differs'
  long=(a/'long.i').read_text();assert 'if(long_dispatch(console,&safe,&empty))good=0;' in long
  assert 'pair_run_launch_expansion' not in long,'TEN runtime function retained in selected LONG'
  assert 'controlled_' not in long and 'bridge_fixture' not in long,'fixture source in production'
  elf=(a/'ELF-readelf/stdout').read_text();assert 'ELF64' in elf and 'Advanced Micro Devices X86-64' in elf and 'EXEC (Executable file)' in elf
  assert 'INTERP' not in elf and 'There is no dynamic section' in elf
  assert not (a/'ELF-undefined-symbols/stdout').read_bytes()
  symbols=(a/'ELF-defined-symbols/stdout').read_text().splitlines();required=['pair_run_long_session','long_now','long_empty','long_pair','long_retain','long_read','long_write']
  matches={name:[line for line in symbols if line.split()[-1]==name] for name in required}
  assert all(len(rows)==1 and rows[0].split()[-2] in ('T','t') for rows in matches.values()),matches
  checks={'default_preprocessed_TEN_byte_identical':True,'LONG_dispatch_selected_TEN_body_excluded':True,'fixture_providers_absent':True,'ELF64_x86_64_static_EXEC_no_INTERP_no_dynamic_no_U':True,'unique_entry_and_actual_callback_symbols':matches,'artifact':ref(a/'pair-long-collector'),'no_ELF_execution':True}
  status='PASS_ACTUAL_STATIC_LONG_ELF_AND_SOURCE_SELECTION'
 except BaseException as exc:
  status='POSTPROCESS_FAILURE_RETAINED';checks={'failure_type':type(exc).__name__,'failure':str(exc)}
h.write(a/'RESULT.json',{'scope':__doc__,'status':status,'results':results,'checks':checks,'native_acceptance':False,'actual_hour_workload':False,'source_or_runtime_acceptance':False})
for p in D.rglob('*'):
 if p.is_file() and p.name not in ('pair-long-collector','libpair_long.a'):
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
print(json.dumps({'status':status,'commands_completed':len(results),'last_label':results[-1]['label'],'checks':checks}))
