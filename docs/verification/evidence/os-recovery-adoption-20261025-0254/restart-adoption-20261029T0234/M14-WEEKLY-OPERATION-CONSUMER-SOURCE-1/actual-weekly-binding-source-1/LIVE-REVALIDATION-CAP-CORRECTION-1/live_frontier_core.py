"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed accepted post-BFD boundary adapter and finite runtime DATA publication rows.
Import and validators do not observe, guard, capture, export or execute commands.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math

BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LIMITS=[1793774133, 1556237.568944064, 1571575.6959913536]
STATUS='PASS_Root63_CURRENT118_TYPED_REOBSERVATION_PENDING_ROOT_ACCEPTANCE'
NONCE='faac1b4804174de5800c58d61ba98004'
OLD_FREE_SHA='6c83eee41b7e90d0f055034b9bbd30cfc9e32efac9e8285a90fc8948f7b82e7d'
FRONTIER_INPUTS_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/FRONTIER-INPUTS.SOURCE-ONLY.json', 'bytes': 5918, 'sha256': 'a46f6b41ea220d1297e92f1747b33311f4a11a61355714d94c6a971f1936910c'}
_frontier_raw=Path(FRONTIER_INPUTS_REF['path']).read_bytes()
assert len(_frontier_raw)==FRONTIER_INPUTS_REF['bytes'] and hashlib.sha256(_frontier_raw).hexdigest()==FRONTIER_INPUTS_REF['sha256']
FRONTIER_INPUTS=json.loads(_frontier_raw)


