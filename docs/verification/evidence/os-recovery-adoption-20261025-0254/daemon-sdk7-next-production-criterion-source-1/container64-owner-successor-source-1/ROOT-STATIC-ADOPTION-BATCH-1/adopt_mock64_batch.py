"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-invoked data assembly batch; frozen Source20 and policy remain unchanged.
Only explicit entry/current subcommands can invoke the already authorized consumers.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,re,runpy,sys,time
HERE=Path(__file__).resolve().parent;D=HERE.parent.resolve()
sys.path.insert(0,str(D))  # The ONLY additional import root, matching Root's -I bootstrap.
import mock64_contract as mc
import mock64_owner as owner
BASIS=json.loads((HERE/'STATIC-BASIS.json').read_bytes())
NONCE='1fff493f114662040e1147fdcbf5fa32'
REVIEWER='/root/custody_release_review'

def need(ok,why):
 if not ok:raise ValueError(why)
def read(path):return mc.json_bytes(Path(path).read_bytes())
def ref(path):return mc.ref(Path(path))
def two(reference):return {k:reference[k] for k in ('path','sha256')}
def write(path,value):
 with Path(path).open('xb') as f:f.write(mc.canonical(value))
def verify_static():
 need(str(D)==BASIS['directory'],'exact frozen Source20 directory')
 for expected in BASIS['refs'].values():need(ref(expected['path'])==expected,'static data/source drift: '+expected['path'])
 request=read(D/'MOCK64-REQUEST.json');need(request['nonce']==NONCE,'prepared nonce changed')
 source=read(D/'ROOT-RECORDED-INDEPENDENT-SOURCE-REVIEW.json');mapping=read(D/'EXACT-RUNTIME-SOURCE-MAP.SOURCE-ONLY.json')['source_sha256']
 need(source['decision']=='PASS_SOURCE' and source['reviewer']==REVIEWER and source['implementation_ownership'] is False and source['source_sha256']==mapping,'actual frozen source review differs')
 return request

def frontend(filename,arguments):
 need(filename in ['prepare_mock64_inputs.py','prepare_mock64_release_proposal.py','run_mock64_owned_capture.py'],'closed frozen frontend')
 need(ref(D/filename)==BASIS['refs'][filename],'frozen frontend changed')
 old=sys.argv;sys.argv=[str(D/filename)]+list(arguments)
 try:
  try:runpy.run_path(str(D/filename),run_name='__main__');return 0
  except SystemExit as error:
   if error.code is None:return 0
   if type(error.code) is int:return error.code
   raise
 finally:sys.argv=old

def validated_payload(envelope):
 need(envelope['status']=='PENDING_ACTUAL_INDEPENDENT_EXECUTION_REVIEW_NOT_A_RELEASE','pending envelope required')
 payload=envelope['proposed_release_payload'];digest=mc.sha(mc.canonical(payload))
 need(digest==envelope['reviewed_release_payload_sha256'] and 'execution_review' not in payload,'exact unmodified review payload')
 need(payload['nonce']==NONCE and payload['request']==two(BASIS['refs']['MOCK64-REQUEST.json']),'prepared request/nonce binding')
 return payload,digest

def build_release(envelope,review,review_reference):
 payload,digest=validated_payload(envelope)
 need(review.get('decision')=='PASS_EXECUTION' and review.get('reviewer')==REVIEWER and review.get('implementation_ownership') is False,'actual sole independent execution PASS required')
 need(review.get('reviewed_release_payload_sha256')==digest,'actual execution review hash differs')
 return dict(payload,execution_review=two(review_reference))

def actual_review(path,digest):
 r=ref(path);need(re.fullmatch('[0-9a-f]{64}',digest) is not None and r['sha256']==digest,'actual supplied review SHA differs');return read(path),r

