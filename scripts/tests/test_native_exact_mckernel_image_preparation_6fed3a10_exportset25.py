"""Execute the supervisor and real preparer in confined disposable namespaces.

Only toolchain/owner dependencies are substituted. Inventory/identity routines
are production bodies. The fixture owner is not production image admission.
"""
import ast
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
PACKET = ROOT/'docs/verification/evidence/native-exact-mckernel-image-preparation-6fed3a10-exportset25.sh'
PREPARER = ROOT/'scripts/native_rust_exact_mckernel_image_request_prepare.py'
OWNER = ROOT/'scripts/native_rust_exact_mckernel_image_container_owner.py'
C = '6fed3a1022db0b4f9828dd42a8bd8f88fc052053'
I = '3114d9e7101ad52030eb3effa849a5c108972a1f'
IMAGE = 'sha256:5688f9c8cb83e2aafb43c6aba8e8ff85fe17ddbc83a5935b6b804c1478bdcb98'
LOCK = 'fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802'
NIGHTLY = 'rustc 1.95.0-nightly (c04308580 2026-02-18)'
AUTH = ('base','receipt','gitlink_manifest','helper','owner','driver','provenance','host_owner','git')
TARGETS = ('work','evidence','inputs','toolchain','request','lease','exclusion','claim','log','terminal')

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

FIXTURE_OWNER = '''import hashlib, json, os, stat
from pathlib import Path
class OwnerError(RuntimeError): pass
def _fail(ok, message):
    if not ok: raise OwnerError(message)
def _sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
def _closure_inventory(root, *args): return _tree_inventory(root)
def _disjoint(paths):
    for n, p in enumerate(paths):
        for q in paths[n+1:]:
            _fail(p != q and p not in q.parents and q not in p.parents, 'overlap')
def _validate_library_closure(*args): pass
def _validate_gitlink_manifest(*args): pass
class ImageOwner:
    def __init__(self, req): self.req = req
    def validate(self):
        mode = (Path(__file__).parent/'mode').read_text()
        if mode == 'toolchain-only' and self.req['toolchain_manifest'] == str(Path(__file__).parent/'toolchain'):
            raise OwnerError('late fixture validation failure')
        if mode == 'owner-reject': raise OwnerError('fixture owner rejection')
        _fail(self.req['jobs'] == 4, 'jobs')
        _fail(not Path(self.req['lease_path']).exists(), 'lease acquired')
        _fail(not Path(self.req['common_exclusion_path']).exists(), 'exclusion acquired')
        return {}
    def run(self): raise AssertionError('IMAGE OWNER EXECUTION PROHIBITED')
'''

BEFORE_MAIN = '''
if __name__ == '__main__':
    import signal, subprocess, time
    fixture_root = Path(__file__).parent
    fixture_mode = (fixture_root/'mode').read_text()
    if fixture_mode == 'midflight-build':
        (fixture_root/'build'/'build'/'kernel').write_text('changed before preparer scans')
    if fixture_mode == 'midflight-nightly':
        (fixture_root/'nightly'/'new-file').write_text('changed before preparer scans')
    if fixture_mode == 'sleep':
        kid = subprocess.Popen(['/usr/bin/python3', '-c',
            'import os,pathlib,signal,time; os.setsid(); signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path('+repr(str(fixture_root/'kid-ready'))+').touch(); time.sleep(40)'])
        while not (fixture_root/'kid-ready').exists(): time.sleep(.01)
        (fixture_root/'pids').write_text(str(os.getpid())+' '+str(kid.pid))
        time.sleep(40)
    if fixture_mode == 'helper-fail':
        print('ORIGINAL_HELPER_FAILURE', flush=True)
        raise SystemExit(7)
'''

