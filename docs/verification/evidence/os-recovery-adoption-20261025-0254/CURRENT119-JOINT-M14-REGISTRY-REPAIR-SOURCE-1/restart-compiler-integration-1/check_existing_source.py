"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run the existing pinned pure checker, redirecting its reports into this owned lane.
No compiler, origin, export, Docker, admission or runtime execution occurs.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
PINS = {
    'check_joint.py': '928023c787707a725c80a04635dab3657d5ce13f88fd5c88a1cf22d0c80ecd60',
    'compose_joint.py': 'ebb3bf4f194fd47a5c1ae462c18327d879c94bbce5fc6e9bf8f5ab9e9877d527',
}
for name, expected in PINS.items():
    assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('current119_existing_source_checker', SOURCE / 'check_joint.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
reports = {}
def write_local(name, value):
    assert Path(name).name == name
    assert name not in reports
    reports[name] = value
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')
checker.write = write_local
started = time.monotonic()
with contextlib.redirect_stdout(io.StringIO()):
    checker.main()
assert reports['PURE-JOINT-CHECKS.json']['status'] == 'PASS_SOURCE_ONLY_JOINT119'
receipt = {
    'scope': checker.PINS['scope'],
    'status': 'PASS_EXISTING_SOURCE_CHECKER_REPORTS_REDIRECTED_ONLY',
    'checker_sha256': PINS['check_joint.py'],
    'report_names': sorted(reports),
    'wall_seconds': time.monotonic() - started,
    'source_paths': 18,
    'canonical_writes': 0,
    'compiler_origin_export_Docker_heavy_native_calls': 0,
    'runtime_authority': None,
}
(HERE / 'EXISTING-SOURCE-CHECK-RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
