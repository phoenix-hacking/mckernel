"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
AST-extracted synthetic containment, root-record mode and lease-unlink cases only.
No actual owner, sudo, Docker, root document or lease is touched.
"""
import ast,errno,hashlib,json,re,types,unittest
from pathlib import Path

HERE=Path(__file__).parent
owner=ast.parse((HERE/'sdk13_compile_image_owner.v6.py').read_text())
parent=ast.parse((HERE/'sdk13_daemon_metadata_parent.v6.py').read_text())


def extract(tree,names,env):
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    values=dict(env);exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                                  '<synthetic-only>','exec'),values)
    return values


def fail(ok,why):
    if not ok:raise ValueError(why)


class ContainmentFixture(unittest.TestCase):
    def setUp(self):
        self.cid='a'*64;self.template='fixed inspect format';self.clock=types.SimpleNamespace(
            time=lambda:110,monotonic=lambda:50,clock_gettime=lambda which:70,CLOCK_BOOTTIME=7)
        self.policy={'max_calls':8,'max_wall_seconds':90,'until_utc':200,'until_boot':200,'until_mono':200}
        self.root_identity=('sealed',);self.release={'policy':'fixture'}
        self.lease=types.SimpleNamespace(record={'pid':42,'starttime':'birth','request_core_sha256':'core'},
                                         load_owned=lambda:b'lease')
        env={'_fail':fail,'re':re,'SDK13_INSPECT_TEMPLATE':self.template,'time':self.clock,
             '_sdk13_root':lambda ref,path:(self.release,self.root_identity),
             '_sdk13_containment_policy':lambda release,request:self.policy,
             'SDK13_RELEASE':Path('/synthetic/release'),'_request_core_hash':lambda request:'core',
             '_proc_starttime':lambda pid:'birth','os':types.SimpleNamespace(getpid=lambda:42),
             'hashlib':hashlib,'_assert_owned_container':lambda info,cid:fail(info.get('Id')==cid,'wrong owner')}
        self.env=extract(owner,{'_sdk13_containment_args','SDK13Containment'},env)
        self.state=self.env['SDK13Containment']({'compile_only_release':'ref'},{'release':self.root_identity},
                                                 self.lease,self.cid)

    def test_exact_owned_containment_after_stop_or_expiry(self):
        # STOP/compile-expiry are deliberately not authority for new work;
        # the separate limited policy permits only the captured exact CID.
        normal=extract(owner,{'_sdk13_capture_fresh','_sdk13_evaluate_effect'},
                       {'_fail':fail,'SDK13_UTC':1000,'SDK13_BOOT':1000,'SDK13_MONO':1000,
                        'SDK13_BOOT_ID':'boot'})
        facts={'service_status':'NO_NEW_REJECTION','paid_fallback':False,'weekly_used_percent':67,
               'weekly_observed_utc':90,'expiry_utc':100}
        with self.assertRaises(ValueError):
            normal['_sdk13_evaluate_effect']('r','r',['c'],['c'],facts,110,70,50,'boot',True)
        self.state.gate(('inspect','--format',self.template,self.cid));self.state.confirm({'Id':self.cid})
        result=self.state.gate(('stop','--time','15',self.cid))
        self.assertEqual(result['phase'],'containment-stop')
        self.assertTrue(result['limited_retirement_only'])

    def test_wrong_cid_start_and_unauthenticated_mutation_rejected(self):
        for argv in [('start',self.cid),('stop','--time','15','b'*64),('stop','--time','15',self.cid)]:
            with self.subTest(argv=argv),self.assertRaises(ValueError):self.state.gate(argv)

    def test_release_and_lease_identity_drift_rejected(self):
        self.root_identity=('changed',)
        with self.assertRaises(ValueError):self.state.gate(('inspect','--format',self.template,self.cid))
        self.root_identity=('sealed',);self.lease.record['pid']=43
        with self.assertRaises(ValueError):self.state.gate(('inspect','--format',self.template,self.cid))

    def test_absolute_deadline_and_counter_bound(self):
        self.policy['until_utc']=109
        with self.assertRaises(ValueError):self.state.gate(('inspect','--format',self.template,self.cid))
        self.policy['until_utc']=200;self.state.calls=8
        with self.assertRaises(ValueError):self.state.gate(('inspect','--format',self.template,self.cid))

    def test_root_document_mode_matches_parent_and_owner(self):
        owner_mode=extract(owner,{'_sdk13_root_file_mode'},{})['_sdk13_root_file_mode']
        parent_mode=extract(parent,{'root_file_mode'},{})['root_file_mode']
        for fn in (owner_mode,parent_mode):
            self.assertTrue(fn(0,1000,0o640,1000))
            self.assertTrue(fn(0,0,0o600,0))
            for args in [(0,0,0o640,1000),(0,1000,0o660,1000),(0,1000,0o644,1000),
                         (1000,1000,0o640,1000),(0,0,0o600,1000)]:
                with self.subTest(args=args):self.assertFalse(fn(*args))

    def test_extended_acl_and_acl_read_errors_rejected(self):
        for tree,name,error in ((owner,'_sdk13_no_access_acl',ValueError),(parent,'no_access_acl',ValueError)):
            fake=types.SimpleNamespace(getxattr=lambda *args:b'extended')
            fn=extract(tree,{name},{'os':fake,'errno':errno,'OwnerError':ValueError})[name]
            with self.assertRaises(error):fn(4)
            def missing(*args):raise OSError(errno.ENODATA,'absent')
            fake.getxattr=missing;fn(4)
            def denied(*args):raise OSError(errno.EACCES,'denied')
            fake.getxattr=denied
            with self.assertRaises(OSError):fn(4)

    def test_stale_final_unlink_gate_prevents_unlink(self):
        cls=next(n for n in owner.body if isinstance(n,ast.ClassDef) and n.name=='CompileLease')
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='release_accepted')
        calls=[];record={'device':1,'inode':2,'operation':'op','request_core_sha256':'core'}
        raw=json.dumps(record).encode()
        fake_os=types.SimpleNamespace(O_RDONLY=0,O_DIRECTORY=0,O_NOFOLLOW=0,
             open=lambda *a,**k:4, fstat=lambda fd:types.SimpleNamespace(st_dev=1,st_ino=2,st_size=len(raw)),
             read=lambda *a:raw,close=lambda fd:None,unlink=lambda *a,**k:calls.append('unlink'),
             fsync=lambda fd:None)
        env={'_fail':fail,'os':fake_os,'hashlib':hashlib,'json':json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<synthetic>','exec'),env)
        lease=types.SimpleNamespace(path=Path('/synthetic/lease'),record=record,load_owned=lambda:raw)
        acceptance={'status':'ACCEPTED_COMPILE_ONLY_PHYSICAL_RETIREMENT','operation':'op',
                    'request_core_sha256':'core','lease_sha256':hashlib.sha256(raw).hexdigest()}
        def stale():raise ValueError('synthetic stale acceptance')
        with self.assertRaisesRegex(ValueError,'stale'):env['release_accepted'](lease,acceptance,unlink_gate=stale)
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
