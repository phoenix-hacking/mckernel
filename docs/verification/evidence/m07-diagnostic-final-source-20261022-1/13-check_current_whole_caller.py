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
    assert nd._same_plan(nd._freeze(nd._thaw(manifest)),nd._freeze(pre['validated_manifest_view'])) and manifest['payload']==cfg['payload_contract']
    assert pre['raw_manifest_descriptor']==cfg['normalized_manifest']
    assert nd._same_plan(nd._freeze(pre['raw_manifest_view']),nd._freeze(json.loads(Path(cfg['normalized_manifest']['path']).read_bytes())))
    assert nd._same_plan(nd._freeze(nd._thaw(nd.load_manifest(cfg['normalized_manifest']['path']))),nd._freeze(pre['validated_manifest_view']))
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
    # Inspect complete pending binder outputs and their actual selected control files.
    pending_cfg=json.loads((Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json.PENDING-STATIC-CORRECTED').read_bytes())
    runtime_map=json.loads(Path(pending_cfg['runtime_source_fd_identity_map']['path']).read_bytes())
    selected={row['path'] for row in pending_cfg['runtime_source_refs'] if row['path'].endswith('.py')}
    assert len(selected)==12 and set(runtime_map['identities'])==selected
    assert not selected.intersection({str(D/'bind_numa_native_packet.py'),str(D/'check_current_whole_caller.py'),str(Q/'root-run-exact-readonly-stage.py'),str(Q/'review_final_threads_release.py'),str(Q/'root-execute-seven-1.py')})
    assert pending['root_caller']==ref(Q/'root-run-exact-readonly-stage.py') and pending['final_guard_source']==ref(Q/'review_final_threads_release.py')
    executor=Q/'root-execute-seven-1.py.PENDING-STATIC-CORRECTED'
    executor_observed=ref(executor);executor_final=dict(executor_observed,path=str(Q/'root-execute-seven-1.py'))
    assert executor_final==pending['root_executor'] and not (Q/'root-execute-seven-1.py').exists()
    assert seven['required_caller']==ref(Q/'root-run-exact-readonly-stage.py')
    for row in seven['steps']:
        assert row['caller_argv_template'][3]==str(Q/'root-run-exact-readonly-stage.py')
    assert any(isinstance(n,__import__('ast').Assign) and any(isinstance(t,__import__('ast').Name) and t.id=='B' for t in n.targets) and __import__('ast').literal_eval(n.value.args[0])==str(Q) for n in __import__('ast').parse(executor.read_text()).body)
    assert pending['seven_rows']['sha256'] in executor.read_text()
    code=[row for row in cfg['runtime_source_refs'] if row['path'].endswith('.py')]
    roles=json.loads(Path(cfg['native_predecessor_binding']['path']).read_bytes())
    code += [ref(D/'root_manual_snapshot_threads.py'),roles['released_record_projection_source'],ref(D/'bind_numa_native_packet.py'),ref(D/'check_current_whole_caller.py'),ref(Q/'root-run-exact-readonly-stage.py'),ref(Q/'review_final_threads_release.py'),executor_observed]
    assert len(code)==len({row['path'] for row in code})==17
    descriptor=next(row for row in cfg['runtime_source_refs'] if row['path'].endswith('/remaining_descriptor.json'))
    # The qualified caller has an absolute, separately pinned capture primitive provider.
    caller_source=(Q/'root-run-exact-readonly-stage.py').read_text();caller_tree=__import__('ast').parse(caller_source)
    helper_node=next(n for n in caller_tree.body if isinstance(n,__import__('ast').Assign) and any(isinstance(t,__import__('ast').Name) and t.id=='hp' for t in n.targets))
    helper=Path(__import__('ast').literal_eval(helper_node.value.args[0]));helper_ref=ref(helper)
    assert helper_ref['sha256']=='5c884624b748b862aa1b48a369d3ee758f311ab6c70e82f1346c93d6b478b10d'
    fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns');identities={}
    for row in code+[descriptor,helper_ref]:
        path=Path(row['path']);fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd);chunks=[]
            while True:
                chunk=os.read(fd,1<<20)
                if not chunk:break
                chunks.append(chunk)
            after=os.fstat(fd);named=path.lstat();raw=b''.join(chunks)
            assert __import__('stat').S_ISREG(before.st_mode) and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields)
            assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row.get('bytes',row.get('size'))
            identities[str(path)]={k:getattr(before,k) for k in fields}
        finally:os.close(fd)
    assert {path:identities[path] for path in selected}==runtime_map['identities']
    closure=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_COMPLETE_CURRENT_PENDING17_CODE_DESCRIPTOR_HELPER_AND_RUNTIME12_CONFIG_FD_JOINS_ONLY',code=code,descriptor=descriptor,external_qualified_caller_helper=helper_ref,full_nine_field_identities=identities,retained_FD_lease=False,executor_observed=executor_observed,executor_future_final_descriptor=executor_final,actual_pending_packet=ref(Q/'NATIVE-COHERENT-REVIEW-PACKET.json.PENDING-STATIC-CORRECTED'),runtime12_map=ref(Path(pending_cfg['runtime_source_fd_identity_map']['path'])),future_final_static_review=None,snapshot=None,runtime_release=None)
    (D/'ACTUAL-COMPLETE-CONTROL-AND-FD-CLOSURE.json').open('x').write(json.dumps(closure,sort_keys=True,indent=2)+'\n')
    assert pending_cfg['external_latest_native_physical_review']==cfg['external_latest_native_physical_review']
    assert pending['external_latest_native_physical_review']==pending_cfg['external_latest_native_physical_review']
    assert pending_cfg['legacy_reference_scope']=='NATIVE_TERMINAL_ANCESTRY_ONLY_C9_RELEASED_BUILD_ANCESTRY'
    cases=[dict(case='genuine-current-reader-owner-loader-pending19-and-snapshot-terminal-joins',result='PASS')]
    def refuse(name,fn,expected_exception=ValueError,contains=None):
        try:fn()
        except expected_exception as e:
            if contains is not None:assert contains in str(e),str(e)
            cases.append(dict(case=name,result='REFUSED'));return
        raise AssertionError('required refusal not observed: '+name)
    for key in ('container_id','owner_nonce'):
        altered=copy.deepcopy(b);altered['physical_predecessor'][key]='0'*len(altered['physical_predecessor'][key])
        refuse('wrong-current-native-projection-'+key,lambda altered=altered:snapshot.terminal_joins(physical,altered),snapshot.Refusal,contains='latest native container and owner nonce')
    binding=json.loads(Path(cfg['actual_binding_result']['path']).read_bytes());parent=Path(binding['attempt_parent'])
    assert not list(parent.iterdir()) and not os.path.lexists(pre['paths']['attempt']) and not os.path.lexists(str(parent)+'.owner-'+binding['nonce'])
    result=dict(status='PASS_ACTUAL_CURRENT_KIND_PENDING19_AND_CALLER_BODY_ONLY',cases=cases,actual_pending_outputs=[ref(p) for p in sorted(produced)],source_publication_fetched_proof=None,final_static_release=None,snapshot=None,runtime_release=False,root_operations=0,guest_runs=0)
    (D/'actual-whole-caller-result.json').open('x').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(cases),pending_outputs=len(produced),root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
