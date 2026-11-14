"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact existing owner live_admission/measure read-only call-through; no PROC census,
Docker query, root lock, historical observer or build is started here.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,sys,time
sys.path.insert(0,'/home/holden/mckernel/scripts')
H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-7/prepared-sdk')
O=H/'derived-runtime/native_running_external_modules_owner.py'
assert hashlib.sha256(O.read_bytes()).hexdigest()=='b48a27d974d68a369ab9c566dd1d35406fe82beaf48f07097ee2359c72b81555'
raw=(H/'request.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='3878c1fbcbeb75f12e03050cbb9ec343bdbdd919f64c181b1ee7ebb2d754ca73'
r=json.loads(raw);assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
assert resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1),'owner inherited CPU must remain unlimited'
spec=importlib.util.spec_from_file_location('sdk7_owner_final_facts',O);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mount=m.live_admission(r);capacity=m.measure(r)
absent=[r['owner_evidence_root'],str(m.ROOT/('native-running-modules-admission-'+r['nonce']))]
assert all(not os.path.lexists(p) for p in absent),'fresh exact SDK7 owner/admission namespaces required'
mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
assert mem>=19*2**30,'aggregate19GiB available required'
print(json.dumps({'scope':__doc__.splitlines()[0],'status':'PASS_FRESH_SDK7_OWNER_CAPACITY_AND_NAMESPACES','at_unix':time.time(),'request_sha256':hashlib.sha256(raw).hexdigest(),'owner_sha256':hashlib.sha256(O.read_bytes()).hexdigest(),'mount':mount,'capacity':capacity,'request_directory_identities':{k:r[k] for k in ('candidate_identity','input_identity','backing_identity','basis_identity','output_parent_identity')},'fresh_namespaces_absent':absent,'CPU_limits':list(resource.getrlimit(resource.RLIMIT_CPU)),'NPROC_limits':list(resource.getrlimit(resource.RLIMIT_NPROC)),'affinity':sorted(os.sched_getaffinity(0)),'MemAvailable_bytes':mem,'aggregate_available_required_bytes':19*2**30,'mutation':False,'Docker_operations':0,'PROC_census':0,'build':False},sort_keys=True))
