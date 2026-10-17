"""Actual collector profile/serializer admission; selected captures are replay only.

Set ND_COLLECTOR_MANIFEST_SELECTION to a hash-bound selection JSON for the
campaign manifests and retained TLS capture. No PID-1 collector is executed.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'scripts/application-tests/native_diagnostic_guest_collector.c'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bound_bytes(ref):
    raw = Path(ref['path']).read_bytes()
    if digest(raw) != ref['sha256']:
        raise ValueError('selected input hash differs')
    return raw


def check_contract(manifest, producer):
    payload = manifest['payload']
    for key in ('argv', 'env', 'cwd'):
        if payload[key] != producer[key]:
            raise ValueError('collector/manifest payload ' + key)
    for stream in ('stdout', 'stderr'):
        if payload[stream + '_limit_bytes'] != producer['streams'][stream]['limit']:
            raise ValueError('collector/manifest stream accounting')


class CollectorManifestLimitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection_path = os.environ.get('ND_COLLECTOR_MANIFEST_SELECTION')
        cls.selection = json.loads(Path(cls.selection_path).read_bytes()) if cls.selection_path else None
        retained = os.environ.get('ND_COLLECTOR_MANIFEST_EVIDENCE')
        cls.temp = None if retained else tempfile.TemporaryDirectory()
        cls.work = Path(retained if retained else cls.temp.name)
        cls.work.mkdir(mode=0o700, parents=True, exist_ok=True)
        cls.outputs = {}
        source_hash = digest(SOURCE.read_bytes())
        wrapper = '#define main collector_pid1_main\n#include ' + json.dumps(str(SOURCE)) + r'''
#undef main
int main(void)
{
    struct result r = {0};
    char output[FRAME_LIMIT];
    r.clean = 1; r.out.eof = 1; r.err.eof = 1;
    r.started = 1; r.reaped = 2; r.finished = 3;
    printf("STREAM_LIMIT=%u\nARGV", STREAM_LIMIT);
    for (size_t i = 0; payload_argv[i]; ++i) printf("\t%s", payload_argv[i]);
    printf("\nENV");
    for (size_t i = 0; payload_env[i]; ++i) printf("\t%s", payload_env[i]);
    printf("\n");
    int n = frame(output, &r, 1);
    if (n <= 0 || fwrite(output, 1, (size_t)n, stdout) != (size_t)n) return 2;
    return 0;
}
'''
        for profile, flags in (('default', []), ('futex', ['-DND_FUTEX'])):
            source = cls.work / (profile + '-wrapper.c')
            binary = cls.work / (profile + '-wrapper')
            source.write_text(wrapper)
            argv = ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', *flags,
                    str(source), '-o', str(binary)]
            cls.command(profile + '-compile', argv, 30)
            raw = cls.command(profile + '-constants', [str(binary)], 5)
            lines = raw.decode().splitlines()
            limit = int(lines[0].split('=', 1)[1])
            actual_argv = lines[1].split('\t')[1:]
            actual_env = dict(item.split('=', 1) for item in lines[2].split('\t')[1:])
            frame = json.loads(lines[3].removeprefix('ND_PAYLOAD ')) if hasattr(str, 'removeprefix') else json.loads(lines[3][len('ND_PAYLOAD '):])
            if (actual_argv != frame['argv'] or actual_env != frame['env'] or
                    any(frame['streams'][s]['limit'] != limit for s in ('stdout', 'stderr'))):
                raise AssertionError('actual producer constants/serializer disagree')
            cwd = re.findall(r'supervise\("/bin/mcexec",\s*payload_argv,\s*payload_env,\s*"([^"]+)"', SOURCE.read_text())
            if cwd != [frame['cwd']]:
                raise AssertionError('actual supervise cwd/serializer disagree')
            cls.outputs[profile] = frame
        if digest(SOURCE.read_bytes()) != source_hash:
            raise AssertionError('collector source changed during checks')

    @classmethod
    def command(cls, label, argv, timeout):
        env = dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C', TMPDIR=str(cls.work))
        result = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, timeout=timeout, check=False)
        (cls.work / (label + '.stdout')).write_bytes(result.stdout)
        (cls.work / (label + '.stderr')).write_bytes(result.stderr)
        (cls.work / (label + '.json')).write_text(json.dumps(dict(argv=argv, env=env,
            exit_code=result.returncode, stdout_sha256=digest(result.stdout),
            stderr_sha256=digest(result.stderr)), sort_keys=True, indent=2) + '\n')
        if result.returncode:
            raise AssertionError(label + ' failed; evidence retained')
        return result.stdout

    @classmethod
    def tearDownClass(cls):
        if cls.temp is not None:
            cls.temp.cleanup()

    def test_actual_default_and_futex_profile_limits(self):
        for profile, limit in (('default', 1024), ('futex', 4096)):
            self.assertEqual(self.outputs[profile]['streams']['stdout']['limit'], limit)
            self.assertEqual(self.outputs[profile]['streams']['stderr']['limit'], limit)

    def test_profile_admission_rejects_original_tls_limit(self):
        producer = self.outputs['futex']
        old = dict(payload={k: producer[k] for k in ('argv', 'env', 'cwd')})
        old['payload'].update(stdout_limit_bytes=1024, stderr_limit_bytes=1024)
        with self.assertRaisesRegex(ValueError, 'stream accounting'): check_contract(old, producer)
        corrected = copy.deepcopy(old)
        corrected['payload'].update(stdout_limit_bytes=4096, stderr_limit_bytes=4096)
        check_contract(corrected, producer)

    def selected(self):
        if self.selection is None:
            self.skipTest('campaign manifest selection not supplied; generic profiles still compiled')
        return {key: json.loads(bound_bytes(self.selection[key]))
                for key in ('original_tls', 'corrected_tls', 'default_signal')}

    def test_selected_actual_manifests_full_payload_contract(self):
        selected = self.selected()
        check_contract(selected['default_signal'], self.outputs['default'])
        check_contract(selected['corrected_tls'], self.outputs['futex'])
        with self.assertRaisesRegex(ValueError, 'stream accounting'):
            check_contract(selected['original_tls'], self.outputs['futex'])
        reconstructed = copy.deepcopy(selected['original_tls'])
        reconstructed['payload'].update(stdout_limit_bytes=4096, stderr_limit_bytes=4096)
        self.assertEqual(reconstructed, selected['corrected_tls'])

    def test_retained_actual_tls_serializer_to_frozen_evaluator(self):
        selected = self.selected()
        ref = self.selection['evaluator']
        bound_bytes(ref)
        spec = importlib.util.spec_from_file_location('collector_manifest_frozen_evaluator', ref['path'])
        evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator)
        raw_tar = bound_bytes(self.selection['tls_attempt_archive'])
        import io
        with tarfile.open(fileobj=io.BytesIO(raw_tar), mode='r:') as tar:
            serial = tar.extractfile('./serial.log').read().decode()
            debugcon = tar.extractfile('./debugcon.log').read().decode()
            transcript = json.loads(tar.extractfile('./qmp.transcript.json').read())
            result = json.loads(tar.extractfile('./result.json').read())
        times = [item['monotonic'] for item in transcript]
        guest_shutdown, host_quit, terminal_status = [], [], []
        for item in transcript:
            for line in bytes.fromhex(item['raw_hex']).splitlines():
                message = json.loads(line)
                if item['direction'] == 'received':
                    if message.get('event') == 'SHUTDOWN' and message.get('data', {}).get('guest') is True:
                        guest_shutdown.append(item['monotonic'])
                    if message.get('return', {}).get('status') == 'shutdown':
                        terminal_status.append(item['monotonic'])
                elif item['direction'] == 'sent' and message.get('execute') == 'quit':
                    host_quit.append(item['monotonic'])
        self.assertTrue(guest_shutdown and terminal_status and host_quit)
        self.assertLess(min(guest_shutdown), min(host_quit))
        self.assertLessEqual(min(guest_shutdown), min(terminal_status))
        self.assertLess(max(terminal_status), min(host_quit))
        evidence = result['qemu_evidence']
        observation = dict(serial=serial, debugcon=debugcon, qmp={'status': 'shutdown'}, teardown=True,
                           started_at=min(times), finished_at=max(times) + 1,
                           deadline=min(times) + 300, qemu_evidence=evidence,
                           process_identity={k: evidence[k] for k in ('pid', 'pgid', 'sid', 'starttime_ticks')})
        with self.assertRaisesRegex(evaluator.DiagnosticError, '^stream accounting$'):
            evaluator.evaluate(selected['original_tls'], observation)
        replay = evaluator.evaluate(selected['corrected_tls'], observation)
        self.assertEqual(replay['status'], 'PROTOCOL_PASS')
        self.assertFalse(replay['application_acceptance'])
        self.assertFalse(replay['mckernel_application_executed'])
        output = dict(status='PASS_NEGATIVE_AND_POSITIVE_EVALUATOR_REPLAY', original_manifest='FAIL stream accounting',
                      corrected_manifest='PROTOCOL_PASS', runtime_acceptance=False,
                      caveat='Host time bounds reconstructed from retained QMP monotonic times; replay is not original runtime acceptance.',
                      qmp_guest_shutdown_before_host_quit=True, qmp_terminal_status_observed='shutdown',
                      evaluator=ref, original_tls=self.selection['original_tls'], corrected_tls=self.selection['corrected_tls'],
                      raw_tls_archive=self.selection['tls_attempt_archive'], observation=observation)
        (self.work / 'retained-tls-evaluator-replay.json').write_text(json.dumps(output, sort_keys=True, indent=2) + '\n')
        if digest(Path(ref['path']).read_bytes()) != ref['sha256']:
            raise AssertionError('frozen evaluator source changed')


if __name__ == '__main__':
    unittest.main()
