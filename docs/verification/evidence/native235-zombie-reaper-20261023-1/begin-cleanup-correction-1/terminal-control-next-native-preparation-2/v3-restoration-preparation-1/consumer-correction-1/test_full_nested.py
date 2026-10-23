"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Controlled derivatives of one retained accepted full two-generation observation.
Every test calls the actual full nested consumer; no validators are mocked.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import unittest

D = Path(__file__).resolve().parent
BASE = Path('/home/holden/mckernel/docs/verification/evidence/p-m05-current68-first-complete-restoration-20261022-1/actual-guest')
MANIFEST = D.parent/'actual-stage-1/manifest.json'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def begin_fixture(serial):
    """Replace only two release rows; preserve actual ACK/resource bytes."""
    lines = serial.splitlines(keepends=True)
    schedules = re.findall(r'application SCHEDULE os=0 generation=([12]) pid=(\d+) cpu=0\r?$', serial, re.M)
    if len(schedules) != 2 or {g for g, _ in schedules} != {'1', '2'}:
        raise ValueError('one scheduled identity per retained epoch required')
    replaced = set()
    for generation, pid in schedules:
        identity = 'os=0 generation=' + generation + ' pid=' + pid
        acknowledgements = [line for line in lines if re.search(
            r'application cleanup ACK ' + re.escape(identity) + r' token=\d+ errno=0 abandoned=[01]\r?\n$', line)]
        release = [i for i, line in enumerate(lines) if re.search(
            r'mcctrl: application_process=release ' + re.escape(identity) + r' cleanup_errno=0\r?\n$', line)]
        if len(acknowledgements) != 1 or len(release) != 1:
            raise ValueError('one actual ACK and one original release per scheduled epoch required')
        index = release[0]
        original = lines[index]
        lines[index] = original.replace('application_process=release ', 'application_process=cleanup_requested ', 1).replace(' cleanup_errno=0', ' intent_errno=0', 1)
        replaced.add(index)
    before = serial.splitlines(keepends=True)
    if len(replaced) != 2 or any(old != new for i, (old, new) in enumerate(zip(before, lines)) if i not in replaced):
        raise ValueError('only exact two release rows may change')
    return ''.join(lines)

def mutate_ack(serial, generation, mutation):
    schedules = re.findall(r'application SCHEDULE os=0 generation=' + str(generation) + r' pid=(\d+) cpu=0\r?$', serial, re.M)
    if len(schedules) != 1:
        raise ValueError('one target scheduled PID required')
    identity = 'os=0 generation=' + str(generation) + ' pid=' + schedules[0]
    lines = serial.splitlines(keepends=True)
    targets = [i for i, line in enumerate(lines) if re.search(
        r'application cleanup ACK ' + re.escape(identity) + r' token=\d+ errno=0 abandoned=[01]\r?\n$', line)]
    if len(targets) != 1:
        raise ValueError('exactly one actual matched ACK mutation required')
    index = targets[0]
    original = lines[index]
    lines[index] = mutation(original)
    if lines[index] == original:
        raise ValueError('ACK mutation must change exactly one matched row')
    return ''.join(lines)

def mutate_counter(serial, family):
    lines = serial.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(family + '_CHUNK '):
            row = json.loads(line.split(' ', 1)[1])
            if row['name'] != 'stdout':
                continue
            raw = bytes.fromhex(row['hex'])
            if b'134217728' in raw:
                row['hex'] = raw.replace(b'134217728', b'134217729', 1).hex()
                lines[i] = family + '_CHUNK ' + json.dumps(row, separators=(',', ':')) + '\n'
                return ''.join(lines)
    raise ValueError('known physical memory byte counter not present')

class FullNestedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.consumer = load('actual_full_second_stop', D/'second_stop_capture.py')
        cls.original = load('original_full_second_stop', D/'original/second_stop_capture.py')
        cls.observation = json.loads((BASE/'result.json').read_text())['observation']
        cls.serial = (BASE/'serial.log').read_bytes().decode('utf-8')
        if cls.observation['serial'] != cls.serial:
            raise ValueError('baseline raw observation/serial differs')
        cls.manifest = json.loads(MANIFEST.read_text())
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != '8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7':
            raise ValueError('actual manifest source binding')
        cls.legacy = copy.deepcopy(cls.manifest)
        cls.legacy.pop('cleanup_profile')
        cls.begin_serial = begin_fixture(cls.serial)

    def evaluate(self, serial, begin=True, original=False):
        observation = dict(self.observation, serial=serial)
        consumer = self.original if original else self.consumer
        return consumer.evaluate(self.manifest if begin else self.legacy, observation)

    def rejects(self, serial, begin=True):
        with self.assertRaises((ValueError, RuntimeError, KeyError)):
            self.evaluate(serial, begin)

    def test_legacy_original_and_successor_full_nested_equal(self):
        self.assertEqual(self.evaluate(self.serial, False, True), self.evaluate(self.serial, False))

    def test_begin_full_nested_preserves_all_resource_results(self):
        old = self.evaluate(self.serial, False)
        new = self.evaluate(self.begin_serial)
        self.assertEqual(old, new)
        self.assertTrue(new['second_stop_verified'])
        self.assertTrue(new['second_public_release_verified'])
        self.assertFalse(new['native_execution_verified'])
        self.assertFalse(new['complete_restoration_verified'])
        self.assertFalse(new['quota_credit'])

    def test_missing_intent_each_epoch(self):
        for generation in (1, 2):
            with self.subTest(generation=generation):
                changed, count = re.subn(r'^.*application_process=cleanup_requested os=0 generation=' + str(generation) + r' .*\n', '', self.begin_serial, flags=re.M)
                self.assertEqual(count, 1)
                self.rejects(changed)

    def test_missing_ack_each_epoch(self):
        for generation in (1, 2):
            with self.subTest(generation=generation):
                self.rejects(mutate_ack(self.begin_serial, generation, lambda line: ''))

    def test_wrong_pid_each_epoch(self):
        for generation in (1, 2):
            with self.subTest(generation=generation):
                def foreign(line):
                    changed, count = re.subn(r' pid=\d+ ', ' pid=9999 ', line)
                    self.assertEqual(count, 1)
                    return changed
                self.rejects(mutate_ack(self.begin_serial, generation, foreign))

    def test_wrong_generation_ack(self):
        self.rejects(mutate_ack(self.begin_serial, 2, lambda line: line.replace(' generation=2 ', ' generation=3 ', 1)))

    def test_duplicate_actual_ack_each_epoch(self):
        for generation in (1, 2):
            with self.subTest(generation=generation):
                self.rejects(mutate_ack(self.begin_serial, generation, lambda line: line + line))

    def test_retirement_before_ack_each_epoch(self):
        for generation in (1, 2):
            with self.subTest(generation=generation):
                lines = self.begin_serial.splitlines(keepends=True)
                ack = next(i for i, line in enumerate(lines) if 'application cleanup ACK os=0 generation=' + str(generation) + ' ' in line)
                retirement = next(i for i, line in enumerate(lines) if 'application retirement os=0 generation=' + str(generation) + ' ' in line)
                lines[ack], lines[retirement] = lines[retirement], lines[ack]
                self.rejects(''.join(lines))

    def test_physical_counter_wrong_both_releases(self):
        for family in ('ND_RESOURCE', 'ND_SECOND_RESOURCE'):
            with self.subTest(family=family):
                self.rejects(mutate_counter(self.begin_serial, family))

    def test_legacy_controls_remain_strict(self):
        self.rejects(re.sub(r'^.*application_process=release os=0 generation=2 .*\n', '', self.serial, flags=re.M), False)
        self.rejects(mutate_counter(self.serial, 'ND_SECOND_RESOURCE'), False)

    def test_undeclared_begin_cannot_replace_legacy(self):
        self.rejects(self.begin_serial, False)

    def test_begin_cannot_fake_legacy_release(self):
        self.rejects(self.serial)

    def test_profile_identity_is_strict(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['cleanup_profile']['id'] = 'unknown'
        with self.assertRaises((ValueError, RuntimeError)):
            self.consumer.evaluate(manifest, dict(self.observation, serial=self.begin_serial))

if __name__ == '__main__':
    unittest.main(verbosity=2)
