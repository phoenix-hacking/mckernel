from pathlib import Path
import ast,copy,hashlib,json,os,shutil,stat,time,types
R=Path(__file__).resolve().parent
owner_tree=ast.parse((R/'launcher_only_container_owner.py').read_text())
# Execute the WHOLE actual terminal consumer plus its actual path/hash/error
# helpers. No condition, path check or expected source result is mocked.
names={'_fail','_sha256','_safe_regular','_safe_directory','_no_symlink_parents','_validate_driver_result'}
selected=[n for n in owner_tree.body if (isinstance(n,ast.ClassDef) and n.name=='OwnerError') or (isinstance(n,ast.FunctionDef) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXPECTED_LAUNCHER_SOURCE_AUTHORITY' for t in n.targets))]
assert len(selected)==8
scope={'Path':Path,'hashlib':hashlib,'os':os,'stat':stat};exec(compile(ast.Module(body=selected,type_ignores=[]),str(R/'launcher_only_container_owner.py'),'exec'),scope)
consumer=scope['_validate_driver_result'];OwnerError=scope['OwnerError']
prior_ref=json.loads((R/'PRIOR-RECEIPT-REFERENCE.json').read_text());prior_path=Path(prior_ref['path']);data=prior_path.read_bytes();assert hashlib.sha256(data).hexdigest()==prior_ref['sha256']
prior=json.loads(data);unit=R/'unit-result-fixture';evidence=unit/'evidence';output=unit/'output';evidence.mkdir(parents=True);output.mkdir()
# Prior real receipts name container paths; recreate those SAME relative
# output/evidence members under the private host fixture namespace.
for rel in prior['inventory']:
 src=prior_path.parent/rel;dst=evidence/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for name,row in prior['artifacts'].items():
 rel=Path(row['path']).relative_to('/work/output');dst=output/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(evidence/'artifacts'/name,dst)
# New-source/symbol descriptors in this file are UNIT FIXTURES ONLY. The
# underlying retained artifact bytes are old da71, never current990 artifacts.
fixture=copy.deepcopy(prior)
offline_tree=ast.parse((R/'launcher_only_offline.py').read_text());run=next(n for n in offline_tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
constant=next(n for n in offline_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NEW_SOURCE_SHA' for t in n.targets));source_env={};exec(compile(ast.Module(body=[constant],type_ignores=[]),'<actual producer source pin>','exec'),source_env)
initializer=next(n for n in run.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets))
field=next(k.value for k in initializer.value.keywords if k.arg=='launcher_source_sha256')
fixture['launcher_source_sha256']=eval(compile(ast.Expression(field),'<actual producer receipt source expression>','eval'),source_env)
assert fixture['launcher_source_sha256']==scope['EXPECTED_LAUNCHER_SOURCE_AUTHORITY']['source_override']
# Run the exact production success descriptor update and evidence-inventory
# statement to make the final producer receipt shape consumed below.
update=next(n for n in ast.walk(run) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='result' and n.value.func.attr=='update' and any(k.arg=='source_change' for k in n.value.keywords))
producer_env={'result':fixture,'needed':prior['needed'],'time':time,'evidence':evidence,'base':types.SimpleNamespace(_sha256=scope['_sha256'])}
exec(compile(ast.Module(body=[update],type_ignores=[]),'<actual producer success descriptor>','exec'),producer_env)
inventory=next(n for n in ast.walk(run) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='result' and isinstance(t.slice,ast.Constant) and t.slice.value=='inventory' for t in n.targets))
exec(compile(ast.Module(body=[inventory],type_ignores=[]),'<actual producer evidence inventory>','exec'),producer_env)
request={k:prior[k] for k in ['candidate_sha','ihk_sha','source_manifest_sha256','toolchain_manifest_sha256']}
(evidence/'receipt.json').write_text(json.dumps(fixture,indent=2)+'\n')
consumer(evidence,output,fixture,request)
results=['actual-producer990-whole-consumer-positive']
for name,alter,expected in [
 ('old-da71',lambda d:d.update(launcher_source_sha256=prior['launcher_source_sha256']),'actual launcher target/source/providers'),
 ('unknown-source',lambda d:d.update(launcher_source_sha256='0'*64),'actual launcher target/source/providers'),
 ('failed-owner-result',lambda d:d.update(status='FAIL'),'truthful launcher-only receipt required'),
 ('false-image-claim',lambda d:d.update(kernel_rebuilt=True),'truthful launcher-only receipt required'),
 ('changed-candidate',lambda d:d.update(candidate_sha='0'*40),'accepted base/toolchain provenance'),
 ('changed-command',lambda d:d['commands'][0].update(exit_code=1),'single actual production target command'),
 ('missing-inventory-member',lambda d:d['inventory'].pop('linked-symbols.txt'),'driver evidence inventory is incomplete or has unexpected members'),
 ('artifact-path-drift',lambda d:d['artifacts']['mcexec'].update(path='/work/output/build/other'),'launcher artifact byte/path binding mcexec'),
]:
 value=copy.deepcopy(fixture);alter(value)
 try:consumer(evidence,output,value,request)
 except OwnerError as error:assert expected in str(error),(name,str(error));results.append(name+'-refused')
 else:raise AssertionError(name+' incorrectly admitted')
assert len(results)==9
# Audit only the coupled new source postimage consumers in this exact pair.
old_tree=ast.parse((R.parent/'launcher_only_container_owner.py').read_text())
oldconsumer=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_driver_result')
assert any(isinstance(n,ast.Constant) and n.value==prior['launcher_source_sha256'] for n in ast.walk(oldconsumer))
newconsumer=next(n for n in owner_tree.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_driver_result')
assert not any(isinstance(n,ast.Constant) and n.value==prior['launcher_source_sha256'] for n in ast.walk(newconsumer))
owner_run=next(n for n in owner_tree.body if isinstance(n,ast.ClassDef) and n.name=='ImageOwner')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_validate_driver_result' for n in ast.walk(owner_run))
assert (R/'launcher_only_offline.py').read_bytes()==(R.parent/'launcher_only_offline.py').read_bytes()
result={'status':'PASS_ACTUAL_PRODUCER_DESCRIPTOR_TO_WHOLE_TERMINAL_CONSUMER','checks':results,'unit_fixture_only':True,'fixture_artifact_bytes':'genuine PRIOR da71 artifacts; not current990 native/build artifacts','actual_producer_nodes_executed':['launcher_source_sha256 field','PASS target/sourcechange/provider descriptor update','complete evidence inventory construction'],'actual_consumer':'WHOLE _validate_driver_result with actual path/hash/error helpers, no condition mocks','prior_receipt':prior_ref,'production_build':False,'native_acceptance':False}
(R/'terminal-consumer-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS 9 whole terminal-consumer checks; actual producer descriptor/inventory; UNIT FIXTURE ONLY')
