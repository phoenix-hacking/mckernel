"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
CURRENT119 build operation binding; does not grant execution or acquire resources.
UNBOUND until Root authors the exact binding and an independent operation review.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,re,time
D=Path(__file__).resolve().parent
BINDING=D/'ROOT-PRODUCER-GUARD-BINDING.ACTUAL.json'
FIXED={'path':str(D/'FIXED-INPUTS.SOURCE-ONLY.json'),'bytes':4727,'sha256':'e5d02301d120a59e2cc50ecebb7094d8177e85ed3c036fbb61f42e936955d185'}
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
ARM={'path':'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/ACTUAL-CONTROLS-ARMED.json','bytes':2021,'sha256':'42c8b2a0045a7720f15ef591436a0158c2e08f219e30982d22f961c19be4c039'}
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
THREAD='01a18582-1fc6-77b1-bfb6-15c86483f579'
WEEKLY=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133)
WINDOW_SHA='c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
MAXIMUM=(1793774133,1556235.568922472,1571573.6959699572)
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok,why):
 if not ok:raise ValueError(why)
def decode(raw):
 def unique(rows):
  x={}
  for k,v in rows:need(k not in x,'duplicate JSON key');x[k]=v
  return x
 def bad(_):raise ValueError('nonfinite JSON')
 return json.loads(raw,object_pairs_hook=unique,parse_constant=bad)
def ref(path):
 p=Path(path);need(p.is_absolute() and p.is_file() and not p.is_symlink(),'absolute regular subject');b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'} and ref(row['path'])==row,'exact immutable BYTE subject');return Path(row['path'])
def read(row):return decode(auth(row).read_bytes())
def load(row,name):
 p=auth(row);s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def triplet(v):
 need(type(v)in(list,tuple) and len(v)==3 and all(type(x)in(int,float)and math.isfinite(x)and x>=0 for x in v),'three finite UTC/MONO/BOOT values');return tuple(v)

def fixed_subjects():
 """Exact existing producer source closure; no directory crawl or resource query."""
 f=read(FIXED);out={'fixed_inputs':FIXED,'runtime_guard':ref(__file__)};out.update(f)
 adoption=read(f['adoption']);export=read(f['export']);profile=read(f['profile_template']);manifest=read(f['export_manifest']);recipe=read(f['recipe'])
 need(adoption['author']=='/root' and adoption['status']=='PASS_EXACT18_CANONICAL119_SOURCE_ADOPTION_ONLY' and len(adoption['canonical_rows'])==18,'exact accepted canonical18 source binding')
 need(export['author']=='/root' and export['canonical_adoption']==f['adoption'] and export['files_count']==133 and export['rust_count']==122 and len(export['files'])==133,'exact actual133/122 export binding')
 need(len(manifest['files'])==133 and sum(r['relative'].endswith('.rs')for r in manifest['files'])==122 and len(recipe['ordered_commands'])==4,'unchanged source manifest and four-command recipe')
 need(export['directory']==manifest['export_root'] and [r['actual_export'] for r in export['files']]==[r['snapshot'] for r in manifest['files']],'same exact export rows')
 for row in adoption['canonical_rows']:out['canonical:'+row['relative']]=row['actual']
 for row in export['files']:out['export:'+row['relative']]=row['actual_export']
 inputs=profile['inputs'];need(inputs['source6153'] and profile['producer_contract']['reused_objects']==8 and profile['producer_contract']['SDK21_recompiled'] is False,'source6153 and no SDK21 rebuild')
 config=inputs['configuration'];retained=[r for r in inputs['objects'] if not r['replace']];external=inputs['external_relative_modules'];need(len(retained)==8 and len(external)==3,'exact eight retained object and external3 source inputs')
 for i,row in enumerate(config):out['config:'+str(i)]=row['source']
 for i,row in enumerate(retained):out['retained_object:'+str(i)]=row['source']
 for i,row in enumerate(external):out['external:'+str(i)]=row['source']
 return out

