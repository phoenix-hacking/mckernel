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
    physical=json.loads(Path(cfg['latest_physical']['path']).read_bytes())
    b=json.loads(Path(cfg['native_predecessor_binding']['path']).read_bytes())
    snapshot=load('actual_current_native_LAST_snapshot_source',D/'root_manual_snapshot_threads.py')
    snapshot.terminal_joins(physical,b)
    assert physical==snapshot.checked(cfg['latest_physical'])
    # Exact actual owner loader and accepted current normalized manifest.
    owner=load('actual_canonical_root_owner',cfg['runtime_owner']['path'])
    nd,manifest=owner.bound_manifest(cfg['normalized_manifest']['path'],cfg['normalized_manifest']['sha256'])
    pre=json.loads(Path(cfg['actual_full_preflight']['path']).read_bytes())
    assert manifest==pre['validated_manifest_view'] and manifest['payload']==cfg['payload_contract']
    assert owner.SOURCE_HASHES==cfg['runtime_source_hashes']
    assert pre['root_owner_argv']==cfg['root_owner_argv'] and pre['qemu_argv']==nd.expected_qemu_argv(manifest,Path(pre['paths']['attempt']))
    # Invoke the real existing nineteen-output derivative in pending mode only.
    before=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert not before
    saved_argv=sys.argv;sys.argv=[str(D/'bind_numa_native_packet.py')]
    try:runpy.run_path(str(D/'bind_numa_native_packet.py'),run_name='__main__')
    finally:sys.argv=saved_argv
    produced=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert len(produced)==19
    seven=json.loads((Q/'FINAL-SEVEN-ROOT-CALL-DATA.json.PENDING-STATIC-CORRECTED').read_bytes())
    assert len(seven['steps'])==7 and seven['native_allowed_argv']==pre['root_owner_argv']
    assert seven['steps'][3]['argv_template']==pre['root_owner_argv']
    assert len(seven['fresh_capture_and_actual_command_paths'])==49
    assert all(not os.path.lexists(p) for p in seven['fresh_capture_and_actual_command_paths'])
    assert all(not os.path.lexists(seven[k]) for k in ('snapshot_output','final_machine_output','final_guard_output'))
    pending=json.loads((Q/'NATIVE-COHERENT-REVIEW-PACKET.json.PENDING-STATIC-CORRECTED').read_bytes())
    assert pending['actual_guest_runs']==0 and pending['native_runtime_authority'] is False and pending['static_decision']==dict(path=None,sha256=None,bytes=None)
    cases=[dict(case='genuine-current-reader-owner-loader-pending19-and-snapshot-terminal-joins',result='PASS')]
    def refuse(name,fn,expected_exception=ValueError,contains=None):
        try:fn()
        except expected_exception as e:
            if contains is not None:assert contains in str(e),str(e)
            cases.append(dict(case=name,result='REFUSED'));return
        raise AssertionError('required refusal not observed: '+name)
    for key in ('container_id','owner_nonce'):
        altered=copy.deepcopy(b);altered['physical_predecessor'][key]='0'*len(altered['physical_predecessor'][key])
        refuse('wrong-current-native-projection-'+key,lambda altered=altered:snapshot.terminal_joins(physical,altered),snapshot.Refusal,contains='complete current failed-owner seven-field predecessor')
    binding=json.loads(Path(cfg['actual_binding_result']['path']).read_bytes());parent=Path(binding['attempt_parent'])
    assert not list(parent.iterdir()) and not os.path.lexists(pre['paths']['attempt']) and not os.path.lexists(str(parent)+'.owner-'+binding['nonce'])
    result=dict(status='PASS_ACTUAL_CURRENT_KIND_PENDING19_AND_CALLER_BODY_ONLY',cases=cases,actual_pending_outputs=[ref(p) for p in sorted(produced)],source_publication_fetched_proof=None,final_static_release=None,snapshot=None,runtime_release=False,root_operations=0,guest_runs=0)
    (D/'actual-whole-caller-result.json').open('x').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(cases),pending_outputs=len(produced),root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
