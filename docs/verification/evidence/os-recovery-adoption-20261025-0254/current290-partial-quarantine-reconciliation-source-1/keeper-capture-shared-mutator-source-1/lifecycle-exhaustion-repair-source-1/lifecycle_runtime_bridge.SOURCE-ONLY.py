"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed additive source composition only. No root operations or live keeper edits.
"""
import ast,hashlib,importlib.util,json,os,time,types
from pathlib import Path
INPUTS={'prior_installer': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-proc-snapshot-lifecycle-source-1/whole-pair-enoent-correction-source-1/source-origin-correction-source-1/current-reviewer-correction-source-1/deadscan_runtime_bridge.SOURCE-ONLY.py', 'bytes': 10296, 'sha256': 'ee69ea61211f43ece62feeb15df885c2d75987effb9c03386491bc33009d8e74'}, 'patch': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-partial-quarantine-reconciliation-source-1/keeper-capture-shared-mutator-source-1/lifecycle-exhaustion-repair-source-1/dead_caller_confirmed_exited.FOCUSED-FUNCTIONS.SOURCE-ONLY.py', 'bytes': 17841, 'sha256': 'c75997323aee2032dcacb4dcb21f3bc73d08b450b8669f95f617582e2317549d'}, 'history_seed': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW18H-PARTIAL-CUSTODY-PREPARATION-1/RUNTIME/SHARED-FAILURE.DEAD-CALLER-OBSERVATIONS.json', 'bytes': 1938953, 'sha256': '32bc631dc8160f4ac4c6208c5ed41ffef709e397535c3b555324f0b68fc42ac7'}}
REPLACE=('record_dead_caller_observation','dead_caller_absent')
ADD=('dead_caller_confirm_exited','dead_caller_retained_births')
STATE_ADD=('_DEAD_CALLER_RETAINED_HISTORY_SEED',)
MANIFEST_SLOT='_CONFIRMED_EXIT_DELTA_MANIFEST'
class LifecycleBridgeRefusal(RuntimeError):pass
def need(value,message):
 if not value:raise LifecycleBridgeRefusal(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def reference(path):
 raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def authenticated(ref):
 need(isinstance(ref,dict) and set(ref)=={'path','bytes','sha256'},'exact-reference')
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact-source-or-document-reference');return raw
def prior_bridge():
 ref=INPUTS['prior_installer'];raw=authenticated(ref);m=types.ModuleType('_exact_prior_deadscan_installer');m.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),m.__dict__);return m
def expected_authorization(review):
 return dict(schema='mckernel.current290.confirmed-exited-lifecycle-delta.authorization.v1',author='/root',decision='GRANT_EXACT_CONFIRMED_EXITED_LIFECYCLE_SOURCE_DELTA',installer_sha256=reference(__file__)['sha256'],patch_sha256=INPUTS['patch']['sha256'],prior_installer=INPUTS['prior_installer'],history_seed=INPUTS['history_seed'],source_review=review)
def nodes(raw,path):return {node.name:node for node in ast.parse(raw,path).body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
def same_function(module,name,node,path):
 namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),path,'exec',dont_inherit=True,optimize=0),namespace)
 value=module.__dict__.get(name)
 need(type(value) is types.FunctionType and value.__globals__ is module.__dict__ and value.__code__.co_filename==path and value.__code__==namespace[name].__code__,'unmodified-prior-function:'+name)
def history_seed(module):
 observations=json.loads(authenticated(INPUTS['history_seed']))
 need(isinstance(observations,list),'retained-history-list')
 births={};seen=set();exited=set();gaps=[]
 def include(pid,birth):
  need(type(pid) is int and pid>0 and isinstance(birth,str) and birth.isdigit(),'retained-history-birth')
  need(pid not in births or births[pid]==birth,'retained-history-reused-pid');births[pid]=birth
 for observation in observations:
  need(isinstance(observation,dict) and type(observation.get('sequence')) is int,'retained-history-observation')
  if 'observed_births' not in observation and 'raw_full_eof_snapshots' not in observation:gaps.append(observation['sequence'])
  for pid,birth in observation.get('observed_births',{}).items():include(int(pid),birth)
  for pid in observation.get('observed_pids',[]):
   need(type(pid) is int and pid>0,'retained-history-enumerated-pid');seen.add(pid)
  for snapshot in observation.get('raw_full_eof_snapshots',[]):
   for row in snapshot:
    pid=row['pid'];need(type(pid) is int and pid>0,'retained-history-enumerated-pid');seen.add(pid)
    if row.get('stat_hex'):
     fields=module.dead_caller_stat_fields(bytes.fromhex(row['stat_hex']),pid);include(pid,fields[19].decode('ascii'))
    if row.get('current_absence',{}).get('confirmed_at_least_once') is True:exited.add(pid)
  for pid in observation.get('confirmed_exited_pids',[]):
   need(type(pid) is int and pid>0,'retained-history-exited-pid');seen.add(pid);exited.add(pid)
 return dict(source=INPUTS['history_seed'],observed_births={str(pid):birth for pid,birth in sorted(births.items())},observed_pids=sorted(seen),confirmed_exited_pids=sorted(exited),prior_compact_sequences=sorted(set(gaps)))
def install_confirmed_exit_delta(module,authorization):
 need(type(module) is types.ModuleType and MANIFEST_SLOT not in module.__dict__,'genuine-not-already-confirmed-exit-composed-module')
 need(isinstance(authorization,dict) and isinstance(authorization.get('source_review'),dict),'distinct-source-authorization-required')
 need(authorization==expected_authorization(authorization['source_review']),'exact-root-source-composition-authorization')
 review=json.loads(authenticated(authorization['source_review']))
 need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY' and review.get('reviewer') not in (None,'','/root') and review.get('installer_sha256')==authorization['installer_sha256'] and review.get('patch_sha256')==INPUTS['patch']['sha256'],'independent-exact-current-source-review')
 prior=prior_bridge();oldraw=authenticated(prior.FROZEN_INPUTS['patch']);newraw=authenticated(INPUTS['patch'])
 originalraw=authenticated(prior.FROZEN_INPUTS['baseline']);censusraw=authenticated(prior.FROZEN_INPUTS['census_corrected'])
 old=nodes(oldraw,prior.FROZEN_INPUTS['patch']['path']);new=nodes(newraw,INPUTS['patch']['path']);original=nodes(originalraw,prior.FROZEN_INPUTS['baseline']['path']);censusnodes=nodes(censusraw,prior.FROZEN_INPUTS['census_corrected']['path'])
 need(set(new)==set(old)|set(ADD),'closed-patch-node-set')
 need(all(ast.dump(new[name],include_attributes=False)==ast.dump(old[name],include_attributes=False) for name in set(old)-set(REPLACE)),'unchanged-existing-helpers')
 need(module.__file__==prior.FROZEN_INPUTS['baseline']['path'],'original-engine-file-identity')
 need(hashlib.sha256(canonical(module.RELEASE)).hexdigest()==prior.OLD_RELEASE_CANONICAL_SHA,'original-release-preserved')
 assignments={target.id:node.value for node in ast.parse(originalraw).body if isinstance(node,ast.Assign) for target in node.targets if isinstance(target,ast.Name)}
 need(module.PUBLISHED_SCRIPT==ast.literal_eval(assignments['PUBLISHED_SCRIPT']),'original-published-script')
 need(module.BOOT_ID==module.RELEASE['observation']['boot_id'] and module.OWNER_PID==module.RELEASE['observation']['target']['owner_pid'] and tuple(module.WAITER_PIDS)==tuple(row['pid'] for row in module.RELEASE['observation']['client_ledger']),'original-owner-boot-waiters')
 for name,expected in [('os',os),('time',time),('json',json),('Path',Path)]:need(module.__dict__.get(name) is expected,'baseline-dependency:'+name)
 need(isinstance(module.Refusal,type) and module.Refusal.__name__=='Refusal' and module.Refusal.__bases__==(ValueError,),'original-refusal-class')
 deadscan=module.__dict__.get('_DEADSCAN_DELTA_MANIFEST');census=module.__dict__.get('_PROCESS_CENSUS_DELTA_MANIFEST')
 need(isinstance(deadscan,dict) and deadscan.get('installer')==INPUTS['prior_installer'] and deadscan.get('patch_source')==prior.FROZEN_INPUTS['patch'] and deadscan.get('baseline_source')==prior.FROZEN_INPUTS['baseline'] and deadscan.get('old_release_canonical_sha256')==prior.OLD_RELEASE_CANONICAL_SHA and deadscan.get('old_plan_sha256')==prior.OLD_PLAN_SHA,'exact-prior-deadscan-composition-required')
 need(isinstance(census,dict) and census.get('corrected_source')==prior.FROZEN_INPUTS['census_corrected'] and census.get('changed_slots')==['PROC_CODE','root_command','validate_process_report'] and hashlib.sha256(module.PROC_CODE.encode()).hexdigest()==census['proc_code_sha256'] and hashlib.sha256(canonical(census)).hexdigest()==deadscan.get('prior_census_manifest_sha256'),'prior-census-three-slots-and-manifest')
 for name in ('root_command','validate_process_report'):same_function(module,name,censusnodes[name],prior.FROZEN_INPUTS['census_corrected']['path'])
 for name in ('record_dead_caller_observation','dead_caller_absent','dead_caller_publisher','dead_caller_forbidden_rows','dead_caller_stat_fields'):same_function(module,name,old[name],prior.FROZEN_INPUTS['patch']['path'])
 for name in set(prior.BASELINE_FUNCTIONS)-set(REPLACE):same_function(module,name,original[name],prior.FROZEN_INPUTS['baseline']['path'])
 need(isinstance(module.DeadCallerIncompleteSnapshot,type) and module.DeadCallerIncompleteSnapshot.__name__=='DeadCallerIncompleteSnapshot' and module.DeadCallerIncompleteSnapshot.__bases__==(Exception,) and set(module.DeadCallerIncompleteSnapshot.__dict__) <= {'__module__','__doc__','__dict__','__weakref__'},'unchanged-incomplete-exception-type')
 need(all(name not in module.__dict__ for name in ADD+STATE_ADD),'new-helper-slot-collision')
 selected=[new[name] for name in REPLACE+ADD]
 need(all(isinstance(node,ast.FunctionDef) and not node.decorator_list for node in selected),'closed-function-nodes')
 compiled=compile(ast.Module(body=selected,type_ignores=[]),INPUTS['patch']['path'],'exec',dont_inherit=True,optimize=0)
 need(set(compiled.co_names)==set(REPLACE+ADD),'closed-top-level-function-names')
 seed=history_seed(module)
 before=dict(module.__dict__)
 try:
  exec(compiled,module.__dict__)
  module.__dict__[STATE_ADD[0]]=seed
  need({name for name,value in before.items() if module.__dict__.get(name) is not value}==set(REPLACE) and set(module.__dict__)-set(before)==set(ADD+STATE_ADD) and set(before)-set(module.__dict__)==set(),'only-exact-confirmed-exit-slots-change')
  for name,value in before.items():
   if name not in REPLACE:need(module.__dict__[name] is value,'unapproved-existing-global-mutation:'+name)
  manifest=dict(schema='mckernel.current290.confirmed-exited-lifecycle-delta.composition.v1',installer=reference(__file__),patch_source=INPUTS['patch'],changed_slots=list(REPLACE),added_slots=list(ADD+STATE_ADD),history_seed=INPUTS['history_seed'],history_seed_inventory_sha256=hashlib.sha256(canonical(seed)).hexdigest(),prior_compact_sequences=seed['prior_compact_sequences'],manifest_slot=MANIFEST_SLOT,independent_source_review=authorization['source_review'],authorization_sha256=hashlib.sha256(canonical(authorization)).hexdigest(),prior_deadscan_manifest_sha256=hashlib.sha256(canonical(deadscan)).hexdigest(),prior_census_manifest_sha256=hashlib.sha256(canonical(census)).hexdigest(),old_release_canonical_sha256=prior.OLD_RELEASE_CANONICAL_SHA,old_plan_sha256=prior.OLD_PLAN_SHA,all_other_existing_globals_identity_preserved=True,unknown_history_never_claimed_full_eof=True,retry_budget_unchanged=3)
  module.__dict__[MANIFEST_SLOT]=manifest
  return manifest
 except BaseException:
  for name in REPLACE:module.__dict__[name]=before[name]
  for name in ADD+STATE_ADD:module.__dict__.pop(name,None)
  module.__dict__.pop(MANIFEST_SLOT,None)
  raise
