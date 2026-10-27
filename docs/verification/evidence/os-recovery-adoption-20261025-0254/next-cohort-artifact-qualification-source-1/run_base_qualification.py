"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only first-failure capture for actual next cohort accepted observer gates.
"""
from pathlib import Path
import json,runpy,traceback
D=Path(__file__).resolve().parent
report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',completed=[],native_acceptance=False,Root_physical_postjoin='SEPARATE_ROOT_READER')
try:
 for name in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py']:
  runpy.run_path(str(D/name),run_name='__main__');report['completed'].append(name)
 report['status']='PASS_NEXT_ACTUAL_PRODUCER_PANIC_LOGGER_CLONE_STORAGE_IMAGE_LINK_BASE_GATES'
except BaseException as error:
 report['status']='FAIL_FIRST_NEXT_ACTUAL_BASE_GATE_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
(D/'ACTUAL-BASE-QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if report['status'].startswith('FAIL'):raise SystemExit(1)
