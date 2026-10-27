"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only assembly and explicit dispatch to unchanged approved frontends.
Nothing runs on import. This helper creates no nonce, clock, reservation or grant.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,runpy,sys
HERE=Path(__file__).resolve().parent
R=HERE.parent;D=R.parents[1];E=D.parents[1]
sys.path.insert(0,str(R))
import repro_contract as mc
import repro_owner as owner
READY_SHA='9e1f69b971c1cf6f92203267d3b02bc373a9bc7b7c7a7cd6ea0428f7a5c3d26b'
MAP_SHA='9f16dd3ad1325cb5b2e160145c9f8cf3239ae4eef223ca8c5ac5ede832302146'
LATEST=E/'NEXT10-DEFAULT-INDEPENDENT-ARTIFACT-AND-POSTJOIN-ACCEPTANCE.json'
LATEST_SHA='b9edb7a5c8cf9355cab4defa1fc1fbd8713f22ee91e77cd91c021e273d24d483'
OLD_LEDGER=D/'ROOT-CURRENT-NONCE-LEDGER-ATTESTATION.json'
FAILED_NONCE='1fff493f114662040e1147fdcbf5fa32'
NEXT_NONCE='05779a0ade362eb7876ce6b6ef768877'

def write(path,value):
 with Path(path).open('xb') as stream:stream.write(mc.canonical(value))
 Path(path).chmod(0o600)
def read_ref(path,digest):
 path=Path(path).resolve(strict=True);mc.regular(path);raw=path.read_bytes()
 mc.need(mc.sha(raw)==digest,'exact supplied reference differs: '+str(path))
 return dict(path=str(path),sha256=digest),mc.json_bytes(raw)
def preflight():
 read_ref(R/'READY.SOURCE-ONLY.json',READY_SHA);_,mapping=read_ref(R/'RUNTIME-SOURCE-MAP.SOURCE-ONLY.json',MAP_SHA)
 mc.need(len(mapping['source_sha256'])==25,'approved25 map required')
 owner.validate_runtime_source_bindings(mapping['source_sha256'])
 _,latest=read_ref(LATEST,LATEST_SHA)
 mc.need(latest.get('decision')=='PASS_SUPPORTED_PROFILE_NEXT10_ARTIFACT_AND_RETAINED_POSTJOIN' and latest.get('nonce')==NEXT_NONCE and latest.get('independent') is True and latest.get('implementation_ownership') is False,'actual latest accepted NEXT10 boundary differs')
 old=mc.json_bytes(OLD_LEDGER.read_bytes());known=old['consumed_nonces']+[FAILED_NONCE,NEXT_NONCE]
 mc.need(len(known)==len(set(known))==18,'exact retained18 exclusion list')
 return mapping,known
def call_frontend(filename,args):
 previous=list(sys.argv)
 try:
  sys.argv=[str(R/filename),*args];runpy.run_path(sys.argv[0],run_name='__main__')
 finally:sys.argv=previous
def root_static_refs(args,known):
 _,ledger=read_ref(args.ledger,args.ledger_sha256)
 mc.need(ledger.get('author')=='/root' and ledger.get('complete_within_declared_current_boundary') is True and ledger.get('root_attests_no_unlisted_post_boundary_execution_or_custody_operation') is True and set(ledger.get('consumed_nonces',[]))==set(known) and len(ledger['consumed_nonces'])==18,'actual current Root18 ledger required')
 mc.need(ledger.get('latest_accepted_free_boundary')==mc.ref(LATEST),'Root ledger must name actual latest NEXT10 acceptance')
 _,publication=read_ref(args.publication,args.publication_sha256)
 mc.need(publication.get('source_map_sha256')==MAP_SHA and publication.get('runtime_authority') is None,'actual approved25 publication binding required')
 rows=publication.get('rows');mc.need(isinstance(rows,list) and len(rows)==25,'actual25 fetched source rows')
 expected={row['path']:row for row in mc.json_bytes((R/'RUNTIME-SOURCE-MAP.SOURCE-ONLY.json').read_bytes())['sources'].values()}
 observed={}
 for row in rows:
  source=row['executing_source'];mc.need(source['path'] not in observed and expected.get(source['path'])==source,'fetched executing source differs')
  retained=Path(row['path']);mc.regular(retained);raw=retained.read_bytes();mc.need(len(raw)==source['bytes']==row['bytes'] and mc.sha(raw)==source['sha256']==row['sha256'],'fetched source bytes differ');observed[source['path']]=source
 mc.need(observed==expected,'complete fetched source identity map required')
 for target,source in [('ROOT-CURRENT-NONCE-LEDGER-ATTESTATION.json',Path(args.ledger)),('ACTUAL-STATIC-SOURCE-PUBLICATION.json',Path(args.publication))]:
  path=R/target
  if path.resolve()==source.resolve():continue
  mc.need(not path.exists(),'preserve existing actual static record: '+target)
  with path.open('xb') as stream:stream.write(source.read_bytes())
  path.chmod(0o600)
