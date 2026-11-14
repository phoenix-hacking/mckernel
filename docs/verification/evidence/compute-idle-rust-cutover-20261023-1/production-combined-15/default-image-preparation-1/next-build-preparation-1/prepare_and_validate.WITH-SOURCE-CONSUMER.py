"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact exclusive namespace/request preparation and one complete pure validation; no run/acquire.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,sys,time
D=Path(__file__).resolve().parent;N=D.parent
B=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-14/default-image-preparation-1/next-build-preparation-1')
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def save(n,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 with (D/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def identity(p):
 s=os.lstat(p);return dict(path=str(p.resolve(strict=True)),dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),file_type=stat.S_IFMT(s.st_mode))
assert sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}
begin=time.monotonic();host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks)
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
capacity=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+67108864,scratch_required=13631488000,MemAvailable=mem,root_planning_reservation=19*1073741824)
save('ACTUAL-PREPARATION-CAPACITY.json',capacity);assert capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'] and mem>=19*1073741824
raw=(B/'image-request.PREPARED.json').read_bytes();assert sha(raw)=='d68b8cc32ecc2f76f3446ffe78001852f3de6420bd1c857bf616d4076d5b4b90';request=json.loads(raw);before=json.loads(raw)
material=json.loads((N/'source-materialization-attempt-1/MATERIALIZATION-RESULT.json').read_text());assert material['source_manifest_canonical_sha256']=='77fd79cde7d48ceb65aaf9de2ff8be78005274f22031fe12c58d8309173c58a4'
oldattempt=B/'pinned-full-image-attempt-1';newattempt=D/'pinned-full-image-attempt-1';assert not os.path.lexists(newattempt)
created=[]
for q in (newattempt,newattempt/'owner-work',newattempt/'owner-evidence'):
 os.mkdir(q,0o700);row=identity(q);assert row['uid']==row['gid']==1000 and row['mode']==448 and not list(q.iterdir());created.append(row)
for k in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path'):
 assert request[k].startswith(str(oldattempt)+'/');request[k]=str(newattempt)+request[k][len(str(oldattempt)):]
