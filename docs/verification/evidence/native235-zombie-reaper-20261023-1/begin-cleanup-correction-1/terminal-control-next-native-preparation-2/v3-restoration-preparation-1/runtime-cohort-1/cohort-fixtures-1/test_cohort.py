"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure imports, command construction and exact source guards. No child factories,
container calls, source-map history rehash or root publication are exercised.
"""
from pathlib import Path
import ast, hashlib, importlib.util, json, types, unittest

D = Path(__file__).resolve().parent
CURRENT = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/observer227-successor-2/runtime')
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def assignment(path, name):
    return next(ast.literal_eval(n.value) for n in ast.parse(path.read_text()).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))

class CohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner = load('M05_actual_owner', D/'native_diagnostic_container_owner.py')
        cls.runner = load('M05_actual_runner', D/'native_diagnostic_runner.py')
        cls.nd = load('M05_actual_nd', D/'native_diagnostic.py')
        cls.old = load('current_reviewed_owner', CURRENT/'native_diagnostic_container_owner.py')
        cls.cohort = json.loads((D/'EXACT-M05-RUNTIME-COHORT.json').read_text())
        cls.manifest = json.loads((D.parent/'actual-stage-1/manifest.json').read_text())

    def test_real_imports_and_source_local_backend(self):
        diagnostic, backend = self.runner._runtime()
        self.assertEqual(Path(diagnostic.__file__), D/'native_diagnostic.py')
        self.assertEqual(Path(backend.__file__), D/'native_diagnostic_backend.py')
        self.assertTrue(callable(self.owner.DiagnosticOwner._create_argv))

    def test_owner_ownership_and_normal_cleanup_AST_unchanged(self):
        def classes(path):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)}
        self.assertEqual(classes(CURRENT/'native_diagnostic_container_owner.py'), classes(D/'native_diagnostic_container_owner.py'))

    def test_exact_135_historical_rows_reused_without_rehash(self):
        rows = assignment(CURRENT/'native_diagnostic_container_owner.py', 'SOURCE_HASHES')
        historical = {p: value for p, value in rows.items() if not p.startswith(str(CURRENT)+'/')}
        self.assertEqual(len(historical), 135)
        self.assertEqual(historical, self.cohort['historical_source_rows_reused_without_rehash'])
        self.assertTrue(all(self.owner.SOURCE_HASHES[path] == value for path, value in historical.items()))

    def test_actual_typed_hook_source_guards(self):
        for path, expected in self.cohort['typed_hook_source_entries'].items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), expected)
            self.assertEqual(self.owner.SOURCE_HASHES[path], expected)
        self.assertEqual(len(self.owner.SOURCE_HASHES), 149)

    def owner_state(self, module, digest):
        # This invokes only pure argument construction, without constructor,
        # manifest acquisition, locks, commands or workload factories.
        obj = object.__new__(module.DiagnosticOwner)
        obj.parent = Path('/home/holden/mckernel-work/scratch/nm05p5a1/p')
        obj.nonce = '495e2edd278e4733ae4d17476cb93831'
        obj.name = 'mckernel-native-diagnostic-' + obj.nonce
        obj.label = 'mckernel.native-diagnostic.owner=' + obj.nonce
        obj.owner_sha = digest
        obj.manifest_path = '/home/holden/mckernel-work/scratch/nm05p5a1/m.json'
        obj.manifest_sha256 = '8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7'
        return obj

    def test_actual_create_argv_current_profile_and_added_readonly_roots(self):
        newsha = hashlib.sha256((D/'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
        new = self.owner_state(self.owner, newsha)._create_argv()
        old = self.owner_state(self.old, '251acc456d5c7f6b563cb8e41feeb7e095c8098c1a780c44338f2157d357b0e6')._create_argv()
        normalized = list(new)
        for path in self.cohort['added_readonly_roots']:
            mount = 'type=bind,src=' + path + ',dst=' + path + ',readonly'
            index = normalized.index(mount)
            self.assertEqual(normalized[index-1], '--mount')
            del normalized[index-1:index+1]
        normalized = [str(CURRENT/'native_diagnostic_container_owner.py') if value == str(D/'native_diagnostic_container_owner.py') else '251acc456d5c7f6b563cb8e41feeb7e095c8098c1a780c44338f2157d357b0e6' if value == newsha else value for value in normalized]
        self.assertEqual(normalized, old)
        self.assertIn('--cpuset-cpus=2-5', new)
        self.assertIn('--memory=12g', new)
        self.assertIn('--network=none', new)

    def test_actual_two_generation_QEMU_argv(self):
        manifest = self.manifest
        self.assertEqual(hashlib.sha256((D.parent/'actual-stage-1/manifest.json').read_bytes()).hexdigest(), '8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7')
        argv = self.nd.expected_qemu_argv(manifest, Path('/home/holden/mckernel-work/scratch/nm05p5a1/p/attempt-495e2edd278e4733ae4d17476cb93831'))
        self.assertEqual(argv[argv.index('-smp')+1], '4,sockets=2,cores=2,threads=1')
        self.assertEqual(argv[argv.index('-m')+1], '8192')
        self.assertEqual(argv[argv.index('-initrd')+1], manifest['staging']['derived_initramfs']['path'])
        self.assertEqual(argv[argv.index('-kernel')+1], manifest['artifacts']['bzImage']['path'])
        socket = argv[argv.index('-qmp')+1].split(':', 1)[1].split(',', 1)[0]
        self.assertLess(len(socket.encode()), 108)

    def test_runner_rejects_foreign_diagnostic_before_hook(self):
        with self.assertRaisesRegex(ValueError, 'private diagnostic binding'):
            self.runner._bind_m05(types.SimpleNamespace(__file__='/foreign/native_diagnostic.py'), self.manifest, '/foreign/m.json')

    def test_real_hook_rejects_wrong_manifest_source(self):
        with self.assertRaisesRegex(ValueError, 'exact normalized manifest'):
            self.runner._bind_m05(self.nd, self.manifest, '/foreign/m.json')

if __name__ == '__main__':
    unittest.main(verbosity=2)
