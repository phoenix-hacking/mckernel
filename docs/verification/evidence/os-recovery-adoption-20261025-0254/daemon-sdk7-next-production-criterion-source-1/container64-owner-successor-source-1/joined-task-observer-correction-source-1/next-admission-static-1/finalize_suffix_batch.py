"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data assembly and explicit delegation to approved Source28 frontends only.
No operation on import; no nonce generation, clock capture, reservation or grant.
"""
from pathlib import Path
import argparse,json,os,re,runpy,sys,time
HERE=Path(__file__).resolve().parent;S=HERE.parent;D=S.parent;E=D.parents[1]
sys.path.insert(0,str(S))
import suffix_contract as mc
import suffix_owner as owner
READY_SHA='d326fc265198dc13114f711e56830183873ea391605179a37535486eb64f9f5a'
MAP_SHA='573309001bb43c9ffb11c7fc1f5f34e67533b968a6c0db8b74b0f42054fef61a'
LATEST=E/'FIVE-BUILD-INDEPENDENT-POSTJOIN-CURRENT-ACCEPTANCE.json'
LATEST_SHA='bf8d80ab06b1789080453602ae5156b578619d978f38f07eaec9ab4de07786ac'

def write(path,value):
 with Path(path).open('xb') as stream:stream.write(mc.canonical(value))
 Path(path).chmod(0o600)
def read_ref(path,digest):
 path=Path(path).resolve(strict=True);mc.regular(path);raw=path.read_bytes();mc.need(mc.sha(raw)==digest,'exact reference differs: '+str(path))
 return dict(path=str(path),sha256=digest),mc.json_bytes(raw)
def known_consumed():
 old=mc.json_bytes((D/'ROOT-CURRENT-NONCE-LEDGER-ATTESTATION.json').read_bytes())['consumed_nonces']
 result=old+['1fff493f114662040e1147fdcbf5fa32','05779a0ade362eb7876ce6b6ef768877','7cf529a05d0430c6651f07b63168e8e1','86c485c4719a61f118032f283a3f7e62','302eabc386ed259685d41fbec898b174']
 mc.need(len(result)==len(set(result))==21,'known21 consumed exclusions differ');return result
def preflight():
 read_ref(S/'READY.SOURCE-ONLY.json',READY_SHA);_,mapping=read_ref(S/'RUNTIME-SOURCE-MAP.SOURCE-ONLY.json',MAP_SHA)
 mc.need(len(mapping['source_sha256'])==28,'approved Source28 required');owner.validate_runtime_source_bindings(mapping['source_sha256'])
 mc.need(mc.verify_retained_prefix(mc.PREP['retained_prefix_host'])==183,'actual unchanged prefix183 required')
 _,latest=read_ref(LATEST,LATEST_SHA);mc.need(latest.get('decision')=='PASS_FIVE_BUILD_POSTJOIN_CURRENT_PHYSICAL' and latest.get('nonce')=='302eabc386ed259685d41fbec898b174','published actual FIVE current-free boundary differs')
 return mapping,known_consumed()
def frontend(name,args):
 previous=sys.argv
 try:sys.argv=[str(S/name),*args];runpy.run_path(sys.argv[0],run_name='__main__')
 finally:sys.argv=previous
def source_review(path,digest,mapping):
 reference,review=read_ref(path,digest);review=owner.bound(reference)
 mc.need(review.get('decision')=='PASS_SOURCE' and review.get('source_sha256')==mapping['source_sha256'] and review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'','/root'),'actual typed independent Source28 PASS_SOURCE required')
 return reference
def copy_actual(name,reference):
 destination=S/name;source=Path(reference['path']);raw=source.read_bytes();mc.need(mc.sha(raw)==reference['sha256'],'actual source changed')
 if destination.exists():mc.need(destination.read_bytes()==raw,'preserve existing actual binding: '+name)
 else:
  with destination.open('xb') as stream:stream.write(raw)
  destination.chmod(0o600)
def bind(args,mapping,known):
 latest_ref,_=read_ref(args.latest_postjoin,args.latest_postjoin_sha256)
 ledger_ref,ledger=read_ref(args.ledger,args.ledger_sha256);nonces=ledger.get('consumed_nonces')
 mc.need(ledger.get('author')=='/root' and ledger.get('complete_within_declared_current_boundary') is True and ledger.get('root_attests_no_unlisted_post_boundary_execution_or_custody_operation') is True and isinstance(nonces,list) and len(nonces)==len(set(nonces)) and set(known)<=set(nonces) and all(re.fullmatch('[0-9a-f]{32}',str(n)) for n in nonces),'actual complete Root ledger must retain all21 known exclusions')
 mc.need(ledger.get('latest_accepted_free_boundary')==mc.ref(Path(latest_ref['path'])),'Root latest operation/current-free reference differs')
 publication_ref,publication=read_ref(args.publication,args.publication_sha256);mc.need(publication.get('source_map_sha256')==MAP_SHA and publication.get('runtime_authority') is None,'actual Source28 fetched publication required')
 expected={row['path']:row for row in mapping['sources'].values()};observed={}
 rows=publication.get('rows');mc.need(isinstance(rows,list) and len(rows)==28,'exact28 fetched rows')
 for row in rows:
  executing=row['executing_source'];mc.need(executing['path'] not in observed and expected.get(executing['path'])==executing,'fetched executing source differs')
  actual=mc.ref(Path(row['path']));mc.need(actual['bytes']==row['bytes']==executing['bytes'] and actual['sha256']==row['sha256']==executing['sha256'],'actual fetched bytes differ');observed[executing['path']]=executing
 mc.need(observed==expected,'complete fetched28 map required');sr=source_review(args.source_review,args.source_review_sha256,mapping)
 request=mc.json_bytes((S/'SUFFIX-REQUEST.json').read_bytes());mc.need(request['nonce'] not in nonces,'fresh request already consumed')
 for name,reference in [('ROOT-CURRENT-NONCE-LEDGER-ATTESTATION.json',ledger_ref),('ACTUAL-STATIC-SOURCE-PUBLICATION.json',publication_ref)]:copy_actual(name,reference)
 write(HERE/'STATIC-BINDINGS.ACTUAL-DATA-NOT-RELEASED.json',dict(request=mc.ref(S/'SUFFIX-REQUEST.json'),source_review=sr,publication=publication_ref,ledger=ledger_ref,latest_postjoin=latest_ref,runtime_authority=None))
def postjoin():
 request=mc.json_bytes((S/'SUFFIX-REQUEST.json').read_bytes());whole=mc.json_bytes((S/'OWNER-WHOLE-JOIN.json').read_bytes());mc.need(mc.capture_ok(whole) and whole['captures']['stderr']['size']==0,'actual whole caller join0/groups/streams required')
 for stream in ['stdout','stderr']:
  raw=(S/'OWNER-CAPTURE'/stream).read_bytes();mc.need(len(raw)==whole['captures'][stream]['size'] and mc.sha(raw)==whole['captures'][stream]['sha256'],'whole stream differs')
 root=Path(request['owner_evidence_root']);receipt=mc.json_bytes((root/'owner-receipt.json').read_bytes());mc.need(mc.json_bytes((S/'OWNER-CAPTURE/stdout').read_bytes())==receipt,'actual printed owner receipt differs')
 mc.need(receipt['request']==request and receipt['owner_nonce']==request['nonce'] and receipt['status']=='PASS' and receipt['retired'] is True and receipt['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and receipt['cleanup_separately_required'] is False and receipt['terminal_container_retained'] is False,'actual normal owner retirement required')
 owner.validate_library_receipt(receipt['driver_receipt'],request)
 proof=receipt['postflight'];mc.need(proof['container_absent'] is True and proof['all_clients_reaped'] is True and proof['compiler_status']=='PASS','actual normal postflight required')
 mc.need(mc.json_bytes((root/'postflight-proof.json').read_bytes())==proof,'durable postflight differs')
 released=mc.json_bytes((root/'record-release-complete.json').read_bytes());mc.need(released['status']=='OWNED_RECORDS_RELEASED' and released['nonce']==request['nonce'] and released['archive_sha256']==mc.ref(root/'ownership-archive.json')['sha256'],'actual ownership archive/release differs')
 write(HERE/'POSTJOIN-VALIDATION.PENDING-INDEPENDENT-CURRENT.json',dict(status='PASS_RECORDED_SUFFIX_CASES_AND_NORMAL_RETIREMENT_PENDING_INDEPENDENT_CURRENT',recorded_at=time.time(),caller_join_finished_wall=whole.get('finished_wall'),whole_caller=mc.ref(S/'OWNER-WHOLE-JOIN.json'),owner_receipt=mc.ref(root/'owner-receipt.json'),retained_prefix_cases=8,new_corrected_cases=18,passed_prefix_reexecuted=False,historical_1fff_extra_tid=None,native_acceptance=False,production_daemon_acceptance=False,current_physical=None,independent_acceptance=None,parent_tool_join_reference=None))
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['preflight','static','bind','propose','publish','entry','postjoin'])
 for name in ['nonce','ledger','ledger-sha256','publication','publication-sha256','source-review','source-review-sha256','latest-postjoin','latest-postjoin-sha256','admission-sha256','execution-review','execution-review-sha256']:parser.add_argument('--'+name)
 args=parser.parse_args();mapping,known=preflight()
 if args.mode=='preflight':
  request_path=S/'SUFFIX-REQUEST.json'
  if request_path.exists():
   request=mc.json_bytes(request_path.read_bytes());mc.need(request['nonce'] not in known,'prepared nonce consumed');owner.validate_preparation(mc.PREP,request);mc.verify_request_inputs(request)
  print(json.dumps(dict(status='PASS_SOURCE28_REAL_STATIC_API',prefix_files=183,retained_cases=8,new_cases=18,known_consumed_count=len(known),actual_prepared_request=mc.ref(request_path) if request_path.exists() else None,latest_published_current_free=mc.ref(LATEST),runtime_authority=None)));return
 mc.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID1000 caller required')
 if args.mode=='static':
  mc.need(re.fullmatch('[0-9a-f]{32}',str(args.nonce)) is not None and args.nonce not in known,'Root-selected unused32hex nonce required');frontend('prepare_suffix_inputs.py',['--nonce',args.nonce]);request=mc.json_bytes((S/'SUFFIX-REQUEST.json').read_bytes());owner.validate_preparation(mc.PREP,request);mc.verify_request_inputs(request)
 elif args.mode=='bind':bind(args,mapping,known)
 elif args.mode=='propose':
  bound=mc.json_bytes((HERE/'STATIC-BINDINGS.ACTUAL-DATA-NOT-RELEASED.json').read_bytes());sr=bound['source_review'];request=mc.json_bytes((S/'SUFFIX-REQUEST.json').read_bytes())
  frontend('prepare_suffix_release.py',['propose','--source-review',sr['path'],'--source-review-sha256',sr['sha256'],'--admission',str(S/'CURRENT-ADMISSION.ACTUAL-1.json'),'--admission-sha256',args.admission_sha256])
  payload=mc.json_bytes((S/'RELEASE-PAYLOAD.PROPOSAL.json').read_bytes());rr=mc.ref(S/'SUFFIX-REQUEST.json');owner.check_current_admission(payload,request,Path(rr['path']),rr['sha256'])
  write(HERE/'EXACT-EXECUTION-REVIEW-INPUT.json',dict(payload=mc.ref(S/'RELEASE-PAYLOAD.PROPOSAL.json'),reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),request=payload['request'],source_review=sr,current_admission=payload['current_admission'],latest_postjoin=bound['latest_postjoin'],runtime_authority=None))
 elif args.mode=='publish':
  frontend('prepare_suffix_release.py',['publish','--execution-review',args.execution_review,'--execution-review-sha256',args.execution_review_sha256]);rr=mc.ref(S/'SUFFIX-REQUEST.json');er=mc.ref(S/'ACTUAL-REVIEWED-RELEASE.json');owner.authenticate(Path(rr['path']),rr['sha256'],Path(er['path']),er['sha256']);write(HERE/'AUTHENTICATE-PREFLIGHT.ACTUAL.json',dict(status='PASS_REAL_AUTHENTICATE_NO_ENTRY',request=rr,release=er,target_calls=0,nonce_consumed=False))
 elif args.mode=='entry':frontend('run_suffix_owned_capture.py',[])
 else:postjoin()
if __name__=='__main__':main()
