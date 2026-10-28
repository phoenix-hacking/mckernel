"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Byte-bound static execution review only: never import a reviewed module or run a guard.
"""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path('/home/holden/mckernel')
E = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254'
D = E / 'bfd-default-control-routing-restart-20261028-1'
OWN = E / 'restart-adoption-20261028T1911/BFD-FINITE-REVIEW-1'


def ref(path):
    path = Path(path)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                  after.st_mtime_ns, after.st_ctime_ns)
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def authenticated(row):
    assert set(row) == {'path', 'bytes', 'sha256'} and ref(row['path']) == row
    return Path(row['path'])


def checked(row):
    return json.loads(authenticated(row).read_bytes())


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    b = load(D / 'entry/ENTRY-BINDINGS.json')
    refs = b['static_refs']
    assert len(refs) == 28
    for row in refs.values():
        authenticated(row)
    for key in ['contract', 'guard_facade', 'guard_configuration', 'observer_source',
                'observer_schema', 'observer_schema_review', 'finite_verifier',
                'capture_source', 'publisher_source']:
        authenticated(b[key])
    assert b['reviewer'] == '/root/observerreview'
    assert b['Root_must_not_execute_approver'] is True
    assert b['Root_capture_owner'] == '/root'
    assert b['nonce'] == 'faac1b4804174de5800c58d61ba98004'
    limits = [1793253600.0, 1035704.5689393478, 1051042.6959879305]
    assert b['authorized_cutoffs'] == limits
    profile = checked(refs['profile'])
    request = checked(refs['request_payload'])
    contract = checked(b['contract'])
    assert profile['fixed_three_clock_cutoffs'] == contract['limits'] == limits
    assert profile['CPU'] == '2-5' and profile['memory_bytes'] == 12 << 30
    assert profile['pids'] == 512 and profile['maximum_wall_seconds'] == 19800
    assert profile['exact_commands'] == request['commands']
    assert len(request['commands']) == 3
    assert request['commands'][1]['argv'] == [
        '/usr/bin/cmake', '--build', '/work/current-bfd-build', '--target',
        'mcinspect', 'eclair', '--parallel', '1']
    assert profile['actual_nonce'] is None and profile['runtime_authority'] is None
    assert not os.path.lexists(profile['actual_output_root'])
    ledger = checked(contract['Root61_observer_fragment']['current_ledger'])
    assert len(ledger['consumed_nonces']) == 70 and b['nonce'] not in ledger['consumed_nonces']
    reservation = load(E / 'restart-adoption-20261028T1911/BFD-FINAL-INTEGRATION-1/ROOT-NONCE-RESERVATION.json')
    assert reservation['nonce'] == b['nonce'] and reservation['ledger_consumed_by_this_reservation'] is False
    assert reservation['actual_output_root'] == profile['actual_output_root']
    assert reservation['decision'] == 'RESERVED_UNUSED_SOURCE_PREPARATION_ONLY'
    A = Path(b['admission'])
    absent = [A / n for n in ['OUTPUT', 'ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json',
        'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json', 'HOLDER', 'ROOT-PREHOLDER-PHYSICAL-1.json',
        'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json', 'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json']]
    for path in absent:
        assert not os.path.lexists(path), 'Existing runtime namespace: ' + str(path)
    bootstrap = load(A / 'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
    assert bootstrap['author'] == '/root' and bootstrap['maximum_invocations'] == 1
    assert bootstrap['nonce'] == b['nonce'] and bootstrap['permanent_mutex_path'] == '/run/lock/mckernel-development.lock'
    assert bootstrap['runtime_authority'] is None
    for key, name in [('source', 'holder_source'), ('runner', 'runner'), ('worker', 'worker'), ('profile', 'profile')]:
        assert bootstrap[key] == refs[name]
    facade = checked(b['guard_configuration'])
    op = checked(facade['operation_bindings'])
    successor = checked(op['successor'])
    operation_review = checked(op['independent_review'])
    assert operation_review['independent'] is True and operation_review['successor'] == successor
    assert successor['subjects'] == op['expected_subjects'] and len(successor['subjects']) == 12
    for row in successor['subjects'].values():
        authenticated(row)
    assert successor['operation_cutoffs'] == limits
    assert successor['credit_run_id'] == '7f4af94a83b14cc08f97401f5891d965'
    assert successor['credit_ceiling'] == '57774.852125'
    assert successor['minimum_cumulative_spent'] == '22812.3311'
    receipt = checked(successor['actual_control_receipt'])
    assert '01a183ec-72e5-7400-8f48-b4efb8725520' in json.dumps(receipt)
    for key in ['common_dependency_review', 'physical_configuration_review', 'top_dependency_review', 'observer_schema_review']:
        review = checked(refs[key])
        assert review['independent'] is True and review['decision'].startswith('PASS')
    commands = load(D / 'ROOT-EXACT-COMMANDS.NOT-AUTHORITY.json')
    assert len(commands['commands']) == 8
    assert commands['commands'][2]['owner'] == '/root/observerreview'
    assert all(x['owner'] == '/root' for i, x in enumerate(commands['commands']) if i != 2)
    assert commands['runtime_authority'] is None
    result = dict(scope=__doc__.splitlines()[0], decision='PASS_STATIC_EXECUTION_DESIGN_ONLY',
        reviewer='/root/observerreview', implementation_ownership=False,
        entry_bindings=ref(D/'entry/ENTRY-BINDINGS.json'), static_refs=refs,
        exact_commands=ref(D/'ROOT-EXACT-COMMANDS.NOT-AUTHORITY.json'),
        holder_bootstrap=ref(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json'),
        operation_binding=facade['operation_bindings'], actual_control_receipt=successor['actual_control_receipt'],
        reserved_nonce=reservation['nonce'], output_absent=True,
        runtime_namespaces_absent=[str(x) for x in absent],
        source_publication=b['source_publication'], sealed_exists=(D/'entry/SEALED-ENTRY-BINDINGS.json').exists(),
        runtime_authority=None, guard_calls=0, physical_captures=0, holders=0,
        producers=0, default_artifacts=0, native_cases=0,
        remaining=['Exact fetched source/config publication authenticated independently',
                   'Root sealing binding the same 28 static refs and publication',
                   'Fresh operation/account/identity guard and finite PREWARM release',
                   'Fresh positively joined physical and held resource captures',
                   'Actual independent Hot PASS and postfsync READY before one producer'])
    with (OWN/'STATIC-CHECK.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(decision=result['decision'], static_refs=len(refs), runtime_authority=None)))


if __name__ == '__main__':
    main()
