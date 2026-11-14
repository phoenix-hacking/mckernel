#!/usr/bin/env python3
"""Prepare conditional draft release artifacts after final retention is copied.

Native container: python3 -B /work/prepare-ultra-drafting-release.py FRESH_N
No build, guest, test, Git, publication or fixture drafting is performed.
Root copies the publication_map outputs, commits/pushes and runs the retained
exact-fetched-blob verifier before announcing the user's manual model switch.
"""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import shutil
import sys

assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
assert len(sys.argv) == 2 and re.fullmatch(r'[1-9][0-9]*', sys.argv[1])
repo, work = Path('/workspace'), Path('/work')
attempt = sys.argv[1]
out = work / ('ultra-drafting-release-20260909-' + attempt)
out.mkdir()
run_id = 'ultra-handoff-' + attempt
draft_root = work / 'application-test-drafts-20260909' / run_id
metadata = work / 'ultra-test-plan-protocol-20260909-2'
checkpoint_path = 'docs/verification/ultra-final-checkpoint-20260909.json'
queue_path = 'scripts/application-tests/draft-queue.json'
catalog_path = 'scripts/application-tests/cases.json'
verifier_path = 'docs/verification/evidence/verify-ultra-final-github-20260909.py'
generator_path = 'docs/verification/evidence/prepare-ultra-drafting-release-20260909.py'
input_path = 'docs/verification/ultra-draft-inputs-20260909.json'
capability_path = 'docs/verification/ultra-draft-capabilities-20260909.json'
release_path = 'docs/verification/ultra-drafting-handoff-20260909.json'
record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
    scope='Prepare drafting artifacts only; final GitHub verification and user model choice/switch remain required',
    publication_map=[], checked_inputs=[], gates=[], drafting_started=False,
    runtime_execution_authorized=False, application_tests_executed=0)


def identity(path, final_path=None):
    digest = hashlib.sha256()
    size = 0
    assert path.is_file() and not path.is_symlink(), str(path)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            size += len(chunk)
            digest.update(chunk)
    return dict(path=final_path if final_path is not None else str(path),
                size=size, sha256=digest.hexdigest())


def verify(row, path=None):
    actual = identity(path if path is not None else Path(row['path']))
    assert (actual['size'], actual['sha256']) == (row['size'], row['sha256']), (row, actual)
    return actual


def repository_input(relative):
    row = identity(repo / relative, relative)
    record['checked_inputs'].append(row)
    return row


def write_artifact(name, final_path, value):
    destination = out / name
    with destination.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    row = identity(destination, final_path)
    record['publication_map'].append(dict(source=str(destination), **row))
    return row


def gate(name, **facts):
    record['gates'].append(dict(name=name, status='PASS', **facts))


