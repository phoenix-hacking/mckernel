# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import os,json,hashlib,runpy,sys
D=Path(__file__).resolve().parent
sys.path.insert(0,'/home/holden/mckernel/scripts')
owner=D.parent/'prepared-sdk/derived-runtime/native_running_external_modules_owner.py'
assert hashlib.sha256(owner.read_bytes()).hexdigest()=='a5b919adfed8ee5e7e3f154e0385ae3063e86ea1314bfc60d50115f4bf0b0ef3'
g=runpy.run_path(str(owner),run_name='reviewed_sdk6_authenticate_only');canonical=g['canonical'];digest=lambda r:hashlib.sha256(r).hexdigest()
def exclusive(p,raw):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
raw=(D/'RELEASE-PAYLOAD.CANONICAL.PENDING-EXECUTION-REVIEW.json').read_bytes();assert digest(raw)=='60feace7b08343c42881bc3e8981271c6c4cb53a7218aae4ca8ab3151537864b'
v=json.loads(raw);assert canonical(v)==raw and 'execution_review' not in v
reviewpath=D/'EXECUTION-REVIEW.ROOT-RECORD.json';reviewraw=reviewpath.read_bytes();review=json.loads(reviewraw);assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer']!=v['author'] and review['reviewed_release_payload_sha256']==digest(raw)
reviewref=dict(path=str(reviewpath),sha256=digest(reviewraw));v['execution_review']=reviewref
releasepath=D/'release.json';releaseraw=canonical(v);exclusive(releasepath,releaseraw)
request=v['request'];g['authenticate'](Path(request['path']),request['sha256'],releasepath,digest(releaseraw))
operation=json.loads((D/'OPERATION.EXACT-REQUEST.NOT-RELEASED.json').read_bytes());assert operation['argv'][-1] is None;operation['argv'][-1]=digest(releaseraw);operation['execution_review']=reviewref;operation['status']='EXACT_INDEPENDENTLY_RELEASED_SDK6_OWNER_OPERATION';opraw=canonical(operation);exclusive(D/'operation.json',opraw)
a=json.loads((D/'CAPTURE-ARGV.NOT-RELEASED.json').read_bytes());assert a[-1] is None;a[-1]=digest(opraw);exclusive(D/'CAPTURE-ARGV.FINAL.NOT-EXECUTED.json',canonical(a))
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_FINAL_RELEASE_AUTHENTICATE_AND_CAPTURE_BINDING',payload_sha256=digest(raw),release_sha256=digest(releaseraw),operation_sha256=digest(opraw),actual_authenticate='PASS',native_invoked=False,build_invoked=False)
exclusive(D/'ACTUAL-FINAL-AUTHENTICATE.json',canonical(result));print(json.dumps(result))
