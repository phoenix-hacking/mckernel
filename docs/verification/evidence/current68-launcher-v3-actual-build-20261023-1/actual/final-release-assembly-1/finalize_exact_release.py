"""Mechanical exact release binding only; Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import argparse,hashlib,json
D=Path(__file__).resolve().parent;L=D.parent;B=L/'bound-source-1'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),sha256=sha(raw),bytes=len(raw))
def load(path):return json.loads(Path(path).read_bytes())
def exact(path,digest):
 r=ref(path);assert r['sha256']==digest;return load(path),r
def save(path,value):
 with Path(path).open('xb')as stream:stream.write((json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())
def main():
 p=argparse.ArgumentParser();p.add_argument('--resource-grant',required=True);p.add_argument('--resource-grant-sha256',required=True);p.add_argument('--execution-authority',required=True);p.add_argument('--execution-authority-sha256',required=True);a=p.parse_args()
 grant,grantref=exact(a.resource_grant,a.resource_grant_sha256);authority,authorityref=exact(a.execution_authority,a.execution_authority_sha256);packet=load(D/'ACTUAL-FINAL-REQUEST-REVIEW-PACKET.json')
 assert grant['latest_retired_predecessor_event']==packet['newest_retired_predecessor']and grant['admission']==packet['admission']and grant['heavy_operations']==1 and grant['pids']==512 and grant['network']=='none'and grant['jobs']==1
 assert grant.get('status')not in('NOT_RELEASED_RESOURCE_GRANT_PAYLOAD',None)or grant.get('granted')is True
 assert authority['decision']=='RELEASE_EXACT_ONE_V3_PINNED_LAUNCHER_ONLY_BUILD_AFTER_FRESH_ADMISSION'and authority['independent_conditional_review']and authority['resource_grant']==grantref and authority['latest_retired_predecessor']==packet['newest_retired_predecessor']
 assert authority['owner_sha256']==packet['owner']['sha256']and authority['driver_sha256']==packet['driver']['sha256']and authority['source_sha256']=='8f9fbe474220433118e6662c9f2517f73a547730575b83ffb73255d06e9b40d7'
 request=load(D/'pinned-launcher-request.FINAL-PAYLOAD-NOT-RELEASED.json');pending=request['pending_root_execution_authority'];pending.update(independent_exact_execution_release=authorityref,fresh_resource_grant=grantref)
 save(D/'pinned-launcher-request.FINAL.json',request);binding=load(D/'ROOT-FINAL-REQUEST-BINDING.PAYLOAD.json');binding.update(decision='PASS_FINAL_REQUEST_EXACT_RELEASE_BINDING_ONE_INVOCATION',request=ref(D/'pinned-launcher-request.FINAL.json'),authority=authorityref,resource_grant=grantref);save(D/'ROOT-FINAL-REQUEST-BINDING-1.json',binding)
 copyargv=['/home/holden/anaconda3/bin/python3','-I','-B','-c',"from pathlib import Path;import hashlib,sys;raw=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[3];f=Path(sys.argv[2]).open('xb');f.write(raw);f.flush();__import__('os').fsync(f.fileno());f.close()",str(D/'ROOT-FINAL-REQUEST-BINDING-1.json'),str(L/'ROOT-FINAL-REQUEST-BINDING-1.json'),ref(D/'ROOT-FINAL-REQUEST-BINDING-1.json')['sha256']]
 save(D/'PUBLISH-ROOTBINDING-ARGV.json',copyargv)
 result=dict(status='ACTUAL_FINAL_REQUEST_AND_GENUINE_ROOT_AUTHORITY_BOUND_ONE_INVOCATION',request=ref(D/'pinned-launcher-request.FINAL.json'),binding=ref(D/'ROOT-FINAL-REQUEST-BINDING-1.json'),publish_rootbinding_argv=copyargv,capture_argv=['/usr/bin/taskset','-c','7','/home/holden/anaconda3/bin/python3','-I','-B',str(B/'capture_pinned_launcher_build.py')],capture_source=ref(B/'capture_pinned_launcher_build.py'),owner_argv=binding['owner_argv'],before_capture='Root independently confirms fresh granted emptyprivate namespaces/oneheavy exclusion/resource/census; ordinary UID1000 capture runs once, without sudo. No build executed by finalizer.',runtime_owner_nonce=None,actual_container=None,actual_lease=None,actual_build_receipt=None,native_acceptance=False)
 save(D/'FINAL-EXACT-OWNER-REQUEST-AND-CAPTURE.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
