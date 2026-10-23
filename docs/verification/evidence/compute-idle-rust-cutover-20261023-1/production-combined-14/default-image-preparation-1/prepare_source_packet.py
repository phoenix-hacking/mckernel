"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate14 source/default-consumer preparation only; no ordinaryCPUreservation or execution.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-13/default-image-preparation-1';N=H/'production-combined-14/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/velocity-intervention-20261023-3/m14-top-log/CANONICAL-INTEGRATION.ROOT-RECORD.json';ACTUAL=AUTH.parent/'selected-production-consumer-1/ACTUAL-SELECTED-CONSUMER-RECEIPT.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen13/'+name,tofile='candidate14/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert ref(AUTH)['sha256']=='c0e5ffd7303154bf3d70b9d5fc8192c29bca3ae10d90625d7b329cf109473843' and a['status']=='EXACT_TWO_CANONICAL_LOGGER_POSTIMAGES_INTEGRATED'
actual=json.loads(ACTUAL.read_text());assert ref(ACTUAL)['sha256']=='6a6432a326904ae0d00fbf6e78b25eaa4f03d1867af4eb1cbbc2c9dacf0b0e85' and actual['Rust_provider_count']==29 and actual['C_provider_count']==2
POST={p:row['after']['sha256'] for p,row in a['changes'].items()};pre={p:row['before']['sha256'] for p,row in a['changes'].items()};assert len(POST)==2
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='12b430700c83fc62cd9bc7bc62d29f40d69511953907590696827a64337d92a2'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay']);doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.CPU6.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for z in reversed(ast.parse(old).body):
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in values:
  name=z.targets[0].id;lines[z.lineno-1:z.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'PASS_EXACT_TWO_CANONICAL_MEMORY_POSTIMAGES' and authority['canonical_postimages']","authority['status'] == 'EXACT_TWO_CANONICAL_LOGGER_POSTIMAGES_INTEGRATED' and {p:row['after']['sha256'] for p,row in authority['changes'].items()}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
for row in delta:assert new.count(row['before_sha256'])==1;new=new.replace(row['before_sha256'],row['after_sha256'])
# Actual selectedpartialproof: Rust logger is internalRust consumer/provider; no CloggerU.
new=new.replace("'clear_range', 'ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range')","'clear_range', 'ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range', 'x86_clear_range_top_log_bridge')",1)
new=new.replace("M14_RUST_EXPORTS = ('ihk_mc_pt_clear_range',","M14_RUST_EXPORTS = ('x86_clear_range_top_log_bridge', 'ihk_mc_pt_clear_range',",1)
# Preserve existing realheader logger ABI within eight-assertion memory appendix.
new=new.replace("for name in ('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body'):","for name in ('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body','x86_clear_range_top_log_bridge'):",1)
new=new.replace("for name,index in (('remote_flush_tlb_array_cpumask',1),('x86_clear_range_top_log_bridge',0),
                       ('x86_clear_range_walk_l4_bridge',0)):","for name,index in (('remote_flush_tlb_array_cpumask',1),('x86_clear_range_walk_l4_bridge',0)):",1)
new=new.replace("actual_C_providers=('remote_flush_tlb_array_cpumask','x86_clear_range_top_log_bridge','x86_clear_range_walk_l4_bridge'),","actual_C_providers=('remote_flush_tlb_array_cpumask','x86_clear_range_walk_l4_bridge'),
                Rust_top_logger='x86_clear_range_top_log_bridge',C_logger_import_required=False,
                real_header_logger_ABI_in_existing_eight_assertions=True,",1)
new=new.replace('all3_C_providers_remain_computeC_debt=True','all2_C_providers_remain_computeC_debt=True',1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
constant=lambda s,n:next(ast.literal_eval(z.value) for z in ast.parse(s).body if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in z.targets))
for name in ('M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS','M14_MIGRATION_HEADER_ABI_ASSERTIONS','M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS'):assert constant(old,name)==constant(new,name)
assert constant(new,'M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS').count('_Static_assert')==8 and 'x86_clear_range_top_log_bridge' in constant(new,'M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS')
constants={}
for z in ast.parse(new).body:
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in ('M14_IDLE_IMPORTS','M14_MEMORY_IMPORTS','M14_RUST_EXPORTS'):
  constants[z.targets[0].id]=eval(compile(ast.Expression(z.value),'sourceconstants-only','eval'),{'__builtins__':{}},constants)
assert len(constants['M14_RUST_EXPORTS'])==len(set(constants['M14_RUST_EXPORTS']))==29 and set(constants['M14_RUST_EXPORTS'])==set(actual['actual_Rust_providers']) and len(constants['M14_MEMORY_IMPORTS'])==5
assert 'x86_clear_range_top_log_bridge' not in constants['M14_MEMORY_IMPORTS']
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='CANDIDATE14_SOURCE_ONLY_READY_NO_GRANT_OR_EXECUTION',canonical_integration=ref(AUTH),actual_selected_GCC9_partial_consumer=ref(ACTUAL),accepted_actual78_Rust=ref(AUTH.parent/'production-fullcrate-1/ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),changed_source_files=delta,producer=producer,provenance=prov,driver=driver,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),predicted_source_derivative_sha256=doc['source_derivative_sha256'],predicted_materialization_sha256=doc['materialization_sha256'],actual_derived_29_Rust_guard_names=constants['M14_RUST_EXPORTS'],actual_C_memory_imports=constants['M14_MEMORY_IMPORTS'],actual2_C_provider_contracts=actual['actual_C_providers'],logger_no_C_import_or_relocation_required=True,logger_C_definition_excluded_underPUBLIC=True,logger_fullglobal_Rust_final_T_noU=True,logger_realheaderABI_preserved_in_existing_memory8=True,old148_descriptor6_memory8_assertion_bytes_exact_preserved=True,preserved_source_entries=6959,preserved_symlinks=49,actual_source=None,actual_manifest=None,actual_owner=None,actual_request=None,actual_pure=None,actual_GCC14_defaultlink_native=None,ordinary_grant=None,remaining2_C_providers_still_computeC_debt=True))
save('NEXT-ORDINARY-PROFILE.NOT-RELEASED.json',dict(scope=__doc__,status='PREPARED_ONLY_NO_CPU_RESERVATION',materializer_argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'materialize_source.py')],materializer=producer,profile=dict(cpu=6,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),source_growth_max_bytes=268435456,capture_extra_bytes=16777216,requires='Rootexecutable-readyexplicitordinarygrant; exactsource+completepure route/owned990registeredhandlers/full19GiB bothstages/HOSTscratchfullremaining110GiBsparsegap/floors/reserves; no compiler/root/heavy/build/native.',actual_outputs=None))
print(json.dumps(dict(producer=producer,driver=driver,predicted_manifest=mh,Rust_guards=29,C_providers=2),sort_keys=True))
