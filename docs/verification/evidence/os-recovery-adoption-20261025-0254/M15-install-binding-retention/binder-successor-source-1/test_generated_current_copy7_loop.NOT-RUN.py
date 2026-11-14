"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap source-only regression: no binder main/publication/query/install executes.
"""
import ast,copy,hashlib,json,os,stat,unittest
from pathlib import Path
from unittest import mock
import builtins
SOURCE=Path(__file__).with_name('bind_install_recorded_COPY7_authority.CURRENT-READER-LOOP.NOT-RELEASED.py')
class RecordedCopy7(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text())
  names={'FIELDS','COPY7_AUTHORITY'};functions={'need','digest','read','require_copy7_identity'}
  nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in functions) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
  self.env=dict(Path=Path,hashlib=hashlib,json=json,os=os,stat=stat)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<selected-readonly-guards>','exec'),self.env)
  refs=self.env['COPY7_AUTHORITY'];self.ph=json.loads(self.env['read'](refs['physical_acceptance']));self.post=json.loads(self.env['read'](refs['current_postjoin']));self.normal=json.loads(self.env['read'](refs['normal_retirement']))
 def check(self):
  original_open=os.open
  attempted=[]
  def readonly_open(path,flags,*args,**kwargs):
   if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
    attempted.append(str(path));raise AssertionError('pure test attempted write:'+str(path))
   return original_open(path,flags,*args,**kwargs)
  def forbidden(*args,**kwargs):
   attempted.append(str(args));raise AssertionError('pure test attempted filesystem mutation')
  with mock.patch.object(os,'open',readonly_open), mock.patch.object(Path,'write_text',forbidden), mock.patch.object(Path,'write_bytes',forbidden), mock.patch.object(Path,'mkdir',forbidden), mock.patch.object(os,'rename',forbidden), mock.patch.object(os,'unlink',forbidden):
   try:self.env['require_copy7_identity'](self.ph,self.post,self.normal)
   finally:self.assertEqual(attempted,[])

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


class GeneratedCurrentCopy7Loop(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text())
  names={'CURRENT_COPY7_LOOP_PREDECESSOR','CURRENT_COPY7_LOOP_SUCCESSOR','COPY7_AUTHORITY','SOURCES'}
  nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ('need','adapt_current_copy7_reader_loop')) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
  self.env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<selected-current-query-transform>','exec'),self.env)
  self.original=Path(self.env['SOURCES']['query']['path']).read_text()
  self.generated=self.env['adapt_current_copy7_reader_loop'](self.original)
  self.block=self.env['CURRENT_COPY7_LOOP_SUCCESSOR']
  self.code=compile(self.block,'<generated-exact-current-normal_cfg-loop>','exec')
  refs=self.env['COPY7_AUTHORITY'];self.ph=json.loads(Path(refs['physical_acceptance']['path']).read_bytes());self.post=json.loads(Path(refs['current_postjoin']['path']).read_bytes());self.normal=json.loads(Path(refs['normal_retirement']['path']).read_bytes())
 def run_block(self,mutator=None):
  import types
  def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
  joins={key:self.post[key+'_whole_join'] for key in ('proc','mutex')}
  output_paths={}
  for key,ref in joins.items():
   joined=json.loads(Path(ref['path']).read_bytes());output_paths[joined['captures']['stdout']['path']]=key
  def bound(ref):
   raw=Path(ref['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);v=json.loads(raw)
   if mutator and ref['path'] in output_paths:mutator(output_paths[ref['path']],v)
   return v
  owner=types.SimpleNamespace(safe_path=lambda p,unused:Path(p),bound=bound,host=types.SimpleNamespace(digest=digest),BOOT=self.ph['boot_id'])
  env={'owner':owner,'normal_cfg_links':joins,'normal_cfg':copy.deepcopy(self.ph),'normal_cfg_normal_ref':self.env['COPY7_AUTHORITY']['normal_retirement'],'normal_cfg_normal':self.normal}
  # The generated loop has read-only mocked owner services; no binder main or effects.
  forbidden=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('unexpected mutation'))
  with mock.patch.object(Path,'write_bytes',forbidden),mock.patch.object(Path,'write_text',forbidden),mock.patch.object(Path,'mkdir',forbidden),mock.patch.object(os,'rename',forbidden),mock.patch.object(os,'unlink',forbidden):
   exec(self.code,env)
 def test_generated_current_block_accepts_actual_captured_bytes(self):self.run_block()
 def test_historical_query_bytes_unchanged(self):
  self.assertEqual(self.generated.replace(self.env['CURRENT_COPY7_LOOP_SUCCESSOR'],self.env['CURRENT_COPY7_LOOP_PREDECESSOR']),self.original)
  self.assertEqual(self.generated.count('PASS_COPY7_COMPLETE_PROC_OBSERVATION'),1)
  self.assertEqual(self.generated.count('PASS_COPY7_MUTEX_HELD_PHYSICAL_POSTFLIGHT'),1)
 def test_current_loop_negative_controls(self):
  cases=[('proc',('status',),'CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION'),('proc',('proc','status'),'INCOMPLETE'),('proc',('proc','boot_id'),'WRONG'),('proc',('proc','failure'),{}),('proc',('proc','publishers'),[[1,'1','publisher']]),('proc',('proc','snapshots'),[]),('proc',('known_owner','pid'),1),('proc',('known_cleanup','pid'),1),('proc',('waiter_pids',),[]),('mutex',('status',),'PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE'),('mutex',('root_lock','inode'),5),('mutex',('root_lock','device'),1),('mutex',('root_lock','mode'),'0o600'),('mutex',('absence_paths',),[]),('mutex',('container_absent','nonce'),'WRONG'),('mutex',('cleanup','starttime'),'0'),('mutex',('artifact_native_acceptance',),True),('mutex',('preserved_inventory_rows',),0),('mutex',('preserved_selected_files',),0),('mutex',('journal_events',),8),('mutex',('transaction_records',),[]),('mutex',('proc','failure'),{})]
  for wanted,path,replacement in cases:
   with self.subTest(reader=wanted,path=path):
    def mutate(key,value):
     if key==wanted:
      target=value
      for part in path[:-1]:target=target[part]
      target[path[-1]]=replacement
    with self.assertRaises(AssertionError):self.run_block(mutate)
 def test_ambiguous_current_predecessor_is_refused(self):
  with self.assertRaises(ValueError):self.env['adapt_current_copy7_reader_loop'](self.original+self.env['CURRENT_COPY7_LOOP_PREDECESSOR'])
if __name__=='__main__':unittest.main()
