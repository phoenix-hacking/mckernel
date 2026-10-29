"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root ordinary one-manifest stage from actual bound bytes; same successful235 typed/API procedure.
No compose, compiler, guard, observation, native call, grant or cleanup; execute only as Root-owned stage.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent
PINS={'manifest': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/root-actual-compose-1/manifest.HOST-STATIC.json', 'bytes': 9068, 'sha256': '25bb59f824698dc3141830ef7108984379399dc69684970e9b3a79e61d48ac8c'}, 'binding': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/root-actual-compose-1/COMPOSITION-RESULT.json', 'bytes': 2863, 'sha256': '1bd87fc2436e37baf5bd5bd102f257fdb8ce6b4408274b4838a30b2a3d312060'}, 'composition_review': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/actual-composition-review-1/ACTUAL-COMPOSITION-ACCEPTANCE.json', 'bytes': 5309, 'sha256': 'dcfc6b675ee910df1e0aa3649c8cb95a433568065c9573460349df1b56c529bf'}, 'owner': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v2-root-export-and-native-preparation-source-1/bound-native-runtime-1/native_diagnostic_container_owner.py', 'bytes': 94258, 'sha256': 'af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10'}, 'planned_parent': '/home/holden/mckernel-work/scratch/m119n1', 'scratch_parent': '/home/holden/mckernel-work/scratch/m119n1i', 'scratch_manifest': '/home/holden/mckernel-work/scratch/m119n1i/manifest.json'}
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def validate_bound_source(manifest,binding,review):
 assert manifest['case_id']=='P-M06-01-process-exec-wait-235B'
 assert manifest['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 assert manifest['artifacts']['mckernel_image']==binding['image']==review['image']
 assert binding['manifest']==review['manifest'] and binding['manifest']['sha256']==PINS['manifest']['sha256']
 assert manifest['artifacts']['mckernel_image']['sha256']=='759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31'
 assert manifest['staging']['derived_initramfs']==binding['overlay']==review['overlay']
 assert manifest['staging']['base_initramfs']==binding['base']==review['base']
 assert review['decision']=='PASS_EXACT_CURRENT119_IMAGE_ONLY_MATCHING235_OFFLINE_COMPOSITION' and review['independent'] is True and review['implementation_ownership'] is False
 assert review['full_map_records']==review['base_map_records']==60 and review['changed_final_map_records']==['images/mckernel.img'] and all(review['checks'].values())
 assert review['guest_execution_authorized'] is False and review['native_release'] is None
 for key in ('source_authority','capability','nonce','current_ledger','current_free','native_release','native_acceptance'):assert binding[key] is None
 return True

def main():
 assert os.getuid()==os.geteuid()==1000
 for key in ('manifest','binding','composition_review','owner'):assert ref(PINS[key]['path'])==PINS[key]
 source=Path(PINS['manifest']['path']);raw=source.read_bytes();assert len(raw)<1<<20 and not source.is_symlink()
 validate_bound_source(json.loads(raw),json.loads(Path(PINS['binding']['path']).read_bytes()),json.loads(Path(PINS['composition_review']['path']).read_bytes()))
 parent=Path(PINS['planned_parent']);inputs=Path(PINS['scratch_parent']);target=Path(PINS['scratch_manifest'])
 receipt=D/'ROOT-ACTUAL-SCRATCH-STAGE.json'
 for p in (parent,inputs,receipt):assert not os.path.lexists(p),str(p)
 assert parent.parent==inputs.parent==Path('/home/holden/mckernel-work/scratch') and parent.name=='m119n1' and inputs.name=='m119n1i'
 parent.mkdir(mode=0o700);inputs.mkdir(mode=0o700)
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(inputs,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 assert target.read_bytes()==raw and not list(parent.iterdir())
 spec=importlib.util.spec_from_file_location('literal_matching119_235_owner',PINS['owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
 owner._manifest_identity(str(target),ref(target)['sha256']);owner._manifest_outside_writable_parent(str(target),str(parent));diagnostic,m=owner.bound_manifest(str(target),ref(target)['sha256'])
 assert m['case_id']=='P-M06-01-process-exec-wait-235B' and m['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 assert m['artifacts']['mckernel_image']['sha256']=='759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31'
 value=dict(scope=__doc__.splitlines()[0],status='ACTUAL_ROOT_ORDINARY_MATCHING119_235_MANIFEST_SCRATCH_STAGE_OWNER_API_PASS',source_manifest=PINS['manifest'],scratch_manifest=ref(target),planned_attempt_parent=str(parent),nonce=None,runtime_authority=None)
 with receipt.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=value['status'],stage=ref(receipt),manifest=ref(target),actual_owner_API_only=True,native_acceptance=False)))
if __name__=='__main__':main()
