"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap source-only regression: no binder main/publication/query/install executes.
"""
import ast,copy,hashlib,json,os,stat,unittest
from pathlib import Path
SOURCE=Path(__file__).with_name('bind_install_recorded_COPY7_authority_once.WITH-PUBLISHER.NOT-RELEASED.py')
class RecordedCopy7(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text())
  names={'FIELDS','COPY7_AUTHORITY'};functions={'need','digest','read','require_copy7_identity'}
  nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in functions) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
  self.env=dict(Path=Path,hashlib=hashlib,json=json,os=os,stat=stat)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<selected-readonly-guards>','exec'),self.env)
  refs=self.env['COPY7_AUTHORITY'];self.ph=json.loads(self.env['read'](refs['physical_acceptance']));self.post=json.loads(self.env['read'](refs['current_postjoin']));self.normal=json.loads(self.env['read'](refs['normal_retirement']))
 def check(self):self.env['require_copy7_identity'](self.ph,self.post,self.normal)
 def test_actual_recorded_schema(self):self.check()
 def test_each_pinned_identity_rejects_change(self):
  fields={'ph':['schema','status','reviewer','owner_pid','owner_starttime','cleanup_pid','cleanup_starttime','reported_parent_pid','container_id','closed_nonce','boot_id','consumed_cleanup_release_sha256','journal_events','preserved_selected_files','preserved_inventory_rows'],'post':['schema','reviewer','implementation_ownership','owner_pid','owner_starttime','cleanup_pid','cleanup_starttime','reported_parent_pid','container_id','boot_id'],'normal':['schema','terminal','container_absent','container_id','boot_id','release_sha256']}
  for label,keys in fields.items():
   for key in keys:
    row=getattr(self,label);saved=row[key]
    with self.subTest(row=label,key=key):
     row[key]=True if saved is False else False if saved is True else 'WRONG'
     with self.assertRaises((ValueError,KeyError)):self.check()
     row[key]=saved
 def test_current_boolean_is_not_fabricated(self):
  self.assertNotIn('current_live_postjoin_accepted_non_null',self.ph)
  self.assertEqual(self.post['status'],'ACCEPTED_NON_NULL')
 def test_raw_and_canonical_release_hashes_are_distinct(self):
  self.assertNotEqual(self.ph['consumed_cleanup_release_sha256'],self.normal['release_sha256'])
if __name__=='__main__':unittest.main()
