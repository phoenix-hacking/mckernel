"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual controller main statements until BEFORE out.mkdir, with explicit TESTONLY root/profile environment scaffolding.
No productguard removed; no mkdir/Popen/process factory is executed. This is not rootprofile proof.
"""
import ast,copy,hashlib,importlib.util,json,os,resource,sys,types
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=D.parent/'failure-dfbb-docker-start-1/runtime-successor-1';S=D/'source';F=D/'guard-vectors-1';F.mkdir(mode=0o700)
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
 seq[0]+=1;p=D/('TESTONLY-request-%02d.json'%seq[0]);b=(json.dumps(x,sort_keys=True)+'\n').encode();p.write_bytes(b);return p,sha(b)
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
corrected=json.loads((D/'TESTONLY-CORRECTED-REQUEST.json').read_bytes());p,h=request_file(corrected);expect('corrected_actual_guard_prefix_with_real_sourcefilepins',D/'capture_root_LONG.NOT-RELEASED.py',p,h)
# Clone exactly one controllerliteral atatime, recompute only its requiredfilepin.
controller=(D/'capture_root_LONG.NOT-RELEASED.py').read_text();oldsource=(OLD/'capture_root_LONG.NOT-RELEASED.py').read_text()
def literal(text,key):return next(ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
for key in ['OWNER_PATH','RELEASE_PATH','HOST_PARENT','NONCE','MANIFEST_PATH','MANIFEST_SHA']:
 value=literal(oldsource,key) if key!='MANIFEST_SHA' else '0'*64
 assert value!=literal(controller,key)
 node=next(n for n in ast.parse(controller).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets));bad=controller.replace(ast.get_source_segment(controller,node),key+' = '+repr(value),1);f=F/('TESTONLY-stale-controller-'+key+'.py');f.write_text(bad);r=copy.deepcopy(corrected);r['wrapper_sha256']=sha(f.read_bytes());p,h=request_file(r);expect('one_stale_controller_literal_'+key,f,p,h,'exact LONG owner/release paths' if key in ('OWNER_PATH','RELEASE_PATH') else 'exact LONG root owner argv')
for name,mut,reason in [
 ('request_wrapper_drift',lambda r:r.update(wrapper_sha256='0'*64),'wrapper source'),
 ('request_owner_hash_drift',lambda r:r['command_source'].update(sha256='0'*64),'command source'),
 ('request_release_path_stale',lambda r:r['long_profile_release'].update(path='/home/holden/mckernel-work/scratch/p12s5l2/r.json'),'exact LONG owner/release paths'),
 ('request_parent_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--attempt-parent')+1,'/home/holden/mckernel-work/native-runs/l12b1/p'),'exact LONG root owner argv'),
 ('request_nonce_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--nonce')+1,'dfbb3adb1c7d45b689a899140f3afffc'),'exact LONG root owner argv'),
 ('request_manifest_stale',lambda r:r['argv'].__setitem__(r['argv'].index('--manifest')+1,'/home/holden/mckernel-work/scratch/p12s5l2/m.json'),'exact LONG root owner argv'),
 ('request_release_digest_argv_mismatch',lambda r:r['argv'].__setitem__(-1,'0'*64),'exact LONG root owner argv'),
 ('request_capture_parent_stale',lambda r:r.update(capture_directory=str(OLD/'actual-capture-1')),'exact fresh capture path'),
 ('request_capture_name_drift',lambda r:r.update(capture_directory=str(F/'unexpected-capture')),'exact fresh capture path')]:
 r=copy.deepcopy(corrected);mut(r);p,h=request_file(r);expect(name,D/'capture_root_LONG.NOT-RELEASED.py',p,h,reason)
o=load(S/'native_diagnostic_container_owner.py','actual_corrected_owner');g=o._long_transport();matrix=json.loads((D/'SOURCE-TO-REQUEST-BINDING-MATRIX.json').read_bytes());module=load(D/'capture_root_LONG.NOT-RELEASED.py','corrected_full_binding_module');r=corrected;a=r['argv'];field=lambda k:a[a.index(k)+1]
assert module.OWNER_PATH==o.SELF==r['command_source']['path'] and r['command_source']['sha256']==sha(Path(o.SELF).read_bytes())
assert module.HOST_PARENT==g.HOST_OUTPUT['parent']==field('--attempt-parent') and module.NONCE==field('--nonce')
assert module.MANIFEST_PATH==field('--manifest') and module.MANIFEST_SHA==field('--manifest-sha256') and module.RELEASE_PATH==r['long_profile_release']['path']==field('--long-profile-release')
assert r['wrapper_sha256']==g.EXTERNAL_CAPTURE_BINDING['controller_sha256']==sha((D/'capture_root_LONG.NOT-RELEASED.py').read_bytes()) and g.EXTERNAL_CAPTURE_BINDING['controller_path']==str(D/'capture_root_LONG.NOT-RELEASED.py') and g.EXTERNAL_CAPTURE_BINDING['request_path']==str(D/'CAPTURE-REQUEST.json') and g.EXTERNAL_CAPTURE_BINDING['capture_directory']==r['capture_directory']
d,m=o.bound_manifest(module.MANIFEST_PATH,module.MANIFEST_SHA);assert m['pair_long_session']==g.PROFILE and len(o.SOURCE_HASHES)==156
checks.append(dict(name='actual_full_bound_manifest_156_and_controller_transport_owner_request_matrix',status='PASS',readonly_roots=len(o.EXTRA_READONLY)))
assert not factory_calls and not (D/'actual-capture-1').exists()
report=dict(scope=__doc__,status='PASS_ACTUAL_CONTROLLER_PRE_EFFECT_GUARDS_NOT_ROOTPROFILE_PROOF',interpreter=sys.executable,version=sys.version,checks=checks,check_count=len(checks),privileged_environment_scaffolding=dict(os=['getuid=0','geteuid=0','sched_getaffinity={7}'],resource=['FSIZE384MiB','CPUunlimited'],qualification='All three actual environment needstatements evaluated with explicitTESTONLY values. No actual root/profile qualification claimed. All functional/source/path/argv/capture guards run unmodified.'),actual_main_prefix_AST_identical=True,boundary='Immediatelybefore out.mkdir; both mkdir and Popen unreachable',process_factory_calls=0,capture_directories_created=0,root=0,Docker=0,workload=0,source_cohort=156,final_release_actual_realclock_validation=None,root_execution_release=None,native_acceptance=False)
(D/'ACTUAL-CONTROLLER-GUARD-RESULT.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
