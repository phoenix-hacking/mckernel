"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Input binding/table tests only. Never calls an observer, actual guard or command.
"""
from pathlib import Path
import copy
import importlib.util
import json
import resource
import retained_effect_oracle as s

D=Path(__file__).resolve().parent


def main():
    resource.setrlimit(resource.RLIMIT_AS,(2*2**30,2*2**30))
    capture,used=s.authenticate_actual_proof()
    corpus,pointers=s.exact_corpus(capture)
    physical=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-physical-history-successor-source-20261028-1/physical_history_successor.py')
    spec=importlib.util.spec_from_file_location('unchanged_physical_source_chain_input_only',physical)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    oracle=s.RetainedEffectOracle(module.source_chain())
    manifest=oracle.manifest()
    assert len(manifest['rows'])==97
    for key,response in corpus.items():assert oracle.get(list(key))==response
    bad=copy.deepcopy(capture)
    second=bad
    for key in s.PATHS[1]:second=second[key]
    second[0]['stdout']='SYNTHETIC_CONFLICT_ONLY'
    try:s.exact_corpus(bad)
    except ValueError as error:assert 'CONFLICTING_AUTHENTICATED_SUPPLEMENT_DUPLICATE'in str(error)
    else:raise AssertionError('conflicting genuine-key duplicate was accepted')
    unknown=['/usr/bin/sudo','-A','/usr/bin/docker','ps','-aq','--no-trunc','--filter','id='+'f'*64]
    try:oracle.get(unknown)
    except AssertionError as error:assert 'UNSUPPORTED_RETAINED_EFFECT_ARGV'in str(error)
    else:raise AssertionError('unsupported command received a default reply')
    # No newly generated executable spelling or daemon alias is admitted.
    added=manifest['actual_bfd_input_supplement']['new_exact_keys']
    for key in added:
        alias=list(key);alias[0]='sudo'
        try:oracle.get(alias)
        except AssertionError:pass
        else:raise AssertionError('supplement generated an unobserved sudo alias')
    base=s.auth(s.BINDINGS['inputs']['base_oracle'])
    assert s.query is s._base.query and s.RetainedEffectOracle.get is s._base.RetainedEffectOracle.get
    assert s.reference(s.BINDINGS['inputs']['base_oracle']['path'])['sha256']=='9e6ef78fb3b2e56429194c76bf16f92f5871be254573c09fdc539facd50eead8'
    (D/'SUPPLEMENT-CORPUS-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    summary=dict(scope=__doc__.splitlines()[0],decision='PASS_GENUINE_BFD_INPUT_SUPPLEMENT_BINDING_AND_EXACT_TABLE_ONLY',
         base_keys=94,supplement_unique_keys=5,new_exact_keys=added,identical_existing_keys=2,
         duplicated_raw_rows=10,total_keys=97,new_aliases=0,
         tests=['positive_capture_join_and_actual_finite_HOT_lineage','Root61_historical_scope',
                'all_five_exact_actual_raw_replies','conflicting_duplicate_rejects',
                'unsupported_command_refuses','unobserved_executable_alias_refuses','unchanged_base_classifier_and_dispatch'],
         source=s.reference(D/'retained_effect_oracle.py'),inputs=s.reference(D/'INPUT-BINDINGS.json'),
         corpus_manifest=s.reference(D/'SUPPLEMENT-CORPUS-MANIFEST.json'),
         full_fixture_runs=0,observe_calls=0,actual_guard_calls=0,actual_commands=0,runtime_authority=None)
    (D/'PURE-INPUT-SUPPLEMENT-TEST.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
