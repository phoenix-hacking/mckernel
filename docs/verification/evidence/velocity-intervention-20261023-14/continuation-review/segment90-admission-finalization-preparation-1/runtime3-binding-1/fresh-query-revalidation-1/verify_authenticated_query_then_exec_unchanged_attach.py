from pathlib import Path
import json,hashlib,os,sys,time
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/continuation-review/segment90-admission-finalization-preparation-1/runtime3-binding-1/fresh-query-revalidation-1')
assert os.getuid()==os.geteuid()==1000 and sys.version_info[:3]==(3,9,12)
def raw(p,cap):
 b=p.read_bytes();assert len(b)<=cap;return b
inv=json.loads(raw(D/'ROOT-QUERY.INVOCATION.stdout',1048576));r=json.loads(raw(D/'AUTHENTICATED-CLOSED-CAPTURE.json',1048576));assert inv['closed_capture']==r
assert inv['profile_sha256']=='513b8f422526780f539748a64623ea814463f4d5d54e55476926f28ebe536e33' and inv['status']=='PASS_ROOT_OWNED_FRESH_LONG_READONLY_CAPTURE'
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
assert r['captures']['stderr']['size']==0 and r['captures']['stderr']['sha256']==hashlib.sha256(b'').hexdigest()
b=raw(D/'AUTHENTICATED-FRESH-QUERY.stdout',33554432);h=hashlib.sha256(b).hexdigest();assert r['captures']['stdout']['path']==str(D/'actual-fresh-root-admission-1/stdout') and len(b)==r['captures']['stdout']['size'] and h==r['captures']['stdout']['sha256']
q=json.loads(b);assert q['status']=='PASS_FRESH_READ_ONLY_P12_LONG_ADMISSION' and 0<=time.time()-q['at_unix']<=120
path=D/'ATTACH-SAME-REVIEWED-PAYLOAD.FRESH-QUERY-SHA-PENDING.json';a=json.loads(raw(path,131072))['argv'];assert a[9] is None;a[9]=h
fd=os.open(D/'ACTUAL-AUTHENTICATED-FRESH-QUERY-AND-ATTACH-ARGV.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
with os.fdopen(fd,'w') as f:json.dump({'scope':'Functional OS/apps and Rust/assembly migration only; no security testing.','query_sha256':h,'closed_capture':r,'argv':a,'payload_sha256':'c981b6113387b4eadd44ac28ec7c1a879ab54d9550a1e118f9004c6ee4e81088','new_payload_or_expiry':False},f);f.write('\n');f.flush();os.fsync(f.fileno())
os.execv(a[0],a)
