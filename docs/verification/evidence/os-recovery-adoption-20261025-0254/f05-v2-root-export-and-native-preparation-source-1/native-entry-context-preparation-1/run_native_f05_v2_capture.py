"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,subprocess,os,time,resource,datetime,decimal,importlib.util
A=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
G=json.loads((A/'ROOT-ACTUAL-ONE-NATIVE-F05-V2-GRANT.json').read_bytes())
assert G['decision']=='GRANTED_ONE_EXACT_NATIVE_F05_V2' and G['maximum_invocations']==1
for ref in [G['execution_review'],G['fresh_resource_physical'],G['pending_execution_packet']]:
 raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
review=json.loads(Path(G['execution_review']['path']).read_bytes());packet_raw=Path(G['pending_execution_packet']['path']).read_bytes()
assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer']!='/root' and review['payload_sha256']==hashlib.sha256(packet_raw).hexdigest()
P=json.loads(packet_raw);assert G['exact_argv']==P['exact_argv'] and G['nonce']==P['nonce']
policy=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py')
assert hashlib.sha256(policy.read_bytes()).hexdigest()=='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
spec=importlib.util.spec_from_file_location('f05v2_literal_actual_new12h_guard',policy);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.__file__==str(policy) and m.__spec__.origin==str(policy)
clocks=m.guard();cutoffs=m.current_cutoffs()
R=json.loads(Path(G['fresh_resource_physical']['path']).read_bytes());assert all(0<=n-o<120 for n,o in zip(clocks,R['observed_clocks']))
assert R['fixed_cutoffs']==list(cutoffs) and P['fixed_cutoffs']==R['fixed_cutoffs']
assert all(n<e for n,e in zip(clocks,cutoffs))
assert P['decision']=='PENDING_ONE_EXACT_NATIVE_F05_V2_RELEASE' and P['expected_case']=='M14-05-05-owned-processvm-v2-204B'
assert P['expected_new_image_sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57'
assert P['owner_sha256']=='af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10' and P['evaluator_sha256']=='529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da'
C=A/'CAPTURE';assert C.is_dir() and not list(C.iterdir())
stat=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split();start=time.time()
(C/'STARTED.json').write_text(json.dumps(dict(argv=G['exact_argv'],caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,grant=G),indent=2)+'\n')
before=resource.getrusage(resource.RUSAGE_CHILDREN)
with (C/'stdout').open('xb') as out,(C/'stderr').open('xb') as err:
 child=subprocess.Popen(G['exact_argv'],stdout=out,stderr=err);rc=child.wait()
after=resource.getrusage(resource.RUSAGE_CHILDREN)
(C/'JOINED.json').write_text(json.dumps(dict(joined=True,returncode=rc,caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,finished_at=time.time(),cpu_seconds=(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime),peak_rss_kib=after.ru_maxrss),indent=2)+'\n')
print('Actual F05v2 native caller joined',rc,flush=True)
