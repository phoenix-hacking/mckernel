"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual SDK6 artifact/source/owner/read/image/launcher strict authority consumer; no mocked graph.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys
D=Path(__file__).resolve().parent
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12) and os.getuid()==1000
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load(D/'composite_module_binding.py','actual_SDK6_authority');a=m.authority();links=a.links();sdk=a.read(links['proofs']['SDK6_acceptance']);assert links['proofs']['SDK6_acceptance']['sha256']=='9159dcbd13c816f50d42390a05223e08a479b5f85d8183c4f61579bda20bc176'
manifest=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/actual-stage-1/manifest.json');raw=manifest.read_bytes();assert hashlib.sha256(raw).hexdigest()=='0c0c6e3bb3744665c5b4dddbfdd0977be39db25b78ca19392e5a380f7f0502f6';base=json.loads(raw)
base['modules']=[dict(path=sdk['artifacts'][n]['path'],sha256=sdk['artifacts'][n]['sha256'],size=sdk['artifacts'][n]['bytes'],mode=sdk['artifacts'][n]['mode']) for n in m.NAMES]
# Actual entry point used by unchanged strict pair/LONG manifest loader.
m.validate_module_binding(base)
binding=json.loads(Path(base['pair']['source_authority']['path']).read_bytes());a.validate(binding,base['artifacts']['mckernel_image'])
old=json.loads(raw)
try:m.validate_module_binding(old)
except ValueError as exc:old_refusal=str(exc)
else:raise AssertionError('old2eb3 manifest accepted asSDK6')
result=dict(scope=__doc__,status='PASS_ACTUAL_SDK6_STRICT_AUTHORITY_CURRENT_ARTIFACT_IMAGE_AND_LAUNCHER_CONSUMERS',SDK6_acceptance=links['proofs']['SDK6_acceptance'],source_identity=sdk['source_identity'],actual_nonce=sdk['nonce'],actual_module_descriptors=base['modules'],actual_image=base['artifacts']['mckernel_image'],actual_launcher=base['artifacts']['mcexec'],normalized_actual_reads=sdk['actual_reads'],actual_owner=sdk['owner_receipt'],old_SDK5_manifest_refusal=old_refusal,strict_loader_entrypoints_executed=['composite.validate_module_binding','repaired_image_authority.validate/native_proof'],new_capsule_full_load_manifest=None,new_capsule_loader_blocker='Oldcapsulecontains2eb3; true4489capsule mustbeproduced beforefullnewmanifest loader canpass. No fakecapsule/reference substitution.',new_capsule_stage=None,native_acceptance=False)
with (D/'ACTUAL-SDK6-AUTHORITY-CONSUMER-RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(result,sort_keys=True))
