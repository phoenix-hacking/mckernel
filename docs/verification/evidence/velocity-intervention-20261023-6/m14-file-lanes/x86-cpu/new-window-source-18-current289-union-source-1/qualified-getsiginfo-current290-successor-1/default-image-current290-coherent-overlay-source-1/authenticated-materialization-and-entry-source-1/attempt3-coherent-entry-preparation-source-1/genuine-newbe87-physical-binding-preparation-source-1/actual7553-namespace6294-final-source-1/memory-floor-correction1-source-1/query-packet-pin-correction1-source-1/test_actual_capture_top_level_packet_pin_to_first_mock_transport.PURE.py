"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run genuine full capture top-level bytes to first mocked owned_capture call.
Only disposable copied sibling/capture files. No subprocess or actualquery occurs.
"""
from pathlib import Path
import ast,builtins,copy,hashlib,json,os,signal,subprocess,tempfile,types,unittest
from unittest.mock import patch
K=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1');READY=K/'READY-QUERY-PACKET-PIN-CORRECTION1.FINAL-STATIC.NOT-EXECUTION.json';READY_SHA='4cb46f015e254407d12dd4eb5fa539163e51e500de423675b137178908693fe9'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def auth(row):assert ref(row['path'])==row;return Path(row['path']).read_bytes()
assert ref(READY)['sha256']==READY_SHA
r=json.loads(READY.read_bytes());old=json.loads(auth(r['query_packet_pin_predecessor']));real_exec=builtins.exec;events=[]
class FirstMockQuery(BaseException):pass
class Tests(unittest.TestCase):
 def exercise(self,source_row,packet_mode='actual'):
  raw=auth(source_row);selected=auth(r['readonly_packet']);calls=[]
  with tempfile.TemporaryDirectory(prefix='disposable-capture-top-',dir=str(K)) as temp:
   d=Path(temp);script=d/Path(source_row['path']).name;script.write_bytes(raw);packet=d/Path(r['readonly_packet']['path']).name
   if packet_mode=='actual':packet.write_bytes(selected)
   elif packet_mode=='wrong':packet.write_bytes(b'{}\n')
   def transport(command,path,wall_seconds,limits,*args,**kwargs):
    calls.append(dict(argv=command['argv'],wall_seconds=wall_seconds,path=str(path)))
    raise FirstMockQuery()
   def injected_exec(code,globals=None,locals=None):
    result=real_exec(code,globals,locals)
    # Production capture has just authenticated and loaded real h990 functions.
    # Replace only command transport before its first invocation.
    if isinstance(globals,dict) and globals.get('__file__','').endswith('/run_two_commands_source_bound_corrected.py') and 'owned_capture' in globals:globals['owned_capture']=transport
    return result
   saved={sig:signal.getsignal(sig) for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGALRM]};error=None
   try:
    with patch.object(builtins,'exec',injected_exec),patch.object(os,'sched_getaffinity',return_value={7}),patch.object(subprocess,'Popen',side_effect=AssertionError('no actual process allowed')) as popen:
     try:real_exec(compile(raw,source_row['path'],'exec'),dict(__file__=str(script),__name__='actual_capture_test'))
     except BaseException as exc:error=exc
     self.assertEqual(popen.call_count,0)
   finally:
    for sig,handler in saved.items():signal.signal(sig,handler)
   descriptor=d/'actual-readonly-admission-capture-1/SOURCE-ARGV-BINDING.json';document=json.loads(descriptor.read_bytes()) if descriptor.exists() else None
   return error,calls,document
 def test_1_genuine_actual_top_level_authenticates_packet_reaches_first_mockquery(self):
  error,calls,document=self.exercise(r['readonly_capture']);self.assertIsInstance(error,FirstMockQuery);self.assertEqual(len(calls),1);packet=json.loads(auth(r['readonly_packet']));self.assertEqual(calls[0]['argv'],packet['read_only_admission_commands'][0]['argv']);self.assertEqual(document['packet_sha256'],r['readonly_packet']['sha256']);self.assertEqual(document['runner_sha256'],r['readonly_capture']['sha256']);self.assertEqual(document['helper_sha256'],'990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8');events.append(dict(actual_packet_sha256=document['packet_sha256'],actual_capture_sha256=document['runner_sha256'],first_mocked_argv=calls[0]['argv'],actual_processes=0))
 def test_2_actual_old_capture_stale_pin_refused_before_transport(self):
  error,calls,document=self.exercise(old['readonly_capture']);self.assertIsInstance(error,AssertionError);self.assertEqual(calls,[]);self.assertIsNone(document)
 def test_3_wrong_sibling_hash_refused_before_transport(self):
  error,calls,document=self.exercise(r['readonly_capture'],'wrong');self.assertIsInstance(error,AssertionError);self.assertEqual(calls,[]);self.assertIsNone(document)
 def test_4_missing_sibling_refused_before_transport(self):
  error,calls,document=self.exercise(r['readonly_capture'],'missing');self.assertIsInstance(error,FileNotFoundError);self.assertEqual(calls,[]);self.assertIsNone(document)
 def test_5_actual_observer_caller_config_top_level_dependency_prefix(self):
  raw=auth(r['census_observer']);nodes=[]
  for node in ast.parse(raw).body:
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='root' for t in node.targets):break
   nodes.append(node)
  ns=dict(__file__=r['census_observer']['path'],__name__='observer_static_dependency_prefix');real_exec(compile(ast.Module(body=nodes,type_ignores=[]),r['census_observer']['path'],'exec'),ns);self.assertEqual(ref(ns['CALLER']),r['caller']);self.assertEqual(ref(ns['m'].CONFIG),r['config']);self.assertEqual(ns['cfg']['commands']['five_observations']['source'],r['readonly_capture'])
 def test_6_both_pins_helpers_cfg_and_floor_unchanged(self):
  raw=auth(r['readonly_capture']).decode();self.assertEqual(raw.count(r['readonly_packet']['sha256']),2);self.assertNotIn(r['old_incorrect_embedded_packet_sha256'],raw);packet=json.loads(auth(r['readonly_packet']));commands=packet['read_only_admission_commands']+[packet['namespace_observation']];self.assertEqual(len(commands),5);self.assertEqual(commands[3]['argv'],['/usr/bin/sudo','-A','/usr/sbin/losetup','--list','--json','--associated','/home/holden/mckernel-work/scratch.ext4']);self.assertEqual(auth(r['readonly_packet']),auth(old['readonly_packet']))
  def funcs(row):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(auth(row)).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  for k in ['readonly_capture','fill','protocol','cleanup']:self.assertEqual(funcs(r[k]),funcs(old[k]))
  self.assertEqual(funcs(r['caller'])['immediate'],funcs(old['caller'])['immediate']);self.assertFalse(os.path.lexists(K/'actual-entry-1'));self.assertFalse(os.path.lexists(K/'actual-readonly-admission-capture-1'))
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),events=events,actual_processes_or_queries=0),sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
