"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent pure controls against coherent byte-reference mutations and exact schema.
The retained scenario substitutes guard/process effects and removes temporary files.
"""
from pathlib import Path
import ast
import copy
import importlib.util
import json
import unittest

E = Path(__file__).resolve().parent.parent
D = E / ('m15-bfd-default-next-integration-source-20261028-1/'
         'new-window-producer-cohort-source-1/latest-root61-consumer-successor-source-1/'
         'actual-entry-coupling-source-1')
spec = importlib.util.spec_from_file_location('retained_coupling_test_scenario', D / 'test_coupled_pipeline.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class IndependentCoupling(unittest.TestCase):
    def test_reject_resource_change_with_coherent_new_hash_chain(self):
        with fixture.scenario() as x:
            value = copy.deepcopy(x['resource'])
            value['other_reserved_pids'] = 65
            resource = fixture.common.atomic_json(x['A'] / 'TEST_ONLY_CHANGED_RESOURCE.json', value)
            pending = copy.deepcopy(x['pending'])
            pending['resource_authority'] = resource
            pending_ref = fixture.common.atomic_json(x['A'] / 'TEST_ONLY_CHANGED_PENDING.json', pending)
            marker = dict(x['marker'], resource=resource, pending_input=pending_ref)
            with self.assertRaisesRegex(ValueError, 'full actual producer'):
                fixture.review.hot(x['c'], marker)

    def test_reject_pending_change_with_valid_reference(self):
        with fixture.scenario() as x:
            pending = copy.deepcopy(x['pending'])
            pending['maximum_invocations'] = 2
            pending_ref = fixture.common.atomic_json(x['A'] / 'TEST_ONLY_CHANGED_PENDING.json', pending)
            with self.assertRaisesRegex(ValueError, 'full actual producer'):
                fixture.review.hot(x['c'], dict(x['marker'], pending_input=pending_ref))

    def test_exact_schema_and_unchanged_retained_consumer_body(self):
        contract = fixture.contract['Root61_observer_fragment']
        accepted = json.loads(Path(contract['current_observer_schema']['path']).read_bytes())
        candidate = json.loads((D / 'OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json').read_bytes())
        self.assertEqual(set(candidate), set(accepted))
        self.assertEqual({k: v for k, v in candidate.items() if k != 'observer'},
                         {k: v for k, v in accepted.items() if k != 'observer'})
        self.assertEqual(candidate['observer'], fixture.common.reference(D / 'observe_bfd_current61.py'))
        def body(path, name):
            module = ast.parse(Path(path).read_bytes())
            return ast.dump(next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name),
                            include_attributes=False)
        for name in ('validate_current', 'consumer_value'):
            self.assertEqual(body(D / 'observe_bfd_current61.py', name),
                             body(contract['current_observer_source']['path'], name))


if __name__ == '__main__':
    unittest.main(verbosity=2)
