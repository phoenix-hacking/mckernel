"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Authorized exclusive ordinary namespace/request preparation; never acquires heavy ownership.
"""
from pathlib import Path
import ast,difflib,hashlib,json,os,stat,time
E=Path(__file__).resolve().parent
D=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1')
B=D.parent
OLD=D.parents[1]/'default-image-successor-1'
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def identity(p):
 s=os.lstat(p);return dict(path=str(p.resolve(strict=True)),dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),file_type=stat.S_IFMT(s.st_mode))
def write(p,b):
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def save(name,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 for root in [D,E]:write(root/name,b)
def main():
 start=time.monotonic();assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 oldrequest=OLD/'image-request.FINAL.json';raw=oldrequest.read_bytes();assert sha(raw)=='377e6be0f6225246d60fea55b38d300922e47d210497e1ac7b62d110e9973349';request=json.loads(raw);before=json.loads(raw)
 name='native_rust_exact_mckernel_image_container_owner.py';accepted=B/name;source=accepted.read_text();assert sha(source.encode())=='dbbf7d952918005a6cfa78feaf1cb711eae32492014aedabece9eb0bcadcb37d'
 oldattempt=OLD/'pinned-full-image-attempt-1';newattempt=D/'pinned-full-image-attempt-2';oldcommon=str(oldattempt/'common-exclusion.json');newcommon=str(newattempt/'common-exclusion.json');assert source.count(oldcommon)==1
 successor=source.replace(oldcommon,newcommon);assert successor.count('LIMITS = {')==1;successor=successor.replace('LIMITS = {', 'RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('+repr(oldcommon)+',))\n\nLIMITS = {',1)
 functions=lambda s:{n.name:ast.dump(n) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};assert functions(source)==functions(successor)
 for root in [D,E]:write(root/name,successor.encode())
 write(E/'namespace-owner.diff',''.join(difflib.unified_diff(source.splitlines(True),successor.splitlines(True),fromfile=str(accepted),tofile=str(D/name))).encode())
 assert not os.path.lexists(newattempt)
 assert os.statvfs(D).f_bavail*os.statvfs(D).f_frsize>=16*2**30+(64<<20) and os.statvfs('/home/holden/mckernel-work/scratch').f_bavail*os.statvfs('/home/holden/mckernel-work/scratch').f_frsize>=12*2**30
 created=[]
 for path in [newattempt,newattempt/'owner-work',newattempt/'owner-evidence']:
  os.mkdir(path,0o700);row=identity(path);assert row['uid']==row['gid']==1000 and row['mode']==448 and row['file_type']==16384 and list(path.iterdir())==[];created.append(row)
 for key in ['work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path']:
  assert request[key].startswith(str(oldattempt)+'/');request[key]=str(newattempt)+request[key][len(str(oldattempt)):]
 rootmap={str(oldattempt/'owner-work'):str(newattempt/'owner-work'),str(oldattempt/'owner-evidence'):str(newattempt/'owner-evidence')};assert all(p in request['memory_allocation_roots'] for p in rootmap);request['memory_allocation_roots']=[rootmap.get(p,p) for p in request['memory_allocation_roots']]
 request['source_identity']=identity(Path(request['source_root']));request['disk_identity']=identity(Path(request['source_root']));request['backup_identity']=identity(Path(request.get('backup_root',request.get('source_backup_root'))));request['disk_admission']['host_device']=Path(request['disk_admission']['host_root']).stat().st_dev;request['disk_admission']['scratch_device']=Path(request['disk_admission']['scratch_root']).stat().st_dev
 allowed=set(['work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path','memory_allocation_roots','source_identity','disk_identity','backup_identity','disk_admission']);changed=[k for k in request if request[k]!=before[k]];assert set(changed)<=allowed and len(changed)==8
 encoded=(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(encoded)<=32<<20;dest=D/'image-request.PREPARED.json';write(dest,encoded);assert dest.read_bytes()==encoded
 receipt=ref(B/'PURE-CONSUMER-RECEIPT.json');assert receipt['sha256']=='3b3d01c5ad566bbfe0046edd979f06306f291895d7ac00ce23b00ef998208fbe'
 save('ACTUAL-NAMESPACE-AND-REQUEST.json',dict(scope=__doc__,status='PASS_EXCLUSIVE_ORDINARY_SUCCESSOR2_NAMESPACE_AND_REQUEST_ONLY',accepted_owner=ref(accepted),successor_owner=ref(D/name),same_function_and_class_AST=True,owner_changes=['COMMON_EXCLUSION freshattempt2','retire consumed originalattempt1 common path'],original_request=ref(oldrequest),new_request=ref(dest),changed_request_fields=changed,source_identity=request['source_identity'],materialization_sha256=request['materialization_sha256'],source_derivative_sha256=request['source_derivative_sha256'],source_manifest=dict(path=request['source_manifest'],sha256=request['source_manifest_sha256']),created_namespace_identities=created,still_absent=[request[k] for k in ['output_root','evidence_root','attempt_root','lease_path','common_exclusion_path']],accepted_pure_consumer=receipt,failed_fixture_history=json.loads((B/'PURE-CONSUMER-RECEIPT.json').read_text())['failure_family_history'],seconds=time.monotonic()-start,old_request_and_namespace_unchanged=True,heavy_acquire=False,execution_authorized=False))
 print(json.dumps(dict(status='PASS_NEW_REQUEST_AND_EXCLUSIVE_NAMESPACE',request=ref(dest),owner=ref(D/name))))
if __name__=='__main__':main()
