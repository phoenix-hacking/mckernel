"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite closed-input DATA collection only; no imports of owner/engine and no live operations.
"""
from pathlib import Path
import hashlib,json,os,stat
T=Path(__file__).resolve().parent;C=T.parent;A=C/'pinned-launcher-attempt-1';G=C/'actual-pinned-build-capture-1';F=C/'final-release-assembly-1';S=C/'bound-source-1'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def data(p):return json.loads(Path(p).read_bytes())
def identity(p):
 p=Path(p);s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,size=s.st_size,nlink=s.st_nlink,sha256=ref(p)['sha256'])
status=data(G/'status.json');assert status['returncode']==0 and all(status[k]is True for k in ('direct_child_joined','process_group_absent','streams_closed'))
request_path=F/'pinned-launcher-request.FINAL.json';request=data(request_path);child=data(G/'child-start.json');owner_path=A/'owner-evidence/owner-receipt.json';owner=data(owner_path);driver_path=A/'owner-work/evidence/receipt.json';driver=data(driver_path)
assert owner['status']=='PASS' and owner['exit_code']==0 and owner['retired']is True and owner['terminal_container_retained']is True and owner['cleanup_separately_required']is True
assert driver['status']=='PASS' and driver['launcher_source_sha256']=='8f9fbe474220433118e6662c9f2517f73a547730575b83ffb73255d06e9b40d7' and driver['kernel_rebuilt']is False and driver['actual_elf_needed_provider_join']is True
assert data(G/'stdout')==owner and (G/'stderr').read_bytes()==b''
assert child['argv']==['/usr/bin/python3','-I','-B',str(S/'launcher_only_container_owner.py'),str(request_path)]
roles=dict(request=ref(request_path),owner=ref(owner_path),driver=ref(driver_path),owner_source=ref(S/'launcher_only_container_owner.py'),supervisor_source=ref(S/'capture_pinned_launcher_build.py'),child_start=ref(G/'child-start.json'),controller_status=ref(G/'status.json'),controller_stdout=ref(G/'stdout'),controller_stderr=ref(G/'stderr'))
clients=[];logs=[]
for p in sorted((A/'owner-evidence/attempt').glob('command-*/status.json')):
 s=data(p);assert s['state']=='exited' and s['exit_code']==0 and not s.get('client_retirement_unproven');row=dict(pid=s['pid'],status=ref(p),stdout=ref(p.parent/'stdout'),stderr=ref(p.parent/'stderr'));clients.append(row)
 if s['argv'][4]=='logs':logs.append(row)
assert len(clients)==7 and len(logs)==1 and len({child['pid'],*[r['pid']for r in clients]})==8
assert logs[0]['stderr']['bytes']==0 and (A/'owner-evidence/attempt/container.log').read_bytes()==Path(logs[0]['stdout']['path']).read_bytes()
ledger=dict(schema='mckernel.launcher.controller-client-ledger.v1',owner_child=dict(pid=child['pid'],start=child['start'],child_start=roles['child_start'],status=roles['controller_status']),docker_clients=clients)
target={k:owner[k]for k in ('container_id','container_name','owner_nonce','exit_code')};target.update(owner_pid=child['pid'],owner_starttime=child['start'],image_id=request['image_id'])
artifacts={}
for name,row in driver['artifact_copies'].items():
 p=A/'owner-work/evidence/artifacts'/name;r=ref(p);assert r['bytes']==row['size']and r['sha256']==row['sha256'];s=p.stat();artifacts[name]=dict(path=str(p),sha256=r['sha256'],size=r['bytes'],mode=s.st_mode)
x=dict(status='ACTUAL_CURRENT_LAUNCHER_OWNER_DRIVER_CLOSED_RETAINED_NOT_PHYSICALLY_RELEASED',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',roles=roles,target=target,controller_client_ledger=ledger,log_channels={k:logs[0][k]for k in ('status','stdout','stderr')},retained_ownership=dict(common=identity(request['common_exclusion_path']),shared=identity(owner['shared_heavy_operation']['path'])),owner_lease=dict(path=request['lease_path'],observed_absent=not os.path.lexists(request['lease_path']),meaning='Expected request lease release on owner retired; no physical clearance'),source_identity={k:request[k]for k in ('candidate_identity_scope','candidate_sha','launcher_plan','materialization_sha256','source_derivative_sha256','source_identity','source_root')},actual_artifact_candidates=artifacts,launcher_candidate=artifacts['mcexec'],artifact_acceptance=None,controller_review=None,tool_started=None,tool_completed=None,supervisor_command=None,current_live_postjoin=None,cleanup_release=None,physical_clearance=False,native_acceptance=False)
with(T/'ACTUAL-CLOSED-LAUNCHER-RECORDS.json').open('x')as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(ref(T/'ACTUAL-CLOSED-LAUNCHER-RECORDS.json'),sort_keys=True))
