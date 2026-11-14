"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical selective Root adoption/materialization proposal. No operational calls.
"""
import ast,copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'outer-perf-line-restore-source-1';E=D.parents[1];ROOT=E.parents[3]
R=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
p=read(P/'PROFILE.SOURCE-ONLY.json');assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256'].startswith('b61944dd')
review=P/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json';assert ref(review)['sha256'].startswith('941b9839')
accepted=p['predecessor_CURRENT113_actual_acceptance'];a=read(accepted['path']);ap=read(a['profile']['path'])
newmap_path=Path(p['inputs']['source_directory_exports'][0]['manifest']['path']);newmap=read(newmap_path)
oldmap_path=Path(ap['inputs']['source_directory_exports'][0]['manifest']['path']);oldmap=read(oldmap_path)
oldrust={r['relative']:r for r in oldmap['files']};assert len(oldrust)==118 and len(newmap['files'])==119
prior_post={r['relative']:r for r in ap['inputs']['postimages']}
rows=[]
for row in p['inputs']['postimages']:
 relative=row['relative']
 if relative in ['kernel/CMakeLists.txt','kernel/process.c','kernel/syscall.c']:
  rows.append(dict(relative=relative,canonical_path=str(ROOT/relative),preimage=prior_post[relative]['postimage'],candidate=row['postimage'],mode_if_new=420))
for row in newmap['files']:
 relative=row['relative'];prior=oldrust.get(relative)
 if prior is None or row['snapshot']['sha256']!=prior['snapshot']['sha256']:
  rows.append(dict(relative='kernel/rust/'+relative,canonical_path=str(ROOT/'kernel/rust'/relative),preimage=prior['snapshot'] if prior else None,candidate=row['snapshot'],mode_if_new=420))
assert {r['relative'] for r in rows}=={'kernel/CMakeLists.txt','kernel/process.c','kernel/syscall.c','kernel/rust/lib.rs','kernel/rust/process_verbose_data.rs','kernel/rust/syscall_policy.rs'}
# Only six changed candidate files are authenticated here; no unchanged119file inventory.
for row in rows:assert ref(row['candidate']['path'])==row['candidate']
write_set=save('EXACT-SIX-FILE-WRITE-SET.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,source_review=ref(review),accepted_CURRENT113=accepted,source_profile=ref(P/'PROFILE.SOURCE-ONLY.json'),files=rows,canonical_writes_performed=0,new_runtime_C_bodies=0,excluded=['LOCAL14+configs4bb0','ptrace_setsiginfo6777','LOCK4','WAKE3'],retained_arch_source_and_object_unchanged=True,origin_replay=False))
# Candidate selected-provider accounting includes reused existing atomic provider.
profile=copy.deepcopy(p);profile['status']='NEXT114_ROOT_SELECTIVE_MATERIALIZATION_TEMPLATE_NOT_AUTHORITY'
profile['producer_contract']['expected_current_cohort_Rust_function_exports']=59
profile['producer_contract']['candidate_selected_Rust_provider_accounting']=dict(accepted113_selected_providers=56,new_Rust_wrapper_definitions=2,newly_selected_existing_atomic_provider=1,candidate_selected_providers=59,new_actual_Rust_function_definitions=2,physical_export_delta_not_inferred=True)
profile['source_preparation_current_context']=dict(runtime_authority=None,status='ROOT41_OR_LATER_ACTUAL_LEDGER_AND_POSITIVE_FREE_PENDING',current_nonce_ledger=None,current_native_custody_clearance=None,accepted_CURRENT113=accepted)
profile_ref=save('PROFILE.SOURCE-ONLY.json',profile)
export_ref=save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',read(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'))
plan=read(P/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan['source_profile']=profile_ref;plan['producer_contract']=profile['producer_contract'];save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(n,(P/n).read_bytes())
# Literal finite six-file writer, only Root invoking real bindings can cause mutation.
writer='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact six-file selective adoption, preserving originals. No compiler/configure/runtime.
SOURCE PROPOSAL ONLY until Root supplies real bindings and invokes it once.
"""
from pathlib import Path
import argparse,hashlib,json,os,re
D=Path(__file__).resolve().parent
ROOT=Path(%r)
WRITESET=%r
REVIEW=%r

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def fresh_json(p,x):
 with p.open('x') as f:f.write(json.dumps(x,indent=2)+'\\n')
