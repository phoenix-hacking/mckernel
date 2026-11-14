"""Current accepted kernel/launcher/module tuple only; never runtime release.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import hashlib,importlib.util
PRIMITIVES=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-three-rounds-20261020-1/stage-preparation-1/repaired_image_authority.py')
assert hashlib.sha256(PRIMITIVES.read_bytes()).hexdigest()=='e375bd0eadf5ea8fa8ef6621603a8617b45bbce965a74f10e08b3cd7256b6f2e'
_spec=importlib.util.spec_from_file_location('_accepted_pair_authority_FD_primitives',PRIMITIVES)
_p=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_p)
checked=_p.checked;need=_p.need
CONTRACT={'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-stage-preparation-1/actual-data-1/CONSUMER-CONTRACT.ACTUAL-ACCEPTED-LAUNCHER.json', 'sha256': '1048577dc98e269a7b4a10a4e1785b84d93592f4213ebd9555e65618cd850035', 'size': 4842, 'mode': 33152}
IMAGE_SHA='1d8c4e78f7219792c0d2008952e11602a19451eb6697593ec10f0c77a8f1c101'
LAUNCHER_SHA='33f88082a995857c17ca07dab698e51d78064632462b4069b3c2396e0d29a131'
MODULE_SHAS=('51b48a9e42eaa2411cab2a28edf9bb5db8b2d648675d083473e926f91dd0e038', '82c9021f7491fa8bc6d178fe99e7d4b7b6f90838474a9c91b62ddb8edb3d13f8', '6571ac7eca13559d8bab65125d54facbbc65e84f815d4ff3fc77ec6aa1104972')

def validate(a,image,launcher,modules):
    need(a.get('schema')=='mckernel.current-six-launch.production-tuple-authority.v1' and a.get('consumer_contract')==CONTRACT,'fixed accepted current tuple authority')
    c=checked(CONTRACT)
    need(a['runtime_image']==image and a['runtime_launcher']==launcher and a['runtime_modules']==modules,'exact current runtime descriptors')
    need(image['sha256']==c['kernel_image']['sha256']==IMAGE_SHA and image['size']==c['kernel_image']['size'] and image['mode']==c['kernel_image']['mode'],'retained accepted image bytes/mode')
    need(launcher['sha256']==c['launcher_artifact']['sha256']==LAUNCHER_SHA and launcher['size']==c['launcher_artifact']['size'] and launcher['mode']==c['launcher_artifact']['mode'],'actual corrected launcher bytes/mode')
    need(modules==c['matched_modules'] and tuple(r['sha256'] for r in modules)==MODULE_SHAS,'current matched SDK module tuple')
    for key in ('kernel_artifact_acceptance','launcher_artifact_acceptance','launcher_dependency_join'):
        need(a[key]==c[key],'fixed current evidence '+key)
    k=checked(a['kernel_artifact_acceptance']);l=checked(a['launcher_artifact_acceptance']);d=checked(a['launcher_dependency_join'])
    need(k['schema']=='mckernel.current-numa-scheduler.production-image-artifact-review.v1' and k['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and k['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY' and k['implementation_ownership'] is False and k['reviewer'],'genuine kernel artifact acceptance')
    need(k['artifact_descriptors_verified']['artifacts/mckernel.img']['sha256']==IMAGE_SHA and k['artifact_descriptors_verified']['artifacts/mckernel.img']['bytes']==image['size'],'kernel acceptance descriptor')
    need(l['schema']=='mckernel.launcher-only-production-artifact-review.v1' and l['status']=='PASS_ACTUAL_LAUNCHER_ONLY_PRODUCTION_TARGET_ARTIFACT' and l['implementation_ownership'] is False and l['reviewer'] and l['target']=='mcexec' and l['kernel_rebuilt'] is False and l['launcher_source_sha256']==c['launcher_source_sha256'],'genuine launcher-only acceptance')
    fact=l['artifact_descriptors_verified']['artifacts/mcexec']
    need(fact['sha256']==LAUNCHER_SHA and fact['bytes']==launcher['size'] and fact['path']==c['launcher_artifact']['path'],'launcher acceptance descriptor')
    need(d['schema']=='mckernel.launcher-only-dependency-join-review.v1' and d['status']=='PASS_ACTUAL_LAUNCHER_ONLY_DEPENDENCY_JOIN' and d['implementation_ownership'] is False and d['reviewer'],'genuine launcher dependency acceptance')
    need(d['launcher']==fact and d['baseline_dependency_acceptance']==c['unchanged_dependency_ancestry'] and d['actual_elf_needed_provider_join'] is True,'current ELF provider/dependency join')
    return c
