"""Functional exact census composition only; no security testing.
Installs a separately authorized three-symbol diagnostic delta into a genuine
configured e49 module. It never configures, runs, opens FDs or changes custody.
"""
import ast,hashlib,json,marshal,os,subprocess,types
from pathlib import Path
FROZEN_INPUTS = json.loads('{"baseline": {"bytes": 128910, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py", "sha256": "e49eaf2a7bacc6a64523f9f6c91516b9a3abefc875cdc1d8941c4e6b55473de3"}, "corrected": {"bytes": 133996, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-correction-source-1/native_rust_cutover_image_terminal_cleanup.PROCESS-LIFECYCLE.v2.SOURCE-ONLY.py", "sha256": "1eb0a669f5d3c248afa1b14130421a1582f1410847be95494ec107a322f6ad9a"}, "old_release": {"bytes": 241402, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-normal-cleanup-source-1/ROOT-NORMAL-RETIREMENT-PREPARATION-1/RELEASE.PASS_EXECUTION_RELEASE.json", "sha256": "9c7589afa411c1b40fe02777facf69007b885d228632b12c3f34e5a091b517e9"}, "review": {"bytes": 5811, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-review-1/REVIEW.json", "sha256": "6d138ab30b2aed59af88551f005787eda2a4e6c8936ceb3cafc69c80908522e7"}}')
SLOTS=('PROC_CODE','root_command','validate_process_report')
BASELINE_FUNCTIONS=('root_command','validate_process_report','process_absent','run_privileged','canonical')
MANIFEST_SLOT='_PROCESS_CENSUS_DELTA_MANIFEST'
OLD_RELEASE_CANONICAL_SHA='57c62c0c739438ca4a68c2ec167dc953f7274b4968e7c4e6dba74272acc32f70'
OLD_PLAN_SHA='279b40f40ae69255914c064e92486fdfbb65ad798077206dc9c598d185e277f8'
class BridgeRefusal(RuntimeError):pass
def need(value,message):
 if not value:raise BridgeRefusal(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def authenticated(ref):
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact-source-bytes:'+ref['path']);return raw
def source_nodes(raw,path):
 tree=ast.parse(raw,path);found={}
 for node in tree.body:
  if isinstance(node,ast.FunctionDef):found[node.name]=node
  elif isinstance(node,ast.Assign):
   for target in node.targets:
    if isinstance(target,ast.Name):found[target.id]=node
 return found
def expected_authorization():
 return dict(schema='mckernel.current290.process-census-delta.authorization.v1',author='/root',
             decision='GRANT_EXACT_PROCESS_CENSUS_LIFECYCLE_DELTA',
             baseline_source_sha256=FROZEN_INPUTS['baseline']['sha256'],
             corrected_source_sha256=FROZEN_INPUTS['corrected']['sha256'],
             independent_review_sha256=FROZEN_INPUTS['review']['sha256'],
             old_release_canonical_sha256=OLD_RELEASE_CANONICAL_SHA,old_plan_sha256=OLD_PLAN_SHA)
def function_fingerprint(function):return hashlib.sha256(marshal.dumps(function.__code__)).hexdigest()
def install_census_delta(module,authorization,*,slots=SLOTS):
 need(tuple(slots)==SLOTS,'unapproved-delta-slots')
 need(type(module) is types.ModuleType and MANIFEST_SLOT not in module.__dict__,'genuine-not-already-composed-module')
 need(authorization==expected_authorization(),'distinct-exact-new-authorization-required')
 refs=FROZEN_INPUTS
 old_raw=authenticated(refs['baseline']);new_raw=authenticated(refs['corrected']);review=json.loads(authenticated(refs['review']));release=json.loads(authenticated(refs['old_release']))
 need(review['decision']=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY' and review['reviewer']=='/root/census_lifecycle_review','exact-independent-source-review')
 old=source_nodes(old_raw,refs['baseline']['path']);new=source_nodes(new_raw,refs['corrected']['path'])
 need({'__file__','PUBLISHED_SCRIPT','PROC_CODE','RELEASE','BOOT_ID','OWNER_PID','WAITER_PIDS','Refusal','__builtins__','os','subprocess','hashlib','json',*BASELINE_FUNCTIONS}<=set(module.__dict__),'missing-baseline-context-dependency')
 need(str(module.__file__)==refs['baseline']['path'],'baseline-file-identity')
 need(module.PUBLISHED_SCRIPT==ast.literal_eval(old['PUBLISHED_SCRIPT'].value),'baseline-published-source-binding')
 need(module.PROC_CODE==ast.literal_eval(old['PROC_CODE'].value),'baseline-PROC_CODE-binding')
 need(module.RELEASE==release and hashlib.sha256(canonical(module.RELEASE)).hexdigest()==OLD_RELEASE_CANONICAL_SHA,'unchanged-original-release')
 need(module.BOOT_ID==release['observation']['boot_id'] and module.OWNER_PID==release['observation']['target']['owner_pid'] and tuple(module.WAITER_PIDS)==tuple(r['pid'] for r in release['observation']['client_ledger']),'original-owner-boot-client-context')
 for name,expected in [('os',os),('subprocess',subprocess),('hashlib',hashlib),('json',json)]:need(module.__dict__.get(name) is expected,'unchanged-dependency:'+name)
 need('__builtins__' in module.__dict__ and isinstance(module.Refusal,type) and module.Refusal.__name__=='Refusal' and module.Refusal.__bases__==(ValueError,),'missing-execution-dependencies')
 expected={}
 for name in BASELINE_FUNCTIONS:
  node=old[name];need(not node.decorator_list and not node.args.defaults and not node.args.kw_defaults,'unexpected-baseline-function-shape')
  namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),refs['baseline']['path'],'exec',dont_inherit=True,optimize=0),namespace)
  value=module.__dict__.get(name)
  need(type(value) is types.FunctionType and value.__globals__ is module.__dict__ and value.__code__.co_filename==refs['baseline']['path'] and value.__code__==namespace[name].__code__,'baseline-function-modified:'+name)
  expected[name]=function_fingerprint(value)
 nodes=[]
 for name in SLOTS:
  node=new[name]
  if name=='PROC_CODE':need(isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id==name and isinstance(ast.literal_eval(node.value),str),'exact-PROC_CODE-constant')
  else:need(isinstance(node,ast.FunctionDef) and not node.decorator_list and not node.args.defaults and not node.args.kw_defaults,'closed-function-node')
  nodes.append(node)
 # A closed node allowlist: no imports, source-selection assignments, configure,
 # recover, file identity spoofing or transaction release/plan edits are compiled.
 compiled=compile(ast.Module(body=nodes,type_ignores=[]),refs['corrected']['path'],'exec',dont_inherit=True,optimize=0)
 need(set(compiled.co_names)==set(SLOTS),'unexpected-top-level-delta-name')
 before=dict(module.__dict__)
 try:
  exec(compiled,module.__dict__)
  changed={name for name,value in before.items() if module.__dict__.get(name) is not value}
  need(changed==set(SLOTS) and set(module.__dict__)==set(before),'unapproved-global-mutation')
  for name in SLOTS[1:]:need(module.__dict__[name].__globals__ is module.__dict__ and module.__dict__[name].__code__.co_filename==refs['corrected']['path'],'genuine-corrected-code-binding')
  need(module.__file__==before['__file__'] and module.PUBLISHED_SCRIPT==before['PUBLISHED_SCRIPT'] and module.RELEASE is before['RELEASE'],'old-file-published-release-preservation')
  manifest=dict(schema='mckernel.current290.process-census-delta.composition.v1',author=authorization['author'],reviewer=review['reviewer'],
                baseline_source=refs['baseline'],corrected_source=refs['corrected'],independent_review=refs['review'],
                authorization_sha256=hashlib.sha256(canonical(authorization)).hexdigest(),
                original_release=refs['old_release'],old_release_canonical_sha256=OLD_RELEASE_CANONICAL_SHA,old_plan_sha256=OLD_PLAN_SHA,
                changed_slots=list(SLOTS),manifest_slot=MANIFEST_SLOT,
                baseline_function_fingerprints=expected,
                corrected_function_fingerprints={name:function_fingerprint(module.__dict__[name]) for name in SLOTS[1:]},
                corrected_co_filename=refs['corrected']['path'],proc_code_sha256=hashlib.sha256(module.PROC_CODE.encode()).hexdigest(),
                original_file_and_PUBLISHED_SCRIPT_preserved=True,original_RELEASE_identity_preserved=True,
                original_process_absent_and_run_privileged_preserved=True,all_other_existing_globals_identity_preserved=True)
  module.__dict__[MANIFEST_SLOT]=manifest
  return manifest
 except BaseException:
  for name in SLOTS:module.__dict__[name]=before[name]
  module.__dict__.pop(MANIFEST_SLOT,None)
  raise
