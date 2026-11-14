"""Execute the real packet; only inputs/helper and fault hooks are disposable."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'docs/verification/evidence/native-exact-mckernel-gitlink-preparation-6fed3a10-exportset25.sh'
HELPER = ROOT / 'scripts/native_rust_exact_mckernel_gitlink_prepare.py'
CANDIDATE = '6fed3a1022db0b4f9828dd42a8bd8f88fc052053'
IHK = '3114d9e7101ad52030eb3effa849a5c108972a1f'
LINK = 'executer/user/lib/libdwarf/libdwarf'

FAKE = '''import argparse, hashlib, json, os, pathlib, runpy, shutil, signal, subprocess, time
real = runpy.run_path(REAL_HELPER)
inventory = real['inventory']
_authenticate_git = real['_authenticate_git']
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for arg in ('source','checkout','output','base-manifest','candidate-sha','ihk-sha'):
        p.add_argument('--'+arg, required=True)
    a = p.parse_args()
    root = pathlib.Path(a.output).parent
    mode = (root/'mode').read_text()
    if mode == 'sleep':
        kid = subprocess.Popen(['/usr/bin/python3', '-c', 'import pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path('+repr(str(root/'kid-ready'))+').touch(); time.sleep(30)'])
        while not (root/'kid-ready').exists(): time.sleep(.01)
        (root/'pids').write_text(str(os.getpid())+' '+str(kid.pid))
        time.sleep(30)
    if mode == 'helper-fail':
        print('ORIGINAL_HELPER_FAILURE', flush=True)
        raise SystemExit(7)
    shutil.copytree(a.source, a.checkout)
    v = inventory(pathlib.Path(a.checkout))
    link = 'executer/user/lib/libdwarf/libdwarf'
    row = dict(path=link, commit=v['head'], tree=v['tree'], files=v['files'], git_metadata=v['git_metadata'])
    d = dict(schema='mckernel.native-exact-mckernel-gitlink-inputs.v1', candidate_sha=a.candidate_sha, ihk_sha=a.ihk_sha, base_manifest_sha256=hashlib.sha256(pathlib.Path(a.base_manifest).read_bytes()).hexdigest(), consumed_gitlinks={link:row}, preparer_git=_authenticate_git())
    if mode == 'wrong-base': d['base_manifest_sha256'] = '0'*64
    if mode == 'wrong-inventory': row['files']['file']['sha256'] = '0'*64
    if mode == 'wrong-metadata': row['git_metadata']['HEAD']['sha256'] = '0'*64
    if mode == 'wrong-tool': d['preparer_git']['sha256'] = '0'*64
    if mode == 'dirty-checkout': (pathlib.Path(a.checkout)/'file').write_text('changed')
    if mode == 'terminal-collision': (root/'terminal').write_text('sentinel')
    pathlib.Path(a.output).write_text('{' if mode == 'truncated' else json.dumps(d))
    print('COMPLETE_HELPER_LOG_BYTES', flush=True)
'''

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class PacketBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mckernel-gitlink25-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = {key: str(self.root/key) for key in ('src','dest','base','out','log','terminal','helper')}
        src = self.root/'src'
        src.mkdir()
        self.git(src, 'init', '-q')
        (src/'file').write_text('payload\n')
        os.chmod(src/'file', 0o644)
        self.git(src, 'add', 'file')
        self.git(src, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        commit = self.git(src, 'rev-parse', 'HEAD').strip()
        (self.root/'base').write_text(json.dumps(dict(candidate_sha=CANDIDATE, ihk_sha=IHK, gitlinks={LINK:commit})))
        (self.root/'helper').write_text('REAL_HELPER = '+repr(str(HELPER))+'\n'+FAKE)
        self.cfg.update(base_sha=digest(self.root/'base'), helper_sha=digest(self.root/'helper'))
        (self.root/'mode').write_text('valid')
        self.procs = []
        self.addCleanup(self.stop_processes)

    def git(self, root, *args):
        return subprocess.check_output(['/usr/bin/git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE)

    def stop_processes(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def start(self, mode='valid', **settings):
        (self.root/'mode').write_text(mode)
        cfg = dict(self.cfg, **settings)
        (self.root/'config.json').write_text(json.dumps(cfg))
        env = dict(os.environ, MCK_GITLINK25_TEST_CONFIG=str(self.root/'config.json'))
        proc = subprocess.Popen(['/bin/bash', str(PACKET), '--disposable-test'], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.procs.append(proc)
        return proc

    def wait_file(self, name):
        deadline = time.monotonic()+8
        while not (self.root/name).exists():
            if time.monotonic() > deadline: self.fail('missing '+name)
            time.sleep(.01)

    def done(self, proc, expected=0):
        out, err = proc.communicate(timeout=12)
        self.assertEqual(proc.returncode, expected, (out, err, (self.root/'log').read_text() if (self.root/'log').exists() else ''))
        return out, err

    def terminal(self):
        d = json.loads((self.root/'terminal').read_text())
        self.assertEqual(d['log_sha256'], digest(self.root/'log'))
        self.assertTrue(d['child_retired'])
        self.assertFalse(Path('/proc/'+str(d['child']['pid'])).exists())
        return d

    def test_valid_real_inventory_durable_log_and_identity(self):
        proc = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        start = Path('/proc/%d/stat' % proc.pid).read_text().rsplit(')',1)[1].split()[19]
        (self.root/'resume-before-commit').touch()
        out, err = self.done(proc)
        d = self.terminal()
        self.assertEqual(d['owner'], dict(pid=proc.pid, starttime=start))
        self.assertEqual(d['boot_id'], Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        self.assertEqual(d['returncode'], 0)
        self.assertEqual(d['output_sha256'], digest(self.root/'out'))
        self.assertEqual(json.loads(out)['terminal_sha256'], digest(self.root/'terminal'))
        self.assertIn('COMPLETE_HELPER_LOG_BYTES', (self.root/'log').read_text())
        helper_rows = [json.loads(line) for line in (self.root/'log').read_text().splitlines()
                       if line.startswith('{') and '"helper"' in line and '"command"' in line]
        self.assertEqual(len(helper_rows), 1)
        self.assertTrue(helper_rows[0]['helper']['starttime'].isdigit())
        self.assertFalse(Path('/proc/'+str(helper_rows[0]['helper']['pid'])).exists())
        self.assertEqual(helper_rows[0]['boot_id'], d['boot_id'])

    def test_semantic_failures(self):
        # Fresh real packet/namespace for every vector.
        for mode in ('wrong-base','wrong-inventory','wrong-metadata','wrong-tool','dirty-checkout','truncated','helper-fail'):
            with self.subTest(mode=mode):
                case = PacketBehavior('test_valid_real_inventory_durable_log_and_identity')
                case.setUp()
                try:
                    case.done(case.start(mode), 1)
                    self.assertEqual(case.terminal()['returncode'], 1)
                    self.assertNotIn('PREPARATION_RESULT=PASS', (case.root/'log').read_text())
                finally: case.doCleanups()

    def test_signal_retires_helper_and_term_ignoring_grandchild(self):
        for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig):
                case = PacketBehavior('test_valid_real_inventory_durable_log_and_identity')
                case.setUp()
                try:
                    proc = case.start('sleep')
                    case.wait_file('pids')
                    pids = (case.root/'pids').read_text().split()
                    os.kill(proc.pid, sig)
                    case.done(proc, 128+sig)
                    case.terminal()
                    for pid in pids: self.assertFalse(Path('/proc/'+pid).exists(), pid)
                finally: case.doCleanups()

    def test_concurrent_start_cannot_overwrite_claims_or_logs(self):
        first = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        before = (self.root/'log').read_bytes()
        self.done(self.start(pause_at='before-commit'), 1)
        self.assertEqual(before, (self.root/'log').read_bytes())
        (self.root/'resume-before-commit').touch()
        self.done(first)
        self.terminal()

    def test_existing_output_untouched(self):
        (self.root/'out').write_text('sentinel')
        self.done(self.start(), 1)
        self.assertEqual((self.root/'out').read_text(), 'sentinel')
        self.assertFalse((self.root/'dest').exists())

    def test_signal_before_commit_fails(self):
        proc = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        proc.terminate()
        (self.root/'resume-before-commit').touch()
        self.done(proc, 143)
        self.assertEqual(self.terminal()['returncode'], 143)

    def test_late_signal_cannot_interrupt_committed_delivery(self):
        proc = self.start(pause_at='after-terminal')
        self.wait_file('paused-after-terminal')
        for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM): os.kill(proc.pid, sig)
        (self.root/'resume-after-terminal').touch()
        out, err = self.done(proc)
        self.assertEqual(self.terminal()['returncode'], 0)
        self.assertEqual(json.loads(out)['preparation_returncode'], 0)

    def test_terminal_collision_never_overwrites_or_delivers_success(self):
        out, err = self.done(self.start('terminal-collision'), 1)
        self.assertEqual((self.root/'terminal').read_text(), 'sentinel')
        self.assertEqual(out, b'')

    def test_fsync_failures_never_deliver_success(self):
        for stage in ('log','log-parent','terminal','terminal-parent'):
            with self.subTest(stage=stage):
                case = PacketBehavior('test_valid_real_inventory_durable_log_and_identity')
                case.setUp()
                try:
                    out, err = case.done(case.start(fail_fsync=stage), 1)
                    self.assertEqual(out, b'')
                    self.assertIn(b'injected fsync failure', err)
                    if stage in ('log','log-parent'): self.assertFalse((case.root/'terminal').exists())
                finally: case.doCleanups()

    def test_broken_stdout_is_nonzero_after_durable_preparation(self):
        proc = self.start(pause_at='after-terminal')
        self.wait_file('paused-after-terminal')
        proc.stdout.close()
        proc.stdout = None
        (self.root/'resume-after-terminal').touch()
        self.done(proc, 1)
        self.assertEqual(self.terminal()['returncode'], 0)
        self.assertEqual(self.terminal()['acceptance_requires'], 'zero-wrapper-exit-and-stdout-commit-witness')

    def test_test_override_cannot_target_production_paths(self):
        self.cfg['out'] = '/home/holden/mckernel/not-permitted'
        out, err = self.done(self.start(), 1)
        self.assertIn(b'test-path-outside-disposable-root', err)
        self.assertFalse((self.root/'dest.claim').exists())

    def test_overrides_require_explicit_test_argument(self):
        (self.root/'config.json').write_text(json.dumps(self.cfg))
        result = subprocess.run(['/bin/bash', str(PACKET)], capture_output=True,
                                env=dict(os.environ, MCK_GITLINK25_TEST_CONFIG=str(self.root/'config.json')),
                                timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'test-mode-requires-explicit-argument-and-config', result.stderr)
        self.assertFalse((self.root/'dest.claim').exists())

if __name__ == '__main__':
    unittest.main()
