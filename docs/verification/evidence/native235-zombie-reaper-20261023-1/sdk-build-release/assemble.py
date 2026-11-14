"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Assemble exact release proposal and publication copies, never execute owner/compile.
"""
from pathlib import Path
import ast,hashlib,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7}
B=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1');A=B/'release-assembly';R=Path('/home/holden/mckernel')
OLD=R/'docs/verification/evidence/current68-native235-sdk-v3-actual-build-20261023-1/retained/actual-final-release-and-admission'
def load(p):return json.loads(p.read_text())
def ref(p,expected=None):
 b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
 if expected:assert h==expected,(str(p),h,expected)
 return dict(path=str(p),sha256=h,bytes=len(b))
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()+b'\n'
p=load(B/'SUCCESSOR-REVIEW-PACKET.json');request=load(B/'request.json');req=ref(B/'request.json','544b16e0aa6db1f71cb5a03c543ca948dc5b2e8a6d9650c1485e16b0602cf313');assert request['nonce']=='9850d940ac3649a6b8e7ebebf3251853'
cohort=p['runtime_cohort'];assert len(cohort)==11
for r in cohort.values():assert ref(Path(r['path']),r['sha256'])['bytes']==r['bytes']
source_sha={k:r['sha256']for k,r in cohort.items()}
base=load(OLD/'RELEASE-PAYLOAD-EXCLUDING-EXECUTION-REVIEW.CANONICAL.json')
# Preserve existing release schema/required fields and use honest pending state.
payload={k:base[k]for k in ('schema','author','execution_count','historical_observer')}
payload.update(status='PROPOSED_PAYLOAD_NOT_EXECUTION_RELEASE',boot_id=request['boot_id'],nonce=request['nonce'],terminal_policy=request['terminal_policy'],request=dict(path=req['path'],sha256=req['sha256']),source_sha256=source_sha,source_review=None,fetched_source_verified=False,current_Git_fetched_proof=None,current_live_postjoin=None,fresh_resource_and_ownership_admission=None,
actual_source11_identity_readback=dict(dataset=ref(B/'RUNTIME-COHORT.json'),canonical_guard_result=ref(B/'PURE-PREPARATION-VALIDATION.json')))
assert payload['terminal_policy']=='remove-owned-terminal'
release=A/'release.json';operation=load(OLD/'OPERATION-EXACT-ACTUAL-REQUEST.TEMPLATE.json')
owner=p['owner']['path'];code="import sys,runpy; sys.path.insert(0,'/home/holden/mckernel/scripts'); runpy.run_path("+repr(owner)+",run_name='__main__')"
argv=operation['argv'];argv[argv.index('-c')+1]='7';argv[argv.index('-I')+3]=code
# Explicit lookup after -c's Python form, no shell execution or quoting.
argv[argv.index('--request')+1]=req['path'];argv[argv.index('--request-sha256')+1]=req['sha256'];argv[argv.index('--release')+1]=str(release)
operation.update(actual_nonce=request['nonce'],actual_release=str(release),capture_directory=str(A/'owner-capture-1'),status='EXACT_SUCCESSOR_REQUEST_PENDING_REVIEW_RELEASE',execution_review=None)
write(A/'OPERATION-EXACT-REQUEST.TEMPLATE.json',operation)
capture=Path(base['outer_capture']['source']['path']);cref=ref(capture,base['outer_capture']['source']['sha256'])
payload['outer_capture']=dict(source=dict(path=cref['path'],sha256=cref['sha256']),operation_template=ref(A/'OPERATION-EXACT-REQUEST.TEMPLATE.json'),mechanical_finalization='After actual review/admission/fetched evidence is bound and genuine PASS_EXECUTION receipt exists, write final release.json and replace only ACTUAL_FINAL_RELEASE_SHA256 in this operation; hash final operation and invoke accepted capture once.')
(A/'RELEASE-PAYLOAD.PROPOSED.CANONICAL.json').write_bytes(canonical(payload));write(A/'RELEASE-PAYLOAD.PROPOSED.json',payload)
write(A/'OUTER-CAPTURE-ARGV.TEMPLATE.json',['/usr/bin/taskset','-c','7','/home/holden/anaconda3/bin/python3','-I','-B',str(capture),'--operation',str(A/'operation.json'),'--sha256','ACTUAL_FINAL_OPERATION_SHA256'])
# Copy only the changed provider and new derivatives/preparation. Reuse67
# predecessor source refs already in accepted c10 preparation; no archive copies.
inputmap=load(B/'CURRENT68-ZOMBIE-INPUT-MAP.json');oldprep=load(Path(inputmap['predecessor_preparation']['path']));prior={r['path']:r for r in oldprep['closure']}
reuse=[]
for row in inputmap['rows']:
 n=row['relative'];r=row['source']
 if n=='mcctrl_process.rs':continue
 assert r['sha256']==prior[n]['sha256'] and r['bytes']==prior[n]['bytes'];reuse.append(dict(relative=n,sha256=r['sha256'],bytes=r['bytes'],accepted_preparation=inputmap['predecessor_preparation'],accepted_origin=prior[n]['origin']))
assert len(reuse)==67
write(A/'REUSED-67-ACCEPTED-SOURCE-REFERENCES.json',dict(status='67_UNCHANGED_ACCEPTED_C10_SOURCE_REFERENCES_NO_NEW_COPIES',rows=reuse))
refs=[(B/'derived-runtime/native_running_external_modules_owner.py','derived-runtime/native_running_external_modules_owner.py'),(B/'derived-runtime/native_running_external_modules_offline.py','derived-runtime/native_running_external_modules_offline.py'),(B/'source-modules/mcctrl_process.rs','source-candidate/mcctrl_process.rs')]
refs += [(B/n,n)for n in ('request.json','preparation.json','CURRENT68-ZOMBIE-INPUT-MAP.json','RUNTIME-COHORT.json','SUCCESSOR-REVIEW-PACKET.json','PURE-PREPARATION-VALIDATION.json','staging-once/result.json')]
refs += [(A/n,n)for n in ('OPERATION-EXACT-REQUEST.TEMPLATE.json','RELEASE-PAYLOAD.PROPOSED.CANONICAL.json','RELEASE-PAYLOAD.PROPOSED.json','OUTER-CAPTURE-ARGV.TEMPLATE.json','REUSED-67-ACCEPTED-SOURCE-REFERENCES.json')]
publication=[]
for src,name in refs:
 dst=D/'retained'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes());sr=ref(src);dr=ref(dst);assert sr['sha256']==dr['sha256'];publication.append(dict(private=sr,publication=dr))
write(D/'EXACT-SMALL-PUBLICATION-MAP.json',dict(scope=__doc__.splitlines()[0],status='EXACT_SMALL_SUCCESSOR_COPIES_PENDING_ROOT_GIT_FETCHED_PROOF',selected=publication,reused67=ref(A/'REUSED-67-ACCEPTED-SOURCE-REFERENCES.json'),git_commit=None,fetched_proof=None,private_execution_paths_preserved=True,large_archive_copies=0))
write(A/'ASSEMBLY-RESULT.json',dict(scope=__doc__.splitlines()[0],status='CANONICAL_PAYLOAD_AND_EXACT_OPERATION_READY_PENDING_SOURCE_REVIEW_FRESH_ADMISSION_FETCHED_AND_EXECUTION_REVIEW',request=req,release_payload=ref(A/'RELEASE-PAYLOAD.PROPOSED.CANONICAL.json'),operation=ref(A/'OPERATION-EXACT-REQUEST.TEMPLATE.json'),publication_map=ref(D/'EXACT-SMALL-PUBLICATION-MAP.json'),runtime_cohort=source_sha,author='/root',source_review=None,execution_review=None,compiler_operations=0,root_Docker_guest_operations=0))
print(json.dumps(dict(status='PASS_EXACT_RELEASE_ASSEMBLY_NO_AUTHORITY',request=req,publication_copies=len(publication),reused_source_refs=len(reuse))))
