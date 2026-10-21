"""One genuine-shape current PASS adapter check; no root/Docker/locks or engine import."""
import ast,base64,copy,hashlib,io,json,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS = {'engine': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/cleanup_pass_image.py', 'sha256': '25e8657a301c6d486833de7bf8f6cdd7ebc360d9930a997809b3089b16551633', 'bytes': 88292}, 'observer': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/observe_current_pass_image_retirement.py', 'sha256': '41a187650605a312ff2710a359f236cf6b9c3d5e90f06efd2f442c038e26a8c1', 'bytes': 25439}, 'physical': {'bytes': 6332, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/independent-runtime-binding-review-1/ROOT-RECORDED-INDEPENDENT-CURRENT-IMAGE-RETAINED-PHYSICAL-ACCEPTANCE.json', 'sha256': '3351eefc3df372220d7a32c20932fa20f8143d466786f0d21bcb1d6e400e1b3f'}, 'postjoin': {'bytes': 542, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/execution-preparation-1/image-guard-postjoin-readback.json', 'sha256': '510cf681e6a3678a10c25f229a4bbeede676e18c2868ea6ddf872886bf998f5a'}, 'case': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/PASS-CASE-STATIC.json', 'sha256': '6422685923bf3c6bac434c47a5771ecdaec491656d0c2e402866170da6e906ca', 'bytes': 55898}, 'base_engine': {'bytes': 90336, 'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/current-pass-terminal-preparation-2/cleanup_pass_image.py', 'sha256': '2d632211c533702380624863194b8514ebd973d3ebf495ed4f9a97c26d44cf2d'}, 'artifact': {'bytes': 8699, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/independent-runtime-binding-review-1/ROOT-RECORDED-CANONICAL-ARTIFACT-SCHEMA-PROJECTION-1.json', 'sha256': '84bfc043987fc67444e627bef142b2ddaf6c19107d92ba307d50ee10fa157edd'}}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(name):
 p=Path(PINS[name]['path']);b=p.read_bytes();assert sha(b)==PINS[name]['sha256'];return b

def function(source,name,namespace):
 t=ast.parse(source);n=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[n],type_ignores=[]),'<actual-whole-function:'+name+'>','exec'),namespace)
 return namespace[name]

