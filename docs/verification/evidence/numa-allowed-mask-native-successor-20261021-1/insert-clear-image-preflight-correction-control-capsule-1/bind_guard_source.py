#!/usr/bin/env python3
"""Bind finite genuine source/gate/runtime/request refs; never import a runtime.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

R = Path(__file__).resolve().parent
TEMPLATE_SHA256 = '5c8005d1934fc5a074b8c2cccca68eb320a9f67073813e8ca120f2b69148b6ab'
SLOTS = ('SOURCE_REF', 'GATES_REF', 'RESULT_REF', 'VALIDATOR_CAPTURE_REF',
         'MATERIAL_CAPTURE_REF', 'RECEIPT_REF')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings', type=Path, required=True)
    args = parser.parse_args()
    values = json.loads(args.bindings.read_bytes())
    if not isinstance(values, dict) or set(values) != set(SLOTS) | {'BINDINGS'}:
        raise ValueError('exact six evidence slots and BINDINGS required')
    bindings = values['BINDINGS']
    if not isinstance(bindings, dict) or set(bindings) != {'runtime_ref', 'basis_ref'}:
        raise ValueError('exact runtime_ref and basis_ref required; no unresolved refs')
    pointers = {key: values[key] for key in SLOTS}
    pointers.update(bindings)
    docs = {}
    for key, record in pointers.items():
        if (not isinstance(record, dict) or set(record) != {'path', 'bytes', 'sha256'} or
                not Path(record['path']).is_absolute() or type(record['bytes']) is not int or
                record['bytes'] <= 0 or re.fullmatch('[0-9a-f]{64}', str(record['sha256'])) is None):
            raise ValueError('explicit actual pointer required: ' + key)
        raw = Path(record['path']).read_bytes()
        if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('actual pointer bytes/hash differ: ' + key)
        docs[key] = json.loads(raw)
    review, request = docs['runtime_ref'], docs['basis_ref']
    if (review.get('status') != 'PASS_EXACT_FULL_RUNTIME_ADAPTER_OWNER_AND_REQUEST_BINDINGS_ONLY' or
            review.get('implementation_ownership') is not False or not review.get('reviewer') or
            review.get('reviewed_request_proposal') != bindings['basis_ref'] or
            review.get('actual_source_materialization_acceptance') != values['SOURCE_REF'] or
            review.get('actual_coupled_source_gate_acceptance') != values['GATES_REF'] or
            request.get('schema') != 'mckernel.native-exact-mckernel-image-container-request.v1' or
            request.get('native_fork_owned_transaction') is not True or
            request.get('disk_identity') != request.get('source_identity') or
            request.get('source_derivative_sha256') != 'cae8b221bdaa12f2212e4e8d0cfd8f39ab6b5dce6ba30c821f4997a2be8b0d87' or
            request.get('materialization_sha256') != '3b2cac15a99f4a6a85e5ca213ce915d615d74b6ed854abd3cd2840bf327d857f'):
        raise ValueError('genuine independent current runtime/request review required')
    raw = (R/'native_exact_current_optin_image_guard.UNBOUND.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('frozen guard template drift')
    text = raw.decode()
    assignments = {key: values[key] for key in SLOTS}
    assignments['BINDINGS'] = bindings
    for key, value in assignments.items():
        token = '\n' + key + ' = None\n'
        if text.count(token) != 1:
            raise ValueError('unique unresolved assignment required: ' + key)
        text = text.replace(token, '\n' + key + ' = ' + repr(value) + '\n')
    ast.parse(text)
    target = R/'native_exact_current_optin_image_guard.py'
    with target.open('x') as stream:
        stream.write(text)
    print(json.dumps(dict(status='BOUND_GUARD_SOURCE_ONLY_NO_EXECUTION_RELEASE',
        path=str(target), bytes=len(text.encode()), sha256=hashlib.sha256(text.encode()).hexdigest(),
        bindings=values), sort_keys=True))

if __name__ == '__main__':
    main()
