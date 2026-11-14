"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,subprocess,os,time,resource,datetime,decimal,importlib.util,math
AUTHORIZED_FIXED_LIMITS = (1793165769.0, 947874.5689514667, 963213.6960030915)

def cutoff_triplet(values, label):
 if type(values) not in (list, tuple) or len(values) != 3:
  raise ValueError(label + ': three clock values required')
 if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in values):
  raise ValueError(label + ': finite positive numeric clocks required')
 return tuple(values)

def entry_clamps(clocks, observed_clocks, resource_cutoffs, packet_cutoffs, guardian_cutoffs):
 now = cutoff_triplet(clocks, 'admission clocks')
 observed = cutoff_triplet(observed_clocks, 'resource observation clocks')
 resource = cutoff_triplet(resource_cutoffs, 'resource cutoffs')
 packet = cutoff_triplet(packet_cutoffs, 'packet cutoffs')
 guardian = cutoff_triplet(guardian_cutoffs, 'live guardian cutoffs')
 if packet != resource:
  raise ValueError('packet and resource cutoffs differ')
 if not all(live <= recorded <= authorized for live, recorded, authorized in zip(guardian, resource, AUTHORIZED_FIXED_LIMITS)):
  raise ValueError('guardian/resource cutoffs widen an inherited ceiling')
 ages = [current - prior for current, prior in zip(now, observed)]
 if not all(0 <= age < 120 for age in ages):
  raise ValueError('resource observation expired or from the future')
 effective = [min(live, recorded, released, authorized) for live, recorded, released, authorized in zip(guardian, resource, packet, AUTHORIZED_FIXED_LIMITS)]
 if not all(current < deadline for current, deadline in zip(now, effective)):
  raise ValueError('effective inherited deadline reached')
 return dict(authorizedFixedLimits=list(AUTHORIZED_FIXED_LIMITS), resourceCutoffs=list(resource),
             packetCutoffs=list(packet), liveGuardianCutoffs=list(guardian),
             effectiveCutoffs=effective, resourceAgesSeconds=ages)

A=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
G=json.loads((A/'ROOT-ACTUAL-ONE-NATIVE-M15-STARTUP-GRANT.json').read_bytes())
assert G['decision']=='GRANTED_ONE_EXACT_NATIVE_M15_STARTUP' and G['maximum_invocations']==1
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
R=json.loads(Path(G['fresh_resource_physical']['path']).read_bytes())
clampsUsed=entry_clamps(clocks,R['observed_clocks'],R['fixed_cutoffs'],P['fixed_cutoffs'],cutoffs)
assert P['decision']=='PENDING_ONE_EXACT_NATIVE_M15_STARTUP_RELEASE' and P['expected_case']=='P-M06-01-process-exec-wait-235B'
assert P['expected_new_image_sha256']=='de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024'
assert P['owner_sha256']=='af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10' and P['evaluator_sha256']=='529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da'
C=A/'CAPTURE';assert C.is_dir() and not list(C.iterdir())
stat=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split();start=time.time()
(C/'STARTED.json').write_text(json.dumps(dict(argv=G['exact_argv'],caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,grant=G,clampsUsed=clampsUsed),indent=2)+'\n')
before=resource.getrusage(resource.RUSAGE_CHILDREN)
with (C/'stdout').open('xb') as out,(C/'stderr').open('xb') as err:
 child=subprocess.Popen(G['exact_argv'],stdout=out,stderr=err);rc=child.wait()
after=resource.getrusage(resource.RUSAGE_CHILDREN)
(C/'JOINED.json').write_text(json.dumps(dict(joined=True,returncode=rc,caller_pid=os.getpid(),caller_starttime=stat[19],started_at=start,finished_at=time.time(),cpu_seconds=(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime),peak_rss_kib=after.ru_maxrss),indent=2)+'\n')
print('Actual original startup Rustexecutor native caller joined',rc,flush=True)
