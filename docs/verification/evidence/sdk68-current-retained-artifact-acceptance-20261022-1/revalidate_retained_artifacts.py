"""One read-only retained-artifact validation; never build or load modules.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

HERE = Path(__file__).resolve().parent
FIXED = {'driver_sha256': 'a129da6157069d341226741b3a948712cca51c6b976eac3bf55001a5780ff539', 'original_receipt_sha256': '58ffcfb9febb788d6e3f4c6d949f0307c88031b95940655b49f8a577a0bbb2d3', 'candidate_root': '/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-candidate-20352dabb9c94403a03c224ec2826ff2', 'inputs_root': '/home/holden/mckernel-work/scratch/native-running-modules-inputs-20352dabb9c94403a03c224ec2826ff2'}

def digest(path):
    with path.open('rb') as stream:
        value = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()

def need(ok, message):
    if not ok: raise ValueError(message)

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--output',required=True)
    output=Path(parser.parse_args().output)
    need(output.is_absolute() and output.parent==HERE and output.resolve()==output and
         re.fullmatch(r'readonly-validation-[1-9][0-9]*',output.name), 'fresh isolated output required')
    output.mkdir(mode=0o700)
    report=dict(schema='mckernel.current68.retained-artifact-revalidation.v1',status='FAIL',
        application_acceptance=False,production_acceptance=False,native_acceptance=False,
        build_reexecuted=False,compiled_bytes_modified=False,original_driver_status='FAIL')
    started=time.monotonic()
    try:
        driver_path=HERE/'native_running_external_modules_offline.py'
        need(digest(driver_path)==FIXED['driver_sha256'],'reviewed corrected checker hash')
        candidate=Path(FIXED['candidate_root']);inputs=Path(FIXED['inputs_root'])
        original_path=candidate/'evidence/receipt.json'
        need(digest(original_path)==FIXED['original_receipt_sha256'],'original FAIL receipt changed')
        original=json.loads(original_path.read_text())
        need(original['status']=='FAIL' and original['make_returncode']==0 and
             original['error']=='ValueError: missing held v12/control-receipt export: ihk_os_create_unbooted_v12',
             'exact original postbuild checker failure required')
        spec=importlib.util.spec_from_file_location('retained_current68_artifact_checker',driver_path)
        driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
        def no_process(*args,**kwargs):raise AssertionError('read-only validator cannot start a process')
        driver.subprocess.run=no_process
        manifest=driver.load_preparation(inputs/'preparation.json')
        need(original['preparation_sha256']==driver.PREPARATION_SHA256 and
             original['source_candidate_sha']==driver.SOURCE_CANDIDATE_SHA and
             original['source_provenance']['closure_sha256']==manifest['source_identity'] and
             original['source_sha256']=={r['path']:r['sha256'] for r in manifest['closure']},
             'original successful compile/source/preparation provenance join')
        retained=original['retained_files']
        need(type(retained) is dict and len(retained)<=4096 and
             sum(row['bytes'] for row in retained.values())<=256*1024*1024,
             'bounded original retained module tree')
        def snapshot():
            files=driver.files(candidate/'modules')
            need(set(files)==set(retained),'retained module file set changed')
            for name,row in retained.items():
                need(files[name].stat().st_size==row['bytes'] and digest(files[name])==row['sha256'],
                     'retained compiled/source file changed: '+name)
        snapshot()
        need((candidate/'evidence/make.stderr').stat().st_size==0,'original compiler stderr not empty')
        driver.closure(manifest,candidate)
        artifacts=driver.outputs(candidate,inputs)
        snapshot()
        need(digest(original_path)==FIXED['original_receipt_sha256'],'original FAIL receipt changed after read')
        report.update(status='RETAINED_CURRENT68_ARTIFACT_CHECKS_PASS',
            source_identity=manifest['source_identity'],preparation_sha256=driver.PREPARATION_SHA256,
            checker_sha256=FIXED['driver_sha256'],original_driver_receipt=dict(path=str(original_path),
                sha256=FIXED['original_receipt_sha256'],status='FAIL',make_returncode=0,error=original['error']),
            original_retained_file_count=len(retained),original_retained_bytes=sum(row['bytes'] for row in retained.values()),
            before_after_retained_hashes_match=True,artifacts=artifacts,
            validation_scope='Same retained three linked modules; source/compiler/cfg/module-order/vermagic/MM/current-export checks. No make, subprocess, module load, container or native acceptance.')
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
    report['wall_seconds']=time.monotonic()-started
    path=output/'report.json';path.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],report=str(path),sha256=digest(path))))
    return int(report['status']!='RETAINED_CURRENT68_ARTIFACT_CHECKS_PASS')

if __name__=='__main__':raise SystemExit(main())