try:
    generator = out / 'prepare-ultra-drafting-release-20260909.py'
    shutil.copyfile(__file__, generator)
    generator_ref = identity(generator, generator_path)
    record['publication_map'].append(dict(source=str(generator), **generator_ref))
    checkpoint_ref = repository_input(checkpoint_path)
    checkpoint = json.loads((repo / checkpoint_path).read_text())
    assert checkpoint['status'] == 'PASS' and checkpoint['runtime_execution_authorized'] is False
    assert checkpoint['application_catalog_runtime_verified'] is False
    assert checkpoint['actual_vector_runtime_verified'] is False
    assert checkpoint['transport_runtime_injection_verified'] is False
    assert len(checkpoint['native_compiler_bindings']) == 57
    assert len({row['path'] for row in checkpoint['guest_production_bindings']}) == 44
    for row in checkpoint['native_compiler_bindings'] + checkpoint['guest_production_bindings']:
        verify(row, repo / row['path'])
    selected = checkpoint['selected_pair']
    assert selected['host_compiler_bindings'] == 57 and selected['guest_production_inputs'] == 44
    assert set(selected['image_profiles']) == {'fallback', 'legacy-rust', 'native-rust', 'native-sysfs-verify'}
    assert selected['actual_fault_injection_claimed'] is False
    for key in ('module_record', 'image_record', 'linux_kernel', 'mckernel_image', 'launcher', 'core'):
        verify(selected[key])
    assert len(selected['modules']) == 3
    for row in selected['modules']:
        verify(row)
    gate('retained-source-and-selected-pair', host_compiler_bindings=57,
         guest_production_bindings=44, image_profiles=4, native_modules=3,
         evidence=checkpoint_ref)

    baselines = checkpoint['baseline_replays']
    assert len(baselines) == 4 and {row['case'] for row in baselines} == {'memory', 'files', 'threads', 'signals'}
    for row in baselines:
        assert row['hello_applications'] == 8 and row['core']['exit_code'] == 37
        assert row['core']['stdout'] == 'NATIVE_CORE PASS ' + row['case'] + '\n'
    controls = checkpoint['control_replays']
    assert len(controls) == 2 and {row['architecture'] for row in controls} == {'x86_64', 'i386'}
    for row in controls:
        assert row['process']['checks'] == 153 and row['process']['physical_queue_cleanup_exchanges'] == 73
        assert row['application_execution'] is False
    assert checkpoint['actual_hello_applications'] == 48 and checkpoint['original_core_replays'] == 6
    assert checkpoint['original_control_replays'] == 2
    gate('unchanged-regression-replay', core_modes=4, total_core_replays=6,
         hello_applications=48, control_architectures=2, checks_per_control=153,
         evidence=checkpoint_ref)

    signal = checkpoint['ordinary_signal_abi']
    assert len(signal['cases']) == 5
    assert all(row['exit_code'] == 37 and row['raw_wait_status'] == 37 << 8 for row in signal['cases'])
    assert signal['external_restart']['status'] == 'BLOCKED' and signal['external_restart']['guest_executed'] is False
    futex = checkpoint['ordinary_futex_abi']['result']
    assert futex['same_guest_linux_reference'] and futex['normal_retirement'] and futex['no_process_nodes']
    assert futex['direct_child_settid_verified'] and futex['fork_cow_verified'] is False
    assert futex['all_host_returns_audited'] is False
    assert len(futex['sides']) == 2 and all(len(side['cases']) == 16 for side in futex['sides'])
    assert all(value == 0 for value in futex['pager_references_remaining'].values())
    assert checkpoint['new_signal_guest_cases'] == 2 and checkpoint['new_futex_logical_cases'] == 16
    assert checkpoint['new_valid_shared_vm_child_tid_case'] == 1
    gate('ordinary-signal-and-futex-guest-evidence', signal_guest_cases=2,
         signal_linux_reference_cases=3, futex_logical_cases=16,
         futex_engines=2, shared_vm_child_tid_cases=1, external_restart='BLOCKED',
         evidence=checkpoint_ref)

    queue_ref, catalog_ref = repository_input(queue_path), repository_input(catalog_path)
    queue = json.loads((repo / queue_path).read_text())
    catalog = json.loads((repo / catalog_path).read_text())
    assert queue['review_state'] == queue['status'] == 'released-for-drafting'
    assert queue['mode'] == 'draft-only' and queue['execution_enabled'] is False
    assert queue['packet_count'] == len(queue['packets']) == 97
    assert queue['logical_case_count'] == catalog['logical_case_count'] == len(catalog['cases']) == 273
    assert sum(row['family'] == 'vector' for row in catalog['cases']) == 56
    metadata_ref = identity(metadata / 'record.json')
    verify(checkpoint['application_plan']['plan_validation_record'], metadata / 'record.json')
    metadata_record = json.loads((metadata / 'record.json').read_text())
    assert metadata_record['status'] == 'PASS' and metadata_record['runtime_authorized'] is False
    assert metadata_record['application_tests_passed'] == 0
    assert metadata_record['logical_cases'] == 273 and metadata_record['queue_packets'] == 97
    negatives = metadata_record['negative_checks']
    assert len(negatives) == len({row['name'] for row in negatives}) == 48
    assert all(row['status'] == 'PASS' for row in negatives)
    required_negatives = {'dependency-cycle', 'unknown-capability', 'false-case-pass', 'resource-expansion',
        'write-path-escape', 'unreviewed-execution', 'shell-command', 'common-mode-osxsave-removal',
        'feature-self-cycle', 'transitive-gate-missing', 'weakened-case-feature-binding',
        'external-identical-packet', 'external-changed-report-packet', 'external-changed-cases-packet',
        'canonical-packet-changed-after-validation', 'packet-identity-mismatch',
        'duplicate-case-assignment', 'within-packet-dependency-order', 'missing-queue-cli'}
    assert required_negatives <= {row['name'] for row in negatives}
    # The protocol ran before retention; reject any changed planning input.
    for path in sorted((repo / 'scripts/application-tests').rglob('*')):
        if path.is_file():
            saved = metadata / 'application-tests' / path.relative_to(repo / 'scripts/application-tests')
            assert path.read_bytes() == saved.read_bytes(), str(path)
    context_refs = {}
    for number in ('001', '007'):
        relative = 'docs/verification/evidence/ultra-packet-' + number + '-context-20260909.json'
        ref = repository_input(relative)
        context = json.loads((repo / relative).read_text())
        assert (repo / relative).read_bytes() == (metadata / ('packet-' + number + '-context.json')).read_bytes()
        assert context['schema_version'] == 1 and context['mode'] == 'draft-only' and context['execution_enabled'] is False
        assert context['catalog_sha256'] == catalog_ref['sha256']
        assert context['queue_cursor']['queue_sha256'] == queue_ref['sha256']
        assert context['queue_cursor']['review_state'] == 'released-for-drafting'
        assert context['queue_cursor']['total'] == 97 and context['queue_cursor']['index'] == int(number)
        packet = repo / ('scripts/application-tests/packets/packet-' + number + '.json')
        assert context['packet_sha256'] == identity(packet)['sha256']
        assert len(context['cases']) == 3
        assert [row['id'] for row in context['cases']] == context['packet']['case_ids']
        context_refs[number] = ref
    gate('validated-bounded-draft-queue', logical_cases=273, packets=97,
         vector_cases=56, negative_rejection_checks=48, bounded_contexts=2,
         active_cases_per_context=3, evidence=metadata_ref, queue=queue_ref)
    verifier_ref = repository_input(verifier_path)
    gate('retained-final-github-verifier-present', evidence=verifier_ref,
         execution_status='NOT_RUN_BY_THIS_GENERATOR')

    common = dict(schema_version=1, mode='draft-only', drafting_only=True,
                  execution_enabled=False, runtime_execution_authorized=False)
    inputs = dict(common, status='PREPARED_FOR_DRAFTING', execution_inputs_complete=False,
        final_checkpoint=checkpoint_ref, selected_pair=copy.deepcopy(selected),
        source_binding_authority='Exact current source/compiler identities and detailed accepted evidence are in final_checkpoint; a prior source_parent commit alone is insufficient.',
        unresolved_runtime_inputs=dict(payloads='Per-case payloads are not drafted or built.',
            oracles='Independent per-case oracle artifacts remain unresolved and unaccepted.',
            runner='The broader repository execution runner and its runtime validation remain incomplete.',
            capability_acceptance='All broader catalog execution remains blocked by global and case-specific gates.'),
        baseline_scope='Only the explicit selected-pair regression and ordinary signal/futex facts in final_checkpoint are accepted.',
        draft_queue=queue_ref, fresh_queue_run_id=run_id, draft_reporting_root=str(draft_root))
    input_ref = write_artifact('draft-inputs.json', input_path, inputs)
    capabilities = dict(common, status='PREPARED_FOR_DRAFTING', input_manifest_sha256=input_ref['sha256'],
        input_manifest=input_ref, final_checkpoint=checkpoint_ref,
        global_execution_gates=catalog['global_execution_gates'],
        capabilities={name: dict(state='blocked', contract=value['acceptance'],
            planning_state=value['state'], blocked_by=catalog['global_execution_gates'],
            evidence_scope='No broad execution capability is accepted by the drafting release.')
            for name, value in sorted(catalog['capabilities'].items())},
        accepted_baseline_facts=dict(final_checkpoint=checkpoint_ref,
            scope='Facts about the exact retained pair; these do not satisfy broader execution release gates.',
            core_modes=['memory', 'files', 'threads', 'signals'], control_architectures=['x86_64', 'i386'],
            hello_applications=48, core_replays=6, ordinary_signal_guest_cases=2,
            ordinary_futex_logical_cases=16, shared_vm_child_tid_cases=1,
            vector_runtime_verified=False, external_signal_restart_verified=False,
            fork_cow_verified=False, transport_runtime_injection_verified=False))
    capability_ref = write_artifact('draft-capabilities.json', capability_path, capabilities)

    # Reserve an empty reporting root only after all evidence/binding checks.
    draft_root.parent.mkdir(exist_ok=True)
    assert not draft_root.parent.is_symlink()
    draft_root.mkdir()
    assert not any(draft_root.iterdir())
    release = dict(common, status='PASS', release='released-for-drafting',
        logical_case_count=273, packet_count=97, vector_case_count=56,
        final_checkpoint=checkpoint_ref, queue=queue_ref, catalog=catalog_ref,
        verification_helper=verifier_ref, preparation_helper=generator_ref,
        starting_context=context_refs['001'], vector_context=context_refs['007'],
        reviewed_input_manifest=input_ref, reviewed_capability_manifest=capability_ref,
        fresh_queue_run_id=run_id, draft_reporting_root=str(draft_root),
        gate_results=copy.deepcopy(record['gates']),
        executor_model='Luna or Spark; user chooses', user_controls_model_switch=True,
        queue_execution='Automatically advance only through the 97 reviewed draft packets after each immutable report; at most three active cases, no repeated permission requests and no runtime or production-source changes.',
        effective_at_generation=False, github_verification_required=True,
        effectiveness_condition='Drafting starts only after the retained verification_helper succeeds on the exact fetched GitHub checkpoint containing these release/input/capability/context/queue bytes, root announces readiness, and the user chooses and manually switches the executor model. Generation, metadata PASS and the released-for-drafting label alone are insufficient.',
        remaining_execution_gates=catalog['global_execution_gates'],
        remaining_capabilities='External signals, fork/COW, extended xstate signal ABI, actual transport faults, accounting and every other blocked capability retain their separate evidence requirements.',
        application_acceptance_claim='273 specifications and 97 drafting packets; no new catalog/vector runtime cases are accepted by this release.')
    release_ref = write_artifact('ultra-drafting-handoff-20260909.json', release_path, release)
    # Reject a concurrent mutation of copied repository evidence before return.
    for row in record['checked_inputs']:
        verify(row, repo / row['path'])
    record.update(status='PASS', release=release_ref, reviewed_input_manifest=input_ref,
                  reviewed_capability_manifest=capability_ref, fresh_queue_run_id=run_id,
                  draft_reporting_root=str(draft_root), effective_at_generation=False,
                  github_verification_required=True)
except BaseException as error:
    record.update(status='FAIL', error=str(error))
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    record['outputs'] = [identity(path) for path in sorted(out.iterdir()) if path.is_file() and path.name != 'record.json']
    with (out / 'record.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(record['status'], str(out), flush=True)
