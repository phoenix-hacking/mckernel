#!/usr/bin/env python3
"""Bind two genuine external review refs to frozen guard source; no runtime import.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
R = Path(__file__).resolve().parent
TEMPLATE_SHA256 = 'f95f7ecb07c51926cf0ebd86e5ba2e6373b781cc9c2b99c255352f66da066712'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bindings', type=Path, required=True)
    args = p.parse_args()
    bindings = json.loads(args.bindings.read_bytes())
    if not isinstance(bindings, dict) or set(bindings) != {'runtime_ref', 'basis_ref'}:
        raise ValueError('exact runtime_ref and basis_ref required; no unresolved refs')
    docs = {}
    for key, ref in bindings.items():
        if (not isinstance(ref, dict) or set(ref) != {'path', 'bytes', 'sha256'} or
                not Path(ref['path']).is_absolute() or type(ref['bytes']) is not int or ref['bytes'] <= 0 or
                re.fullmatch('[0-9a-f]{64}', str(ref['sha256'])) is None):
            raise ValueError('explicit actual pointer required: ' + key)
        raw = Path(ref['path']).read_bytes()
        if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('actual pointer bytes/hash differ: ' + key)
        docs[key] = json.loads(raw)
    review, request = docs['runtime_ref'], docs['basis_ref']
    if (review.get('status') != 'PASS_EXACT_FULL_RUNTIME_ADAPTER_OWNER_AND_REQUEST_BINDINGS_ONLY' or
            review.get('implementation_ownership') is not False or not review.get('reviewer') or
            review.get('reviewed_request_proposal') != bindings['basis_ref'] or
            request.get('schema') != 'mckernel.native-exact-mckernel-image-container-request.v1' or
            request.get('native_fork_owned_transaction') is not True or
            request.get('disk_identity') != request.get('source_identity') or
            request.get('source_derivative_sha256') != '050b953f46ff55f5ec819923819096fde8688400d860f7e666db9bbddb5b3f44' or
            request.get('materialization_sha256') != '317752dc9138cde2aac932da3b9e1b3e7f3434379361778a6aff035b2d46c44c'):
        raise ValueError('genuine independent current runtime/request review required')
    raw = (R / 'native_exact_current_optin_image_guard.UNBOUND.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('frozen guard template drift')
    text = raw.decode()
    if text.count('\nBINDINGS = None\n') != 1:
        raise ValueError('unique unbound assignment required')
    successor = text.replace('\nBINDINGS = None\n', '\nBINDINGS = ' + repr(bindings) + '\n')
    ast.parse(successor)
    target = R / 'native_exact_current_optin_image_guard.py'
    with target.open('x') as stream: stream.write(successor)
    print(json.dumps({'status': 'BOUND_GUARD_SOURCE_ONLY_NO_EXECUTION_RELEASE', 'path': str(target),
        'bytes': len(successor.encode()), 'sha256': hashlib.sha256(successor.encode()).hexdigest(),
        'bindings': bindings}, sort_keys=True))

if __name__ == '__main__': main()
