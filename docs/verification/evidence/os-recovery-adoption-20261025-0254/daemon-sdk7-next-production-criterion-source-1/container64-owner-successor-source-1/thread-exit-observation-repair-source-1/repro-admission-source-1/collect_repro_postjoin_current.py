"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read the completed exact probe and reuse the accepted current physical observer.
No workload, cleanup, release, source mutation or automatic retry occurs.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import time

D = Path(__file__).resolve().parent
NONCE = '7cf529a05d0430c6651f07b63168e8e1'
E = D.parents[3]
OBSERVER = E / 'ROOT-F03-F06-RUSTMM-STRICT235-NATIVE-ADMISSION-1/check_postnative_current.py'


def read(path):
    return json.loads(path.read_text())


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert os.getuid() == os.geteuid() == 1000
    assert time.time() < 1793100290
    assert reference(OBSERVER)['sha256'] == '9891cf1816c8639a8ca4a55e8ace130c049bd5ef65f1e126ef347353904be6fc'
    whole = read(D / 'OWNER-WHOLE-JOIN.json')
    terminal = read(D / 'ROOT-ACTUAL-PARENT-TOOL92106-TERMINAL.json')
    assert terminal['exit_code'] == 0 and terminal['positive_tool_join'] is True
    assert all(whole[k] is True for k in ['direct_child_joined', 'group_absent', 'closed_streams'])
    assert whole['returncode'] == 0 and whole['error'] is None and whole['retirement_error'] is None
    receipt_path = D / f'workspace/native-running-modules-owner-{NONCE}/owner-receipt.json'
    receipt = read(receipt_path)
    assert receipt['owner_nonce'] == NONCE and receipt['status'] == 'PASS'
    assert receipt['wait_exit_code'] == 0 and receipt['retired'] is True
    assert receipt['cleanup_status'] == 'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE'
    assert receipt['cleanup_separately_required'] is False
    actors = {whole['pid']: whole['start']}
    for key in ['client_group_checks', 'admission_client_group_checks']:
        for row in receipt[key]:
            assert row['empty'] is True and not row['surviving_members']
            status = read(Path(row['status_path']))
            assert status['pid'] == row['pid'] and status['state'] == 'exited' and status['exit_code'] == 0
            actors[row['pid']] = None  # Status records do not contain client birth ticks.
    assert len(actors) == 16
    assert all(not Path('/proc', str(pid)).exists() for pid in actors)
    spec = importlib.util.spec_from_file_location('accepted_current_observer', OBSERVER)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    physical = observer.observe()
    census = physical['group_membership_observation']
    assert not census['errors']
    assert not any(row['pid'] in actors or row['pgrp'] in actors for row in census['rows'])
    prefix = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock']
    queries = []
    for flags in [[], ['--filter', 'id=' + receipt['container_id']],
                  ['--filter', 'name=^/' + receipt['container_name'] + '$'],
                  ['--filter', 'label=mckernel.owner=' + NONCE]]:
        argv = prefix + ['ps'] + ([] if not flags else ['--all']) + ['--quiet', '--no-trunc'] + flags
        result = subprocess.run(argv, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0 and not result.stdout.strip() and not result.stderr
        queries.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    records = [Path('/home/holden/mckernel-work/scratch') / name for name in
               ['native-running-external-modules.lease.json', 'native-running-external-modules-operational-exclusion.json', 'mckernel-heavy-operation.lock']]
    assert all(not os.path.lexists(path) for path in records)
    output = dict(scope=__doc__.splitlines()[0], observed_at=time.time(),
                  nonce=NONCE, status='PASS_REPRO_COMPLETED_CURRENT_PHYSICAL_PENDING_INDEPENDENT_ACCEPTANCE',
                  whole_join=reference(D / 'OWNER-WHOLE-JOIN.json'), parent_tool_join=reference(D / 'ROOT-ACTUAL-PARENT-TOOL92106-TERMINAL.json'),
                  owner_receipt=reference(receipt_path), known_numeric_actors_absent=actors,
                  client_birth_ticks_not_recorded=True, outer_caller_numeric_identity_not_recorded=True,
                  current_physical=physical, fresh_container_queries=queries,
                  owned_records_absent=[str(path) for path in records],
                  daemon_acceptance=False, historical_extra_tid=None, runtime_authority=None)
    path = D / 'POSTREPRO-CURRENT.json'
    with path.open('x') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps(reference(path)))


if __name__ == '__main__':
    main()
