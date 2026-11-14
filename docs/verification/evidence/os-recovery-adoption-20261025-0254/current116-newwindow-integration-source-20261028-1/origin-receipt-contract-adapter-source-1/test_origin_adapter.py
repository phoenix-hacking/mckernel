"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY retained data and full real materializer with no-effects guard/temp output.
"""
from pathlib import Path
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import types
import unittest

D = Path(__file__).resolve().parent
E = D.parent.parent
C = D.parent / 'configured-dependencies-successor-1/cohort'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


a = load(D / 'adapt_origin_receipt.py', 'exact_origin_receipt_adapter')


class OriginAdapterTests(unittest.TestCase):
    def test_exact_retained_receipt_preserved(self):
        original = json.loads(a.SOURCE.read_bytes())
        output = a.adapted(a.SOURCE)
        for key, value in original.items(): self.assertEqual(output[key], value)
        self.assertIs(output['compiler_executed'], False)
        self.assertIs(output['direct_child_joined'], True)
        self.assertIs(output['streams_closed'], True)
        self.assertEqual(output['source_receipt']['sha256'], a.SOURCE_SHA)

    def test_semantic_false_missing_and_changed_source_controls(self):
        original = json.loads(a.SOURCE.read_bytes())
        for key, wrong in [('compiler', True), ('source_generation_only', False),
                           ('child_positive_join', False), ('closed_streams', False),
                           ('returncode', 1), ('returncode', False), ('author', '/root/worker')]:
            with self.subTest(key=key, wrong=wrong):
                changed = copy.deepcopy(original); changed[key] = wrong
                with self.assertRaises(ValueError): a.validate_semantics(changed)
        for key in ['compiler', 'child_positive_join', 'closed_streams', 'outputs', 'argv']:
            changed = copy.deepcopy(original); del changed[key]
            with self.assertRaises(ValueError): a.validate_semantics(changed)
        changed = copy.deepcopy(original); changed['argv'][-1] += '-wrong'
        with self.assertRaises(ValueError): a.validate_semantics(changed)
        changed = copy.deepcopy(original); changed['outputs'].reverse()
        with self.assertRaises(ValueError): a.validate_semantics(changed)
        with tempfile.TemporaryDirectory(prefix='TEST-ONLY-wrong-source-', dir=D) as temporary:
            wrong = Path(temporary) / 'same-bytes-wrong-source.json'
            wrong.write_bytes(a.SOURCE.read_bytes())
            with self.assertRaises(ValueError): a.adapted(wrong)
            wrong.write_text('{}')
            with self.assertRaises(ValueError): a.adapted(wrong)

    def test_full_real_materializer_against_actual_root_bindings(self):
        materializer = load(C / 'materialize_admission.py', 'real116_materializer_TEST_ONLY')
        original = json.loads((C / 'ROOT-ACTUAL-BINDINGS-1.json').read_bytes())
        self.assertFalse(Path(original['admission']).exists(), 'actual admission remains absent')
        guards = []
        with tempfile.TemporaryDirectory(prefix='TEST-ONLY-full-materializer-', dir=D) as temporary:
            root = Path(temporary)
            adapted_path = root / 'ADAPTED-ORIGIN.TEST-ONLY.json'
            adapted_path.write_text(json.dumps(a.adapted(a.SOURCE), indent=2) + '\n')
            bindings = copy.deepcopy(original)
            bindings['actual_origin_producer'] = a.reference(adapted_path)
            # TEST_ONLY output routing; all accepted input/reference predicates stay
            # actual. No frozen source or production Root binding changes occur.
            bindings['admission'] = str(root / 'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-99999')
            materializer.E = root
            actual_ref = materializer.ref
            def redirected_reference(path):
                path = Path(path)
                if path.is_relative_to(root) and not path.exists():
                    return actual_ref(E / path.relative_to(root))
                return actual_ref(path)
            materializer.ref = redirected_reference
            actual_util = importlib.util
            def no_effect_spec(name, path):
                spec = actual_util.spec_from_file_location(name, path)
                actual_loader = spec.loader
                class NoEffectsRunnerLoader:
                    def create_module(self, spec): return actual_loader.create_module(spec)
                    def exec_module(self, module):
                        actual_loader.exec_module(module)
                        module.current_operation_guard = lambda: guards.append('TEST_ONLY guard effect substituted')
                spec.loader = NoEffectsRunnerLoader()
                return spec
            materializer.importlib = types.SimpleNamespace(util=types.SimpleNamespace(
                spec_from_file_location=no_effect_spec, module_from_spec=actual_util.module_from_spec))
            input_path = root / 'BINDINGS.TEST-ONLY.json'
            input_path.write_text(json.dumps(bindings, indent=2) + '\n')
            with contextlib.redirect_stdout(io.StringIO()): materializer.materialize(input_path)
            self.assertEqual(guards, ['TEST_ONLY guard effect substituted'])
            output = Path(bindings['admission'])
            profile = json.loads((output / 'PROFILE.SOURCE-ONLY.json').read_bytes())
            request = json.loads((output / 'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json').read_bytes())
            export = json.loads((output / 'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json').read_bytes())
            self.assertEqual(len(profile['exact_commands']), 4)
            self.assertEqual(profile['inputs']['retained_count'], 8)
            self.assertIsNone(request['actual_execution_grant'])
            self.assertEqual(export['actual_origin_producer_receipt'], bindings['actual_origin_producer'])
            self.assertFalse((output / 'HOLDER').exists())
            self.assertFalse((output / 'OUTPUT').exists())
        self.assertFalse(Path(original['admission']).exists())


if __name__ == '__main__': unittest.main(verbosity=2)
