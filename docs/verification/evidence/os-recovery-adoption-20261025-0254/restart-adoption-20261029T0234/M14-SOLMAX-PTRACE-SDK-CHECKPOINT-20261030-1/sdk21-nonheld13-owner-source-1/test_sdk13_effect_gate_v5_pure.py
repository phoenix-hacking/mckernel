"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic AST-extracted guard and stream regressions; no owner, helper or process execution.
"""
import ast,base64,hashlib,json,types,unittest
from pathlib import Path

HERE=Path(__file__).parent
owner=ast.parse((HERE/'sdk13_compile_image_owner.v5.py').read_text())
parent=ast.parse((HERE/'sdk13_daemon_metadata_parent.v5.py').read_text())
capture=ast.parse((HERE/'sdk13_owned_capture.v5.py').read_text())
helper=ast.parse((HERE/'sdk13_compile_host_helper.v5.py').read_text())


def extract(tree,names,env):
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    scope=dict(env);exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                                  '<synthetic-fixture>','exec'),scope)
    return scope


def fail(ok,why):
    if not ok:raise ValueError(why)


def valid_capture():
    daemon={'pid':2036,'starttime':1513,'exe_device':4,'exe_inode':5,'socket_device':6,'socket_inode':7}
    parent_id={'pid':11,'birth':200,'ppid':10,'pgid':10,'sid':10}
    reader={'pid':12,'birth':300,'ppid':11,'pgid':12,'sid':12}
    sample={'status':'OBSERVED_EXACT_DAEMON_READONLY','boot_id':'boot-fixed','daemon':daemon,
            'daemon_birth_before':1513,'daemon_birth_after':1513,'reader':reader}
    raw=(json.dumps(sample,sort_keys=True)+'\n').encode()
    stdout={'base64':base64.b64encode(raw).decode(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'complete':True,'error':None}
    stderr={'base64':'','bytes':0,'sha256':hashlib.sha256(b'').hexdigest(),'complete':True,'error':None}
    inner={'boot':102,'mono':202,'weekly_observed_utc':900,'expiry_utc':1200}
    doc={'status':'PASS_EXACT_DAEMON_METADATA','parent':parent_id,'reader':reader,'reader_wait4_pid':12,
         'reader_wait4_status':0,'reader_direct_joined':True,'reader_group_absent':True,
         'reader_streams_closed':True,'reader_stdout':stdout,'reader_stderr':stderr,
         'pre_reader_gate':inner,'error':None,'sample':sample}
    join={'pid':10,'returncode':0,'direct_child_joined':True,'group_absent':True,'closed_streams':True,
          'error':None,'retirement_error':None,'timed_out':False,
          'effect_boundary':{'boot':101,'mono':201,'weekly_observed_utc':900,'expiry_utc':1200}}
    return join,doc,daemon


class GuardFixture(unittest.TestCase):
    def setUp(self):
        env={'_fail':fail,'SDK13_UTC':2000,'SDK13_BOOT':1000,'SDK13_MONO':1000,'SDK13_BOOT_ID':'boot-fixed',
             'base64':base64,'hashlib':hashlib,'json':json,'OwnerError':ValueError}
        self.env=extract(owner,{'_sdk13_capture_fresh','_sdk13_evaluate_effect','_sdk13_check_daemon_capture'},env)
        self.facts={'service_status':'NO_NEW_REJECTION','paid_fallback':False,'weekly_used_percent':67,
                    'weekly_observed_utc':990,'expiry_utc':1010}

    def evaluate(self,release='r',controls=['c'],utc=1000,stopped=False):
        return self.env['_sdk13_evaluate_effect']('r',release,['c'],controls,self.facts,utc,100,100,'boot-fixed',stopped)

    def test_valid_boundary_and_setup_expiry(self):
        self.assertEqual(self.evaluate()['utc'],1000)
        with self.assertRaises(ValueError):self.evaluate(utc=1010)
        with self.assertRaises(ValueError):self.evaluate(utc=1021)

    def test_release_control_and_stop_drift_fail(self):
        for opts in ({'release':'new'}, {'controls':['new']}, {'stopped':True}):
            with self.subTest(opts=opts),self.assertRaises(ValueError):self.evaluate(**opts)

    def test_nonempty_or_incomplete_stderr_is_not_pass(self):
        check=self.env['_sdk13_check_daemon_capture'];join,doc,daemon=valid_capture()
        self.assertEqual(check(join,doc,daemon),daemon)
        for change in ({'bytes':3,'base64':base64.b64encode(b'bad').decode(),'sha256':hashlib.sha256(b'bad').hexdigest()},
                       {'complete':False}):
            join,doc,daemon=valid_capture();doc['reader_stderr'].update(change)
            with self.assertRaises(ValueError):check(join,doc,daemon)

    def test_boundary_order_and_retained_stdout(self):
        check=self.env['_sdk13_check_daemon_capture'];join,doc,daemon=valid_capture();doc['pre_reader_gate']['mono']=199
        with self.assertRaises(ValueError):check(join,doc,daemon)
        join,doc,daemon=valid_capture();doc['reader_stdout']['sha256']='0'*64
        with self.assertRaises(ValueError):check(join,doc,daemon)

    def test_bounded_stream_preserves_partial_error(self):
        class Reader:
            def __init__(self):self.i=0
            def read(self,fd,n):
                self.i+=1
                if self.i==1:return b'partial'
                raise OSError('synthetic stream failure')
        fake=types.SimpleNamespace(read=Reader().read)
        fn=extract(parent,{'bounded_stream'},{'os':fake,'base64':base64,'hashlib':hashlib})['bounded_stream']
        raw,record=fn(types.SimpleNamespace(fileno=lambda:4),4096)
        self.assertEqual(raw,b'partial');self.assertFalse(record['complete'])
        self.assertEqual(base64.b64decode(record['base64']),raw)

    def test_each_capture_source_has_one_guarded_popen_without_retry(self):
        owned=next(n for n in capture.body if isinstance(n,ast.FunctionDef) and n.name=='owned_capture')
        docker=next(n for n in helper.body if isinstance(n,ast.ClassDef) and n.name=='Docker')
        call=next(n for n in docker.body if isinstance(n,ast.FunctionDef) and n.name=='call')
        for fn,marker in ((owned,'effect_gate()'),(call,'self.effect_gate(args[0])')):
            text=ast.unparse(fn)
            self.assertLess(text.index(marker),text.index('subprocess.Popen('))
            self.assertEqual(text.count('subprocess.Popen('),1)
        direct=next(n for n in parent.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        text=ast.unparse(direct)
        self.assertLess(text.index('parent_effect_gate(token)'),text.index('subprocess.Popen('))
        self.assertEqual(text.count('subprocess.Popen('),1)


if __name__=='__main__':unittest.main()
