"""Functional OS only; no security testing. Production source/data/layout controls; no queries/runtime."""
import ast,copy,hashlib,importlib.util,json,unittest,os,runpy,sys,tempfile
from unittest import mock
from pathlib import Path
D=Path(__file__).parent
READY=json.loads((D/'READY-ATTEMPT4-FRONTEND-CLEANUP-PROTOCOL.SOURCE-ONLY.json').read_bytes())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def functions(path):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.state=json.loads((D/'PREPARED-ATTEMPT4-BASE-DATA.SOURCE-ONLY.json').read_bytes());cls.q=json.loads(Path(READY['request']['path']).read_bytes());cls.origin=load('actual_attempt4_origin',READY['origin_helper']['path']);cls.data=cls.origin.data();cls.retention=json.loads(Path(cls.data['source_retention']['path']).read_bytes());cls.mode=load('actual_attempt4_seedmode',READY['mode_adapter']['path']);cls.cleanup=load('actual_attempt4_cleanup',next(D.glob('native*cleanup*.py')));cls.protocol=cls.cleanup.current230_contract();cls.fill=load('actual_attempt4_fill',next(D.glob('fill*.py')));cls.caller=load('actual_attempt4_caller',next(D.glob('run_frozen*.py')))
 def test_actual_origin_and_original_retention(self):
  self.assertTrue(self.origin.validate_source_origin(self.q,self.retention));self.assertEqual(len(self.data['allowed_changed_request_fields']),13);self.assertEqual(self.data['added_request_fields'],['image_receipt_candidate_sha','readonly_reuse_inputs']);self.assertEqual(self.retention['source_entries'],6153);self.assertEqual(self.retention['full_owner_request'],self.data['published_origin_request']);self.assertEqual(str(self.cleanup.image_request_binding(self.q)),self.q['source_root'])
 def test_origin_rejects_changed_seed_or_role_or_source(self):
  for key in ('readonly_reuse_inputs','host_owner_path','driver_sha256','image_receipt_candidate_sha'):
   q=copy.deepcopy(self.q);q[key]='changed'
   with self.subTest(key=key),self.assertRaises(RuntimeError):self.origin.validate_source_origin(q,self.retention)
 def test_exact_origin69_real_producer(self):
  proof=json.loads(Path(self.fill.FETCHED_ORIGIN_PROOF['path']).read_bytes());self.assertEqual(len(self.fill.origin69_rows(proof)),69);bad=copy.deepcopy(proof);bad['members'][0]['sha256']='0'*64
  with self.assertRaises(RuntimeError):self.fill.origin69_rows(bad)
  # Authentic retained ATTEMPT3 phase fixture: current shared record is correctly
  # retired, so only this former-phase existence predicate is virtualized. All
  # byte reads, selectedidentity rows, source/root validation and protocol funcs
  # remain production. No future ATTEMPT4 runtime facts are invented.
  old=Path(self.state['K']);protocol=load('retained_real7b47',next(old.glob('current*protocol*.py')));obs=json.loads((old/'terminal-cleanup-preconstruction-source-1/dynamic-selected-closure-correction1-source-1/explicit-retained-raw-only-preparation-source-1/actual-retained-raw-current-metadata-observation-1/OBSERVATION.json').read_bytes());contract=protocol.contract();selected={r['path']:r for r in obs['selected_files']};receipt=json.loads(Path(contract['owner_receipt']).read_bytes());joined=json.loads(Path(contract['normal_paths']['owner.JOIN.json']).read_bytes());request=json.loads(Path(contract['static']['request']['path']).read_bytes());receiptsha=selected[contract['owner_receipt']]['sha256'];actualexists=os.path.lexists
  def normal(rows):return protocol.normal_owner_join_binding(receipt,joined,obs['target'],obs['container_inspect'],receiptsha,request,obs,rows)
  grant=json.loads(Path(contract['normal_paths']['ACTUAL-OWNER-ENTRY.json']).read_bytes())['root_execution_grant'];payload=json.loads(Path(grant['path']).read_bytes())['payload'];paths=[grant['path'],payload['path'],contract['fetched_origin_proof']['path']]
  with mock.patch.object(os.path,'lexists',side_effect=lambda path:True if str(path)==contract['shared_heavy_path'] else actualexists(path)):
   self.assertTrue(normal(selected));self.assertTrue(protocol.typed_source_binding(request,obs,selected))
   for path in paths:
    missing=copy.deepcopy(selected);missing.pop(path)
    with self.subTest(kind='missing',path=path),self.assertRaisesRegex(RuntimeError,'complete selected identity row:'):normal(missing)
    changed=copy.deepcopy(selected);changed[path]['sha256']='0'*64
    with self.subTest(kind='changed',path=path),self.assertRaisesRegex(RuntimeError,'selected bytes/full identity differ'):normal(changed)

 def test_actual_physical_and_pending_namespace_failclosed(self):
  validator=load('actual08860',self.state['physical_validator']['path']);self.assertTrue(validator.validate(READY['physical'],READY['postjoin']));cfg=json.loads(next(D.glob('FROZEN*IMAGE-ENTRY-INPUTS*.json')).read_bytes())
  with self.assertRaisesRegex(RuntimeError,'pending'):self.origin.require_new_runtime_facts(cfg)
  self.assertIsNone(cfg['namespace_initialization']);self.assertFalse(Path(self.state['base']).exists());self.assertEqual(self.caller.CONFIG_SHA,hashlib.sha256(self.caller.CONFIG.read_bytes()).hexdigest());self.assertTrue(all(v is None for v in READY['runtime_pending'].values()))
 def test_actual_layout_matches_production15fe(self):
  command,mounts=self.cleanup.image_layout(self.q);owner=self.mode.owner_module();actual=[(target,str(source),'bind',not ro) for source,target,ro in owner._reuse_mounts(self.q['readonly_reuse_inputs'])];self.assertEqual(command[-2:],['--readonly-reuse-inputs','/reuse-inputs.json']);self.assertEqual(sorted(row for row in mounts if row in actual),sorted(actual));self.assertEqual(len(actual),9);self.assertEqual([row for row in mounts if row[3]],[('/work',str(self.cleanup.OUTPUT),'bind',True)])
 def test_seed_closure_and_real_protocol_pending_guard(self):
  rows=self.protocol.required_static_references();paths={r['path'] for r in rows};fixed=json.loads(Path(self.q['readonly_reuse_inputs']).read_bytes());self.assertIn(self.q['readonly_reuse_inputs'],paths)
  for row in fixed['objects']+fixed['configuration']:self.assertIn(row['source']['path'],paths)
  for row in fixed['postimages']:self.assertIn(row['postimage']['path'],paths)
  with self.assertRaisesRegex(RuntimeError,'namespace identities pending'):self.protocol._source_identity(self.protocol.contract(),{})
  code=Path(READY['owner']['path']).read_text();tree=ast.parse(code);node=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_driver_result'][-1];text=ast.get_source_segment(code,node);self.assertIn('mandatory_fresh_compiled_object_gate',text);self.assertIn('fresh-compiled-rust-ownership-proof.json',text);self.assertIn('logger_proof',text);self.assertIn('whole_undefined_set_exact_except_removed_panics',text);self.assertIn('._validate_driver_result(e,o,result,request)',Path(READY['mode_adapter']['path']).read_text())
 def test_caller_functions_and_transaction_unchanged(self):
  old=Path(self.state['K']);oldcaller=next(old.glob('run_frozen*.py'));cb=functions(oldcaller);ca=functions(next(D.glob('run_frozen*.py')));self.assertEqual({k for k in cb if cb[k]!=ca[k]},{'execute'});before=functions(next(old.glob('native*cleanup*.py')));after=functions(next(D.glob('native*cleanup*.py')));changed={k for k in before if before[k]!=after[k]};self.assertEqual(changed,{'image_layout','configure'});self.assertEqual(before['Transaction'],after['Transaction'])
 def test_actual_capture_top_level_packet_and_binding_to_first_mockquery(self):
  runner=D/'capture_readonly_admission.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.py';packet=D/'READONLY-ADMISSION-ARGV.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.json';originaltrace=sys.gettrace()
  class FirstQuery(BaseException):pass
  for corrupt in (False,True):
   with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);local=root/runner.name;local.write_bytes(runner.read_bytes());(root/packet.name).write_bytes(packet.read_bytes()+(b' ' if corrupt else b''));calls=[]
    def first(command,path,wall,limits):calls.append(command);raise FirstQuery()
    def trace(frame,event,arg):
     if frame.f_code.co_filename==str(local) and 'ns' in frame.f_locals and 'owned_capture' in frame.f_locals['ns']:frame.f_locals['ns']['owned_capture']=first
     return trace
    try:
     with mock.patch.object(os,'sched_getaffinity',return_value={7}),mock.patch('signal.signal'):
      sys.settrace(trace)
      with self.assertRaises(AssertionError if corrupt else FirstQuery):runpy.run_path(str(local),run_name='__main__')
    finally:sys.settrace(originaltrace)
    cap=root/'actual-readonly-admission-capture-1'
    if corrupt:self.assertEqual(calls,[]);self.assertFalse(cap.exists())
    else:
     proof=json.loads((cap/'SOURCE-ARGV-BINDING.json').read_bytes());self.assertEqual(proof['packet_sha256'],hashlib.sha256(packet.read_bytes()).hexdigest());self.assertEqual(proof['runner_sha256'],hashlib.sha256(runner.read_bytes()).hexdigest());self.assertEqual(len(calls),1);self.assertEqual(calls[0],proof['commands'][0])
if __name__=='__main__':unittest.main(verbosity=2)
