"""Exact retained single-child launcher evidence, never live retirement authority.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No process, Docker, root or mutation action is provided by this module.
"""
from pathlib import Path
import ast,hashlib,json,os,stat
SCHEMA='mckernel.launcher.single-child-controller-proof.v1'
DECISION='PASS_ACTUAL_M06_SINGLE_CHILD_CONTROLLER_AND_SEVEN_DOCKER_CLIENTS_SOURCE_ONLY'
class Refusal(ValueError):pass
def need(ok,reason):
 if not ok:raise Refusal(reason)
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def checked(row):
 need(type(row)is dict and set(row)=={'path','sha256','bytes'},'whole controller descriptor')
 p=Path(row['path']);need(p.is_absolute() and p.resolve()==p,'canonical controller descriptor')
 fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size<=128<<20,'bounded controller input');chunks=[]
  while True:
   chunk=os.read(fd,1<<20)
   if not chunk:break
   chunks.append(chunk)
  raw=b''.join(chunks)
  z=os.fstat(fd);named=p.lstat();keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(all(getattr(a,k)==getattr(z,k)==getattr(named,k)for k in keys),'stable controller input')
 finally:os.close(fd)
 need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'exact controller input bytes')
 return raw
def data(row):return json.loads(checked(row))
def require_review(review,proof_ref):
 need(review is not None,'independent controller review pending')
 r=data(review)
 need(r.get('implementation_ownership')is False and type(r.get('reviewer'))is str and bool(r['reviewer']) and r.get('decision')==DECISION and r.get('findings')==[] and r.get('accepted_proof')==proof_ref and r.get('cleanup_release')is None and r.get('physical_clearance')is False,'exact independent controller source review')
 return r