def propose():
 request=verify_static();admission=D/'CURRENT-ADMISSION.ACTUAL-1.json';publication=D/'ACTUAL-STATIC-SOURCE-PUBLICATION.json';need(admission.is_file() and publication.is_file(),'Root fresh capture/admission/publication not present')
 owner.check_current_admission(dict(current_admission=two(ref(admission))),request,D/'MOCK64-REQUEST.json',BASIS['refs']['MOCK64-REQUEST.json']['sha256'])
 code=frontend('prepare_mock64_release_proposal.py',['--source-review',str(D/'ROOT-RECORDED-INDEPENDENT-SOURCE-REVIEW.json'),'--current-admission',str(admission)]);need(code==0,'frozen proposal frontend failed')
 path=D/'RELEASE-PAYLOAD.PENDING-INDEPENDENT-REVIEW.json';payload,digest=validated_payload(read(path))
 result=dict(status='PENDING_ACTUAL_EXECUTION_REVIEW_NO_GRANT',nonce=NONCE,reviewed_release_payload_sha256=digest,pending_envelope=ref(path),source_review=payload['source_review'],current_admission=payload['current_admission'],reviewer_required=REVIEWER,publish_command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'publish','--review','ACTUAL_EXECUTION_REVIEW_PATH','--review-sha256','ACTUAL_EXECUTION_REVIEW_SHA256'],Target_calls=0,runtime_authority=None)
 write(HERE/'EXECUTION-REVIEW-NEEDED.json',result);print(json.dumps(result))

def publish(path,digest):
 request=verify_static();review,r=actual_review(path,digest);envelope=read(D/'RELEASE-PAYLOAD.PENDING-INDEPENDENT-REVIEW.json');release=build_release(envelope,review,r)
 target=D/'ACTUAL-REVIEWED-RELEASE.json';need(not target.exists(),'actual release exists; preserve, no republish/replay')
 # Authenticate exact bytes through the frozen API before publication; no FD/Target call.
 temporary=HERE/'ROOT-REVIEWED-RELEASE.PREPARED.json';write(temporary,release)
 owner.authenticate(D/'MOCK64-REQUEST.json',BASIS['refs']['MOCK64-REQUEST.json']['sha256'],temporary,ref(temporary)['sha256'])
 with target.open('xb') as f:f.write(temporary.read_bytes())
 command=dict(scope=__doc__.splitlines()[0],argv=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'entry'],maximum_invocations=1,request=BASIS['refs']['MOCK64-REQUEST.json'],release=ref(target),execution_review=r,nonce=NONCE,Target_calls=0)
 write(HERE/'ROOT-ENTRY.COMMAND.json',command);print(json.dumps(command))

def entry():
 verify_static();target=D/'ACTUAL-REVIEWED-RELEASE.json';owner.authenticate(D/'MOCK64-REQUEST.json',BASIS['refs']['MOCK64-REQUEST.json']['sha256'],target,ref(target)['sha256'])
 need(not (HERE/'ENTRY-CALLER.STARTED.json').exists(),'entry already consumed; preserve actual attempt')
 stat=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split();started=dict(pid=os.getpid(),starttime=int(stat[19]),pgid=os.getpgid(0),command_hex=Path('/proc/self/cmdline').read_bytes().hex(),entered_wall=time.time(),nonce=NONCE,release=ref(target),frontend=BASIS['refs']['run_mock64_owned_capture.py'])
 write(HERE/'ENTRY-CALLER.STARTED.json',started)
 code=frontend('run_mock64_owned_capture.py',[])
 write(HERE/'ENTRY-CALLER.RETURNED.json',dict(caller=started,function_returned=True,returncode=code,returned_wall=time.time(),process_joined=False))
 return code

def tool_completed(document):
 need(type(document.get('exit_code')) is int and document['exit_code']==0 and document.get('session_id') is None,'genuine completed parent tool exit0 required')
 return document

def current_absence(current,pids):
 rows=current['group_membership_observation']['rows'];need(not current['group_membership_observation'].get('errors'),'unresolved current process observation')
 need(not any(row['pid'] in pids or row['pgrp'] in pids for row in rows),'mock actor or process group remains')
 for pid in pids:need(not Path('/proc',str(pid)).exists(),'known mock numeric actor present')

