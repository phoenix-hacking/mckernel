import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'docs/verification/evidence/native-exact-tool-image-scratch17-toolimage-1-execution-packet-20261001.py'


def load_packet():
    spec = importlib.util.spec_from_file_location('scratch17_toolimage_packet', PACKET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Scratch17ToolImagePacketTests(unittest.TestCase):
    def test_validate_only_is_side_effect_free_and_binds_exact_profile(self):
        packet = load_packet()
        result = subprocess.run([sys.executable, '-I', '-B', str(PACKET), '--validate-only'],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'PASS_VALIDATE_ONLY')
        self.assertEqual(report['candidate_sha'], '50b084322610a9326b1b7b528edd4cd73b635632')
        self.assertEqual(report['limits']['cpus'], '2-5')
        self.assertEqual(report['limits']['preparation_network'], 'bridge')
        self.assertEqual(report['limits']['offline_network'], 'none')
        self.assertFalse(report['limits']['source_mounts'])
        for path in report['fresh_paths'].values():
            self.assertFalse(Path(path).exists(), path)
        self.assertEqual(packet.validate()['command'], report['command'])

    def test_execute_requires_independent_release_before_subprocess(self):
        packet = load_packet()
        with mock.patch.object(packet.subprocess, 'call', side_effect=AssertionError('must not execute')):
            self.assertEqual(packet.main(['--execute']), 2)

    def test_release_is_bound_to_packet_and_candidate(self):
        packet = load_packet()
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / 'release.json'
            release.write_text(json.dumps({'status': packet.RELEASE_STATUS,
                                           'candidate_sha': packet.CANDIDATE,
                                           'packet_sha256': packet.sha256(PACKET)}))
            with mock.patch.object(packet.subprocess, 'call', return_value=0) as call:
                self.assertEqual(packet.main(['--execute', '--release', str(release)]), 0)
                call.assert_called_once_with(list(packet.COMMAND))
            release.write_text(json.dumps({'status': packet.RELEASE_STATUS,
                                           'candidate_sha': '0' * 40,
                                           'packet_sha256': packet.sha256(PACKET)}))
            with mock.patch.object(packet.subprocess, 'call', side_effect=AssertionError('must not execute')):
                self.assertEqual(packet.main(['--execute', '--release', str(release)]), 2)

    def test_source_hash_mutation_is_fail_closed(self):
        packet = load_packet()
        original = packet.PRODUCER_SHA256
        packet.PRODUCER_SHA256 = '0' * 64
        try:
            with self.assertRaises(packet.PacketError):
                packet.validate()
        finally:
            packet.PRODUCER_SHA256 = original


if __name__ == '__main__':
    unittest.main()
