"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Minimal CURRENT112/Root34 source-only helper successor; no operational calls.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;U=D.parent;E=U.parent
P=U/'actual-origin-bound-source-1'
PREV=E/'current113-qualified-lock4-next4-scalar4-union-source-1/root34-admission-preparation-source-1'
ROOT=E.parents[3]
R=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1'
LEDGER=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER34.json'
FREE=E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'
ADOPT=U/'root-source-adoption-1/ROOT-SOURCE-ADOPTION.json'
ORIGIN=U/'oci-origin-bind-correction-source-1/ROOT-ACTUAL-ORIGIN-PRODUCER-RESULT.json'
REVIEW=P/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json'
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
assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='a253477abbd879d505c4d2b20bf6717a1214f4e57b76604af3632f8aedda2153'
assert ref(REVIEW)['sha256'].startswith('487e1523')
assert ref(LEDGER)['sha256']=='c817825d68c8aa736acb9dbe05296b3dec9e40f574dc1a3bf7ef4bfa95bf8f88'
assert ref(FREE)['sha256']=='bf19e5a464ce05f49657acce7e598ce1125d8bf913c85631d5883190290e4890'
p=read(P/'PROFILE.SOURCE-ONLY.json');origin=read(ORIGIN);header=origin['actual_header'];auth(header)
assert len(p['exact_commands'])==4 and sum(not r['replace'] for r in p['inputs']['objects'])==8
assert origin['returncode']==0 and header['sha256']=='aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded'
assert read(LEDGER)['latest_accepted_free_boundary']==ref(FREE)
assert not R.exists()
out=Path(header['path']).parent
# Same Root34 observer and exact original ownership/current controls, byte for byte.
write('observe_root34_current.py',(PREV/'observe_root34_current.py').read_bytes())
capture=(PREV/'capture_resources.py').read_text()
capture=once(capture,"OBSERVER_SHA='"+ref(PREV/'observe_root34_current.py')['sha256']+"'","OBSERVER_SHA='"+ref(D/'observe_root34_current.py')['sha256']+"'")
capture=once(capture,"assert len(runner.source_directory_postimages(profile))==118","assert len(runner.source_directory_postimages(profile))==113")
write('capture_resources.py',capture)
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(name,(P/name).read_bytes())
materializer=(PREV/'materialize_admission.py').read_text()
materializer=once(materializer,"P=Path("+repr(str(E/'current113-qualified-lock4-next4-scalar4-union-source-1/next4-scalar4-logical-line-hold-successor-source-1'))+")","P=Path("+repr(str(P))+")")
materializer=once(materializer,'MATERIALIZE_REVIEWED_CURRENT113_STATIC_INPUTS_AND_HOLDER_ONLY','MATERIALIZE_REVIEWED_CURRENT112_STATIC_INPUTS_AND_HOLDER_ONLY')
materializer=once(materializer,"assert adoption['author']=='/root' and adoption['status']=='ROOT_SOURCE_ADOPTED_CURRENT113_NEXT4_SCALAR4_NOT_BUILT'","assert b['source_adoption']=="+repr(ref(ADOPT))+"\n assert b['independent_source_profile_review']=="+repr(ref(REVIEW))+"\n assert adoption['author']=='/root' and adoption['status']=='ROOT_SOURCE_ADOPTED_QUALIFIED_F03_EVENT2_AND_F06_ALLOC_FREE_ORIGIN_NOT_BUILT'")
materializer=once(materializer,"for row in read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']:","for row in read(Path(read(P/'PROFILE.SOURCE-ONLY.json')['inputs']['source_directory_exports'][0]['manifest']['path']))['files']:")
materializer=once(materializer," origin=read(auth(b['actual_origin_producer']))\n"," assert b['actual_origin_producer']=="+repr(ref(ORIGIN))+"\n origin=read(auth(b['actual_origin_producer']))\n")
materializer=once(materializer,"assert context['command']==template['exact_commands'][3]","assert context['command']==template['exact_commands'][2]")
materializer=once(materializer,"ref(P/'candidate/arch/x86_64/kernel/syscall.c')","ref(Path("+repr(str(U/'candidate/arch/x86_64/kernel/syscall.c'))+"))")
materializer=once(materializer,"ref(P/'candidate/scripts/f06_origin_command_profile.json')","ref(Path("+repr(str(U/'candidate/scripts/f06_origin_command_profile.json'))+"))")
a=""" preview=next(r['postimage'] for r in profile['inputs']['postimages'] if r.get('source_preview_not_runtime_producer'))
 assert preview['sha256']==header['sha256'] and preview['bytes']==header['bytes']
 for row in profile['inputs']['postimages']:
  if row['postimage']==preview:
   row['postimage']=header;row.pop('source_preview_not_runtime_producer');row['actual_origin_producer_receipt']=b['actual_origin_producer']
 for row in profile['cohort_source_bindings']:
  if row['postimage']==preview:row['postimage']=header
"""
b=""" assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='a253477abbd879d505c4d2b20bf6717a1214f4e57b76604af3632f8aedda2153'
 assert len(profile['exact_commands'])==4 and sum(not row['replace'] for row in profile['inputs']['objects'])==8
 assert not any(row.get('source_preview_not_runtime_producer') for row in profile['inputs']['postimages'])
 assert next(row['postimage'] for row in profile['inputs']['postimages'] if row['relative']=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h')==header
 assert profile['origin_source_materialization']['actual_producer_receipt']==b['actual_origin_producer']
 assert profile['origin_source_materialization']['actual_generated_header']==header
"""
materializer=once(materializer,a,b)
materializer=once(materializer,'ACTUAL_CURRENT113_ORIGIN_PRODUCER_BOUND','ACTUAL_CURRENT112_ALREADY_GENERATED_ORIGIN_BOUND_NO_REPLAY')
materializer=once(materializer," export['qualified_readonly_files']=[header if row==preview else row for row in export['qualified_readonly_files']]\n"," assert header in export['qualified_readonly_files']\n")
write('materialize_admission.py',materializer)
# Closed static/current source context; no original113 profile is selected.
context=dict(scope=SCOPE,runtime_authority=None,status='CURRENT112_CLOSED_INPUT_CONTEXT_NO_ACTUAL_ADMISSION',source_profile=ref(P/'PROFILE.SOURCE-ONLY.json'),source_review=ref(REVIEW),actual_seven_file_Root_adoption=ref(ADOPT),actual_origin_producer=ref(ORIGIN),actual_header=header,actual_origin_binding=ref(out/'ORIGIN-BINDING.json'),actual_Rust_environment=ref(out/'rust-environment.json'),actual_CMake_origin=ref(out/'f06_rt_sigreturn_origin.cmake'),Root34=ref(LEDGER),post_Root4_free=ref(FREE),source_map=p['inputs']['source_directory_exports'][0]['manifest'],reuse_descriptor=ref(p['reuse_descriptor']),exact_four_commands=p['exact_commands'],exact_eight_retained_inputs=[r for r in p['inputs']['objects'] if not r['replace']],generation_already_complete_no_replay=True,current113_excluded_and_unchanged=True)
save('CLOSED-ROOT-CONTEXT.NOT-AUTHORITY.json',context)
base=read(PREV/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')
base.update(admission=str(R),source_adoption=ref(ADOPT),independent_source_profile_review=ref(REVIEW),actual_origin_producer=ref(ORIGIN),actual_generated_header=header,actual_origin_binding=ref(out/'ORIGIN-BINDING.json'),actual_Rust_environment=ref(out/'rust-environment.json'),actual_CMake_origin=ref(out/'f06_rt_sigreturn_origin.cmake'))
base['expected_actual_decision']='MATERIALIZE_REVIEWED_CURRENT112_STATIC_INPUTS_AND_HOLDER_ONLY'
save('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',base)
resource=read(PREV/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json');resource['schema_label']='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES retained reviewed schema; actualCURRENT1124commands/113sources/eightretained'
save('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',resource)
py='/home/holden/anaconda3/bin/python3'
commands=[dict(phase='Root-only metadata materialization after review+real bindings; existing origin reused',argv=[py,'-I','-B',str(D/'materialize_admission.py'),'--root-bindings',str(D/'ROOT-ACTUAL-BINDINGS-1.json')]),dict(phase='Fresh physical/current capture BEFORE holder',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--physical-output',str(R/'ROOT-PREHOLDER-PHYSICAL-1.json')]),dict(phase='Exact holder-only entry after real Root bootstrap/publication',argv=[py,'-I','-B',str(R/'hold_and_run_build_only.py'),'--bootstrap-grant',str(R/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')]),dict(phase='Held resource capture after actual holderREADY and real Root resource input',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--admission',str(R),'--root-input',str(R/'ROOT-ACTUAL-RESOURCE-INPUT-1.json')])]
save('EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,status='LITERAL_ORDERED_CURRENT112_PROPOSAL_NOT_EXECUTED',planned_admission=str(R),commands=commands,origin_producer_command_replayed=False,actual_four_compiler_commands=p['exact_commands'],independent_review_before_any_source_materialization_or_currentcapture=True,publish_and_GO='Root publishes/fetch-verifies exact static source, acquires holder only under bootstrap grant, captures genuine resources, obtains exact independent execution review, then binds one-use grant/GO. No new gate/framework.',fresh_resource_age_seconds=120,all_actual_calls=0))
# Small diffs against immediately preceding Root34 admission helpers and exact112 tools.
derivation=[]
for name in ['observe_root34_current.py','capture_resources.py','materialize_admission.py','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 predecessor=PREV/name
 ast.parse((D/name).read_text(),filename=name)
 delta=''.join(difflib.unified_diff(predecessor.read_text().splitlines(keepends=True),(D/name).read_text().splitlines(keepends=True),fromfile='Root34-CURRENT113/'+name,tofile='Root34-CURRENT112/'+name))
 path=write('helper-diffs/'+name+'.diff',delta)
 derivation.append(dict(name=name,predecessor=ref(predecessor),successor=ref(D/name),diff=ref(path),exact_current112_tool=ref(P/name) if (P/name).exists() else None))
save('HELPER-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,helpers=derivation,changes='SameRoot34observerbyteidentical;capture113sources;fourcommand112toolingbyteidentical;materializerexisting112sevenfileadoption/genuineorigin/archivepaths only.',controls_unchanged='Original27:4/scratch21/CPU2-5/12GiB/noswap/512pids/networknone/7jobs/23259332608B, HOST16GiB/scratch12GiB and greater original packet floors; samecreditrun7f4af94a83b14cc08f97401f5891d965/57774.852125 cumulative debits/realholds; fixed05:36:09Z.',tests_or_operations=0))
files=[ref(q) for q in D.rglob('*') if q.is_file() and q.name not in ['prepare_source.py','PREPARATION-MANIFEST.json','SOURCE-READY.json']]
external=[ref(P/n) for n in ['PROFILE.SOURCE-ONLY.json','INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json']]+[ref(REVIEW),ref(ADOPT),ref(ORIGIN),header,ref(out/'ORIGIN-BINDING.json'),ref(out/'rust-environment.json'),ref(out/'f06_rt_sigreturn_origin.cmake'),ref(LEDGER),ref(FREE),p['inputs']['source_directory_exports'][0]['manifest'],ref(p['reuse_descriptor'])]
for row in external:auth(row)
save('PREPARATION-MANIFEST.json',dict(scope=SCOPE,runtime_authority=None,status='SOURCE_ONLY_CURRENT112_ROOT34_METADATA_HOLDER_PREPARATION',files=files,external_inputs=external,current113_selected=False,actual_nonce=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_release=None,all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='CURRENT112_ROOT34_MINIMAL_ADMISSION_HELPER_SUCCESSOR_SOURCE_READY_NOT_RELEASED',runtime_authority=None,manifest=ref(D/'PREPARATION-MANIFEST.json'),closed_root_context=ref(D/'CLOSED-ROOT-CONTEXT.NOT-AUTHORITY.json'),helper_derivation=ref(D/'HELPER-DERIVATION.json'),entry_commands=ref(D/'EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json'),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),commands=4,new_objects=3,retained_objects=8,Rust_sources=113,existing_origin_reused_no_replay=True,current113_unchanged=True,all_actual_calls=0,canonical_or_Git_edits=0))
print(json.dumps(dict(status='CURRENT112_ROOT34_SOURCE_READY_NO_OPERATIONS',ready=ref(D/'SOURCE-READY.json'),manifest=ref(D/'PREPARATION-MANIFEST.json'))))
