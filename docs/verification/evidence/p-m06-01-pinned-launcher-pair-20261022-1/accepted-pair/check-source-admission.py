from pathlib import Path
import ast,copy,hashlib,json
R=Path(__file__).resolve().parent
plan=json.loads((R/'launcher-plan.json').read_text())
paths=[Path(plan[k]['path']) for k in ['source_override','original_source','reviewed_preimage','source_patch','source_review']]
results=[]
for name in ['launcher_only_offline.py','launcher_only_container_owner.py']:
 tree=ast.parse((R/name).read_text());before=ast.parse((R/'before'/name).read_text())
 # Compile/exercise the actual new admission function, without importing any
 # host owner, heavy contract or toolchain modules and without calling run().
 selected=[n for n in tree.body if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXPECTED_LAUNCHER_SOURCE_AUTHORITY' for t in n.targets)) or (isinstance(n,ast.FunctionDef) and n.name=='_validate_launcher_source')]
 assert len(selected)==2
 env={'Path':Path,'hashlib':hashlib,'json':json};exec(compile(ast.Module(body=selected,type_ignores=[]),str(R/name),'exec'),env)
 guard=env['_validate_launcher_source'];assert guard(plan,*paths)==plan['source_override']['sha256'];results.append(name+':exact-reviewed-positive')
 for case,index,key in [('changed-source',0,'source_override'),('unknown-patch',3,'source_patch'),('unknown-review',4,'source_review')]:
  altered=R/'test-inputs'/(name+'-'+case);altered.parent.mkdir(exist_ok=True);altered.write_bytes(paths[index].read_bytes()+b'\nchanged\n')
  p=copy.deepcopy(plan);data=altered.read_bytes();p[key]={'path':str(altered),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  args=list(paths);args[index]=altered
  try:guard(p,*args)
  except RuntimeError as error:
   assert 'unreviewed launcher source authority' in str(error);results.append(name+':'+case+'-refused')
  else:raise AssertionError(case+' admitted')
 changed={'_validate_launcher_source','run'} if name=='launcher_only_offline.py' else {'_validate_launcher_source','_validate_launcher_additions','_validate_driver_result','run'}
 def functions(t):
  out={}
  for n in t.body:
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):out[n.name]=n
   elif isinstance(n,ast.ClassDef):
    for m in n.body:
     if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)):out[n.name+'.'+m.name]=m
  return out
 old=functions(before);new=functions(tree)
 for fn,node in old.items():
  if fn.split('.')[-1] not in changed:assert ast.dump(node)==ast.dump(new[fn]),fn+' unrelated function changed'
 consumer=functions(tree)['run' if name=='launcher_only_offline.py' else '_validate_launcher_additions']
 assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_validate_launcher_source' for n in ast.walk(consumer))
 if name=='launcher_only_container_owner.py':
  text=(R/name).read_text();offline=hashlib.sha256((R/'launcher_only_offline.py').read_bytes()).hexdigest()
  assert "EXPECTED_DRIVER_SHA256 = '"+offline+"'" in text
  for mount in ['/launcher-preimage.rs','/launcher-patch.diff','/launcher-review.json']:assert mount in text
  for authority in ['acquire_heavy_operation','_revalidate_inputs(bound, r)','--network=none','--read-only','with Signals() as signals:','terminal_container_retained','inventory']:
   assert authority in text and authority in (R/'before'/name).read_text(),authority
assert len(results)==8
(R/'source-admission-result.json').write_text(json.dumps({'status':'PASS_EXACT_REVIEWED_SOURCE_ADMISSION_PAIR','checks':results,'unrelated_function_ASTs_preserved':True,'production_build_run':False,'native_acceptance':False},indent=2)+'\n')
print('PASS 8 actual source-admission checks; pairedpin/mounts/callerjoins; unrelated function ASTs preserved')
