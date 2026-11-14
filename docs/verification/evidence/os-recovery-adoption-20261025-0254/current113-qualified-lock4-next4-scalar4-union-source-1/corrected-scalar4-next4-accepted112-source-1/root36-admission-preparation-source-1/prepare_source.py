"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded CURRENT113 Root36 admission source successor. No operational calls.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;CAND=D.parent;P=CAND/'final-scope-source-1';E=D.parents[2]
PREV=E/'current112-ready-f06-event2-coherent-source-1/root34-admission-preparation-source-1'
ROOT=E.parents[3]
R=E/'ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1'
LEDGER=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER36.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
assert ref(LEDGER)['sha256'].startswith('4534fe9e') and ref(LEDGER)['bytes']==4870
ledger=read(LEDGER);FREE=auth(ledger['latest_accepted_free_boundary']);assert ref(FREE)['sha256'].startswith('85ce9349')
assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='b027f2a5d1f2ef909638056815f6a066561df2dcd7a9a9532e9d0304a583bfe1'
p=read(P/'PROFILE.SOURCE-ONLY.json');assert len(p['exact_commands'])==4 and sum(not r['replace'] for r in p['inputs']['objects'])==8
assert not R.exists()
# Only exact latest reviewed ownership metadata changes; unchanged baseline implementation reused.
observer=(PREV/'observe_root34_current.py').read_text()
oldledger=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER34.json'
oldfree=E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'
observer=observer.replace(str(oldledger),str(LEDGER)).replace(str(oldfree),str(FREE))
observer=observer.replace(str(ref(oldledger)['bytes']),str(ref(LEDGER)['bytes'])).replace(ref(oldledger)['sha256'],ref(LEDGER)['sha256'])
observer=observer.replace(str(ref(oldfree)['bytes']),str(ref(FREE)['bytes'])).replace(ref(oldfree)['sha256'],ref(FREE)['sha256'])
observer=observer.replace('PASS_POSITIVE_ROOT4_NATIVE_OWNER_RETIREMENT_AND_CURRENT_FREE','PASS_POSITIVE_STARTUP_FAILED_BATCH_RETIREMENT_AND_CURRENT_FREE')
observer=once(observer,"review['evidence']['retained_owner_and_guest_snapshot']","review['evidence']['RETAINED-OWNER-AND-GUEST-SNAPSHOT.json']")
observer=once(observer,"review['fresh_current']['all_owned_pids_and_groups_absent']","review['fresh_current']['all_28_owned_pids_and_groups_absent']")
observer=observer.replace('Root34','Root36').replace('root34','root36').replace('Root4/','startup/').replace('POSTROOT4','POSTSTARTUP')
write('observe_root36_current.py',observer)
capture=(PREV/'capture_resources.py').read_text()
capture=once(capture,"OBSERVER=D/'observe_root34_current.py'","OBSERVER=D/'observe_root36_current.py'")
capture=once(capture,"OBSERVER_SHA='"+ref(PREV/'observe_root34_current.py')['sha256']+"'","OBSERVER_SHA='"+ref(D/'observe_root36_current.py')['sha256']+"'")
capture=once(capture,"assert len(runner.source_directory_postimages(profile))==113","assert len(runner.source_directory_postimages(profile))==118")
capture=once(capture,repr(ref(oldledger)),repr(ref(LEDGER)));capture=once(capture,repr(ref(oldfree)),repr(ref(FREE)))
write('capture_resources.py',capture)
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(n,(P/n).read_bytes())
# Minimal retained materializer adaptation: actual113 adoption/origin are Root-filled, never guessed.
materializer=(PREV/'materialize_admission.py').read_text()
oldP=E/'current112-ready-f06-event2-coherent-source-1/actual-origin-bound-source-1'
materializer=once(materializer,"P=Path("+repr(str(oldP))+")","P=Path("+repr(str(P))+")")
materializer=once(materializer,'MATERIALIZE_REVIEWED_CURRENT112_STATIC_INPUTS_AND_HOLDER_ONLY','MATERIALIZE_REVIEWED_CURRENT113_STATIC_INPUTS_AND_HOLDER_ONLY')
materializer=once(materializer,repr(ref(oldledger)),repr(ref(LEDGER)));materializer=once(materializer,repr(ref(oldfree)),repr(ref(FREE)))
oldadopt=E/'current112-ready-f06-event2-coherent-source-1/root-source-adoption-1/ROOT-SOURCE-ADOPTION.json'
oldreview=oldP/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json'
materializer=once(materializer," assert b['source_adoption']=="+repr(ref(oldadopt))+"\n",'')
materializer=once(materializer," assert b['independent_source_profile_review']=="+repr(ref(oldreview))+"\n",'')
materializer=once(materializer,'ROOT_SOURCE_ADOPTED_QUALIFIED_F03_EVENT2_AND_F06_ALLOC_FREE_ORIGIN_NOT_BUILT','ROOT_SOURCE_ADOPTED_CURRENT113_CORRECTED_SCALAR4_NEXT4_NOT_BUILT')
oldorigin=E/'current112-ready-f06-event2-coherent-source-1/oci-origin-bind-correction-source-1/ROOT-ACTUAL-ORIGIN-PRODUCER-RESULT.json'
materializer=once(materializer," assert b['actual_origin_producer']=="+repr(ref(oldorigin))+"\n",'')
# No producer receipt/header ref exists here until Root actually runs that exact producer.
materializer=once(materializer,"ref(Path("+repr(str(E/'current112-ready-f06-event2-coherent-source-1/candidate/arch/x86_64/kernel/syscall.c'))+"))","ref(Path("+repr(str(CAND/'candidate/arch/x86_64/kernel/syscall.c'))+"))")
materializer=once(materializer,"ref(Path("+repr(str(E/'current112-ready-f06-event2-coherent-source-1/candidate/scripts/f06_origin_command_profile.json'))+"))","ref(Path("+repr(str(CAND/'candidate/scripts/f06_origin_command_profile.json'))+"))")
old=""" assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='a253477abbd879d505c4d2b20bf6717a1214f4e57b76604af3632f8aedda2153'
 assert len(profile['exact_commands'])==4 and sum(not row['replace'] for row in profile['inputs']['objects'])==8
 assert not any(row.get('source_preview_not_runtime_producer') for row in profile['inputs']['postimages'])
 assert next(row['postimage'] for row in profile['inputs']['postimages'] if row['relative']=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h')==header
 assert profile['origin_source_materialization']['actual_producer_receipt']==b['actual_origin_producer']
 assert profile['origin_source_materialization']['actual_generated_header']==header
"""
new=""" assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='b027f2a5d1f2ef909638056815f6a066561df2dcd7a9a9532e9d0304a583bfe1'
 assert len(profile['exact_commands'])==4 and sum(not row['replace'] for row in profile['inputs']['objects'])==8
 preview=next(row['postimage'] for row in profile['inputs']['postimages'] if row.get('source_preview_not_runtime_producer'))
 assert preview['bytes']==header['bytes'] and preview['sha256']==header['sha256']
 for row in profile['inputs']['postimages']:
  if row['postimage']==preview:
   row['postimage']=header;row.pop('source_preview_not_runtime_producer');row['actual_origin_producer_receipt']=b['actual_origin_producer']
 for row in profile['cohort_source_bindings']:
  if row['postimage']==preview:row['postimage']=header
 profile['source_preparation_current_context']=dict(runtime_authority=None,Root36=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],actual_admission_required=True)
"""
materializer=once(materializer,old,new)
materializer=once(materializer,'ACTUAL_CURRENT112_ALREADY_GENERATED_ORIGIN_BOUND_NO_REPLAY','ACTUAL_CURRENT113_GENUINE_ORIGIN_BOUND_NO_BUILD_REPLAY')
materializer=once(materializer," assert header in export['qualified_readonly_files']\n"," export['qualified_readonly_files']=[header if row==preview else row for row in export['qualified_readonly_files']]\n")
write('materialize_admission.py',materializer)
# Exact selectable adoption inputs, genuine actual receipt remains null.
source_map=read(Path(p['inputs']['source_directory_exports'][0]['manifest']['path']))
adopt=[]
for row in p['inputs']['postimages']:
 if row.get('source_preview_not_runtime_producer'):continue
 adopt.append((row['relative'],row['postimage']))
