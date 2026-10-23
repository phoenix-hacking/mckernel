"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,stat,time
B=Path(__file__).resolve().parent
RECEIPT_SHA='6da26bb30beaf2b45f7a8b1ff2ae1f96d3feb97da57bf6df349e1192b70e5209'
CONTRACT=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_disk_build_wrapper.py')
CONTRACT_SHA='c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1'
REQUEST=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/default-image-successor-1/image-request.FINAL.json')
TOKEN=Path('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
raw=(B/'ACTUAL-PREFLIGHT-PHYSICAL-ONLY-RECEIPT.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==RECEIPT_SHA;r=json.loads(raw)
assert os.getuid()==os.geteuid()==1000
cap=Path(r['actual_closed_capture']['path']);rawcap=cap.read_bytes();assert hashlib.sha256(rawcap).hexdigest()==r['actual_closed_capture']['sha256'];c=json.loads(rawcap)
assert c['returncode']==1 and c['direct_child_joined'] and c['process_group_absent'] and c['streams_closed']
assert not Path('/proc/'+str(r['token_record']['pid'])).exists()
assert hashlib.sha256(TOKEN.read_bytes()).hexdigest()==r['token_sha256']
s=TOKEN.lstat();assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and (s.st_dev,s.st_ino)==(1828,116631)
rawq=REQUEST.read_bytes();assert hashlib.sha256(rawq).hexdigest()=='377e6be0f6225246d60fea55b38d300922e47d210497e1ac7b62d110e9973349';q=json.loads(rawq)
for name in ('attempt_root','common_exclusion_path','lease_path','output_root','evidence_root'):assert not os.path.lexists(q[name])
for name in ('owner_evidence_root','work_root'):
 p=Path(q[name]);s=p.lstat();assert stat.S_ISDIR(s.st_mode) and not p.is_symlink() and s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700 and not any(p.iterdir())
m=Path('/run/lock/mckernel-development.lock').stat();assert (m.st_dev,m.st_ino)==(27,4)
rawc=CONTRACT.read_bytes();assert hashlib.sha256(rawc).hexdigest()==CONTRACT_SHA
fn=next(n for n in ast.parse(rawc).body if isinstance(n,ast.FunctionDef) and n.name=='_release_exclusion')
ns={'os':os,'json':json};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(CONTRACT),'exec'),ns)
assert ns['_release_exclusion'](TOKEN,r['token_record'],r) is True
assert not os.path.lexists(TOKEN)
m=Path('/run/lock/mckernel-development.lock').stat();assert (m.st_dev,m.st_ino)==(27,4)
result=dict(scope=__doc__,status='PASS_NORMAL_API_PREFLIGHT_TOKEN_RECONCILIATION',physical_receipt_sha256=RECEIPT_SHA,contract_sha256=CONTRACT_SHA,token_absent=True,permanent_mutex=[27,4],build_status='FAIL_PRESERVED_STOPPED',build_acceptance=False,at_ns=time.time_ns())
with (B/'ACTUAL-RECONCILIATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
