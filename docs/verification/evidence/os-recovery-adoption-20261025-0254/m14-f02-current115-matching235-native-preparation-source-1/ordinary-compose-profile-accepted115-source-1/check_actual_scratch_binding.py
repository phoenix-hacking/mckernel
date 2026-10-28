"""Functional OS only; no security testing. Root postcompose scratch/API binder only.
No guard, resource, subprocess, stage, native or grant operation.
"""
import argparse,hashlib,json,importlib.util
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent
OWNER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v2-root-export-and-native-preparation-source-1/bound-native-runtime-1/native_diagnostic_container_owner.py')
OWNER_SHA='af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10'
def main():
 p=argparse.ArgumentParser()
 for n in ['scratch-manifest','scratch-manifest-sha256','attempt-parent']:p.add_argument('--'+n,required=True)
 a=p.parse_args();raw=Path(a.scratch_manifest).read_bytes();assert hashlib.sha256(raw).hexdigest()==a.scratch_manifest_sha256
 actual=B/'root-actual-compose-1/manifest.HOST-STATIC.json';assert actual.read_bytes()==raw
 m=json.loads(raw);plan=json.loads((B/'MATCHING235-CURRENT115-PLAN.NOT-RELEASED.json').read_text());assert m['artifacts']['mckernel_image']==plan['new_image'] and m['payload']==plan['original_payload_contract']
 assert hashlib.sha256(OWNER.read_bytes()).hexdigest()==OWNER_SHA
 s=importlib.util.spec_from_file_location('literal_matching235_owner',OWNER);o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
 o._manifest_identity(a.scratch_manifest,a.scratch_manifest_sha256);o._manifest_outside_writable_parent(a.scratch_manifest,a.attempt_parent)
 _,v=o.bound_manifest(a.scratch_manifest,a.scratch_manifest_sha256)
 assert v['payload']==m['payload'] and v['artifacts']['mckernel_image']==plan['new_image']
 print(json.dumps(dict(status='PASS_ACTUAL_MATCHING115_ORIGINAL235_LITERAL_OWNER_API_NOT_NATIVE',manifest=a.scratch_manifest,manifest_sha256=a.scratch_manifest_sha256,native_release=None)))
if __name__=='__main__':main()
