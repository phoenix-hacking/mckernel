"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate10 exactsource/consumer metadata from frozen9 and accepted0915derivative.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-9/default-image-preparation-1';N=H/'production-combined-10/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/CANONICAL-INTEGRATION.json'
OP=AUTH.parent/'production-process-tu-1/EXACT-NEXT-PRODUCTION-PROCESS-TU.OPERATION.NOT-RELEASED.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='base/'+name,tofile='candidate10/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='CANONICAL_BOUNDED_SPIN_SLEEP_SOURCE_INTEGRATED'
op=json.loads(OP.read_text());assert ref(OP)['sha256']=='c6e12e8c60266bb9e1b3fd978ba137c71999ccf108363f4197a49197e45ad150'
POST={p:row['sha256'] for p,row in a['postimages'].items()};pre={p:row['sha256'] for p,row in a['preimages'].items()};base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='fbd125807193835f88905d0c89d985dd9a0a066265598b09accd69d6fe25f3ea'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay']);doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for z in reversed(ast.parse(old).body):
 if isinstance(z,ast.Assign) and len(z.targets)==1 and isinstance(z.targets[0],ast.Name) and z.targets[0].id in values:
  name=z.targets[0].id;lines[z.lineno-1:z.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'CANONICAL_BOUNDED_SET_TIMER_SOURCE_INTEGRATED' and {p:row['sha256'] for p,row in authority['outputs'].items()}","authority['status'] == 'CANONICAL_BOUNDED_SPIN_SLEEP_SOURCE_INTEGRATED' and {p:row['sha256'] for p,row in authority['postimages'].items()}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
pin=op['private_existing_consumer'];accepted=Path(pin['path']);assert ref(accepted)==pin and pin['sha256']=='0915f5266361faae378467324f233340193df78f1831d51bd9fcda76e22e15b0'
old=accepted.read_text();priorprov=ref(B/'native_rust_exact_build_offline.py')['sha256'];assert old.count(priorprov)==1;new=old.replace(priorprov,prov['sha256'],1)
fns=lambda s:{z.name:ast.dump(z,include_attributes=False) for z in ast.parse(s).body if isinstance(z,ast.FunctionDef)};assert fns(old)==fns(new)
for row in delta:assert row['before_sha256'] not in new and row['after_sha256'] in new
witness=next(ast.literal_eval(z.value) for z in ast.parse(new).body if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS' for t in z.targets));assert witness.count('_Static_assert')==148 and '7848' in witness
# The accepted string contains130Rust layout assertions plus18C callback/type assertions.
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_METADATA_ONLY_PENDING_ACTUAL',canonical_integration=ref(AUTH),accepted_TU_consumer_operation=ref(OP),accepted_driver=pin,actual_layout_evidence=op['actual_layout_evidence'],source_ABI_review=ref(AUTH.parent/'INDEPENDENT-PRODUCTION-SPIN-SLEEP-CONSUMER-ACCEPTANCE.ROOT-RECORD.json'),changed_source_files=delta,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],producer=producer,provenance=prov,driver=driver,all_accepted_driver_function_AST_unchanged=True,layout_assertions=130,callback_type_assertions=18,total_assertions=148,CpuLocalVar_current_expected=7848,preserved_source_entries=6959,preserved_symlinks=49,original19GiB_guard_required=True,preserved_hash_count_failure='candidate9initialsinglepinassertion correctedonce to exactprocess2/sched3/harness1; original retained; no repeatedfailure',actual_materialization=None,actual_pure=None,actual_whole_C_TU_defaultlink_native=None))
print(json.dumps(dict(manifest=mh,producer=producer,driver=driver,provenance=prov),sort_keys=True))
