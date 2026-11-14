#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure observer mocks: replace all proc transport OS operations before calling it.
No LocalOps, actual proc read, pidfd, signals, flock or shared record operations.
"""
import ast
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'failed_validation_recovery.proc-eof-correction1.py'
SPEC = importlib.util.spec_from_file_location('owner15_proc_eof', SOURCE)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)
TARGET = b'102: FLOCK  ADVISORY  WRITE 997661 00:1b:4 0 EOF\n'
OTHER = b'1: POSIX ADVISORY READ 5 08:01:99 0 EOF\n'


class MockProcOS:
    O_RDONLY = os.O_RDONLY
    O_NOFOLLOW = os.O_NOFOLLOW
    O_CLOEXEC = os.O_CLOEXEC
    O_NONBLOCK = os.O_NONBLOCK

    def __init__(self, chunks, error_after=None):
        self.chunks = list(chunks)
        self.opened, self.closed, self.reads = [], [], []
        self.returned_bytes = 0
        self.error_after = error_after

    def open(self, path, flags):
        if path != '/proc/locks':
            raise AssertionError('pure fixture attempted an unexpected observation path')
        self.opened.append((path, flags))
        return 77

    def read(self, fd, maximum):
        if fd != 77 or maximum <= 0:
            raise AssertionError('invalid mock descriptor/read bound')
        if self.error_after is not None and len(self.reads) == self.error_after:
            raise OSError('mock read failure')
        self.reads.append(maximum)
        if not self.chunks:
            return b''
        chunk = self.chunks[0]
        raw = chunk[:maximum]
        self.returned_bytes += len(raw)
        if len(raw) == len(chunk):
            self.chunks.pop(0)
        else:
            self.chunks[0] = chunk[len(raw):]
        return raw

    def close(self, fd):
        if fd != 77:
            raise AssertionError('unexpected mock close')
        self.closed.append(fd)


class EofObserverTests(unittest.TestCase):
    def algorithms(self):
        # Reads only the immutable reviewed source to define functions. No
        # selected function executes until proc_bytes is fully mocked below.
        return recovery.reviewed_algorithms()

    def parse(self, chunks):
        fake = MockProcOS(chunks)
        algorithms = self.algorithms()
        with mock.patch.object(recovery, 'os', fake):
            result = algorithms['require_lock_holder'](997661)
        self.assertEqual(fake.closed, [77])
        return result, fake

    def test_short_reads_across_target_row_preserve_exact_holder(self):
        rows, fake = self.parse([OTHER, TARGET[:11], TARGET[11:30], TARGET[30:], b''])
        self.assertEqual(rows, [['FLOCK', 'ADVISORY', 'WRITE', '997661', '00:1b:4', '0', 'EOF']])
        self.assertEqual(len(fake.reads), 5)
        self.assertEqual(fake.opened, [('/proc/locks', os.O_RDONLY | os.O_NOFOLLOW
                                      | os.O_CLOEXEC | os.O_NONBLOCK)])

    def test_one_byte_chunks_are_not_eof(self):
        rows, fake = self.parse([bytes([value]) for value in TARGET])
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(fake.reads), len(TARGET) + 1)

    def test_actual_readonly_counterexample_legacy_fails_complete_passes(self):
        observed = json.loads((ROOT / 'ACTUAL-PROC-LOCKS-READONLY-DIAGNOSTIC.stdout').read_text())
        self.assertTrue(observed['short_read_omitted_target'])
        raw = bytes.fromhex(observed['raw_hex'])
        first = observed['legacy_first_read_bytes']
        rows, _ = self.parse([raw[:first], raw[first:], b''])
        self.assertEqual(len(rows), 1)
        tree = ast.parse(recovery.REFERENCE.read_text())
        original = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'proc_bytes')
        fake = MockProcOS([raw[:first], raw[first:], b''])
        namespace = dict(os=fake, Refusal=recovery.Refusal)
        exec(compile(ast.Module(body=[original], type_ignores=[]), '<original-proc-bytes>', 'exec'),
             namespace)
        legacy_raw = namespace['proc_bytes']('/proc/locks', 1 << 20)
        self.assertEqual(legacy_raw, raw[:first])
        self.assertNotIn(b'997661 00:1b:4', legacy_raw)
        self.assertEqual(len(fake.reads), 1)

    def test_true_eof_and_exact_limit(self):
        for chunks, limit, expected, reads in [([b''], 0, b'', 1),
                                                ([b'ab', b'cd', b''], 4, b'abcd', 3),
                                                ([b'abcd', b''], 4, b'abcd', 2)]:
            fake = MockProcOS(chunks)
            with mock.patch.object(recovery, 'os', fake):
                self.assertEqual(recovery.proc_bytes_complete('/proc/locks', limit), expected)
            self.assertEqual(len(fake.reads), reads)
            self.assertEqual(fake.closed, [77])

    def test_maximum_plus_one_overflow_remains_rejected(self):
        for chunks in ([b'abcde'], [b'ab', b'cd', b'e']):
            fake = MockProcOS(chunks)
            with mock.patch.object(recovery, 'os', fake):
                with self.assertRaisesRegex(recovery.Refusal, 'exceeds bound'):
                    recovery.proc_bytes_complete('/proc/locks', 4)
            self.assertEqual(fake.closed, [77])
            self.assertEqual(fake.returned_bytes, 5, 'only original maximum+1 bytes consumed')

    def test_duplicate_missing_wrong_holder_or_lock_mode_still_rejected(self):
        for raw in (TARGET + TARGET, OTHER, TARGET.replace(b'997661', b'997662'),
                    TARGET.replace(b'WRITE', b'READ'), TARGET.replace(b'00:1b:4', b'00:1b:5')):
            with self.subTest(raw=raw):
                fake = MockProcOS([raw[:7], raw[7:], b''])
                algorithms = self.algorithms()
                with mock.patch.object(recovery, 'os', fake):
                    with self.assertRaises(recovery.Refusal):
                        algorithms['require_lock_holder'](997661)
                self.assertEqual(fake.closed, [77])

    def test_malformed_rows_still_rejected_after_complete_read(self):
        for raw in (b'bad row\n', TARGET + b'incomplete\n',
                    TARGET.replace(b'00:1b:4', b'bad-device')):
            fake = MockProcOS([raw[:5], raw[5:], b''])
            algorithms = self.algorithms()
            with mock.patch.object(recovery, 'os', fake):
                with self.assertRaises((recovery.Refusal, ValueError)):
                    algorithms['require_lock_holder'](997661)
            self.assertEqual(fake.closed, [77])

    def test_read_error_closes_fd_without_returning_truncated_success(self):
        fake = MockProcOS([OTHER], error_after=1)
        with mock.patch.object(recovery, 'os', fake):
            with self.assertRaises(OSError):
                recovery.proc_bytes_complete('/proc/locks', 1 << 20)
        self.assertEqual(fake.closed, [77])

    def test_only_transport_definition_and_binding_changed(self):
        original = ast.parse((ROOT / 'failed_validation_recovery.py').read_text())
        corrected = ast.parse(SOURCE.read_text())
        corrected.body = [node for node in corrected.body if not (
            isinstance(node, ast.FunctionDef) and node.name == 'proc_bytes_complete')]
        algorithms = next(node for node in corrected.body if isinstance(node, ast.FunctionDef)
                          and node.name == 'reviewed_algorithms')
        algorithms.body = [node for node in algorithms.body if not (
            isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Subscript)
            and isinstance(node.value, ast.Name) and node.value.id == 'proc_bytes_complete')]
        self.assertEqual(ast.dump(original, include_attributes=False),
                         ast.dump(corrected, include_attributes=False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