def validate_closed_unlaunched_frontier(frontier_ref,current):
    """Exact A2 custody history and Root's complete post-base declaration, not clearance."""
    pins=FRONTIER_INPUTS;frontier=checked(frontier_ref);packet=checked(pins['evidence_packet'])
    need(set(frontier)=={'schema','author','decision','base_ledger','base_free','base_current_bindings','evidence_packet','abandoned_nonces','actors','all_post_base_custody_and_reservations_listed','root_attests_no_unlisted_post_base_operation','recorded_epoch','runtime_authority'},'exact closed-unlaunched frontier schema')
    need(frontier['schema']=='mckernel.current118.closed-unlaunched-frontier.v1' and frontier['author']=='/root' and frontier['decision']=='BIND_COMPLETE_POST_ROOT63_CLOSED_UNLAUNCHED_FRONTIER' and frontier['runtime_authority']is None,'Root-only truthful closed-unlaunched declaration')
    for key,wanted in [('base_ledger',pins['base_ledger']),('base_free',pins['base_free']),('base_current_bindings',pins['base_current_bindings']),('evidence_packet',pins['evidence_packet'])]:
        need(frontier[key]==wanted,'exact frontier '+key);auth(wanted)
    need(current['ledger']==pins['base_ledger'] and current['latest_free']==pins['base_free'],'Root63 remains exact accepted historical base')
    need(frontier['all_post_base_custody_and_reservations_listed']is True and frontier['root_attests_no_unlisted_post_base_operation']is True,'complete declared post-base custody/reservation frontier')
    need(frontier['abandoned_nonces']==[pins['abandoned_nonce']] and packet['old_nonce']==pins['abandoned_nonce'] and packet['old_admission']==pins['admission'],'exact abandoned-unlaunched nonce, never a consumed producer')
    refs=packet['evidence'];need(refs==pins['evidence'],'all original A2 evidence retained')
    for row in refs.values():auth(row)
    holder=checked(refs['holder_retirement']);withdrawal=checked(refs['operation_withdrawal']);ready=checked(refs['old_holder_ready'])
    need(holder['author']=='/root' and holder['holder']==dict(pid=2198978,birth=102765089) and holder['positive_tool_join_returncode']==1 and holder['normal_guard_failure_unwind']is True and holder['original_holder_absent']is True and holder['permanent_mutex_rows_now']==[],'genuine normal holder retirement history')
    need(holder['nonce']==pins['abandoned_nonce'] and holder['nonce_disposition']=='ABANDONED_UNLAUNCHED_NEVER_REPLAY_SOURCE_OR_WORKLOAD_NAMESPACE' and not holder['READY_present'] and not holder['runner_started'] and not holder['container_claim_present'] and holder['compiler_calls']==holder['container_launches']==holder['native_calls']==holder['signals_sent']==0 and holder['global_controls_or_window_or_credit_changed']is False and holder['new_admission_clearance']is False,'actual unlaunched outcome is not a new clearance')
    need(withdrawal['holder_pid']==2198978 and withdrawal['holder_birth']==102765089 and withdrawal['no_runner_or_READY_or_container_claim']is True and withdrawal['signals_sent']==withdrawal['source_code_changes']==withdrawal['global_control_changes']==0,'own operation withdrawal only')
    need(ready['holder']==dict(path='/run/lock/mckernel-development.lock',pid=2198978,starttime=102765089,device=27,inode=4,fd=3) and ready['nonce']==pins['abandoned_nonce'],'actual HOLDER.READY custody existed; build READY did not')
    finite=checked(refs['finite_parent_join']);completion=checked(refs['finite_completion']);wrapper=checked(refs['held_wrapper_parent_join']);held=checked(refs['held_child_started']);physical=checked(refs['physical_complete']);physical_start=checked(refs['physical_child_started']);age=checked(refs['held_age_failure'])
    need(finite['pid']==2198306 and finite['starttime']==102756246 and finite['returncode']==1 and finite['positive_direct_wait_join']is True and finite['streams_closed']is True and finite['process_group_absent']is True and not finite['remaining_group_members'] and not finite['group_observation_errors'],'original finite waiter positive failure join/group closure')
    need(completion['positive_join']==refs['finite_parent_join'] and completion['nonce']==pins['abandoned_nonce'] and completion['finite_runs']==1 and completion['automatic_retries']==0 and not completion['independent_Hot_PASS'],'original600s finite failure preserved')
    physical_wrapper=checked(pins['physical_wrapper_join'])
    need(physical_wrapper['pid']==2198339 and physical_wrapper['birth']==102760316 and physical_wrapper['returncode']==0 and physical_wrapper['positive_direct_parent_wait']is True and physical_wrapper['streams_closed']is True,'actual physical outer wrapper positive join; inherited group not claimed absent')
    need(wrapper['pid']==2199448 and wrapper['birth']==102772975 and wrapper['returncode']==1 and wrapper['positive_direct_parent_wait']is True and wrapper['streams_closed']is True,'held wrapper positive failure join; shared group not claimed absent')
    need(held['pid']==2199449 and held['starttime']==102772979 and physical_start['pid']==physical['pid']==2198340 and physical_start['starttime']==102760320 and physical['returncode']==0 and physical['direct_child_joined']is True and physical['group_absent']is True and physical['closed_streams']is True,'original held/physical children and dedicated physical group')
    need(age['physical_to_Root_input_seconds']==113.98561024665833 and age['nonce']==pins['abandoned_nonce'] and not age['independent_Hot_PASS'] and age['automatic_retry']is False,'original120s failure unchanged')
    actors=[dict(pid=2198978,birth=102765089,role='A2_unlaunched_holder',group=None,fd=3),dict(pid=2198306,birth=102756246,role='A2_finite_waiter',group=2198306,fd=None),dict(pid=2199449,birth=102772979,role='A2_held_capture_child',group=2199449,fd=None),dict(pid=2199448,birth=102772975,role='A2_held_wrapper',group=None,fd=None),dict(pid=2198340,birth=102760320,role='A2_physical_capture_child',group=2198340,fd=None),dict(pid=2198339,birth=102760316,role='A2_physical_wrapper',group=None,fd=None)]
    need(frontier['actors']==actors,'all six exact A2 actor pairs; inherited holder/wrapper groups remain unclaimed')
    need(type(frontier['recorded_epoch'])in (int,float) and math.isfinite(frontier['recorded_epoch']) and holder['epoch']<=frontier['recorded_epoch']<LIMITS[0],'forward finite Root frontier epoch within immutable window')
    need(checked(pins['base_ledger'])['consumed_nonces']==checked(current['ledger'])['consumed_nonces'] and len(checked(current['ledger'])['consumed_nonces'])==71,'same71 consumed/native history')
    return frontier


