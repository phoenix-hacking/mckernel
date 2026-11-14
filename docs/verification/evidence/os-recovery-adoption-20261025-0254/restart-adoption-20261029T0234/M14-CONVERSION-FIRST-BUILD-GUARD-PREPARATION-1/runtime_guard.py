"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Conversion-first build operation binding; does not grant execution or acquire resources.
UNBOUND until Root authors the exact binding and an independent operation review.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,math,re,time
D=Path(__file__).resolve().parent
BINDING=D/'ROOT-PRODUCER-GUARD-BINDING.ACTUAL.json'
FIXED={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-CONVERSION-FIRST-BUILD-GUARD-PREPARATION-1/FIXED-INPUTS.SOURCE-ONLY.json', 'bytes': 6266, 'sha256': 'a428be01e57aae19c754588bd68fb3c5804fd9cd304abc01cce354109ced25ea'}
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
 """Authenticate the exact producer source and retained object closure."""
 f=read(FIXED);out={'fixed_inputs':FIXED,'runtime_guard':ref(__file__)};out.update(f)
 request=read(f['request']);manifest=read(f['snapshot_manifest']);mapping=read(f['snapshot_map']);recipe=read(f['recipe']);reuse=read(f['reuse_descriptor']);profile=read(f['profile119'])
 need(request['author']=='/root' and request['runtime_authority'] is None and request['candidate']==f['composition'] and request['recipe']==f['recipe'] and request['snapshot_map']==f['snapshot_map'] and request['actual_snapshot_manifest']==f['snapshot_manifest'],'exact actual conversion request')
 need(reuse['author']=='/root' and reuse['runtime_authority'] is None and reuse['candidate']==f['composition'] and reuse['recipe']==f['recipe'] and len(reuse['configuration'])==10 and len(reuse['retained_objects'])==9 and reuse['new_object_tokens']==['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o'] and reuse['retained_sdk21']=='EXACT_CURRENT119_PROFILE_AND_HISTORICAL_EXPORT_NO_RECOMPILE','exact nine retained objects and SDK')
 need(recipe['retained_inputs']==reuse['retained_objects'] and reuse['configuration']==profile['inputs']['configuration'],'same recipe objects and profile configuration')
 need(len(recipe['ordered_commands'])==3 and len(mapping['entries'])==149 and len(manifest['files'])==149 and sum(r['relative'].endswith('.rs') for r in manifest['files'])==138,'exact three commands and frozen 149/138')
 need(manifest['schema']=='mckernel.exact-kernel-rust-subtree-readonly.v1' and manifest['runtime_authority'] is None and manifest['container_destination']=='/src/kernel/rust' and manifest['external_inputs']==profile['inputs']['external_relative_modules'],'exact snapshot schema and external inputs')
 expected={r['relative']:r['source'] for r in mapping['entries']};seen=set();root=Path(manifest['export_root']);need(root.is_absolute() and len(expected)==149,'unique source mapping')
 for row in manifest['files']:
  name=row['relative'];p=Path(name);need(not p.is_absolute() and '..' not in p.parts and str(p)==name and name not in seen and name in expected,'exact unique relative source');seen.add(name);subject=row['snapshot'];source=expected[name]
  need(subject['path']==str(root/p) and subject['sha256']==source['sha256'] and subject['bytes']==source['bytes'],'unchanged selected snapshot bytes');out['snapshot:'+name]=subject
 need(seen==set(expected),'complete source snapshot')
 affected=read(f['affected']);need(recipe['affected']==f['affected'] and affected['frozen_current119_profile']==f['profile119'] and affected['runtime_authority'] is None,'exact affected unit source map')
 overlay={r['target']:r['source'] for r in affected['file_overlay']};origin=reuse['original_origin']
 for row in profile['inputs']['postimages']:
  name=row['relative'];value=row['postimage']
  if name in ('kernel/syscall.c','kernel/CMakeLists.txt'):value=overlay[name]
  elif name.endswith('/f06_rt_sigreturn_origin.h'):value=origin['actual_generated_header']
  elif name.endswith('/f06_clone_cpuid_metadata.rs'):value=origin['actual_generated_metadata']
  out['postimage:'+name]=value
 for i,row in enumerate(reuse['configuration']):out['config:'+str(i)]=row['source']
 for i,row in enumerate(reuse['retained_objects']):out['retained_object:'+str(i)]=row['source']
 for i,row in enumerate(manifest['external_inputs']):out['external:'+str(i)]=row['source']
 for key,row in reuse['original_origin'].items():out['origin:'+key]=row
 return out

def validate_frontier(context):
 """Reuse the unmodified sealer predicate, without executing its live history checks."""
 f=read(FIXED);tree=ast.parse(auth(f['frontier_sealer']).read_bytes());funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_latest_frontier'];need(len(funcs)==1,'one pinned frontier predicate')
 ns={'read':lambda p:decode(Path(p).read_bytes()),'auth':auth,'re':re,'ROOT68_LEDGER':f['root68_ledger'],'ROOT68_FREE':f['root68_free'],'ROOT68_BOUNDARY':f['root68_boundary']}
 exec(compile(ast.Module(body=funcs,type_ignores=[]),str(auth(f['frontier_sealer'])),'exec'),ns)
 ledger=ns['validate_latest_frontier'](context,read(f['root68_ledger']))
 bundle=read(context['current_bindings']);review=read(bundle['independent_adoption_review']);need(review['reviewer'] not in ('/root','/root/m14_integration_terra'),'independent frontier reviewer')
 return ledger

def validate_operation(successor,review,subjects,context,clocks,ceilings):
 """Pure operation/review checks; successful return is not a build release."""
 clocks=triplet(clocks);ceilings=triplet(ceilings);limits=triplet(successor['operation_cutoffs'])
 need(successor['schema']=='mckernel.explicit-new-window-operation-successor.v1' and successor['author']=='/root' and successor['decision']=='EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and successor['operation']=='conversion-first-three-command-build','Root conversion-first build operation only')
 need(successor['window_sha256']==successor['first_prepared_window_sha256']==WINDOW_SHA,'exact current weekly window')
 need(successor['weekly_limit_identity']==WEEKLY and successor['billing_mode']=='included_only' and successor['allow_prepaid_fallback'] is False and successor['predecessor_cutoffs'] is None,'same included-only weekly allowance; no replay')
 need(not any(k in successor for k in ('credit_run_id','credit_ceiling','minimum_cumulative_spent','api_key')),'historical credit fields never active')
 need(all(0<l<=maximum and 0<cap<=maximum and now<min(l,cap) for now,l,cap,maximum in zip(clocks,limits,ceilings,MAXIMUM)),'strict clocks before minimum of authorized operation and current effective ceilings')
 need(successor['subjects']==subjects and successor['context']==context and type(subjects)is dict and bool(subjects),'exact conversion producer and fresh frontier subjects/context')
 need(successor['guardian']==dict(source=subjects['guardian'],entrypoint='guard') and all(owner in successor['source_owners'] for owner in ('/root','/root/m14_integration_terra')),'exact guardian and owners')
 need(review['schema']=='mckernel.independent-operation-window-review.v1' and review['decision']=='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and review['independent'] is True and review['implementation_ownership'] is False and isinstance(review['reviewer'],str) and review['reviewer'].startswith('/root/') and review['reviewer'] not in successor['source_owners'] and review['operation']=='conversion-first-three-command-build' and review['successor']==successor,'independent exact producer operation review')
 return limits

def binding_metadata(binding):
 need(set(binding)=={'author','decision','runtime_authority','source','successor','independent_review'} and binding['author']=='/root' and binding['decision']=='BIND_REVIEWED_CONVERSION_FIRST_PRODUCER_GUARD' and binding['runtime_authority'] is None and binding['source']==ref(__file__),'Root exact build-only operation binding, no execution grant')
 successor=read(binding['successor']);review=read(binding['independent_review']);context=successor['context']
 need(set(context)=={'request','nonce','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor'} and context['armed_controls']==ARM,'exact fresh frontier build context')
 f=read(FIXED);need(context['request']==f['request'] and context['candidate_snapshot_manifest']==f['snapshot_manifest'] and context['reuse_descriptor']==f['reuse_descriptor'] and context['bootstrap_caps']==f['bootstrap_caps'],'exact request, bootstrap and conversion inputs')
 need(type(context['nonce'])is str and re.fullmatch('[0-9a-f]{32}',context['nonce']) and context['nonce']!='e984210ca59641b299cf42d392eb953b','fresh explicit producer nonce')
 for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor'):auth(context[k])
 validate_frontier(context)
 subjects=fixed_subjects();subjects.update({'root:'+k:context[k] for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor')})
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
 # History is verified by the sealer before claim; only the pure latest-frontier predicate is repeated here.
 accepted=load(subjects['accepted_helper'],'exact_current119_root65_metadata')
 need(tuple(accepted.weekly_limits(read(context['armed_controls']),read(context['bootstrap_caps'])))==limits,'same sealer earliest actual armed/bootstrap cutoffs')
 guardian=load(subjects['guardian'],'actual_weekly_q_guardian');observed=triplet(guardian.guard())
 need(all(a<=b<min(limit,cap) for a,b,limit,cap in zip(clocks,observed,limits,ceilings)),'actual weekly guardian clocks under both authorized and observed effective cutoffs')
 return list(observed)
