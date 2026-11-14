"""Functional OS source-role regressions only; no workload/tool/guard execution."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

D = Path(__file__).resolve().parent
P = D.parent
B = P.parents[1] / 'bfd-default-control-routing-restart-20261028-1/cohort'
spec = importlib.util.spec_from_file_location('consumer_outer_source_test', D / 'run_build_only.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def functions(path):
    return {n.name: n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}


class ConsumerRoleTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((D / 'PROFILE.SOURCE-ONLY.json').read_text())
        self.role = json.loads((D / 'STATIC-ROLE.SOURCE-ONLY.json').read_text())

    def test_generic_owner_and_holder_logic_remain_exact(self):
        before, after = functions(B / 'run_build_only.py'), functions(D / 'run_build_only.py')
        for name in ('require', 'reference', 'auth', 'read', 'strict_parent', 'resource_guards',
                     'docker_prefix', 'docker_argv', 'current_operation_guard', 'main'):
            self.assertEqual(ast.dump(before[name]), ast.dump(after[name]), name)
        self.assertEqual((D / 'hold_and_run_build_only.py').read_bytes(),
                         (B / 'hold_and_run_build_only.py').read_bytes())
        # The ownership/launch/terminal suffix is exact except the container role name.
        old = ast.get_source_segment((B / 'run_build_only.py').read_text(), before['execute'])
        new = ast.get_source_segment((D / 'run_build_only.py').read_text(), after['execute'])
        old = old[old.index('    holder=resources'):].replace("name='bfd-current-two-target-'", "name='m15-current-consumer-'")
        new = new[new.index('    holder=resources'):]
        # The selected-source callback name stays compatible; its body alone changes.
        self.assertEqual(old, new)

    def test_one_exact_leaf_and_original_eight_argv(self):
        commands = r.commands_for_plan(self.profile)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]['new_output'], '/work/evidence/current-consumer-producer.json')
        self.assertEqual(commands[0]['cwd'], '/work')
        phase = json.loads((P / 'CONSUMER-PHASE-CONTRACT.SOURCE-ONLY.json').read_text())
        self.assertEqual(len(phase['phases']), 15)
        self.assertTrue(phase['original_eight_argv_unchanged'])
        self.assertEqual(commands[0]['argv'][-1], r.reference(P / 'CONSUMER-PHASE-CONTRACT.SOURCE-ONLY.json')['sha256'])
        bad = copy.deepcopy(self.profile)
        bad['exact_commands'].append(copy.deepcopy(commands[0]))
        with self.assertRaises(RuntimeError): r.commands_for_plan(bad)
        bad = copy.deepcopy(self.profile)
        bad['exact_commands'][0]['argv'] = ['/old-sdk11-ten-command-driver']
        with self.assertRaises(RuntimeError): r.commands_for_plan(bad)

    def test_readonly_mounts_are_exact_and_use_actual_adoption(self):
        export = dict(source_adoption=self.profile['actual_source_adoption'],
                      readable_source_export=self.profile['inputs']['source_export_root'])
        with mock.patch.object(r, 'verify_bfd_source_export', return_value=None) as verified:
            rows = r.mounts(self.profile, export, Path('/fresh-uncreated-test-output'))
            verified.assert_called_once_with(self.profile)
        self.assertEqual(rows[:-2], self.role['read_only_mount_roles'])
        self.assertTrue(all(x['readonly'] is True for x in rows))
        self.assertEqual(len({x['target'] for x in rows}), len(rows))
        targets = {x['target']: x for x in rows}
        self.assertEqual(targets['/source']['host'], self.role['source_root'])
        self.assertEqual(targets['/source/.git/modules/ihk']['host'], '/home/holden/mckernel/.git/modules/ihk')
        self.assertIn('/accepted-sdk11', targets)
        self.assertIn('/nightly', targets)
        self.assertIn('/out', targets)
        bad = dict(export, readable_source_export='/old-source')
        with self.assertRaises(RuntimeError): r.mounts(self.profile, bad, Path('/unused'))

    def test_changed_source_receipt_and_null_root_facts_rejected(self):
        # Finite selected files only: no directory inventory or SDK archive hashing.
        adoption = r.verify_bfd_source_export(self.profile)
        self.assertEqual(len(adoption['verified_selected_inputs']), 58)
        bad = copy.deepcopy(self.profile)
        bad['actual_source_adoption']['sha256'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'exact f24'):
            r.verify_bfd_source_export(bad)
        bad = copy.deepcopy(self.profile)
        bad['inputs']['read_only_mount_roles'][1]['readonly'] = False
        with self.assertRaisesRegex(RuntimeError, 'readonly mounts'):
            r.verify_bfd_source_export(bad)
        for field in ('native_custody_clearance', 'current_entry_bindings', 'source_writer_quiescence',
                      'actual_nonce', 'actual_execution_review', 'actual_resource_authority',
                      'actual_output_root', 'actual_root_ledger', 'actual_current_descriptor',
                      'current_free', 'Root_author', 'Root_grant'):
            self.assertIsNone(self.profile[field], field)
        with self.assertRaisesRegex(RuntimeError, 'authenticated reference'):
            r.auth(self.profile['current_entry_bindings'])

    def test_worker_only_role_predicates_and_tighter_cutoff_change(self):
        old = (B / 'build_only_worker.py').read_text()
        expected = old.replace('1035705.5689454618, 1051043.6959931096',
                               '1035704.5689393478, 1051042.6959879305')
        expected = expected.replace("len(plan['commands'])==3,'exact three current BFD producer commands'",
                                    "len(plan['commands'])==1,'one exact current consumer serial leaf'")
        start = expected.index('            if index==1:\n')
        end = expected.index("        (out/'producer-contract.json')", start)
        expected = expected[:start] + expected[end:]
        expected = expected.replace("status='ACTUAL_CURRENT_BFD_THREE_COMMAND_PRODUCER'",
                                    "status='ACTUAL_CURRENT_CONSUMER_ONE_SERIAL_LEAF'")
        expected = expected.replace('fresh_genuine_two_target_configure=True', 'serial_consumer_leaf=True')
        expected = expected.replace("'first failed configure/build/readback stops suffix'",
                                    "'failed consumer leaf stops without replay'")
        self.assertEqual((D / 'build_only_worker.py').read_text(), expected)
        # No subprocess constructor is invoked by this test suite.


if __name__ == '__main__': unittest.main(verbosity=2)
