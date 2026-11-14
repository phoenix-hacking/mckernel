"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,subprocess,os,time,resource,datetime,decimal,importlib.util
A=Path(__file__).resolve().parent
G=json.loads((A/'ROOT-ACTUAL-ONE-NATIVE-MEMORY-GRANT.json').read_bytes())
assert G['decision']=='GRANTED_ONE_EXACT_NATIVE_MEMORY' and G['maximum_invocations']==1
for ref in [G['execution_review'],G['fresh_resource_physical'],G['pending_execution_packet']]:
 raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
review=json.loads(Path(G['execution_review']['path']).read_bytes());packet_raw=Path(G['pending_execution_packet']['path']).read_bytes()
assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer']!='/root' and review['payload_sha256']==hashlib.sha256(packet_raw).hexdigest()
P=json.loads(packet_raw);assert G['exact_argv']==P['exact_argv'] and G['nonce']==P['nonce']
clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
R=json.loads(Path(G['fresh_resource_physical']['path']).read_bytes());assert all(0<=n-o<120 for n,o in zip(clocks,R['observed_clocks']))
assert all(n<e for n,e in zip(clocks,[1793100290,882395.5689528405,897734.6960034363]))
s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert s['phase']=='running' and s['thread_id']=='01a170fb-57c3-7ab3-862d-8005bef92a63' and s.get('stop_reason') is None and s.get('stop_now',False) is False
assert s['credit_budget']['id']=='7f4af94a83b14cc08f97401f5891d965' and decimal.Decimal(s['credit_budget']['budget'])==decimal.Decimal('57774.852125') and decimal.Decimal(s['credit_budget']['remaining'])>0 and s['credit_budget_error'] is None
assert 0<=clocks[0]-datetime.datetime.fromisoformat(s['heartbeat_at']).timestamp()<180
policy=Path('/home/holden/mckernel/scripts/os_goal_credits.py');assert hashlib.sha256(policy.read_bytes()).hexdigest()=='adf5187240ed8199746eef3b59b79d4d38c4ae8ac5821c8d8324833926b21ec3'
spec=importlib.util.spec_from_file_location('readonly_credit_policy',policy);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.available_balance(s['last_rate_limits'])
C=A/'CAPTURE';assert C.is_dir() and not list(C.iterdir())
stat=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split();start=time.time()
(C/'STARTED.json').write_text(json.dumps(dict(argv=G['exact_argv'],caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,grant=G),indent=2)+'\n')
before=resource.getrusage(resource.RUSAGE_CHILDREN)
with (C/'stdout').open('xb') as out,(C/'stderr').open('xb') as err:
 child=subprocess.Popen(G['exact_argv'],stdout=out,stderr=err);rc=child.wait()
after=resource.getrusage(resource.RUSAGE_CHILDREN)
(C/'JOINED.json').write_text(json.dumps(dict(joined=True,returncode=rc,caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,finished_at=time.time(),cpu_seconds=(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime),peak_rss_kib=after.ru_maxrss),indent=2)+'\n')
print('Actual memory native caller joined',rc,flush=True)
