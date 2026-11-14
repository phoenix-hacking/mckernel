#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute only Root's exact four mocked HOST commands, stopping on first failure.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
GRANT_SHA = '51f2a19a7432fb657c8c4bf126dc28f8e4dea11e3452b95fb45b401353d0e08a'
GUARD = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-operation-guard-source-20261028-1/guardian_guard.py'
GUARD_SHA = '48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def verify(row):
    path = Path(row['path'])
    assert path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']


def identity(pid):
    fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'birth': fields[19], 'ppid': int(fields[1]),
            'pgrp': int(fields[2]), 'session': int(fields[3]), 'state': fields[0]}


def group_members(pgrp):
    members = []
    errors = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            observed = identity(int(path.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            errors.append(str(exc))
            continue
        if observed['pgrp'] == pgrp:
            members.append(observed)
    return members, errors


grant_path = HERE / 'ROOT-ORDINARY-HOST-GRANT.json'
assert sha(grant_path) == GRANT_SHA
grant = json.loads(grant_path.read_text())
verify(grant['command_plan'])
plan = json.loads(Path(grant['command_plan']['path']).read_text())
assert len(plan['commands']) == grant['maximum_commands'] == 4
assert Path(plan['cwd']) == HERE
out = Path(grant['output'])
assert out == Path(plan['fresh_output']) and out.parent == HERE
assert not out.exists(), 'fresh output already exists; no replay'
out.mkdir()
write(out / 'RUNNER-BINDING.json', {'scope': SCOPE, 'runner': str(Path(__file__).resolve()),
                                  'runner_sha256': sha(Path(__file__)), 'grant_sha256': GRANT_SHA,
                                  'initial_output_absent': True, 'pid': os.getpid(),
                                  'birth': identity(os.getpid())['birth'],
                                  'scope_limit': 'Mocked HOST effects only; no default/native/file acceptance'})
results = []


def preflight(command):
    assert sha(grant_path) == GRANT_SHA
    for row in [grant['source_ready'], grant['command_plan'], grant['preimage_manifest']] + grant['actual_source_bindings'] + grant['actual_tools']:
        verify(row)
    pre = json.loads(Path(grant['preimage_manifest']['path']).read_text())
    checked = []
    for relative, entry in pre['snapshots'].items():
        for key in ('canonical', 'snapshot'):
            verify(entry[key])
            checked.append({'relative': relative, 'kind': key, **entry[key]})
    for row in pre['real_header_inputs']:
        verify(row)
        checked.append({'kind': 'real_header_inputs', **row})
    for row in [pre['source_adoption116'], pre['original_body'], pre['retained_object_frontier']]:
        verify(row)
    assert command['purpose'].startswith(SCOPE)
    executable = Path(command['argv'][0]).resolve()
    if executable != out / 'fixture':
        assert any(Path(row['path']).resolve() == executable for row in grant['actual_tools'])
    assert sha(GUARD) == GUARD_SHA
    spec = importlib.util.spec_from_file_location('f06_granted_readonly_guard', GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clocks = module.guard()
    assert all(actual < cutoff for actual, cutoff in zip(clocks, grant['actual_cutoffs']))
    state = json.loads((ROOT / '.git/os-autopilot/state.json').read_text())
    credit = state['credit_budget']
    return {'scope': SCOPE, 'status': 'PASS', 'guard_sha256': GUARD_SHA,
            'clocks_epoch_MONO_BOOT': clocks, 'actual_cutoffs': grant['actual_cutoffs'],
            'credit': {key: credit[key] for key in ('id', 'budget', 'spent', 'remaining')},
            'all_actual_source_bindings_verified': True, 'all_actual_tools_verified': True,
            'actual_preimages_and_header_inputs_verified': checked}


for index, command in enumerate(plan['commands']):
    prefix = out / ('command' + str(index))
    try:
        checked = preflight(command)
        write(prefix.with_suffix('.PREFLIGHT.json'), checked)
    except Exception as exc:
        result = {'scope': SCOPE, 'command': index, 'status': 'REFUSED_BEFORE_COMMAND',
                  'error': repr(exc), 'argv': command['argv'], 'cwd': str(HERE),
                  'compiler_started': False, 'no_retry': True}
        write(prefix.with_suffix('.REFUSED.json'), result)
        results.append(result)
        print(json.dumps(result), flush=True)
        break
    stdout_path = prefix.with_suffix('.stdout')
    stderr_path = prefix.with_suffix('.stderr')
    started_path = prefix.with_suffix('.STARTED.json')
    argv = command['argv']

    def child_setup():
        os.sched_setaffinity(0, {grant['cpu']})
        resource.setrlimit(resource.RLIMIT_AS, (grant['AS_bytes'], grant['AS_bytes']))
        resource.setrlimit(resource.RLIMIT_CPU, (grant['CPU_seconds'], grant['CPU_seconds']))
        started = {'scope': SCOPE, 'purpose': command['purpose'], 'argv': argv, 'cwd': str(HERE),
                   'identity': identity(os.getpid()), 'affinity': sorted(os.sched_getaffinity(0)),
                   'AS_limit': list(resource.getrlimit(resource.RLIMIT_AS)),
                   'CPU_limit': list(resource.getrlimit(resource.RLIMIT_CPU)),
                   'epoch': time.time(), 'monotonic': time.monotonic(),
                   'boot': time.clock_gettime(time.CLOCK_BOOTTIME)}
        write(started_path, started)

    start = time.monotonic()
    waited = None
    process = None
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        try:
            process = subprocess.Popen(argv, cwd=str(HERE), stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True,
                                       preexec_fn=child_setup, close_fds=True)
            while time.monotonic() - start < grant['wall_seconds']:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid == process.pid:
                    waited = (pid, status, usage)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(0.025)
        except Exception as exc:
            result = {'scope': SCOPE, 'command': index, 'status': 'EXECUTOR_FAILURE_RETAINED',
                      'error': repr(exc), 'pid': process.pid if process is not None else None,
                      'argv': argv, 'no_retry': True}
            write(prefix.with_suffix('.FAILURE.json'), result)
            results.append(result)
            print(json.dumps(result), flush=True)
            break
    wall = time.monotonic() - start
    started = json.loads(started_path.read_text())
    members, scan_errors = group_members(started['identity']['pgrp'])
    if waited is None:
        result = {'scope': SCOPE, 'command': index, 'status': 'WALL_TIMEOUT_OWNERSHIP_RETAINED',
                  'identity': started['identity'], 'wall_seconds': wall, 'group_members': members,
                  'group_scan_errors': scan_errors, 'parent_streams_closed': True,
                  'child_streams_uncertain': True, 'no_signal_or_retry': True,
                  'argv': argv, 'cwd': str(HERE)}
        write(prefix.with_suffix('.TIMEOUT.json'), result)
        results.append(result)
        print(json.dumps(result), flush=True)
        break
    pid, status, usage = waited
    result = {'scope': SCOPE, 'command': index, 'status': 'PASS' if process.returncode == 0 and not members and not scan_errors else 'FIRST_FAILURE_RETAINED',
              'argv': argv, 'cwd': str(HERE), 'identity': started['identity'],
              'wait4': {'pid': pid, 'status': status, 'exit': process.returncode,
                        'positive_direct_join': pid == process.pid},
              'wall_seconds': wall, 'CPU_user_seconds': usage.ru_utime,
              'CPU_system_seconds': usage.ru_stime,
              'CPU_seconds': usage.ru_utime + usage.ru_stime, 'peak_RSS_KiB': usage.ru_maxrss,
              'group_members': members, 'group_scan_errors': scan_errors,
              'group_absent': not members and not scan_errors,
              'parent_streams_closed': stdout.closed and stderr.closed,
              'child_streams_closed_by_whole_group_absence': not members and not scan_errors,
              'stdout_sha256': sha(stdout_path), 'stderr_sha256': sha(stderr_path)}
    write(prefix.with_suffix('.JOINED.json'), result)
    results.append(result)
    print(json.dumps({k: result[k] for k in ('command', 'status', 'wait4', 'wall_seconds', 'CPU_seconds', 'peak_RSS_KiB', 'group_absent')}), flush=True)
    if result['status'] != 'PASS':
        break

summary = {'scope': SCOPE, 'status': 'FOUR_HOST_COMMANDS_PASS' if len(results) == 4 and all(r['status'] == 'PASS' for r in results) else 'STOPPED_FIRST_FAILURE_OR_REFUSAL_RETAINED',
           'commands': results, 'actual_commands_started': sum((out / ('command' + str(i) + '.STARTED.json')).exists() for i in range(4)),
           'grant_sha256': GRANT_SHA, 'compiler_or_fixture_retries': 0,
           'default_artifact_credit': 0, 'native_credit': 0, 'file_closure_credit': 0}
write(out / 'RESULTS.json', summary)
print(json.dumps({'status': summary['status'], 'actual_commands_started': summary['actual_commands_started']}), flush=True)
sys.exit(0 if summary['status'] == 'FOUR_HOST_COMMANDS_PASS' else 1)
