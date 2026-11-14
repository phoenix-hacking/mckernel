"""Functional-only synthetic permission-view checks; source only, unrun."""
import ast
import hashlib
import importlib.util
import stat
import types
import unittest
from pathlib import Path

HERE=Path(__file__).parent
SOURCE=HERE.parent/'root-install-direct-child-successor-4'/'install_source_closure.py'
SOURCE_SHA='6fa1cca87cb3e5b2cfdfc746875dd3909bfa084052b9344d48931de959e68888'
spec=importlib.util.spec_from_file_location('fixture_permission_view',HERE/'role_fd_budget.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def row(device,inode,mode):
    return types.SimpleNamespace(st_dev=device,st_ino=inode,st_mode=mode,st_uid=1000)


def actual_guard(proxy):
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('actual installer source differs')
    tree=ast.parse(raw,filename=str(SOURCE))
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dir_identity']
    if len(selected)!=1:raise ValueError('actual private-root guard missing')
    def fail(message):raise ValueError(message)
    scope={'os':types.SimpleNamespace(fstat=lambda fd:proxy),'stat':stat,
           'ident':lambda value:{'device':value.st_dev,'inode':value.st_ino},'fail':fail}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'),scope)
    return scope['dir_identity'](123,{'device':9,'inode':22},True)


class PermissionView(unittest.TestCase):
    def test_exact_private_root_0700_is_preserved_and_actual_guard_accepts(self):
        real=row(9,22,stat.S_IFDIR|0o700);view=fixture.StatProxy(real,(9,22))
        self.assertEqual(stat.S_IMODE(view.st_mode),0o700);self.assertEqual(view.st_uid,0)
        actual_guard(view)
    def test_exact_private_root_0701_is_preserved_and_actual_guard_rejects(self):
        real=row(9,22,stat.S_IFDIR|0o701);view=fixture.StatProxy(real,(9,22))
        self.assertEqual(stat.S_IMODE(view.st_mode),0o701)
        with self.assertRaisesRegex(ValueError,'root-private'):actual_guard(view)
    def test_distinct_ancestor_device_or_inode_uses_traversable_view(self):
        for device,inode in ((9,23),(10,22)):
            view=fixture.StatProxy(row(device,inode,stat.S_IFDIR|0o700),(9,22))
            self.assertEqual(stat.S_IMODE(view.st_mode),0o701)
    def test_file_mode_is_unchanged(self):
        view=fixture.StatProxy(row(9,22,stat.S_IFREG|0o640),(9,22))
        self.assertEqual(stat.S_IMODE(view.st_mode),0o640)


if __name__=='__main__':unittest.main()
