"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate12 metadata/controller source preparation only; noCPUjob/ordinarygrant.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-11/default-image-preparation-1';N=H/'production-combined-12/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-3/CANONICAL-INTEGRATION.json';DATA=AUTH.parent/'CANDIDATE12-SOURCE-SUCCESSOR-DATA.PREPARED.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen11/'+name,tofile='candidate12/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='PASS_EXACT_TWO_CANONICAL_POSTIMAGES';data=json.loads(DATA.read_text());assert data['base_source_manifest_sha256']=='a96e1e20e2a79b38027c4f7ccef661b0a7cecb67f3c3968f59ccabef2925ee5a'
POST={p:row['after']['sha256'] for p,row in a['changes'].items()};pre={p:row['before']['sha256'] for p,row in a['changes'].items()};assert len(POST)==2
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='a96e1e20e2a79b38027c4f7ccef661b0a7cecb67f3c3968f59ccabef2925ee5a'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay']);doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for z in reversed(ast.parse(old).body):
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in values:
  name=z.targets[0].id;lines[z.lineno-1:z.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'ROOT_CANONICAL_EXACT_TWO_REVIEWED_POSTIMAGES_INTEGRATED' and {p:row['after'] for p,row in authority['changes'].items()}","authority['status'] == 'PASS_EXACT_TWO_CANONICAL_POSTIMAGES' and {p:row['after']['sha256'] for p,row in authority['changes'].items()}")
new=new.replace('os.sched_getaffinity(0) == {6}','os.sched_getaffinity(0) == {0}').replace('ordinary CPU6 grant required','ordinary CPU0 grant required')
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256']);counts={'kernel/process.c':2,'kernel/rust/sched_helpers.rs':3}
for row in delta:
 assert new.count(row['before_sha256'])==counts[row['path']]
 new=new.replace(row['before_sha256'],row['after_sha256'])
# Replace exactold logging-provider requirement with retainedCdata/newRustprovider contract.
new=new.replace("M14_MIGRATION_C_LOG_PROVIDER = 'process_sched_migrate_log_bridge'","M14_MIGRATION_RUST_LOG_PROVIDER = 'process_sched_migrate_log_bridge'",1)
lines=new.splitlines(True)
for z in reversed(ast.parse(new).body):
 if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M14_MIGRATION_HEADER_ABI_ASSERTIONS' for t in z.targets):
  appendix=json.loads((E/'migration_descriptor_ABI.PREPARED.json').read_text())['appendix'];lines[z.lineno-1:z.end_lineno]=['M14_MIGRATION_HEADER_ABI_ASSERTIONS = '+repr(appendix)+'\n']
new=''.join(lines)
new=new.replace("M14_RUST_EXPORTS = ('sched_request_migrate',","M14_RUST_EXPORTS = ('process_sched_migrate_log_bridge', 'sched_request_migrate',",1)
lines=new.splitlines(True)
for z in reversed(ast.parse(new).body):
 if isinstance(z,ast.FunctionDef) and z.name=='_validate_m14_migration_contract':
  replacement=(E/'migration_log_contract.inc.py').read_text();lines[z.lineno-1:z.end_lineno]=[replacement+'\n']
new=''.join(lines);driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
constant=lambda s,name:next(ast.literal_eval(z.value) for z in ast.parse(s).body if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in z.targets))
w=constant(new,'M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS');assert w==constant(old,'M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS') and w.count('_Static_assert')==148
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='READY_SOURCE_ONLY_NO_CPU_RESERVATION_OR_EXECUTION',canonical_integration=ref(AUTH),accepted_successor_data=ref(DATA),accepted_Rust_object=data['actual_Rust_object_acceptance'],changed_source_files=delta,producer=producer,provenance=prov,driver=driver,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),predicted_source_derivative_sha256=doc['source_derivative_sha256'],predicted_materialization_sha256=doc['materialization_sha256'],preserved_source_entries=6959,preserved_symlinks=49,preserved_other_sources_modes_metadata=True,existing148_assertions_bytes_sha256=sha(w.encode()),new_descriptor_header_assertions=6,descriptor_C32byte_aligned8_original_verbose_data=True,Rust_log_uniqueT_noU=True,Rust_descriptor_import_U=True,final_unique_Rust_log_and_C_descriptor=True,no_fake_C_logprototype_or_bitfield_offsetof=True,actual_materialization=None,actual_manifest=None,actual_owner=None,actual_request=None,actual_pure=None,actual_whole_C_TU_defaultlink_native=None,ordinary_grant=None))
save('EXACT-NEXT-ORDINARY-PREPARATION.NOT-RELEASED.json',dict(scope=__doc__,status='CPU0_AFFINITY_SUCCESSOR_PREPARED_NO_GRANT_OR_RESERVATION',materializer_argv=['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'materialize_source.py')],combined_outer_argv_template=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'run_materialization_and_pure.py')],combined_runner=None,profile=dict(cpu=0,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),data_only_affinity_delta='Accepted ordinaryCPU6->CPU0 literal and materializer affinity assertion6->0; existing historicalCPU0 ordinaryprofile reused. No command algorithm/resource expansion.',guard='Freshfull19GiB predicate bothstages; HOST16GiB+complete110GiBbackingremaininggap+acceptedcompiler/output/capture/emergencyreserve+256MiBsource/16MiBcapture, scratch12GiB+67108864control+679477248emergency; no root/resize.',requires='Root explicit ordinarygrant then exactaccepted11namespace/request/completepurevalidator successor withowned990ASTload+signalhandlers. CPU6reservedP12fixture. No compiler/Docker/heavy/run/acquire.',actual_outputs=None,independent_heavy_release=None))
print(json.dumps(dict(producer=producer,driver=driver,predicted_manifest=mh),sort_keys=True))
