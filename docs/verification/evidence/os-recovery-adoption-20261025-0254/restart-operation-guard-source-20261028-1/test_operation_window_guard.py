"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap pure regression checks; never invokes live guard/account or runtime operations.
"""
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('candidate', HERE/'operation_window_guard.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def fixture(operation='current116'):
    successor = dict(schema='mckernel.explicit-new-window-operation-successor.v1',
                     author='/root', operation=operation, decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',
                     window_sha256=g.WINDOW_SHA256, credit_run_id=g.RUN, credit_ceiling=g.CEILING,
                     predecessor_cutoffs=list(g.PREDECESSOR_CUTOFFS[operation]),
                     operation_cutoffs=list(g.CUTOFFS), subjects={'consumer': {'path': '/fixture/source.py', 'bytes': 1, 'sha256': '0'*64}},
                     source_owners=['/root', '/root/windowguards'], minimum_cumulative_spent='22812.3311',
                     guardian={'source': g.GUARDIAN_SOURCE.copy(), 'entrypoint': 'guard'})
    review = dict(schema='mckernel.independent-operation-window-review.v1',
                  decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR', independent=True,
                  reviewer='/root/independent_review', operation=operation, successor=copy.deepcopy(successor))
    return successor, review


class OperationChecks(unittest.TestCase):
    def check(self, successor, review, operation='current116', clocks=None, subjects=None, boot=g.BOOT):
        return g.validate_operation(successor, review, operation,
                                    successor['subjects'] if subjects is None else subjects,
                                    [1793166746, 948853, 964191] if clocks is None else clocks, boot)

    def test_two_operations(self):
        for operation in g.PREDECESSOR_CUTOFFS:
            self.assertEqual(self.check(*fixture(operation), operation=operation), g.CUTOFFS)

    def test_actual_new_window_bytes(self):
        self.assertEqual(g.load_window()['deadline_epoch'], g.CUTOFFS[0])

    def test_explicit_tighter_operation(self):
        successor, review = fixture()
        successor['operation_cutoffs'] = [1793170000, 950000, 965000]
        review['successor'] = copy.deepcopy(successor)
        self.assertEqual(self.check(successor, review), tuple(successor['operation_cutoffs']))

    def test_negative_mutations(self):
        mutations = [
            ('author', '/root/worker'), ('operation', 'original227'),
            ('decision', 'LAUNCHER_WINDOW_IS_ENOUGH'), ('window_sha256', '0'*64),
            ('credit_run_id', 'new'), ('credit_ceiling', '57775'),
            ('predecessor_cutoffs', list(g.CUTOFFS)),
            ('operation_cutoffs', [1793253601, *g.CUTOFFS[1:]]),
            ('operation_cutoffs', [g.CUTOFFS[0], g.CUTOFFS[1]+1, g.CUTOFFS[2]]),
            ('operation_cutoffs', [*g.CUTOFFS[:2], g.CUTOFFS[2]+1]),
            ('operation_cutoffs', [True, 1, 1]), ('operation_cutoffs', [float('nan'), 1, 1]),
            ('operation_cutoffs', list(g.PREDECESSOR_CUTOFFS['current116'])),
            ('subjects', {}), ('minimum_cumulative_spent', '0'),
            ('minimum_cumulative_spent', '57774.852125'), ('guardian', {}),
        ]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                successor, review = fixture()
                successor[key] = value
                review['successor'] = copy.deepcopy(successor)
                with self.assertRaises((ValueError, KeyError)):
                    self.check(successor, review)

    def test_independent_review_required(self):
        for key, value in [('independent', False), ('reviewer', '/root'), ('reviewer', '/root/windowguards'),
                           ('operation', 'original227'), ('decision', 'SOURCE_ONLY')]:
            with self.subTest(key=key):
                successor, review = fixture()
                review[key] = value
                with self.assertRaises(ValueError):
                    self.check(successor, review)

    def test_no_stale_review(self):
        successor, review = fixture()
        successor['minimum_cumulative_spent'] = '22813'
        with self.assertRaises(ValueError):
            self.check(successor, review)

    def test_exact_boundary_all_clocks(self):
        for index in range(3):
            successor, review = fixture()
            clocks = [1793166746, 948853, 964191]
            clocks[index] = g.CUTOFFS[index]
            with self.assertRaises(ValueError):
                self.check(successor, review, clocks=clocks)

    def test_wrong_boot_and_sources(self):
        with self.assertRaises(ValueError):
            self.check(*fixture(), boot='different')
        with self.assertRaises(ValueError):
            self.check(*fixture(), subjects={'other': {}})

    def test_byte_subject_is_not_json(self):
        source = g.reference(HERE/'operation_window_guard.py')
        self.assertIsInstance(g.authenticated(source), bytes)
        with self.assertRaises(json.JSONDecodeError):
            g.authenticated(source, declared_json=True)

    def test_historical_account_semantics_and_tightened_floor(self):
        state = json.loads((g.PREDECESSOR.parent/'ACCOUNT-FIXTURE.json').read_text())
        old_thread = state['thread_id']
        state['thread_id'] = g.THREAD
        wall = datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp()+1
        for wrong_thread in [old_thread, 'unrelated']:
            changed = copy.deepcopy(state)
            changed['thread_id'] = wrong_thread
            with self.assertRaises(ValueError):
                g.check_account_state(changed, wall, '22812.3311')
        self.assertGreater(g.check_account_state(state, wall, '22812.3311'), 0)
        for floor in ['0', '57774.852125']:
            with self.assertRaises(ValueError):
                g.check_account_state(state, wall, floor)
        for key in ['service_hold', 'policy_hold', 'auth_hold', 'billing_hold', 'stop_now']:
            with self.subTest(key=key):
                changed = copy.deepcopy(state)
                changed[key] = True
                with self.assertRaises(ValueError):
                    g.check_account_state(changed, wall, '22812.3311')
        with self.assertRaises(ValueError):
            g.check_account_state(state, wall+180, '22812.3311')
        for key in ['automatic_credit_purchase', 'api_key_billing']:
            changed = copy.deepcopy(state)
            changed['settings']['billing'][key] = True
            with self.assertRaises(ValueError):
                g.check_account_state(changed, wall, '22812.3311')

    def test_two_noarg_adapters_without_live_guard(self):
        for operation in g.PREDECESSOR_CUTOFFS:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory(dir=HERE) as directory:
                directory = Path(directory)
                successor, review = fixture(operation)
                for name, data in [('successor', successor), ('review', review)]:
                    (directory/(name+'.json')).write_text(json.dumps(data))
                config = dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',
                              operation=operation, shared_guard=g.reference(HERE/'operation_window_guard.py'),
                              successor=g.reference(directory/'successor.json'), review=g.reference(directory/'review.json'),
                              subjects=successor['subjects'])
                path = directory/'config.json'
                path.write_text(json.dumps(config))
                spec = importlib.util.spec_from_file_location('adapter_'+operation, HERE/('bfd_guard_adapter.py' if operation == 'bfd-current-default-two-tools' else operation+'_guard_adapter.py'))
                adapter = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(adapter)
                with self.assertRaisesRegex(ValueError, 'explicit sealed'):
                    adapter.current_cutoffs()
                adapter.configure(g.reference(path))
                self.assertEqual(adapter.current_cutoffs(), g.CUTOFFS)
                with self.assertRaisesRegex(ValueError, 'one-time immutable'):
                    adapter.configure(g.reference(path))
                path.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'sealed config/source bytes'):
                    adapter.current_cutoffs()

    def test_strict_json(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}']:
            with self.assertRaises(ValueError):
                g.decode(raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
