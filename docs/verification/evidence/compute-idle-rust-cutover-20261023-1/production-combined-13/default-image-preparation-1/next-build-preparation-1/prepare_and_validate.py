"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact exclusive namespace/request preparation and one complete pure validation; no run/acquire.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,sys,time
D=Path(__file__).resolve().parent;N=D.parent
B=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-12/default-image-preparation-1/next-build-preparation-1')
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def save(n,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 with (D/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def identity(p):
 s=os.lstat(p);return dict(path=str(p.resolve(strict=True)),dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),file_type=stat.S_IFMT(s.st_mode))
assert sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
begin=time.monotonic();host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
capacity=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+67108864,scratch_required=13631488000,MemAvailable=mem,root_planning_reservation=19*1073741824)
save('ACTUAL-PREPARATION-CAPACITY.json',capacity);assert capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'] and mem>=19*1073741824
raw=(B/'image-request.PREPARED.json').read_bytes();assert sha(raw)=='43630603e0515f525cc609222b743cc1947e94ce9f84ec75ea432160e7052ff2';request=json.loads(raw);before=json.loads(raw)
material=json.loads((N/'source-materialization-attempt-1/MATERIALIZATION-RESULT.json').read_text());assert material['source_manifest_canonical_sha256']=='12b430700c83fc62cd9bc7bc62d29f40d69511953907590696827a64337d92a2'
oldattempt=B/'pinned-full-image-attempt-1';newattempt=D/'pinned-full-image-attempt-1';assert not os.path.lexists(newattempt)
created=[]
for q in (newattempt,newattempt/'owner-work',newattempt/'owner-evidence'):
 os.mkdir(q,0o700);row=identity(q);assert row['uid']==row['gid']==1000 and row['mode']==448 and not list(q.iterdir());created.append(row)
for k in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path'):
 assert request[k].startswith(str(oldattempt)+'/');request[k]=str(newattempt)+request[k][len(str(oldattempt)):]
newsource=N/'source-materialization-attempt-1/materialized-source';oldsource=request['source_root']
request.update(source_root=str(newsource),source_manifest=str(N/'source-materialization-attempt-1/source-inputs.json'),source_manifest_sha256=material['source_manifest_canonical_sha256'],source_derivative_sha256=material['source_derivative_sha256'],materialization_sha256=material['materialization_sha256'],gitlink_manifest=str(D/'gitlink-inputs.json'),gitlink_manifest_sha256=ref(D/'gitlink-inputs.json')['sha256'],driver_path=str(N/'native_rust_exact_mckernel_image_offline.py'),driver_sha256='502434a8c61126b250c3c61d770ee089a41b1903e143e393212dcf76e4247012',provenance_path=str(N/'native_rust_exact_build_offline.py'),provenance_sha256='0a6f8d7c3710df51ff0d5d1311b2bd1aefb68f6b467563f708d0cb368653307f')
rootmap={oldsource:str(newsource),str(oldattempt/'owner-work'):str(newattempt/'owner-work'),str(oldattempt/'owner-evidence'):str(newattempt/'owner-evidence')};assert all(k in request['memory_allocation_roots'] for k in rootmap);request['memory_allocation_roots']=[rootmap.get(k,k) for k in request['memory_allocation_roots']]
request['source_identity']=identity(newsource);request['disk_identity']=identity(newsource);request['backup_identity']=identity(Path(request['backup_root']));request['disk_admission']['host_device']=Path(request['disk_admission']['host_root']).stat().st_dev;request['disk_admission']['scratch_device']=Path(request['disk_admission']['scratch_root']).stat().st_dev
encoded=(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(encoded)<33554432
with (D/'image-request.PREPARED.json').open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
ownerpath=D/'native_rust_exact_mckernel_image_container_owner.py';assert ref(ownerpath)['sha256']=='da78fc6bb5364f0980de569215cd9d01006f6122667713d4535a2b03ea364578'
save('ACTUAL-NAMESPACE-AND-REQUEST.json',dict(scope=__doc__,status='PASS_CANDIDATE13_NAMESPACE_AND_REQUEST_PREPARATION_ONLY',owner=ref(ownerpath),request=ref(D/'image-request.PREPARED.json'),created_namespace_identities=created,changed_request_fields=[k for k in request if request[k]!=before[k]],source_manifest_sha256=request['source_manifest_sha256'],source_derivative_sha256=request['source_derivative_sha256'],materialization_sha256=request['materialization_sha256'],same_owner_functions_classes_AST=True,source_identity=request['source_identity'],execution_authorized=False,heavy_acquire=False))
roots=[Path(request[k]) for k in ('work_root','owner_evidence_root')];absent=[Path(request[k]) for k in ('output_root','evidence_root','attempt_root','lease_path','common_exclusion_path')];before_ns={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert all(not v for v in before_ns.values()) and all(not os.path.lexists(q) for q in absent)
spec=importlib.util.spec_from_file_location('accepted_candidate13_owner',ownerpath);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
validation_start=time.monotonic();bound=owner._validate_request(request)
after_ns={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert before_ns==after_ns and all(not os.path.lexists(q) for q in absent) and (D/'image-request.PREPARED.json').read_bytes()==encoded
result=dict(scope=__doc__,status='PASS_ACTUAL_COMPLETE_CANDIDATE13_VALIDATE_REQUEST_ONLY',validation_seconds=time.monotonic()-validation_start,total_seconds=time.monotonic()-begin,owner=ref(ownerpath),request=ref(D/'image-request.PREPARED.json'),interpreter=sys.version,source=str(bound['source']),measurement=bound['measurement'],own_namespace_before=before_ns,own_namespace_after=after_ns,absent_paths=[str(q) for q in absent],ImageOwner_run=False,heavy_acquire=False,compiler_Docker_root_guest=False)
save('ACTUAL-PURE-CONSUMER-RESULT.json',result);print(json.dumps(result,sort_keys=True))