def static(args,mapping,known):
 mc.need(re.fullmatch('[0-9a-f]{32}',str(args.nonce)) is not None and args.nonce not in known,'Root-selected unused32hex nonce required')
 root_static_refs(args,known)
 call_frontend('prepare_repro_inputs.py',['--nonce',args.nonce])
 request_path=R/'REPRO-REQUEST.json';request=mc.json_bytes(request_path.read_bytes())
 # Real APIs, before any clock or target command. No validate_request/execute.
 owner.validate_preparation(mc.PREP,request);mc.verify_request_inputs(request)
 mc.need(request['nonce']==args.nonce and request['image_id']==owner.IMAGE and request['driver']['sha256']==mapping['source_sha256']['scripts/native_running_external_modules_offline.py'],'real request API differs')
 write(HERE/'STATIC-PREFLIGHT.ACTUAL-DATA-NOT-RELEASED.json',dict(status='PASS_REAL_OWNER_STATIC_APIS_NOT_RELEASED',request=mc.ref(request_path),source_map=mc.ref(R/'RUNTIME-SOURCE-MAP.SOURCE-ONLY.json'),latest_postjoin=mc.ref(LATEST),consumed_nonces=known,real_api_checks=['validate_runtime_source_bindings','validate_preparation','verify_request_inputs'],image=owner.IMAGE,runtime_authority=None))
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['preflight','static','propose','publish','entry'])
 for name in ['nonce','ledger','ledger-sha256','publication','publication-sha256','source-review','source-review-sha256','admission-sha256','execution-review','execution-review-sha256']:parser.add_argument('--'+name)
 args=parser.parse_args();mapping,known=preflight()
 if args.mode=='preflight':print(json.dumps(dict(status='PASS_REAL_RUNTIME_SOURCE_API_LATEST_BOUNDARY',source_count=25,known_consumed_count=18,latest_postjoin=mc.ref(LATEST),runtime_authority=None)));return
 mc.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID1000 preparation/entry caller')
 if args.mode=='static':static(args,mapping,known)
 elif args.mode=='propose':
  request=mc.json_bytes((R/'REPRO-REQUEST.json').read_bytes());mc.need(request['nonce'] not in known,'consumed nonce')
  # Exact inherited proposer handles real source-review/ref shape and full map.
  call_frontend('prepare_repro_release.py',['propose','--source-review',args.source_review,'--source-review-sha256',args.source_review_sha256,'--admission',str(R/'CURRENT-ADMISSION.ACTUAL-1.json'),'--admission-sha256',args.admission_sha256])
  payload=mc.json_bytes((R/'RELEASE-PAYLOAD.PROPOSAL.json').read_bytes())
  # Check all actual binding and review APIs up to the deliberately missing
  # execution review; no fabricated PASS record or admission clock is supplied.
  owner.validate_runtime_source_bindings(payload['source_sha256'])
  rr=mc.ref(R/'REPRO-REQUEST.json')
  owner.check_current_admission(payload,request,Path(rr['path']),rr['sha256'])
  write(HERE/'EXACT-EXECUTION-REVIEW-INPUT.json',dict(payload=mc.ref(R/'RELEASE-PAYLOAD.PROPOSAL.json'),reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),request=payload['request'],source_review=payload['source_review'],current_admission=payload['current_admission'],latest_postjoin=mc.ref(LATEST),runtime_authority=None))
 elif args.mode=='publish':
  call_frontend('prepare_repro_release.py',['publish','--execution-review',args.execution_review,'--execution-review-sha256',args.execution_review_sha256])
  rr=mc.ref(R/'REPRO-REQUEST.json');er=mc.ref(R/'ACTUAL-REVIEWED-RELEASE.json')
  owner.authenticate(Path(rr['path']),rr['sha256'],Path(er['path']),er['sha256'])
  write(HERE/'AUTHENTICATE-PREFLIGHT.ACTUAL.json',dict(status='PASS_REAL_OWNER_AUTHENTICATE_NO_ENTRY',request=rr,release=er,target_calls=0,nonce_consumed=False))
 else:call_frontend('run_repro_owned_capture.py',[])
if __name__=='__main__':main()
