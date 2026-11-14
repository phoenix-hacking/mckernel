"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact existing metadata/current-adoption predicate reuse. No guard/process calls.
"""
from pathlib import Path
from decimal import Decimal
import ast,hashlib,importlib.util,json,math
HERE=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
CONTROL=E/'restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1'
GUARDIAN=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/guardian_guard.py')
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
ORIGINAL_MAX=[1793774133,1556237.568944064,1571575.6959913536]

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
 need(source=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/observe_current64_current118_postjoin.py', 'bytes': 46502, 'sha256': '59052b99eb32e98bcca6d08c77a37d16cd6bd5e0e4e5fe34f5a06297f8b05c59'},'exact expert-census observer body and constructor namespace')
 observer=load(source,'actual_root65_pure_adoption')
 # Proven existing pure reader: all72/native history, retirement, raw capture,
 # positive joins, independent free and boundary/schema checks; no observe/guard.
 return observer.validate_current_adoption(bindings,observer.validate_retained())

WEEKLY_BINDINGS_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/weekly_source_bindings.py', 'bytes': 3108, 'sha256': '7cf5be38eaa4a1a96a1451c6b87d174d8d545e78c0279001524184524c07b1a4'}
WEEKLY_AUTH_REF={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/USER-WEEKLY-ONLY-AUTHORIZATION.json', 'bytes': 1391, 'sha256': '234367690e532f77670374986be31fbe2ce66e9bdf3dd302da9af38f62a93c68'}
WEEKLY_WINDOW_REF={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/ACTUAL-WINDOW.json', 'bytes': 1373, 'sha256': 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'}
WEEKLY_GUARDIAN_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/guardian_guard.py', 'bytes': 16310, 'sha256': '3b4d2c9816d69084a26433383333082885a2b4bfe88a17e39cd6675702d843ab'}

def weekly_limits(armed,bootstrap):
 binding=load(WEEKLY_BINDINGS_REF,'pure_actual_weekly_caps')
 return binding.minimum_caps(read(WEEKLY_AUTH_REF),read(WEEKLY_WINDOW_REF),bootstrap,armed['caps'])

def armed_metadata(armed,packet_ref,current_thread,bootstrap):
 guardian=load(WEEKLY_GUARDIAN_REF,'exact_weekly_guardian_metadata_only')
 need(current_thread==guardian.THREAD and packet_ref['sha256']==guardian.PACKET_SHA,'actual weekly current Root/packet')
 guardian.validate_armed_metadata(armed) # Pure function; never guardian.guard().
 return weekly_limits(armed,bootstrap)


def review_binds_guard(review,guard):
 need(review['independent']is True and review['implementation_ownership']is False and str(review['decision']).startswith('PASS'),'independent fresh guard source review only')
 def contains(value):
  if value==guard:return True
  if isinstance(value,dict):return any(contains(v)for v in value.values())
  if isinstance(value,list):return any(contains(v)for v in value)
  return False
 need(contains(review),'review binds exact fresh runtime guard source')
