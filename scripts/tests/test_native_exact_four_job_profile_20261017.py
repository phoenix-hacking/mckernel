"""Later-candidate four-job change: exact diff and shell syntax, no build."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/native-rust-host-modules-exact-build.yml'
ORIGINAL_SHA256 = '030822f476e5aaa290b06255d3e874dbf584760e06a221b2dd15ed9332ed8629'
DRIVER_SHA256 = 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a'
OWNER_SHA256 = '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
EDITS = (
    ('                -j2 bzImage\n', '                -j4 bzImage\n'),
    ('                -j2 "${module_targets[@]}"\n', '                -j4 "${module_targets[@]}"\n'),
)


def proposed_workflow():
    """Keep the authority-blocked patch disposable, never modify production."""
    source = WORKFLOW.read_text()
    if hashlib.sha256(source.encode()).hexdigest() != ORIGINAL_SHA256:
        raise AssertionError('unchanged baseline required for disposable proposal')
    for old, new in EDITS:
        if source.count(old) != 1:
            raise AssertionError('unique original command required')
        source = source.replace(old, new, 1)
    return source


class FourJobProfile(unittest.TestCase):
    def test_exactly_two_bounded_make_arguments_changed(self):
        current = proposed_workflow()
        original = current
        for old, new in EDITS:
            self.assertEqual(current.count(new), 1)
            self.assertNotIn(old, current)
            original = original.replace(new, old, 1)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(), ORIGINAL_SHA256)

    def test_actual_canonical_workflow_bodies_and_bash_syntax(self):
        driver_path = ROOT / 'scripts/native_rust_exact_build_offline.py'
        self.assertEqual(hashlib.sha256(driver_path.read_bytes()).hexdigest(), DRIVER_SHA256)
        spec = importlib.util.spec_from_file_location('four_job_driver', driver_path)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        bodies = driver.workflow_bodies(proposed_workflow())
        compile_body = bodies[driver.STEPS[3]]
        self.assertEqual(compile_body.count('-j4 '), 2)
        self.assertIn('-j4 bzImage\n', compile_body)
        self.assertIn('-j4 "${module_targets[@]}"\n', compile_body)
        self.assertNotIn('nproc', compile_body)
        for name, body in bodies.items():
            result = subprocess.run(['/usr/bin/bash', '--noprofile', '--norc', '-n'],
                                    input=body, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=10,
                                    env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
            self.assertEqual(result.returncode, 0, name + ': ' + result.stderr)

    def test_original_external_profile_is_byte_identical(self):
        owner = ROOT / 'scripts/native_rust_exact_build_container_owner.py'
        self.assertEqual(hashlib.sha256(owner.read_bytes()).hexdigest(), OWNER_SHA256)
        tree = ast.parse(owner.read_text())
        resource_args = next(ast.literal_eval(node.value) for node in tree.body
                             if isinstance(node, ast.Assign) and any(
                                 isinstance(target, ast.Name) and target.id == 'RESOURCE_ARGS'
                                 for target in node.targets))
        self.assertEqual(resource_args, ['--cpus=4', '--cpuset-cpus=2-5', '--memory=12g',
                                         '--memory-swap=12g', '--pids-limit=512'])


if __name__ == '__main__':
    unittest.main()
