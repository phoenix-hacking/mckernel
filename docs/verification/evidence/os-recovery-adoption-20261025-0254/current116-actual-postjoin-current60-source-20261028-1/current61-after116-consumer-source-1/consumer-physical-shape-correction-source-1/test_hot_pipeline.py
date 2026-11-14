"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY retained-data effects/clock: actual entryprepare→observer→Resource2→binder.
No fixture is runtime evidence, authority, a nonce reservation or an actual child join.
"""
from pathlib import Path
import ast,contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile
D=Path(__file__).resolve().parent
E=D.parent.parent.parent
C=D/'cohort'
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

observer=load(D/'observe_current61_original227.py','real_current61_TEST_ONLY_effects')
ledger,free,ext,actors=observer.validate_current(observer.CURRENT)
capture=observer.checked(observer.PINS['capture2'])
host=capture['historical_Root59_native_and_physical']
q=json.loads((D/'ROOT61-227-INPUT.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
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
 subjects=dict(observer=ref(D/'observe_current61_original227.py'),facade=ref(C/'runtime_guard.py'),adapter=actual_adapter_ref)
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
 deps=dict(author='/root',observer=ref(D/'observe_current61_original227.py'),ledger=observer.CURRENT['ledger'],guard_adapter=actual_adapter_ref,guard_configuration=configref)
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
 # Build TEST_ONLY static data around the actual frozen227 tuple. Authority fields
 # are explicit source-only fixtures; no nonce is allocated, prepare is --check-static.
 base=E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1'
 st=json.loads((base/'actual-host-bound-source-1/STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json').read_bytes())
 fixture=write(T/'TEST_ONLY-not-authority.json',dict(TEST_ONLY=True,runtime_authority=None))
 for key in ['source_authority','case_capability','stage_map_acceptance','nonce_reservation']:st[key]=fixture
 for key in ['offline_manifest','manifest','composed_case_binding','scratch_manifest_stage']:st[key]=q[key]
 st.update(root_ledger35=q['current_ledger'],latest_serial_operation_physical_acceptance=q['latest_free'],operation_guard_adapter=actual_adapter_ref,current_observer_source=ref(D/'observe_current61_original227.py'),fixed_cutoffs=limits,nonce=None)
 st['executor_contract']=ref(base/'next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json')
 manifest=json.loads(realPath(q['offline_manifest']['path']).read_bytes())
 st['overlay']=ref(realPath(manifest['staging']['derived_initramfs']['path']));st['overlay_manifest']=ref(realPath(manifest['staging']['overlay_manifest']['path']))
 for key in ['collector','payload']:st[key]=ref(realPath(st[key]['path']))
 st['capture_helper']=ref(C/'run_native_startup_capture.py');st['capture_sources']={p.name:ref(p)for p in C.glob('*.py')}
 st['attempt_parent']=str(T/'TEST_ONLY-ATTEMPT');realPath(st['attempt_parent']).mkdir();(T/'CAPTURE').mkdir()
 write(T/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',st)
 write(T/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',st)
 prepare=load(C/'prepare_startup_bindings.py','real227_prepare_TEST_ONLY');prepare.A=T
 oldargv=sys.argv;sys.argv=['prepare_startup_bindings.py','--check-static']
 try:
  with contextlib.redirect_stdout(io.StringIO()) as stdout:prepare.main()
 finally:sys.argv=oldargv
 assert 'PASS_FULL_M15_STARTUP_MANIFEST_AND_LITERAL_OWNER_API_ONLY' in stdout.getvalue()
 checks.append('ACTUAL entryprepare --check-static executes originalfull5298validator and real227contract26producer joins; TEST_ONLY authorityrefs/no nonce')
 resource=load(C/'capture_fresh_startup_resource.py','real227_Resource2_TEST_ONLY');resource.A=T;resource.Path=EffectPath
 actual_resource_load=resource.load
 def resource_load(reference,name):
  if reference==ref(resource.GUARD):return facade
  if reference==ref(D/'observe_current61_original227.py'):return observer
  return actual_resource_load(reference,name)
 resource.load=resource_load
 output=T/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json';sys.argv=['capture_fresh_startup_resource.py','--output-path',str(output)]
 try:
  with contextlib.redirect_stdout(io.StringIO()):resource.main()
 finally:sys.argv=oldargv
 captured=json.loads(output.read_bytes());assert captured['root_ledger35']==q['current_ledger'] and captured['actual_latest_operation_postjoin_acceptance']==q['latest_free']
 checks.append('ACTUAL Resource2.main executes actual facade/configured currentobserver through exact original fields/dirs/memory/cgroup checks with retained TEST_ONLY effects')
 binder=load(C/'bind_startup_resource.py','real227_Resource2_binder_TEST_ONLY')
 pending=binder.packet_for(st,ref(T/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),captured,ref(output),fixture)
 assert pending['nonce'] is None and pending['runtime_authority'] is None and pending['root_ledger35']==q['current_ledger']
 checks.append('ACTUAL Resource2 packet_for binds actualRoot61/free and exactclockmin, no nonce/grant')
 for label,edit in [('wrong latestfree',lambda x:x.__setitem__('actual_latest_operation_postjoin_acceptance',observer.checked(observer.PINS['ledger60'])['latest_accepted_free_boundary'])),('wrong Rootledger',lambda x:x.__setitem__('root_ledger35',observer.PINS['ledger60'])),('changed occupancy',lambda x:x.__setitem__('pids_current',1)),('widened clock',lambda x:x.__setitem__('fixed_cutoffs',[1793253601,limits[1],limits[2]]))]:
  bad=copy.deepcopy(captured);edit(bad);reject(lambda:binder.packet_for(st,fixture,bad,fixture,fixture),'Resource2 rejects '+label)
result=dict(scope=__doc__.splitlines()[0],decision='PASS_TEST_ONLY_ACTUAL227_PREPARE_OBSERVER_RESOURCE2_BINDER_PIPELINE',checks=checks,count=len(checks),live_guard_calls=0,live_observer_calls=0,real_Docker_calls=0,nonce_allocations=0,runtime_authority=None)
with (D/'HOT-PIPELINE-CONTROLS.json').open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