def validate_fresh_closed_unlaunched(value,frontier,module):
    """Reuse complete authenticated raw censuses, then require A2 PID/group/FD/lock absence."""
    receipts=module.validate_capture_commands(value)
    need(value['boot_id']==BOOT and len(value['fixed_cutoffs'])==3 and all(0<limit<=maximum for limit,maximum in zip(value['fixed_cutoffs'],LIMITS)) and value['observed_clocks'][0]>=frontier['recorded_epoch'],'new complete observation after declared frontier; old free/capture not replayed')
    need(all(frontier['recorded_epoch']<=value['observed_clocks'][0]<=row['started_epoch']<=row['finished_epoch']<=value['last_observed_clocks'][0] for row in receipts),'all five authenticated client receipts are post-frontier')
    actors=frontier['actors'];groups={row['group']for row in actors if row['group']is not None}
    for report in value['complete_process_reports']:
        need(len(report['snapshots'])==len(report['groups'])==2,'two complete proc/group snapshots per raw census')
        for snapshot,group_snapshot in zip(report['snapshots'],report['groups']):
            need(not any(row[0]in {a['pid']for a in actors} for row in snapshot),'all A2 recorded PIDs absent in every raw census')
            need(not any(row[0]in {a['pid']for a in actors} or row[3]in groups for row in group_snapshot),'all A2 PIDs/known dedicated groups absent in every raw census')
    for actor in actors:need(not Path('/proc',str(actor['pid'])).exists(),'A2 recorded PID remains absent after fresh full census')
    need(not Path('/proc/2198978/fd/3').exists(),'old A2 holder own FD3 absent')
    locks=Path('/proc/locks').read_text().splitlines()
    need(not any(len(parts)>=8 and parts[5]=='00:1b:4'for parts in (line.split()for line in locks)),'fresh permanent27:4 has no owner before new holder')
    return dict(actors=actors,raw_censuses=2,proc_snapshots=4,all_PIDs_and_known_groups_absent=True,old_holder_FD3_absent=True,permanent27_4_rows_absent=True,inherited_holder_wrapper_groups_absence_not_claimed=True)


def need(ok,why):
    if not ok:raise ValueError(why)


