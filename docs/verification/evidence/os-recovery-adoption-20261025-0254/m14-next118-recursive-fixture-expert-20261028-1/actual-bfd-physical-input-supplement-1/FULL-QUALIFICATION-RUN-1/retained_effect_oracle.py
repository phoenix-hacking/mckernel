"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Add genuine BFD preholder query INPUTS to unchanged finite oracle9e6. No effects.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

BINDINGS_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/actual-bfd-physical-input-supplement-1/INPUT-BINDINGS.json', 'bytes': 3322, 'sha256': 'e078739bf3923f3d7e54bab9c68db2570ae7efc2da8a581227cd7329dd08acba'}


def auth(row):
    path=Path(row['path']);raw=path.read_bytes()
    assert set(row)=={'path','bytes','sha256'} and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'exact supplemental input bytes'
    return json.loads(raw) if path.suffix=='.json' else raw


BINDINGS=auth(BINDINGS_REF)
BASE_REF=BINDINGS['inputs']['base_oracle']
auth(BASE_REF)
_spec=importlib.util.spec_from_file_location('unchanged_reviewed_finite_oracle9e6',BASE_REF['path'])
_base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_base)
reference=_base.reference
query=_base.query  # Original classifier remains unchanged, including URI policy.
PATHS=[('physical','historical_Root59_native_and_physical','native_exact_CID_queries'),
       ('physical','historical_current60_reobservation','historical_Root59_native_and_physical','native_exact_CID_queries')]


