"""Functional OS only; no security testing. Production source/data/layout controls; no queries/runtime."""
import ast,copy,hashlib,importlib.util,json,unittest,os,runpy,sys,tempfile,shutil
from unittest import mock
from pathlib import Path
D=Path(__file__).parent
READY=json.loads((D/'READY-ATTEMPT4-FRONTEND-CLEANUP-PROTOCOL.EXPERT-NAMESPACE-CORRECTION1.SOURCE-ONLY.json').read_bytes())
PACKAGE=D
D=Path(READY['caller']['path']).parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def functions(path):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  b=load('actual_complete_bootstrap',PACKAGE/'bootstrap_actual_attempt4_frontend_dependencies.PURE.py').bootstrap();cls.state=json.loads((Path(b['state']['original_frontend'])/'PREPARED-ATTEMPT4-BASE-DATA.SOURCE-ONLY.json').read_bytes());cls.q=json.loads(Path(READY['request']['path']).read_bytes());cls.origin=b['origin'];cls.data=b['data'];cls.retention=json.loads(Path(cls.data['source_retention']['path']).read_bytes());cls.mode=b['mode'];cls.cleanup=b['cleanup'];cls.protocol=b['protocol'];cls.fill=b['fill'];cls.caller=b['caller'];cls.pure=b['pure'];cls.selected=b['selected'];cls.typed_source_observation=b['typed_source_observation'];print('ACTUAL_FRONTEND_DEPENDENCY_BOOTSTRAP_PASS refs='+str(b['authenticated_reference_count']))
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
  validator=load('actual08860',self.state['physical_validator']['path']);self.assertTrue(validator.validate(READY['physical'],READY['postjoin']));cfg=json.loads(Path(READY['config']['path']).read_bytes());self.assertTrue(self.origin.require_new_runtime_facts(cfg));oldcfg=json.loads((Path(self.state['F'])/Path(READY['config']['path']).name).read_bytes())
  with self.assertRaisesRegex(RuntimeError,'namespace3 receipt'):self.origin.require_new_runtime_facts(oldcfg)
  self.assertIsNone(oldcfg['namespace_initialization']);self.assertTrue(Path(self.state['base']).is_dir());self.assertEqual(self.caller.CONFIG_SHA,hashlib.sha256(self.caller.CONFIG.read_bytes()).hexdigest());self.assertTrue(all(v is None for v in READY['runtime_pending'].values()))
 def test_actual_layout_matches_production15fe(self):
  command,mounts=self.cleanup.image_layout(self.q);owner=self.mode.owner_module();actual=[(target,str(source),'bind',not ro) for source,target,ro in owner._reuse_mounts(self.q['readonly_reuse_inputs'])];self.assertEqual(command[-2:],['--readonly-reuse-inputs','/reuse-inputs.json']);self.assertEqual(sorted(row for row in mounts if row in actual),sorted(actual));self.assertEqual(len(actual),9);self.assertEqual([row for row in mounts if row[3]],[('/work',str(self.cleanup.OUTPUT),'bind',True)])
  self.assertFalse(hasattr(self.pure,'ImageOwner'));self.assertFalse(hasattr(self.pure,'_validate_request'));self.assertTrue(self.pure.PURE_VALIDATOR_GLOBAL_DEPENDENCIES)
  # Synthetic disposable typed-data fixture only: never native/compiled acceptance.
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);output=root/'output';evidence=root/'evidence';output.mkdir();evidence.mkdir();fixed=self.pure._REUSE_FIXED
   def file(path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
   def metadata(path,canonical):return dict(path=canonical,size=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
   for row in fixed['objects']:
    path=output/'build'/row['build_relative'];path.parent.mkdir(parents=True,exist_ok=True)
    if row['replace']:path.write_bytes(('DISPOSABLE-FUNCTIONAL-FIXTURE-'+row['build_relative']).encode())
    else:shutil.copyfile(row['source']['path'],path)
   outpaths={'mckernel.img':'build/kernel/mckernel.img','mckernel.img.map':'build/kernel/mckernel.img.map','CMakeCache.txt':'build/CMakeCache.txt','compile_commands.json':'build/compile_commands.json','mckernel_rust.o':'build/kernel/rust/mckernel_rust.o','build.make':'build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make'};artifacts={};copied={}
   for name,relative in outpaths.items():
    path=output/relative
    if not path.exists():file(path,('DISPOSABLE-FUNCTIONAL-FIXTURE-'+name).encode())
    artifacts[name]=metadata(path,'/work/output/'+relative);dest=evidence/'artifacts'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);copied[name]=metadata(dest,'/work/evidence/artifacts/'+name)
   markers=['F06_PROCESS_VM_IOV_LOCAL_DEBUG','F06_PROCESS_VM_IOV_REMOTE_DEBUG','F06_PROCESS_VM_FOUND_DEBUG','F06_PROCESS_VM_COPY_DEBUG'];ownership=dict(status='PASS_ACTUAL_DEFAULT_WHOLE_RUST_HANDLER_NO_PANIC_AND_FOUR_LOCAL_LOGGERS',mandatory_fresh_compiled_object_gate=True,new_Rust_object=artifacts['mckernel_rust.o'],whole_undefined_set_exact_except_removed_panics=True,removed_original_panic_imports=['fixture-panic1','fixture-panic2'],logger_proof={marker:dict(record=dict(symbol=dict(bind=0,size=32),filename='/src/kernel/rust/syscall_policy.rs',function='arch_process_vm_rw_log_bridge',relocations=[1,2]),callback_consumer_relocations=[1]) for marker in markers})
   file(evidence/'fresh-compiled-rust-ownership-proof.json',json.dumps(ownership,sort_keys=True).encode());objects=[]
   for row in fixed['objects']:objects.append(dict(build_relative=row['build_relative'],reused=not row['replace'],artifact=metadata(output/'build'/row['build_relative'],'/work/output/build/'+row['build_relative'])))
   result=dict(status='PASS',native_fork_owned_transaction=False,candidate_sha=self.q['candidate_sha'],ihk_sha=self.q['ihk_sha'],source_manifest_sha256=self.q['source_manifest_sha256'],toolchain_manifest_sha256=self.q['toolchain_manifest_sha256'],gitlink_manifest_sha256=self.q['gitlink_manifest_sha256'],source_derivative_sha256=self.q['source_derivative_sha256'],materialization_sha256=self.q['materialization_sha256'],candidate_identity_scope='base_git_commit_only',production_rust_core_panic_reference_proof=dict(status='PASS_PRODUCTION_RUST_NO_TARGETED_CORE_PANIC_REFS',forbidden=[],clone_thread_undefined=1,object=artifacts['mckernel_rust.o']),artifacts=artifacts,evidence_artifacts=copied,commands=[dict(phase=phase) for phase in ['recompile-full-Rust','recompile-process','raw-ld-11-inputs']],readonly_reuse=dict(schema=fixed['schema'],inputs_sha256=self.pure._REUSE_INPUT_SHA256,configuration_mode=fixed['configuration_mode'],fresh_full_configure=False,reused_object_count=9,replaced_object_count=2,link_input_count=11,postimages=fixed['postimages'],fresh_object_ownership=ownership,objects=objects))
   result['inventory']={str(path.relative_to(evidence)):dict(size=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in evidence.rglob('*') if path.is_file()};file(evidence/'receipt.json',json.dumps(result,sort_keys=True).encode());self.assertIsNone(self.pure._validate_driver_result(evidence,output,result,self.q))
   bad=copy.deepcopy(result);bad['readonly_reuse']['fresh_object_ownership']['mandatory_fresh_compiled_object_gate']=False
   with self.assertRaisesRegex(RuntimeError,'mandatory fresh compiled Rust ownership proof missing'):self.pure._validate_driver_result(evidence,output,bad,self.q)
   bad=copy.deepcopy(result);bad['readonly_reuse']['fresh_object_ownership']['logger_proof'].pop(markers[0])
   with self.assertRaisesRegex(RuntimeError,'four strict logger proofs missing'):self.pure._validate_driver_result(evidence,output,bad,self.q)

 def test_seed_closure_and_real_protocol_pending_guard(self):
  rows=self.protocol.required_static_references();paths={r['path'] for r in rows};fixed=json.loads(Path(self.q['readonly_reuse_inputs']).read_bytes());self.assertIn(self.q['readonly_reuse_inputs'],paths)
  for row in fixed['objects']+fixed['configuration']:self.assertIn(row['source']['path'],paths)
  for row in fixed['postimages']:self.assertIn(row['postimage']['path'],paths)
  self.assertTrue(self.protocol.typed_source_binding(self.q,self.typed_source_observation,self.selected));bad=copy.deepcopy(self.typed_source_observation);bad['namespace_binding']['inode']+=1
  with self.assertRaises(RuntimeError):self.protocol._source_identity(self.protocol.contract(),bad)
  code=Path(READY['owner']['path']).read_text();tree=ast.parse(code);node=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_driver_result'][-1];text=ast.get_source_segment(code,node);self.assertIn('mandatory_fresh_compiled_object_gate',text);self.assertIn('fresh-compiled-rust-ownership-proof.json',text);self.assertIn('logger_proof',text);self.assertIn('whole_undefined_set_exact_except_removed_panics',text);self.assertIn('._validate_driver_result(e,o,result,request)',Path(READY['mode_adapter']['path']).read_text());self.assertNotIn('spec.loader.exec_module',Path(READY['mode_adapter']['path']).read_text())
 def test_caller_functions_and_transaction_unchanged(self):
  old=Path(self.state['K']);oldcaller=next(old.glob('run_frozen*.py'));cb=functions(oldcaller);ca=functions(next(D.glob('run_frozen*.py')));self.assertEqual({k for k in cb if cb[k]!=ca[k]},{'execute'});before=functions(next(old.glob('native*cleanup*.py')));after=functions(READY['cleanup']['path']);changed={k for k in before if before[k]!=after[k]};self.assertEqual(changed,{'image_layout','configure'});self.assertEqual(before['Transaction'],after['Transaction']);self.assertEqual(Path('/home/holden/mckernel')/self.cleanup.PUBLISHED_SCRIPT,Path(READY['cleanup']['path']));self.assertEqual(self.cleanup.CURRENT230_TYPED_PROTOCOL,READY['protocol']);self.assertTrue(self.protocol.CONTRACT.is_file());self.assertEqual(hashlib.sha256(self.protocol.CONTRACT.read_bytes()).hexdigest(),self.protocol.CONTRACT_SHA);self.assertTrue(self.origin.DATA_BINDING.is_file());self.assertTrue(all((D/name).is_file() for name in self.fill.SOURCES))
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

  observer=Path(READY['corrected_census_observer']['path']);observertext=observer.read_text()
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);compact=root/'fixture-compact.json';compact.write_text('{}');compactref=dict(path=str(compact),sha256=hashlib.sha256(compact.read_bytes()).hexdigest(),bytes=compact.stat().st_size);cfg=json.loads(self.caller.CONFIG.read_bytes());cfg['capture_root']=str(root);command=list(cfg['commands']['compact_census']['argv']);command[-1]=compactref['sha256'];fake_ready=dict(deadline_epoch=9999999999,five_end_epoch=__import__('time').time(),argv=command,compact_request=compactref);calls=[]
   def first(command,path,wall,limits):calls.append(command);raise FirstQuery()
   def trace(frame,event,arg):
    if frame.f_code.co_filename==str(observer):
     m=frame.f_locals.get('m')
     if m is not None and hasattr(m,'strict') and not getattr(m,'_prefix_test_strict',False):
      original=m.strict
      def strict(path):
       if str(path)==str(m.CONFIG):return cfg
       if Path(path).name=='CENSUS-READY.json':return fake_ready
       return original(path)
      m.strict=strict;m._prefix_test_strict=True
     ns=frame.f_locals.get('ns')
     if isinstance(ns,dict) and 'owned_capture' in ns:ns['owned_capture']=first
    return trace
   try:
    with mock.patch.object(os,'sched_getaffinity',return_value={2,3,4,5}),mock.patch('signal.signal'):
     sys.settrace(trace)
     with self.assertRaises(FirstQuery):runpy.run_path(str(observer),run_name='__main__')
   finally:sys.settrace(originaltrace)
   self.assertEqual(len(calls),1);self.assertEqual(calls[0]['argv'],command)
if __name__=='__main__':unittest.main(verbosity=2)
