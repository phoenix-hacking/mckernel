"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure AST and mocked-Popen regression. No child program, source export or SDK runs.
"""
import ast
import copy
import json
from pathlib import Path
import types
import unittest

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[2] / 'phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'


def function(path):
    return next(n for n in ast.parse(path.read_bytes()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'owned_capture')


def popen_call(node):
    return next(n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess' and n.func.attr == 'Popen')


class CwdTests(unittest.TestCase):
    def setUp(self):
        self.old, self.new = function(OLD), function(HERE / 'owned_capture_optional_cwd.py')

    def invoke_constructor(self, node, command):
        observed = {}
        output, error, devnull, result = object(), object(), object(), object()
        def fake_popen(*args, **kwargs):
            observed.update(args=args, kwargs=kwargs)
            return result
        limits = lambda: None
        context = dict(subprocess=types.SimpleNamespace(Popen=fake_popen, DEVNULL=devnull),
                       command=command, out=output, err=error, child_limits=limits)
        expression = ast.Expression(body=copy.deepcopy(popen_call(node)))
        self.assertIs(eval(compile(ast.fix_missing_locations(expression), '<exact-h990-Popen-call>', 'eval'), context), result)
        return observed

    def test_explicit_cwd_reaches_exact_Popen(self):
        argv = ['/usr/bin/cmake', '-E', 'cmake_link_script', 'CMakeFiles/ihklib.dir/link.txt', '--verbose=1']
        command = dict(argv=argv, cwd='/work/output/current-ihkconfig-library-consumer/ihk/linux/user')
        observed = self.invoke_constructor(self.new, command)
        self.assertIs(observed['args'][0], argv)
        self.assertEqual(observed['kwargs']['cwd'], command['cwd'])
        self.assertTrue(observed['kwargs']['start_new_session'])

    def test_omitted_cwd_preserves_original_default(self):
        command = dict(argv=['/usr/bin/cmake', '--version'])
        observed = self.invoke_constructor(self.new, command)
        self.assertIsNone(observed['kwargs']['cwd'])
        self.assertNotIn('cwd', {k.arg: k.value for k in popen_call(self.old).keywords})
        self.assertEqual([x.arg for x in popen_call(self.new).keywords if x.arg != 'cwd'],
                         [x.arg for x in popen_call(self.old).keywords])

    def test_one_keyword_is_the_entire_capture_function_delta(self):
        normalized = copy.deepcopy(self.new)
        call = popen_call(normalized)
        cwd = [keyword for keyword in call.keywords if keyword.arg == 'cwd']
        self.assertEqual(len(cwd), 1)
        self.assertEqual(ast.unparse(cwd[0].value), "command.get('cwd')")
        call.keywords = [keyword for keyword in call.keywords if keyword.arg != 'cwd']
        self.assertEqual(ast.dump(normalized, include_attributes=False), ast.dump(self.old, include_attributes=False))

    def test_phase_contract_keeps_exact_eight_producer_argv(self):
        plan = json.loads((HERE / 'CONSUMER-PHASE-CONTRACT.SOURCE-ONLY.json').read_bytes())
        original = json.loads((HERE.parent / 'GUARDED-CURRENT-CONSUMER-RECIPE.json').read_bytes())
        selected = [phase for phase in plan['phases'] if 'producer_index' in phase]
        self.assertEqual([phase['argv'] for phase in selected], [phase['argv'] for phase in original['commands']])
        self.assertEqual(len(plan['phases']), 15)
        self.assertEqual(sum(phase['kind'] == 'git_identity' for phase in plan['phases']), 6)
        self.assertEqual(plan['actual_source_adoption']['sha256'], 'f24b9dbe11483db23b16ab896521d183385ad8e64dc64b03c8f969dc55101b39')
        for phase in selected:
            if phase['kind'].startswith('link_'):
                self.assertEqual(phase['cwd'], '/work/output/current-ihkconfig-library-consumer/ihk/linux/user')
        self.assertTrue(any(phase['output']['type'] == 'directory' for phase in selected if 'output' in phase))


if __name__ == '__main__':
    unittest.main(verbosity=2)
