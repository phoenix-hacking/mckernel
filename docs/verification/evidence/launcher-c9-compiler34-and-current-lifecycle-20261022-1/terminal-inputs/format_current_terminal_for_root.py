"""Finite mechanical projection. ROOT executes this; no runtime actions.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
All authority belongs to the preserved genuine independent decisions.
"""
from pathlib import Path
import hashlib,json,os,stat

HERE=Path(__file__).resolve().parent
T=HERE.parent.parent
G=Path('/home/holden/mckernel-work/host-preparation/current-focused-progress-recording-20261021-1/current-normalization-review-recording-1')
OLD=Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-terminal-data-preparation-1/actual-binding-1')
def ref(path):
    p=Path(path);b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(path,sha=None):
    p=Path(path);b=p.read_bytes()
    if sha:assert hashlib.sha256(b).hexdigest()==sha,str(p)
    return json.loads(b)
def write(name,data):
    p=HERE/name
    with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
    return ref(p)
def text(name,body):
    p=HERE/name
    with p.open('x') as f:f.write(body)
    return ref(p)
def descriptor(p):
    p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
    b=p.read_bytes();assert p.lstat()==s
    return dict(path=str(p),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,
                mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=len(b),sha256=hashlib.sha256(b).hexdigest())
def identity(p):
    s=Path(p).lstat();return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=s.st_mode)
