from pathlib import Path
import json,hashlib,copy,os
S="Functional McKernel OS/apps and Rust/assembly migration only; no security testing."
R=Path('/home/holden/mckernel')
rel=Path('docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-5')
B=R/rel; D=B/'actual-owner-consumer-correction-1/next-build-preparation-1'; O=D/'post-ten-build-admission-preparation-1'
P=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/post-ten-build-admission-preparation-1')
P.mkdir(mode=0o700)
def read(p):return json.loads(p.read_text())
def ref(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def save(n,d):
 b=(json.dumps(d,indent=2,sort_keys=True)+'\n').encode()
 for dest in (O/n,P/n):
  with dest.open('xb') as f:f.write(b)
 return ref(P/n)
old=B/'default-image-successor-1/release-assembly-1'
contract=read(old/'REMAINING-COMMANDS.NOT-EXECUTED.json')
operation=read(D/'NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json')
assert ref(D/'NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json')['sha256']=='35befe0d794df69f592d4df9ded809be570e9cc492a0071895f6d92d2cbc39fa'
operation['capture_directory']=str(P/'actual-build-owner-capture-1')
# Literal capture namespace substitution only; accepted argv/owner/request/profile remain exact.
opref=save('BUILD-OPERATION.PENDING-RELEASE.json',operation)
capture=read(D/'NEXT-CAPTURE-ARGV.READY.json');capture['argv'][-3]=str(P/'BUILD-OPERATION.PENDING-RELEASE.json');capture['argv'][-1]=opref['sha256'];capture['operation_sha256']=opref['sha256']
capref=save('CAPTURE-ARGV.PENDING-RELEASE.json',capture)
queries=copy.deepcopy(contract['read_only_admission_commands'])
namespace=copy.deepcopy(contract['namespace_observation'])
oldattempt=str(old.parent/'pinned-full-image-attempt-1')
newattempt=str(P.parent/'pinned-full-image-attempt-2')
namespace['argv'][-1]=namespace['argv'][-1].replace(oldattempt,newattempt).replace("'/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'",repr(str(P/'actual-build-owner-capture-1'))+", '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'")
assert oldattempt not in namespace['argv'][-1]
commands=save('READONLY-ADMISSION-ARGV.NOT-EXECUTED.json',{'scope':S,'status':'PREPARED_ONLY_NOT_RELEASED_OR_EXECUTED','source_contract':ref(old/'REMAINING-COMMANDS.NOT-EXECUTED.json'),'read_only_admission_commands':queries,'namespace_observation':namespace,'namespace_rule':'Existing attempt2/work/evidence must retain pinned UID1000/GID1000 mode0700 identities and work/evidence emptiness. Output/evidence/attempt/lease/common/capture must remain absent. No creation or cleanup operation included. Absence does not prove retirement.','actual_results':None,'independent_readonly_release':None})
proof=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1/CHECKPOINT-A5AB468B-FETCHED.json';proofdata=read(proof)
assert proofdata['status']=='PASS_FETCHED_COMMIT_AND_LOCAL_BLOB_VERIFICATION' and proofdata['commit']==proofdata['fetched_commit']=='a5ab468b24b9104b1b4a8059049121a53a24c81c'
batch=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/m05-readiness-runtime-failure-2/next-batch-binding-preparation-1/coherent-ten-cycle-preparation-1/accepted-first-binding-1/derivation-bounded-correction-1/release-assembly-1/actual-ordered-ten-batch-capture-1'
closed=read(batch/'ACTUAL-CLOSED-CAPTURE.json');assert closed['returncode']==0 and all(closed[k] for k in ('direct_child_joined','process_group_absent','streams_closed'))
G=1073741824
facts={'scope':S,'status':'POST_TEN_SUCCESSOR2_BUILD_ADMISSION_PREPARATION_ONLY','accepted_operation_before_literal_capture_substitution':ref(D/'NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json'),'operation':opref,'capture_argv':capref,'readonly_argv':commands,'accepted_owner':operation['owner'],'accepted_request':operation['request'],'accepted_pure_consumer':operation['actual_pure_request_consumer'],'accepted_whole_successor2':ref(D/'WHOLE-SUCCESSOR2-HANDOFF.json'),'source_publication':ref(proof),'source_publication_status':proofdata['status'],'source_commit':proofdata['commit'],'fetched_commit':proofdata['fetched_commit'],'ten_batch_closed_capture':ref(batch/'ACTUAL-CLOSED-CAPTURE.json'),'ten_batch_invocation_source':ref(batch/'SOURCE-CHECKPOINT-AT-INVOCATION.json'),'ten_batch_actual_observation':closed,'ten_batch_qualification':'Parent reports all10 qualified/positive per-case retirement; independent actual/physical review pending. Outer closure is not formal application acceptance.','current_live_postjoin':None,'independent_ten_batch_physical_acceptance':None,'fresh_admission_results':None,'fresh_capacity_acceptance':None,'fresh_loop_backing_association':None,'root_current_continuity':None,'root_aggregate_reservation':None,'independent_exact_build_release':None,'execution_authorized':False,'actual_build_execution':None,
'planning_memory':{'status':'PROSPECTIVE_ONLY_ROOT_FRESH_AGGREGATE_ADOPTION_REQUIRED','aggregate_limit_GiB':'22.5259','total_reserved_bytes':19*G,'total_reserved_GiB':19,'headroom_GiB':'3.5259','roles':[{'role':'sole heavy container CPUs2-5 / j4','bytes':12*G,'jobs':4},{'role':'ordinary CPU0 lane','bytes':2*G,'jobs':1},{'role':'ordinary CPU6 lane','bytes':2*G,'jobs':1},{'role':'CPU7 owner controller AS envelope','bytes':2*G,'jobs':0},{'role':'root coordinator and outer capture shared control lane','bytes':G,'jobs':1}],'total_planned_jobs':7,'control_lane_note':'Owner/outer capture/root coordinator share the serialized waiting control lane; job accounting is not a process count. The1GiB pooled root/capture envelope is a declared planning reservation, not measured RSS or enforced cgroup. Fresh actual memory and root ledger required. No concurrent heavy.','container_profile':operation['profile']},
'planning_storage':{'declared_budget_authority':ref(old/'DECLARED-HOST-OUTPUT-BUDGET.json'),'root_adoption':'Parent adopts unchanged05b6 fixed envelope; fresh capacity acceptance remains NULL.','host_floor_bytes':16*G,'compiler_output_control_growth_bytes':16106090496,'postbuild_capture_growth_bytes':377487360,'emergency_bytes':679477248,'full_fresh_sparse_gap_bytes':None,'host_required_formula':'17179869184 + max(0, fresh_backing_size -512*fresh_backing_blocks) +16106090496+377487360+679477248','scratch_floor_bytes':12*G,'scratch_readonly_control_capture_growth_bytes':67108864,'scratch_emergency_bytes':679477248,'scratch_required_bytes':13631488000,'fresh_host_available_bytes':None,'fresh_scratch_available_bytes':None,'no_resize_or_lowered_reserves':True},
'failure_history':[{'phase':'attempt1 preflight','facts':'Original owner acquired shared-heavy before request validation, then rejected thin source manifest schema. No attempt1 replay.'},{'phase':'normal API token reconciliation','independent_physical':operation['independent_predecessor_preflight_physical']},{'phase':'accepted source correction','owner_sha256':'dbbf7d952918005a6cfa78feaf1cb711eae32492014aedabece9eb0bcadcb37d','pure_fixture_receipt_sha256':'3b3d01c5ad566bbfe0046edd979f06306f291895d7ac00ce23b00ef998208fbe','history':'First fixture Python3.8 Path.is_relative_to failure preserved; one bounded correction to exact Anaconda3.9 passed.'},{'phase':'actual complete successor2 pure validation','seconds':33.43511123408098,'returncode':0,'receipt':operation['actual_pure_request_consumer'],'no_ImageOwner_run_or_shared_token':True}],
'next_action':'Independent review/release of exact finite read-only argv, then root performs fresh admission and binds genuine postjoin/physical, continuity, aggregate/source publication. Independent exact one-shot build release remains separately required. Prefer eligible functional native/P12 work first. No build/query executed in this metadata preparation.'}
save('EXECUTION-FACTS.PENDING-ROOT.json',facts)
print(json.dumps({p.name:ref(p)['sha256'] for p in O.glob('*.json')},sort_keys=True))
