"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Accepted VM-current-union h990/profile/headroom/durable loop; frozen union3 commands.
Requires separate ROOT execution grant; preparation does not execute this file.
"""
from pathlib import Path
import ast,collections,hashlib,json,os,resource,signal,stat,sys,time
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2')
RETAINED_SUFFIX_PROOFS={'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-ADOPTED-RUST-00.json': {'sha256': 'fae31e02fb87eb6d6821232a0d6b35b2cc857e66d5062f9335ace142c73cfa43', 'bytes': 36582}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-OBJECT-01.json': {'sha256': 'c83c2f5ecc5e9ac2dd8c01ae9aa7d227a3efd38ac9416488b23657472bfc3027', 'bytes': 34042}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-OBJECT-02.json': {'sha256': 'f935d2529cc155d3238bb2df892d1db4d96aa21bff6c22652954a7e4cfdd8193', 'bytes': 34046}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/FAILURE.STOP.json': {'sha256': '126096db77ab688264fa594818c870af7aace368f8dc1a8c38e6b8e4ce1a8987', 'bytes': 7987}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/01/command.json': {'sha256': '0572a5b19930d682553042a9eaa25731dd7e8f4004fc4d0da9eca53180290eeb', 'bytes': 3469}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/01/whole-join.json': {'sha256': 'b9927e0894a8bb95ab4610cd0ac7c58c4e9800345806932500b1d13e71ba0035', 'bytes': 1227}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/02/command.json': {'sha256': 'bccf52aab9ffe8bea15f3386d870eac5473fefdb9a3231ff49eff976e06c4960', 'bytes': 3327}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/02/whole-join.json': {'sha256': '7e3c3bba5faf8ae465b67a00d52a18aad491cd2e49508371cb92fdbab1f2868e', 'bytes': 1227}}
QUALIFIED_HEADER={'source': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/passed-exec-cputime-production-preparation-1/executer/include/uti.h', 'destination': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/source/executer/include/uti.h', 'bytes': 1747, 'sha256': '0787fcf51f5c5f5a702196e891cede5e570bb472e2b0a1a1041566b59e784fb7', 'supplement': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/passed-exec-cputime-production-preparation-1/FINAL-CONSUMED-SOURCE-BINDING.SUPPLEMENT.json', 'sha256': '4a72f37e1d2eccd93d80aa5cb54e0d925cb56a602363897e9dbc4b1fb8d7c24e'}, 'header_authority': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/passed-exec-cputime-production-preparation-1/BOUND-COMPOSED-CONSUMED-HEADER-INPUTS.json', 'sha256': 'f369391dd52033c515bc4d1773ceabda2724993c09b7f36e008b34fd6e3370c7'}, 'unchanged_literal': '../executer/include/uti.h', 'source_flags_oracles_changed': False}
PRODUCER_PROOFS={'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/PRECHILD-SOURCE-AND-TOOLS.json': {'sha256': 'c858f564b9cbd6610dbec21cae4649a3441698380811db9ad5922afb7e4bc624', 'bytes': 35411}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/00/command.json': {'sha256': '5c083a8e81d2d6dfc47f64cab091a28d8e61e9c1ba10d9d900ffbf6018e3448e', 'bytes': 1617}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/00/whole-join.json': {'sha256': '46d09efde587c83aaa36234ca4a7783b36872b245065e2165b69808d0b0be9e2', 'bytes': 1131}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/00/direct-wait.json': {'sha256': 'f82abd760bb6fe9617686a96a7fafbff447252dfe0667954dc8ce278762f595c', 'bytes': 82}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/FAILURE.STOP.json': {'sha256': 'f20fc8b1665dca08b52ef59443fd6961149cc3100edc38bd736ab4d92c79ec6d', 'bytes': 1543}}
RETAINED_OBJECT_STAT={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/mckernel_rust.union.o', 'device': 66306, 'inode': 56261129, 'size': 14111144, 'uid': 1000, 'gid': 1000, 'mode': '0o600', 'nlink': 1, 'mtime_ns': 1792817945700782659, 'ctime_ns': 1792817945700782659}
PINNED_METADATA={'EXACT-COMBINED-PRODUCTION-COMMANDS.NOT-EXECUTED.json': 'a740c072536b7f7a45e787302b8354f8fa6cfd789cbd16f9f34e8432f7ee8ec8', 'EXACT12-SOURCE-MANIFEST.json': '3e41a3c0bf998456d443eca83eddeddfe2d689e663307cd1f296dba5e3fa2f27', 'FULL78-SOURCE-MANIFEST.json': '059e50cb07deae5aa7c48e1daae8062a7d7ae0ed6294287744fdd9f48bc51fde'}
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
assert hashlib.sha256(H.read_bytes()).hexdigest()==HELPER_SHA
# Same accepted actual-body extraction as existing ordinary campaign drivers.
# Top-level product/main code is never imported or executed.
tree=ast.parse(H.read_bytes(),str(H))
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture','cpu_used'}
assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
selected=[]
for node in tree.body:
 if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in names or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in node.targets):selected.append(node)
assert {x.name for x in selected if isinstance(x,ast.FunctionDef)}==names
c={'__file__':str(H),'__name__':'accepted_capture_functions_only'}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(H),'exec'),c)
# Prechild global/profile/readiness bindings, before any Popen.
assert c['stopping'] is False and c['STOP_SIGNALS']=={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
for n in c['STOP_SIGNALS']:signal.signal(n,c['stop'])
os.umask(0o077);os.chdir(D);assert Path.cwd().resolve()==D.resolve()
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
A=D/'qualified-uti-closure-and-retained-suffix-correction-1'/'root-actual-qualified-uti-suffix-1';A.mkdir(mode=0o700);results=[];durable={};begin=time.monotonic();source_binding=[]
try:
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for name,digest in PINNED_METADATA.items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
 p=json.loads((D/'EXACT-COMBINED-PRODUCTION-COMMANDS.NOT-EXECUTED.json').read_bytes())
 manifest=json.loads((D/'EXACT12-SOURCE-MANIFEST.json').read_bytes());full=json.loads((D/'FULL78-SOURCE-MANIFEST.json').read_bytes())
 assert len(manifest['files'])==12 and full['count']==len(full['sources'])==78 and len(p['commands'])==18
 # Adopt exact successful command00/source/tool producer proof; no Rust replay.
 for path,row in PRODUCER_PROOFS.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==row['sha256'],path
 prior=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/PRECHILD-SOURCE-AND-TOOLS.json').read_bytes());source_binding=prior['source_binding'];tool_bindings=prior['tools']
 def stable_identity(row):
  st=Path(row['path']).lstat()
  assert all(getattr(st,k)==row[v] for k,v in [('st_dev','device'),('st_ino','inode'),('st_size','size'),('st_uid','uid'),('st_gid','gid'),('st_nlink','nlink'),('st_mtime_ns','mtime_ns'),('st_ctime_ns','ctime_ns')]),row['path']
  assert stat.S_ISREG(st.st_mode) and oct(stat.S_IMODE(st.st_mode))==row['mode'],row['path']
 for row in source_binding+tool_bindings:stable_identity(row)
 stable_identity(RETAINED_OBJECT_STAT)
 actual00=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/00/command.json').read_bytes());assert actual00==p['commands'][0]
 adopted=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/root-actual-union3-production-1/00/whole-join.json').read_bytes())
 assert adopted['pid']==4118482 and adopted['start']==61537485 and adopted['returncode']==0 and adopted['direct_child_joined'] and adopted['group_absent'] and adopted['closed_streams'] and adopted['error'] is None and adopted['retirement_error'] is None and not adopted['timed_out']
 results.append(adopted)
 # Expert parser disposition: strip only exact frozen --emit=obj= prefix.
 emit=[a for a in actual00['argv'] if a.startswith('--emit=obj=')];assert len(emit)==1
 retained=Path(emit[0][len('--emit=obj='):]);assert retained.is_absolute() and retained==D/'mckernel_rust.union.o'
 # Reuse genuine prior firsthash authority via actualdurable receipt and stableidentity.
 for path,row in RETAINED_SUFFIX_PROOFS.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==row['sha256'],path
 rust_receipt=json.loads(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-ADOPTED-RUST-00.json').read_bytes())
 durable[str(retained)]=rust_receipt['artifact'];assert durable[str(retained)]['path']==str(retained)
 stable_identity(durable[str(retained)]);stable_identity(RETAINED_OBJECT_STAT)
 for index,receiptpath,commandpath,joinpath in [(1, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-OBJECT-01.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/01/command.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/01/whole-join.json'), (2, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/DURABLE-OBJECT-02.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/02/command.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/root-union3-preparation-2/retained-rust-adoption-and-suffix-correction-1/root-actual-retained-Rust-suffix-1/02/whole-join.json')]:
  rec=json.loads(Path(receiptpath).read_bytes());artifact=rec['artifact'];stable_identity(artifact);durable[artifact['path']]=artifact
  assert json.loads(Path(commandpath).read_bytes())==p['commands'][index]
  r=json.loads(Path(joinpath).read_bytes());assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out'];results.append(r)
 # Bind only the previously accepted quoted-header supplement at its real literal path.
 actual_header=c['hashed'](Path(QUALIFIED_HEADER['destination']),4096)
 assert actual_header['sha256']==QUALIFIED_HEADER['sha256'] and actual_header['size']==1747
 source_binding.append(actual_header)
 c['write'](A/'ADOPTED-C01-C02-AND-QUALIFIED-HEADER.json',{'retained_source_proofs':RETAINED_SUFFIX_PROOFS,'durable_objects':durable,'literal_header':QUALIFIED_HEADER,'header_actual':actual_header,'new_commands_only':list(range(3,18)),'old_objects_recompiled_or_rehashed':False})

 c['write'](A/'DURABLE-ADOPTED-RUST-00.json',{'artifact':durable[str(retained)],'successful_producer':adopted,'producer_metadata':PRODUCER_PROOFS,'actual_source_binding':source_binding,'failed_original_observer_preserved':True,'original_durable_objects_empty':True,'no_Rust_recompile':True,'before_symbol_oracles':True})
 c['write'](A/'PRECHILD-SOURCE-AND-TOOLS.json',{'source_binding':source_binding,'tools':tool_bindings,'capture_helper':HELPER_SHA,'metadata':PINNED_METADATA,'driver':c['hashed'](Path(__file__),1<<20),'interpreter':sys.executable,'version':sys.version,'actual_CWD':str(Path.cwd()),'CPU':sorted(os.sched_getaffinity(0)),'RUST_MIN_STACK':os.environ['RUST_MIN_STACK']})
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 facts={'memory_available':mem,'memory_required':25501368320,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'reserves_preserved':679477248,'CPU':6,'root_grant_required':True}
 c['write'](A/'HEADROOM.json',facts);assert bs.st_size==110<<30 and mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required'],facts
 assert (D/'output-1').is_dir() and not (D/'output-1').is_symlink()
 assert {str(x) for x in (D/'output-1').iterdir()}=={str(D/'output-1/F01-mem.c.o'),str(D/'output-1/F02-process.c.o')}
 assert (D/'output-1').stat().st_uid==1000 and stat.S_IMODE((D/'output-1').stat().st_mode)==0o700
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,cmd in enumerate(p['commands']):
  if i<3:continue # adopt successful Rust/C01/C02; never replay them
  assert Path(cmd['cwd']).resolve()==D.resolve() and Path.cwd().resolve()==D.resolve()
  C=A/('%02d'%i);C.mkdir(mode=0o700);c['write'](C/'command.json',cmd)
  if i<=6:
   target=Path(next(a[len('--emit=obj='):] for a in cmd['argv'] if a.startswith('--emit=obj='))) if i==0 else Path(cmd['argv'][cmd['argv'].index('-o')+1]);assert not target.exists()
  remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c['owned_capture'](cmd,C,remaining,lambda:None);c['write'](C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None,r
  if i<=6 or i==14:
   target=Path(next(a[len('--emit=obj='):] for a in cmd['argv'] if a.startswith('--emit=obj='))) if i==0 else Path(cmd['argv'][cmd['argv'].index('-o')+1])
   durable[str(target)]=c['hashed'](target,32<<20);c['write'](A/('DURABLE-OBJECT-%02d.json'%i),{'artifact':durable[str(target)],'actual_source_binding':source_binding,'commands_completed':i+1,'before_symbol_oracles':True})
 # Consume actual completed NM captures; no product/import execution.
 all_T=[];all_U=set();all_defined=set();per_object=[]
 for i in range(7,14):
  T=[];U=set();defined=set()
  for line in (A/('%02d'%i)/'stdout').read_text().splitlines():
   f=line.split()
   if len(f)<2:continue
   kind,name=f[-2:]
   if kind=='T':T.append(name)
   if kind=='U':U.add(name)
   elif kind.isupper():defined.add(name)
  assert len(T)==len(set(T)),(i,'duplicateT');all_T+=T;all_U|=U;all_defined|=defined;per_object.append({'capture':i,'T':sorted(T),'U':sorted(U),'strong_defined':sorted(defined)})
 assert len(all_T)==len(set(all_T)),'duplicate strong text definitions across selected objects'
 PT=[];PU=set()
 for line in (A/'15/stdout').read_text().splitlines():
  f=line.split()
  if len(f)<2:continue
  kind,name=f[-2:]
  if kind=='T':PT.append(name)
  if kind=='U':PU.add(name)
 assert len(PT)==len(set(PT)) and set(PT)==set(all_T),'partial strong text closure'
 assert PU==all_U-all_defined,'partial unresolved strong-definition difference'
 # Recheck stable source/object identities; no shared binary/evidence rescans.
 for row in source_binding+tool_bindings+list(durable.values()):
  st=Path(row['path']).lstat();assert all(getattr(st,k)==row[v] for k,v in [('st_dev','device'),('st_ino','inode'),('st_size','size'),('st_mtime_ns','mtime_ns'),('st_ctime_ns','ctime_ns')]),row['path']
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_UNION3_COMBINED78_SIX_WHOLE_C_STRONG_SYMBOL_AND_PARTIAL_CLOSURE_ONLY','captures':results,'adopted_successful_commands':3,'new_suffix_commands':15,'producer_proofs':PRODUCER_PROOFS,'durable_objects':durable,'source_binding':source_binding,'per_object_actual_symbols':per_object,'actual_partial_T':sorted(PT),'actual_partial_U':sorted(PU),'wall_seconds':time.monotonic()-begin,'CPU_seconds':c['cpu_used'](),'CPU6_released':True,'perlane_allocated_ABI_oracles':'Separate inherited suffix predicates not newly executed in this minimal18-command queue. No perlane/default/native acceptance inferred.','native_default_GCC14_final_image':None,'canonical_integration':None}
 c['write'](A/'ACTUAL-WHOLE-JOIN.json',receipt);print(json.dumps({'status':receipt['status'],'commands':len(results),'wall_seconds':receipt['wall_seconds'],'CPU6_released':True}))
except BaseException as exc:
 c['write'](A/'FAILURE.STOP.json',{'scope':__doc__,'error':repr(exc),'captures':results,'durable_objects':durable,'STOP_no_retry':True,'CPU6_released':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