for row in source_map['files']:
 if row['kind']!='unchanged adopted CURRENT112 source':adopt.append(('kernel/rust/'+row['relative'],row['snapshot']))
adopt += [('scripts/derive_f06_origin.py',ref(CAND/'candidate/scripts/derive_f06_origin.py')),('scripts/f06_origin_command_profile.json',ref(CAND/'candidate/scripts/f06_origin_command_profile.json'))]
rows=[]
for relative,candidate in adopt:
 canonical=ROOT/relative;rows.append(dict(relative=relative,canonical_path=str(canonical),current_preimage=ref(canonical) if canonical.exists() else None,private_source=candidate))
save('ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,required_Root_status='ROOT_SOURCE_ADOPTED_CURRENT113_CORRECTED_SCALAR4_NEXT4_NOT_BUILT',files=rows,actual_Root_adoption=None,LOCK4_WAK3_bulkdebug32_excluded=True))
bindings=read(PREV/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')
bindings.update(status='CURRENT113_ROOT36_TEMPLATE_NOT_AUTHORITY',admission=str(R),nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),expected_actual_decision='MATERIALIZE_REVIEWED_CURRENT113_STATIC_INPUTS_AND_HOLDER_ONLY')
for k in ['source_adoption','independent_source_profile_review','actual_origin_producer','actual_generated_header','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:bindings[k]=None
save('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',bindings)
resource=read(PREV/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json');resource.update(nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),schema_label='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES retained existing schema; actualCURRENT113fourcommands/118sources/eightretained, no kernelC rebuild')
save('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',resource)
py='/home/holden/anaconda3/bin/python3';origin_proposal=read(CAND/'NEW-ORIGIN-PRODUCER.NOT-GRANTED.json')
commands=[dict(phase='Fresh actual113origin producer only after Root source review/authorization',argv=origin_proposal['argv']),dict(phase='Root static metadata materializer after genuine source-adoption/origin receipts and real bindings',argv=[py,'-I','-B',str(D/'materialize_admission.py'),'--root-bindings',str(D/'ROOT-ACTUAL-BINDINGS-1.json')]),dict(phase='Fresh current physical capture before holder under actual Root authority',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--physical-output',str(R/'ROOT-PREHOLDER-PHYSICAL-1.json')]),dict(phase='Actual holder-only entry after bootstrap/sourcepublication',argv=[py,'-I','-B',str(R/'hold_and_run_build_only.py'),'--bootstrap-grant',str(R/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')]),dict(phase='Held resource capture after genuine holderREADY and actual Root resource input',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--admission',str(R),'--root-input',str(R/'ROOT-ACTUAL-RESOURCE-INPUT-1.json')])]
save('EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,status='ROOT36_ORDERED_LITERAL_PROPOSAL_NOT_EXECUTED',planned_admission=str(R),commands=commands,actual_four_compiler_commands=p['exact_commands'],actual_origin_producer_receipt=None,actual_generated_header=None,actual_materialization=None,actual_holder=None,actual_resource_authority=None,actual_execution_grant=None,required_before_fresh_capture='Independent source/helper review and Root-authored exact origin/adoption/bindings. Complete sourcepublication/fetchverification, holder-only grant, actual resource capture, independent executionPASS then one-use grant/GO.',resource_maximum_age_seconds=120,all_actual_calls=0))
helpers=[]
for n in ['observe_root36_current.py','capture_resources.py','materialize_admission.py','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 oldpath=PREV/('observe_root34_current.py' if n=='observe_root36_current.py' else n)
 ast.parse((D/n).read_text(),filename=n)
 delta=''.join(difflib.unified_diff(oldpath.read_text().splitlines(keepends=True),(D/n).read_text().splitlines(keepends=True),fromfile='Root34-CURRENT112/'+oldpath.name,tofile='Root36-CURRENT113/'+n))
 diff=write('helper-diffs/'+n+'.diff',delta);helpers.append(dict(name=n,predecessor=ref(oldpath),successor=ref(D/n),diff=ref(diff),current113tool=ref(P/n) if (P/n).exists() else None))
save('HELPER-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,helpers=helpers,changes='Original machinery only: exact Root36/lateststartup retirement source metadata;113fourcommands/118Rust; Root-filled fresh113origin and correctedscalar+next4 canonical-adoption mappings. No new framework/global observer.',all_actual_calls=0))
save('CLOSED-ROOT36-CONTEXT.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,Root36=ref(LEDGER),latest_accepted_free=ref(FREE),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),source_ready=ref(P/'SOURCE-READY.json'),source_map=p['inputs']['source_directory_exports'][0]['manifest'],reuse_descriptor=ref(p['reuse_descriptor']),new_origin_proposal=ref(CAND/'NEW-ORIGIN-PRODUCER.NOT-GRANTED.json'),actual_origin_producer_receipt=None,actual_generated_header=None,actual_origin_environment=None,actual_source_adoption=None,actual_source_publication=None,actual_resource_authority=None,actual_holder=None,actual_nonce=None,actual_output_root=None,actual_execution_review=None,actual_release=None,fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs'],controls='Samecreditrun7f4af94a83b14cc08f97401f5891d965/57774.852125/cumulative debits/realholds; CPU2-5/12GiB/noswap/512pids/networknone; oneheavy/permanent27:4/scratch21;7aggregatejobs/23259332608B and original floors. No old clock/release renewed.',preserved_source_failures=[ref(CAND/n) for n in ['PREPARATION-FIRST-FAILURE.json','PREPARATION-SECOND-FAILURE.json']],current112_accepted_unchanged=True,current113_original_blocked_profiles_unchanged=True))
files=[ref(q) for q in D.rglob('*') if q.is_file() and q.name not in ['prepare_source.py','PREPARATION-MANIFEST.json','SOURCE-READY.json']]
external=[ref(P/'PROFILE.SOURCE-ONLY.json'),ref(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),ref(P/'SOURCE-READY.json'),p['inputs']['source_directory_exports'][0]['manifest'],ref(p['reuse_descriptor']),ref(CAND/'NEW-ORIGIN-PRODUCER.NOT-GRANTED.json'),ref(LEDGER),ref(FREE)]
for row in external:auth(row)
save('PREPARATION-MANIFEST.json',dict(scope=SCOPE,runtime_authority=None,status='SOURCE_ONLY_CURRENT113_ROOT36_ADMISSION_PREPARATION',files=files,external_inputs=external,all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='CURRENT113_ROOT36_ADMISSION_SOURCE_SUCCESSOR_READY_NOT_RELEASED',runtime_authority=None,manifest=ref(D/'PREPARATION-MANIFEST.json'),closed_context=ref(D/'CLOSED-ROOT36-CONTEXT.NOT-AUTHORITY.json'),helper_derivation=ref(D/'HELPER-DERIVATION.json'),adoption_inputs=ref(D/'ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json'),entry_commands=ref(D/'EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json'),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),Root36=ref(LEDGER),latest_free=ref(FREE),commands=4,new_objects=3,retained_objects=8,Rust_sources=118,actual_origin_outputs=None,actual_adoption=None,actual_grant=None,all_actual_calls=0,canonical_or_Git_changes=0))
print(json.dumps(dict(status='CURRENT113_ROOT36_SOURCE_READY_NO_OPERATIONS',ready=ref(D/'SOURCE-READY.json'),manifest=ref(D/'PREPARATION-MANIFEST.json'))))
