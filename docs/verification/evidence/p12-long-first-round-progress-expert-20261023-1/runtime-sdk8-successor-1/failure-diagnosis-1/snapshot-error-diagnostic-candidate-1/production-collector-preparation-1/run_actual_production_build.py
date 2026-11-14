"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,sys,signal,time
D=Path(__file__).resolve().parent
E=D/'evidence'
assert sys.version.startswith('3.9.12 ')
raw=(D/'EXACT-PRODUCTION-BUILD.READY.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='ae255ddd1f2246d2bd40e8c0c149ca25f7570a476d1a008c6463d32893809123';plan=json.loads(raw)
helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw,str(helper));end=next(i for i,x in enumerate(tree.body) if isinstance(x,ast.FunctionDef) and x.name=='owned_capture');ns={'__file__':str(helper)};exec(compile(ast.Module(body=tree.body[:end+1],type_ignores=[]),str(helper),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=19<<30
used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
capacity={}
for label,root,floor in [('HOST',D,16<<30),('scratch',Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 st=os.statvfs(root);free=st.f_bavail*st.f_frsize;assert free>=floor+(64<<20);capacity[label]=free
assert capacity['HOST']>=140534349824 and capacity['scratch']>=13899923456,'existing fullgap/capture/floors/reserves'
ns['write'](D/'ACTUAL-PREBUILD-HEADROOM.json',dict(scope=__doc__,MemAvailable=mem,capacity=capacity,included_usage_percent=used,CPU=[6],aggregate_ceiling=19<<30))
for name,row in plan['source_closure'].items():
 for path in [Path(row['selected']['path']),D/'production-source'/name]:assert hashlib.sha256(path.read_bytes()).hexdigest()==row['selected']['sha256']
for name in ['pair_long_static.rs','pair_long_producer.rs']:
 row=plan['source_closure'][name];assert row['unchanged'] and hashlib.sha256(Path(row['accepted_preimage']['path']).read_bytes()).hexdigest()==row['accepted_preimage']['sha256']
archive=Path(plan['Rust_archive_reuse']['path']);assert archive.stat().st_size==plan['Rust_archive_reuse']['size_observed']
assert all('-DTEST' not in flag and 'FIXTURE' not in flag for flag in plan['commands'][0]['argv'])
assert not (D/'pair-long-collector').exists()
os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
pre=ns['hashed'](archive,32<<20);assert pre['sha256']==plan['Rust_archive_reuse']['expected_sha256'];ns['write'](D/'ACTUAL-RUST-ARCHIVE-PREBUILD.json',pre)
results=[];status='FAIL_FIRST_COMMAND_RETAINED';error=None;elf=None;post=None;reads={}
try:
 for operation in plan['commands']:
  command=dict(operation);label=command.pop('label');env=command.pop('env_binding',{})
  os.chdir(command['cwd']);os.environ.update(env)
  cap=D/('actual-'+label+'-1');cap.mkdir();ns['write'](cap/'command.json',command)
  joined=ns['owned_capture'](command,cap,90,lambda:None);ns['write'](cap/'whole-join.json',joined);results.append({'label':label,'capture':str(cap),'whole_join':joined})
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error'],'first failed '+label
  reads[label]=(cap/'stdout').read_text()
  if label=='production-static-LONG-ELF':
   elf=ns['hashed'](D/'pair-long-collector',32<<20)
   # Durable artifact receipt is emitted before any NM/readelf/consumer observer.
   receipt={'scope':__doc__,'status':'ACTUAL_ELF_COMPILED_POSTPROCESSORS_PENDING','artifact':elf,'source_closure':plan['source_closure'],'compile_whole_join':joined,'production_flags':command['argv'],'native_acceptance':False}
   ns['write'](D/'ACTUAL-COMPILED-ELF.DURABLE.json',receipt)
   with (E/'ACTUAL-COMPILED-ELF.DURABLE.json').open('xb') as f:f.write((D/'ACTUAL-COMPILED-ELF.DURABLE.json').read_bytes())
   post=ns['hashed'](archive,32<<20);ns['write'](D/'ACTUAL-RUST-ARCHIVE-POSTBUILD.json',post)
   assert pre==post,'accepted Rust archive changed across production link'
 names={}
 for line in reads['ELF-symbols'].splitlines():
  fields=line.split()
  if len(fields)>=3:names.setdefault(fields[-1],[]).append(fields[-2])
 for symbol in ['pair_run_long_session','pair_complete_long_session']:assert names.get(symbol)==['T'],symbol
 for symbol in plan['required_actual_output_checks']['real_production_callbacks_present']:assert names.get(symbol)==['t'],symbol
 assert not reads['ELF-undefined'].strip(),'unresolved symbols'
 headers=reads['ELF-headers'];assert 'ELF64' in headers and 'EXEC (Executable file)' in headers and 'Advanced Micro Devices X86-64' in headers
 assert 'INTERP' not in headers and 'There is no dynamic section' in headers,'ELF static headers'
 assert 'PASS_ACTUAL_FINAL_GATE_AND_DEFAULT_WORKSPACE_FULL_LONG_CONSUMER' in reads['unchanged-strict-full-consumer']
 status='PASS_ACTUAL_FINAL_PRODUCTION_ELF_STATIC_LINK_AND_UNCHANGED_FULL_CONSUMER'
except BaseException as exc:error=repr(exc)
result={'scope':__doc__,'status':status,'error':error,'commands':results,'actual_ELF':elf,'Rust_archive_pre':pre,'Rust_archive_post':post,'Rust_archive_unchanged':pre==post,'CPU6_released':all(row['whole_join']['direct_child_joined'] and row['whole_join']['group_absent'] and row['whole_join']['closed_streams'] for row in results),'native_ELF_execution':False,'protocol_consumer_TESTONLY_controlled_derivatives':True,'native_or_LONG_credit':0,'actual_tool':{'gcc9_path':'/usr/bin/gcc-9','version':'Ubuntu9.4.0','python':sys.version},'accepted_source_result':plan['expert_candidate_acceptance'],'actual_capsule':None,'runtime_release':None,'independent_actual_ELF_acceptance':None}
ns['write'](D/'ACTUAL-PRODUCTION-BUILD-AND-CONSUMER-RESULT.json',result)
files=[D/'ACTUAL-PRODUCTION-BUILD-AND-CONSUMER-RESULT.json',D/'ACTUAL-RUST-ARCHIVE-PREBUILD.json']
if (D/'ACTUAL-RUST-ARCHIVE-POSTBUILD.json').exists():files.append(D/'ACTUAL-RUST-ARCHIVE-POSTBUILD.json')
for row in results:
 files += list(Path(row['capture']).iterdir())
for path in files:
 target=E/path.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(path.read_bytes())
print(json.dumps({'status':status,'error':error,'commands':len(results),'actual_ELF':elf,'archive_sha256':pre['sha256'],'CPU6_released':result['CPU6_released'],'seconds':[row['whole_join']['seconds'] for row in results]}))
