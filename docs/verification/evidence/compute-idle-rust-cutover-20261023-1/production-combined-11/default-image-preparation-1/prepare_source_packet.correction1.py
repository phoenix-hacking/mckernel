"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate11 source/controller PREPARATION ONLY; no materializer/validator/compiler.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-10/default-image-preparation-1';N=H/'production-combined-11/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-2/CANONICAL-INTEGRATION.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen10/'+name,tofile='candidate11/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='ROOT_CANONICAL_EXACT_TWO_REVIEWED_POSTIMAGES_INTEGRATED';POST={p:row['after'] for p,row in a['changes'].items()};pre={p:row['before'] for p,row in a['changes'].items()};assert len(POST)==2
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='9692f871af1200e00d2627510fb8d2e48b159e330d5438f28998bd03149b6fa3'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay']);doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for z in reversed(ast.parse(old).body):
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in values:
  name=z.targets[0].id;lines[z.lineno-1:z.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'CANONICAL_BOUNDED_SPIN_SLEEP_SOURCE_INTEGRATED' and {p:row['sha256'] for p,row in authority['postimages'].items()}","authority['status'] == 'ROOT_CANONICAL_EXACT_TWO_REVIEWED_POSTIMAGES_INTEGRATED' and {p:row['after'] for p,row in authority['changes'].items()}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
counts={'kernel/process.c':2,'kernel/rust/sched_helpers.rs':3}
for row in delta:
 assert new.count(row['before_sha256'])==counts[row['path']]
 new=new.replace(row['before_sha256'],row['after_sha256'])
new=new.replace("M14_RUST_EXPORTS = ('spin_sleep_or_schedule',",'M14_MIGRATION_C_LOG_PROVIDER = \'process_sched_migrate_log_bridge\'\nM14_MIGRATION_HEADER_ABI_ASSERTIONS = \'_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_request_migrate),void(*)(int,struct thread*)),"migration public ABI");\\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_migrate_log_bridge),void(*)(unsigned long,int,int)),"migration existing log ABI");\\n\'\nM14_RUST_EXPORTS = (\'sched_request_migrate\', \'sched_request_migrate_body_result\', \'spin_sleep_or_schedule\',',1)
# Preserve the accepted148actual layout/callback witness string byte-for-byte.
anchor="    proofs['kernel/process.c'] += M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS";assert new.count(anchor)==1;new=new.replace(anchor,anchor+"\n    proofs['kernel/process.c'] += M14_MIGRATION_HEADER_ABI_ASSERTIONS",1)
extension=(E/'migration_checks.inc.py').read_text();new=new.replace('def _validate_m14_source_pins(source_root):',extension+'\n\ndef _validate_m14_source_pins(source_root):',1)
anchor="    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',";new=new.replace(anchor,"    migration_proof = _validate_m14_migration_contract(source_root, build, tools, env, timeout, command_rows, objects)\n"+anchor,1)
new=new.replace('set_timer_contract=set_timer_proof, idle_imports=M14_IDLE_IMPORTS,','set_timer_contract=set_timer_proof, migration_contract=migration_proof, idle_imports=M14_IDLE_IMPORTS,',1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
getw=lambda s:next(ast.literal_eval(z.value) for z in ast.parse(s).body if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS' for t in z.targets))
assert getw(old)==getw(new) and getw(new).count('_Static_assert')==148
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_ONLY_READY_FOR_FOCUSED_REVIEW_NO_ORDINARY_GRANT',canonical_integration=ref(AUTH),actual_leaf_receipt=ref(AUTH.parent/'ACTUAL-LEAF-RECEIPT.json'),actual_production_Rust_acceptance_sha256=a['production_Rust_review']['receipt_sha256'],actual_78input_Rust_compile_seconds=a['actual_production_compile_seconds'],accepted_Rust_Udelta=a['actual_U_delta'],changed_source_files=delta,producer=producer,provenance=prov,driver=driver,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),predicted_source_derivative_sha256=doc['source_derivative_sha256'],predicted_materialization_sha256=doc['materialization_sha256'],actual_materialized_source=None,actual_manifest_sha256=None,actual_owner=None,actual_request=None,actual_pure=None,actual_whole_C_TU_defaultlink_native=None,preserved_source_entries=6959,preserved_symlinks=49,old148_assertion_string_preserved_sha256=sha(getw(new).encode()),new_header_assertions='2exactdeclarationtypes only; no promoted numericmigrationmodel',migration_layout_evidence='18actualRust/Cheaderchecks retained in acceptedleaf receipt; C request struct/descriptor is !PUBLIC. No fabricated PUBLIC C model or numeric layout asserted; future concrete productionlayout appendix requires sourcebound actualvalues before adding it.',expected_actual_provider_contract='SelectedPUBLICC getterbodyexcluded; Rustgetter/body uniqueT; existingPUBLICClogT and fullRustUlog; finaluniquegetter/body/log+existingallundefinedempty. No fictional CgetterU, no fifthCmemoryimport.',original19GiB_guard_required=True,ordinary_execution_grant=None))
save('NEXT-ORDINARY-PROFILE.NOT-RELEASED.json',dict(scope=__doc__,status='SOURCE_ONLY_NOT_GRANTED_NOT_EXECUTED',materializer_argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'materialize_source.py')],materializer=producer,profile=dict(cpu=6,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),source_growth_max_bytes=268435456,capture_extra_bytes=16777216,requires='Focused independent source/profile review then root ordinarygrant; actualsourcecopy followedbycomplete_validate_request only, exactowned990ASTloader+signalhandlers/full19GiB guards/freshHOSTscratchfullgapfloorsreserves; no run/acquire/compiler/heavy.',actual_outputs=None))
print(json.dumps(dict(producer=producer,driver=driver,predicted_manifest=mh),sort_keys=True))
