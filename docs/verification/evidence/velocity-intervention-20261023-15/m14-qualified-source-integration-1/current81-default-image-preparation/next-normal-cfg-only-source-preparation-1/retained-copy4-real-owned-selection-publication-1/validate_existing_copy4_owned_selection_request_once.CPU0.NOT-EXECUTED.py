"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing normal owner complete pure request consumer on expert-corrected immutable metadata.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,sys,time
D=Path(__file__).resolve().parent
REQUEST=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/image-request.REAL-OWNED-SELECTION.COPY4-BOUND.json');REQUEST_SHA='799041202981030714f94abba114ce7237dab171a3dd8db79eabc5a01314e854'
OWNER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/native_rust_exact_mckernel_image_container_owner.REAL-OWNED-SELECTION.COPY4-BOUND.py');OWNER_SHA='e3e87cfc645409276976a551307365c57c1d54e2637a5355a0577cf73596367d'
assert sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
begin=time.monotonic()
def cpu():
 a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN);return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime
raw=REQUEST.read_bytes();assert hashlib.sha256(raw).hexdigest()==REQUEST_SHA;request=json.loads(raw)
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()==OWNER_SHA
roots=[Path(request[k]) for k in ('work_root','owner_evidence_root')];absent=[Path(request[k]) for k in ('evidence_root','lease_path','common_exclusion_path')]
before={str(p):sorted(x.name for x in p.iterdir()) for p in roots};assert before[str(roots[0])]==['output'] and before[str(roots[1])]==[] and all(not os.path.lexists(p) for p in absent)
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-back.st_blocks*512)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
capacity=dict(HOST_available=host.f_bavail*host.f_frsize,HOST_required=17179869184+gap+16106090496+377487360+679477248+67108864,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=13631488000,MemAvailable=mem,root_planning_reservation=25501368320,workload_planning_memory=21206401024,HOST_control_reserve_memory=4294967296,planning_only_no_durable_lease=True,full_sparse_gap=gap)
assert capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'] and mem>=capacity['root_planning_reservation']
spec=importlib.util.spec_from_file_location('accepted_existing_normal_owner',OWNER);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
bound=owner._validate_request(request)
after={str(p):sorted(x.name for x in p.iterdir()) for p in roots};assert before==after and all(not os.path.lexists(p) for p in absent) and REQUEST.read_bytes()==raw
assert cpu()<=60 and time.monotonic()-begin<=90
result=dict(scope=__doc__,status='PASS_ACTUAL_COMPLETE_PURE_COPY4_REAL_OWNED_SELECTION_REQUEST',request=dict(path=str(REQUEST),sha256=REQUEST_SHA),owner=dict(path=str(OWNER),sha256=OWNER_SHA),source=str(bound['source']),measurement=bound['measurement'],capacity=capacity,own_namespace_before=before,own_namespace_after=after,CPU_seconds=cpu(),wall_seconds=time.monotonic()-begin,ImageOwner_run=False,heavy_acquire=False,compiler_Docker_root_guest=False)
assert cpu()<=60 and time.monotonic()-begin<=90
with (D/'ACTUAL-COPY4-REAL-OWNED-SELECTION-PURE-CONSUMER-RESULT.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(result,sort_keys=True))
