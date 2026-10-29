"""Functional OS pure compatibility regression; no spawned workloads/signals/guards."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import types
import unittest

D = Path(__file__).resolve().parent
P = D.parent
E = P.parents[1]
OLD_TRANSPORT = E / 'bfd-default-build-normal-retirement-preparation-20261028-1/executor-source-1/image-metadata-profile-correction-source-1/retire_exact_bfd_stopped_container.py'
OLD_LIBELF = E / 'm15-bfd-valid-matched-diagnostic-preparation-20261028-1/newlibelf-collector-root63-preparation-1/libelf-extraction-prep-1'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


transport = module(D / 'retire_exact_bfd_stopped_container.py', 'private_libelf_wait4_compat')
driver = module(P / 'current_consumer_driver.py', 'accepted_serial_consumer')


class RuntimeCompatibilityTests(unittest.TestCase):
    def child(self, status, pid=12345, error=None):
        child = object.__new__(transport.Wait4Child)
        child.pid = 12345
        child.process = types.SimpleNamespace(returncode=None)
        child.returncode = None
        child.started = 1.0
        child.clock = types.SimpleNamespace(time=lambda: 4.0, monotonic=lambda: 3.0)
        child.record = dict(positive_wait4=False)
        calls = []
        def wait4(wanted, flags):
            calls.append((wanted, flags))
            if error is not None: raise error
            return pid, status, types.SimpleNamespace(ru_utime=.2, ru_stime=.1, ru_maxrss=123)
        child.wait4 = wait4
        return child, calls

    def test_shared_converter_handles_real_terminal_status_encodings(self):
        for status, expected in ((0, 0), (37 << 8, 37), (255 << 8, 255), (9, -9), (11 | 128, -11)):
            child, calls = self.child(status)
            self.assertEqual(child.reap(), expected)
            self.assertEqual(child.process.returncode, expected)
            self.assertTrue(child.record['positive_wait4'])
            self.assertEqual(child.record['wait4_pid'], 12345)
            self.assertEqual(child.record['wait4_status'], status)
            self.assertEqual(child.record['user_cpu_seconds'], .2)
            self.assertEqual(child.record['system_cpu_seconds'], .1)
            self.assertEqual(child.record['peak_rss_kib'], 123)
            self.assertEqual(child.reap(), expected)
            self.assertEqual(calls, [(12345, os.WNOHANG)])

    def test_unsupported_or_uncertain_wait_never_becomes_rc0(self):
        for status in ((19 << 8) | 127, 65535):
            child, calls = self.child(status)
            with self.assertRaises(ValueError): child.reap()
            self.assertIsNone(child.returncode)
            self.assertIsNone(child.process.returncode)
            self.assertFalse(child.record['positive_wait4'])
        child, calls = self.child(0, pid=0)
        self.assertIsNone(child.poll())
        self.assertFalse(child.record['positive_wait4'])
        child, calls = self.child(0, pid=99999)
        with self.assertRaises(transport.Refusal): child.reap()
        self.assertIsNone(child.returncode)
        child, calls = self.child(0, error=ChildProcessError('unproven direct wait'))
        with self.assertRaises(ChildProcessError): child.reap()
        self.assertFalse(child.record['positive_wait4'])

    def test_transport_and_libelf_adapter_have_only_bound_minimal_delta(self):
        old = ast.parse(OLD_TRANSPORT.read_bytes())
        current = ast.parse((D / 'retire_exact_bfd_stopped_container.py').read_bytes())
        inserted = [n for n in current.body if isinstance(n, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == 'WAIT_STATUS_COMPAT' for t in n.targets)]
        self.assertEqual(len(inserted), 1)
        current.body.remove(inserted[0])
        changes = 0
        for node in ast.walk(current):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'WAIT_STATUS_COMPAT':
                self.assertEqual(node.attr, 'waitstatus_to_exitcode')
                node.value.id = 'os'
                changes += 1
        self.assertEqual(changes, 1)
        old_directory = next(n for n in old.body if isinstance(n, ast.Assign) and
                             any(isinstance(t, ast.Name) and t.id == 'D' for t in n.targets))
        new_directory = next(n for n in current.body if isinstance(n, ast.Assign) and
                             any(isinstance(t, ast.Name) and t.id == 'D' for t in n.targets))
        self.assertEqual(new_directory.value.args[0].value, str(OLD_TRANSPORT.parent))
        new_directory.value = copy.deepcopy(old_directory.value)
        self.assertEqual(ast.dump(current), ast.dump(old))
        # Retain original frozen transport metadata instead of looking beside
        # this private copy, where the distinct libelf binding resides.
        self.assertIsNone(transport.bindings()['runtime_authority'])
        previous = (OLD_LIBELF / 'created_only_libelf_adapter.py').read_text()
        updated = (D / 'created_only_libelf_adapter.py').read_text()
        old_binding = 'f6670b8f41e08b20a4a9161b5ed6d780df6f8fc498285d5f057e5859437a2975'
        new_binding = transport.reference(D / 'BINDINGS.json')['sha256']
        self.assertEqual(updated.replace(new_binding, old_binding), previous)
        old_data = json.loads((OLD_LIBELF / 'BINDINGS.json').read_bytes())
        new_data = json.loads((D / 'BINDINGS.json').read_bytes())
        self.assertEqual(new_data.pop('capture_transport'), transport.reference(D / 'retire_exact_bfd_stopped_container.py'))
        old_data.pop('capture_transport')
        self.assertEqual(new_data, old_data)

    def test_accepted_capture_namespace_and_serial_positive_predicate_on_declared_runtime(self):
        plan = json.loads((P / 'CONSUMER-PHASE-CONTRACT.SOURCE-ONLY.json').read_bytes())
        plan['cwd_adapter']['path'] = str(P / 'owned_capture_optional_cwd.py')
        namespace = driver.capture_namespace(plan)
        self.assertTrue(callable(namespace['owned_capture']))
        for path in (P / 'current_consumer_driver.py', P / 'owned_capture_optional_cwd.py', Path(plan['capture_helper']['path'])):
            self.assertNotIn('waitstatus_to_exitcode', path.read_text())
        record = dict(returncode=0, direct_child_joined=True, group_absent=True, closed_streams=True,
                      error=None, retirement_error=None, timed_out=False, unexpected_group_members=[])
        self.assertTrue(driver.positive(record))
        for key, value in (('returncode', 3), ('direct_child_joined', False), ('group_absent', False),
                           ('closed_streams', False), ('error', 'failed'), ('retirement_error', 'unknown'),
                           ('timed_out', True), ('unexpected_group_members', [123])):
            self.assertFalse(driver.positive(dict(record, **{key: value})))

    def test_exact_cwd_constructor_explicit_and_omitted_on_python38(self):
        tree = ast.parse((P / 'owned_capture_optional_cwd.py').read_bytes())
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess' and n.func.attr == 'Popen')
        keyword = next(n.value for n in call.keywords if n.arg == 'cwd')
        self.assertEqual(ast.dump(keyword), ast.dump(ast.parse("command.get('cwd')", mode='eval').body))
        for command, expected in ((dict(argv=['fixed'], cwd='/work/link'), '/work/link'), (dict(argv=['fixed']), None)):
            seen = {}
            def popen(*args, **kwargs): seen.update(kwargs)
            context = dict(subprocess=types.SimpleNamespace(Popen=popen, DEVNULL=None), command=command,
                           out=object(), err=object(), child_limits=lambda: None)
            expression = ast.Expression(body=copy.deepcopy(call))
            eval(compile(ast.fix_missing_locations(expression), '<mocked-accepted-Popen>', 'eval'), context)
            self.assertEqual(seen['cwd'], expected)


if __name__ == '__main__': unittest.main(verbosity=2)
