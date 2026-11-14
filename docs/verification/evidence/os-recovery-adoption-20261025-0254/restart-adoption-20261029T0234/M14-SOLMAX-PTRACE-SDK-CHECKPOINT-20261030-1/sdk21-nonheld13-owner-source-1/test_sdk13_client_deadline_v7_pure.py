"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure extracted deadline arithmetic and AST order checks; no owner or child is executed.
"""
import ast,unittest
from pathlib import Path

HERE=Path(__file__).parent
tree=ast.parse((HERE/'sdk13_compile_host_helper.v7.py').read_text())
owner=ast.parse((HERE/'sdk13_compile_image_owner.v7.py').read_text())
names={'_sdk13_client_deadlines','_sdk13_deadline_remaining'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes}==names
env={};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                    '<pure-deadline>','exec'),env)


class DeadlineFixture(unittest.TestCase):
    def test_single_absolute_window_does_not_reset_after_setup(self):
        deadline,work=env['_sdk13_client_deadlines']({'mono':100,'absolute_deadline_mono':130},30,101)
        self.assertEqual((deadline,work),(130,125))
        self.assertEqual(env['_sdk13_deadline_remaining'](deadline,125,2),2)
        self.assertEqual(env['_sdk13_deadline_remaining'](deadline,129,2),1)
        with self.assertRaises(TimeoutError):env['_sdk13_deadline_remaining'](deadline,130,5)

    def test_expired_setup_cannot_spawn(self):
        with self.assertRaises(TimeoutError):
            env['_sdk13_client_deadlines']({'mono':100,'absolute_deadline_mono':115},30,110)
        for boundary in ({'mono':100,'absolute_deadline_mono':131}, {'mono':100,'absolute_deadline_mono':100}):
            with self.subTest(boundary=boundary),self.assertRaises(RuntimeError):
                env['_sdk13_client_deadlines'](boundary,30,101)

    def test_term_kill_wait_share_same_budget(self):
        remaining=env['_sdk13_deadline_remaining']
        self.assertEqual(remaining(130,125,2),2)
        self.assertEqual(remaining(130,127,10),3)
        self.assertEqual(remaining(130,129.5,10),0.5)
        with self.assertRaises(TimeoutError):remaining(130,130,10)

    def test_source_uses_deadline_before_spawn_and_after_blocking_steps(self):
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Docker')
        call=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='call')
        text=ast.unparse(call)
        self.assertLess(text.index('_sdk13_client_deadlines('),text.index('subprocess.Popen('))
        self.assertNotIn('deadline = time.monotonic() + timeout',text)
        for marker in ('Popen consumed client deadline','identity capture exceeded deadline',
                       'capture fsync exceeded deadline','stream fsync exceeded work deadline',
                       'retirement UNKNOWN'):
            self.assertIn(marker,text)
        retire=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_retire_client')
        rt=ast.unparse(retire)
        self.assertIn('_sdk13_deadline_remaining(',rt)
        self.assertNotIn('timeout=5',rt)
        self.assertIn('client_deadline_overrun',rt)

    def test_containment_emits_absolute_not_relative_deadline(self):
        cls=next(n for n in owner.body if isinstance(n,ast.ClassDef) and n.name=='SDK13Containment')
        gate=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='gate')
        text=ast.unparse(gate)
        self.assertIn('absolute_deadline_mono',text)
        self.assertNotIn('max_call_seconds',text)
        self.assertIn("deadline - mono > 5.0",text)


if __name__=='__main__':unittest.main()
