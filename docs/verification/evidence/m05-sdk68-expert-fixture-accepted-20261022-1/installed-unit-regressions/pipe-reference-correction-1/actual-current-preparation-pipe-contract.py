"""Actual frozen current68 descriptor, retained proof; only container make digest injected."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, '/home/holden/mckernel')
from scripts import native_running_external_modules_offline as driver
prep=Path('/home/holden/mckernel/docs/verification/evidence/current68-host-control-sdk-preparation-20261022-1.json')
manifest=driver.load_preparation(prep)
assert 'make_pipe_probe' not in manifest
ref=manifest['references']['make_pipe_proof']
retained=Path(ref['retained_copy'])
original_digest=driver.digest
injections=[]
def container_make_digest(path):
    if path == Path('/usr/bin/make'):
        injections.append(str(path))
        return '97539f226fb36b8a39b147b6efe50a44f50c65773f7ad7013c0dc1e633f11362'
    return original_digest(path)
with patch.object(driver,'digest',side_effect=container_make_digest):
    driver.pipe_probe(manifest,retained.parent)
assert injections == ['/usr/bin/make']
print(json.dumps(dict(status='PASS_ACTUAL_CURRENT68_REFERENCE_PIPE_CONTRACT_HOST_MAKE_BOUNDARY_INJECTED',
    preparation_sha256=original_digest(prep),driver_sha256=original_digest(Path(driver.__file__)),
    retained_proof_sha256=original_digest(retained),reference=ref,
    sole_injected_boundary=injections,module_acceptance=False,native_acceptance=False),indent=2))
