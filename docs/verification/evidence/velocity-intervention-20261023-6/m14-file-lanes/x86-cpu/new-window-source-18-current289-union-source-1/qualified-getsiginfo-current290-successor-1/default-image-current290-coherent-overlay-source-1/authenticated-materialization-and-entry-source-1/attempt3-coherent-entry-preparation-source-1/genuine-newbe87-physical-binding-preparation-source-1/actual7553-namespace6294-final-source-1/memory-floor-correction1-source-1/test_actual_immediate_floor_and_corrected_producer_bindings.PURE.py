"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual immediate comparison AST boundaries and changed hash/import producer joins.
No immediate() runtime probes, livequery, holder/clock, namespace/owner/cleanup.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,unittest
Y=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1');READY=Y/'READY-ATTEMPT3-EXACT-MEMORY-FLOOR-CORRECTION1.FINAL-STATIC.NOT-EXECUTION.json';READY_SHA='8fab7e98002c1da15054003dad885e1bd2b585512511063c5ba1b21eb69e3ced'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def module(row,name):
 assert ref(row['path'])==row;s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
assert ref(READY)['sha256']==READY_SHA
r=json.loads(READY.read_bytes());old=json.loads(Path(r['floor_correction_predecessor']['path']).read_bytes());caller=module(r['caller'],'floor_corrected_caller');fill=module(r['fill'],'floor_corrected_fill');cleanup=module(r['cleanup'],'floor_corrected_cleanup');protocol=cleanup.current230_contract();contract=protocol.contract();cfg=json.loads(Path(r['config']['path']).read_bytes());proof=json.loads((Y/'EXACT-IMMEDIATE-FLOOR-AST-AND-DEPENDENT-DATA-CORRECTION.PROOF.json').read_bytes())
def functions(row):return {n.name:n for n in ast.parse(Path(row['path']).read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
oldfs=functions(old['caller']);newfs=functions(r['caller']);immediate=newfs['immediate'];guard=next(n for n in ast.walk(immediate) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='fresh complete entry floors');predicate=compile(ast.Expression(body=copy.deepcopy(guard.args[0])),'actual_immediate_floor_predicate','eval')
def decision(mem):return eval(predicate,{},dict(mem=mem,values={'HOST_available':1<<60,'scratch_available':1<<60},required=1<<30))
class FloorCorrection(unittest.TestCase):
 def test_1_actual_predicate_floor_minus_one_and_floor(self):
  self.assertFalse(decision(25501368319));self.assertTrue(decision(25501368320));self.assertTrue(decision(25501368321))
 def test_2_old_lower_range_is_refused(self):
  for value in [25489368319,25489368320,25489368321,25501368319]:self.assertFalse(decision(value))
 def test_3_only_immediate_constant_change_exact_accepted_c5(self):
  expected=copy.deepcopy(oldfs['immediate']);hits=[]
  for n in ast.walk(expected):
   if isinstance(n,ast.Constant) and n.value==25489368320:n.value=25501368320;hits.append(n)
  self.assertEqual(len(hits),1);self.assertEqual(ast.dump(expected,include_attributes=False),ast.dump(immediate,include_attributes=False));self.assertEqual(ast.dump(functions(proof['accepted_c5_caller'])['immediate'],include_attributes=False),ast.dump(immediate,include_attributes=False))
  self.assertEqual(json.loads(Path(r['context_template']['path']).read_bytes())['aggregate']['minimum'],25501368320)
 def test_4_other_caller_functions_and_execute_data_only(self):
  for key in oldfs:
   if key not in ['immediate','execute']:self.assertEqual(ast.dump(oldfs[key],include_attributes=False),ast.dump(newfs[key],include_attributes=False))
  n=copy.deepcopy(newfs['execute']);mapping={r['binding_helper']['path']:old['binding_helper']['path'],r['binding_helper']['sha256']:old['binding_helper']['sha256']}
  for x in ast.walk(n):
   if isinstance(x,ast.Constant) and isinstance(x.value,str) and x.value in mapping:x.value=mapping[x.value]
  self.assertEqual(ast.dump(n,include_attributes=False),ast.dump(oldfs['execute'],include_attributes=False))
 def test_5_actual_corrected_import_config_protocol_hashes(self):
  self.assertEqual(caller.actual_config(Path(r['config']['path']),r['config']['sha256']),cfg)
  for k,field in [('caller','caller'),('config','caller_base_config'),('fill','metadata_fill'),('census_observer','observer')]:self.assertEqual(contract['static'][field],r[k])
  self.assertEqual(cleanup.PUBLISHED_SCRIPT,str(Path(r['cleanup']['path']).relative_to('/home/holden/mckernel')))
 def test_6_actual_changed_fill_producer_data_origin_join(self):
  p=fill.load(fill.D/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json');self.assertEqual(p['source_origin_binding'],r['source_origin_binding']);self.assertEqual(p['argv'],cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(p['argv'],cleanup.CURRENT230_OWNER_ARGV);self.assertTrue(all((fill.D/name).is_file() for name in fill.SOURCES));q=json.loads(Path(r['request']['path']).read_bytes());ret=json.loads(Path(r['source_retention']['path']).read_bytes());self.assertTrue(fill.attempt2_binding().validate_source_origin(q,ret));self.assertTrue(fill.attempt2_binding().require_new_runtime_facts(cfg))
 def test_7_unchanged_facts_no_live_capture_clock_namespace_action(self):
  for k in ['request','image_entry_owner','host_control_owner','current_physical','postreturn','namespace_initialization','origin69','source_retention']:self.assertEqual(r[k],old[k])
  self.assertFalse(os.path.lexists(cfg['capture_root']));self.assertFalse(os.path.lexists(Y/'actual-readonly-admission-capture-1'))
  for k in ['actual_holder','actual_live_clock','actual_admission_grants']:self.assertIsNone(r[k])
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FloorCorrection));print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),exact_floor=25501368320,no_native_runtime_calls=True),sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
