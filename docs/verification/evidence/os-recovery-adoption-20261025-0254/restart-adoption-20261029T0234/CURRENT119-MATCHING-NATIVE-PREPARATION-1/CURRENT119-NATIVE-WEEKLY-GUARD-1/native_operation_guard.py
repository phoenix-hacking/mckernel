"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unbound CURRENT119 matching235 native operation adapter: no release/resource authority.
Existing native caller retains resource, ownership, once and teardown checks.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,re,time
D=Path(__file__).resolve().parent
BINDING=D/'ROOT-NATIVE-GUARD-BINDING.ACTUAL.json'
FIXED={'path':str(D/'FIXED-INPUTS.SOURCE-ONLY.json'),'bytes':8677,'sha256':'2dd00a3d0e022bdca1d775e03c08602c8acf943fc8f0e569f63a71360db788b9'}
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')
ARM={'path':'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/ACTUAL-CONTROLS-ARMED.json','bytes':2021,'sha256':'42c8b2a0045a7720f15ef591436a0158c2e08f219e30982d22f961c19be4c039'}
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
THREAD='01a18582-1fc6-77b1-bfb6-15c86483f579'
WEEKLY=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133)
WINDOW_SHA='c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
MAXIMUM=(1793774133,1556235.568922472,1571573.6959699572)
OPERATION='current119-matching-original235-native'
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
 f=read(FIXED);out={'fixed_inputs':FIXED,'native_guard':ref(__file__)};out.update(f)
 manifest=read(f['manifest']);composition=read(f['composition']);review=read(f['composition_review']);artifact=read(f['artifact_review'])
 need(manifest['case_id']=='P-M06-01-process-exec-wait-235B' and manifest['artifacts']['mckernel_image']['sha256']==f['image']['sha256']=='759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31','exact actual119 image and strict235 case')
 need(manifest['payload']['oracle']['exit_code']==0 and manifest['payload']['oracle']['stderr_hex']=='' and len(bytes.fromhex(manifest['payload']['oracle']['stdout_hex']))==235,'unchanged strict235 oracle')
 need(manifest['profile']==dict(memory_mib=8192,name='native-diagnostic-4vcpu-8192mib',numa_nodes=2,vcpus=4) and manifest['cleanup_profile']['id']=='begin-cleanup-real-ack-parent-clone-v2','exact guest and lifecycle profile')
 for i,r in enumerate(manifest['modules']):need(f['module:'+str(i)]['path']==r['path'] and f['module:'+str(i)]['sha256']==r['sha256'],'exact existing native module '+str(i))
 need(len(manifest['modules'])==3 and composition['changed_final_map_records']==['images/mckernel.img'] and composition['manifest']['sha256']==f['manifest']['sha256'],'one image-only composition')
 need(review['independent'] is True and review['implementation_ownership'] is False and review['decision']=='PASS_EXACT_CURRENT119_IMAGE_ONLY_MATCHING235_OFFLINE_COMPOSITION' and review['manifest']['sha256']==f['manifest']['sha256'] and review['image']['sha256']==f['image']['sha256'] and review['guest_execution_authorized'] is False,'actual independent 60-record image-only review')
 need(artifact['independent'] is True and artifact['artifact_acceptance'] is True and artifact['native_acceptance'] is False,'artifact-only CURRENT119 acceptance')
 return out

