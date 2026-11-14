#!/usr/bin/python3
"""ONE bounded ordinary synthetic caller fixture; run only after CPU7 allocation.
Creates disjoint tiny files only under mandatory new --output, preserves results.
Root/live census is mocked; this cannot prove root observation or real cleanup.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

SOURCE = Path(__file__).with_name('exact120.py')
spec = importlib.util.spec_from_file_location('cleanup2345', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def scenario(out, fail_preflight=False, fail_second=False, missing_identity=False):
    out.mkdir()
    candidate, retained = out / 'candidate', out / 'retained'
    candidate.mkdir(); retained.mkdir()
    rows = []
    for i in range(120):
        p, r = candidate / ('archive-%03d' % i), retained / ('archive-%03d' % i)
        p.write_bytes(b'x'); r.write_bytes(b'x')
        rows.append({'candidate': str(p), 'candidate_metadata': m.meta(p.lstat()),
                     'retained_repo_path': str(r), 'retained_metadata': m.meta(r.lstat())})
    lock = out / 'rootmutex'
    lock.write_bytes(b'')
    lid = (lock.stat().st_dev, lock.stat().st_ino)
    observation = {'records': {}, 'mount': {'fixture': True}, 'processes': [], 'unmatched': {str(candidate): {}}}
    release = {'status': 'EXECUTION_RELEASE', 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               'manifest_sha256': m.PIN, 'attestations': {k: True for k in m.ATTEST},
               'independent_review': {'status': 'PASS', 'sha256': '0' * 64}, 'boot_id': m.BOOT,
               'coordinator_identity': [os.getpid(), m.proc_identity(os.getpid())[0]], 'expires_unix': time.time() + 60,
               'minimum_available_bytes': {'host': 16 << 30, 'scratch': 12 << 30}, 'expected_records': {},
               'observation': observation, 'observed_unix': time.time(), 'journal': str(out / 'actual-fixture.jsonl')}
    if missing_identity:
        release.pop('coordinator_identity')
    rp = out / 'release.json'; rp.write_text(json.dumps(release))
    if fail_preflight:
        Path(rows[-1]['candidate']).write_bytes(b'drift')
    cap = {k: {'available_bytes': 100 << 30} for k in ('host', 'scratch')}
    actual_unlink = os.unlink
    calls = []
    def unlink(name, *, dir_fd):
        calls.append(name)
        if fail_second and len(calls) == 2:
            raise OSError('injected second unlink failure')
        return actual_unlink(name, dir_fd=dir_fd)
    errors = []
    with patch.multiple(m, BASE=out, REPO=out, ROOT=out, LOCK=lock, LOCK_ID=lid,
                        PARENTS={str(candidate)}, pinned=lambda: {'rows': rows}, snapshot=lambda *a: observation,
                        capacity=lambda: cap, mount_identity=lambda: observation['mount'], records=lambda: {},
                        unmatched=lambda x: observation['unmatched'], git_available=lambda x: {}), \
         patch.object(m.os, 'geteuid', return_value=0), patch.object(m.os, 'unlink', side_effect=unlink), \
         patch.object(sys, 'argv', [str(SOURCE), '--mode', 'execute', '--release', str(rp)]):
        # Held's retained parent derives REPO/docs; fixture supplies that real path.
        (out / 'docs/verification').mkdir(parents=True)
        (out / 'docs/verification/evidence').symlink_to(retained, target_is_directory=True)
        # Explicit real safe-directory helper must reject symlinked ancestry.
        try:
            m.safe_directory(out / 'docs/verification/evidence')
        except OSError:
            pass
        else:
            raise AssertionError('no-follow ancestor accepted symlink')
        # Replace fixture symlink with a real retained parent and update rows.
        actual_unlink(out / 'docs/verification/evidence')
        (out / 'docs/verification/evidence').mkdir()
        for r in rows:
            old = Path(r['retained_repo_path'])
            new = out / 'docs/verification/evidence' / old.name
            old.rename(new)
            r['retained_repo_path'] = str(new)
            r['retained_metadata'] = m.meta(new.lstat())
        try:
            m.main()
        except Exception as exc:
            errors.append(repr(exc))
    remains = [Path(r['candidate']).exists() for r in rows]
    events = [json.loads(line) for line in (out / 'actual-fixture.jsonl').read_text().splitlines()] if (out / 'actual-fixture.jsonl').exists() else []
    if fail_preflight or missing_identity:
        assert errors and all(remains) and not calls and not events, (errors, calls)
    elif fail_second:
        assert errors and sum(remains) == 119 and len(calls) == 2, (errors, sum(remains), calls)
        assert events[-1]['status'] == 'STOP_PARTIAL' and len(events[-1]['removed']) == 1
        assert len(events[-1]['not_attempted']) == 118
        assert events[-1]['failed_or_uncertain_path'] == rows[1]['candidate']
    else:
        assert not errors and sum(remains) == 0 and len(calls) == 120, (errors, sum(remains), calls)
        assert events[-1]['status'] == 'COMPLETE' and len(events[-1]['removed']) == 120
    assert all(Path(r['retained_repo_path']).exists() for r in rows)
    assert lock.exists()
    return {'status': 'PASS', 'name': out.name, 'unlink_calls': len(calls), 'retained': 120, 'errors_expected': errors}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); a = p.parse_args()
    out = Path(a.output); out.mkdir(exist_ok=False)
    results = []
    try:
        assert m.related('/a/b/c', {'/a/b'}) and not m.related('/', {'/a/b'})
        assert m.exposes('/', {'/a/b'}) and not m.exposes('/other', {'/a/b'})
        results.append(scenario(out / 'missing-identity', missing_identity=True))
        results.append(scenario(out / 'last-row-preflight-drift', fail_preflight=True))
        results.append(scenario(out / 'second-unlink-failure', fail_second=True))
        results.append(scenario(out / 'complete120'))
        result = {'status': 'PASS_SYNTHETIC_ONLY', 'scenarios': results, 'live_root_checks_tested': False}
    except BaseException as exc:
        result = {'status': 'FAIL_PRESERVED', 'scenarios': results, 'error': repr(exc)}
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        raise
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
