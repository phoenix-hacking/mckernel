#!/usr/bin/env python3
"""Recheck retained Ultra inputs without granting new runtime acceptance.

Run in the pinned native container. Only the fresh attempt directory is written;
formatting replays operate on copies, never on repository/compiler inputs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def identity(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            digest.update(chunk)
    return {'path': str(path), 'size': size, 'sha256': digest.hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=Path, required=True)
    args = parser.parse_args()
    require(os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5},
            'use the established native container')
    require(args.attempt.is_absolute() and args.attempt.parent.resolve() == Path('/work'),
            'attempt must be a fresh direct child of /work')
    args.attempt.mkdir(mode=0o700)
    out = args.attempt
    report = {'schema_version': 1, 'status': 'RUNNING', 'checked': [],
              'format_replays': [], 'started_utc': datetime.now(timezone.utc).isoformat(),
              'new_runtime_acceptance': False, 'production_gate_credit': False}
    repo = Path('/workspace')

    def check(row, path=None, expected_hash=None):
        path = path or Path(row['path'])
        got = identity(path)
        require(got['sha256'] == (expected_hash or row['sha256']),
                'SHA256 mismatch: ' + str(path))
        if expected_hash is None:
            require(got['size'] == row['size'], 'size mismatch: ' + str(path))
        report['checked'].append(got)
        return got

    try:
        shutil.copyfile(__file__, out / 'helper.py')
        report['helper'] = identity(out / 'helper.py')
        inputs_path = repo / 'docs/verification/ultra-draft-inputs-20260909.json'
        inputs = json.loads(inputs_path.read_text())
        report['input_manifest'] = identity(inputs_path)
        checkpoint_path = repo / inputs['final_checkpoint']['path']
        check(inputs['final_checkpoint'], checkpoint_path)
        checkpoint = json.loads(checkpoint_path.read_text())
        require(checkpoint['status'] == 'PASS', 'retained checkpoint is not PASS')
        report['source_commit'] = subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, timeout=15).strip()
        report['source_status'] = subprocess.check_output(
            ['git', '-C', str(repo), 'status', '--porcelain'], text=True, timeout=15)
        report['formatter'] = subprocess.check_output(
            ['rustfmt', '--version'], text=True, timeout=15)
        require(report['formatter'] == checkpoint['formatter'], 'pinned formatter changed')
        pair = inputs['selected_pair']
        for name in ('core', 'launcher', 'linux_kernel', 'mckernel_image',
                     'module_record', 'image_record'):
            check(pair[name])
        for row in pair['modules']:
            check(row)
        modules = json.loads(Path(pair['module_record']['path']).read_text())
        images = json.loads(Path(pair['image_record']['path']).read_text())
        require(modules['status'] == images['status'] == 'PASS', 'build record is not PASS')
        for row in modules['outputs']:
            check(row)
        require({row['kind'] for row in images['images']} == set(pair['image_profiles']),
                'image profiles differ')
        for profile in images['images']:
            for row in profile['outputs']:
                check(row)
        for group, expected in [('native_compiler_bindings', 57),
                                ('guest_production_bindings', 44)]:
            bindings = checkpoint[group]
            require(len(bindings) == expected and len({r['path'] for r in bindings}) == expected,
                    'compiler binding inventory differs: ' + group)
            for row in bindings:
                original = repo / row['path']
                check(row, original)
                capture = Path(row['compiler_capture'])
                if 'formatted_sha256' in row:
                    copied = out / ('format-' + original.name)
                    shutil.copyfile(original, copied)
                    command = row['replay_command'][:-1] + [str(copied)]
                    result = subprocess.run(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, timeout=120)
                    (out / (copied.name + '.stdout')).write_bytes(result.stdout)
                    (out / (copied.name + '.stderr')).write_bytes(result.stderr)
                    report['format_replays'].append({'command_argv': command,
                                                    'returncode': result.returncode})
                    require(result.returncode == 0, 'formatter failed: ' + str(original))
                    check(row, copied, row['formatted_sha256'])
                    check(row, capture, row['formatted_sha256'])
                else:
                    check(row, capture)
            report[group + '_count'] = expected
        needed_helpers = {
            '/work/run-native-ultra-baseline.py',
            '/work/run-native-ultra-control-regression.py',
            '/work/run-native-ultra-control-compat.py',
            '/work/run-native-ultra-futex.py',
            '/work/run-native-ultra-signal-abi.py',
            '/work/prepare-native-ultra-transport-fault.py',
            '/work/build-native-ultra-transport-fault.py',
        }
        checked_helpers = set()
        for row in checkpoint['helper_and_plan_bindings']:
            if row['current']['path'] in needed_helpers:
                check(row['current'])
                check(row['retained'])
                checked_helpers.add(row['current']['path'])
        require(checked_helpers == needed_helpers, 'missing retained helper binding')
        report['status'] = 'INPUTS_MATCH'
    except BaseException as exc:
        report.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (out / 'record.json').open('x') as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        print(report['status'], out, 'checked=' + str(len(report['checked'])), flush=True)


if __name__ == '__main__':
    main()
