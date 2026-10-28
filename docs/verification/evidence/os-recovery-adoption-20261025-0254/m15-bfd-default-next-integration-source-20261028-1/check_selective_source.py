"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure pre-adoption check: read source bytes, verify the four-path change, run no compiler.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def checked_bytes(path, expected):
    data = path.read_bytes()
    if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
        raise ValueError(f'byte binding mismatch: {path}')
    return data


def transform(original, sites):
    result = original
    for site in sites:
        before, after = site['before'].encode(), site['after'].encode()
        if result.count(before) != 1:
            raise ValueError('selector site missing or repeated')
        result = result.replace(before, after, 1)
    restored = result
    for site in reversed(sites):
        before, after = site['before'].encode(), site['after'].encode()
        if restored.count(after) != 1:
            raise ValueError('postimage site missing or repeated')
        restored = restored.replace(after, before, 1)
    if restored != original:
        raise ValueError('unrelated source bytes changed')
    return result


def check(root=ROOT):
    plan = json.loads((HERE / 'INTEGRATION.json').read_text())
    for key in ('predecessor', 'acceptance'):
        checked_bytes(Path(plan[key]['path']), plan[key])
    original = checked_bytes(root / 'executer/user/CMakeLists.txt', plan['canonical_preimage'])
    if len(plan['sites']) != 5 or len(plan['changes']) != 4:
        raise ValueError('expected five selector sites and four production paths')
    result = transform(original, plan['sites'])
    for item in plan['changes']:
        actual = root / item['relative']
        if item['preimage'] is None:
            if actual.exists() or actual.is_symlink():
                raise ValueError(f'new production path already occupied: {actual}')
        else:
            checked_bytes(actual, item['preimage'])
        postimage = checked_bytes(HERE / 'candidate' / item['relative'], item['postimage'])
        if item['relative'] == 'executer/user/CMakeLists.txt' and result != postimage:
            raise ValueError('five-site result differs from accepted postimage')
    for item in plan['preserved_sources']:
        checked_bytes(root / item['relative'], item['actual'])
    return {
        'scope': __doc__.splitlines()[0],
        'status': 'PASS_SOURCE_ONLY_SELECTIVE_FOUR_PATH_INTEGRATION',
        'selector_sites': 5,
        'production_paths': 4,
        'preserved_existing_sources': 5,
        'canonical_writes': 0,
        'compiler_or_runtime_operations': 0,
        'new_default_native_file_credit': 0,
    }


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT), indent=2))
