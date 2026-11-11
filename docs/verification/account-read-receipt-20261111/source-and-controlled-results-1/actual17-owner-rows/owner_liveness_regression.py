"""Changed9032 consumer branch only; no RPC/Campaign/observe/old18 execution.

The matched account snapshot below is literal private test data. It is never an
actual account receipt, issuance input, goal/budget or current-owner assertion.
"""
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SDK_SOURCE = Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/account-read-receipt-source-sdk-max-1/candidate/scripts/run_os_goal.py')
SDK_SHA = '39a03dd8bb33ea943cad02897dee9b6b113187eee30d33ed22a89886b944d870'
CONSUMER = Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/account-read-receipt-consumer-root-1/owner-liveness-correction-1/current_account_snapshot.py')
CONSUMER_SHA = '9032c50ef25ba72e7c04a06727a5b917a3823b748c63e9cdaef7c663e0d9ad85'
OLD_FIXTURE = Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/account-read-receipt-tests-p03-max-1/consumer-binding-1/test_account_read_receipts.py')
OLD_FIXTURE_SHA = '4597898c22835a6fcf291e207aaedeb613d3fd6773dca1f70085af27451cce4d'


class HarnessError(RuntimeError):
    pass


def load(name, path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise HarnessError('Wrong pinned source: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class OwnerLiveness(unittest.TestCase):
    observations = []

    def test_only_changed_owner_state_branch(self):
        # Reuse qualified Clock/limits data helpers only. Do not call any prior
        # TestCase, consumer_fixture, Campaign, RPC or CreditBudget.observe.
        old = load('qualified_receipt_fixture_data_only', OLD_FIXTURE, OLD_FIXTURE_SHA)
        clock = old.Clock()
        rows = json.loads((HERE / 'EXPECTED-OWNER-STATES.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='owner-liveness-only-') as temporary, ExitStack() as stack:
            repo = Path(temporary)
            scripts = repo / 'scripts'
            scripts.mkdir()
            (scripts / 'run_os_goal.py').write_bytes(SDK_SOURCE.read_bytes())
            consumer = load('actual_owner_liveness_consumer', CONSUMER, CONSUMER_SHA)
            consumer.REPO = repo  # Same qualified private normal-import layout.
            previous = sys.modules.pop('run_os_goal', None)
            previous_path = list(sys.path)
            def restore():
                sys.modules.pop('run_os_goal', None)
                if previous is not None:
                    sys.modules['run_os_goal'] = previous
                sys.path[:] = previous_path
            stack.callback(restore)
            sys.path.insert(0, '/home/holden/mckernel/scripts')
            consumer._load_current_validator()
            sdk = sys.modules['run_os_goal']
            self.assertEqual(Path(sdk.__file__), scripts / 'run_os_goal.py')
            self.assertEqual(hashlib.sha256(Path(sdk.__file__).read_bytes()).hexdigest(), SDK_SHA)
            stack.enter_context(patch.object(consumer.time, 'time_ns', side_effect=clock.time_ns))
            stack.enter_context(patch.object(consumer.time, 'monotonic_ns', side_effect=clock.monotonic_ns))
            effect_names = []
            def blocked(name):
                def fail(*args, **kwargs):
                    effect_names.append(name)
                    raise HarnessError('Forbidden test effect: ' + name)
                return fail
            for obj, name in ((sdk.RPC, 'call'), (sdk.Campaign, '__init__'),
                              (sdk.CreditBudget, 'observe'), (sdk, 'atomic_json'),
                              (sdk.subprocess, 'Popen')):
                stack.enter_context(patch.object(obj, name, side_effect=blocked(name)))
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            credit_path = repo / '.git/os-autopilot/credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json'
            state_path = repo / '.git/os-autopilot/state.json'
            objective = 'Literal private liveness fixture; never an actual saved goal'
            owner = {'boot_id': boot, 'repo': str(repo), 'guardian_run_id': 'private-model',
                'log_dir': str(repo / 'private-model-log'),
                'thread_id': '01a18bc3-e072-7810-9426-75101b0856c0',
                'goal_objective_sha256': sdk._account_value_sha256(objective),
                'worker_pid': 41001, 'worker_start': '11001',
                'server_pid': 41002, 'server_start': '11002',
                'credit_run_id': '7c6ef3604bfb4008a917bba8cfb6cfaa',
                'credit_budget': '100', 'credit_ledger_path': str(credit_path)}
            ledger = {'schema_version': 2, 'id': owner['credit_run_id'], 'budget': '100',
                'initial_balance': '1000', 'minimum_balance': '1000', 'last_balance': '1000',
                'spent': '0', 'remaining': '100', 'scope': 'Literal private test data only'}
            rate = old.limits()
            receipt = {'schema_version': 1, 'source': 'read', 'method': 'account/rateLimits/read',
                'request_id': 17, 'received_at': clock.utc(), 'received_utc_ns': clock.time_ns(),
                'received_mono_ns': clock.monotonic_ns(), 'sequence': 1,
                'server_pid': owner['server_pid'], 'rate_limits_sha256': sdk._account_value_sha256(rate),
                'response_error': False, 'status': 'ACCEPTED', 'owner': owner,
                'credit_record_sha256': sdk._account_value_sha256(ledger),
                'state_limits_and_credit_persisted': True}
            state = dict(owner, phase='running', stop_reason=None,
                weekly_usage_error=None, weekly_confirmation_pending=False,
                auth_mode='chatgpt', credit_budget_error=None,
                goal={'status': 'active', 'threadId': owner['thread_id'], 'objective': objective},
                last_rate_limits=rate, credit_budget=ledger,
                last_account_observation=receipt, successful_account_read=receipt)
            # Literal matched snapshot data is never persisted or published.
            state_bytes = json.dumps(state).encode()
            credit_bytes = json.dumps(ledger).encode()
            original_read = Path.read_bytes
            original_accept = sdk.accepted_account_observation
            for row in rows:
                with self.subTest(row=row['id']):
                    counts = {'state_reads': 0, 'ledger_reads': 0, 'proc_reads': 0}
                    trace = []
                    def read_bytes(path):
                        if path == state_path:
                            counts['state_reads'] += 1
                            return state_bytes
                        if path == credit_path:
                            counts['ledger_reads'] += 1
                            return credit_bytes
                        if path == scripts / 'run_os_goal.py':
                            return original_read(path)
                        raise HarnessError('Unexpected read_bytes path: ' + str(path))
                    def read_text(path, *args, **kwargs):
                        if path == Path('/proc/sys/kernel/random/boot_id'):
                            return boot
                        for kind in ('worker', 'server'):
                            pid, birth = owner[kind + '_pid'], owner[kind + '_start']
                            if path != Path('/proc/%d/stat' % pid):
                                continue
                            counts['proc_reads'] += 1
                            bookend = 'before' if counts['state_reads'] == 1 else 'after'
                            process_state = 'R' if kind == 'worker' else 'S'
                            if row.get('kind') == kind and row.get('bookend') == bookend:
                                process_state = row['state']
                            fields = [process_state] + ['0'] * 18 + [birth] + ['0'] * 10
                            self.assertEqual(fields[19], owner[kind + '_start'])
                            trace.append({'kind': kind, 'bookend': bookend,
                                          'state': process_state, 'birth': birth})
                            return '%d (private model owner) %s\n' % (pid, ' '.join(fields))
                        raise HarnessError('Unexpected read_text path: ' + str(path))
                    with patch.object(Path, 'read_bytes', read_bytes), \
                            patch.object(Path, 'read_text', read_text), \
                            patch.object(Path, 'write_bytes', side_effect=blocked('write_bytes')), \
                            patch.object(Path, 'write_text', side_effect=blocked('write_text')), \
                            patch.object(sdk, 'accepted_account_observation', wraps=original_accept) as validate:
                        accepted = False
                        try:
                            got_state, usage, got_credit, observed = consumer.current_account_snapshot(owner)
                            accepted = True
                        except AssertionError:
                            if row['accepted']:
                                raise
                        if accepted:
                            self.assertEqual(got_state, state)
                            self.assertEqual(got_credit, ledger)
                            self.assertEqual((usage['source_kind'], usage['source_event']),
                                             ('read', 'account/rateLimits/read'))
                            self.assertEqual(usage['receipt_received_utc_ns'], receipt['received_utc_ns'])
                        self.assertEqual(accepted, row['accepted'])
                        self.assertEqual(validate.call_count, row['validator_calls'])
                    for key in counts:
                        self.assertEqual(counts[key], row[key])
                    if not accepted:
                        self.assertEqual((trace[-1]['kind'], trace[-1]['bookend'], trace[-1]['state']),
                                         (row['kind'], row['bookend'], row['state']))
                    self.assertEqual(effect_names, [])
                    self.observations.append({'id': row['id'], 'accepted': accepted,
                        **counts, 'validator_calls': validate.call_count,
                        'matching_births': True, 'proc_trace': trace, 'forbidden_effects': []})


def main():
    if len(sys.argv) != 2:
        raise HarnessError('Expected one new private output file')
    output = Path(sys.argv[1])
    if output.exists() or not output.parent.is_dir():
        raise HarnessError('Output must be absent beneath Root-created output')
    diagnostics = io.StringIO()
    result = unittest.TextTestRunner(stream=diagnostics, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(OwnerLiveness))
    observations = OwnerLiveness.observations
    with output.open('x') as stream:
        json.dump({'observations': observations, 'diagnostics': diagnostics.getvalue(),
                   'failures': len(result.failures), 'errors': len(result.errors)}, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if not result.wasSuccessful():
        sys.stderr.write(diagnostics.getvalue())
        return 1
    print(json.dumps({'status': 'PASS_CHANGED_OWNER_LIVENESS_BRANCH',
        'live_rows': sum(row['accepted'] for row in observations),
        'rejected_rows': sum(not row['accepted'] for row in observations),
        'state_reads': sum(row['state_reads'] for row in observations),
        'ledger_reads': sum(row['ledger_reads'] for row in observations),
        'proc_reads': sum(row['proc_reads'] for row in observations),
        'validator_calls': sum(row['validator_calls'] for row in observations),
        'RPC_Campaign_observe_or_writes': 0, 'old18_methods_executed': 0}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