AFTER_MAIN = '''
if __name__ == '__main__':
    print('COMPLETE_HELPER_LOG_BYTES', flush=True)
    if fixture_mode == 'terminal-collision': (fixture_root/'terminal').write_text('sentinel')
    if fixture_mode == 'log-substitution':
        (fixture_root/'log').rename(fixture_root/'original-log')
        (fixture_root/'log').write_text('substitute')
    if fixture_mode == 'truncated': (fixture_root/'request').write_text('{')
    if fixture_mode == 'nonzero-after-publication': raise SystemExit(9)
    if fixture_mode == 'dirty-backup': (fixture_root/'backup'/'payload').write_text('changed')
    if fixture_mode.startswith('mutate:'):
        _, name, key, encoded = fixture_mode.split(':', 3)
        path = fixture_root/name
        doc = json.loads(path.read_text())
        doc[key] = json.loads(encoded)
        path.write_text(json.dumps(doc))
    if fixture_mode == 'request-only': (fixture_root/'toolchain').unlink()
    if fixture_mode == 'duplicate-key':
        path = fixture_root/'request'
        path.write_text(path.read_text().rstrip()[:-1]+',"jobs":4}')
'''

class PreparationPacket(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mckernel-image25-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        dirs = ('source','backup','build','nightly','gitlink','host_root','scratch_root')
        self.cfg = {k:str(self.root/k) for k in (*AUTH,*TARGETS,*dirs)}
        for k in dirs: Path(self.cfg[k]).mkdir()
        for k in ('source','backup','gitlink'): (self.root/k/'payload').write_text(k+' bytes')
        (self.root/'build'/'build').mkdir()
        (self.root/'build'/'build'/'kernel').write_text('kernel bytes')
        (self.root/'nightly'/'bin').mkdir()
        rustc = self.root/'nightly'/'bin'/'rustc'
        rustc.write_text('#!/bin/sh\nprintf "%s\\n" "'+NIGHTLY+'"\n')
        rustc.chmod(0o700)
        tools = ('cmake','cc','clang','ld.lld','rustc','nm','readelf','make','ld','objcopy','ar','ranlib','git','dd')
        names = ('tool-observation.json','offline-tool-observation.json')
        for name in names: (self.root/name).write_text('{}')
        (self.root/'base').write_text(json.dumps(dict(schema='mckernel.native-exact-build-inputs.v1',candidate_sha=C,ihk_sha=I)))
        (self.root/'gitlink_manifest').write_text(json.dumps(dict(schema='mckernel.native-exact-mckernel-gitlink-inputs.v1',
                candidate_sha=C,ihk_sha=I,base_manifest_sha256=digest(self.root/'base'))))
        (self.root/'receipt').write_text(json.dumps(dict(status='PASS',source_free=True,runtime_network='none',candidate_sha=C,
                retired=True,base_image='fixture-base',image_id=IMAGE,toolchain_lock_sha256=LOCK,
                tools={k:dict(path='/usr/bin/'+k,sha256='a'*64,version='fixture') for k in tools},libraries={},
                evidence={n:dict(sha256=digest(self.root/n),size=2) for n in names})))
        for key, basename in (('owner','native_rust_exact_mckernel_image_container_owner'),
                              ('driver','native_rust_exact_mckernel_image_offline'),
                              ('provenance','native_rust_exact_build_offline'),
                              ('host_owner','native_rust_exact_build_container_owner'),
                              ('helper','native_rust_exact_mckernel_image_request_prepare')):
            self.cfg[key] = str(self.root/(basename+'.py'))
        text = OWNER.read_text()
        bodies = '\n\n'.join(ast.get_source_segment(text,n) for n in ast.parse(text).body
                             if isinstance(n,ast.FunctionDef) and n.name in ('_identity','_tree_inventory'))
        constants = {'REQUEST_SCHEMA':'mckernel.native-exact-mckernel-image-container-request.v1',
            'REQUIRED_TOOLS':tools,'_PREPARATION_EVIDENCE':names,'EXPECTED_V2_RUSTC_VERSION':NIGHTLY,
            'COMMON_EXCLUSION':self.cfg['exclusion'],'PREPARER_BASE_IMAGE':'fixture-base',
            'LAUNCHER_AGGREGATE_GIB':'16.2158','LIMITS':{'Memory':12*2**30}}
        Path(self.cfg['owner']).write_text(FIXTURE_OWNER+'\n'+bodies+'\n'+'\n'.join(k+' = '+repr(v) for k,v in constants.items())+'\n')
        Path(self.cfg['driver']).write_text("def _tree_inventory(root, **kw):\n    from native_rust_exact_mckernel_image_container_owner import _tree_inventory\n    return _tree_inventory(root)\n"
             "TOOLCHAIN_SCHEMA_V2 = 'mckernel.native-exact-mckernel-image-toolchain.v2'\n"
             "REPRO_ENV = {'EXPECTED_KERNEL_RELEASE':'6.12.0-211.44.1.el10_2.mckernel1.x86_64'}\n")
        for k in ('provenance','host_owner'): Path(self.cfg[k]).write_text('# inert fixture dependency\n')
        (self.root/'git').write_text('fixture git descriptor')
        source = PREPARER.read_text().replace('\nif __name__ == "__main__":',BEFORE_MAIN+'\nif __name__ == "__main__":')
        Path(self.cfg['helper']).write_text(source+AFTER_MAIN)
        self.cfg.update({k+'_sha':digest(self.cfg[k]) for k in AUTH})
        (self.root/'mode').write_text('valid')
        self.procs = []
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=6)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def start(self,mode='valid',**settings):
        (self.root/'mode').write_text(mode)
        (self.root/'config.json').write_text(json.dumps(dict(self.cfg,**settings)))
        proc = subprocess.Popen(['/bin/bash',str(PACKET),'--disposable-test'],
                 env=dict(os.environ,MCK_IMAGE25_TEST_CONFIG=str(self.root/'config.json')),
                 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.procs.append(proc)
        return proc

    def done(self,proc,expected=0):
        out,err = proc.communicate(timeout=20)
        self.assertEqual(proc.returncode,expected,(out,err,(self.root/'log').read_text() if (self.root/'log').exists() else 'no log'))
        return out,err

    def wait_file(self,name):
        end = time.monotonic()+8
        while not (self.root/name).exists():
            if time.monotonic() >= end:
                self.fail('missing '+name+'; '+((self.root/'log').read_text() if (self.root/'log').exists() else 'no log'))
            time.sleep(.01)

    def terminal(self):
        d = json.loads((self.root/'terminal').read_text())
        self.assertEqual(d['log_sha256'],digest(self.root/'log'))
        self.assertTrue(d['child_retired'])
        if d['child']: self.assertFalse(Path('/proc/'+str(d['child']['pid'])).exists())
        for k in ('lease','exclusion'): self.assertFalse((self.root/k).exists())
        for k in ('work','evidence'): self.assertEqual(list((self.root/k).iterdir()),[])
        return d

    def cases(self,vectors,run):
        for v in vectors:
            with self.subTest(vector=v):
                case = PreparationPacket('test_success_real_preparer_and_commit_witness')
                case.setUp()
                try: run(case,v)
                finally: case.doCleanups()

    def test_success_real_preparer_and_commit_witness(self):
        proc = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        start = Path('/proc/%d/stat'%proc.pid).read_text().rsplit(')',1)[1].split()[19]
        (self.root/'resume-before-commit').touch()
        out,err = self.done(proc)
        d = self.terminal()
        self.assertEqual(d['returncode'],0)
        self.assertEqual(d['owner']['pid'],proc.pid)
        self.assertEqual(d['owner']['starttime'],start)
        self.assertEqual(d['boot_id'],Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        self.assertEqual(d['validation']['child_returncode'],0)
        self.assertEqual(d['validation']['semantic_validation'],'PASS')
        self.assertEqual(d['publication']['state'],'request-published')
        witness = json.loads(out)
        self.assertEqual(witness['terminal_sha256'],digest(self.root/'terminal'))
        self.assertEqual(witness['log_sha256'],d['log_sha256'])
        self.assertEqual(witness['preparation_returncode'],0)
        self.assertEqual(d['observed_hashes'],{k:digest(self.root/k) for k in ('toolchain','request')})
        claim = json.loads((self.root/'claim').read_text())
        self.assertEqual(claim['owner'],d['owner'])
        self.assertEqual(claim['boot_id'],d['boot_id'])
        log = (self.root/'log').read_text()
        self.assertIn('COMPLETE_HELPER_LOG_BYTES',log)
        rows = [json.loads(s) for s in log.splitlines() if s.startswith('{') and '"command"' in s]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['command'][:4],['/usr/bin/python3','-I','-B','-c'])
        self.assertEqual(len(rows[0]['command']),5)
        self.assertEqual(rows[0]['helper_argv'],[self.cfg['helper'],self.cfg['inputs'],'--request',self.cfg['request']])
        self.assertEqual(len(rows[0]['source_bundle_sha256']),64)
        self.assertEqual(rows[0]['helper']['session'],d['child']['pid'])

    def test_valid_poisoned_pyc_cannot_execute_in_source_bootstrap(self):
        def run(case,key):
            path = Path(case.cfg[key])
            marker = case.root/'forbidden-cache-side-effect'
            # Generate a genuinely valid cache using the SAME Python 3.8
            # interpreter as the supervisor's child, with matching source size
            # and timestamp. First prove ordinary import executes the poison.
            poison = ('from pathlib import Path\nwith Path('+repr(str(marker))+').open("a") as f: f.write("FORBIDDEN\\n")\n'
                      'raise SystemExit(77)\n')
            create = '''import importlib._bootstrap_external as b, importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1]); st = p.stat()
cache = pathlib.Path(importlib.util.cache_from_source(str(p)))
cache.parent.mkdir(exist_ok=True)
cache.write_bytes(b._code_to_timestamp_pyc(compile(sys.argv[2],str(p),'exec'),int(st.st_mtime),st.st_size))
'''
            subprocess.run(['/usr/bin/python3','-I','-B','-c',create,str(path),poison],check=True)
            probe = subprocess.run(['/usr/bin/python3','-I','-B','-c',
                    'import importlib,sys; sys.path.insert(0,sys.argv[1]); importlib.import_module(sys.argv[2])',
                    str(case.root),path.stem],capture_output=True)
            case.assertEqual(probe.returncode,77,(probe.stdout,probe.stderr))
            case.assertEqual(marker.read_text(),'FORBIDDEN\n')
            out,err = case.done(case.start())
            case.assertEqual(case.terminal()['returncode'],0)
            case.assertEqual(marker.read_text(),'FORBIDDEN\n','bootstrap executed poisoned bytecode')
            case.assertEqual(json.loads(out)['preparation_returncode'],0)
        self.cases(('owner','driver','provenance','host_owner','helper'),run)

    def test_initial_build_and_nightly_bindings_survive_helper_rescan(self):
        def run(case,mode):
            case.done(case.start(mode),1)
            d = case.terminal()
            # The preparer accepted and published its post-mutation view; the
            # independently retained pre-helper view must still reject it.
            case.assertEqual(d['validation']['child_returncode'],0)
            case.assertEqual(d['publication']['state'],'request-published')
            case.assertEqual(d['validation']['semantic_validation'],'FAIL')
            case.assertIn('initial toolchain/request bindings changed',d['validation']['error'])
        self.cases(('midflight-build','midflight-nightly'),run)

    def test_authentication_before_mutation(self):
        def run(case,key):
            with Path(case.cfg[key]).open('ab') as f: f.write(b'changed')
            case.done(case.start(),1)
            for k in TARGETS: case.assertFalse(os.path.lexists(case.cfg[k]),k)
        self.cases(AUTH,run)

    def test_stale_target_and_claim_preflight(self):
        def run(case,key):
            Path(case.cfg[key]).write_text('sentinel')
            case.done(case.start(),1)
            case.assertEqual(Path(case.cfg[key]).read_text(),'sentinel')
            for k in TARGETS:
                if k != key: case.assertFalse(os.path.lexists(case.cfg[k]),k)
        self.cases(TARGETS,run)
        (self.root/'work').symlink_to(self.root/'backup',target_is_directory=True)
        self.done(self.start(),1)
        self.assertFalse((self.root/'claim').exists())

    def test_concurrent_claim(self):
        proc = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        saved = {k:(self.root/k).read_bytes() for k in ('claim','log','inputs','toolchain','request')}
        self.done(self.start(),1)
        self.assertEqual(saved,{k:(self.root/k).read_bytes() for k in saved})
        (self.root/'resume-before-commit').touch()
        self.done(proc)
        self.terminal()

    def test_signals_retire_term_ignoring_separate_session_descendant(self):
        def run(case,sig):
            proc = case.start('sleep')
            case.wait_file('pids')
            pids = (case.root/'pids').read_text().split()
            os.kill(proc.pid,sig)
            case.done(proc,128+sig)
            case.assertEqual(case.terminal()['publication']['state'],'no-publication')
            for pid in pids: case.assertFalse(Path('/proc/'+pid).exists(),pid)
        self.cases((signal.SIGHUP,signal.SIGINT,signal.SIGTERM),run)

    def test_deadline(self):
        proc = self.start('sleep',deadline=.5)
        self.wait_file('pids')
        pids = (self.root/'pids').read_text().split()
        self.done(proc,124)
        self.assertEqual(self.terminal()['returncode'],124)
        for pid in pids: self.assertFalse(Path('/proc/'+pid).exists())

    def test_precommit_signal(self):
        proc = self.start(pause_at='before-commit')
        self.wait_file('paused-before-commit')
        proc.terminate()
        (self.root/'resume-before-commit').touch()
        self.done(proc,143)
        self.assertEqual(self.terminal()['returncode'],143)

    def test_late_signals(self):
        proc = self.start(pause_at='after-terminal')
        self.wait_file('paused-after-terminal')
        for sig in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM): os.kill(proc.pid,sig)
        (self.root/'resume-after-terminal').touch()
        out,err = self.done(proc)
        self.assertEqual(json.loads(out)['preparation_returncode'],0)
        self.assertEqual(self.terminal()['returncode'],0)

    def test_partial_publication(self):
        def run(case,pair):
            mode,state = pair
            case.done(case.start(mode),1)
            d = case.terminal()
            case.assertEqual(d['publication']['state'],state)
            case.assertEqual(d['returncode'],1)
            case.assertTrue((case.root/'inputs').exists())
            if state != 'no-publication': case.assertTrue((case.root/'toolchain').exists())
            if state == 'request-published': case.assertTrue((case.root/'request').exists())
        self.cases((('helper-fail','no-publication'),('owner-reject','no-publication'),
                    ('toolchain-only','toolchain-only'),('nonzero-after-publication','request-published')),run)

    def test_exact_semantic_bindings(self):
        vectors = [('request',k,v) for k,v in {
            'schema':'wrong','candidate_sha':'0'*40,'ihk_sha':'0'*40,'image_id':'sha256:'+'0'*64,
            'jobs':3,'timeout':1,'toolchain_manifest_sha256':'0'*64,'source_manifest_sha256':'0'*64,
            'image_receipt_sha256':'0'*64,'gitlink_manifest_sha256':'0'*64,'toolchain_lock_sha256':'0'*64,
            'mounts':{},'disk_admission':{},'source_identity':{},'backup_identity':{},'disk_identity':{},
            'backup_inventory':{},'toolchain_roots':[],'source_root':'/wrong','lease_path':'/wrong',
            'common_exclusion_path':'/wrong','work_root':'/wrong','owner_evidence_root':'/wrong',
            'output_root':'/wrong','evidence_root':'/wrong','attempt_root':'/wrong','nightly':{},
            'host_git':{},'memory_allocation_roots':[],'memory_backed_bytes':False,'extra':True}.items()]
        vectors += [('toolchain',k,v) for k,v in {
            'schema':'wrong','kernel_binding':{},'kernel_inventory':{},'image_tools':{},
            'mounted_tools':{},'toolchain_roots':[],'path_dirs':[],'linux_probe':{},
            'environment':{'X':'1'},'libraries':{'unexpected':1}}.items()]
        def run(case,row):
            name,key,value = row
            case.done(case.start('mutate:'+name+':'+key+':'+json.dumps(value)),1)
            d = case.terminal()
            case.assertEqual(d['validation']['semantic_validation'],'FAIL')
            case.assertEqual(d['publication']['state'],'request-published')
        self.cases(vectors,run)

    def test_malformed_and_changed_outputs(self):
        def run(case,mode):
            case.done(case.start(mode),1)
            case.assertEqual(case.terminal()['validation']['semantic_validation'],'FAIL')
        self.cases(('truncated','dirty-backup','request-only','duplicate-key'),run)

    def test_short_writes(self):
        out,err = self.done(self.start(short_write=True))
        self.assertEqual(json.loads(out)['preparation_returncode'],0)
        self.assertEqual(self.terminal()['returncode'],0)

    def test_fsync_and_write_failure(self):
        def run(case,row):
            setting,label = row
            out,err = case.done(case.start(**{setting:label}),1)
            if out: case.assertNotEqual(json.loads(out)['preparation_returncode'],0)
            for k in ('lease','exclusion'): case.assertFalse((case.root/k).exists())
        self.cases([('fail_fsync',label) for label in ('claim','claim-parent','initial-log','initial-log-parent',
            'work','work-parent','evidence','evidence-parent','child-log','inputs','inputs-parent','toolchain',
            'toolchain-parent','request','request-parent','log','log-parent','terminal','terminal-parent','terminal-publication')]
            + [('fail_write',label) for label in ('claim','inputs','final-log','terminal','stdout')],run)

    def test_terminal_collision(self):
        out,err = self.done(self.start('terminal-collision'),1)
        self.assertEqual(out,b'')
        self.assertEqual((self.root/'terminal').read_text(),'sentinel')
        self.assertTrue((self.root/'terminal.pending').exists())

    def test_log_substitution_fails_without_terminal_or_witness(self):
        out,err = self.done(self.start('log-substitution'),1)
        self.assertEqual(out,b'')
        self.assertFalse((self.root/'terminal').exists())
        self.assertEqual((self.root/'log').read_text(),'substitute')
        self.assertIn('COMPLETE_HELPER_LOG_BYTES',(self.root/'original-log').read_text())

    def test_receipt_evidence_is_checked_before_claim(self):
        (self.root/'tool-observation.json').write_text('changed')
        self.done(self.start(),1)
        for k in TARGETS: self.assertFalse(os.path.lexists(self.cfg[k]),k)

    def test_broken_stdout(self):
        proc = self.start(pause_at='after-terminal')
        self.wait_file('paused-after-terminal')
        proc.stdout.close()
        proc.stdout = None
        (self.root/'resume-after-terminal').touch()
        self.done(proc,1)
        self.assertEqual(self.terminal()['returncode'],0)

    def test_arguments_and_test_namespace_admission(self):
        for args,env in ((['--bad'],{}),(['--disposable-test'],{}),
                         ([],{'MCK_IMAGE25_TEST_CONFIG':str(self.root/'config.json')})):
            p = subprocess.run(['/bin/bash',str(PACKET),*args],env=dict(os.environ,**env),capture_output=True)
            self.assertNotEqual(p.returncode,0)
        self.done(self.start(work='/home/holden/mckernel/forbidden'),1)
        self.assertFalse((self.root/'claim').exists())
        cfg = dict(self.cfg)
        del cfg['work']
        (self.root/'config.json').write_text(json.dumps(cfg))
        p = subprocess.run(['/bin/bash',str(PACKET),'--disposable-test'],
            env=dict(os.environ,MCK_IMAGE25_TEST_CONFIG=str(self.root/'config.json')),capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.root/'claim').exists())

    def test_shell_syntax(self):
        subprocess.run(['/bin/bash','-n',str(PACKET)],check=True)

if __name__ == '__main__': unittest.main()
