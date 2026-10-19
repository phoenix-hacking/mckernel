#!/usr/bin/python3
"""One actual records() role/type regression, ordinary synthetic files only.
No root, no real controlrecord mutation, no observation replay/archives.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).with_name('exact120.py')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); a = parser.parse_args()
    out = Path(a.output); out.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('records2345', SOURCE)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cases = []
    for case in ('exact-directory-and-regular-file', 'directory-replaced-by-file', 'directory-inode-changed', 'nested-exclusion-changed', 'unknown-nonregular-refused'):
        root = out / case; root.mkdir()
        q = root / 'historical-quarantine'; q.mkdir(mode=0o700)
        child = q / 'retained-exclusion.json'; child.write_bytes(b'{"historical":true}\n')
        lease = root / 'active-lease.json'; lease.write_bytes(b'{"owner":"fixture"}\n')
        binding = {'path': str(q), 'metadata': m.meta(q.lstat()), 'child_name': child.name,
                   'child_metadata': m.meta(child.lstat()), 'child_sha256': hashlib.sha256(child.read_bytes()).hexdigest()}
        m.ROOT = root; m.RETAINED_QUARANTINE = binding
        expected = None
        if case == 'directory-replaced-by-file':
            q.rename(root / 'original'); q.write_bytes(b'wrong type'); expected = 'NotADirectoryError'
        elif case == 'directory-inode-changed':
            q.rename(root / 'original'); q.mkdir(); (q / child.name).write_bytes(b'{"historical":true}\n'); expected = 'directory identity drift'
        elif case == 'nested-exclusion-changed':
            child.write_bytes(b'changed retained bytes'); expected = 'retained exclusion identity drift'
        elif case == 'unknown-nonregular-refused':
            (root / 'unknown-lock').mkdir(); expected = 'ownership record not regular'
        error = None
        before = {str(p): m.meta(p.lstat()) for p in root.rglob('*')}
        try:
            result = m.records()  # Actual production body; no record/type/IO mocks.
            assert result[str(q)]['role'] == 'retained-historical-export26-exclusion-quarantine'
            assert result[str(lease)]['sha256'] == hashlib.sha256(lease.read_bytes()).hexdigest()
        except BaseException as exc:
            error = repr(exc)
        after = {str(p): m.meta(p.lstat()) for p in root.rglob('*')}
        assert before == after, 'records body modified fixture'
        ok = error is None if expected is None else error is not None and expected in error
        row = {'case': case, 'status': 'PASS' if ok else 'FAIL', 'expected': expected, 'error': error, 'production_body': 'records()', 'fixture_inventory_unchanged': True}
        cases.append(row)
        if not ok:
            (out / 'result.json').write_text(json.dumps({'status': 'FAIL_PRESERVED', 'cases': cases}, indent=2) + '\n')
            raise RuntimeError('first actual-records fixture failure: ' + repr(row))
    result = {'status': 'PASS_RECORDS_ROLE_BOUNDARY_SYNTHETIC_ONLY', 'interpreter': sys.executable, 'version': sys.version, 'cases': cases,
              'unaffected_cases_replayed': False, 'real_observer_replayed': False}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'cases': len(cases), 'version': sys.version.split()[0]}))


if __name__ == '__main__':
    main()