def afterjoin(tool_path,tool_sha):
 request=verify_static();tool,toolref=actual_review(tool_path,tool_sha);tool_completed(tool)
 joined=read(D/'OWNER-WHOLE-JOIN.json');need(mc.capture_ok(joined),'actual successful owner join required')
 caller=read(HERE/'ENTRY-CALLER.STARTED.json');returned=read(HERE/'ENTRY-CALLER.RETURNED.json');need(returned['caller']==caller and returned['returncode']==0 and returned['function_returned'] is True and returned['process_joined'] is False,'actual frontend return required, not a fabricated process join')
 evidence=Path(request['owner_evidence_root']);receipt=read(evidence/'owner-receipt.json')
 need(receipt['status']==receipt['build_status']=='PASS' and receipt['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and receipt['retired'] is True and receipt['cleanup_separately_required'] is False and receipt['wait_exit_code']==0,'actual owned normal removal/release required')
 need(receipt['request']==request,'owner request differs');owner.validate_library_receipt(receipt['driver_receipt'],request)
 postflight=read(evidence/'postflight-proof.json');need(postflight==receipt['postflight'] and postflight['container_absent'] is True and postflight['all_clients_reaped'] is True,'actual postflight differs')
 release=read(evidence/'record-release-complete.json');need(release['status']=='OWNED_RECORDS_RELEASED' and release['nonce']==NONCE,'actual archived ownership release required')
 pids={joined['pid'],caller['pid']};client_refs=[]
 admission=owner.OUTPUT_PARENT/('native-running-modules-admission-'+NONCE)
 for root in [evidence,admission]:
  statuses=sorted(root.glob('command-*/status.json'));need(statuses,'actual command ledger absent')
  for path in statuses:
   row=read(path);need(row['state']=='exited' and type(row['exit_code']) is int and row['exit_code']>=0 and not row.get('client_retirement_unproven'),'actual client exit unproven');pids.add(row['pid']);client_refs.append(ref(path))
 owner.check_campaign();observer=Path(BASIS['current_observer']['path']);need(ref(observer)==BASIS['current_observer'],'unchanged current observer differs')
 spec=importlib.util.spec_from_file_location('accepted_afterjoin_current_observer',observer);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);current=module.observe()
 current_absence(current,pids);cid=receipt['container_id'];need(cid not in current['docker_observations'][0]['stdout'].splitlines(),'owned mock CID currently present')
 for path in [owner.LEASE,owner.COMMON,Path(owner.shared.SHARED_HEAVY_LOCK_PATH)]:need(not os.path.lexists(path),'owned lease/common/shared remains')
 write(HERE/'AFTERJOIN-CURRENT.READONLY.json',current)
 now=time.time();joined_at=joined['finished_wall'];need(type(joined_at) in (int,float) and math.isfinite(joined_at) and joined_at<=now,'actual join timestamp required')
 validation=dict(status='PASS_EXISTING_MOCK_AND_POSTJOIN_CHECKS_PENDING_INDEPENDENT_ACCEPTANCE',nonce=NONCE,owner_request=BASIS['refs']['MOCK64-REQUEST.json'],owner_join=ref(D/'OWNER-WHOLE-JOIN.json'),actual_parent_tool_result=toolref,caller_started=ref(HERE/'ENTRY-CALLER.STARTED.json'),caller_returned=ref(HERE/'ENTRY-CALLER.RETURNED.json'),owner_receipt=ref(evidence/'owner-receipt.json'),postflight=ref(evidence/'postflight-proof.json'),record_release=ref(evidence/'record-release-complete.json'),actual_client_exit_refs=client_refs,current_observation=ref(HERE/'AFTERJOIN-CURRENT.READONLY.json'),known_mock_numeric_actors_absent=sorted(pids),owned_CID_absent=cid,owner_join_finished_wall=joined_at,current_observed_at=current['observed_at'],validation_finished_wall=now,join_to_validation_seconds=now-joined_at,within180_seconds=now-joined_at<=180,first_compiler_wall=None,first_compiler_wall_reason='Frozen h990 started.json records PID/start ticks, not wall timestamp; no inference presented as observation.',actual_first_compiler_start_record=ref(Path(request['candidate_root'])/'fixture-output/mock-build/started.json'),independent_acceptance=False,production_main_executed=False,real_udev_or_IHK_executed=False,native_acceptance=False,fullgraph_install_accepted=False,M15_file_closure=False)
 write(HERE/'AFTERJOIN-VALIDATION.json',validation)
 proposal=dict(decision=None,reviewer=REVIEWER,independent=True,implementation_ownership=False,nonce=NONCE,validated_evidence=ref(HERE/'AFTERJOIN-VALIDATION.json'),current_observation=validation['current_observation'],scope='26 controlled mock cases/definedreference/ring/oversize plus normal owner/client/container/postjoin current only',production_main_executed=False,native_acceptance=False,fullgraph_install_accepted=False,M15_file_closure=False)
 write(HERE/'AFTERJOIN-ACCEPTANCE.PROPOSAL.NOT-ACTUAL.json',proposal);print(json.dumps(dict(status=validation['status'],validation=ref(HERE/'AFTERJOIN-VALIDATION.json'),join_to_validation_seconds=validation['join_to_validation_seconds'],within180_seconds=validation['within180_seconds'],actual_independent_acceptance=None)))

def bind_acceptance(path,digest):
 review,r=actual_review(path,digest);proposal=read(HERE/'AFTERJOIN-ACCEPTANCE.PROPOSAL.NOT-ACTUAL.json');expected=dict(proposal,decision='PASS_DAEMON64_MOCK_PARITY_AND_POSTJOIN_CURRENT')
 need(all(review.get(k)==v for k,v in expected.items()),'actual independent exactscope acceptance differs')
 validation=read(HERE/'AFTERJOIN-VALIDATION.json');now=time.time();seconds=now-validation['owner_join_finished_wall']
 result=dict(status='ACTUAL_INDEPENDENT_ACCEPTANCE_BOUND',acceptance=r,owner_join_finished_wall=validation['owner_join_finished_wall'],acceptance_bound_wall=now,join_to_acceptance_upper_bound_seconds=seconds,within180_seconds=seconds<=180,actual_review_observed_at=review.get('actual_review_observed_at'),timestamp_scope='Binding time is an observed upper bound; exact reviewer timestamp remains unknown when absent.',blocker=None if seconds<=180 else 'ACCEPTED_SCOPE_BUT_JOIN_TO_ACCEPTANCE_BUDGET_EXCEEDED',production_main_executed=False,native_acceptance=False,M15_file_closure=False)
 write(HERE/'ACTUAL-ACCEPTANCE.BOUND.json',result);print(json.dumps(result))

def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
 s.add_parser('propose');pub=s.add_parser('publish');pub.add_argument('--review',type=Path,required=True);pub.add_argument('--review-sha256',required=True);s.add_parser('entry')
 aft=s.add_parser('afterjoin');aft.add_argument('--parent-tool-result',type=Path,required=True);aft.add_argument('--parent-tool-sha256',required=True)
 accept=s.add_parser('bind-acceptance');accept.add_argument('--review',type=Path,required=True);accept.add_argument('--review-sha256',required=True)
 args=p.parse_args()
 try:
  if args.action=='propose':propose()
  elif args.action=='publish':publish(args.review,args.review_sha256)
  elif args.action=='entry':return entry()
  elif args.action=='afterjoin':afterjoin(args.parent_tool_result,args.parent_tool_sha256)
  else:bind_acceptance(args.review,args.review_sha256)
 except Exception as error:
  # Preserve every failure. This is a blocker report, never an acceptance or retry.
  path=HERE/(args.action.upper()+'.BLOCKER.json')
  if not path.exists():write(path,dict(status='BLOCKED_NO_ACCEPTANCE',action=args.action,error=repr(error),observed_wall=time.time(),timestamp_is_not_admission=True,Target_replay=False,runtime_authority=None))
  raise
 return 0
if __name__=='__main__':raise SystemExit(main())