def adopt(bindings_path):
 b=read(bindings_path)
 assert b['author']=='/root' and b['decision']=='ADOPT_EXACT_NEXT114_GLOBAL32_PERF3_SIX_SOURCES_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exclusive_six_file_integration'] is True and b['root_attests_no_live_source_reader_conflict'] is True
 assert b['write_set']==WRITESET and b['source_review']==REVIEW
 descriptor=read(auth(WRITESET));auth(REVIEW)
 ledger=read(auth(b['current_nonce_ledger']));free=read(auth(b['current_positive_free']))
 match=re.fullmatch(r'ROOT-CURRENT-NONCE-LEDGER(\\d+)\\.json',Path(b['current_nonce_ledger']['path']).name)
 assert match and int(match[1])>=41
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert ledger['latest_accepted_free_boundary']==b['current_positive_free'] and free['current_free'] is True and free['normal_owned_retirement'] is True
 output=D/'ROOT-ACTUAL-SELECTIVE-SOURCE-ADOPTION-1';assert not output.exists()
 checked=[]
 for row in descriptor['files']:
  target=ROOT/row['relative'];assert str(target)==row['canonical_path'] and target.parent.resolve()==target.parent and not target.is_symlink()
  source=auth(row['candidate']);data=source.read_bytes()
  if row['preimage'] is None:assert not os.path.lexists(target);old=None
  else:
   old=target.read_bytes();assert len(old)==row['preimage']['bytes'] and hashlib.sha256(old).hexdigest()==row['preimage']['sha256']
  checked.append((row,target,data,old))
 assert len(checked)==6
 output.mkdir(mode=0o700);(output/'preimages').mkdir(mode=0o700)
 for row,target,data,old in checked:
  if old is not None:
   prior=output/'preimages'/row['relative'];prior.parent.mkdir(mode=0o700,parents=True,exist_ok=True);prior.write_bytes(old)
 fresh_json(output/'STARTED.json',dict(scope=descriptor['scope'],author='/root',runtime_authority=None,Root_bindings=ref(bindings_path),write_set=WRITESET,current_nonce_ledger=b['current_nonce_ledger'],current_positive_free=b['current_positive_free']))
 results=[]
 for row,target,data,old in checked:
  flags=os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC|(os.O_EXCL|os.O_CREAT if old is None else os.O_TRUNC)
  fd=os.open(target,flags,row['mode_if_new'])
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  actual=ref(target);assert actual['bytes']==row['candidate']['bytes'] and actual['sha256']==row['candidate']['sha256']
  results.append(dict(canonical=actual,private_source=row['candidate'],prior=row['preimage']))
 receipt=output/'ROOT-SOURCE-ADOPTION.json'
 fresh_json(receipt,dict(scope=descriptor['scope'],author='/root',status='ROOT_SOURCE_ADOPTED_NEXT114_GLOBAL32_PERF3_SIX_FILES_NOT_BUILT',runtime_authority=None,source_review=REVIEW,write_set=WRITESET,Root_bindings=ref(bindings_path),files=results,current_nonce_ledger=b['current_nonce_ledger'],current_positive_free=b['current_positive_free'],actual_compilers=0,actual_native_apps=0,whole_file_retirement=False))
 print(json.dumps(dict(status='ROOT_SELECTIVE_SIX_SOURCE_ADOPTION_ONLY',receipt=ref(receipt))))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root-bindings',required=True);a=p.parse_args();adopt(Path(a.root_bindings))
