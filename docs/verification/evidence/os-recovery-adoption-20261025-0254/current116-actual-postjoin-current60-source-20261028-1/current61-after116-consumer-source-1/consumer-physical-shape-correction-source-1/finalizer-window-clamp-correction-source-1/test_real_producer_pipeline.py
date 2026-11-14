"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY retained-data effects/clock: actual entryprepare→observer→Resource2→binder.
No fixture is runtime evidence, authority, a nonce reservation or an actual child join.
"""
from pathlib import Path
import ast,contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile
D=Path(__file__).resolve().parent
O=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/current61-after116-consumer-source-1/consumer-physical-shape-correction-source-1')
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
C=O/'cohort'
checks=[]
realPath=Path

def ref(p):
 p=realPath(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
def reject(call,label):
 try:call()
 except (ValueError,AssertionError,KeyError):checks.append(label)
 else:raise AssertionError('negative accepted '+label)

observer=load(O/'observe_current61_original227.py','real_current61_TEST_ONLY_effects')
ledger,free,ext,actors=observer.validate_current(observer.CURRENT)
capture=observer.checked(observer.PINS['capture2'])
host=capture['historical_Root59_native_and_physical']
q=json.loads((O/'ROOT61-227-INPUT.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
W=E/'new-window-operation-guards-source-20261028-1'
actual_adapter_ref=ref(W/'original227_guard_adapter.py')
guardian=free['actual_Root_release2'] # provenance only; actual successor fixture guardian source comes below.
actual_o2=json.loads((E/'new-window-resume-20261028-1/CURRENT116-OPERATION-2-ALL-CONTROLS/ACCOUNT-GUARD-CONFIG.json').read_bytes())
actual_successor=json.loads(realPath(actual_o2['successor']['path']).read_bytes())
clocks=capture['observed_clocks']
limits=[1793253600.0,1035705.5689454618,1051043.6959931096]
with tempfile.TemporaryDirectory(prefix='TEST_ONLY-hot-',dir=D) as temporary:
 T=realPath(temporary)
 successor=json.loads((W/'original227.SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
 subjects=dict(observer=ref(O/'observe_current61_original227.py'),facade=ref(C/'runtime_guard.py'),adapter=actual_adapter_ref)
 successor.update(operation_cutoffs=limits,subjects=subjects,source_owners=['/root','/root/ready227'],minimum_cumulative_spent=actual_successor['minimum_cumulative_spent'],guardian=actual_successor['guardian'])
 sref=write(T/'TEST_ONLY-successor.json',successor)
 review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY_fixture',operation='original227',successor=successor)
 rref=write(T/'TEST_ONLY-operation-review.json',review)
 config=dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='original227',shared_guard=ref(W/'operation_window_guard.py'),successor=sref,review=rref,subjects=subjects)
 configref=write(T/'TEST_ONLY-guard-config.json',config)
 facade=load(C/'runtime_guard.py','real_original227_facade_TEST_ONLY');facade.A=T
 binding=dict(schema='mckernel.original227.configured-guard-binding.v1',author='/root',runtime_facade=ref(C/'runtime_guard.py'),adapter=actual_adapter_ref,configuration=configref)
 fr=dict(decision='PASS_EXACT_ORIGINAL227_GUARD_CONFIGURATION_BINDING',independent=True,implementation_ownership=False,**{k:binding[k]for k in ['runtime_facade','adapter','configuration']})
 binding['independent_review']=write(T/'TEST_ONLY-facade-review.json',fr)
 write(T/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json',binding)
 actual_adapter=facade.configured() # REAL facade→adapter.configure→shared.validate_operation, no guard.
 assert actual_adapter.OPERATION=='original227' and tuple(actual_adapter.current_cutoffs())==tuple(limits)
 checks.append('actual facade→original227adapter.configure→sharedguard validates exact config and inherited clamps')
 # TEST_ONLY clock effect replaces live account/guardian calls after real configure.
 actual_adapter.guard=lambda:list(clocks)
 assert facade.guard()==clocks
 deps=dict(author='/root',observer=ref(O/'observe_current61_original227.py'),ledger=observer.CURRENT['ledger'],guard_adapter=actual_adapter_ref,guard_configuration=configref)
 dr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_ORIGINAL227_OBSERVER_DEPENDENCIES',observer=deps['observer'],guard_adapter=actual_adapter_ref,guard_configuration=configref)
 deps['independent_review']=write(T/'TEST_ONLY-observer-review.json',dr)
 write(T/'ROOT61-RUNTIME-DEPENDENCIES.json',deps)
 observer.HERE=T
 real_observer_load=observer.load
 def observer_load(reference,name):
  module=real_observer_load(reference,name)
  if reference==actual_adapter_ref:
   real_configure=module.configure
   def configure(config_ref):
    real_configure(config_ref);module.guard=lambda:list(clocks)
   module.configure=configure
  elif reference==observer.PINS['current60_source']:
   def retired_capture_effect():
    value=copy.deepcopy(capture)
    # TEST_ONLY future census removes ONLY actual capture2 PID/group after its
    # retained positive wait4/group-absent receipt. Raw capture2 is never changed.
    value['group_membership_observation']['rows']=[row for row in value['group_membership_observation']['rows'] if row['pid']!=1907223 and row['pgrp']!=1907223]
    return value
   module.observe=retired_capture_effect
  return module
 observer.load=observer_load
 class EffectPath:
  def __new__(cls,*parts):
   path=realPath(*parts)
   if str(path).startswith('/proc/') and str(path)!='/proc/meminfo':
    return type('AbsentTESTONLY',(),{'exists':lambda self:False})()
   if str(path)=='/proc/meminfo':
    raw='\n'.join(k+': '+str(v//1024)+' kB' for k,v in host['memory'].items())+'\n'
    return type('MemoryTESTONLY',(),{'read_text':lambda self:raw})()
   if str(path) in host['cgroup']:
    value=host['cgroup'][str(path)]
    return type('CgroupTESTONLY',(),{'read_text':lambda self:value})()
   if str(path)=='/sys/fs/cgroup/pids/mckernel-dev/pids.current':
    return type('PidsTESTONLY',(),{'read_text':lambda self:'0'})()
   return path
 observer.Path=EffectPath
 physical=observer.observe() # REAL current61 observer code, only leaf effects mocked.
 assert physical['Root61']==q['current_ledger'] and physical['actual_latest_operation_postjoin_acceptance']==q['latest_free']
 checks.append('actual configured current61.observe validates genuine Root61/free,61actorrows and retained current60 physical effect')
 # Reordered Mounts alone accepted by exact preserved comparator using actual old52ae record.
 compare_path=realPath(host['historical_physical_reobservation']['historical_predicate_source']['path']) if False else E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/known_cid_inspect_compare.py'
 compare=load(compare_path,'real_full_record_mount_comparator_TEST_ONLY')
 old_query=next(r for r in host['current115_exact_CID_queries'] if 'inspect' in r['argv'])
 data=json.loads(old_query['stdout']);data[0]['Mounts'].reverse()
 compare.compare(old_query,old_query['returncode'],json.dumps(data),old_query['stderr'])
 checks.append('actual old52ae fullrecord Mounts multiset accepts only Mounts order')
 bad=copy.deepcopy(data);bad[0]['State']['ExitCode']=99
 reject(lambda:compare.compare(old_query,old_query['returncode'],json.dumps(bad),old_query['stderr']),'reject altered old52ae State')
 bad=copy.deepcopy(data);bad[0]['Config']['Cmd'].reverse()
 reject(lambda:compare.compare(old_query,old_query['returncode'],json.dumps(bad),old_query['stderr']),'reject reordered nonMounts Cmd')
 # REAL finalizer --seal-source-context, all effects confined to TEST_ONLY temp.
 fixture=write(T/'TEST_ONLY-not-authority.json',dict(TEST_ONLY=True,runtime_authority=None))
 source_review=write(T/'TEST_ONLY-observer-source-review.json',dict(independent=True,implementation_ownership=False,decision='PASS_TEST_ONLY_SOURCE_SCHEMA',observer=ref(O/'observe_current61_original227.py')))
 inputs=copy.deepcopy(q)
 inputs.update(author='/root',Root_attests_exact_current_boundary=True,nonce='00000000000000000000000000000000',operation_guard_configuration=configref,current_observer_source_review=source_review,current_observer_schema_review=source_review,source_authority=fixture,case_capability=fixture,stage_map_acceptance=fixture)
 inputs['nonce_reservation']=write(T/'TEST_ONLY-not-a-real-reservation.json',dict(author='/root',nonce=inputs['nonce'],TEST_ONLY=True,runtime_authority=None))
 inputref=write(T/'TEST_ONLY-source-inputs.json',inputs)
 producer=load(D/'finalize_original227_window_bound.py','actual_window_finalizer_TEST_ONLY')
 producer.D=T;producer.F=T/'root-adopted-process227-entry-1'
 from types import SimpleNamespace
 args=SimpleNamespace(check_template=False,bind_bridge=False,bind_current_observer=False,seal_source_context=True,root_inputs=inputref['path'],root_inputs_sha256=inputref['sha256'])
 with contextlib.redirect_stdout(io.StringIO()):producer.main(args)
 C=producer.F
 produced=C/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json'
 st=json.loads(produced.read_bytes())
 assert st['fixed_cutoffs']==limits
 assert st['historical_original227_static_window']['fixed_cutoffs']==[1793165769.0,947874.5689514667,963213.6960030915]
 assert st['new_original227_sealing_window_binding']['configuration']==configref
 checks.append('ACTUAL finalizer --seal-source-context emits reviewed newclamps and preserves exact oldstatic/clamps prefix; temporary TEST_ONLY source context')
 # No manual cutoff or other static replacement. Model ONLY normal filename phase
 # promotion without invoking --nonce or claiming a real reservation/runtime seal.
 (C/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').write_bytes(produced.read_bytes())
 (C/'CAPTURE').mkdir()
 actual_attempt_parent=st['attempt_parent']
 (T/'TEST_ONLY-ATTEMPT').mkdir()
 original_EffectPath=EffectPath
 class ProducerEffectPath:
  def __new__(cls,*parts):
   path=realPath(*parts)
   if str(path)==actual_attempt_parent:return T/'TEST_ONLY-ATTEMPT'
   return original_EffectPath(*parts)
 EffectPath=ProducerEffectPath
 # Runtime facade is the REAL producer output file/configuration context.
 facade=load(C/'runtime_guard.py','real_produced_facade_TEST_ONLY')
 binding['runtime_facade']=ref(C/'runtime_guard.py')
 fr.update(runtime_facade=binding['runtime_facade'])
 binding['independent_review']=write(C/'TEST_ONLY-facade-review.json',fr)
 write(C/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json',binding)
 actual_adapter=facade.configured();actual_adapter.guard=lambda:list(clocks)
 prepare=load(C/'prepare_startup_bindings.py','real_PRODUCED227_prepare_TEST_ONLY')
 oldargv=sys.argv;sys.argv=['prepare_startup_bindings.py','--check-static']
 try:
  with contextlib.redirect_stdout(io.StringIO()) as stdout:prepare.main()
 finally:sys.argv=oldargv
 assert 'PASS_FULL_M15_STARTUP_MANIFEST_AND_LITERAL_OWNER_API_ONLY' in stdout.getvalue()
 checks.append('ACTUAL produced entryprepare --check-static consumes unmodified realfinalizer static output with originalfull5298/227/HOST26 contract')
 # Pure producer negatives authenticate real configuration modules, never guard.
 historical=json.loads(producer.HOST_STATIC.read_bytes())
 old_successor=copy.deepcopy(successor);old_successor['operation_cutoffs']=historical['fixed_cutoffs']
 old_sref=write(T/'TEST_ONLY-oldclamp-successor.json',old_successor)
 old_review=copy.deepcopy(review);old_review['successor']=old_successor
 old_rref=write(T/'TEST_ONLY-oldclamp-review.json',old_review)
 old_config=copy.deepcopy(config);old_config.update(successor=old_sref,review=old_rref)
 old_cref=write(T/'TEST_ONLY-oldclamp-config.json',old_config)
 badinputs=copy.deepcopy(inputs);badinputs['operation_guard_configuration']=old_cref
 reject(lambda:producer.seal_new_operation_window(badinputs,copy.deepcopy(historical)),'REAL finalizer rejects reviewed-but-expired oldclamps')
 badconfig=copy.deepcopy(config);badconfig['operation']='current116'
 badcref=write(T/'TEST_ONLY-wrongoperation-config.json',badconfig)
 badinputs=copy.deepcopy(inputs);badinputs['operation_guard_configuration']=badcref
 reject(lambda:producer.seal_new_operation_window(badinputs,copy.deepcopy(historical)),'REAL finalizer rejects wrong operation configuration')
 resource=load(C/'capture_fresh_startup_resource.py','real227_Resource2_TEST_ONLY');resource.A=C;resource.Path=EffectPath
 actual_resource_load=resource.load
 def resource_load(reference,name):
  if reference==ref(resource.GUARD):return facade
  if reference==ref(O/'observe_current61_original227.py'):return observer
  return actual_resource_load(reference,name)
 resource.load=resource_load
 output=C/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json';sys.argv=['capture_fresh_startup_resource.py','--output-path',str(output)]
 try:
  with contextlib.redirect_stdout(io.StringIO()):resource.main()
 finally:sys.argv=oldargv
 captured=json.loads(output.read_bytes());assert captured['root_ledger35']==q['current_ledger'] and captured['actual_latest_operation_postjoin_acceptance']==q['latest_free']
 checks.append('ACTUAL Resource2.main executes actual facade/configured currentobserver through exact original fields/dirs/memory/cgroup checks with retained TEST_ONLY effects')
 binder=load(C/'bind_startup_resource.py','real227_Resource2_binder_TEST_ONLY')
 pending=binder.packet_for(st,ref(C/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),captured,ref(output),fixture)
 assert pending['nonce']=='00000000000000000000000000000000' and pending['runtime_authority'] is None and pending['root_ledger35']==q['current_ledger']
 checks.append('ACTUAL Resource2 packet_for binds actualRoot61/free and exactclockmin, TEST_ONLY fixed placeholder only/no actual nonce/grant')
 for label,edit in [('wrong latestfree',lambda x:x.__setitem__('actual_latest_operation_postjoin_acceptance',observer.checked(observer.PINS['ledger60'])['latest_accepted_free_boundary'])),('wrong Rootledger',lambda x:x.__setitem__('root_ledger35',observer.PINS['ledger60'])),('changed occupancy',lambda x:x.__setitem__('pids_current',1)),('widened clock',lambda x:x.__setitem__('fixed_cutoffs',[1793253601,limits[1],limits[2]]))]:
  bad=copy.deepcopy(captured);edit(bad);reject(lambda:binder.packet_for(st,fixture,bad,fixture,fixture),'Resource2 rejects '+label)
result=dict(scope=__doc__.splitlines()[0],decision='PASS_TEST_ONLY_REAL_FINALIZER_NEW_WINDOW_STATIC_TO_ACTUAL227_RESOURCE2_BINDER',checks=checks,count=len(checks),live_guard_calls=0,live_observer_calls=0,real_Docker_calls=0,nonce_allocations=0,runtime_authority=None)
with (D/'REAL-PRODUCER-HOT-PIPELINE-CONTROLS.json').open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
