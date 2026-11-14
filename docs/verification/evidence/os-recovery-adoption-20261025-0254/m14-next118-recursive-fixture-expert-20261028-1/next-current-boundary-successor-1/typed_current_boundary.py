"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed accepted post-BFD boundary adapter and finite runtime DATA publication rows.
Import and validators do not observe, guard, capture, export or execute commands.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LIMITS=[1793253600.0,1035704.5689393478,1051042.6959879305]
STATUS='PASS_Root63_CURRENT118_TYPED_REOBSERVATION_PENDING_ROOT_ACCEPTANCE'
NONCE='faac1b4804174de5800c58d61ba98004'
OLD_FREE_SHA='6c83eee41b7e90d0f055034b9bbd30cfc9e32efac9e8285a90fc8948f7b82e7d'


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
    return dict(binding=binding,current=current,module=module,ledger=ledger,free=free,capture=capture,
                retained=retained,retirement=value,cleanup_actors=actors,subjects=subjects)


def validate_root_context(root,selection_ref,consumer_ref,core_ref):
    context=validate_typed(root['typed_current_boundary_binding'],selection_ref,consumer_ref,core_ref)
    need(root['nonce_ledger']==context['current']['ledger'] and root['native_custody_clearance']==context['current']['latest_free'] and root['current_boundary']==context['binding']['current_boundary'],'materializer exactly consumes accepted typed118 boundary')
    need(root['nonce']not in context['ledger']['consumed_nonces'],'next build nonce is unused; no faac replay')
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
    value.update(status=STATUS,current_boundary=binding['current_boundary'],typed_current118_binding=binding_ref)
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
               operation118=operation_ref,upstream_inputs=selection['inputs'],upstream_subjects=selection['subject_map'])
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
