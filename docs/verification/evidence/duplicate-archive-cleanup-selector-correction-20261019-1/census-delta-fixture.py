#!/usr/bin/python3
"""Affected-boundary fixture only. Real proc fds/maps/cwd/mountinfo, no mocks.
ONE parent command; sequential child cases use declared /usr/bin/python3 -I.
A single-self proc view narrows process inventory, while every per-task boundary
and proc_identity read resolves live kernel /proc. No root/global census claim.
Preserves all outputs; requires a NEW private --output.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).with_name('exact120.py')
CASES = ('positive-held-and-enumerator', 'positive-deleted-held', 'inherited-fd0', 'inherited-fd1', 'inherited-fd2', 'inherited-extra', 'inherited-enumerator')


def child(out, case):
    spec = importlib.util.spec_from_file_location('exact120_delta', SOURCE)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    out.mkdir()
    candidate = out / 'candidate'; candidate.mkdir()
    payload = candidate / 'payload'; payload.write_bytes(b'synthetic')
    targetfd = os.open(payload, os.O_RDONLY)
    parentfd = os.open(candidate, os.O_RDONLY | os.O_DIRECTORY)
    view = out / 'proc'; view.mkdir(); (view / str(os.getpid())).symlink_to('/proc/%s' % os.getpid(), target_is_directory=True)
    m.PARENTS = {str(candidate)}
    extra = saved = replaced = None
    expected = None
    if case == 'positive-deleted-held':
        os.unlink(payload)  # synthetic only; real readlink includes deleted suffix
    if case.startswith('inherited-fd'):
        replaced = int(case[-1]); saved = os.dup(replaced); os.dup2(targetfd, replaced)
        expected = 'open descriptor consumer'
    elif case == 'inherited-extra':
        extra = os.dup(targetfd); expected = 'open descriptor consumer'
    elif case == 'inherited-enumerator':
        extra = os.open('/proc/%s/task/%s/fd' % (os.getpid(), os.getpid()), os.O_RDONLY | os.O_DIRECTORY)
        expected = 'extra self enumeration descriptor'
    held = {'rows': [{'candidate_metadata': m.meta(os.fstat(targetfd))}], 'target_fds': [targetfd], 'parent_fds': [parentfd]}
    error = None
    try:
        assert m.strip_deleted('name (deleted)') == 'name'
        assert m.strip_deleted('name') == 'name'
        actual = m.process_census(held, proc_root=view)
        assert actual == [[os.getpid(), m.proc_identity(os.getpid())[0]]]
    except BaseException as exc:
        error = repr(exc)
    finally:
        if replaced is not None:
            os.dup2(saved, replaced); os.close(saved)
        if extra is not None:
            os.close(extra)
        os.close(targetfd); os.close(parentfd)
    ok = (error is None) if expected is None else (error is not None and expected in error)
    result = {'status': 'PASS' if ok else 'FAIL', 'case': case, 'expected_refusal': expected, 'error': error,
              'interpreter': sys.executable, 'version': sys.version, 'real_process_census_called': True, 'mocked_fd_or_maps': False}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not ok:
        raise RuntimeError('affected boundary failed: ' + repr(result))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); p.add_argument('--child', choices=CASES); a = p.parse_args()
    out = Path(a.output)
    if a.child:
        child(out, a.child); return
    out.mkdir(exist_ok=False)
    results = []
    for case in CASES:
        dest = out / case
        cmd = ['/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--output', str(dest), '--child', case]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        (out / (case + '.stdout')).write_bytes(proc.stdout)
        (out / (case + '.stderr')).write_bytes(proc.stderr)
        result = json.loads((dest / 'result.json').read_text()) if (dest / 'result.json').exists() else {'status': 'FAIL_NO_RESULT'}
        results.append({'case': case, 'exit_code': proc.returncode, 'result': result})
        if proc.returncode != 0 or result['status'] != 'PASS':
            (out / 'result.json').write_text(json.dumps({'status': 'FAIL_PRESERVED', 'cases': results}, indent=2) + '\n')
            raise RuntimeError('stop first affected fixture failure: ' + case)
    result = {'status': 'PASS_AFFECTED_BOUNDARIES_ONLY', 'interpreter': sys.executable, 'version': sys.version, 'cases': results,
              'replayed_unaffected_checks': False, 'full_host_root_census_tested': False}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'cases': len(results), 'version': sys.version.split()[0]}))


if __name__ == '__main__':
    main()