def main():
    rawpath=G/'LAUNCHER-C9-ACTUAL-RETAINED-TERMINAL-POSTJOIN-REVIEW.json'
    raw=read(rawpath,'df2fd824ae77c87497efff7346240e6c7a8145d565dffbe549afbf3da0d9c595')
    assert ref(rawpath)['bytes']==3345
    artifactpath=G/'ROOT-MECHANICAL-CURRENT-C9-LAUNCHER-ARTIFACT-CONSUMER-1.json'
    artifact=read(artifactpath,'c8a734c59b070d8bc79b01dbf5c05ee726d073e60bfa7088cd77b7027741a764')
    dependency=G/'ROOT-MECHANICAL-CURRENT-C9-LAUNCHER-DEPENDENCY-CONSUMER-1.json'
    read(dependency,'d17009c9394d07b438cd4024ebdc128dcdc710f65a592e28083a91c4fe908b75')
    release=read(T/'launcher-execution-release.json')
    requestpath=Path(release['request']['path']);q=read(requestpath,release['request']['sha256'])
    pairpath=T/'latest-native12-release-binding-preparation-1/ACTUAL-TOOL-OWNED-62525-TERMINAL-PAIR-2.json'
    pair=read(pairpath,'09b691c2973bd5d78f2072d49f5dc91c4c5857bdb3eeb99d852eb58eb3b805aa')
    events={}
    for k in ('started','completed'):
        event=pair[k+'_event'];assert event['event']==event['protocol_record']['event']
        assert json.loads(event['raw_event_utf8'])==event['protocol_record']
        events[k]=write('ACTUAL-'+k.upper()+'-PROTOCOL.json',event['protocol_record'])
    first=pair['started_event']['event']['params']['item'];last=pair['completed_event']['event']['params']['item']
    assert all(first[k]==last[k] for k in ('type','id','command','cwd','processId','source','commandActions'))
    assert last['status']=='completed' and last['exitCode']==0
    assert [last['id'],last['processId'],last['durationMs']]==raw['controller_terminal_expected']
    capture=text('ACTUAL-TOOL-COMMAND-VERBATIM.txt',first['command'])
    action=first['commandActions'][0]['command'];assert action.startswith("python3 - <<'PY'\n") and action.endswith('\nPY')
    inline=text('ACTUAL-INLINE-PYTHON-EXTRACTED-SOURCE.txt',action[len("python3 - <<'PY'\n"):-len('\nPY')])
    write('CAPTURE-SOURCE-PROVENANCE.json',dict(kind='raw-tool-command-and-inline-source-evidence',capture_source=capture,
      inline_python_source=inline,raw_tool_pair=ref(pairpath),protocols=events,
      note='Neither evidence text path was executed. Actual command used inline python then os.execv; no executable dispatcher file or outer OS identity was observed.'))
    cap=Path(release['guard_capture']);ownerpath=T/'launcher-attempt-1/owner-evidence/owner-receipt.json'
    owner=read(ownerpath,artifact['owner_receipt']['sha256']);guardpath=cap/'guard-result.json';guard=read(guardpath)
    joinpath=Path(raw['root_postjoin']['path']);join=read(joinpath,raw['root_postjoin']['sha256'])
    assert join['owner_receipt_sha256']==ref(ownerpath)['sha256'] and join['guard_result_sha256']==ref(guardpath)['sha256']
    assert join['root27_4_reacquired_after_join'] and join['guard_direct_joined']
    # Legacy names are roles only. Never represent these typed projections as OS waits.
    outer=write('OUTER-STATUS-TYPED-TOOL-PROJECTION.json',dict(kind='tool-owned-terminal-projection-not-OS-wait',
      terminal_protocol=events['completed'],tool_pair=ref(pairpath),tool_id=last['id'],tool_session=last['processId'],
      exit_code=last['exitCode'],outer_os_identity=None,outer_group_observation=None))
    inner=write('INNER-STATUS-GUARD-POSTJOIN-PROJECTION.json',dict(kind='guard-and-root-postjoin-projection-not-OS-wait',
      guard_result=ref(guardpath),root_postjoin=ref(joinpath),guard_direct_joined=join['guard_direct_joined'],
      retired=guard['retired'],owner_status=guard['owner_status'],owner_receipt=ref(ownerpath)))
    authority=[]
    for role,path in [('common',q['common_exclusion_path']),('shared',owner['shared_heavy_operation']['path'])]:
        full=descriptor(path);record=read(path)
        assert record['pid']==raw['owner_pid'] and record['starttime']==raw['owner_starttime'] and record['boot_id']==release['boot_id']
        assert record['inode']==full['inode'] and record.get('dev',record.get('device'))==full['device']
        authority.append(dict(role=role,full_descriptor=full,record=record,sha256=full['sha256']))
    retained=dict(raw)
    retained.update(original_independent_decision=ref(rawpath),recorder='/root',owner_receipt=ref(ownerpath),guard_result=ref(guardpath),
      outer_status=outer,inner_status=inner,terminal_fresh_inspect=ref(cap/'inspect-terminal-fresh.json'),
      controller_terminal_receipt=events,retained_ownership={a['role']:a['full_descriptor'] for a in authority},
      source_derivative_sha256=artifact['source_derivative_sha256'],materialization_sha256=artifact['materialization_sha256'])
    retained['controller_terminal_contract']=dict(raw['controller_terminal_contract'],capture_source=capture)
    retainedref=write('ROOT-MECHANICAL-CURRENT-RETAINED-CONSUMER.json',retained)
    # Reuse immutable accepted common references; replace every changed actual-role descriptor.
    old=read(OLD/'ACTUAL-SAVED-TERMINAL-BINDINGS-CURRENT.json');data=dict(old);case=dict(old['case']);roles={}
    oldnamespace=old['case']['namespace'];namespace=T/'launcher-attempt-1'
    for key,row in old['case']['finite_roles'].items():
        if key.startswith(('client:','controller:')) or key in ('dispatcher','outer_status','inner_status','artifact_acceptance','dependency_acceptance','retained_physical','guard_postjoin','guard_result','guard_release','guard_source','request','owner_receipt','terminal_inspection','container_log'):continue
        if row['path'].startswith(oldnamespace+'/'):roles[key]=ref(str(namespace)+row['path'][len(oldnamespace):])
        else:roles[key]=dict(row)
    planpath=Path(release['launcher_plan']['path']);plan=read(planpath)
    roles.update(artifact['artifact_descriptors_verified'])
    for key,path in [('request',requestpath),('owner_receipt',ownerpath),('driver_receipt',artifact['producer_receipt']['path']),
      ('guard_result',guardpath),('guard_release',T/'launcher-execution-release.json'),('guard_source',T/'native_exact_current_optin_launcher_guard.py'),
      ('terminal_inspection',cap/'inspect-terminal-fresh.json'),('container_log',Path(q['attempt_root'])/'container.log'),('guard_transport_log',cap/'docker.log'),('launcher_plan',planpath),
      ('launcher_override',plan['source_override']['path']),('image_owner',T/'launcher_only_container_owner.py'),
      ('driver_path',q['driver_path']),('guard_postjoin',joinpath)]:roles[key]=ref(path)
    roles.update(dispatcher=capture,outer_status=outer,inner_status=inner,artifact_acceptance=ref(artifactpath),dependency_acceptance=ref(dependency),retained_physical=retainedref)
    for k,v in events.items():roles['controller:'+k]=v
    clients=read(HERE.parent/'ACTUAL-CLOSED-CLIENT-COUNT-SOURCE-ONLY.json')['clients'];ledger=[];logs=None
    for i,c in enumerate(clients):
        s=read(c['status']['path'],c['status']['sha256']);assert s['state']=='exited' and s['exit_code']==0 and s['pid']==c['pid']
        p=Path(c['status']['path']).parent
        for name in ('status.json','stdout','stderr'):roles[f'client:{i}:{name}']=ref(p/name)
        ledger.append(dict(pid=c['pid'],status_path=c['status']['path'],status_sha256=c['status']['sha256']))
        if s['argv'][-2:]==['logs',raw['container_name']]:
            assert logs is None
            assert (p/'stdout').read_bytes()+(p/'stderr').read_bytes()==Path(roles['container_log']['path']).read_bytes()
            logs={n:ref(p/n) for n in ('status.json','stdout','stderr')}
    assert len(clients)==raw['closed_saved_host_client_count']==8 and logs
    ancestry=[dict(path=str(p),**identity(p)) for p in reversed([namespace,*namespace.parents])]
    target={k:raw[k] for k in ('container_id','container_name','owner_nonce','owner_pid','owner_starttime')};target.update(exit_code=0,image_id=q['image_id'])
    source_identity={k:q[k] for k in ('candidate_identity_scope','candidate_sha','materialization_sha256','source_derivative_sha256','source_identity','source_root')};source_identity['launcher_plan']=ref(planpath)
    case.update(artifact_acceptance=ref(artifactpath),physical=retainedref,client_ledger=ledger,closed_saved_host_client_count=8,
      controller_command=first['command'],controller_terminal_expected=raw['controller_terminal_expected'],controller_terminal_receipt=events,
      current_live_postjoin=ref(joinpath),finite_roles=roles,finite_role_count=len(roles),finite_unique_paths=sorted({r['path'] for r in roles.values()}),
      full_original_record_authority=authority,guard_capture=str(cap),log_channels=logs,namespace=str(namespace),namespace_binding=identity(namespace),
      namespace_ancestry=ancestry,request=roles['request'],source_identity=source_identity,target=target,
      protected_inventory_roots=[str(namespace/'owner-work'),str(namespace/'owner-evidence')])
    sourcerefs={k:roles[k] for k in old['source_bindings']['source_refs']}
    data.update(artifact_acceptance=ref(artifactpath),dependency_acceptance=ref(dependency),boot_id=release['boot_id'],case=case,
      observation_nonce='current-c9-launcher-observation-1',raw_controller_pair_join=ref(pairpath),retained_review=retainedref,root_join=ref(joinpath),
      saved_guard_client_pids=[c['pid'] for c in clients],source_generation_output=str(HERE/'generated-source-1'),
      source_bindings=dict(current_typed_request=source_identity,guard_capture=str(cap),namespace_ancestry=ancestry,namespace_binding=identity(namespace),pass_log_channels=logs,source_refs=sourcerefs,target=target),
      status='ACTUAL_CURRENT_C9_CLOSED_DATA_GENUINE_DECISIONS_BOUND')
    dataref=write('ACTUAL-CURRENT-TERMINAL-DATA.json',data)
    write('FIELD-PROVENANCE.json',dict(raw_retained_decision=ref(rawpath),artifact_decision=ref(artifactpath),dependency_decision=ref(dependency),
      original_ownership_records=authority,client_status_source=ref(HERE.parent/'ACTUAL-CLOSED-CLIENT-COUNT-SOURCE-ONLY.json'),raw_protocol_source=ref(pairpath),
      actual_command_source=capture,inline_python_source=inline,outer_status_role=outer,inner_status_role=inner,
      root_postjoin=ref(joinpath),data=dataref,future_physical_release=None,future_cleanup_release=None,future_observer_release=None))
    print(json.dumps(dict(status='FINITE_ROOT_MECHANICAL_PROJECTION_COMPLETE',data=dataref,retained=retainedref)))
if __name__=='__main__':main()