'''%(str(ROOT),write_set,ref(review))
ast.parse(writer);write('apply_root_selective_adoption.py',writer)
save('ROOT-SOURCE-ADOPTION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',dict(scope=SCOPE,status='TEMPLATE_ONLY_NO_SOURCE_OWNERSHIP_OR_EXECUTION_GRANT',author=None,decision=None,expected_Root_decision='ADOPT_EXACT_NEXT114_GLOBAL32_PERF3_SIX_SOURCES_ONLY',maximum_invocations=1,root_attests_exclusive_six_file_integration=None,root_attests_no_live_source_reader_conflict=None,write_set=write_set,source_review=ref(review),current_nonce_ledger=None,current_positive_free=None))
origin=profile['origin_source_materialization']
save('ROOT-MATERIALIZATION-MAPPINGS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,status='EXACT_NEXT114_MAPPINGS_FOR_EXISTING_ROOT_MATERIALIZATION_METHOD_NO_NEW_FRAMEWORK',source_profile=profile_ref,export_template=export_ref,write_set=write_set,source_review=ref(review),actual_source_adoption_receipt=None,planned_actual_admission=str(R),source_map=profile['inputs']['source_directory_exports'][0]['manifest'],Rust_source_count=119,command_count=4,replacement_count=3,retained_count=8,compiler_sources_in_order=['kernel/rust/lib.rs','kernel/syscall.c','kernel/process.c'],new_object_paths=profile['producer_contract']['new_objects'],unchanged_retained_arch_producer=profile['retained_arch_producer'],origin_producer_reuse=origin['actual_producer_receipt'],origin_header_reuse=origin['actual_generated_header'],origin_context_reuse={k:origin[k] for k in ['actual_origin_binding','actual_Rust_environment','actual_CMake_origin']},arch_context_binding='Compare actual origin.command to template.retained_arch_producer.command; no four-command index is architecture C. Exact archived architecture source/origin-profile/header/env remain pinned. No archC/producer replay.',mechanical_existing_materializer_changes=['Use this exact template/export/six-file Root source-adoption receipt and latest actualRoot41-or-later ledger/free.', 'Retain existingholder/resource/export/request/publication methods and original CPU/memory/PID/capacity/clock/account contracts.', 'Source map119; replacement3/retained8; sources Rust/kernelC/processC. No loops rehashing prior large histories beyond required original validator.', 'Bind existing typedGLOBAL32 env/default0 inputs and perf3flags as this exact profile; existingactualorigin2c419 only.', 'Root supplies real sourceownership/adoption/request/nonce/output/publication/holder/resources and independentPASS; no authority inferred from prepared metadata.'],actual_materializer=None,actual_current_ledger=None,actual_positive_free=None,actual_nonce=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None,candidate_counts=dict(C_functions=80,selected_Rust_providers=59,process_C_OBJECTs=31),counts_are_candidate_only=True))
py='/home/holden/anaconda3/bin/python3'
save('NEXT-ROOT-COMMAND-AND-ORDER.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,next_actual_Root_command=[py,'-I','-B',str(D/'apply_root_selective_adoption.py'),'--root-bindings',str(D/'ROOT-ACTUAL-SOURCE-ADOPTION-BINDINGS.json')],source_write_set=[r['relative'] for r in rows],metadata_output_if_Root_actually_invokes=str(D/'ROOT-ACTUAL-SELECTIVE-SOURCE-ADOPTION-1'),before_command='Root waits for independently accepted actualfree from startup retirement, then writes real exactbindings from template with currentRoot41-or-later facts. Do not touch hotstartup entry, reuse historicalfree or fabricate ledger41.',ordered_followthrough=['Actual Root selective source adoption of exact6files via command above; positive source readback/receipt.', 'Root adapts existing materializer from supplied mappings and binds actual sourceprofile/export/request/bootstrap using latest ledger/free and freshnonce/output.', 'Root publishes/fetch-verifies actual static sources and metadata. Complete all exact entry/resource/publisher commands before fresh capture.', 'Root actual fresh preholder/current capture, holder-only bootstrap, heldresource facts, exact independent executionPASS, existingoneusepublisher/READY; only then fourcompiler/linkcommands.', 'Original native/account/resource/fixedclock controls retained. Actual selected C80/Rust59/process31 are proof obligations, not acceptance or wholefile/native retirement.'],actual_adoption=None,actual_materialization=None,actual_publication=None,actual_resource=None,actual_release=None,all_actual_calls=0))
files=[ref(q) for q in D.rglob('*') if q.is_file() and q.name not in ['prepare_source.py','SOURCE-READY.json']]
save('SOURCE-READY.json',dict(scope=SCOPE,status='NEXT114_EXACT_SIX_SOURCE_ROOT_ADOPTION_AND_MATERIALIZATION_PROPOSAL_READY_NOT_RELEASED',runtime_authority=None,files=files,source_profile=profile_ref,source_review=ref(review),write_set=write_set,materialization_mappings=ref(D/'ROOT-MATERIALIZATION-MAPPINGS.NOT-AUTHORITY.json'),next_command=ref(D/'NEXT-ROOT-COMMAND-AND-ORDER.NOT-AUTHORITY.json'),canonical_files_to_write=6,new_Rust_source_files=1,commands=4,new_objects=3,retained_objects=8,Rust_sources=119,candidate_C_functions=80,candidate_selected_Rust_providers=59,candidate_process_C_OBJECTs=31,unchanged_large_evidence_hashed=False,all_actual_calls=0,canonical_or_Git_edits=0,actual_source_ownership_grants=0))
print(json.dumps(dict(decision='PROPOSAL_SOURCE_READY_NOT_RELEASED',ready=ref(D/'SOURCE-READY.json'),profile=profile_ref,canonical_write_count=6,commands=4,new_objects=3,retained_objects=8,blocker='ActualRoot41-or-later independent positivefree, realRootbindings/adoption/materializer/publication/resource/PASS/release')))
