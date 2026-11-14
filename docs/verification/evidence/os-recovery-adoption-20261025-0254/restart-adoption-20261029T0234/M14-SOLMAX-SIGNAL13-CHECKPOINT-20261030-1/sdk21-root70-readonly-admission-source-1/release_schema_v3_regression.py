"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source-level regression/preseal schema check. No observer or privileged operation.
This check supplies no release, current controls, source identity or live-service proof.
"""
import ast
import json
from pathlib import Path
import sys
import types
import unittest

PARENT = Path(__file__).with_name('root_observer_direct_parent_v3.py')
tree = ast.parse(PARENT.read_text(encoding='utf8'), filename=str(PARENT))
names = {'TIME_UTC', 'TIME_BOOT', 'TIME_MONO', 'EXPECTED_CAPS', 'REQUIRED_RELEASE_KEYS'}
constant_nodes = [node for node in tree.body if isinstance(node, ast.Assign)
                  and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                  and node.targets[0].id in names]
assert {node.targets[0].id for node in constant_nodes} == names
constants = {}
exec(compile(ast.fix_missing_locations(ast.Module(body=constant_nodes, type_ignores=[])),
             str(PARENT), 'exec'), constants)
REQUIRED = constants['REQUIRED_RELEASE_KEYS']
CAPS = constants['EXPECTED_CAPS']


def preseal_check(value):
    if not isinstance(value, dict):
        raise ValueError('release must be a JSON object')
    missing = REQUIRED - value.keys()
    if missing:
        raise ValueError('missing required release keys: ' + ', '.join(sorted(missing)))
    if value['service_status'] != 'NO_NEW_REJECTION':
        raise ValueError('service_status mismatch')
    if value['actual_tighter_caps'] != CAPS:
        raise ValueError('actual_tighter_caps mismatch')
    return True


def mock_validator(value):
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == 'validate_sealed']
    assert len(nodes) == 1
    observer_sha = 'b5a1bc9c4b49142cddee82c1df49b356d5d0972f71acda0146f3a34baa6c9f13'
    packet_sha = 'fca24f38dc603f2b4f04708ec5be890ded7cd22efd7a845850a692797d63e39e'
    refs = {'parent.py': 'a' * 64, 'observer': observer_sha, 'packet': packet_sha,
            'controls': 'b' * 64, 'capacity': 'c' * 64}
    def digest(path, limit):
        return {'sha256': refs[str(path)]}
    state = {'root': value, 'bytes': b'root bytes', 'identity': {'device': 3, 'inode': 4}}
    def root_release(path):
        return state['root'], state['identity'], state['bytes']
    fake_time = types.SimpleNamespace(time=lambda: 1000, monotonic=lambda: 40,
                                      clock_gettime=lambda clock: 50, CLOCK_BOOTTIME=7)
    env = dict(constants, root_release=root_release, digest=digest, time=fake_time,
               Path=Path, __file__='parent.py', RELEASE=Path('release'),
               OBSERVER=Path('observer'), OBSERVER_SHA=observer_sha,
               PACKET=Path('packet'), PACKET_SHA=packet_sha,
               CONTROLS=Path('controls'), CAPACITY=Path('capacity'))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 str(PARENT), 'exec'), env)
    return env['validate_sealed'], state


def example():
    return {'status': 'ROOT_RELEASE_EXACT_OBSERVER_ONLY',
            'operation': 'root70-readonly-observer-v1', 'parent_sha256': 'a' * 64,
            'observer_sha256': 'b5a1bc9c4b49142cddee82c1df49b356d5d0972f71acda0146f3a34baa6c9f13',
            'packet_sha256': 'fca24f38dc603f2b4f04708ec5be890ded7cd22efd7a845850a692797d63e39e',
            'paid_fallback': False, 'weekly_used_percent': 67,
            'service_status': 'NO_NEW_REJECTION', 'controls_sha256': 'b' * 64,
            'capacity_sha256': 'c' * 64, 'weekly_observed_utc': 999,
            'expiry_utc': 1010, 'operation_nonce': 'a' * 32,
            'actual_tighter_caps': dict(CAPS)}


class SealedRegression(unittest.TestCase):
    def test_complete_schema_and_mocked_actual_validator(self):
        value = example()
        self.assertTrue(preseal_check(value))
        validate, _ = mock_validator(value)
        validate()

    def test_each_required_key_including_service_rejected_before_seal(self):
        for key in REQUIRED:
            with self.subTest(key=key):
                value = example()
                del value[key]
                with self.assertRaises(ValueError):
                    preseal_check(value)
                validate, _ = mock_validator(value)
                with self.assertRaises(ValueError):
                    validate()

    def test_changed_caps_or_service_rejected(self):
        for key, bad in [('actual_tighter_caps', {}), ('service_status', 'UNKNOWN')]:
            value = example()
            value[key] = bad
            with self.assertRaises(ValueError):
                preseal_check(value)
            validate, _ = mock_validator(value)
            with self.assertRaises(ValueError):
                validate()

    def test_second_validation_rejects_release_bytes_or_identity_change(self):
        validate, state = mock_validator(example())
        sealed, _ = validate()
        state['bytes'] = b'different bytes'
        with self.assertRaises(ValueError):
            validate(sealed)
        state['bytes'] = b'root bytes'
        state['identity'] = {'device': 3, 'inode': 5}
        with self.assertRaises(ValueError):
            validate(sealed)

    def test_expiry_and_consumed_nonce_rejected(self):
        for key, bad in [('expiry_utc', 999), ('operation_nonce', '5732bbe86da94491884b8b18a020f2ea')]:
            value = example()
            value[key] = bad
            validate, _ = mock_validator(value)
            with self.assertRaises(ValueError):
                validate()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--check-input':
        preseal_check(json.loads(Path(sys.argv[2]).read_text(encoding='utf8')))
        print('SCHEMA_COMPLETE_ONLY_NOT_AUTHORITY')
    else:
        unittest.main()
