"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unbound conversion-frontier readonly operation adapter: no build/native authority.
Retains the existing weekly guard, exact current clock minima and operation review.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,re,time
D=Path(__file__).resolve().parent
BINDING=D/'ROOT-READONLY-GUARD-BINDING.ACTUAL.json'
FIXED={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ATTEMPT-0001-POSTJOIN-FRESH-CONTROLS-SOURCE-1/FIXED-READONLY-INPUTS.json', 'bytes': 644, 'sha256': '1848820e91090d03f3088fa5e80b7081ab080d71149609a0f6d1ae536a1fb7b2'}
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
ARM={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/attempt-0001/ACTUAL-CONTROLS-ARMED.json', 'bytes': 1226, 'sha256': '4ff25cbf4135e78c58d973bd3f22c4fc7f305e96cb37bc620ebff0c617cf2db2'}
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
THREAD='01a18a76-4f1e-7900-8ed6-127394e93689'
WEEKLY=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133)
WINDOW_SHA='c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
MAXIMUM=(1793774133,1556234.56891299,1571572.6959598332)
OPERATION='conversion-first-postretirement-currentfree-readonly'
def need(ok,why):
 if not ok:raise ValueError(why)
def decode(raw):
 def unique(rows):
  d={}
  for k,v in rows:need(k not in d,'duplicate JSON key');d[k]=v
  return d
 def bad(_):raise ValueError('nonfinite JSON')
 return json.loads(raw,object_pairs_hook=unique,parse_constant=bad)
def ref(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink() and p.is_file(),'absolute regular byte subject');b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'} and ref(row['path'])==row,'exact immutable BYTE reference');return Path(row['path'])
def read(row):return decode(auth(row).read_bytes())
def load(row,name):
 p=auth(row);s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def triplet(v):
 need(type(v)in(list,tuple) and len(v)==3 and all(type(x)in(int,float) and math.isfinite(x) and x>=0 for x in v),'three finite UTC/MONO/BOOT clocks');return tuple(v)
def fixed_subjects():
 f=read(FIXED);need(set(f)=={'guardian','accepted_helper'},'exact minimal Q guard/binder subjects')
 for row in f.values():auth(row)
 result={'fixed_inputs':FIXED,'readonly_guard':ref(__file__)};result.update(f);return result

def validate_operation(op,review,subjects,context,clocks,ceilings):
 clocks=triplet(clocks);limits=triplet(op['operation_cutoffs']);caps=triplet(ceilings)
 need(op['schema']=='mckernel.explicit-new-window-operation-successor.v1' and op['author']=='/root' and op['decision']=='EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and op['operation']==OPERATION,'distinct exact readonly operation')
 need(op['window_sha256']==op['first_prepared_window_sha256']==WINDOW_SHA and op['weekly_limit_identity']==WEEKLY and op['billing_mode']=='included_only' and op['allow_prepaid_fallback'] is False and op['predecessor_cutoffs'] is None,'exact current weekly only; no inherited grant')
 need(not any(k in op for k in ('credit_run_id','credit_ceiling','minimum_cumulative_spent','api_key')),'no historical credit or API billing')
 need(all(0<limit<=maximum and 0<cap<=maximum and now<min(limit,cap) for now,limit,cap,maximum in zip(clocks,limits,caps,MAXIMUM)),'all clocks strictly before authorized/effective minimum')
 need(op['subjects']==subjects and op['context']==context and op['guardian']==dict(source=subjects['guardian'],entrypoint='guard') and '/root'in op['source_owners'],'exact readonly subject/context and Q guardian')
 need(review['schema']=='mckernel.independent-operation-window-review.v1' and review['decision']=='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and review['independent'] is True and review['implementation_ownership'] is False and isinstance(review['reviewer'],str) and review['reviewer'].startswith('/root/') and review['reviewer']not in op['source_owners'] and review['operation']==OPERATION and review['successor']==op,'independent exact readonly operation review')
 return limits

def binding_metadata(binding):
 need(set(binding)=={'author','decision','runtime_authority','source','successor','independent_review'} and binding['author']=='/root' and binding['decision']=='BIND_REVIEWED_CONVERSION_FRONTIER_READONLY_GUARD' and binding['runtime_authority'] is None and binding['source']==ref(__file__),'Root exact source binding, no native grant')
 op=read(binding['successor']);review=read(binding['independent_review']);c=op['context'];return op,review,c,context_subjects(c)

def context_subjects(c):
 expected={'current_ledger','current_boundary','post119_current_free','nonce','source_authority','armed_controls','bootstrap_caps','readonly_source_closure'}
 need(set(c)==expected and c['armed_controls']==ARM and type(c['nonce'])is str and re.fullmatch('[0-9a-f]{32}',c['nonce']),'exact new readonly context')
 pins=decode((D/'HISTORY-INPUTS.json').read_bytes())
 need(c['current_ledger']==pins['root70_pending_ledger']and c['current_boundary']==pins['root69_boundary']and c['post119_current_free']==pins['previous_free'],'exact74pending boundary and historical Root69 free, not new free')
 for key in ('current_ledger','current_boundary','post119_current_free','source_authority','armed_controls','bootstrap_caps'):auth(c[key])
 ledger=read(c['current_ledger']);need(c['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']+ledger['reserved_unused_nonces']+ledger['used_readonly_operation_ids'],'unused distinct readonly ID')
 need(set(c['readonly_source_closure'])=={'observer','physical_adapter','capture_parent','history'},'exact four readonly sources')
 need(c['readonly_source_closure']==dict(observer=ref(D/'observe_conversion_postjoin.py'),physical_adapter=ref(D/'readonly_history_guard.py'),capture_parent=ref(D/'root_capture_parent.py'),history=ref(D/'postjoin_history.py')),'exact coherent postjoin source closure')
 for row in c['readonly_source_closure'].values():auth(row)
 history=load(c['readonly_source_closure']['history'],'pure_postretirement_history');actors,_,_=history.validate(read(c['source_authority']));need(len(actors)==230,'230rows225identities retained')
 subjects=fixed_subjects();subjects.update({'root:'+k:c[k]for k in ('current_ledger','current_boundary','post119_current_free','source_authority','armed_controls','bootstrap_caps')});subjects.update({'readonly:'+k:v for k,v in c['readonly_source_closure'].items()});subjects['history_inputs']=ref(D/'HISTORY-INPUTS.json');return subjects


def confirmed_weekly_ceiling(state,guardian):
 row=guardian.validate_confirmed_row(state.get('weekly_confirmed_usage'));need(state.get('thread_id')==THREAD and state.get('weekly_usage')==row and not state.get('weekly_confirmation_pending') and not state.get('weekly_usage_error'),'confirmed same-period usage, no pending confirmation')
 return tuple(min(a,b)for a,b in zip(MAXIMUM,triplet([state.get('weekly_effective_end'),state.get('weekly_effective_monotonic_end'),state.get('weekly_effective_boot_end')])))

def _evaluate():
 b=read(ref(BINDING));op,review,c,subjects=binding_metadata(b);state=decode(STATE.read_bytes());guardian=load(subjects['guardian'],'exact_readonly_weekly_guardian');ceilings=confirmed_weekly_ceiling(state,guardian)
 clocks=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME));limits=validate_operation(op,review,subjects,c,clocks,ceilings)
 for subject in subjects.values():auth(subject)
 # Reuse existing weekly cap binder only; no readonly operation or build alias.
 accepted_ref=read(FIXED).get('accepted_helper');need(accepted_ref is not None,'exact weekly cap binder required')
 binder=load(accepted_ref,'pure_readonly_weekly_cap_binder');need(tuple(binder.weekly_limits(read(c['armed_controls']),read(c['bootstrap_caps'])))==limits,'same original armed/bootstrap minimum')
 observed=triplet(guardian.guard());after=confirmed_weekly_ceiling(decode(STATE.read_bytes()),guardian)
 dynamic=triplet(guardian.current_caps());effective=tuple(min(a,b,c,d)for a,b,c,d in zip(limits,ceilings,after,dynamic))
 need(all(a<=b<limit for a,b,limit in zip(clocks,observed,effective)),'actual Q guard remains inside all observed minima')
 return observed,effective
def guard():return list(_evaluate()[0])
def current_cutoffs():return tuple(_evaluate()[1])
