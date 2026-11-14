"""One finite actual current physical->pending19->snapshot caller body check.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only private pending metadata is generated; no snapshot, root or workload runs.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,runpy,socket,subprocess,sys
D=Path(__file__).resolve().parent;Q=D/'native-packet-1'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def forbidden(*a,**k):raise AssertionError('no process/socket/root/workload in whole-caller check')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p),bytes=Path(p).stat().st_size)
def main():
    cfg=json.loads((D/'STATIC-NONTEMPORAL-INPUTS.json').read_bytes())
    assert Path(sys.executable).resolve()==Path(cfg['interpreter']['path']).resolve()
    for row in json.loads((D/'CHECK-INPUT-PINS.json').read_bytes()):
        assert ref(row['path'])==row
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    pre=json.loads(Path(cfg['actual_full_preflight']['path']).read_bytes())
    binding=json.loads(Path(cfg['actual_binding_result']['path']).read_bytes())
    acceptance=json.loads(Path(cfg['actual_preparation_acceptance']['path']).read_bytes())
    assert acceptance['schema']=='mckernel.current-six-launch.actual-normalization-review.v1'
    assert acceptance['status']=='PASS_ACTUAL_CURRENT_SIX_LAUNCH_NORMALIZATION_ONLY' and acceptance['runtime_release'] is False
    assert acceptance['parent_nine_field_identity']==pre['parent_nine_field_identity']
    assert all(type(v)is int for v in pre['parent_nine_field_identity'].values())
    owner=load('actual_current_six_batch_owner',cfg['runtime_owner']['path'])
    nd,manifest=owner.bound_manifest(cfg['normalized_manifest']['path'],cfg['normalized_manifest']['sha256'])
    assert manifest==pre['validated_manifest_view']
    assert manifest['pair_rounds']==3 and manifest['pair']['cpus']==[0,1] and manifest['pair']['host_cpus']==[1,2]
    assert owner.SOURCE_HASHES==pre['runtime_source_hashes']==cfg['runtime_source_hashes']
    assert pre['root_owner_argv']==cfg['root_owner_argv']
    assert pre['qemu_argv']==nd.expected_qemu_argv(manifest,Path(pre['paths']['attempt']))
    assert len(pre['consumed_paths'])==79 and len(pre['readonly_roots'])==30
    parent=Path(binding['attempt_parent'])
    assert not list(parent.iterdir()) and not os.path.lexists(pre['paths']['attempt'])
    assert not os.path.lexists(str(parent)+'.owner-'+binding['nonce'])
    before=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert not before
    recipe=json.loads((D/'CONSTRUCTOR-SOURCE-REF.json').read_bytes())
    assert ref(recipe['path'])==recipe
    saved=sys.argv;sys.argv=[recipe['path']]
    try:runpy.run_path(recipe['path'],run_name='__main__')
    finally:sys.argv=saved
    produced=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert len(produced)==19
    seven=json.loads((Q/'FINAL-SEVEN-ROOT-CALL-DATA.json.PENDING-STATIC-CORRECTED').read_bytes())
    assert len(seven['steps'])==7 and seven['native_allowed_argv']==pre['root_owner_argv']
    assert seven['steps'][3]['argv_template']==pre['root_owner_argv']
    assert len(seven['fresh_capture_and_actual_command_paths'])==49 and len(set(seven['fresh_capture_and_actual_command_paths']))==49
    assert all(not os.path.lexists(p) for p in seven['fresh_capture_and_actual_command_paths'])
    assert all(not os.path.lexists(seven[k])for k in ('snapshot_output','final_machine_output','final_guard_output'))
    pending=json.loads((Q/'NATIVE-COHERENT-REVIEW-PACKET.json.PENDING-STATIC-CORRECTED').read_bytes())
    assert pending['actual_guest_runs']==0 and pending['native_runtime_authority'] is False
    assert pending['static_decision']==dict(path=None,sha256=None,bytes=None)
    b=json.loads((D/'fresh-snapshot-bindings.json.PENDING-STATIC-CORRECTED').read_bytes())
    assert b['mandatory_consumer_review']==cfg['actual_preparation_acceptance'] and b['stage_review']==cfg['actual_stage_acceptance']
    assert b['parent_review_identity']==pre['parent_nine_field_identity'] and b['pair_contract']==manifest['pair']
    assert b['runtime_source_fd_verifier']==cfg['runtime_source_fd_verifier']
    assert len(b['source_pins'])==9 and b['source_pins'][-1]==cfg['runtime_source_fd_verifier']
    verifier=load('qualified_selected_eight_source_FD_checker',cfg['runtime_source_fd_verifier']['path'])
    fdpin=ref(D/'RUNTIME-SOURCE-FD-IDENTITIES.json')
    verifier.check_runtime_sources(dict(runtime_source_refs=cfg['runtime_source_refs'],runtime_source_fd_identity_map=fdpin))
    fdmap=json.loads(Path(fdpin['path']).read_bytes())['identities']
    assert set(fdmap)=={row['path'] for row in cfg['runtime_source_refs']} and len(fdmap)==8
    for row in cfg['normalization_selected_six']:
        assert fdmap[row['path']]==pre['runtime_source_fd_identities'][row['path']]
    cases=[dict(case='actual-current-batch-normalization-and-full-loader-parent-argv',result='PASS'),dict(case='existing-nineteen-output-and-seven-row-49-path-joins',result='PASS'),dict(case='actual-selected-eight-FD-with-six-normalization-and-two-host-source-identities',result='PASS')]
    result=dict(status='PASS_ACTUAL_CURRENT_SIX_BATCH_PENDING19_AND_CALLER_BODY_ONLY',cases=cases,actual_pending_outputs=[ref(p) for p in sorted(produced)],source_publication_fetched_proof=None,final_static_release=None,actual_final_static_join=None,final_static_join_rule='Full dbd3 static_joins positive is invoked only by final-mode constructor after genuine combined static review and all final nineteen files exist; no placeholder static authority is substituted.',snapshot=None,runtime_release=False,root_operations=0,guest_runs=0,terminal_regression_replayed=False)
    (D/'actual-whole-caller-result.json').open('x').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(cases),pending_outputs=len(produced),root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
