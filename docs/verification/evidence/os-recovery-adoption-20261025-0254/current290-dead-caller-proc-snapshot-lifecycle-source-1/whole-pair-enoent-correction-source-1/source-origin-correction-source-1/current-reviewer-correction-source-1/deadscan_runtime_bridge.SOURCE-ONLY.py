"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed-node source composition after authorized c9af census; no configure/run/root/FD actions.
"""
import ast,hashlib,json,marshal,os,time,types
from pathlib import Path
FROZEN_INPUTS=json.loads('{"baseline": {"bytes": 128910, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py", "sha256": "e49eaf2a7bacc6a64523f9f6c91516b9a3abefc875cdc1d8941c4e6b55473de3"}, "census_bridge": {"bytes": 8758, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-correction-source-1/census-runtime-bridge-source-1/census_runtime_bridge.py", "sha256": "c9af3506af824af58c599a2aa8d7a1aae30b680a25c4bcc5ca87b8bcd1d20a2a"}, "census_corrected": {"bytes": 133996, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-correction-source-1/native_rust_cutover_image_terminal_cleanup.PROCESS-LIFECYCLE.v2.SOURCE-ONLY.py", "sha256": "1eb0a669f5d3c248afa1b14130421a1582f1410847be95494ec107a322f6ad9a"}, "patch": {"bytes": 10186, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-proc-snapshot-lifecycle-source-1/whole-pair-enoent-correction-source-1/dead_caller_whole_pair_enoent.FOCUSED-FUNCTIONS.SOURCE-ONLY.py", "sha256": "2cd8400c362f4fc5252873bb05ded9233dde45c53c030064b45942d5dfbb18e2"}}')
REPLACE=('record_dead_caller_observation','dead_caller_absent')
ADD=('DeadCallerIncompleteSnapshot','dead_caller_publisher','dead_caller_forbidden_rows','dead_caller_stat_fields')
SLOTS=REPLACE+ADD
MANIFEST_SLOT='_DEADSCAN_DELTA_MANIFEST'
BASELINE_FUNCTIONS=REPLACE+('validate_dead_caller_snapshots','validate_dead_operation_argv','same_ofd_process','same_ofd_read','canonical')
OLD_RELEASE_CANONICAL_SHA='57c62c0c739438ca4a68c2ec167dc953f7274b4968e7c4e6dba74272acc32f70'
OLD_PLAN_SHA='279b40f40ae69255914c064e92486fdfbb65ad798077206dc9c598d185e277f8'
class DeadscanBridgeRefusal(RuntimeError):pass
def need(value,message):
 if not value:raise DeadscanBridgeRefusal(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def reference(path):
 raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def authenticated(row):
 raw=Path(row['path']).read_bytes();need(set(row)=={'path','sha256','bytes'} and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'exact-source-reference');return raw
def fingerprint(function):return hashlib.sha256(marshal.dumps(function.__code__)).hexdigest()
def expected_authorization(source_review):
 return dict(schema='mckernel.current290.dead-caller-lifecycle-delta.authorization.v1',author='/root',decision='GRANT_EXACT_DEAD_CALLER_LIFECYCLE_DELTA',installer_sha256=reference(__file__)['sha256'],source_review=source_review,baseline_source_sha256=FROZEN_INPUTS['baseline']['sha256'],patch_sha256=FROZEN_INPUTS['patch']['sha256'],census_bridge_sha256=FROZEN_INPUTS['census_bridge']['sha256'],old_release_canonical_sha256=OLD_RELEASE_CANONICAL_SHA,old_plan_sha256=OLD_PLAN_SHA)
def function_nodes(raw,path):return {node.name:node for node in ast.parse(raw,path).body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
def install_deadscan_delta(module,authorization):
 need(type(module) is types.ModuleType and MANIFEST_SLOT not in module.__dict__,'genuine-not-already-composed-module')
 need(isinstance(authorization,dict) and isinstance(authorization.get('source_review'),dict),'distinct-root-authorization-required')
 need(authorization==expected_authorization(authorization['source_review']),'distinct-exact-root-authorization-required')
 review=json.loads(authenticated(authorization['source_review']))
 need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY' and review.get('reviewer')=='/root/deadscan_review' and review.get('installer_sha256')==authorization['installer_sha256'] and review.get('patch_sha256')==FROZEN_INPUTS['patch']['sha256'],'independent-exact-source-review')
 raw=authenticated(FROZEN_INPUTS['baseline']);patch=authenticated(FROZEN_INPUTS['patch']);authenticated(FROZEN_INPUTS['census_bridge'])
 old=function_nodes(raw,FROZEN_INPUTS['baseline']['path']);new=function_nodes(patch,FROZEN_INPUTS['patch']['path'])
 need(set(new)==set(SLOTS),'closed-patch-node-set')
 need(module.__file__==FROZEN_INPUTS['baseline']['path'],'original-file-identity')
 assignments={target.id:node.value for node in ast.parse(raw).body if isinstance(node,ast.Assign) for target in node.targets if isinstance(target,ast.Name)}
 need(module.PUBLISHED_SCRIPT==ast.literal_eval(assignments['PUBLISHED_SCRIPT']),'original-published-script')
 need(hashlib.sha256(canonical(module.RELEASE)).hexdigest()==OLD_RELEASE_CANONICAL_SHA,'unchanged-original-release')
 need(module.BOOT_ID==module.RELEASE['observation']['boot_id'] and module.OWNER_PID==module.RELEASE['observation']['target']['owner_pid'] and tuple(module.WAITER_PIDS)==tuple(row['pid'] for row in module.RELEASE['observation']['client_ledger']),'unchanged-original-owner-boot-waiters')
 census=module.__dict__.get('_PROCESS_CENSUS_DELTA_MANIFEST')
 need(isinstance(census,dict) and census.get('schema')=='mckernel.current290.process-census-delta.composition.v1' and census.get('baseline_source')==FROZEN_INPUTS['baseline'] and census.get('changed_slots')==['PROC_CODE','root_command','validate_process_report'] and census.get('old_release_canonical_sha256')==OLD_RELEASE_CANONICAL_SHA and census.get('old_plan_sha256')==OLD_PLAN_SHA,'authorized-c9af-census-composition-required-first')
 need(census.get('corrected_source')==FROZEN_INPUTS['census_corrected'] and hashlib.sha256(module.PROC_CODE.encode()).hexdigest()==census['proc_code_sha256'],'census-three-slots-unchanged')
 # marshal byte strings can encode transient object reference flags differently.
 # Authenticate actual1eb bytes and compare compiled code objects directly.
 census_raw=authenticated(FROZEN_INPUTS['census_corrected']);census_nodes=function_nodes(census_raw,FROZEN_INPUTS['census_corrected']['path'])
 for name in ['root_command','validate_process_report']:
  namespace={};exec(compile(ast.Module(body=[census_nodes[name]],type_ignores=[]),FROZEN_INPUTS['census_corrected']['path'],'exec',dont_inherit=True,optimize=0),namespace)
  value=module.__dict__[name]
  need(type(value) is types.FunctionType and value.__globals__ is module.__dict__ and value.__code__.co_filename==FROZEN_INPUTS['census_corrected']['path'] and value.__code__==namespace[name].__code__,'census-three-slots-unchanged')
 for name,expected in [('os',os),('time',time),('json',json),('Path',Path)]:need(module.__dict__.get(name) is expected,'baseline-dependency:'+name)
 need(isinstance(module.Refusal,type) and module.Refusal.__name__=='Refusal' and module.Refusal.__bases__==(ValueError,),'original-refusal-class')
 for name in BASELINE_FUNCTIONS:
  namespace={};exec(compile(ast.Module(body=[old[name]],type_ignores=[]),FROZEN_INPUTS['baseline']['path'],'exec',dont_inherit=True,optimize=0),namespace)
  value=module.__dict__.get(name)
  need(type(value) is types.FunctionType and value.__globals__ is module.__dict__ and value.__code__.co_filename==FROZEN_INPUTS['baseline']['path'] and value.__code__==namespace[name].__code__,'unmodified-baseline-function:'+name)
 need(all(name not in module.__dict__ for name in ADD),'new-helper-slot-collision')
 nodes=[]
 for name in SLOTS:
  node=new[name]
  if isinstance(node,ast.ClassDef):need(name=='DeadCallerIncompleteSnapshot' and not node.decorator_list and len(node.bases)==1 and isinstance(node.bases[0],ast.Name) and node.bases[0].id=='Exception' and not node.keywords and len(node.body)==1 and isinstance(node.body[0],ast.Pass),'closed-exception-class')
  else:need(isinstance(node,ast.FunctionDef) and not node.decorator_list and all(isinstance(value,ast.Constant) and value.value is None for value in node.args.defaults) and not node.args.kw_defaults,'closed-function-node')
  nodes.append(node)
 compiled=compile(ast.Module(body=nodes,type_ignores=[]),FROZEN_INPUTS['patch']['path'],'exec',dont_inherit=True,optimize=0)
 need(set(compiled.co_names)==set(SLOTS)|{'Exception'},'closed-top-level-names')
 before=dict(module.__dict__)
 try:
  exec(compiled,module.__dict__)
  changed={name for name,value in before.items() if module.__dict__.get(name) is not value}
  need(changed==set(REPLACE) and set(module.__dict__)-set(before)==set(ADD) and set(before)-set(module.__dict__)==set(),'only-exact-deadscan-slots-change')
  for name,value in before.items():
   if name not in REPLACE:need(module.__dict__[name] is value,'unapproved-existing-global-mutation:'+name)
  need(all(module.__dict__[name].__globals__ is module.__dict__ and module.__dict__[name].__code__.co_filename==FROZEN_INPUTS['patch']['path'] for name in SLOTS if name!='DeadCallerIncompleteSnapshot'),'actual-composed-function-bindings')
  manifest=dict(schema='mckernel.current290.dead-caller-lifecycle-delta.composition.v1',baseline_source=FROZEN_INPUTS['baseline'],patch_source=FROZEN_INPUTS['patch'],installer=reference(__file__),independent_source_review=authorization['source_review'],authorization_sha256=hashlib.sha256(canonical(authorization)).hexdigest(),prior_census_manifest_sha256=hashlib.sha256(canonical(census)).hexdigest(),changed_slots=list(REPLACE),added_slots=list(ADD),manifest_slot=MANIFEST_SLOT,original_file_PUBLISHED_RELEASE_preserved=True,prior_census_three_slots_and_manifest_preserved=True,all_other_existing_globals_identity_preserved=True,function_fingerprints={name:fingerprint(module.__dict__[name]) for name in SLOTS if name!='DeadCallerIncompleteSnapshot'},old_release_canonical_sha256=OLD_RELEASE_CANONICAL_SHA,old_plan_sha256=OLD_PLAN_SHA)
  module.__dict__[MANIFEST_SLOT]=manifest
  return manifest
 except BaseException:
  for name in REPLACE:module.__dict__[name]=before[name]
  for name in ADD:module.__dict__.pop(name,None)
  module.__dict__.pop(MANIFEST_SLOT,None)
  raise
