"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual controller main statements until BEFORE out.mkdir, with explicit TESTONLY root/profile environment scaffolding.
No productguard removed; no mkdir/Popen/process factory is executed. This is not rootprofile proof.
"""
import ast,copy,hashlib,importlib.util,json,os,resource,sys,types
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/failure-dfbb-docker-start-1/runtime-successor-1');RUNTIME=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/continuation-review/runtime-successor-2');S=RUNTIME/'source';CONTROLLER=RUNTIME/'capture_root_SEGMENT.NOT-RELEASED.py';F=D/'guard-vectors-1';F.mkdir(mode=0o700)
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class ReachedPreEffect(Exception):pass
class Environment:
 def __init__(self,real,values):self.real=real;self.values=values;self.calls=[]
 def __getattr__(self,k):
  if k in self.values:
   def value(*a):self.calls.append(k);return self.values[k](*a)
   return value
  return getattr(self.real,k)
factory_calls=[]
def refused_factory(*a,**kw):factory_calls.append((a,kw));raise AssertionError('process factory forbidden')
checks=[];seq=[0]
def request_file(x):
 seq[0]+=1;p=RUNTIME/('TESTONLY-GUARD-PARENT-CORRECTION2-request-%02d.json'%seq[0]);assert 1<=seq[0]<=16,'exact16requestwriteallowlist';b=(json.dumps(x,sort_keys=True)+'\n').encode()
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:stream.write(b);stream.flush();os.fsync(stream.fileno())
 return p,sha(b)
def consume(controller,request_path,request_sha):
 m=load(controller,'actual_controller_'+str(seq[0]));tree=ast.parse(controller.read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=[];boundary=None
 for n in main.body:
  if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='out' and n.value.func.attr=='mkdir':boundary=n;break
  body.append(n)
 assert boundary is not None and len(body)>15
 original_prefix_AST=ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False)
 extracted=copy.deepcopy(main);extracted.body=copy.deepcopy(body)+[ast.Raise(exc=ast.Call(func=ast.Name(id='ReachedPreEffect',ctx=ast.Load()),args=[],keywords=[]),cause=None)]
 assert ast.dump(ast.Module(body=extracted.body[:-1],type_ignores=[]),include_attributes=False)==original_prefix_AST
 o=Environment(os,dict(getuid=lambda:0,geteuid=lambda:0,sched_getaffinity=lambda pid:{7}));q=Environment(resource,dict(getrlimit=lambda key:(m.CAP,m.CAP) if key==resource.RLIMIT_FSIZE else (resource.RLIM_INFINITY,resource.RLIM_INFINITY) if key==resource.RLIMIT_CPU else (_ for _ in ()).throw(AssertionError('unexpected rootprofile requirement'))))
 m.os=o;m.resource=q;m.subprocess=types.SimpleNamespace(Popen=refused_factory,DEVNULL=__import__('subprocess').DEVNULL);m.ReachedPreEffect=ReachedPreEffect
 exec(compile(ast.fix_missing_locations(ast.Module(body=[extracted],type_ignores=[])),str(controller),'exec'),m.__dict__);prior=sys.argv;sys.argv=[str(controller),str(request_path),request_sha]
 try:m.main()
 finally:sys.argv=prior
 raise AssertionError('unexpectedreturn')
def expect(label,controller,p,h,reason=None):
 try:consume(controller,p,h)
 except ReachedPreEffect:
  assert reason is None,'accepted invalidbinding '+label;checks.append(dict(name=label,status='PASS_REACHED_EXACT_PRE_MKDIR_PRE_POPEN_BOUNDARY'));return
 except RuntimeError as e:
  assert reason is not None and str(e)==reason,(label,str(e),reason);checks.append(dict(name=label,status='PASS_REFUSE',error=str(e)));return
 raise AssertionError('missingexpectedoutcome')
oldrequest=OLD/'CAPTURE-REQUEST.json';expect('actual_failed_aa5_controller_original_serialized_request',OLD/'capture_root_LONG.NOT-RELEASED.py',oldrequest,sha(oldrequest.read_bytes()),'exact LONG owner/release paths')
corrected=json.loads((D/'TESTONLY-CORRECTED-REQUEST.json').read_bytes());p,h=request_file(corrected);expect('corrected_actual_guard_prefix_with_real_sourcefilepins',CONTROLLER,p,h)
# Clone exactly one controllerliteral atatime, recompute only its requiredfilepin.
controller=(CONTROLLER).read_text();oldsource=(OLD/'capture_root_LONG.NOT-RELEASED.py').read_text()
def literal(text,key):return next(ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
for key in ['OWNER_PATH','RELEASE_PATH','HOST_PARENT','NONCE','MANIFEST_PATH','MANIFEST_SHA']:
 value=literal(oldsource,key)
 assert value!=literal(controller,key)
 node=next(n for n in ast.parse(controller).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets));bad=controller.replace(ast.get_source_segment(controller,node),key+' = '+repr(value),1);f=F/('TESTONLY-stale-controller-'+key+'.py');f.write_text(bad);r=copy.deepcopy(corrected);r['wrapper_sha256']=sha(f.read_bytes());p,h=request_file(r);expect('one_stale_controller_literal_'+key,f,p,h,'exact LONG owner/release paths' if key in ('OWNER_PATH','RELEASE_PATH') else 'exact LONG root owner argv')
for name,mut,reason in [
 ('request_wrapper_drift',lambda r:r.update(wrapper_sha256='0'*64),'wrapper source'),
 ('request_owner_hash_drift',lambda r:r['command_source'].update(sha256='0'*64),'command source'),
 ('request_release_path_stale',lambda r:r['long_profile_release'].update(path='/home/holden/mckernel-work/scratch/p12s5l2/r.json'),'exact LONG owner/release paths'),
 ('request_parent_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--attempt-parent')+1,'/home/holden/mckernel-work/native-runs/l12b1/p'),'exact LONG root owner argv'),
 ('request_nonce_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--nonce')+1,'dfbb3adb1c7d45b689a899140f3afffc'),'exact LONG root owner argv'),
 ('request_manifest_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--manifest')+1,'/home/holden/mckernel-work/scratch/p12s5l2/m.json'),'exact LONG root owner argv'),
 ('request_release_digest_argv_mismatch',lambda r:r['argv'].__setitem__(-1,'f'*64),'exact LONG root owner argv'),
 ('request_capture_parent_stale',lambda r:r.update(capture_directory=str(OLD/'actual-capture-1')),'exact fresh capture path'),
 ('request_capture_name_drift',lambda r:r.update(capture_directory=str(F/'unexpected-capture')),'exact fresh capture path')]:
 r=copy.deepcopy(corrected);mut(r);p,h=request_file(r);expect(name,CONTROLLER,p,h,reason)
tracked_open_paths=set()
audit_active=False
def audit_open(event,args):
 if audit_active and event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
  path=os.fsdecode(args[0]);flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
  if path.startswith('/home/holden/mckernel') and not flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):tracked_open_paths.add(path)
sys.addaudithook(audit_open)
o=load(S/'native_diagnostic_container_owner.py','actual_corrected_owner');g=o._long_transport();matrix=json.loads((D/'SOURCE-TO-REQUEST-BINDING-MATRIX.json').read_bytes());module=load(CONTROLLER,'corrected_full_binding_module');r=corrected;a=r['argv'];field=lambda k:a[a.index(k)+1]
assert module.OWNER_PATH==o.SELF==r['command_source']['path'] and r['command_source']['sha256']==sha(Path(o.SELF).read_bytes())
assert module.HOST_PARENT==g.HOST_OUTPUT['parent']==field('--attempt-parent') and module.NONCE==field('--nonce')
assert module.MANIFEST_PATH==field('--manifest') and module.MANIFEST_SHA==field('--manifest-sha256') and module.RELEASE_PATH==r['long_profile_release']['path']==field('--long-profile-release')
assert g.readonly_input(module.MANIFEST_PATH,module.HOST_PARENT)==Path(module.MANIFEST_PATH),'actual_manifest_readonly_scratch_ancestry'
assert r['wrapper_sha256']==g.EXTERNAL_CAPTURE_BINDING['controller_sha256']==sha((CONTROLLER).read_bytes()) and g.EXTERNAL_CAPTURE_BINDING['controller_path']==str(CONTROLLER) and g.EXTERNAL_CAPTURE_BINDING['request_path']==str(RUNTIME/'CAPTURE-REQUEST.json') and g.EXTERNAL_CAPTURE_BINDING['capture_directory']==r['capture_directory']
audit_active=True
try:
 d,m=o.bound_manifest(module.MANIFEST_PATH,module.MANIFEST_SHA)
finally:
 audit_active=False
assert m['pair_long_session']==g.PROFILE and len(o.SOURCE_HASHES)==matrix['source_hash_rows']
# Fresh imports of the actual successor consumer, not only hash-table scanning.
runtime_runner=load(S/'native_diagnostic_runner.py','successor_actual_runner')
runtime_diagnostic,runtime_backend=runtime_runner._runtime()
runtime_paths=dict(diagnostic=runtime_diagnostic.run_diagnostic.__code__.co_filename,
                  backend=runtime_backend.QmpBackend.negotiate.__code__.co_filename,
                  qmp_init=runtime_backend.QmpSession.__init__.__code__.co_filename,
                  qmp_retain=runtime_backend.QmpSession._retain.__code__.co_filename)
assert runtime_paths==dict(diagnostic=str(S/'native_diagnostic.py'),backend=str(S/'native_diagnostic_backend.py'),
                           qmp_init=str(S/'qmp_capture.py'),qmp_retain=str(S/'qmp_capture.py'))
assert g.TRANSPORT==json.loads((D/'LONG-PROFILE.PREPARED.json').read_bytes())

checks.append(dict(name='actual_full_bound_manifest_current_and_controller_transport_owner_request_matrix',status='PASS',readonly_roots=len(o.EXTRA_READONLY),active_runtime_module_paths=runtime_paths))
assert not factory_calls and not (RUNTIME/'actual-capture-1').exists()
# Model exact actualcreateargv destinations, including most-specific ancestor shadow.
obj=object.__new__(o.DiagnosticOwner);obj.owner_sha=r['command_source']['sha256'];obj.manifest_path=module.MANIFEST_PATH;obj.manifest_sha256=module.MANIFEST_SHA;obj.parent=Path(module.HOST_PARENT);obj.nonce=module.NONCE;obj.name='mckernel-native-diagnostic-'+obj.nonce;obj.label='mckernel.native-diagnostic.owner='+obj.nonce;obj.long_requested=True;obj.long_release=module.RELEASE_PATH;obj.long_release_sha=r['long_profile_release']['sha256']
create=obj._create_argv();mounts=[]
for i,arg in enumerate(create[:-1]):
 if arg=='--mount':
  value=create[i+1];parts=value.split(',');fields={k:v for part in parts if '=' in part for k,v in [part.split('=',1)]};src=Path(fields['src']);dst=Path(fields['dst']);assert fields['type']=='bind' and src.is_absolute() and dst.is_absolute() and src.resolve(strict=True)==src and src==dst
  mounts.append(dict(src=str(src),dst=str(dst),directory=src.is_dir(),readonly='readonly' in parts))
required=set(json.loads((D/'PRECISE-SDK6-CONSUMED-PATHS.json').read_bytes())['required_paths']);required.update(o.SOURCE_HASHES);required.update([o.SELF,o.RUNNER,module.MANIFEST_PATH]);actual_reads=sorted(p for p in tracked_open_paths if Path(p).exists());required.update(actual_reads)
def destination(path,table):
 p=Path(path);matches=[row for row in table if p==Path(row['dst']) or row['directory'] and Path(row['dst']) in p.parents]
 assert matches,'requiredpathnotvisible:'+path
 row=max(matches,key=lambda row:len(Path(row['dst']).parts));mapped=Path(row['src'])/p.relative_to(row['dst']);assert mapped==p and mapped.resolve(strict=True)==p and row['readonly'],'shadoworwritablepath:'+path
 return dict(path=path,mount_source=row['src'],mount_destination=row['dst'],readonly=True)
coverage_rows=[destination(p,mounts) for p in sorted(required)]
# A hostfile existing alone is insufficient: removing the exact SDK6owner mount must fail.
owner_json=next(p for p in required if p.endswith('native-running-modules-owner-33f4428ac1c74917bcd6715cdbaee963/owner-receipt.json'))
owner_mount=next(row['dst'] for row in mounts if row['dst']==str(Path(owner_json).parent));bad=[row for row in mounts if row['dst']!=owner_mount]
try:destination(owner_json,bad)
except AssertionError:pass
else:raise AssertionError('missingSDK6ownerROmountnotdetected')
shadow=copy.deepcopy(mounts);shadow.append(dict(src=str(Path(owner_json).parent),dst=owner_json,directory=False,readonly=False))
try:destination(owner_json,shadow)
except AssertionError:pass
else:raise AssertionError('writableshadowancestorignored')
assert not factory_calls and not (RUNTIME/'actual-capture-1').exists()
coverage_report=dict(status='PASS_ACTUAL_CREATE_ARGV_DESTINATION_MODEL_AND_OPEN_FOOTPRINT',all_required_paths=len(coverage_rows),actual_read_open_paths=len(actual_reads),source_hash_rows=len(o.SOURCE_HASHES),historical147preserved=True,readonly_bind_mounts=len([x for x in mounts if x['readonly']]),actual_create_argv=create,required_path_coverage=coverage_rows,actual_strict_consumer_read_paths=actual_reads,negative_missing_SDK6_owner_mount='PASS_REFUSE',negative_writable_destination_shadow='PASS_REFUSE',qualification='Actualfullhostconsumer fileopenfootprint and actualcreateargv exactdestination/ancestor-shadow model; no Docker/container execution or rootprofile qualification.')
(D/'ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json').write_text(json.dumps(coverage_report,sort_keys=True,indent=2)+'\n')
report=dict(scope=__doc__,status='PASS_ACTUAL_CONTROLLER_PRE_EFFECT_GUARDS_NOT_ROOTPROFILE_PROOF',interpreter=sys.executable,version=sys.version,checks=checks,check_count=len(checks),privileged_environment_scaffolding=dict(os=['getuid=0','geteuid=0','sched_getaffinity={7}'],resource=['FSIZE384MiB','CPUunlimited'],qualification='All three actual environment needstatements evaluated with explicitTESTONLY values. No actual root/profile qualification claimed. All functional/source/path/argv/capture guards run unmodified.'),actual_main_prefix_AST_identical=True,boundary='Immediatelybefore out.mkdir; both mkdir and Popen unreachable',process_factory_calls=0,mountcoverage_paths=len(coverage_rows),actual_strict_read_open_paths=len(actual_reads),capture_directories_created=0,root=0,Docker=0,workload=0,source_cohort=len(o.SOURCE_HASHES),final_release_actual_realclock_validation=None,root_execution_release=None,native_acceptance=False)
(D/'ACTUAL-CONTROLLER-GUARD-RESULT.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
