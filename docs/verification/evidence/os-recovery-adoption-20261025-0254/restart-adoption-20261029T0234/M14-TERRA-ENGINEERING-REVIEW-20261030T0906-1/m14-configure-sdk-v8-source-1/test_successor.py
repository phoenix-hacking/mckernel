#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic Python children only; no configure, Kbuild, owner launch or container.
"""
import ast, importlib.util, json, os, pathlib, sys, unittest
P=pathlib.Path(__file__).parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v=module('validator',P/'validator.successor.py'); d=module('driver',P/'driver.successor.py')
class Gates(unittest.TestCase):
    def cmds(self):
        a=['/usr/bin/cmake','-S','/src','-B','/work/output/build','-G','Unix Makefiles',
           '-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=ON','-DKERNEL_DIR=/out/build',
           '-DUNAME_R=synthetic','-DMCKERNEL_M14_EXPECTED_UNAME_R=synthetic',
           '-DMCKERNEL_M14_EXPECTED_MAP_KERNEL_START=0x1234','-DMCKERNEL_M14_EXPECTED_MAKE_SHA256='+'a'*64,
           '-DKBUILD_MAKE_FLAGS=CC=x','-DMCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS=CC=x']
        pairs={'--make-status':'0','--module':'/work/output/build/tmp.resolve_MODULES_END/driver.ko',
               '--kernel-release':'/out/build/include/config/kernel.release','--uts-release-header':'/out/build/include/generated/utsrelease.h',
               '--uname-r':'synthetic','--expected-map':'0x1234','--cmake-cache':'/work/output/build/CMakeCache.txt',
               '--compile-commands':'/work/output/build/compile_commands.json','--expected-kernel-dir':'/out/build',
               '--expected-build-dir':'/work/output/build'}
        b=['/usr/bin/python3','-I','-B','/src/scripts/verify_m14_elf.py']
        for k,x in pairs.items():b += [k,x]
        return [{'stage':'Configure ON composite','cwd':'/work','argv':a},{'stage':'Post-generation verification','cwd':'/work','argv':b}]
    def test_selector_accept_and_rejections(self):
        commands=self.cmds();v._selectors({'commands':commands},{'commands':commands})
        for kind in ('missing','off','duplicate','uname','post','order','held'):
            c=self.cmds()
            if kind=='missing': c[0]['argv'].remove('-DUNAME_R=synthetic')
            if kind=='off': c[0]['argv'][7]='-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=OFF'
            if kind=='duplicate': c[0]['argv'].append('-DUNAME_R=')
            if kind=='uname': c[0]['argv'][10]='-DMCKERNEL_M14_EXPECTED_UNAME_R=other'
            if kind=='post': c[1]['argv'][5]='1'
            if kind=='order': c.reverse()
            if kind=='held': c[0]['argv'].append('EXECVE_TRANSFER')
            with self.subTest(kind=kind),self.assertRaises(ValueError):v._selectors({'commands':c},{'commands':c})
    def test_mount_graph(self):
        rows=[('/tmp/work','/work',False),('/tmp/src','/src',True),('/tmp/rust','/src/kernel/rust',True),('/tmp/nightly','/nightly',True),('/tmp/out','/out',True)]
        v._mount_graph(rows)
        for bad in (rows[:-1],rows[:-1]+[('/tmp/out','/out',False)],rows+[('/tmp/other','/out/build',True)],rows+[('/tmp/other','/src',True)]):
            with self.assertRaises(ValueError):v._mount_graph(bad)
    def test_entry_points_remain_closed(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'):v._collect({},None,None,None)
        with self.assertRaisesRegex(RuntimeError,'SOURCE_ONLY'):d.require_source_binding()
        tree=ast.parse((P/'owner.successor.py').read_text())
        owner=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SDK13ImageOwner')
        run=next(x for x in owner.body if isinstance(x,ast.FunctionDef) and x.name=='run')
        main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main')
        self.assertIsInstance(run.body[0],ast.Raise);self.assertIsInstance(main.body[0],ast.Raise)

class Stages(unittest.TestCase):
    def run_case(self,name,first,second,timeout=3):
        root=P/'cases'/name;root.mkdir(parents=True,exist_ok=False)
        d.EVIDENCE=root/'evidence';d.PER_STAGE_TIMEOUT=timeout
        commands=[{'stage':'Configure ON composite','cwd':str(root),'argv':[sys.executable,'-c',first]},
                  {'stage':'Post-generation verification','cwd':str(root),'argv':[sys.executable,'-c',second]}]
        d.require_source_binding=lambda:None
        d.read_profile=lambda:({},commands)
        d.validate_effective_view=lambda *a:{'status':'SYNTHETIC_ONLY'}
        old=sys.argv;sys.argv=['driver','a'*64,'b'*64,'1','1','1','c'*64]
        try:rc=d.main()
        finally:sys.argv=old
        return rc,root/'evidence'
    def test_success(self):
        rc,p=self.run_case('success','print("configure fake")','print("verify fake")')
        self.assertEqual(rc,0); self.assertEqual(json.loads((p/'result.json').read_text())['artifact_validation'],'POST_GENERATION_STAGE_EXITED_ZERO_ONLY')
        self.assertTrue(json.loads((p/'stage-2-result.json').read_text())['direct_wait_completed'])
    def test_failure_prevents_next_stage(self):
        rc,p=self.run_case('failure','raise SystemExit(7)','print("must not run")')
        self.assertEqual(rc,1);self.assertFalse((p/'stage-2-intent.json').exists());self.assertEqual(json.loads((p/'stage-1-result.json').read_text())['returncode'],7)
    def test_verifier_failure_preserved(self):
        rc,p=self.run_case('verify_fail','pass','raise SystemExit(8)')
        self.assertEqual(rc,1);self.assertEqual(json.loads((p/'stage-2-result.json').read_text())['returncode'],8)
    def test_timeout_is_unknown(self):
        rc,p=self.run_case('timeout','import time; time.sleep(3)','pass',0.05)
        r=json.loads((p/'stage-1-result.json').read_text());self.assertEqual(rc,1);self.assertTrue(r['timed_out']);self.assertEqual(r['descendant_closure'],'UNKNOWN');self.assertFalse((p/'stage-2-intent.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