def authenticate_actual_proof():
    refs=BINDINGS['inputs'];auth(refs['base_test']);capture=auth(refs['capture']);join=auth(refs['capture_join'])
    started=auth(refs['capture_started']);hot=auth(refs['finite_hot']);finite=auth(refs['finite_join'])
    used=dict(refs)
    def checked(row):
        value=auth(row);used[row['path']]=row;return value
    assert capture['status']=='ACTUAL_BFD_ROOT61_PREHOLDER_PHYSICAL_PENDING_INDEPENDENT_REVIEW'
    assert capture['runtime_authority']is None and capture['native_acceptance']is False
    assert join['status']=='ROOT_PHYSICAL_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN'
    assert join['physical']==refs['capture'] and join['returncode']==0
    assert join['direct_child_joined']is True and join['group_absent']is True and join['closed_streams']is True
    assert started['pid']==join['pid']==2123451 and started['starttime']==101426466
    assert started['argv']==join['argv'] and join['argv'][:3]==['/usr/bin/taskset','-c','0']
    for key in ['stdout','stderr']:
        assert len(checked(join[key]))==0
    checked(join['capture_source'])
    assert hot['decision']=='PASS_EXACT_BUILD_ONLY_EXECUTION' and hot['independent']is True
    assert hot['implementation_ownership']is False and hot['maximum_invocations']==1
    assert hot['nonce']==join['nonce']=='faac1b4804174de5800c58d61ba98004'
    assert hot['earliest_clamps']==BINDINGS['cutoffs']
    assert finite['returncode']==0 and finite['positive_direct_wait_join']is True and finite['streams_closed']is True
    assert finite['process_group_absent']is True and not finite['remaining_group_members'] and not finite['group_observation_errors']
    finite_stdout=json.loads(checked(finite['stdout']));assert finite_stdout==dict(decision=hot['decision'],reference=refs['finite_hot'])
    assert len(checked(finite['stderr']))==0
    prewarm=checked(hot['prewarm_ready'])
    assert hot['prewarm_ready']==join['prewarm_ready'] and prewarm['pid']==finite['pid']==2123297
    assert prewarm['starttime']==finite['starttime']==101423116
    assert prewarm['nonce']==hot['nonce'] and prewarm['reviewer']==hot['reviewer']=='/root/observerreview'
    assert prewarm['earliest_clamps']==BINDINGS['cutoffs']
    pending=checked(hot['pending_input']);resource=checked(hot['resource_authority']);held=checked(hot['complete_root_capture'])
    assert pending['nonce']==resource['nonce']==held['nonce']==hot['nonce']
    assert held['status']=='ROOT_HELD_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN'
    assert held['returncode']==0 and held['direct_child_joined']is True and held['group_absent']is True and held['closed_streams']is True
    assert held['physical']==refs['capture'] and held['resource']==hot['resource_authority']
    assert held['pending_input']==hot['pending_input'] and held['prewarm_ready']==hot['prewarm_ready']
    assert pending['resource_authority']==hot['resource_authority']
    assert resource['actual_observations']['physical_ref']==refs['capture']
    assert hot['payload_sha256']==hot['approved_input_sha256']==hot['pending_input']['sha256']
    physical=capture['physical'];ledger=checked(BINDINGS['root61_ledger']);free=checked(BINDINGS['root61_latest_free'])
    assert capture['current_boundary']==physical['Root61']==BINDINGS['root61_ledger']
    assert physical['actual_latest_operation_postjoin_acceptance']==ledger['latest_accepted_free_boundary']==BINDINGS['root61_latest_free']
    assert ledger['author']=='/root' and len(ledger['consumed_nonces'])==70
    assert ledger['complete_within_declared_current_boundary']is True and ledger['current_physical_clearance_pending']is False
    assert free['independent']is True and free['current_free']is True
    assert physical['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
    assert physical['fixed_cutoffs']==BINDINGS['cutoffs']
    assert physical['no_existing_heavy']is True and physical['pids_current']==0 and physical['active_shared_records_absent']is True
    assert not physical['group_membership_observation']['errors'] and len(physical['closed_exclusive_probes'])==2
    assert all(first<=last<limit for first,last,limit in zip(capture['first_observed_clocks'],capture['observed_clocks'],BINDINGS['cutoffs']))
    assert prewarm['starttime']/100<started['starttime']/100<=capture['first_observed_clocks'][2]
    assert capture['observed_clocks'][2]<resource['reservation_holder']['starttime']/100<resource['observed_clocks'][2]
    lifecycle=physical['historical_Root59_native_and_physical']['native_lifecycle']
    assert lifecycle['nonce']=='4d1c28c2d9caa913e4ab1e8a504ac5ea'
    assert lifecycle['container']=='3205b91b74d8bb5ca29f993f6c5851674f04f5446de1b324ae4636a22a07b215'
    return capture,used


def exact_corpus(capture):
    """Every duplicate is compared before any new key is admitted. No aliases."""
    corpus={};provenance={}
    for path in PATHS:
        rows=capture
        for key in path:rows=rows[key]
        assert len(rows)==5
        for index,row in enumerate(rows):
            assert isinstance(row['argv'],list) and all(isinstance(x,str)for x in row['argv'])
            assert type(row['returncode'])is int and isinstance(row['stdout'],str) and isinstance(row['stderr'],str)
            assert row['positive_wait']is True and row['streams_closed']is True
            key=tuple(row['argv']);response={name:row[name]for name in ['returncode','stdout','stderr']}
            pointer='/'+'/'.join(path)+'/'+str(index)
            if key in corpus and corpus[key]!=response:
                raise ValueError('CONFLICTING_AUTHENTICATED_SUPPLEMENT_DUPLICATE '+json.dumps(row['argv']))
            corpus[key]=response;provenance.setdefault(key,[]).append(pointer)
    assert len(corpus)==5 and all(len(paths)==2 for paths in provenance.values())
    return corpus,provenance


class RetainedEffectOracle(_base.RetainedEffectOracle):
    def __init__(self,source_chain):
        super().__init__(source_chain)
        capture,used=authenticate_actual_proof();corpus,paths=exact_corpus(capture)
        original=set(self.rows);conflicts=[]
        for key,response in corpus.items():
            if key in self.rows and self.rows[key]!=response:conflicts.append(list(key))
        if conflicts:raise ValueError('CONFLICTING_BASE_SUPPLEMENT_REPLY '+json.dumps(conflicts))
        added=[];identical=[]
        for key,response in corpus.items():
            if key in self.rows:
                identical.append(list(key));continue
            # Direct exact DATA key insertion; unchanged get() remains the sole
            # dispatch path. No classifier broadening, alias or missing-key rule.
            self.rows[key]=copy.deepcopy(response)
            self.provenance[key]=dict(input=BINDINGS['inputs']['capture'],pointer=paths[key][0],
                                     all_duplicate_pointers=paths[key],derived=False,sudo_spelling_alias=False)
            added.append(list(key))
        assert len(original)==94 and len(added)==3 and len(identical)==2 and len(self.rows)==97
        self.inputs.update({row['path']:row for row in used.values()})
        self.input_supplement=dict(scope_limit=BINDINGS['scope_limit'],capture=BINDINGS['inputs']['capture'],
             positive_capture_join=BINDINGS['inputs']['capture_join'],finite_hot=BINDINGS['inputs']['finite_hot'],
             finite_join=BINDINGS['inputs']['finite_join'],base_keys=94,new_exact_keys=added,
             identical_existing_keys=identical,duplicates=paths_to_json(paths),conflicting_duplicates=[],
             new_aliases=0,missing_key_fallback=False,actual_commands=0,runtime_authority=None)

    def manifest(self):
        result=super().manifest();result['actual_bfd_input_supplement']=self.input_supplement
        return result


def paths_to_json(paths):
    return [dict(argv=list(key),pointers=value)for key,value in sorted(paths.items())]
