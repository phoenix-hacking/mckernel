"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate13 source/consumer preparation only after actual selectedGCC9 consumer wholejoin.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-12/default-image-preparation-1';N=H/'production-combined-13/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/velocity-intervention-20261023-2/m14-memory-next/CANONICAL-INTEGRATION.json';ACTUAL=R/'docs/verification/evidence/velocity-intervention-20261023-2/m14-memory-next/selected-production-consumer-1/ACTUAL-SELECTED-CONSUMER-RECEIPT.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen12/'+name,tofile='candidate13/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='PASS_EXACT_TWO_CANONICAL_MEMORY_POSTIMAGES';POST=a['canonical_postimages'];assert len(POST)==2
actual=json.loads(ACTUAL.read_text());assert ref(ACTUAL)['sha256']=='66bfde9e222d21587fcae4b44b860ddd38c504208131652b5d7c21e19c791412'
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h
 delta.append(dict(path=rel,before_sha256=base['repository_files'][rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='8b2b3f20ccf8da69bbb64deedc7b222e23d00a1c83708486810a430d2fe9b692'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay']);doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for z in reversed(ast.parse(old).body):
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in values:
  name=z.targets[0].id;lines[z.lineno-1:z.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'PASS_EXACT_TWO_CANONICAL_POSTIMAGES' and {p:row['after']['sha256'] for p,row in authority['changes'].items()}","authority['status'] == 'PASS_EXACT_TWO_CANONICAL_MEMORY_POSTIMAGES' and authority['canonical_postimages']")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
for row in delta:assert new.count(row['before_sha256'])==1;new=new.replace(row['before_sha256'],row['after_sha256'])
new=new.replace("'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge')","'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge', 'x86_clear_range_public_body')",1)
new=new.replace("'x86_init_text_map_kernel_start_bridge', 'x86_init_text_end_bridge')","'x86_init_text_map_kernel_start_bridge', 'x86_init_text_end_bridge',\n                               'clear_range', 'ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range')",1)
new=new.replace("M14_RUST_EXPORTS = ('process_sched_migrate_log_bridge',","M14_RUST_EXPORTS = ('ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range', 'process_sched_migrate_log_bridge',",1)
appendix=json.loads((E/'clear_range_ABI.PREPARED.json').read_text())['assertions'];insertion='M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS = '+repr(appendix)+'\n'
new=new.replace('M14_RUST_EXPORTS = ',insertion+'M14_RUST_EXPORTS = ',1)
extension=(E/'clear_range_checks.inc.py').read_text();new=new.replace('def _validate_m14_source_pins(source_root):',extension+'\n\ndef _validate_m14_source_pins(source_root):',1)
anchor="    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',";new=new.replace(anchor,"    clear_range_proof = _validate_m14_clear_range_contract(source_root,build,tools,env,timeout,command_rows,objects)\n"+anchor,1)
new=new.replace('migration_contract=migration_proof, idle_imports=M14_IDLE_IMPORTS,','migration_contract=migration_proof, clear_range_contract=clear_range_proof, idle_imports=M14_IDLE_IMPORTS,',1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
constants={}
for z in ast.parse(new).body:
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in ('M14_IDLE_IMPORTS','M14_MEMORY_IMPORTS','M14_RUST_EXPORTS'):
  constants[z.targets[0].id]=eval(compile(ast.Expression(z.value),'source-constants-only','eval'),{'__builtins__':{}},constants)
assert len(constants['M14_RUST_EXPORTS'])==len(set(constants['M14_RUST_EXPORTS']))==28 and set(constants['M14_RUST_EXPORTS'])==set(actual['actual_Rust_providers_28'])
constant=lambda s,n:next(ast.literal_eval(z.value) for z in ast.parse(s).body if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in z.targets))
assert constant(old,'M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS')==constant(new,'M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS')
assert constant(old,'M14_MIGRATION_HEADER_ABI_ASSERTIONS')==constant(new,'M14_MIGRATION_HEADER_ABI_ASSERTIONS')
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_ONLY_PREPARED_NO_NEW_JOB_OR_GRANT',canonical_integration=ref(AUTH),C_provider_spelling_clarification=ref(AUTH.parent/'CANONICAL-INTEGRATION-PROVIDER-NAME-CLARIFICATION.json'),actual_GCC9_selected_consumer=ref(ACTUAL),changed_source_files=delta,producer=producer,provenance=prov,driver=driver,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),predicted_source_derivative_sha256=doc['source_derivative_sha256'],predicted_materialization_sha256=doc['materialization_sha256'],actual_derived_28_Rust_guard_names=constants['M14_RUST_EXPORTS'],actual_C_memory_imports=constants['M14_MEMORY_IMPORTS'],new_C_import_only_public_body=True,publicclearfree_C_U_not_invented=True,actual3_C_provider_contracts=actual['actual3_C_providers'],all3_C_providers_remain_computeC_debt=True,existing148_and_descriptorABI_assertion_bytes_preserved=True,new_clear_range_headerABI_assertions=8,preserved_source_entries=6959,preserved_symlinks=49,actual_source=None,actual_manifest=None,actual_owner=None,actual_request=None,actual_pure=None,actual_GCC14_defaultlink_native=None,ordinary_grant=None))
save('NEXT-ORDINARY-PROFILE.NOT-RELEASED.json',dict(scope=__doc__,status='SOURCE_ONLY_NO_CPU_RESERVATION',materializer_argv=['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'materialize_source.py')],materializer=producer,profile=dict(cpu=0,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),source_growth_max_bytes=268435456,capture_extra_bytes=16777216,requires='Rootfreshordinarygrant; acceptedmaterialization+completepure route/owned990registeredhandlers/full19GiB bothstages/HOSTscratchfullremaining110GiBsparsegap/floors/reserves; no build/compiler/root/run/acquire',actual_outputs=None))
print(json.dumps(dict(producer=producer,driver=driver,predicted_manifest=mh,Rust_guards=28,C_memory_imports=len(constants['M14_MEMORY_IMPORTS'])),sort_keys=True))