def validate_operation(successor,review,subjects,context,clocks,ceilings):
 """Pure operation/review checks; successful return is not a build release."""
 clocks=triplet(clocks);ceilings=triplet(ceilings);limits=triplet(successor['operation_cutoffs'])
 need(successor['schema']=='mckernel.explicit-new-window-operation-successor.v1' and successor['author']=='/root' and successor['decision']=='EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and successor['operation']=='current119-build','Root current119 producer operation only')
 need(successor['window_sha256']==successor['first_prepared_window_sha256']==WINDOW_SHA,'exact current weekly window')
 need(successor['weekly_limit_identity']==WEEKLY and successor['billing_mode']=='included_only' and successor['allow_prepaid_fallback'] is False and successor['predecessor_cutoffs'] is None,'same included-only weekly allowance; no replay')
 need(not any(k in successor for k in ('credit_run_id','credit_ceiling','minimum_cumulative_spent','api_key')),'historical credit fields never active')
 need(all(0<l<=cap<=maximum and now<l for now,l,cap,maximum in zip(clocks,limits,ceilings,MAXIMUM)),'strict operation cutoff inside actual earliest weekly clocks')
 need(successor['subjects']==subjects and successor['context']==context and type(subjects)is dict and bool(subjects),'exact producer and Root65 subjects/context')
 need(successor['guardian']==dict(source=subjects['guardian'],entrypoint='guard') and '/root' in successor['source_owners'],'exact guardian and owners')
 need(review['schema']=='mckernel.independent-operation-window-review.v1' and review['decision']=='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and review['independent'] is True and review['implementation_ownership'] is False and isinstance(review['reviewer'],str) and review['reviewer'].startswith('/root/') and review['reviewer'] not in successor['source_owners'] and review['operation']=='current119-build' and review['successor']==successor,'independent exact producer operation review')
 return limits

def binding_metadata(binding):
 need(set(binding)=={'author','decision','runtime_authority','source','successor','independent_review'} and binding['author']=='/root' and binding['decision']=='BIND_REVIEWED_CURRENT119_PRODUCER_GUARD' and binding['runtime_authority'] is None and binding['source']==ref(__file__),'Root exact build-only operation binding, no execution grant')
 successor=read(binding['successor']);review=read(binding['independent_review']);context=successor['context']
 need(set(context)=={'request','nonce','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps'} and context['current_free']==read(FIXED)['current_free'] and context['armed_controls']==ARM,'exact Root65 context and independently accepted current-free')
 need(type(context['nonce'])is str and re.fullmatch('[0-9a-f]{32}',context['nonce']) and context['nonce']!='e984210ca59641b299cf42d392eb953b','fresh explicit producer nonce')
 for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps'):auth(context[k])
 ledger=read(context['current_ledger']);need(context['nonce'] not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'never reuse consumed or abandoned nonce')
 subjects=fixed_subjects();subjects.update({'root:'+k:context[k] for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps')})
 return successor,review,context,subjects


def confirmed_weekly_ceiling(state):
 # Reuse the exact Q guardian's confirmed authorized-period rule. Raw reset
 # metadata may jitter within that period; the canonical deadline never changes.
 guardian=load(read(FIXED)['guardian'],'pure_confirmed_weekly_period')
 row=guardian.validate_confirmed_row(state.get('weekly_confirmed_usage'))
 need(state.get('thread_id')==THREAD and state.get('weekly_usage')==row and not state.get('weekly_confirmation_pending') and not state.get('weekly_usage_error'),'same Root, confirmed usage and no unresolved coalesced confirmation')
 effective=triplet([state.get('weekly_effective_end'),state.get('weekly_effective_monotonic_end'),state.get('weekly_effective_boot_end')]);return tuple(min(a,b)for a,b in zip(MAXIMUM,effective))

def guard():
 # Fail closed before any guardian call when Root has not bound this operation.
 binding=read(ref(BINDING));successor,review,context,subjects=binding_metadata(binding)
 state=decode(STATE.read_bytes());ceilings=confirmed_weekly_ceiling(state)
 clocks=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME));limits=validate_operation(successor,review,subjects,context,clocks,ceilings)
 for subject in subjects.values():auth(subject)
 # Pure full accepted Root65/physical history reader; it performs no live capture.
 accepted=load(subjects['accepted_helper'],'exact_current119_root65_metadata');free=read(context['current_free']);ledger=read(context['current_ledger']);accepted.accepted_metadata(context,free,ledger);accepted.accepted_chain(context)
 need(tuple(accepted.weekly_limits(read(context['armed_controls']),read(context['bootstrap_caps'])))==limits,'same sealer earliest actual armed/bootstrap cutoffs')
 guardian=load(subjects['guardian'],'actual_weekly_q_guardian');observed=triplet(guardian.guard())
 need(all(a<=b<limit for a,b,limit in zip(clocks,observed,limits)),'actual weekly guardian clocks under same earliest cutoff')
 return list(observed)
