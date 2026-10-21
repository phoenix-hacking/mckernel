"""One genuine-shape current PASS adapter check; no root/Docker/locks or engine import."""
import ast,base64,copy,hashlib,io,json,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={'engine': {'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/current-pass-terminal-preparation-2/cleanup_pass_image.py', 'sha256': '2d632211c533702380624863194b8514ebd973d3ebf495ed4f9a97c26d44cf2d', 'bytes': 90336}, 'observer': {'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/current-pass-terminal-preparation-2/observe_current_pass_image_retirement.py', 'sha256': '8074a624fca2eb8d01263a9fb68cba2ecd12d06e88334591218da3139bbc434c', 'bytes': 24326}, 'physical': {'bytes': 18453, 'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/independent-review-1/actual-four-overlay-image-retained-physical-1.json', 'sha256': '1d472d0c4edd3b8f6ae97e37dc50eb33dc49b72503bc6e65a0f8618395c8b72c'}, 'postjoin': {'bytes': 542, 'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/owned-fork-pin-successor-1/coupled-current-pin-correction-1/control-successor-1/image-guard-postjoin-readback.json', 'sha256': '27e3e5a1859d810e7244a2173723f3c7dea616dd88d90176f55b711a47f59efe'}, 'case': {'path': '/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/current-pass-terminal-preparation-2/PASS-CASE-STATIC.json', 'sha256': '3eef848ced53fa669314b1366c8d418ad93ca666fbad60076c1b1c940ef54778', 'bytes': 57744}, 'base_engine': {'path': '/home/holden/mckernel-work/host-preparation/phase5-current-pass-image-terminal-20261020-1/cleanup_pass_image.py', 'sha256': 'fdaacfcf2f4875a3e70d06a30dd109a7d603b59ecababce3a1d02863f50fa305', 'bytes': 87190}}
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
 physical=json.loads(read('physical'));case=json.loads(read('case'));post=json.loads(read('postjoin'))
 validate(physical,case,post)
 refused=[]
 def negative(label,p,c,j):
  try:validate(p,c,j)
  except (RuntimeError,KeyError,TypeError):refused.append(label)
  else:raise AssertionError('accepted mismatch/omission:'+label)
 for key in ('container_id','owner_nonce','owner_pid','owner_starttime'):
  p=copy.deepcopy(physical);p[key]='wrong';negative(key,p,case,post)
 for key in ('owner_receipt','guard_result','outer_status','driver_receipt'):
  p=copy.deepcopy(physical);p[key]['sha256']='0'*64;negative(key,p,case,post)
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
   text=ast.unparse(a).replace('native-rust-phase5-current-optin-image-guard-744f4822e8314fada135e4092549787c','native-rust-phase5-current-optin-image-guard-b5f6072d372546c0997a27d33741e2e6');assert text==ast.unparse(b)
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
