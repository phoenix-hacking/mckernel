"""Emit a finite publication projection, preserving genuine-late source hashes."""
from pathlib import Path
import argparse
import hashlib
import json

F = Path(__file__).resolve().parent
A = F.parent
OLD = Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/terminal-preparation-1/failure-preparation-1')
PREFIX = 'docs/verification/evidence/new205-failed-terminal-20261019-1/'
NAMES = (
    'failed_operation_authority.py', 'retain_failed_logs.py', 'cleanup_failed.py',
    'observe_failed_retirement.py', 'readback_observer.py', 'read_original_five_metadata.py',
    'export_raw_five.py', 'postjoin_readback.py', 'prepare_failure_case.py',
    'retirement_binding.py.in', 'finalize_failed_terminal.py', 'prepare_failure_authority_data.py',
    'prepare_chain_bindings.py', 'emit_publication_projection.py', 'test_failure_case.py',
    'test_failure_layout_remaining.py', 'test_final_literal_assertion.py', 'fixture-result.json',
    'candidate-source-pins.json', 'candidate-source-pins-correction.json',
    'candidate-source-pins-final-assertion.json', 'failed-log-original-authorities.json',
    'failed-operation-source-references.json', 'actual-failed-physical-bindings.json',
    'FAILED-CASE-INPUTS.json', 'FAILED-BUILD-PRESERVATION-AUTHORITY.json',
    'failure-helper-source-pins.json', 'FAILURE-TERMINAL-CHAIN-DRAFT.json',
    'failed-retention-release-payload-DRAFT.json', 'failed-owner-terminal-inspection.json',
    'retained-production-objects/retained-objects.json', 'retained-production-objects/result.json',
)

def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def main(final):
    rows, pending = [], []
    for name in NAMES:
        path = F / name
        if not path.exists():
            pending.append(dict(source=str(path), relative=PREFIX + name, status='PENDING_GENUINE_RETENTION_AND_GENERATION'))
            continue
        pin = ref(path)
        rows.append(dict(source=pin['path'], relative=PREFIX + name, sha256=pin['sha256'], bytes=pin['bytes']))
    assert not final or not pending, pending
    existing = json.loads((OLD / 'failure-terminal-source-closure.json').read_bytes())
    source11 = json.loads((A / 'heavy-proposal-1/source-sha256.json').read_bytes())
    value = dict(schema='mckernel.new205.failed-terminal-publication-projection.v1', status='FINAL_SOURCE_ROWS_ONLY_NO_EXECUTION_RELEASE' if final else 'DRAFT_PENDING_GENUINE_OUTPUTS', implementation_author='/root/clone_thread_affinity_rust_repair', rows=rows, pending=pending, exact_relative_prefix=PREFIX, source11=source11['source_sha256'], actual_additional_dispatcher=source11['additional_dispatcher'], actual_control_count=12, source11_count=11, unchanged_accepted_import_closure=existing['unchanged_accepted_import_closure'], existing_closure_proof=ref(OLD / 'failure-terminal-source-closure.json'), shared_generic_core=existing['shared_generic_core'], runtime_tests=existing['tests'], independent_source_review_required=True, exact_fetched_blob_verification_required=True, execution_authorized=False, application_acceptance=False)
    target = F / ('publication-allowlist.json' if final else 'publication-projection-DRAFT.json')
    with target.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('PUBLICATION_SOURCE_PROJECTION rows=' + str(len(rows)) + ' pending=' + str(len(pending)) + ' execution=0')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true')
    main(parser.parse_args().final)
