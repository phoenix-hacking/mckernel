"""Actual installed source/preparation regression; no Docker/root/compiler."""
import json
from pathlib import Path
import sys
sys.path.insert(0, '/home/holden/mckernel')
from scripts import native_running_external_modules_offline as driver
prep_path=Path('/home/holden/mckernel/docs/verification/evidence/current68-host-control-sdk-preparation-20261022-1.json')
manifest=driver.load_preparation(prep_path)
ref=manifest['references']['make_pipe_proof']
try:
    driver.pipe_probe(manifest, Path(ref['retained_copy']).parent)
except Exception as error:
    print(json.dumps(dict(status='FAIL_ACTUAL_PREPARATION_PIPE_CONTRACT', preparation_sha256=driver.digest(prep_path),
                         error=type(error).__name__+': '+str(error), make_pipe_probe=manifest.get('make_pipe_probe'),
                         existing_reference=ref),indent=2))
    raise SystemExit(1)
print(json.dumps(dict(status='PASS_ACTUAL_PREPARATION_PIPE_CONTRACT')))
