"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact existing metadata/current-adoption predicate reuse. No guard/process calls.
"""
from pathlib import Path
from decimal import Decimal
import ast,hashlib,importlib.util,json,math
HERE=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
CONTROL=E/'restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1'
GUARDIAN=E/'restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/new-guardian-source-1/guardian_guard.py'
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
ORIGINAL_MAX=[1793253600.0,1035704.5689393478,1051042.6959879305]

def need(value,message):
 if not value:raise ValueError(message)
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'} and Path(row['path']).is_absolute() and not Path(row['path']).is_symlink() and ref(row['path'])==row,'exact BYTE binding');return Path(row['path'])
def read(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 path=auth(row);spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
CUTOFF_REF=dict(path=str(CONTROL/'cutoff_bindings.py'),bytes=1625,sha256='0c3c71e918a131b2ae3a3a7cc4aba7014af602dc6bed5704e58af69add118998')
CUTOFF=load(CUTOFF_REF,'unchanged_m14_monotone_caps')

def accepted_metadata(q,free,ledger):
 # Exact same fields/decisions as d216 validate_acceptance/current_adoption.
 need(free['independent']is True and free['implementation_ownership']is False and free['decision']=='PASS_ROOT64_CURRENT118_POSTJOIN_CURRENT_FREE' and free['current_free']is True,'existing independent Root64 accepted free')
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary']is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation']is True,'existing Root65 complete frontier')
 need(ledger['current_physical_clearance_pending']is False and ledger['latest_accepted_free_boundary']==q['current_free'],'matching actual ledger/free boundary')
 need(len(ledger['consumed_nonces'])==72,'existing exact72 once history')
 build=ledger['current118_build']
 need(build['normal_retirement_pending']is False and build['current_physical_clearance_pending']is False and build['current_free']==q['current_free'],'existing Root65 current118 retirement linkage')

def accepted_chain(q):
 bindings=read(q['current_bindings'])
 need(bindings['phase']=='accepted_current' and bindings['ledger']==q['current_ledger'] and bindings['latest_free']==q['current_free'],'same accepted-current bindings/ledger/free')
 boundary=read(bindings['current_boundary']);source=boundary['observer']
 need(source=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/expert-census-observer-consumer-source-1/observe_current64_current118_postjoin.py', 'bytes': 45953, 'sha256': '124f9f04c295a205751865cba962c1394c909449d5a5495515717e2f12013b4a'},'exact expert-census observer body and constructor namespace')
 observer=load(source,'actual_root65_pure_adoption')
 # Proven existing pure reader: all72/native history, retirement, raw capture,
 # positive joins, independent free and boundary/schema checks; no observe/guard.
 return observer.validate_current_adoption(bindings,observer.validate_retained())

def armed_metadata(armed,packet_ref,current_thread,bootstrap):
 limits=CUTOFF.bind_cutoffs(ORIGINAL_MAX,armed,bootstrap)
 need(ref(GUARDIAN)['sha256']=='5af549bdf87a248a76bfe4e96de2ddc8c20435f3bafff5397ca7a9557ca68df4','exact original guardian predicate source')
 tree=ast.parse(GUARDIAN.read_bytes());original=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_armed')
 prefix=[]
 for node in original.body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='supervisor'for t in node.targets):break
  prefix.append(node)
 need(len(prefix)==6,'exact metadata prefix before first supervisor/observe')
 fn=ast.FunctionDef(name='validate_existing_armed_metadata',args=original.args,body=prefix+[ast.Return(value=ast.Name(id='armed',ctx=ast.Load()))],decorator_list=[],returns=None,type_comment=None)
 namespace=dict(need=need,Decimal=Decimal,THREAD=current_thread,PACKET_SHA=packet_ref['sha256'],WINDOW_SHA='0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e',DEADLINE=limits[0],MONO_CAP=limits[1],BOOT_CAP=limits[2],RUN='7f4af94a83b14cc08f97401f5891d965',CEILING=Decimal('57774.852125'),SPENT_FLOOR=Decimal('22812.3311'))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(GUARDIAN),'exec'),namespace)
 namespace['validate_existing_armed_metadata'](armed,None)
 return limits

def review_binds_guard(review,guard):
 need(review['independent']is True and review['implementation_ownership']is False and str(review['decision']).startswith('PASS'),'independent fresh guard source review only')
 def contains(value):
  if value==guard:return True
  if isinstance(value,dict):return any(contains(v)for v in value.values())
  if isinstance(value,list):return any(contains(v)for v in value)
  return False
 need(contains(review),'review binds exact fresh runtime guard source')