def main():
 obs=read('observer').decode();engine=read('engine').decode()
 # Execute precisely the production adapter body, with the actual immutable JSON inputs.
 tree=ast.parse(obs);namespace={}
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('BOOT','CURRENT_EXPECTED_SOURCE') for t in node.targets):
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-observer-constants>','exec'),namespace)
 def need(ok,reason):
  if not ok:raise RuntimeError(reason)
 namespace['need']=need;validate=function(obs,'current_pass_prerequisites',namespace)
 physical=json.loads(read('physical'));case=json.loads(read('case'));post=json.loads(read('postjoin'));artifact=json.loads(read('artifact'))
 validate(physical,case,post,artifact)
 refused=[]
 def negative(label,p,c,j,a=None):
  try:validate(p,c,j,artifact if a is None else a)
  except (RuntimeError,KeyError,TypeError):refused.append(label)
  else:raise AssertionError('accepted mismatch/omission:'+label)
 for key in ('container_id','owner_nonce','owner_pid','owner_starttime'):
  p=copy.deepcopy(physical);p[key]='wrong';negative(key,p,case,post)
 for key in ('owner_receipt','guard_result','outer_status','inner_status','terminal_fresh_inspect'):
  p=copy.deepcopy(physical);p[key]['sha256']='0'*64;negative(key,p,case,post)
 # Genuine producer authority is separate from physical retention authority.
 a=copy.deepcopy(artifact);a['producer_receipt']['sha256']='0'*64;negative('artifact:producer_receipt',physical,case,post,a)
 for key in ('schema','status','decision','reviewer','implementation_ownership','physical_clearance','source_derivative_sha256','materialization_sha256','producer_receipt'):
  a=copy.deepcopy(artifact);del a[key];negative('artifact:omitted:'+key,physical,case,post,a)
 for key,value in [('schema','wrong'),('status','FAIL'),('decision','wrong'),('reviewer',''),('implementation_ownership',True),('physical_clearance',True),('source_derivative_sha256','0'*64),('materialization_sha256','0'*64)]:
  a=copy.deepcopy(artifact);a[key]=value;negative('artifact:changed:'+key,physical,case,post,a)
 c=copy.deepcopy(case);c['artifact_acceptance']['sha256']='0'*64;negative('case:artifact_ref',physical,c,post)
 c=copy.deepcopy(case);del c['artifact_acceptance'];negative('case:artifact_ref_omitted',physical,c,post)
 for key in ('root27_4_reacquired_after_join','guard_direct_joined','common_shared_and_container_retained_for_separate_cleanup'):
  j=copy.deepcopy(post);del j[key];negative('omitted:'+key,physical,case,j)
 for role in ('common','shared'):
  for field in ('inode','sha256','size','device','mode','uid','gid','nlink'):
   p=copy.deepcopy(physical);p['retained_ownership'][role][field]='wrong';negative(role+':'+field,p,case,post)
 c=copy.deepcopy(case);c['source_identity']['source_derivative_sha256']='0'*64;negative('source',physical,c,post)
 # The genuine old whole transaction/preflight/census bodies remain byte-for-byte AST identical.
 base=read('base_engine').decode();left=ast.parse(base);right=ast.parse(engine)
 for name in ('Transaction','protected_files','configure','census','recover'):
  a=next(n for n in left.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
  b=next(n for n in right.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
  # configure contains only the exact current guard-capture literal amendment.
  if name=='configure':
   text=ast.unparse(a).replace('native-rust-phase5-current-optin-image-guard-b5f6072d372546c0997a27d33741e2e6','native-rust-phase5-current-optin-image-guard-d37f2175c1c049869e4a5872de864858');assert text==ast.unparse(b)
  else:assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name
 # Whole root_command actual body; completed-child fixtures never launch any process.
 class Refusal(ValueError):pass
 result=types.SimpleNamespace(returncode=0,stdout=b'actual-safe-output',stderr=b'')
 process=types.SimpleNamespace(DEVNULL=-3,PIPE=-1,run=lambda *a,**k:result)
 stderr=io.StringIO();ns=dict(os=types.SimpleNamespace(geteuid=lambda:0),subprocess=process,Refusal=Refusal,base64=base64,json=json,sys=types.SimpleNamespace(stderr=stderr),digest=sha)
 command=function(engine,'root_command',ns);assert command(['/usr/bin/docker','fixture'],100)==result.stdout
 diagnostics=[]
 for label,rc,stdout,err,limit in [('nonzero',1,b'',b'error',100),('stderr',0,b'',b'x'*70000,100),('cap',0,b'0123',b'',1)]:
  result.returncode=rc;result.stdout=stdout;result.stderr=err;stderr.seek(0);stderr.truncate(0)
  try:command(['/usr/bin/docker','fixture'],limit)
  except Refusal:pass
  else:raise AssertionError(label)
  row=json.loads(stderr.getvalue());assert row['returncode']==rc and row['stderr']['bytes']==len(err) and len(row['stderr'].get('base64',''))<=87384;diagnostics.append(label)
 # Whole capture_logs body reads genuine retained dual channels and container.log via in-memory provider.
 channels={str(v['path']):Path(v['path']).read_bytes() for v in case['log_channels'].values()}
 expected=Path(case['finite_roles']['container_log']['path']).read_bytes();assert expected==channels[case['log_channels']['stdout']['path']]
 def bounded(p,maximum):
  raw=expected if str(p)==case['finite_roles']['container_log']['path'] else channels[str(p)]
  assert len(raw)<=maximum;return raw
 ns=dict(PASS_LOG_CHANNELS=case['log_channels'],Path=Path,PROTECTED_LIMIT=128<<20,read_bounded=bounded,digest=sha,Refusal=Refusal,EVIDENCE=Path(case['finite_roles']['owner_receipt']['path']).parent,CAPTURE=Path('/uncreated-fixture-only'),os=types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda p:False)),run_privileged_large=lambda argv:expected,CONTAINER=case['target']['container_id'])
 capture=function(engine,'capture_logs',ns);capture(True,False)
 for channel in ('stdout','stderr'):
  path=case['log_channels'][channel]['path'];saved=channels[path];channels[path]=saved+b'x'
  try:capture(True,False)
  except Refusal:pass
  else:raise AssertionError('log channel drift accepted')
  channels[path]=saved
 print(json.dumps(dict(status='PASS_ACTUAL_CURRENT_PASS_ADAPTER_AND_LOG_BODIES_ONLY',positive_genuine_shape=True,refusal_count=len(refused),refusals=refused,completed_child_refusals=diagnostics,both_actual_log_channels_checked=True,cleanup_executed=False,root_actions=False,engine_imported=False,physical_release=False),sort_keys=True))
if __name__=='__main__':main()