def validate_operation(op,review,subjects,context,clocks,ceilings):
 clocks=triplet(clocks);limits=triplet(op['operation_cutoffs']);caps=triplet(ceilings)
 need(op['schema']=='mckernel.explicit-new-window-operation-successor.v1' and op['author']=='/root' and op['decision']=='EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and op['operation']==OPERATION,'distinct exact native operation')
 need(op['window_sha256']==op['first_prepared_window_sha256']==WINDOW_SHA and op['weekly_limit_identity']==WEEKLY and op['billing_mode']=='included_only' and op['allow_prepaid_fallback'] is False and op['predecessor_cutoffs'] is None,'exact current weekly only; no inherited grant')
 need(not any(k in op for k in ('credit_run_id','credit_ceiling','minimum_cumulative_spent','api_key')),'no historical credit or API billing')
 need(all(0<limit<=maximum and 0<cap<=maximum and now<min(limit,cap) for now,limit,cap,maximum in zip(clocks,limits,caps,MAXIMUM)),'all clocks strictly before authorized/effective minimum')
 need(op['subjects']==subjects and op['context']==context and op['guardian']==dict(source=subjects['guardian'],entrypoint='guard') and '/root'in op['source_owners'],'exact native subject/context and Q guardian')
 need(review['schema']=='mckernel.independent-operation-window-review.v1' and review['decision']=='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR' and review['independent'] is True and review['implementation_ownership'] is False and isinstance(review['reviewer'],str) and review['reviewer'].startswith('/root/') and review['reviewer']not in op['source_owners'] and review['operation']==OPERATION and review['successor']==op,'independent exact native operation review')
 return limits

def binding_metadata(binding):
 need(set(binding)=={'author','decision','runtime_authority','source','successor','independent_review'} and binding['author']=='/root' and binding['decision']=='BIND_REVIEWED_CURRENT119_NATIVE_GUARD' and binding['runtime_authority'] is None and binding['source']==ref(__file__),'Root exact source binding, no native grant')
 op=read(binding['successor']);review=read(binding['independent_review']);c=op['context'];return op,review,c,context_subjects(c)

def context_subjects(c):
 expected={'post119_current_free','current_ledger','current_boundary','nonce','source_authority','case_capability','staged_manifest','armed_controls','bootstrap_caps','native_source_closure'}
 need(set(c)==expected and c['armed_controls']==ARM and type(c['nonce'])is str and re.fullmatch('[0-9a-f]{32}',c['nonce']) and c['nonce']!='dc62394cd7ae43bf8bd1559fd7f5ad20','fresh nonce and exact native Root context')
 for k in ('post119_current_free','current_ledger','current_boundary','source_authority','case_capability','staged_manifest','armed_controls','bootstrap_caps'):auth(c[k])
 need(type(c['native_source_closure'])is dict and {'root_once_startup_entry.py','bind_startup_resource.py','capture_fresh_startup_resource.py','prepare_startup_bindings.py','run_native_startup_capture.py','run_startup_resource_once.py'}<=set(c['native_source_closure']),'exact separately reviewed native source closure')
 for r in c['native_source_closure'].values():auth(r)
 fixed=fixed_subjects();need(c['staged_manifest']['sha256']==fixed['manifest']['sha256'] and c['staged_manifest']['bytes']==fixed['manifest']['bytes'],'staged manifest exactly actual composed bytes')
 free=read(c['post119_current_free']);ledger=read(c['current_ledger']);boundary=read(c['current_boundary'])
 need(free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and str(free['decision']).startswith('PASS') and free['old_readonly_client_status']=='UNKNOWN','independently accepted post119 current-free and UNKNOWN')
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and ledger['current_physical_clearance_pending'] is False and ledger['latest_accepted_free_boundary']==c['post119_current_free'] and len(ledger['consumed_nonces'])==len(set(ledger['consumed_nonces']))==73 and 'dc62394cd7ae43bf8bd1559fd7f5ad20' in ledger['consumed_nonces'],'actual complete post119 nonce and free ledger')
 build=ledger['current119_build'];need(build['nonce']=='dc62394cd7ae43bf8bd1559fd7f5ad20' and build['container']=='593abb2a8d66817d66c6a530341db17fa7873a42f390d3693792556f4b15cd24' and build['normal_retirement_pending'] is False and build['current_physical_clearance_pending'] is False and build['current_free']==c['post119_current_free'] and any(r.get('sha256')==fixed['image']['sha256'] and r.get('bytes')==fixed['image']['bytes'] for r in build['actual_outputs']),'actual exact current119 image retired and free')
 need(c['nonce'] not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'no old consumed or abandoned nonce')
 need(boundary['author']=='/root' and boundary['nonce_ledger']==c['current_ledger'] and boundary['native_custody_clearance']==c['post119_current_free'] and boundary['root_attests_exact_current_boundary'] is True,'Root exact post119 current descriptor')
 subjects=dict(fixed);subjects.update({'root:'+k:c[k]for k in ('post119_current_free','current_ledger','current_boundary','source_authority','case_capability','staged_manifest','armed_controls','bootstrap_caps')});subjects.update({'native_source:'+k:v for k,v in c['native_source_closure'].items()})
 return subjects

def confirmed_weekly_ceiling(state,guardian):
 row=guardian.validate_confirmed_row(state.get('weekly_confirmed_usage'));need(state.get('thread_id')==THREAD and state.get('weekly_usage')==row and not state.get('weekly_confirmation_pending') and not state.get('weekly_usage_error'),'confirmed same-period usage, no pending confirmation')
 return tuple(min(a,b)for a,b in zip(MAXIMUM,triplet([state.get('weekly_effective_end'),state.get('weekly_effective_monotonic_end'),state.get('weekly_effective_boot_end')])))

def _evaluate():
 b=read(ref(BINDING));op,review,c,subjects=binding_metadata(b);state=decode(STATE.read_bytes());guardian=load(subjects['guardian'],'exact_native_weekly_guardian');ceilings=confirmed_weekly_ceiling(state,guardian)
 clocks=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME));limits=validate_operation(op,review,subjects,c,clocks,ceilings)
 for subject in subjects.values():auth(subject)
 # Reuse existing weekly cap binder only; no readonly operation or build alias.
 accepted_ref=read(FIXED).get('accepted_helper');need(accepted_ref is not None,'exact weekly cap binder required')
 binder=load(accepted_ref,'pure_native_weekly_cap_binder');need(tuple(binder.weekly_limits(read(c['armed_controls']),read(c['bootstrap_caps'])))==limits,'same original armed/bootstrap minimum')
 observed=triplet(guardian.guard());after=confirmed_weekly_ceiling(decode(STATE.read_bytes()),guardian)
 effective=tuple(min(a,b,c)for a,b,c in zip(limits,ceilings,after))
 need(all(a<=b<limit for a,b,limit in zip(clocks,observed,effective)),'actual Q guard remains inside all observed minima')
 return observed,effective
def guard():return list(_evaluate()[0])
def current_cutoffs():return tuple(_evaluate()[1])
