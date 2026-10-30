"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure AST extraction with synthetic inputs; no helper, owner, root or daemon is executed.
"""
import ast
from pathlib import Path
import stat
import types
import unittest

HERE=Path(__file__).parent
owner=ast.parse((HERE/'sdk13_compile_image_owner.v4.py').read_text())
reader=ast.parse((HERE/'sdk13_daemon_metadata_reader.v4.py').read_text())


def extract(tree,name,env):
    found=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(found)==1
    values=dict(env);exec(compile(ast.fix_missing_locations(ast.Module(body=found,type_ignores=[])),
                                  '<pure-fixture>','exec'),values)
    return values[name]


def fail(ok,why):
    if not ok:raise ValueError(why)


def valid():
    daemon={'pid':2036,'starttime':1513,'exe_device':4,'exe_inode':5,'socket_device':6,'socket_inode':7}
    parent={'pid':11,'birth':200,'ppid':10,'pgid':10,'sid':10}
    reader_id={'pid':12,'birth':300,'ppid':11,'pgid':12,'sid':12}
    sample={'status':'OBSERVED_EXACT_DAEMON_READONLY','boot_id':'boot-fixed','daemon':daemon,
            'daemon_birth_before':1513,'daemon_birth_after':1513,'reader':reader_id}
    document={'status':'PASS_EXACT_DAEMON_METADATA','parent':parent,'reader':reader_id,'reader_wait4_pid':12,
              'reader_wait4_status':0,'reader_direct_joined':True,'reader_group_absent':True,
              'reader_streams_closed':True,'error':None,'sample':sample}
    join={'pid':10,'returncode':0,'direct_child_joined':True,'group_absent':True,
          'closed_streams':True,'error':None,'retirement_error':None,'timed_out':False}
    return join,document,daemon


class HelperFixture(unittest.TestCase):
    def setUp(self):
        self.check=extract(owner,'_sdk13_check_daemon_capture',{'_fail':fail,'SDK13_BOOT_ID':'boot-fixed'})

    def test_exact_direct_reader_and_sudo_join(self):
        join,document,daemon=valid();self.assertEqual(self.check(join,document,daemon),daemon)

    def test_sudo_error_and_unknown_join_fail(self):
        for key,value in [('returncode',1),('direct_child_joined',False),('group_absent',False),
                          ('retirement_error','denied'),('timed_out',True)]:
            with self.subTest(key=key):
                join,doc,daemon=valid();join[key]=value
                with self.assertRaises(ValueError):self.check(join,doc,daemon)

    def test_reader_join_parent_and_birth_drift_fail(self):
        join,doc,daemon=valid();doc['reader_direct_joined']=False
        with self.assertRaises(ValueError):self.check(join,doc,daemon)
        join,doc,daemon=valid();doc['parent']['ppid']=99
        with self.assertRaises(ValueError):self.check(join,doc,daemon)
        join,doc,daemon=valid();doc['sample']['daemon_birth_after']=1514
        with self.assertRaises(ValueError):self.check(join,doc,daemon)

    def test_freshness_bound_and_expiry(self):
        fresh=extract(owner,'_sdk13_capture_fresh',{'SDK13_UTC':2000})
        self.assertTrue(fresh(1000,970,1001))
        self.assertFalse(fresh(1000,969,1001))
        self.assertFalse(fresh(1000,1001,1001))
        self.assertFalse(fresh(1000,999,1000))
        self.assertFalse(fresh(1000,999,2001))

    def test_reader_root_permission_error_and_daemon_drift_fail(self):
        boot=types.SimpleNamespace(read_text=lambda:'boot-fixed')
        path=lambda *args:boot
        base={'getuid':lambda:0,'geteuid':lambda:0,'sched_getaffinity':lambda pid:{7},'getpid':lambda:50}
        def denied(path):raise PermissionError('synthetic permission failure')
        env={'os':types.SimpleNamespace(**base,stat=denied),'Path':path,'PID':2036,'BIRTH':1513,
             'BOOT':'boot-fixed','SOCKET':'/var/run/docker.sock','stat':stat,
             'proc_identity':lambda pid:{'birth':1513}}
        with self.assertRaises(PermissionError):extract(reader,'sample',env)()
        seq=iter([{'birth':1513},{'birth':1514}])
        fake_stat=lambda p:types.SimpleNamespace(st_mode=stat.S_IFREG if p.endswith('/exe') else stat.S_IFSOCK,
                                                st_dev=1,st_ino=2)
        env['os']=types.SimpleNamespace(**base,stat=fake_stat);env['proc_identity']=lambda pid:next(seq)
        with self.assertRaisesRegex(ValueError,'birth drift'):extract(reader,'sample',env)()

    def test_owner_limits_to_three_unique_phases_and_no_direct_exe_stat(self):
        cls=next(n for n in owner.body if isinstance(n,ast.ClassDef) and n.name=='SDK13ImageOwner')
        run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        text=ast.unparse(run)
        self.assertEqual(text.count('_sdk13_capture_daemon('),3)
        for phase in ('prelease','pre-create','pre-start'):self.assertIn(repr(phase),text)
        auth=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='_sdk13_authorize')
        self.assertNotIn("/proc/%d/exe",ast.unparse(auth))


if __name__=='__main__':unittest.main()
