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
    mapping=json.loads(Path(cfg['physical_consumer_mapping']['path']).read_bytes())
    physical=json.loads(Path(cfg['latest_physical']['path']).read_bytes())
    expected=mapping['independently_data_bound_expected_projection']
    adapterref=json.loads((D/'CURRENT-PHYSICAL-DECODER-SOURCE.json').read_bytes())
    adapter=load('actual_current_pass2_reader',Path(adapterref['path']))
    snapshot=load('actual_threads_LAST_snapshot_source',D/'root_manual_snapshot_threads.py')
    rootlock=dict(device=27,inode=4,uid=0,gid=0,mode='0o644')
    b=dict(physical_projection_source=adapterref,physical_review=cfg['latest_physical'],physical_predecessor=expected,root_lock_identity=rootlock)
    # Exact current source caller, not a stand-in projection function.
    snapshot.terminal_joins(physical,b)
    assert physical==adapter.checked(cfg['latest_physical'])
    # Exact actual owner loader and accepted current normalized manifest.
    owner=load('actual_canonical_root_owner',cfg['runtime_owner']['path'])
    nd,manifest=owner.bound_manifest(cfg['normalized_manifest']['path'],cfg['normalized_manifest']['sha256'])
    pre=json.loads(Path(cfg['actual_full_preflight']['path']).read_bytes())
    assert manifest==pre['validated_manifest_view'] and manifest['payload']==cfg['payload_contract']
    assert owner.SOURCE_HASHES==cfg['runtime_source_hashes']
    assert pre['root_owner_argv']==cfg['root_owner_argv'] and pre['qemu_argv']==nd.expected_qemu_argv(manifest,Path(pre['paths']['attempt']))
    # Invoke the real existing nineteen-output derivative in pending mode only.
    before=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert not before
    saved_argv=sys.argv;sys.argv=[str(D/'bind_threads_native_packet.py')]
    try:generated=runpy.run_path(str(D/'bind_threads_native_packet.py'),run_name='__main__')
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
    binding=json.loads(Path(cfg['actual_binding_result']['path']).read_bytes())
    # Evaluate the actual production constructor. An explicit inert backend avoids
    # backend creation; no run/preflight/lock/root/container method is called.
    actual_owner=owner.DiagnosticOwner(binding['attempt_parent'],manifest=binding['manifest']['path'],manifest_sha256=binding['manifest']['sha256'],backend=object(),nonce=binding['nonce'])
    assert actual_owner.attempt==Path(pre['paths']['attempt'])
    assert actual_owner.parent.resolve(strict=True)==actual_owner.parent
    assert actual_owner.evidence==actual_owner.parent.with_name(actual_owner.parent.name+'.owner-'+binding['nonce'])
    wrong_parent=actual_owner.parent.with_name('p')
    assert not os.path.lexists(wrong_parent) and not os.path.lexists(str(wrong_parent)+'.owner-'+binding['nonce'])
    # The real host caller passes literal argv to Popen; tar --directory and
    # cat's operand resolve on the host, outside the owner container mount.
    outputs=generated['outputs'];validate=generated['validate_current_path_join']
    raw=validate(outputs,D,binding,pre)
    resolved=[Path(raw[0][5].removeprefix('--directory=')).resolve(strict=False),Path(raw[1][3]).resolve(strict=False),Path(raw[2][5].removeprefix('--directory=')).resolve(strict=False)]
    assert resolved==[actual_owner.evidence.resolve(strict=False),(actual_owner.attempt/'result.json').resolve(strict=False),actual_owner.attempt.resolve(strict=False)]
    assert all(str(wrong_parent) not in str(p) for p in resolved)
    assert actual_owner.container is None and actual_owner.lock is None and not actual_owner.create_issued and not actual_owner.pending_evidence
    cases=[dict(case='genuine-current-reader-owner-constructor-host-readbacks-pending19-and-whole-hash-joins',result='PASS')]

    def refuse(name,fn,expected_exception=ValueError,contains=None):
        try:fn()
        except expected_exception as e:
            if contains is not None:assert contains in str(e),str(e)
            cases.append(dict(case=name,result='REFUSED'));return
        raise AssertionError('required refusal not observed: '+name)
    # Refuse the exact inherited stale parent and each changed readback target
    # through the production whole-output validator, before descriptor rehashing.
    def replace_json(out,path,change):
        value=json.loads(out[path]);change(value);out[path]=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    stale=dict(outputs)
    replace_json(stale,Q/'conditional-metadata.json',lambda v:v['postjoin_readback'].update(argv=[[arg.replace(str(actual_owner.parent),str(wrong_parent)) for arg in row] for row in v['postjoin_readback']['argv']]))
    refuse('stale-inherited-parent-host-readbacks',lambda:validate(stale,D,binding,pre),contains='whole current host readback operands')
    for index in range(3):
        changed=dict(outputs)
        def wrong_target(v,index=index):
            row=v['postjoin_readback']['argv'][index]
            pos=5 if index!=1 else 3
            row[pos]+='.changed-target'
        replace_json(changed,Q/'conditional-metadata.json',wrong_target)
        refuse('changed-host-readback-target-'+str(index+1),lambda changed=changed:validate(changed,D,binding,pre),contains='whole current host readback operands')
    changed=dict(outputs)
    replace_json(changed,Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json',lambda v:v.update(owner_evidence=str(wrong_parent)+'.owner-'+binding['nonce']))
    refuse('changed-config-owner-evidence',lambda:validate(changed,D,binding,pre),contains='whole current config owner output derivation')
    changed=dict(outputs)
    replace_json(changed,Q/'FINAL-SEVEN-ROOT-CALL-DATA.json',lambda v:v['steps'][4]['argv_template'].__setitem__(-2,'--directory='+str(wrong_parent)+'.owner-'+binding['nonce']))
    refuse('changed-wrapped-reader-target',lambda:validate(changed,D,binding,pre),contains='whole current wrapped host readback argv')
    changed=dict(outputs)
    replace_json(changed,Q/'capture-templates/06-readback-3.json',lambda v:v['operations'][1]['argv_template'].__setitem__(-3,'--directory='+str(wrong_parent/('attempt-'+binding['nonce']))))
    refuse('changed-capture-reader-target',lambda:validate(changed,D,binding,pre),contains='whole current capture template join')
    changed=dict(outputs)
    replace_json(changed,Q/'FINAL-SEVEN-ROOT-CALL-DATA.json',lambda v:v.update(final_machine_output=str(D/'wrong-execution-release.json')))
    refuse('changed-late-machine-output',lambda:validate(changed,D,binding,pre),contains='whole current late output paths')
    status=adapter.checked(physical['actual_cleanup_status'])
    wrongfd=dict(status['stdout'],inode=status['stdout']['inode']+1)
    refuse('wrong-complete-stream-FD-inode',lambda:adapter.checked_bytes(wrongfd),contains='full actual transaction/raw record identity')
    badbirth=copy.deepcopy(physical['captures'][0]);badbirth['inner_birth']['proc_start_ticks']='0'
    refuse('changed-inner-birth-identity',lambda:adapter.capture_join(badbirth,status),contains='current inner birth identity')
    for key in ('container_id','owner_nonce'):
        altered=copy.deepcopy(b);altered['physical_predecessor'][key]='0'*len(altered['physical_predecessor'][key])
        refuse('wrong-expected-projection-'+key,lambda altered=altered:snapshot.terminal_joins(physical,altered),snapshot.Refusal,contains='complete genuine')
    binding=json.loads(Path(cfg['actual_binding_result']['path']).read_bytes());parent=Path(binding['attempt_parent'])
    assert not list(parent.iterdir()) and not os.path.lexists(pre['paths']['attempt']) and not os.path.lexists(str(parent)+'.owner-'+binding['nonce'])
    result=dict(status='PASS_ACTUAL_CURRENT_OWNER_READBACK_AND_WHOLE_PENDING19_BODY_ONLY',cases=cases,actual_pending_outputs=[ref(p) for p in sorted(produced)],source_publication_fetched_proof=None,final_static_release=None,snapshot=None,runtime_release=False,root_operations=0,guest_runs=0)
    (D/'actual-whole-caller-result.json').open('x').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(cases),pending_outputs=len(produced),root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
