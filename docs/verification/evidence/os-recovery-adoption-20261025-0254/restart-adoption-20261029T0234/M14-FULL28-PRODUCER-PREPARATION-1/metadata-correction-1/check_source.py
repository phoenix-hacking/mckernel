"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure producer data/AST tests; no guard/worker/container/compiler/native call.
"""
from pathlib import Path
import ast,copy,hashlib,json
D=Path(__file__).parent
read=lambda p:json.loads(Path(p).read_text())
recipe=read(D/'FOUR-COMMANDS.SOURCE-ONLY.json');snapshot=read(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json');bases=read(D/'REUSED-PRODUCER-BASES.json')
assert recipe['candidate']['sha256']=='8b738728d75f7df09c99629711a02c0107a21af42392eb2f1968861729097d0c'
assert recipe['uti_owner']['sha256'].startswith('38ac0893')
for row in snapshot['entries']:
 p=Path(row['source']['path']);b=p.read_bytes();assert len(b)==row['source']['bytes'] and hashlib.sha256(b).hexdigest()==row['source']['sha256']
assert len(snapshot['entries'])==166 and snapshot['source_files']==166 and snapshot['rust_files']==155
assert len({x['relative']for x in snapshot['entries']})==166
oldprofile=read(bases['source3_profile']['path']);original4=read(bases['original4_recipe']['path'])
assert snapshot['external_relative_modules']==oldprofile['inputs']['external_relative_modules'] and len(snapshot['external_relative_modules'])==3
for row in snapshot['external_relative_modules']:
 p=Path(row['source']['path']);b=p.read_bytes();assert len(b)==row['source']['bytes']and hashlib.sha256(b).hexdigest()==row['source']['sha256']
assert len(recipe['ordered_commands'])==4 and len(recipe['retained_inputs'])==8 and len(recipe['replacement_objects'])==3
for key in ['argv','cwd','new_output']:
 assert recipe['ordered_commands'][3][key]==oldprofile['exact_commands'][2][key]==original4['ordered_commands'][3][key]
assert [x['id']for x in recipe['ordered_commands']]==['0','1','2','3']
canonical=lambda argv:hashlib.sha256((json.dumps(argv,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')).hexdigest()
assert all(canonical(x['argv'])==x['argv_sha256']for x in recipe['ordered_commands'])
assert all(canonical(x['argv'])==x['argv_sha256']for x in original4['ordered_commands'])
# The original failed recipe's executable argv/cwd/outputs remain exact.
failed=read(D.parent/'FOUR-COMMANDS.SOURCE-ONLY.json')
assert all(all(a[k]==b[k]for k in ['argv','cwd','new_output'])for a,b in zip(recipe['ordered_commands'],failed['ordered_commands']))
assert all(not r['link_token'].endswith('arch/x86_64/kernel/syscall.c.o')for r in recipe['retained_inputs'])
assert recipe['C_ABI_probe_link_inputs']==[]
for i,base in [(0,oldprofile['exact_commands'][0]),(1,oldprofile['exact_commands'][1]),(2,original4['ordered_commands'][2])]:
 argv=iter(recipe['ordered_commands'][i]['argv'])
 assert all(any(x==token for x in argv)for token in base['argv']),'original exact compiler argv retained as ordered subsequence'
 assert recipe['ordered_commands'][i]['cwd']==base['cwd']and recipe['ordered_commands'][i]['new_output']==base['new_output']
old=Path(bases['source3_runner']['path']).read_text();new=(D/'run_build_only.template.py').read_text()
def segment(s,name):
 n=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef)and x.name==name)
 return ast.dump(n,include_attributes=False)
operation_names=['resource_guards','mounts','docker_prefix','docker_argv','current_operation_guard','execute']
for name in operation_names:assert segment(old,name)==segment(new,name),'operational body changed:'+name
assert (D/'build_only_worker.template.py').read_bytes()==Path(bases['original4_worker']['path']).read_bytes()
assert 'len(manifest[\'files\'])==166' in new and '==155' in new
# Consume ONLY the pure command-plan validator AST, with clearly synthetic
# request/source wrappers. No actual guard/sealer or provider is imported/called.
fn=next(x for x in ast.parse(new).body if isinstance(x,ast.FunctionDef)and x.name=='commands_for_plan')
mod=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(mod)
def require(ok,msg):
 if not ok:raise ValueError(msg)
ns={'hashlib':hashlib,'json':json,'require':require,'read':lambda _:recipe,'auth':lambda _:None,'COMMAND_RECIPE_REF':{},'source_directory_postimages':lambda p:p['_closed_rows']}
exec(compile(mod,'<pure-command-plan-AST>','exec'),ns)
objects=[dict(r,replace=False)for r in recipe['retained_inputs']]+[dict(link_token=t,replace=True)for t in recipe['replacement_objects']]
post=[dict(relative='kernel/syscall.c',postimage={'synthetic':1}),dict(relative='arch/x86_64/kernel/syscall.c',postimage={'synthetic':2})]
closed=[dict(relative='kernel/rust/lib.rs',postimage={'synthetic':3})]
p={'request_sha256':'a'*64,'inputs':{'postimages':post,'objects':objects},'cohort_source_bindings':post+closed,'_closed_rows':closed,'reuse_descriptor':'/not-an-authority','producer_contract':{'process_delta':'eight unchanged object refs; new full Rust/generic/arch objects'},'exact_commands':copy.deepcopy(recipe['ordered_commands'])}
assert ns['commands_for_plan'](p)==recipe['ordered_commands']
mutations=[]
def reject(name,change):
 q=copy.deepcopy(p);change(q)
 try:ns['commands_for_plan'](q)
 except (ValueError,KeyError):mutations.append(name)
 else:raise AssertionError('mutation accepted:'+name)
reject('Rust argv drift',lambda q:q['exact_commands'][0]['argv'].append('--bad'))
reject('arch argv drift',lambda q:q['exact_commands'][2]['argv'].append('--bad'))
reject('arch incorrectly retained',lambda q:next(x for x in q['inputs']['objects']if x['link_token'].endswith('arch/x86_64/kernel/syscall.c.o')).update(replace=False,source={'sha256':'0'*64}))
reject('missing third replacement',lambda q:q['inputs']['objects'].pop())
reject('changed raw-link order',lambda q:q['exact_commands'][3]['argv'].reverse())
reject('source closure binding drift',lambda q:q['cohort_source_bindings'].pop())
reject('stale argv hash',lambda q:q['exact_commands'][2].update(argv_sha256='0'*64))
reject('duplicate command id',lambda q:q['exact_commands'][3].update(id='2'))
params=read(D/'ROOT-CURRENT-FRONTIER.PARAMETERS.NOT-AUTHORITY.json')
for x in ['nonce','current_free','current_ledger','current_boundary','independent_current_frontier_review','current_bindings','runtime_guard','cutoffs','actual_source_snapshot_manifest']:assert params[x]is None
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_FULL28_FOUR_COMMAND_SOURCE_DATA_ONLY','candidate_sha256':recipe['candidate']['sha256'],'closed_source_files':166,'rust_files':155,'external_modules_authenticated':3,'four_exact_commands':True,'eight_retained_three_replaced':True,'original_raw_link_order':True,'C_ABI_probe_objects_excluded':True,'unchanged_operational_guard_bodies':operation_names,'original119_four_worker_exact':True,'pure_command_validator_positive':True,'negative_plan_mutations_rejected':mutations,'fresh_actual74_frontier_parameters_unbound':True,'actual_guard_sealer_export_compiler_native':False,'runtime_authority':None,'canonical_argv_hashes_and_ordered_ids':True,'unchanged_executable_argv_from_retained_failure':True}
(D/'PURE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
