"""No-effect exact authentication-prefix regression on the genuine failed release.
No synthetic execution review, mount command, locks, owner, Docker or effects.
The original SOURCE closure remains used for genuine predecessor crossrefs;
new successor source/release/canonical authority requires separate final review.
"""
import ast,copy,hashlib,json,os,pathlib,re
G=pathlib.Path(__file__).resolve().parent.parent
old=G/'native_exact_current_optin_image_guard.py';new=pathlib.Path(__file__).with_name(old.name)
d=json.loads((G/'image-execution-release.json').read_text());qpath=pathlib.Path(d['request']['path'])
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def bound(r):
 b=pathlib.Path(r['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'];assert 'bytes' not in r or len(b)==r['bytes'];return json.loads(b)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
base=ast.parse(old.read_text());updated=ast.parse(new.read_text())
ns={'os':os,'Path':pathlib.Path,'hashlib':hashlib,'json':json,'re':re,'bound':bound,'digest':digest,'canonical':canonical}
for x in base.body:
 if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ROOT','CANDIDATE','UUID','REPO','SOURCES') for t in x.targets):exec(compile(ast.Module(body=[x],type_ignores=[]),str(old),'exec'),ns)
for tree in (base,updated):
 for x in tree.body:
  if isinstance(x,ast.FunctionDef) and x.name=='require_actual_ordinary':exec(compile(ast.Module(body=[x],type_ignores=[]),str(old),'exec'),ns)
 def extracted():
  fn=copy.deepcopy(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='authenticate'))
  i=next(i for i,x in enumerate(fn.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mounted' for t in x.targets))
  fn.body=fn.body[:i]+[ast.Return(value=ast.Tuple(elts=[ast.Name(id='request',ctx=ast.Load()),ast.Name(id='release',ctx=ast.Load())],ctx=ast.Load()))]
  ast.fix_missing_locations(fn);exec(compile(ast.Module(body=[fn],type_ignores=[]),str(old),'exec'),ns);return ns['authenticate']
 fn=extracted();args=(qpath,d['request']['sha256'],G/'image-execution-release.json',digest(G/'image-execution-release.json'))
 if tree is base:
  try:fn(*args)
  except RuntimeError as e:assert str(e)=='fresh exact authority3 image release required'
  else:raise AssertionError('stale literal accepted')
 else:
  request,release=fn(*args)
  # Isolated negative: actual request map copy changed in memory, never published.
  original_bound=ns['bound']
  for field in ('source_derivative_sha256','materialization_sha256'):
   def wrong(r):
    value=original_bound(r)
    if r['path']==str(qpath):value[field]='0'*64
    return value
   ns['bound']=wrong
   try:fn(*args)
   except RuntimeError as e:assert str(e)=='fresh exact authority3 image release required'
   else:raise AssertionError('wrong source identity accepted: '+field)
   ns['bound']=original_bound
result={'status':'PASS_ACTUAL_AUTHENTICATION_STATIC_PREFIX_ONLY','observed_old_release_rejected':True,'corrected_exact_pins_accept_all_original_static_authority_and_source_crossrefs':True,'wrong_derivative_refused':True,'wrong_materialization_refused':True,'projection_ends_before_live_findmnt_and_nonce_capture_check':True,'old_release_not_runnable_or_reused':True,'synthetic_approval_created':False,'owner_run_or_Docker_or_lock_or_measurement':False}
p=pathlib.Path(__file__).with_name('ACTUAL-AUTHENTICATION-PREFIX-RESULT.json')
with p.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(result))
