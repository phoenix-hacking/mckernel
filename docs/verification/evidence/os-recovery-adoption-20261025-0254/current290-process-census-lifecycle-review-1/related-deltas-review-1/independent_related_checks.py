"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure virtual-module and proc-model source checks, without root/runtime queries.
"""
import ast
import copy
import errno
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from unittest import mock

E = Path(__file__).resolve().parents[2]
BRIDGE = E / 'current290-process-census-lifecycle-correction-source-1/census-runtime-bridge-source-1'
DEAD = E / 'current290-dead-caller-proc-snapshot-lifecycle-source-1'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def genuine_old(bridge):
    ref = bridge.FROZEN_INPUTS['baseline']
    module = types.ModuleType('independent_virtual_e49')
    module.__file__ = ref['path']
    exec(compile(bridge.authenticated(ref), ref['path'], 'exec'), module.__dict__)
    release = json.loads(bridge.authenticated(bridge.FROZEN_INPUTS['old_release']))
    module.RELEASE = release
    module.BOOT_ID = release['observation']['boot_id']
    module.OWNER_PID = release['observation']['target']['owner_pid']
    module.WAITER_PIDS = tuple(row['pid'] for row in release['observation']['client_ledger'])
    return module


def bridge_checks():
    bridge = load_module('independent_related_bridge', BRIDGE / 'census_runtime_bridge.py')
    checks = []
    module = genuine_old(bridge)
    before = dict(module.__dict__)
    plan = module.PLAN if 'PLAN' in module.__dict__ else None
    manifest = bridge.install_census_delta(module, bridge.expected_authorization())
    for name, value in before.items():
        if name not in bridge.SLOTS:
            assert module.__dict__[name] is value, name
    assert set(module.__dict__) - set(before) == {bridge.MANIFEST_SLOT}
    assert manifest['proc_code_sha256'] == '0e6da43702e25f72741eddc4ae28cd245d474cb597c16ff19c79da86865a4302'
    checks.append('exact genuine e49 namespace preserved except three slots and manifest')

    # Execute the actual retained process_absent -> run_privileged -> corrected
    # root_command -> corrected validate_process_report path, with all IO mocked.
    class SelfStat:
        def __init__(self, path):
            assert path == '/proc/self/stat'
        def read_bytes(self):
            fields = [b'S'] + [b'0'] * 49
            fields[19] = b'555'
            return b'888 (fixture) ' + b' '.join(fields)
    calls = []
    def child(args, **kwargs):
        calls.append((args, kwargs))
        assert args[:4] == ['/usr/bin/python3', '-I', '-B', '-c']
        assert args[4] == module.PROC_CODE
        assert args[-2:] == ['888', '555']
        report = dict(schema='fp-save-image.proc.lifecycle.v2', uid=0,
                      boot_id=module.BOOT_ID, challenge=args[5], caller=[888, '555'],
                      publishers=[], snapshots=[[[1, 0, '1'], [888, 1, '555']]] * 2,
                      attempts=1, retry_failures=[])
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(report).encode(), stderr=b'')
    with mock.patch.object(module, 'Path', SelfStat), mock.patch.object(module.os, 'getpid', return_value=888), mock.patch.object(module.os, 'geteuid', return_value=0), mock.patch.object(module.subprocess, 'run', side_effect=child):
        module.process_absent()
    assert len(calls) == 1 and calls[0][1]['timeout'] == 30
    checks.append('genuine old consumer routes isolated argv through corrected root_command and v2 validator')

    # A post-install manifest construction failure must restore old function and
    # constant identities. This exercises the rollback branch independently.
    module = genuine_old(bridge)
    before = dict(module.__dict__)
    fingerprint = bridge.function_fingerprint
    def fail_corrected(function):
        if function.__code__.co_filename == bridge.FROZEN_INPUTS['corrected']['path']:
            raise RuntimeError('independent manifest fixture failure')
        return fingerprint(function)
    with mock.patch.object(bridge, 'function_fingerprint', side_effect=fail_corrected):
        try:
            bridge.install_census_delta(module, bridge.expected_authorization())
        except RuntimeError as error:
            assert str(error) == 'independent manifest fixture failure'
        else:
            raise AssertionError('expected rollback fixture failure')
    assert set(module.__dict__) == set(before)
    assert all(module.__dict__[name] is value for name, value in before.items())
    checks.append('post-install manifest error rolls back every changed slot')

    module = genuine_old(bridge)
    template = json.loads((BRIDGE / 'NEW-DIAGNOSTIC-AUTHORIZATION.TEMPLATE.NOT-GRANTED.json').read_text())
    try:
        bridge.install_census_delta(module, template)
    except bridge.BridgeRefusal as error:
        assert str(error) == 'distinct-exact-new-authorization-required'
    else:
        raise AssertionError('NOT_GRANTED template accepted')
    checks.append('actual NOT_GRANTED template refuses installation')

    module = genuine_old(bridge)
    bridge.install_census_delta(module, bridge.expected_authorization())
    stderr = b'e' * 5000
    stdout = b'private fixture output'
    response = types.SimpleNamespace(returncode=3, stdout=stdout, stderr=stderr)
    with mock.patch.object(module.os, 'geteuid', return_value=0), mock.patch.object(module.subprocess, 'run', return_value=response):
        try:
            module.root_command(['/usr/bin/python3'], 1048576)
        except module.Refusal as error:
            text = str(error)
            context = json.loads(text.split(':/usr/bin/python3:', 1)[1])
        else:
            raise AssertionError('failed child accepted')
    assert context['stderr_prefix_bytes'] == 4096 and not context['stderr_complete']
    assert len(bytes.fromhex(context['stderr_prefix_hex'])) == 4096
    assert context['stderr_bytes'] == 5000 and context['stderr_sha256'] == hashlib.sha256(stderr).hexdigest()
    assert stdout.decode() not in text and context['returncode'] == 3
    checks.append('bridged child failure retains exact hashes and bounded4096B stderr prefix')
    return checks


def dead_counterexamples():
    # Load fixture declarations without running unittest or any live controller.
    path = DEAD / 'test_dead_caller_snapshot_lifecycle.PURE.py'
    scope = {'__name__': 'independent_dead_fixture_declarations', '__file__': str(path)}
    exec(compile(path.read_bytes(), str(path), 'exec'), scope)
    results = []
    for malformed in ('nonnumeric-birth', 'negative-pgrp'):
        namespace = scope['load'](True)
        state = {'snapshot': 0, 'target_reads': 0}
        class MemoryPath(scope['ProcPath']):
            def __truediv__(self, part):
                return MemoryPath(self.path + '/' + part)
            def iterdir(self):
                state['snapshot'] += 1
                pids = [1, 77, 88] if state['snapshot'] == 1 else [1, 88]
                return [MemoryPath('/proc/' + str(pid)) for pid in pids]
        namespace['Path'] = MemoryPath
        def read(path, limit):
            pid = int(path.split('/')[2])
            if path.endswith('/cmdline'):
                return b'/usr/bin/python3\0'
            if pid == 77:
                state['target_reads'] += 1
                if state['target_reads'] == 2:
                    raise FileNotFoundError(errno.ENOENT, 'ordinary exit fixture', path)
                if malformed == 'nonnumeric-birth':
                    return scope['stat'](77, birth='not-a-number')
                return scope['stat'](77, pgrp=-1)
            return scope['stat'](pid, birth='555' if pid == 88 else '123')
        namespace['same_ofd_read'] = read
        namespace['dead_caller_absent']()
        observations = namespace['DEAD_CALLER_OBSERVATIONS']
        assert state['snapshot'] == 3
        assert [row['status'] for row in observations] == ['REFUSED', 'PASS_FULL_EOF_RECHECK']
        failed = observations[0]['raw_full_eof_snapshots'][0][-1]
        assert failed['pid'] == 77 and failed['stat_after_error']['errno'] == 2
        for rows in observations[1]['raw_full_eof_snapshots']:
            assert {row['pid'] for row in rows} == {1, 88}
        results.append({'case': malformed, 'frozen_candidate_behavior': 'ACCEPTS_AFTER_RETRY',
                        'required_behavior': 'HARD_REFUSAL_BEFORE_RETRY',
                        'snapshot_enumerations': state['snapshot'],
                        'statuses': [row['status'] for row in observations],
                        'failed_stat_hex': failed['stat_hex']})
    return results


if __name__ == '__main__':
    print(json.dumps({'scope': __doc__.splitlines()[0], 'bridge': {'decision': 'PASS_SOURCE_COMPATIBILITY_ONLY', 'checks': bridge_checks()},
                      'dead_guard': {'decision': 'CHANGES_REQUIRED', 'counterexamples': dead_counterexamples()}}, sort_keys=True))
