"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure future regression; no binder main or source publication executes.
"""
import ast
from pathlib import Path
import unittest
SOURCE=Path(__file__).with_name('bind_install_actual_COPY7_authority_once.WITH-PUBLISHER.NOT-RELEASED.py')
class Copy7Identity(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text())
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('need','require_copy7_identity')]
  self.env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-copy7-identity>','exec'),self.env)
  self.ph={'reviewer':'/root/recovery_review','owner_pid':413643,'owner_starttime':'68359948'}
  self.post={'owner_pid':413643,'owner_starttime':'68359948'}
  self.normal={'schema':'fp-save-image.cleanup-result.v1','terminal':True,'container_absent':True,'container_id':'0e41e2cf1f390c77108eafef7d031a1d1e561485a38ed7524f77d953e0c62d70','boot_id':'7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'}
 def check(self):self.env['require_copy7_identity'](self.ph,self.post,self.normal)
 def test_exact_identity(self):self.check()
 def test_each_wrong_identity_rejected(self):
  for label in ('ph','post','normal'):
   for key,value in getattr(self,label).copy().items():
    with self.subTest(row=label,key=key):
     getattr(self,label)[key]=False if value is True else 'WRONG'
     with self.assertRaises(ValueError):self.check()
     getattr(self,label)[key]=value
 def test_historical_reviewer_stays_rejected(self):
  self.ph['reviewer']='/root/native235_release_review'
  with self.assertRaises(ValueError):self.check()
if __name__=='__main__':unittest.main()
