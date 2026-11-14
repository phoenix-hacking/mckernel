"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only preparation; run by Root after actual fresh observation and holder READY.
No observer, query, FD, admission, review decision or workload is executed here.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
A=Path(__file__).resolve().parent
ADAPTER=A.parent/'sdk7-postgrowth-final-static-1/sdk-reference-shape-correction-1/sdk7_authority_adapter.OWNER-REFERENCE-SHAPE.SOURCE-ONLY.py'
def read(p):return json.loads(p.read_bytes())
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def need(ok,message):
 if not ok:raise ValueError(message)
def static_checks():
 inputs=read(A/'STATIC-REUSE-INPUTS.json')
 for row in inputs['copied_scripts']:
  need(ref(Path(row['source']['path']))==row['source'],'original source changed')
  need(ref(Path(row['successor']['path']))==row['successor'],'copied source changed')
  need(row['source']['sha256']==row['successor']['sha256'],'source bytes differ')
 for key in ('request','request_local_identical_copy','static_bundle','query_template','query_command'):
  need(ref(Path(inputs[key]['path']))==inputs[key],'static input changed: '+key)
 need(inputs['request']['sha256']==inputs['request_local_identical_copy']['sha256'],'request copy differs')
 return inputs

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-static',action='store_true');p.add_argument('--bind-reviewed-query',action='store_true');args=p.parse_args();need(not(args.check_static and args.bind_reviewed_query),'choose one mode')
 inputs=static_checks()
 if args.check_static:
  print(json.dumps(dict(status='PASS_BYTE_IDENTICAL_STATIC_REUSE_ONLY',execution_authority=False)));return
 if args.bind_reviewed_query:
  proposal=read(A/'QUERY-RELEASE.PENDING-REVIEW.json');actual=read(A/'ACTUAL-INDEPENDENT-QUERY-RELEASE.json')
  expected=dict(proposal,decision='PASS_READONLY_QUERY_ONLY',reviewer='/root/custody_release_review')
  need(actual==expected,'actual independent query release differs from exact proposal/decision/reviewer')
  write(A/'QUERY-RELEASE-REF.json',ref(A/'ACTUAL-INDEPENDENT-QUERY-RELEASE.json'))
  print(json.dumps(dict(status='BOUND_EXISTING_ACTUAL_QUERY_REVIEW_ONLY',reference=ref(A/'QUERY-RELEASE-REF.json'),SDK_execution_released=False)));return
 for name in ['PREQUERY-BUNDLE.json','QUERY-RELEASE.PENDING-REVIEW.json','QUERY-RELEASE-REF.PENDING.json']:
  need(not (A/name).exists(),'output already exists: '+name)
 for name in ['QUERY-CAPTURE','QUERY-WHOLE-JOIN.json','ACTUAL-READONLY-QUERY.json','ACTUAL-REVIEWED-RELEASE.json','SDK-CAPTURE']:
  need(not os.path.lexists(A/name),'successor already entered: '+name)
 b=read(A/'accepted-finalization-1/SDK7-BUNDLE.STATIC.NOT-RELEASED.json');q=read(A/'QUERY-RELEASE.STATIC.NOT-RELEASED.json');request=read(Path(b['request']['path']))
 parent=Path(request['output_parent_identity']['path'])
 for prefix in ('native-running-modules-admission-','native-running-modules-owner-'):
  need(not os.path.lexists(parent/(prefix+request['nonce'])),'owner nonce namespace already consumed')
 need(Path(request['candidate_root']).is_dir() and not any(Path(request['candidate_root']).iterdir()),'candidate no longer empty')
 head=read(A/'SDK-HEAD-BINDING.json');need(isinstance(head.get('commit'),str) and len(head['commit'])==40,'actual Root HEAD binding required')
 publication=read(A/'ACTUAL-STATIC-PUBLICATION.json')
 need(publication.get('status')=='ROOT_VERIFIED_SAME_BYTES_REUSE_OF_FETCHED_SOURCE_BLOBS' and publication.get('runtime_authority') is None and publication.get('current_fetched_checkpoint')==head['commit'],'actual Root same-bytes publication/HEAD required')
 expected=[dict(source_reference=row['source'],reused_path=row['successor']['path'],same_bytes_required=True) for row in inputs['copied_scripts']]
 need(sorted(publication['rows'],key=lambda r:r['reused_path'])==sorted(expected,key=lambda r:r['reused_path']),'published same-bytes mapping differs')
 holder=read(A/'QUERY-HOLDER.READY.json')
 need(set(holder)=={'pid','starttime','fd','device','inode','uid','nonce','command_hex'},'exact holder READY fields required')
 need(all(type(holder[k]) is int and holder[k]>0 for k in ('pid','starttime')) and type(holder['fd']) is int and holder['fd']>=0 and (holder['device'],holder['inode'],holder['uid'],holder['nonce'])==(27,4,1000,request['nonce']),'holder identity/nonce differs')
 command=bytes.fromhex(holder['command_hex']).split(b'\0');need(any(Path(os.fsdecode(x)).resolve()==A/'hold_query_mutex.py' for x in command if x),'holder command source differs')
 b['live_observation']=ref(A/'LIVE-CURRENT.json')
 spec=importlib.util.spec_from_file_location('reviewed_pure_sdk_adapter',ADAPTER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 need(hashlib.sha256(ADAPTER.read_bytes()).hexdigest()==q['adapter_sha256'],'adapter source differs')
 m.context(b,read(m.ORIGIN),m.load_window(),m.actual_clock())
 write(A/'PREQUERY-BUNDLE.json',b)
 q.update(bundle=ref(A/'PREQUERY-BUNDLE.json'),owned_holder=holder,HEAD=ref(A/'SDK-HEAD-BINDING.json'),static_publication=ref(A/'ACTUAL-STATIC-PUBLICATION.json'))
 need(q['decision'] is None and q['reviewer'] is None and q['SDK_execution_released'] is False,'query proposal must remain unsigned')
 write(A/'QUERY-RELEASE.PENDING-REVIEW.json',q)
 write(A/'QUERY-RELEASE-REF.PENDING.json',dict(path=str(A/'ACTUAL-INDEPENDENT-QUERY-RELEASE.json'),bytes=None,sha256=None,status='PENDING_ACTUAL_INDEPENDENT_REVIEW_NOT_AN_INPUT_REF'))
 print(json.dumps(dict(status='PENDING_ACTUAL_QUERY_REVIEW_NO_RELEASE',bundle=ref(A/'PREQUERY-BUNDLE.json'),proposal=ref(A/'QUERY-RELEASE.PENDING-REVIEW.json'),nonce=request['nonce'],SDK_execution_released=False)))
if __name__=='__main__':main()
