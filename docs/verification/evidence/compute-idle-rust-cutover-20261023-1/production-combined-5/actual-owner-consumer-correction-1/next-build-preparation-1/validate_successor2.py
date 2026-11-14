"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exactly one complete pure _validate_request; never ImageOwner.run/acquire/Docker.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,sys,time
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sys.version_info[:3]==(3,9,12),'actual accepted Anaconda3.9.12 interpreter required'
assert os.geteuid()==os.getuid()==1000
begin=time.monotonic();p=D/'image-request.PREPARED.json';ownerpath=D/'native_rust_exact_mckernel_image_container_owner.py'
assert sha(p)=='28caca822e9b6f6fa3d0ff49d0e874eb8da7b87a282afc5568f033c15179a7f3'
assert sha(ownerpath)=='f7e1aec84e6974538a54b9a1c6acd38f5ccf49df59b8a5677f5866119b87f258'
request=json.loads(p.read_bytes());roots=[Path(request[k]) for k in ['work_root','owner_evidence_root']]
before={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert all(not x for x in before.values())
absent=[Path(request[k]) for k in ['output_root','evidence_root','attempt_root','lease_path','common_exclusion_path']];assert all(not os.path.lexists(q) for q in absent)
spec=importlib.util.spec_from_file_location('accepted_schema_owner_fresh_namespace',ownerpath);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
bound=owner._validate_request(request)
after={str(q):sorted(x.name for x in q.iterdir()) for q in roots};assert before==after and all(not os.path.lexists(q) for q in absent)
assert sha(p)=='28caca822e9b6f6fa3d0ff49d0e874eb8da7b87a282afc5568f033c15179a7f3' and sha(ownerpath)=='f7e1aec84e6974538a54b9a1c6acd38f5ccf49df59b8a5677f5866119b87f258'
print(json.dumps(dict(scope=__doc__,status='PASS_ACTUAL_COMPLETE_NEW_NAMESPACE_VALIDATE_REQUEST_ONLY',seconds=time.monotonic()-begin,interpreter=sys.version,owner_sha256=sha(ownerpath),request_sha256=sha(p),source=str(bound['source']),source_manifest=str(bound['manifest']),toolchain_schema=bound['toolchain_schema'],measurement=bound['measurement'],gitlink_root=str(bound['gitlink_root']),own_namespace_before=before,own_namespace_after=after,absent_paths_unchanged=[str(q) for q in absent],ImageOwner_run=False,heavy_acquire=False,Docker_root_compiler_guest=False),sort_keys=True))
