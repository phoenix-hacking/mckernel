"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root ordinary one-manifest stage from actual bound bytes; same successful235 typed/API procedure.
No compose, compiler, guard, observation, native call, grant or cleanup; execute only as Root-owned stage.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent
PINS={'manifest': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/root-actual-compose-1/manifest.HOST-STATIC.json', 'bytes': 8986, 'sha256': 'b362c873552a9d3e4344dc311cc5fc69b7fa28b2f7ffe8a05cdd815d57b6b6ec'}, 'binding': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/root-actual-compose-1/COMPOSITION-RESULT.json', 'bytes': 2794, 'sha256': '8a0d82cc874b95c25c84f3cfa167970390365a4cfc2659d431a51d3ebf5a83ff'}, 'binder': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/ordinary-compose-profile-accepted115-source-1/check_actual_scratch_binding.py', 'bytes': 1862, 'sha256': 'd2db4c9a719d927040965e4ff0a80197564183a0907b59763ce797ebbbe60513'}, 'owner': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v2-root-export-and-native-preparation-source-1/bound-native-runtime-1/native_diagnostic_container_owner.py', 'bytes': 94258, 'sha256': 'af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10'}, 'planned_parent': '/home/holden/mckernel-work/scratch/f02p115n1', 'scratch_parent': '/home/holden/mckernel-work/scratch/f02p115n1-inputs', 'scratch_manifest': '/home/holden/mckernel-work/scratch/f02p115n1-inputs/manifest.json'}
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert os.getuid()==os.geteuid()==1000
 for key in ('manifest','binding','binder','owner'):assert ref(PINS[key]['path'])==PINS[key]
 source=Path(PINS['manifest']['path']);raw=source.read_bytes();assert len(raw)<1<<20 and not source.is_symlink()
 parent=Path(PINS['planned_parent']);inputs=Path(PINS['scratch_parent']);target=Path(PINS['scratch_manifest'])
 receipt=D/'ROOT-ACTUAL-SCRATCH-STAGE.json'
 for p in (parent,inputs,receipt):assert not os.path.lexists(p),str(p)
 assert parent.parent==inputs.parent==Path('/home/holden/mckernel-work/scratch') and parent.name=='f02p115n1' and inputs.name=='f02p115n1-inputs'
 parent.mkdir(mode=0o700);inputs.mkdir(mode=0o700)
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(inputs,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 assert target.read_bytes()==raw and not list(parent.iterdir())
 spec=importlib.util.spec_from_file_location('literal_matching115_235_owner',PINS['owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
 owner._manifest_identity(str(target),ref(target)['sha256']);owner._manifest_outside_writable_parent(str(target),str(parent));diagnostic,m=owner.bound_manifest(str(target),ref(target)['sha256'])
 assert m['case_id']=='P-M06-01-process-exec-wait-235B' and m['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 assert m['artifacts']['mckernel_image']['sha256']=='de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024'
 value=dict(scope=__doc__.splitlines()[0],status='ACTUAL_ROOT_ORDINARY_MATCHING115_235_MANIFEST_SCRATCH_STAGE_OWNER_API_PASS',source_manifest=PINS['manifest'],scratch_manifest=ref(target),planned_attempt_parent=str(parent),nonce=None,runtime_authority=None)
 with receipt.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=value['status'],stage=ref(receipt),manifest=ref(target),actual_owner_API_only=True,native_acceptance=False)))
if __name__=='__main__':main()
