"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Read one protocol-passed, joined native attempt and observe current availability.
No cleanup, signal, container mutation or old execution replay.
"""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import subprocess
import time
import types

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
CID = 'fe99b8b17da7e8949b0d3beecc1b0dfde9c5996b864503e2ffb894db6e994301'
NONCE = '108cd725fce84fe769c9ff99e5f97562'


def read(path):
    return json.loads(path.read_text())


def observe():
    assert os.getuid() == os.geteuid() == 1000 and time.time() < 1793100290
    source = EVIDENCE / 'current290-build3-postjoin-current-physical-1/check_current.py'
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '3cefea1bf7e5dc6ab95b4498137622cc0b0a46df2e98c724988171cd831d756b'
    helper = types.ModuleType('accepted_readonly_helpers')
    helper.__file__ = str(source)
    exec(compile(raw, str(source), 'exec'), helper.__dict__)
    original = HERE / 'OWNER-RAW'
    exported = read(HERE / 'OWNER-RAW-EXPORT.json')
    for row in exported['rows']:
        data = (original / row['relative']).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    result = read(original / 'result.json')
    assert result['status'] == 'PROTOCOL_PASS' and result['application_acceptance'] is False
    assert result['absence_verified'] is True and result['lease_retained'] is False and result['container'] == CID
    joined = read(HERE / 'CAPTURE/JOINED.json')
    assert joined['joined'] is True and joined['returncode'] == 0
    owner = read(original / 'owner.json')
    assert owner['nonce'] == NONCE and owner['name'] == 'mckernel-native-diagnostic-' + NONCE
    actors = {joined['caller_pid']: int(joined['caller_starttime']),
              owner['outer']['pid']: owner['outer']['proc_starttime']}
    groups = {owner['outer']['pgid']}
    commands = []
    for path in sorted(original.glob('[0-9][0-9][0-9]-*.json')):
        command = read(path)
        if 'command' in command:
            child = command['command']
            assert child['reaped'] is True and child['returncode'] == command['returncode']
            actors[child['pid']] = child['proc_starttime']
            groups.add(child['pgid'])
            commands.append({'path': str(path), 'command': child})
    assert len(commands) == 30
    absent = sorted(set(actors) | groups)
    assert all(not Path('/proc', str(pid)).exists() for pid in absent), 'known numeric actor/group leader present'
    # A departed leader does not prove its process group empty. Observe every
    # current numeric entry; ordinary unrelated exits are retained explicitly.
    proc_entries = sorted(int(path.name) for path in Path('/proc').iterdir() if path.name.isdecimal())
    assert len(proc_entries) <= 10000, 'bounded process observation exceeded'
    census = {'rows': [], 'confirmed_exits': [], 'errors': []}
    for pid in proc_entries:
        path = Path('/proc', str(pid), 'stat')
        try:
            with path.open() as stream:
                raw_stat = stream.read(4097)
            assert len(raw_stat) <= 4096 and raw_stat.endswith('\n'), 'bounded full stat record'
            close = raw_stat.rfind(')')
            fields = raw_stat[close + 2:].split()
            assert close > 0 and len(fields) >= 20 and int(raw_stat.split('(', 1)[0]) == pid
            group = int(fields[2])
            census['rows'].append({'pid': pid, 'pgrp': group, 'raw_stat': raw_stat})
        except FileNotFoundError as error:
            # No target/reused numeric actor may become an exit tombstone.
            if pid in absent or path.parent.exists():
                census['errors'].append({'pid': pid, 'error': repr(error), 'unresolved': True})
            else:
                census['confirmed_exits'].append({'pid': pid, 'error': repr(error),
                                                  'directory_confirmed_absent': True})
        except (OSError, ValueError, AssertionError) as error:
            census['errors'].append({'pid': pid, 'error': repr(error), 'unresolved': True})
    assert not census['errors'], json.dumps(census)
    assert not any(row['pgrp'] in groups for row in census['rows']), json.dumps(census)
    assert not helper.lock_rows()
    probes = []
    for _ in range(2):
        assert helper.mutex_metadata(helper.MUTEX.lstat())
        descriptor = os.open(helper.MUTEX, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            assert helper.mutex_metadata(os.fstat(descriptor))
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = helper.lock_rows()
            assert len(rows) == 1 and str(os.getpid()) in rows[0].split()
            assert helper.mutex_metadata(helper.MUTEX.lstat()) and helper.mutex_metadata(os.fstat(descriptor))
            probes.extend(rows)
        finally:
            os.close(descriptor)
        assert not helper.lock_rows() and helper.mutex_metadata(helper.MUTEX.lstat())
    prefix = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock']
    observations = []
    for arguments in [['ps', '-aq', '--no-trunc'],
                      ['ps', '-aq', '--no-trunc', '--filter', 'name=^/mckernel-native-diagnostic-' + NONCE + '$'],
                      ['ps', '-aq', '--no-trunc', '--filter', 'label=mckernel.native-diagnostic.owner=' + NONCE]]:
        completed = subprocess.run(prefix + arguments, capture_output=True, text=True, timeout=15)
        assert completed.returncode == 0 and not completed.stderr and CID not in completed.stdout.splitlines()
        if '--filter' in arguments:
            assert not completed.stdout
        observations.append({'argv': prefix + arguments, 'returncode': completed.returncode,
                             'stdout': completed.stdout, 'stderr': completed.stderr})
    plan = read(Path('/home/holden/mckernel-work/scratch/m14-current290-owner213-rolejoin-pathfix-retirement-20261026-1.plan.json'))
    assert all(not os.path.lexists(row[0]) for row in plan['records'])
    mount = subprocess.run(['/usr/bin/findmnt', '-J', '-T', '/home/holden/mckernel-work/scratch',
                            '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], capture_output=True, text=True, timeout=10)
    expected = read(EVIDENCE / 'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json')['mount']
    assert mount.returncode == 0 and not mount.stderr and json.loads(mount.stdout)['filesystems'] == [expected]
    capacity = {path: os.statvfs(path).f_bavail * os.statvfs(path).f_frsize
                for path in ['/home/holden/mckernel', '/home/holden/mckernel-work/scratch']}
    assert capacity['/home/holden/mckernel'] >= 16 * 2**30
    assert capacity['/home/holden/mckernel-work/scratch'] >= 12 * 2**30 + 603979776
    assert os.stat('/home/holden/mckernel-work/scratch').st_dev == 1828
    return {'status': 'PASS_FILES1_POSTJOIN_CURRENT_OBSERVATION_PENDING_INDEPENDENT_ACCEPTANCE',
            'scope': __doc__.splitlines()[0], 'observed_at': time.time(), 'native_acceptance': False,
            'actual_protocol_result': result, 'exact_container_absent': CID,
            'known_actor_births_absent': actors, 'known_numeric_controls_absent': absent,
            'group_membership_observation': census,
            'commands_actual_reaped': commands, 'closed_exclusive_probes': probes,
            'docker_observations': observations, 'mount': json.loads(mount.stdout),
            'capacity': capacity, 'meminfo': Path('/proc/meminfo').read_text()}


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
