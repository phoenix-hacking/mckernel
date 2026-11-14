"""Mocked direct install model regressions; no process, root or native actions."""
import importlib.util
import pathlib
import types
import unittest

spec=importlib.util.spec_from_file_location('completion_under_test',str(pathlib.Path(__file__).with_name('install_completion.py')))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def hex64(value):
    return type(value) is str and len(value)==64 and all(x in '0123456789abcdef' for x in value)


class DirectModel(unittest.TestCase):
    def setUp(self):
        c.SOURCE_PINS={'issuer_sha256':'1'*64,'completion_sha256':'2'*64,'ipc_sha256':'3'*64,'review_sha256':'4'*64}
        self.install=types.SimpleNamespace(CLOSURE_SHA256='5'*64,hex64=hex64)
        self.template={'nonce':'6'*64,'installer_sha256':'7'*64,'interpreter':{'sha256':'8'*64}}
        self.intent={'wait_literal_sha256':'9'*64}
        self.row={'version':1,'record_type':'ROOT_INSTALL_DIRECT_MODEL_APPROVAL_V1','scope':'ROOT_CODE_INSTALL_ONLY',
                  'nonce':'6'*64,'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN',
                  'status':'APPROVED_KNOWN_ROLE_MODEL','model_sha256':'98ea72583a41f747f01c5bdb04b545319fc08cedf443366a6c2637a35562ed04',
                  'issuer_sha256':'1'*64,'completion_sha256':'2'*64,'installer_sha256':'7'*64,'wait_sha256':'9'*64,
                  'ipc_sha256':'3'*64,'runtime_sha256':'8'*64,'source_closure_sha256':'5'*64,'review_sha256':'4'*64,
                  'trusted_platform':'DIRECT_CPYTHON_LIBC_KERNEL'}

    def accept(self):return c.verify_creation_model_value(self.install,{'creation_model_approval':self.row},self.template,self.intent)

    def test_exact_model_keeps_unknown(self):
        self.assertEqual(self.accept()['global_descendants'],'UNKNOWN')

    def test_old_timeout_model_is_rejected(self):
        self.row['record_type']='ROOT_INSTALL_CREATION_MODEL_APPROVAL_V1'
        with self.assertRaises(ValueError):self.accept()

    def test_changed_ipc_is_rejected(self):
        self.row['ipc_sha256']='0'*64
        with self.assertRaises(ValueError):self.accept()

    def test_native_currentfree_cannot_be_inferred(self):
        self.row['native_currentfree']=True
        with self.assertRaises(ValueError):self.accept()

    def test_global_empty_cannot_be_inferred(self):
        self.row['global_descendants']='EMPTY'
        with self.assertRaises(ValueError):self.accept()

    def test_terminal_requires_real_integer_wait_and_zero(self):
        result={'installer_wait_status':False,'installer':{'pid':42,'birth':'7','pgid':42},
                'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN'}
        with self.assertRaises(ValueError):c.verify_terminal_result(result,42,'7',0)
        result['installer_wait_status']=0
        self.assertEqual(c.verify_terminal_result(result,42,'7',0)['installer_direct_wait_status'],0)
        with self.assertRaises(ValueError):c.verify_terminal_result(result,42,'7',256)

if __name__=='__main__':unittest.main()
