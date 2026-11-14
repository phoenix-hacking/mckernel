"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure AST extraction and synthetic mount/environment/daemon regression sources.
No owner, driver main, Docker, compiler, daemon query or actual lease is invoked.
"""
import ast
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest

HERE=Path(__file__).parent
owner=ast.parse((HERE/'sdk13_compile_image_owner.py').read_text())
driver=ast.parse((HERE/'sdk13_four_command_driver.py').read_text())


def extract(tree,names,values):
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes}==set(names)
    env=dict(values)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])), '<synthetic-only>', 'exec'),env)
    return env


def fail(value,why):
    if not value:raise ValueError(why)


class EffectiveViewFixture(unittest.TestCase):
    def setUp(self):
        self.env=extract(driver,{'decode_mount_path','validate_mountinfo','masked','read_regular','validate_tree'},
                         {'MAX_MOUNTINFO':4*1024*1024,'MAX_ENTRIES':1000,'MAX_BYTES':10*1024*1024,
                          'Path':Path,'os':os,'stat':stat,'hashlib':hashlib})
        self.mounts={'/src':True,'/src/kernel/rust':True,'/work':False}
        self.valid=(b'1 0 0:1 / /src ro,relatime - ext4 dev rw\n'
                    b'2 1 0:1 / /src/kernel/rust ro,relatime - ext4 dev rw\n'
                    b'3 0 0:1 / /work rw,relatime - ext4 dev rw\n')

    def test_valid_effective_mount_table(self):
        self.assertEqual(self.env['validate_mountinfo'](self.valid,self.mounts),3)

    def test_wrong_mask_unlisted_and_duplicate_mount_rejected(self):
        cases=[self.valid.replace(b'/src/kernel/rust ro,',b'/src/kernel/rust rw,'),
               self.valid+b'4 1 0:1 / /src/kernel/hidden ro - ext4 dev rw\n',
               self.valid+b'4 1 0:1 / /src ro - ext4 dev rw\n']
        for data in cases:
            with self.subTest(data=data),self.assertRaises(ValueError):
                self.env['validate_mountinfo'](data,self.mounts)

    def test_shadowed_source_cannot_hide_unexpected_unmounted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'kernel').mkdir();(root/'kernel'/'masked').mkdir()
            (root/'kernel'/'masked'/'replacement').write_bytes(b'overlay')
            (root/'kernel'/'keep').write_bytes(b'correct')
            sha=hashlib.sha256(b'correct').hexdigest()
            rows=[{'relative':'kernel','kind':'dir'}, {'relative':'kernel/masked','kind':'dir'},
                  {'relative':'kernel/masked/original','kind':'file','bytes':3,'sha256':'0'*64},
                  {'relative':'kernel/keep','kind':'file','bytes':7,'sha256':sha}]
            self.env['validate_tree'](str(root),{'entries':rows},[str(root/'kernel'/'masked')],{'entries':0,'bytes':0})
            (root/'kernel'/'extra').write_bytes(b'unlisted')
            with self.assertRaises(ValueError):
                self.env['validate_tree'](str(root),{'entries':rows},[str(root/'kernel'/'masked')],{'entries':0,'bytes':0})

    def test_inherited_environment_rejected_before_file_io(self):
        fake=types.SimpleNamespace(environ={'LD_PRELOAD':'bad'})
        check=extract(driver,{'validate_effective_view'}, {'os':fake,'CLEAN_ENV':{'PATH':'/usr/bin:/bin'}})
        with self.assertRaisesRegex(ValueError,'environment differs'):
            check['validate_effective_view']({},'a'*64,'b'*64,(1,2,3),'c'*64)

    def test_source_orders_view_check_before_compiler_and_clean_env(self):
        main=next(n for n in driver.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        text=ast.unparse(main)
        self.assertLess(text.index('validate_effective_view('),text.index('subprocess.Popen('))
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and n.func.attr=='Popen']
        self.assertEqual(len(calls),1)
        self.assertIn('env=dict(CLEAN_ENV)',ast.unparse(calls[0]))

    def test_redacted_inspect_never_serializes_raw_config_env(self):
        text=(HERE/'sdk13_compile_image_owner.py').read_text()
        section=text[text.index('SDK13_ENV_TEMPLATE='):text.index('def _sdk13_prepare_work')]
        self.assertIn('range .Config.Env',section)
        self.assertNotIn('{{json .Config.Env}}',section)
        self.assertIn('SDK13_ENV_MARKERS',section)


class DaemonFixture(unittest.TestCase):
    def test_changed_daemon_birth_rejected(self):
        birth=iter([100,101]); objects={
            '/proc/42/exe':types.SimpleNamespace(st_dev=1,st_ino=2),
            '/var/run/docker.sock':types.SimpleNamespace(st_dev=3,st_ino=4,st_mode=stat.S_IFSOCK)}
        fake=types.SimpleNamespace(stat=lambda p:objects[p])
        env=extract(owner,{'_sdk13_daemon_identity'}, {'_proc_starttime':lambda pid:next(birth),
                                                     '_fail':fail,'os':fake,'stat':stat})
        expected={'pid':42,'starttime':100,'exe_device':1,'exe_inode':2,'socket_device':3,'socket_inode':4}
        with self.assertRaisesRegex(ValueError,'birth changed'):
            env['_sdk13_daemon_identity'](expected)

    def test_stable_daemon_birth_accepted_by_pure_matcher(self):
        objects={'/proc/42/exe':types.SimpleNamespace(st_dev=1,st_ino=2),
                 '/var/run/docker.sock':types.SimpleNamespace(st_dev=3,st_ino=4,st_mode=stat.S_IFSOCK)}
        fake=types.SimpleNamespace(stat=lambda p:objects[p])
        env=extract(owner,{'_sdk13_daemon_identity'}, {'_proc_starttime':lambda pid:100,
                                                     '_fail':fail,'os':fake,'stat':stat})
        expected={'pid':42,'starttime':100,'exe_device':1,'exe_inode':2,'socket_device':3,'socket_inode':4}
        self.assertEqual(env['_sdk13_daemon_identity'](expected),expected)


if __name__=='__main__':unittest.main()
