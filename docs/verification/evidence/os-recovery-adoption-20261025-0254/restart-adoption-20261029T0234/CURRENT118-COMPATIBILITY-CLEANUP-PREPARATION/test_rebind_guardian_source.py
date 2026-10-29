"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast, copy, hashlib, importlib.util, unittest
p=Path(__file__).with_name('rebind_guardian_source.py');s=importlib.util.spec_from_file_location('rebinder',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
 b=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',TEST_ONLY=True)
 for k,r in [('armed','ACTUAL-CONTROLS-ARMED.json'),('config','armed-controller/CONFIG.json'),('packet','armed-controller/FROZEN-PACKET.json'),('bridge','armed-controller/bridge-start.json')]:b[k]=dict(path=str(m.NEWSC/r),bytes=100,sha256='a'*64)
 actors={k:dict(pid=3000000+i,start=str(110000000+i),ppid=1311,state='S') for i,k in enumerate(('watcher','worker','server','guardian','monitor'))};actors['worker']['ppid']=actors['watcher']['pid'];actors['server']['ppid']=actors['worker']['pid'];actors['phone']=dict(pid=1894242,start='96505809',ppid=1311,state='S')
 arm=dict(status='LIVE_CONTINUED_CAMPAIGN_GUARDIAN_20MIN_STEERING_AND_RETAINED_PHONE',thread_id='01a18582-1fc6-77b1-bfb6-15c86483f579',phase='running',goal_status='active',native_release=False,guardian_packet_sha256='a'*64,original_window_unchanged_sha256=m.WINDOW_SHA,steering_interval_seconds=1200,auxiliary_leases_held=dict(guardian=True,monitor=True,phone=True),earliest_control_caps=dict(deadline_epoch=m.UTC,monotonic_deadline=m.MONO,boot_deadline=m.BCAP),credit_budget=dict(id=m.RUN,budget=str(m.CEILING),spent=str(m.FLOOR)),actors=actors)
 config=dict(expected_thread=arm['thread_id'],credit_run_id=m.RUN,credit_ceiling=str(m.CEILING),credit_spent_floor=str(m.FLOOR),included_first=True,automatic_credit_purchase=False,api_key_billing=False,initial_watch_clock=dict(boot_id=m.BOOT,deadline=m.UTC,watcher_pid=actors['watcher']['pid'],watcher_start=actors['watcher']['start'],boot_deadline=m.BCAP,watcher_cutoff_lower=m.MONO))
 bridge=dict(deadline=m.UTC,pid=actors['guardian']['pid'],birth=dict(pid=actors['guardian']['pid'],start=actors['guardian']['start'],ppid=3000999))
 return b,arm,config,dict(private={},canonical={}),bridge
class Tests(unittest.TestCase):
 def test_validation_function_ast_unchanged_except_declared_bindings(self):
  original=ast.parse(m.ORIGINAL.read_text());new=ast.parse(m.render(m.ORIGINAL.read_text(),*fixture()))
  replacements={'GUARDIAN_LAUNCH_PPID':'2111551','GUARDIAN_RECORDED_PPID':'1311','EXPECTED_ACTORS':"dict(INITIAL, guardian=(2111552, '101236067'), monitor=(2111966, '101243270'), phone=(1894242, '96505809'))",'AUX_RECORDED_PPIDS':'dict(guardian=1311,monitor=2111963,phone=1311)'}
  class Normalize(ast.NodeTransformer):
   def visit_Name(self,node):
    return ast.parse(replacements[node.id],mode='eval').body if node.id in replacements else node
  oldfunc={n.name:ast.dump(n,include_attributes=False) for n in original.body if isinstance(n,ast.FunctionDef)}
  newfunc={n.name:ast.dump(Normalize().visit(n),include_attributes=False) for n in new.body if isinstance(n,ast.FunctionDef)}
  self.assertEqual(oldfunc,newfunc)
 def test_missing_actual_receipt_refuses(self):
  with self.assertRaises((FileNotFoundError,ValueError)):m.authenticate(dict(path=str(m.NEWSC/'MISSING-TEST_ONLY-ARM.json'),bytes=1,sha256='a'*64))
 def test_pure_current_fixture_and_render(self):
  f=fixture();m.validate_inputs(*f);source=m.render(m.ORIGINAL.read_text(),*f);namespace={};exec(compile(source,'TEST_ONLY','exec'),namespace)
  self.assertEqual(namespace['THREAD'],f[1]['thread_id']);self.assertEqual(namespace['ARM_RECEIPT_REF'],f[0]['armed']);self.assertEqual(namespace['CONFIG_SHA'],f[0]['config']['sha256']);self.assertEqual(namespace['PACKET_SHA'],f[0]['packet']['sha256']);namespace['validate_control_config'](f[2])
  observed={a['pid']:dict(a) for a in f[1]['actors'].values()};observed[1311]=dict(pid=1311,start='596',ppid=1,comm='systemd',state='S');namespace['validate_armed'](f[1],observed.get)
  for name,actor in f[1]['actors'].items():
   for field,value in [('pid',actor['pid']+100),('start','999'),('ppid',999)]:
    bad=copy.deepcopy(f[1]);bad['actors'][name][field]=value
    with self.subTest(name=name,field=field),self.assertRaises(ValueError):namespace['validate_armed'](bad,observed.get)
 def test_old_receipt_rejected(self):
  f=list(fixture());f[0]['armed']['path']=str(m.NEWSC.parent/'restart-20261028-1200-pacific-1/ACTUAL-CONTROLS-ARMED.json')
  with self.assertRaises(ValueError):m.validate_inputs(*f)
 def test_extended_caps_credit_and_thread_rejected(self):
  for key in ('monotonic_deadline','boot_deadline','deadline_epoch'):
   f=fixture();f[1]['earliest_control_caps'][key]+=1
   with self.subTest(key=key),self.assertRaises(ValueError):m.validate_inputs(*f)
  for key,val in [('id','another-run'),('budget','57775'),('spent','0')]:
   f=fixture();f[1]['credit_budget'][key]=val
   with self.subTest(key=key),self.assertRaises(ValueError):m.validate_inputs(*f)
  f=fixture();f[2]['expected_thread']='01a183ec-72e5-7400-8f48-b4efb8725520'
  with self.assertRaises(ValueError):m.validate_inputs(*f)
 def test_tighter_caps_preserved(self):
  f=fixture();f[1]['earliest_control_caps']['boot_deadline']-=2;f[1]['earliest_control_caps']['monotonic_deadline']-=2;f[2]['initial_watch_clock']['watcher_cutoff_lower']-=2
  namespace={};exec(m.render(m.ORIGINAL.read_text(),*f),namespace);self.assertEqual(namespace['MONO_CAP'],m.MONO-2);self.assertEqual(namespace['BOOT_CAP'],m.BCAP-2)
if __name__=='__main__':unittest.main()