def validate(proof_ref,review=None,require_authority=True):
 p=data(proof_ref);need(p.get('schema')==SCHEMA and p.get('outer_os_identity')is None and p.get('outer_group_observation')is None and p.get('runtime_release')is None,'typed controller scope; outer identity unobserved')
 roles=p['roles'];need(set(roles)=={'request','owner','driver','artifact_review','owner_source','supervisor_command','supervisor_source','tool_started','tool_completed','child_start','controller_status','controller_stdout','controller_stderr'},'complete controller role set')
 raw={key:checked(row)for key,row in roles.items()};v={key:json.loads(value)for key,value in raw.items()if key not in ('owner_source','supervisor_source','controller_stdout','controller_stderr')}
 request,owner,driver=v['request'],v['owner'],v['driver'];child,status=v['child_start'],v['controller_status'];artifact=v['artifact_review']
 need(status['returncode']==0 and type(status['returncode'])is int and all(status[k]is True for k in ('direct_child_joined','process_group_absent','streams_closed')),'positive exact supervisor child wait/group/stream joins')
 need(set(child)=={'pid','start','argv'} and type(child['pid'])is int and child['pid']>0 and type(child['start'])is str and child['start'].isdigit(),'real child OS identity')
 need(child['argv']==['/usr/bin/python3','-I','-B',roles['owner_source']['path'],roles['request']['path']],'exact current owner child command')
 need(owner['status']=='PASS' and owner['exit_code']==0 and owner['retired']is True and owner['terminal_container_retained']is True and owner['cleanup_separately_required']is True and not owner.get('client_retirement_unproven'),'positive retained owner; separate cleanup remains')
 need(owner['schema']=='mckernel.native-exact-launcher-container-receipt.v1' and owner['launcher_only']is True and owner['operation_scope']=='launcher-only','current launcher owner shape')
 need(json.loads(raw['controller_stdout'])==owner and raw['controller_stderr']==b'','exact closed owner stdout/stderr')
 need(driver['status']=='PASS' and driver['kernel_rebuilt']is False and driver['native_fork_owned_transaction']is True and driver['actual_elf_needed_provider_join']is True,'actual production launcher receipt')
 need(artifact['implementation_ownership']is False and artifact['reviewer'] and artifact['decision']=='PASS_ACTUAL_M06_LAUNCHER_PRODUCTION_ARTIFACT_ONLY' and artifact['findings']==[] and artifact['receipt']==roles['driver'] and artifact['owner_retirement_acceptance']is None and artifact['native_acceptance']is False,'separate artifact-only review')
 need(driver['launcher_source_sha256']==artifact['launcher_source_sha256']==p['launcher_source_sha256'],'current launcher source join')
 for key in ('candidate_sha','source_derivative_sha256','materialization_sha256'):
  need(owner[key]==request[key],'owner/request source fingerprint '+key)
 need(artifact['toolchain_manifest_sha256']==driver['toolchain_manifest_sha256']==request['toolchain_manifest_sha256'],'pinned compiler join')
 for role in ('elf','rust_object'):checked(artifact[role])
 target=p['target'];need(set(target)=={'container_id','container_name','owner_nonce','owner_pid','owner_starttime','image_id','exit_code'},'whole actual target')
 need(all(target[k]==owner[k]for k in ('container_id','container_name','owner_nonce','exit_code')) and (target['owner_pid'],target['owner_starttime'])==(child['pid'],child['start']) and target['image_id']==request['image_id'],'exact actual target identity')
 first=v['tool_started']['event']['params']['item'];last=v['tool_completed']['event']['params']['item']
 need(v['tool_started']['event']['method']=='item/started' and v['tool_completed']['event']['method']=='item/completed','genuine tool protocol event pair')
 keys=('type','id','command','cwd','processId','source','commandActions')
 need(all(first[k]==last[k]for k in keys) and first['command']==v['supervisor_command'],'tool exact command/session identity')
 need(first['type']=='commandExecution' and first['status']=='inProgress' and first['exitCode']is None and last['status']=='completed' and last['exitCode']==0 and type(last['exitCode'])is int and last['processId']==p['tool_session'],'actual completed tool terminal')
 # Source is retained for independent exact-control-flow review. Verify the
 # one Popen/one direct p.wait shape here without executing that source.
 tree=ast.parse(raw['supervisor_source']);calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)]
 pops=[n for n in calls if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='subprocess' and n.func.attr=='Popen']
 waits=[n for n in calls if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='p' and n.func.attr=='wait']
 need(len(pops)==len(waits)==1 and any(k.arg=='start_new_session'and isinstance(k.value,ast.Constant)and k.value.value is True for k in pops[0].keywords),'one source-exact direct child/session/wait')
 ledger=p['controller_client_ledger'];need(set(ledger)=={'schema','owner_child','docker_clients'}and ledger['schema']=='mckernel.launcher.controller-client-ledger.v1','typed controller client ledger')
 need(ledger['owner_child']==dict(pid=child['pid'],start=child['start'],child_start=roles['child_start'],status=roles['controller_status']),'exact owner child ledger')
 clients=ledger['docker_clients'];capture=Path(owner['attempt_root'])
 need(type(clients)is list and len(clients)==7 and {r['status']['path']for r in clients}=={str(q)for q in capture.glob('command-*/status.json')},'all seven actual Docker client statuses')
 pids=[child['pid']];paths=[roles['controller_status']['path']]
 for row in clients:
  need(set(row)=={'pid','status','stdout','stderr'},'whole Docker client ledger row');s=data(row['status']);checked(row['stdout']);checked(row['stderr'])
  need(type(row['pid'])is int and row['pid']>0 and s['pid']==row['pid'] and s['state']=='exited' and type(s['exit_code'])is int and s['exit_code']==0 and not s.get('client_retirement_unproven'),'positive saved Docker client terminal')
  parent=Path(row['status']['path']).parent
  need(parent.parent==capture and row['stdout']['path']==str(parent/'stdout')and row['stderr']['path']==str(parent/'stderr'),'exact Docker client stream/status paths')
  need(s['argv'][:4]==['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'],'actual Docker command provider')
  pids.append(row['pid']);paths.append(row['status']['path'])
 need(len(set(pids))==8,'eight distinct saved child/client PIDs')
 if require_authority:require_review(review,proof_ref)
 return dict(proof=p,owner=owner,driver=driver,request=request,target=target,pids=tuple(pids),status_paths=paths,ledger=ledger,review=review,physical_clearance=False)
