"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse the accepted finite materializer and controller/static-request derivation.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1')
B=H/'production-combined-4/default-image-successor-1';N=H/'production-combined-5/default-image-successor-1';S=N/'source-materialization-attempt-1'
OLD=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-4/default-image-successor-1'
AUTH=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/CANONICAL-INTEGRATION.json'
POST={'kernel/mem.c':'bac5d4fb766b5cb80e036457465e215743a1cb31622ff11c5b5b605749f3d7fe','kernel/rust/page_helpers.rs':'cfc64f72bf9b94c65417bc8f4e29d65b81f98239fe52ab2a7dd0352ebdfc3f70'}
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def write(p,b):
 with p.open('xb') as f:f.write(b)
def save(name,v):write(E/name,(json.dumps(v,indent=2,sort_keys=True)+'\n').encode())
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n)
 return s.replace(a,b)
def controller(name,s,old):
 ast.parse(s);write(N/name,s.encode());write(E/name,s.encode())
 write(E/(name+'.diff'),''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=str(B/name),tofile=str(N/name))).encode())
 return ref(N/name)
def main():
 oldmanifest=B/'source-materialization-attempt-1/source-inputs.json';raw=oldmanifest.read_bytes();base=json.loads(raw);assert sha(raw)==sha(canonical(base))=='802f963e8f3ec1c47f98c5f3440b8a132f5b0fa617dd2e014976c63d78870073'
 authority=json.loads(AUTH.read_text());assert authority['status']=='CANONICAL_TWO_FILE_SOURCE_INTEGRATION_ONLY' and {x['path']:x['postimage_sha256'] for x in authority['integrated']}==POST
 doc=copy.deepcopy(base);delta=[]
 for p,h in POST.items():
  assert ref(R/p)['sha256']==h;delta.append(dict(path=p,before_sha256=base['repository_files'][p],after_sha256=h));doc['repository_files'][p]=doc['materialized_repository_files'][p]=h
 derivation=dict(base_manifest_canonical_sha256=sha(raw),base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
 doc['source_derivative_sha256']=sha(canonical(derivation));doc['latest_memory_callback_overlay']=derivation
 mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canonical(mat));mh=sha(canonical(doc))
 assert {p for p in base['repository_files'] if base['repository_files'][p]!=doc['repository_files'][p]}==set(POST)
 # Only constants and the exact accepted authority schema advance; copy/hash loop is retained.
 materializer=(OLD/'materialize_source.py').read_text();tree=ast.parse(materializer);lines=materializer.splitlines(True)
 values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(sha(raw)),'POST':repr(POST)}
 for node in reversed(tree.body):
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   name=node.targets[0].id;lines[node.lineno-1:node.end_lineno]=[name+' = '+values[name]+'\n']
 materializer=''.join(lines);materializer=replace(materializer,"authority['status'] == 'PASS_SOURCE_INTEGRATED' and authority['postimages'] == POST","authority['status'] == 'CANONICAL_TWO_FILE_SOURCE_INTEGRATION_ONLY' and {row['path']:row['postimage_sha256'] for row in authority['integrated']} == POST")
 ast.parse(materializer);write(E/'materialize_source.py',materializer.encode())
 old=json.loads((OLD/'ACTUAL-CANDIDATE.json').read_text());pins=old['production_sources'];sources={}
 name='native_rust_exact_build_offline.py';rawtext=Path(pins[name]['path']).read_text();assert sha(rawtext.encode())==pins[name]['sha256'];sources[name]=controller(name,replace(rawtext,sha(raw),mh),rawtext)
 name='native_rust_exact_mckernel_image_offline.py';rawtext=Path(pins[name]['path']).read_text();assert sha(rawtext.encode())==pins[name]['sha256'];text=replace(rawtext,pins['native_rust_exact_build_offline.py']['sha256'],sources['native_rust_exact_build_offline.py']['sha256'])
 anchor='M14_SOURCE_PINS = {\n';text=replace(text,anchor,anchor+''.join('    '+repr(p)+': '+repr(h)+',\n' for p,h in POST.items()))
 text=replace(text,"M14_RUST_EXPORTS = M14_IDLE_IMPORTS + M14_MEMORY_IMPORTS + (","M14_RUST_EXPORTS = M14_IDLE_IMPORTS + M14_MEMORY_IMPORTS + ('page_unmap',) + (")
 extension=(E/'page_unmap_checks.inc.py').read_text();text=replace(text,'def _validate_m14_source_pins(source_root):',extension+'\n\ndef _validate_m14_source_pins(source_root):')
 anchor="    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',"
 text=replace(text,anchor,"    page_unmap_proof = _validate_m14_page_unmap_contract(source_root, build, tools, env, timeout, command_rows, objects)\n"+anchor)
 text=replace(text,'        source_pins=M14_SOURCE_PINS, objects=objects, idle_imports=M14_IDLE_IMPORTS,','        source_pins=M14_SOURCE_PINS, objects=objects, page_unmap_public_contract=page_unmap_proof, idle_imports=M14_IDLE_IMPORTS,')
 sources[name]=controller(name,text,rawtext)
 name='native_rust_exact_mckernel_image_container_owner.py';rawtext=Path(pins[name]['path']).read_text();assert sha(rawtext.encode())==pins[name]['sha256'];text=rawtext
 for n in sources:text=replace(text,pins[n]['sha256'],sources[n]['sha256'])
 text=replace(text,str(B/'native_rust_exact_build_offline.py'),str(N/'native_rust_exact_build_offline.py'))
 oldattempt=B/'pinned-full-image-attempt-1';newattempt=N/'pinned-full-image-attempt-1'
 text=replace(text,str(oldattempt/'common-exclusion.json'),str(newattempt/'common-exclusion.json'))
 text=replace(text,'LIMITS = {','RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('+repr(str(oldattempt/'common-exclusion.json'))+',))\n\nLIMITS = {')
 sources[name]=controller(name,text,rawtext)
 gitlink=json.loads((B/'gitlink-inputs.json').read_text());assert gitlink['base_manifest_sha256']==sha(raw);gitlink['base_manifest_sha256']=mh;write(N/'gitlink-inputs.json',(json.dumps(gitlink,sort_keys=True,indent=2)+'\n').encode())
 save('SOURCE-BINDING-DELTA.json',dict(scope=__doc__,base_manifest=ref(oldmanifest),canonical_integration=ref(AUTH),changed_source_files=delta,predicted_source_manifest_sha256=mh,predicted_manifest_bytes=len(canonical(doc)),source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],preserved_source_entries=6959,preserved_other_source_modes_symlinks=True,actual_source_materialization=None,production_sources=sources,gitlink_supplement=ref(N/'gitlink-inputs.json'),source_and_consumer_evidence={k:authority[k] for k in ['accepted_source','actual_production_consumer']},independent_consumer_review=ref(R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/production-consumer-1/INDEPENDENT-ACTUAL-CONSUMER-REVIEW.json')))
 oldstatic=old['static_request'];fields={k:str(newattempt)+v[len(str(oldattempt)):] for k,v in json.loads((OLD/'REQUEST-FIELD-DELTA.json').read_text())['new_named_fields'].items() if k in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path')}
 fields.update(source_root=str(S/'materialized-source'),source_manifest=str(S/'source-inputs.json'),source_manifest_sha256=mh,source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],gitlink_manifest=str(N/'gitlink-inputs.json'),gitlink_manifest_sha256=ref(N/'gitlink-inputs.json')['sha256'])
 for key,name in [('driver','native_rust_exact_mckernel_image_offline.py'),('provenance','native_rust_exact_build_offline.py')]:fields[key+'_path']=sources[name]['path'];fields[key+'_sha256']=sources[name]['sha256']
 save('REQUEST-FIELD-DELTA.json',dict(scope=__doc__,base_static_request=oldstatic,new_named_fields=fields,memory_allocation_roots_mapping={str(B/'source-materialization-attempt-1/materialized-source'):str(S/'materialized-source'),str(oldattempt/'owner-work'):str(newattempt/'owner-work'),str(oldattempt/'owner-evidence'):str(newattempt/'owner-evidence')},expected_changed_field_count=19,all_other_fields_preserved=True,final_request=None))
 # Pure added-gate checks use actual already-accepted C/Rust/partial-link outputs.
 ns={'_fail':lambda ok,msg: None if ok else (_ for _ in ()).throw(ValueError(msg))};node=next(x for x in ast.parse(extension).body if isinstance(x,ast.FunctionDef) and x.name=='_m14_check_page_unmap_symbols');exec(compile(ast.Module(body=[node],type_ignores=[]),str(E/'page_unmap_checks.inc.py'),'exec'),ns)
 consumer=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/production-consumer-1';texts=[(consumer/p).read_text() for p in ['C-symbols-capture-1/stdout','Rust-symbols-capture-1/stdout','correction1/partial-symbols-capture-1/stdout']];ns[node.name](*texts)
 rejected=[]
 for symbol in ['page_unmap','page_unmap_hash_shift','page_unmap_hash_mask','page_unmap_lock_stride']:
  bad='\n'.join(line for line in texts[2].splitlines() if line.split()[-1:]!=[symbol])
  try:ns[node.name](texts[0],texts[1],bad)
  except ValueError:rejected.append(symbol)
 assert len(rejected)==4
 # Legacy process runner and observer source bodies must remain byte-for-AST identical.
 functions=lambda s:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
 before=functions(Path(pins['native_rust_exact_mckernel_image_offline.py']['path']).read_text());after=functions((N/'native_rust_exact_mckernel_image_offline.py').read_text());changed=[k for k in before if before[k]!=after[k]];assert changed==['_validate_m14_default_link']
 save('CONTROLLER-SOURCE-CHECK.json',dict(scope=__doc__,status='PASS_AST_AND_ACTUAL_ACCEPTED_CONSUMER_SYMBOL_GATES',unchanged_legacy_functions_except=changed,new_functions=['_m14_check_page_unmap_symbols','_validate_m14_page_unmap_contract'],accepted_actual_symbol_input_positive=True,rejected_missing_final_providers=rejected,runner_and_observer_AST_unchanged=True,observer_cap_bytes=1<<20,new_toolchain_tools=0,default_GCC14_or_image_run=False))
 save('MATERIALIZATION-COMMAND.PREPARED.json',dict(scope=__doc__,argv=['/usr/bin/taskset','-c','0','/usr/bin/python3','-I','-B',str(E/'materialize_source.py')],materializer=ref(E/'materialize_source.py'),profile=dict(cpu=0,jobs=1,as_bytes=2<<30,cpu_seconds=60,wall_seconds=90,cleanup_seconds=6,fsize_bytes=32<<20,nofile=256,core=0),source_tree_growth_max_bytes=256<<20,capture_extra_bytes=16<<20,host_floor_bytes=16<<30,scratch_floor_bytes=12<<30,execution_granted_ordinary_only=True))
 print(json.dumps(dict(status='PASS_PREPARED_AND_SOURCE_CHECKED',predicted_manifest_sha256=mh,source_gate_cases=5)))
if __name__=='__main__':main()
