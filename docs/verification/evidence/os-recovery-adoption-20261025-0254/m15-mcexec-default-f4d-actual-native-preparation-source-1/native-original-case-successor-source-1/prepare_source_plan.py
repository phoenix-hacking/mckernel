"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare separate original-case data proposal only; never composes or runs a guest.
"""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
L=HERE.parent;E=L.parent

def ref(f):
    raw=f.read_bytes();s=f.stat();return dict(path=str(f),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=s.st_mode)
def load(f):return json.loads(f.read_bytes())
def main():
    native=load(L/'SOURCE-BOUND-NATIVE-CONTRACT.json');f05path=E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-stage-source-1/offline-materialization-1/manifest.HOST-STATIC.json';f05=load(f05path);receip=load(Path(f05['staging']['overlay_manifest']['path']));strict=E/'f03-f06-default-rustmm-strict235-preparation-1/offline-preparation-1/manifest.HOST-STATIC.json';template=load(strict);loader=L/'loader-current-limit-correction-1/independent-review-1/INDEPENDENT-ACTUAL-LOADER-ACCEPTANCE.json'
    assert ref(loader)['sha256']=='8417dbe4a42058cd859d01d1934eefbf72bca34e4c4ed0818c76434701734d4c'
    installed=ref(Path(native['installed']['path']));overlay=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/native_diagnostic_overlay.py');collector=f05['staging']['collector'];base=f05['artifacts']['root_base'];cases={}
    for key,name in [('startup','startup.argv-empty'),('strict235','P-M06-01-process-exec-wait-235B')]:
        old=native['cases'][name];payload=ref(Path(old['payload']['path']));path=HERE/(key+'-overlay.cpio.gz');m=copy.deepcopy(template);m['case_id']=name;m['modules']=copy.deepcopy(f05['modules']);m['cleanup_profile']['modules']=copy.deepcopy(f05['modules']);m['artifacts']=copy.deepcopy(f05['artifacts']);m['artifacts'].update(mcexec=installed,payload=payload,root_base=base,initramfs=base)
        m['payload']=dict(argv=old['argv'],cwd=old['cwd'],env=old['environment'],oracle=old['oracle'],stdout_limit_bytes=1024,stderr_limit_bytes=1024);m['staging']=dict(base_initramfs=base,derived_initramfs=None,collector=collector,overlay_source=ref(overlay),overlay_manifest=None)
        argv=['/usr/bin/python3','-B',str(overlay),base['path'],payload['path'],collector['path'],installed['path'],str(path),'--collector-sha256',collector['sha256'],'--mcexec-sha256',installed['sha256'],'--payload-sha256',payload['sha256'],'--base-sha256',base['sha256'],'--base-size',str(base['size']),'--base-cpio-sha256',receip['base_cpio_sha256'],'--base-cpio-size',str(receip['base_cpio_size'])]
        cases[key]=dict(case_id=name,manifest_proposal=m,overlay_command=dict(argv=argv,purpose=native['scope']+' Separate original-case overlay selecting installed Rust executor; frozen F05 stays unchanged.'),expected_output=str(path),actual_overlay_receipt=None,native_release=None,execution_authority=False)
    plan=dict(scope=native['scope'],status='SOURCE_ONLY_SEPARATE_ORIGINAL_CASES_INSTALLED_RUST_EXECUTOR_SUCCESSOR',selected_executor=installed,installed_loader_acceptance=ref(loader),source_template=ref(strict),frozen_F05_manifest=ref(f05path),frozen_F05_untouched=True,source_base=base,source_base_raw={k:receip[k] for k in ('base_cpio_sha256','base_cpio_size')},supported_image=f05['artifacts']['mckernel_image'],modules=f05['modules'],collector=collector,diagnostic=ref(E/'f05-v2-root-export-and-native-preparation-source-1/bound-native-runtime-1/native_diagnostic.py'),overlay_source=ref(overlay),cases=cases,compose_profile_proposal=dict(cpu=6,jobs=1,AS_bytes=2*2**30,CPU_seconds=60,work_wall_seconds=90,FSIZE_bytes=32<<20,HOST_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,aggregate_memory_ceiling_bytes=23259332608,aggregate_jobs_max=7),current_free_or_runtime_grant=None,new_case_quota=0,claim='Potential exact installed Rust-executor main/startup/strict235 native behavior only; no all349/all51/allocation/wholefile acceptance.',execution_authority=False)
    (HERE/'ORIGINAL-CASES-SUCCESSOR.NOT-RELEASED.json').write_text(json.dumps(plan,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status=plan['status'],plan=ref(HERE/'ORIGINAL-CASES-SUCCESSOR.NOT-RELEASED.json'))))
if __name__=='__main__':main()
