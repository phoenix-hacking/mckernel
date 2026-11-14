"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure AST fixture; no import or execution of the compile owner or driver.
"""
import ast
from decimal import Decimal
from pathlib import Path
import re
import unittest

HERE = Path(__file__).parent
OWNER = HERE / 'sdk13_compile_image_owner.py'
ORIGINAL = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate/compile_image_owner.py')
tree = ast.parse(OWNER.read_text())
original_tree = ast.parse(ORIGINAL.read_text())
required = {'SDK13_PROFILE_SHA', 'SDK13_RETIREMENT_SHA', 'SDK13_RETIREMENT_ACCEPTANCE_SHA',
            'SDK13_V3_REVIEW_SHA', 'SDK13_REQUIRED_FACTS'}
nodes = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
         and isinstance(n.targets[0], ast.Name) and n.targets[0].id in required]
nodes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_validate_sdk13_facts']
assert len(nodes) == len(required) + 1

def fail(ok, reason):
    if not ok:
        raise ValueError(reason)

env = {'Decimal': Decimal, 're': re, '_fail': fail}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), '<sdk13-pure>', 'exec'), env)


def valid():
    return {'status': 'SDK13_COMPILE_ONLY_ADMISSION', 'profile_sha256': env['SDK13_PROFILE_SHA'],
            'retirement_result_sha256': env['SDK13_RETIREMENT_SHA'],
            'retirement_acceptance_sha256': env['SDK13_RETIREMENT_ACCEPTANCE_SHA'],
            'v3_observation_review_sha256': env['SDK13_V3_REVIEW_SHA'],
            'boot_id': 'fixture-boot', 'observed_boottime_ns': 100,
            'unknown_custody_retained': True, 'historical_no_unlisted': None, 'current_free': None,
            'facts': {k: {'verdict': 'PASS', 'evidence_sha256': '1' * 64}
                      for k in env['SDK13_REQUIRED_FACTS']},
            'reservations': {'native_memory_bytes': 12 * 2**30, 'native_cpus': '2-5',
                             'native_memory_swap_bytes': 12 * 2**30, 'native_pids': 512,
                             'v2_unknown_memory_bytes': 2 * 2**30, 'v2_unknown_cpu': '7',
                             'pure_memory_bytes': 2**29, 'pure_cpu': '0', 'compile_memory_bytes': 4 * 2**30,
                             'compile_memory_swap_bytes': 4 * 2**30, 'compile_pids': 128,
                             'compile_cpu': '6', 'mutex': '27:4', 'scratch': '21'},
            'aggregate_memory_bytes': 20 * 2**30, 'aggregate_cpu_shares': 7,
            'MemAvailable': 24 * 2**30, 'host_free_bytes': 16 * 2**30,
            'scratch_free_bytes': 12 * 2**30}


class AdmissionFixture(unittest.TestCase):
    def test_complete_fixture(self):
        self.assertEqual(env['_validate_sdk13_facts'](valid(), 101, 'fixture-boot')['status'],
                         'SDK13_COMPILE_ONLY_ADMISSION')

    def test_all_missing_facts_fail(self):
        for name in env['SDK13_REQUIRED_FACTS']:
            with self.subTest(name=name):
                item = valid()
                del item['facts'][name]
                with self.assertRaisesRegex(ValueError, 'required reviewed fact missing'):
                    env['_validate_sdk13_facts'](item, 101, 'fixture-boot')

    def test_unknown_cannot_be_erased(self):
        for name, value in [('unknown_custody_retained', False), ('current_free', True),
                            ('historical_no_unlisted', True)]:
            with self.subTest(name=name):
                item = valid(); item[name] = value
                with self.assertRaises(ValueError):
                    env['_validate_sdk13_facts'](item, 101, 'fixture-boot')

    def test_reservation_and_budget_fail_closed(self):
        for key, value in [('aggregate_memory_bytes', 23 * 2**30), ('aggregate_cpu_shares', 8),
                           ('MemAvailable', 23 * 2**30), ('host_free_bytes', 0)]:
            with self.subTest(key=key):
                item = valid(); item[key] = value
                with self.assertRaises(ValueError):
                    env['_validate_sdk13_facts'](item, 101, 'fixture-boot')
        item = valid(); item['reservations']['v2_unknown_memory_bytes'] = 0
        with self.assertRaises(ValueError):
            env['_validate_sdk13_facts'](item, 101, 'fixture-boot')

    def test_old_owner_lifecycle_asts_retained(self):
        retained = {'CompileLease', '_assert_owned_container', '_own_inspect', '_own_absence',
                    '_cleanup_owned_compile', 'release_accepted_compile_lease', 'ImageOwner'}
        def selected(t):
            return {n.name: ast.dump(n, include_attributes=False) for n in t.body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in retained}
        self.assertEqual(selected(tree), selected(original_tree))
        self.assertEqual(set(selected(tree)), retained)

    def test_sdk13_path_authenticates_before_lease(self):
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SDK13ImageOwner')
        run = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        body = ast.unparse(run)
        self.assertLess(body.index('_sdk13_authorize(r)'), body.index('lease.acquire()'))
        self.assertLess(body.index('self.validator.validate('), body.index('lease.acquire()'))
        self.assertEqual(body.count('self.validator.revalidate(bound, r)'), 5)
        self.assertNotIn('_check_live_p12', body)
        self.assertIn('no_container_create_attempted', body)

    def test_private_helper_keeps_sudo_A_and_captures_birth(self):
        helper=(HERE/'sdk13_compile_host_helper.py').read_text()
        self.assertIn("'/usr/bin/sudo', '-A'",helper)
        self.assertNotIn("'/usr/bin/sudo', '-n'",helper)
        self.assertIn("'birth': int(fields[19])",helper)
        self.assertIn('self.client_retirement_unproven = True',helper)



if __name__ == '__main__':
    unittest.main()