def ref(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def auth(row):
    need(type(row)is dict and set(row)=={'path','bytes','sha256'} and Path(row['path']).is_absolute() and ref(row['path'])==row,'exact typed boundary BYTE reference')
    return Path(row['path'])


def checked(row):return json.loads(auth(row).read_bytes())


def load(row,name):
    spec=importlib.util.spec_from_file_location(name,auth(row))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def upstream(selection_ref):
    selection=checked(selection_ref);subjects=checked(selection['subject_map'])
    need(selection['observer']==subjects['observer'] and selection['inputs']==subjects['inputs'],'latest exact source/input subject map, no irrevocable old observer fallback')
    auth(selection['inputs'])
    module=load(selection['observer'],'current118_typed_post_BFD_upstream')
    need(module.NONCE==NONCE and list(module.PINS['limits'])==LIMITS,'same consumed BFD nonce and actual tight clamps')
    return module,selection,subjects


def validate_typed(binding_ref,selection_ref,consumer_ref,core_ref):
    binding=checked(binding_ref)
    need(binding['schema']=='mckernel.current118.accepted-post-BFD-boundary.v1' and binding['author']=='/root' and
         binding['decision']=='BIND_CURRENT118_TO_ACCEPTED_POST_BFD_ROOT63' and binding['runtime_authority']is None and
         binding['phase']=='accepted_current' and binding['upstream_selection']==selection_ref,'exact Root-authored accepted post-BFD binding; pending is not current')
    module,selection,subjects=upstream(selection_ref)
    need(binding['accepted_current_bindings']==FRONTIER_INPUTS['base_current_bindings'],'exact immutable accepted Root63 base binding')
    current=checked(binding['accepted_current_bindings'])
    need(current['phase']=='accepted_current','postjoin candidate cannot become current by DATA substitution')
    need(current['latest_free']['sha256']!=OLD_FREE_SHA and current['ledger']!=module.PINS['prior_ledger'],'old Root61/free6c83 is historical only')
    retained=module.validate_retained()
    need(len(retained['prior']['consumed_nonces'])==70 and len(retained['actors'])==72,'all72 historical/BFD/failed-custody rows retained')
    capture=module.validate_current_adoption(current,retained)
    executor=module.load(module.PINS['retirement_executor'],'current118_reused_normal_retirement_validator')
    cleanup,value,receipts,actors=module.validate_retirement(executor,current['retirement_result'],current['retirement_parent_join'])
    ledger=checked(current['ledger']);free=checked(current['latest_free']);pending=checked(current['pending_ledger'])
    need(ledger['consumed_nonces']==pending['consumed_nonces'] and len(ledger['consumed_nonces'])==71 and ledger['consumed_nonces'].count(NONCE)==1,'consumed faac retained exactly once')
    need(ledger['current_native_operation']==retained['prior']['current_native_operation'],'ordinary BFD never reclassifies the genuine native branch')
    need(ledger['current_physical_clearance_pending']is False and ledger['latest_accepted_free_boundary']==current['latest_free'],'actual newly accepted post-BFD free')
    need(ledger['bfd_default_build']['failed_retirement_attempts']==[module.PINS['failed_retirement_attempt'],module.PINS['failed_retirement_attempt_2']],'both actual failed custody attempts preserved in order')
    need(capture['BFD_retirement_result']==current['retirement_result'] and capture['BFD_retirement_parent_join']==current['retirement_parent_join'],'accepted capture binds successful cleanup and separate parent join')
    need(capture['all_recorded_actors_absent']==retained['actors']+actors,'accepted capture preserves exact recorded actor multiset including both failures')
    boundary=checked(binding['current_boundary'])
    need(boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary']is True and
         boundary['nonce_ledger']==current['ledger'] and boundary['native_custody_clearance']==current['latest_free'] and boundary['observer']==consumer_ref,'new118 descriptor couples exact current ledger/free/consumer')
    schema=checked(boundary['observer_schema']);schema_review=checked(boundary['observer_schema_review'])
    need(schema==dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=consumer_ref,ledger_key='Root63',expected_status=STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance'),'exact Root63/current118 consumer schema')
    need(schema_review['independent']is True and schema_review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and schema_review['reviewed_observer_schema']==boundary['observer_schema'],'new schema independent review')
    auth(boundary['independent_current_boundary_review'])
    review=checked(binding['independent_review'])
    need(review['independent']is True and review['implementation_ownership']is False and review['decision']=='PASS_EXACT_CURRENT118_TYPED_POST_BFD_BOUNDARY','independent typed boundary source/data review')
    auth(binding['readonly_release'])
    for key,wanted in [('consumer',consumer_ref),('core',core_ref),('upstream_selection',selection_ref),('accepted_current_bindings',binding['accepted_current_bindings']),('current_boundary',binding['current_boundary']),('readonly_release',binding['readonly_release'])]:
        need(review[key]==wanted,'exact reviewed typed118 '+key)
    frontier=validate_closed_unlaunched_frontier(binding['closed_unlaunched_frontier'],current)
    need(review['closed_unlaunched_frontier']==binding['closed_unlaunched_frontier'],'independent exact supplemented custody frontier review')
    need(checked(binding['readonly_release'])['closed_unlaunched_frontier']==binding['closed_unlaunched_frontier'],'same exact frontier in fresh readonly delegation')
    return dict(binding=binding,current=current,module=module,ledger=ledger,free=free,capture=capture,
                retained=retained,retirement=value,cleanup_actors=actors,subjects=subjects,frontier=frontier)


def validate_root_context(root,selection_ref,consumer_ref,core_ref):
    context=validate_typed(root['typed_current_boundary_binding'],selection_ref,consumer_ref,core_ref)
    need(root['nonce_ledger']==context['current']['ledger'] and root['native_custody_clearance']==context['current']['latest_free'] and root['current_boundary']==context['binding']['current_boundary'],'materializer exactly consumes accepted typed118 boundary')
    need(root['nonce']not in context['ledger']['consumed_nonces'],'next build nonce is unused; no faac replay')
    need(root['nonce']not in context['frontier']['abandoned_nonces'],'abandoned unlaunched A2 nonce never replayed')
    need(root['closed_unlaunched_frontier']==context['binding']['closed_unlaunched_frontier'],'materializer consumes truthful supplemented frontier')
    need(root['next_attempt_reservation']==FRONTIER_INPUTS['reservation'],'exact new Root A3 reservation')
    reservation=checked(root['next_attempt_reservation'])
    need(reservation['author']=='/root' and reservation['decision']=='RESERVE_NEW_UNUSED_CURRENT118_ATTEMPT_NONCE_WITHOUT_EXECUTION_AUTHORITY' and reservation['status']=='RESERVED_UNUSED_A3_NOT_MATERIALIZED_OR_GRANTED' and reservation['nonce']==root['nonce'] and reservation['admission']==root['admission'] and reservation['base_nonce_ledger']==FRONTIER_INPUTS['base_ledger'] and reservation['prior_abandoned_nonce']==FRONTIER_INPUTS['abandoned_nonce'] and reservation['runtime_authority']is None,'same new unused Root reservation, not execution authority')
    return context


def observe(binding_ref,selection_ref,consumer_ref,core_ref):
    """No-argument caller adapter; actual execution remains separately Root released."""
    context=validate_typed(binding_ref,selection_ref,consumer_ref,core_ref)
    binding=context['binding'];module=context['module'];release=checked(binding['readonly_release'])
    need(release['author']=='/root' and release['decision']=='AUTHORIZE_ONE_CURRENT118_TYPED_CURRENT63_REOBSERVATION' and release['maximum_invocations']==1 and release['consumer']==consumer_ref and release['core']==core_ref and release['accepted_current_bindings']==binding['accepted_current_bindings'],'exact Root readonly delegation, never source authority')
    out=Path(release['output_directory'])
    need(out.is_absolute() and out.is_dir() and not list(out.iterdir()),'Root-created fresh exact current reobservation directory')
    need(release['capture_scope']==module.capture_scope(),'release covers unchanged complete recursive and tracked query/census scope')
    value=module.observe(context['current'],out)
    need(value['status']==module.CURRENT_STATUS and value['Root63']==context['current']['ledger'] and value['actual_latest_operation_postjoin_acceptance']==context['current']['latest_free'],'fresh upstream current63 result; no candidate substitution')
    frontier_check=validate_fresh_closed_unlaunched(value,context['frontier'],module)
    value.update(status=STATUS,current_boundary=binding['current_boundary'],typed_current118_binding=binding_ref,closed_unlaunched_frontier=binding['closed_unlaunched_frontier'],closed_unlaunched_fresh_checks=frontier_check)
    return value


def byte_refs(value):
    if isinstance(value,dict):
        if set(value)=={'path','bytes','sha256'}:
            yield value
        else:
            for child in value.values():yield from byte_refs(child)
    elif isinstance(value,list):
        for child in value:yield from byte_refs(child)


def runtime_data_rows(binding_ref,selection_ref,operation_ref):
    """Exact typed closure; explicitly seed implicit sibling DATA, then follow BYTE edges.
    JSON documents are authenticated and traversed. Non-JSON leaves retain their
    exact declared BYTE refs for normal publication verification, without replaying
    artifact/large-archive hashing here. No directory inventory is performed.
    """
    binding=checked(binding_ref);selection=checked(selection_ref);current=checked(binding['accepted_current_bindings'])
    subjects=checked(selection['subject_map']);base=Path(selection['observer']['path']).parent
    roots=dict(typed118=binding_ref,selection=selection_ref,upstream_accepted_current=binding['accepted_current_bindings'],
               operation118=operation_ref,upstream_inputs=selection['inputs'],upstream_subjects=selection['subject_map'],frontier_inputs=ref(Path(__file__).resolve().parent/'FRONTIER-INPUTS.SOURCE-ONLY.json'))
    # These are real sibling reads in unchanged upstream/current61/current60/common
    # sources. They are not reachable from a source BYTE row by parsing JSON alone.
    for name in ['history/ROOT61-RUNTIME-DEPENDENCIES.json','history/ACTUAL-PINS.json','history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json']:
        roots['implicit:'+name]=ref(base/name)
    pending=[(role,row)for role,row in roots.items()];rows={};provenance={}
    while pending:
        role,row=pending.pop();path=row['path']
        need(set(row)=={'path','bytes','sha256'},'complete BYTE closure row')
        if path in rows:
            need(rows[path]==row,'conflicting runtime DATA reference for '+path);provenance[path].append(role);continue
        rows[path]=row;provenance[path]=[role]
        if path.endswith('.json'):
            document=checked(row)
            for child in byte_refs(document):pending.append(('declared_by:'+path,child))
    result=[]
    for path in sorted(rows):
        try:fetched=str(Path(path).relative_to('/home/holden/mckernel'))
        except ValueError:fetched=None
        result.append(dict(actual=rows[path],fetched_equivalent_path=fetched,
                           requires_explicit_fetched_alias=fetched is None,
                           declared_by=provenance[path],kind='JSON'if path.endswith('.json')else'BYTE'))
    return result


def source_rows_for_capture(profile,runner,overlay_ref):
    """Retain exact118123-path/hash membership; derive count from authenticated overlay."""
    overlay=checked(overlay_ref);expected={row['relative']:row['source']['sha256']for row in overlay['files']}
    need(len(expected)==len(overlay['files'])==123 and sum(x.endswith('.rs')for x in expected)==112,'unchanged exact118 source overlay123/112')
    directories=profile['inputs']['source_directory_exports'];need(len(directories)==1,'one exact readonly123 subtree')
    manifest=checked(directories[0]['manifest'])
    actual={row['relative']:row['snapshot']['sha256']for row in manifest['files']}
    need(len(actual)==len(manifest['files'])==len(expected) and actual==expected,'all exact123 paths/hashes, no duplicate, missing or extra export')
    rows=runner.source_directory_postimages(profile)
    need(len(rows)==len(expected) and {r['relative'].removeprefix('kernel/rust/'):r['postimage']['sha256']for r in rows}==expected,'runner exact manifest-derived source rows')
    external=profile['inputs']['external_relative_modules']
    need(len(external)==3 and manifest['external_inputs']==external,'same exact external3 module membership')
    return [r['source']for r in profile['inputs']['configuration']]+[r['source']for r in profile['inputs']['objects']if not r['replace']]+[r['postimage']for r in profile['inputs']['postimages']]+[r['postimage']for r in rows]+[r['source']for r in external]