newsource=N/'source-materialization-attempt-1/materialized-source';oldsource=request['source_root']
request.update(source_root=str(newsource),source_manifest=str(N/'source-materialization-attempt-1/source-inputs.json'),source_manifest_sha256=material['source_manifest_canonical_sha256'],source_derivative_sha256=material['source_derivative_sha256'],materialization_sha256=material['materialization_sha256'],gitlink_manifest=str(D/'gitlink-inputs.json'),gitlink_manifest_sha256=ref(D/'gitlink-inputs.json')['sha256'],driver_path=str(N/'native_rust_exact_mckernel_image_offline.py'),driver_sha256='776b478b6f4f7a9e3ec502ac2a23c6a03fbd407c6b599760206b1bf8bfdb0ff7',provenance_path=str(N/'native_rust_exact_build_offline.py'),provenance_sha256='c5868d8a336795b5c3d76215bba8bcb3e56a804e00f1014d8b4eeaf6ddb76a69')
rootmap={oldsource:str(newsource),str(oldattempt/'owner-work'):str(newattempt/'owner-work'),str(oldattempt/'owner-evidence'):str(newattempt/'owner-evidence')};assert all(k in request['memory_allocation_roots'] for k in rootmap);request['memory_allocation_roots']=[rootmap.get(k,k) for k in request['memory_allocation_roots']]
request['source_identity']=identity(newsource);request['disk_identity']=identity(newsource);request['backup_identity']=identity(Path(request['backup_root']));request['disk_admission']['host_device']=Path(request['disk_admission']['host_root']).stat().st_dev;request['disk_admission']['scratch_device']=Path(request['disk_admission']['scratch_root']).stat().st_dev
encoded=(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(encoded)<33554432
with (D/'image-request.PREPARED.json').open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
ownerpath=D/'native_rust_exact_mckernel_image_container_owner.py';assert ref(ownerpath)['sha256']=='6d6372c8b6525872868d7f925a4bb2d25b3af210798b354b4eb087a4b5ed0fe8'
save('ACTUAL-NAMESPACE-AND-REQUEST.json',dict(scope=__doc__,status='PASS_CANDIDATE14_NAMESPACE_AND_REQUEST_PREPARATION_ONLY',owner=ref(ownerpath),request=ref(D/'image-request.PREPARED.json'),created_namespace_identities=created,changed_request_fields=[k for k in request if request[k]!=before[k]],source_manifest_sha256=request['source_manifest_sha256'],source_derivative_sha256=request['source_derivative_sha256'],materialization_sha256=request['materialization_sha256'],same_owner_functions_classes_AST=True,source_identity=request['source_identity'],execution_authorized=False,heavy_acquire=False))
roots=[Path(request[k]) for k in ('work_root','owner_evidence_root')];absent=[Path(request[k]) for k in ('output_root','evidence_root','attempt_root','lease_path','common_exclusion_path')];before_ns={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert all(not v for v in before_ns.values()) and all(not os.path.lexists(q) for q in absent)
spec=importlib.util.spec_from_file_location('accepted_candidate15_owner',ownerpath);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)

# Cheap actual retained-artifact consumers of the new bounded ELF witnesses.
import ast
artifact_authority = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-memory-callback-next/production-consumer-preparation-1/coherent-current78-refresh-corrected-1/ACTUAL-PRODUCTION-OBSERVER-STOP-RECEIPT.json', 'bytes': 24284, 'sha256': '90239bcb458a6b716b1bc8370c8b2b36aa56b3434fbd4e6e3b9a63b0dcd24986'}
assert ref(Path(artifact_authority['path']))['sha256']==artifact_authority['sha256']
artifacts=json.loads(Path(artifact_authority['path']).read_text())['artifacts_durable_hashed_once_before_observers']
def stat_same(row):
 s=os.stat(row['path']);assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==tuple(row[k] for k in ('device','inode','size','mtime_ns','ctime_ns'))
for name in ('memory.c.o','mckernel_rust.o'):stat_same(artifacts[name])
source_tree=ast.parse((N/'native_rust_exact_mckernel_image_offline.py').read_text())
selected=[node for node in source_tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_m14_l4_callback_object','_m14_Rust_callback_relocations')]
assert len(selected)==2
consumer_ns={'Path':Path,'_fail':lambda condition,message: None if condition else (_ for _ in ()).throw(AssertionError(message))}
exec(compile(ast.Module(body=selected,type_ignores=[]),'source-bound-successor-witnesses','exec'),consumer_ns)
callback_names=('mem_tlb_rdtsc_bridge', 'mem_tlb_current_cpu_bridge', 'mem_tlb_get_vector_bridge', 'mem_tlb_interrupt_cpu_bridge', 'mem_tlb_noirq_lock_bridge', 'mem_tlb_noirq_unlock_bridge', 'mem_tlb_atomic_set_bridge', 'mem_tlb_atomic_inc_bridge', 'mem_tlb_atomic_read_bridge', 'mem_tlb_flush_single_bridge', 'mem_tlb_flush_all_bridge', 'mem_tlb_pause_bridge', 'vm_range_insert_log_bridge', 'vm_range_insert_dump_bridge', 'x86_running_on_kvm_bridge', 'x86_cpuid6_bridge', 'x86_read_msr_bridge', 'x86_write_msr_bridge', 'syscall_alloc_bridge', 'syscall_mckfd_lock_bridge', 'syscall_mckfd_unlock_bridge')

callback_proof=consumer_ns['_m14_l4_callback_object'](Path(artifacts['memory.c.o']['path']))
relocation_counts=consumer_ns['_m14_Rust_callback_relocations'](Path(artifacts['mckernel_rust.o']['path']),callback_names)
for name in ('memory.c.o','mckernel_rust.o'):stat_same(artifacts[name])
save('ACTUAL-SOURCE-BOUND-OBSERVER-CONSUMER.json',dict(scope=__doc__,status='PASS_ACTUAL_RETAINED_GCC9_ELF_CALLBACK_WITNESSES_ONLY',artifact_authority=artifact_authority,artifacts_stat_unchanged_no_rehash=True,callback_proof=callback_proof,Rust_callback_relocation_counts=relocation_counts,compiler_invocations=0,GCC14_defaultlink_native=False))

validation_start=time.monotonic();bound=owner._validate_request(request)
after_ns={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert before_ns==after_ns and all(not os.path.lexists(q) for q in absent) and (D/'image-request.PREPARED.json').read_bytes()==encoded
result=dict(scope=__doc__,status='PASS_ACTUAL_COMPLETE_CANDIDATE14_VALIDATE_REQUEST_ONLY',validation_seconds=time.monotonic()-validation_start,total_seconds=time.monotonic()-begin,owner=ref(ownerpath),request=ref(D/'image-request.PREPARED.json'),interpreter=sys.version,source=str(bound['source']),measurement=bound['measurement'],own_namespace_before=before_ns,own_namespace_after=after_ns,absent_paths=[str(q) for q in absent],ImageOwner_run=False,heavy_acquire=False,compiler_Docker_root_guest=False)
save('ACTUAL-PURE-CONSUMER-RESULT.json',result);print(json.dumps(result,sort_keys=True))
