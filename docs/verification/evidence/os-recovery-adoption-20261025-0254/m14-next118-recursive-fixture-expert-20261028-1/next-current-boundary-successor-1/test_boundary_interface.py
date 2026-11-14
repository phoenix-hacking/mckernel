"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused hypothetical accepted-boundary/export/closure interface checks only.
No observe, guard, query, capture, cleanup, export, compiler or native call.
"""
from pathlib import Path
import copy
import importlib.util
import json
import resource
import sys
import tempfile
import types
import typed_current_boundary as c

D=Path(__file__).resolve().parent
SELECTION=c.ref(D/'UPSTREAM-SELECTION.SOURCE-ONLY.json')


def write(path,value):
    with path.open('x')as out:json.dump(value,out,indent=2);out.write('\n')
    return c.ref(path)


def fixture(root):
    module,selection,subjects=c.upstream(SELECTION)
    # Reuse the updated upstream acceptance/retirement record oracle exactly.
    sys.path.insert(0,str(Path(selection['observer']['path']).parent))
    builder=c.load(selection['fixture_builder'],'TEST_ONLY_latest_typed_acceptance_builder')
    f=builder.future_fixture(root)
    upstream=dict(f['binding'],phase='accepted_current')
    upstream_ref=write(root/'TEST_ONLY-ACCEPTED-CURRENT-BINDINGS.json',upstream)
    consumer=c.ref(D/'prepare_next_boundary.py') # Symbolic reviewed consumer for interface vectors only.
    core=c.ref(D/'typed_current_boundary.py')
    schema=write(root/'TEST_ONLY-118-SCHEMA.json',dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=consumer,ledger_key='Root63',expected_status=c.STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance'))
    sr=write(root/'TEST_ONLY-118-SCHEMA-REVIEW.json',dict(TEST_ONLY=True,independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=schema))
    boundary=write(root/'TEST_ONLY-118-BOUNDARY.json',dict(TEST_ONLY=True,author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',root_attests_exact_current_boundary=True,nonce_ledger=upstream['ledger'],native_custody_clearance=upstream['latest_free'],observer=consumer,independent_current_boundary_review=write(root/'TEST_ONLY-118-BOUNDARY-REVIEW.json',dict(TEST_ONLY=True)),observer_schema=schema,observer_schema_review=sr))
    release=write(root/'TEST_ONLY-READONLY-RELEASE.json',dict(TEST_ONLY=True,not_runtime_authority=True))
    review=write(root/'TEST_ONLY-TYPED-REVIEW.json',dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_EXACT_CURRENT118_TYPED_POST_BFD_BOUNDARY',consumer=consumer,core=core,upstream_selection=SELECTION,accepted_current_bindings=upstream_ref,current_boundary=boundary,readonly_release=release))
    binding=dict(TEST_ONLY=True,schema='mckernel.current118.accepted-post-BFD-boundary.v1',author='/root',decision='BIND_CURRENT118_TO_ACCEPTED_POST_BFD_ROOT63',runtime_authority=None,phase='accepted_current',upstream_selection=SELECTION,accepted_current_bindings=upstream_ref,current_boundary=boundary,independent_review=review,readonly_release=release)
    bindingref=write(root/'TEST_ONLY-TYPED-CURRENT.json',binding)
    return f,upstream,binding,bindingref,consumer,core


def rejects(call):
    try:call()
    except (ValueError,AssertionError):return
    raise AssertionError('negative interface vector was accepted')


def main():
    resource.setrlimit(resource.RLIMIT_AS,(2*2**30,2*2**30))
    root=Path(tempfile.mkdtemp(prefix='TEST_ONLY-boundary-interface-',dir=D))
    f,upstream,binding,bindingref,consumer,core=fixture(root)
    context=c.validate_typed(bindingref,SELECTION,consumer,core)
    assert len(context['retained']['actors'])==72 and len(context['ledger']['consumed_nonces'])==71
    materializer=dict(nonce='1'*32,nonce_ledger=upstream['ledger'],native_custody_clearance=upstream['latest_free'],current_boundary=binding['current_boundary'],typed_current_boundary_binding=bindingref)
    c.validate_root_context(materializer,SELECTION,consumer,core)
    # Negative mutations are immutable new hypothetical files, not authority.
    for index,mutate in enumerate([lambda b:b.update(phase='postjoin_candidate'),lambda b:b.update(accepted_current_bindings=c.ref(root/'TEST_ONLY-ACCEPTED-CURRENT-BINDINGS.json'))]):
        bad=copy.deepcopy(binding)
        if index==1:
            candidate=dict(upstream,phase='postjoin_candidate');bad['accepted_current_bindings']=write(root/'TEST_ONLY-PENDING-BINDING.json',candidate)
        else:mutate(bad)
        badref=write(root/('TEST_ONLY-BAD-BINDING-'+str(index)+'.json'),bad)
        rejects(lambda:c.validate_typed(badref,SELECTION,consumer,core))
    old=copy.deepcopy(upstream);old['latest_free']=c.checked(c.upstream(SELECTION)[0].PINS['prior_ledger'])['latest_accepted_free_boundary']
    oldref=write(root/'TEST_ONLY-OLD-FREE-BINDING.json',old);bad=dict(binding,accepted_current_bindings=oldref)
    rejects(lambda:c.validate_typed(write(root/'TEST_ONLY-OLD-FREE-TYPED.json',bad),SELECTION,consumer,core))
    rejects(lambda:c.validate_root_context(dict(materializer,nonce=c.NONCE),SELECTION,consumer,core))
    # The real upstream adoption layer must reject a missing actual custody failure.
    ledger=c.checked(upstream['ledger']);ledger['bfd_default_build']['failed_retirement_attempts'].pop()
    badup=dict(upstream,ledger=write(root/'TEST_ONLY-MISSING-FAILED-CUSTODY-LEDGER.json',ledger))
    rejects(lambda:c.upstream(SELECTION)[0].validate_current_adoption(badup,context['retained']))
    parent=c.checked(f['retirement_join']);parent['positive_direct_parent_wait']=False
    badup=dict(upstream,retirement_parent_join=write(root/'TEST_ONLY-NO-RETIREMENT-PARENT-JOIN.json',parent))
    rejects(lambda:c.upstream(SELECTION)[0].validate_current_adoption(badup,context['retained']))
    # Exact 123 membership is independently derived from the immutable source map.
    overlay=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json')
    expected=c.checked(c.ref(overlay));files=[dict(relative=r['relative'],snapshot=dict(path='/TEST_ONLY_NOT_EXPORTED/'+r['relative'],bytes=r['source']['bytes'],sha256=r['source']['sha256']))for r in expected['files']]
    external=c.checked(c.ref(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1/cohort-successor-1/recursive-routing-correction-1/prepared118/EXTERNAL-THREE-MODULE-INPUTS.json')))['external_inputs']
    manifest=dict(TEST_ONLY=True,files=files,external_inputs=external)
    profile=dict(inputs=dict(source_directory_exports=[dict(manifest=write(root/'TEST_ONLY-123-MANIFEST.json',manifest))],external_relative_modules=external,configuration=[],objects=[],postimages=[]))
    rows=[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot'])for r in files]
    runner=types.SimpleNamespace(source_directory_postimages=lambda p:rows)
    result=c.source_rows_for_capture(profile,runner,c.ref(overlay));assert len(result)==126
    for index,change in enumerate([lambda m:m['files'].pop(),lambda m:m['files'].extend(m['files'][:1]),lambda m:m['files'][0]['snapshot'].update(sha256='0'*64),lambda m:m['external_inputs'].pop()]):
        bad=copy.deepcopy(manifest);change(bad);badp=copy.deepcopy(profile);badp['inputs']['source_directory_exports'][0]['manifest']=write(root/('TEST_ONLY-INVALID-EXPORT-'+str(index)+'.json'),bad)
        rejects(lambda:c.source_rows_for_capture(badp,runner,c.ref(overlay)))
    # The exact runtime closure includes implicit nested common/current60/physical
    # DATA even when no top-level static assembler had referenced those filenames.
    closure=root/'closure';history=closure/'history';history.mkdir(parents=True)
    guard=write(closure/'guard-config.json',dict(TEST_ONLY=True))
    physical=write(closure/'physical-config.json',dict(guard_config=guard))
    common=write(history/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',dict(physical_history_configuration=physical,account_window_guard_configuration=guard))
    write(history/'ACTUAL-PINS.json',dict(common_dependencies=common))
    write(history/'ROOT61-RUNTIME-DEPENDENCIES.json',dict(guard_configuration=guard))
    source=closure/'source.py';source.write_text('# TEST_ONLY source\n')
    inputs=write(closure/'INPUTS.json',dict(TEST_ONLY=True));subjects=write(closure/'SUBJECTS.json',dict(TEST_ONLY=True))
    selection=write(closure/'selection.json',dict(observer=c.ref(source),inputs=inputs,subject_map=subjects))
    accepted=write(closure/'accepted-current.json',dict(TEST_ONLY=True))
    typed=write(closure/'typed.json',dict(accepted_current_bindings=accepted))
    operation=write(closure/'operation.json',dict(TEST_ONLY=True))
    closure_rows=c.runtime_data_rows(typed,selection,operation);paths={row['actual']['path']for row in closure_rows}
    assert all(str(path)in paths for path in [history/'ROOT61-RUNTIME-DEPENDENCIES.json',history/'ACTUAL-PINS.json',history/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',closure/'guard-config.json',closure/'physical-config.json'])
    (history/'ROOT61-RUNTIME-DEPENDENCIES.json').rename(history/'PRESERVED-FOR-MISSING-INPUT-NEGATIVE.json')
    try:c.runtime_data_rows(typed,selection,operation)
    except FileNotFoundError:pass
    else:raise AssertionError('omitted implicit runtime DATA was accepted')
    summary=dict(scope=__doc__.splitlines()[0],decision='PASS_FOCUSED_TYPED_POST_BFD_BOUNDARY_123_EXPORT_AND_RUNTIME_DATA_CLOSURE_INTERFACE_ONLY',
       genuine_pending_nonce_count=71,genuine_recorded_prior_actor_rows=72,qualified_export_paths=123,external_modules=3,
       negatives=['pending_phase','candidate_bindings','old_Root61_free','consumed_faac_replay','missing_failed_custody','missing_retirement_parent_join','missing_export_path','duplicate_or_extra_export','changed_export_hash','external_module_mismatch','omitted_nested_runtime_DATA'],
       hypothetical_fixture=str(root),full_observer_runs=0,actual_guards=0,actual_queries=0,actual_cleanup=0,actual_captures=0,actual_exports=0,compiler_native_calls=0,runtime_authority=None)
    write(D/'PURE-INTERFACE-RESULT.json',summary);print(json.dumps(summary))


if __name__=='__main__':main()
