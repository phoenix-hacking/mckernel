"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual F02 qualification, fail once with compact durable evidence.
"""
import json,runpy,traceback
from pathlib import Path
D=Path(__file__).resolve().parent
report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',completed=[],native_acceptance=False,physical_postjoin='SEPARATE_ROOT_READER',compiler_container_grant_Git_canonical_actions=0)
try:
    for filename in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py']:
        namespace=runpy.run_path(str(D/filename),run_name='__main__')
        report['completed'].append(filename)
    report['status']='PASS_ACTUAL_F02_BASE_PROFILE_ELF_LINK_GATES_PENDING_FOUR_DATA_OWNER_SUFFIX'
except BaseException as error:
    report['status']='FAIL_FIRST_ACTUAL_F02_QUALIFICATION_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
(D/'ACTUAL-BASE-QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if report['status'].startswith('FAIL'):raise SystemExit(1)
