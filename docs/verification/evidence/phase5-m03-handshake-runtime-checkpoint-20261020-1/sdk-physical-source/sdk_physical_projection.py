"""One SDK retirement kind; reuse the accepted stable-FD reader unchanged.
No root/live snapshot/guest operations. No SDK artifact or M03 source join.
"""
from pathlib import Path
import hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent
READER={'path':'/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/runtime-source-1/native_failure_physical_projection.py','sha256':'ba5d3ea283eefb8f5e8249a8e703a10f4ffaeae15b8bfe4e51f379e8e6b45656'}
# Exact source hash is replaced from the accepted source descriptor at freeze.
SCHEMA='mckernel.independent-current-v6-sdk.actual-physical-retirement.v1'
def need(ok,why):
 if not ok:raise ValueError(why)
def reader():
 p=Path(READER['path']);need(hashlib.sha256(p.read_bytes()).hexdigest()==READER['sha256'],'accepted stable FD reader source')
 s=importlib.util.spec_from_file_location('accepted_m03_stable_fd_reader',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
R=reader();read_bytes=R.read_bytes;checked=R.checked
CONTEXT_REF={'path': '/home/holden/mckernel-work/host-preparation/phase5-m03-current-sdk-physical-binding-20261020-1/SDK-PHYSICAL-CONTEXT.json', 'sha256': '645ad0e5b92a3e1c889c41c999e07d1af3afd61c1ec06f6764d8275d7889c3e6', 'bytes': 8879}

def kind(t):
 need(t['schema']==SCHEMA and t['status']=='PASS' and t['decision']=='PASS_PHYSICAL_RETIREMENT_ONLY','exact current SDK physical kind')

def record_join(t,ctx,receipt,archive,authorized,complete,outer):
 need(archive['schema']=='mckernel.native-running-external-modules-ownership-archive.v1','SDK ownership archive kind')
 need(archive['records']==authorized['records']==ctx['archived_owned_records'],'whole archived SDK record identities and data')
 need(authorized['status']=='POSTFLIGHT_RELEASE_AUTHORIZED' and complete['status']=='OWNED_RECORDS_RELEASED','positive SDK record release')
 need(authorized['archive_sha256']==complete['archive_sha256']==t['ownership_archive']['sha256'],'exact release archive authority')
 need(archive['nonce']==authorized['nonce']==complete['nonce']==receipt['owner_nonce']==t['owner_nonce'],'SDK request-owner nonce')
 need(len(archive['records'])==len(t['raw_record_bindings'])==len(ctx['raw_record_FDs'])==3,'three SDK records')
 for row,binding,fd,key in zip(archive['records'],t['raw_record_bindings'],ctx['raw_record_FDs'],('operation_lease','common_record','shared_record')):
  raw=read_bytes(fd)
  need(binding['original']==row['path'] and binding['device']==row['device'] and binding['inode']==row['inode'],'whole original SDK record identity')
  need(binding['archive']==dict(path=fd['path'],sha256=fd['sha256'],bytes=fd['size']) and row['sha256']==fd['sha256'] and row['size']==len(raw),'full retained raw descriptor authority')
  need(json.loads(raw,object_pairs_hook=R.no_duplicates)==row['record']==receipt[key],'whole genuine SDK raw record content')
  need(row['record']['pid']==outer['pid'] and row['record']['starttime']==str(outer['start']),'SDK record process birth identity')
  need(not os.path.lexists(row['path']),'released SDK owned path currently absent')
 need(receipt['operation_lease']['nonce']!=t['owner_nonce'],'operation lease nonce stays distinct from request owner')
 for row in archive['records'][1:]:
  need(row['record']['inode']==row['inode'] and row['record'].get('dev',row['record'].get('device'))==row['device'],'SDK exclusion self identity')

def project(t,physical_ref):
 kind(t);ctx=checked(CONTEXT_REF)
 need(physical_ref==ctx['physical'] and t==checked(ctx['physical_FD']),'whole exact accepted SDK report')
 for key in ('physical_release','retired','all_owned_groups_empty','container_absent','current_owned_records_absent','outer_direct_joined','outer_group_absent'):
  need(t[key] is True,'positive SDK retirement '+key)
 for key in ('lease_retained','implementation_ownership','terminal_container_retained','cleanup_separately_required','application_acceptance','module_or_native_acceptance'):
  need(t[key] is False,'SDK physical-only fact '+key)
 need(t['permanent_mutex_identity']==[27,4,0,0],'SDK permanent mutex preserved identity')
 outer=checked(t['outer_status']);need(outer['returncode']==0 and outer['direct_child_joined'] is True and outer['process_group_absent'] is True and outer['observer_error'] is None,'closed actual SDK direct/group status')
 for name,fd in ctx['outer_stream_FDs'].items():
  raw=read_bytes(fd);r=outer['streams'][name]
  need(r['path']==fd['path'] and r['sha256']==fd['sha256'] and r['bytes']==fd['size'],'SDK outer whole stream authority')
  need(all(r[k]==fd[k] for k in ('device','inode','mtime_ns','ctime_ns')) and r['mode']==int(fd['mode'],8)|0o100000,'SDK outer captured stream identities')
  if name=='stderr_path':need(raw==b'','SDK outer stderr empty')
 receipt=checked(t['owner_receipt']);need(json.loads(read_bytes(ctx['outer_stream_FDs']['stdout_path']),object_pairs_hook=R.no_duplicates)==receipt,'SDK saved stdout equals complete owner receipt')
 need(receipt['status']==receipt['build_status']=='PASS' and receipt['retired'] is True and receipt['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and receipt['terminal_container_retained'] is False and receipt['cleanup_separately_required'] is False and receipt['wait_exit_code']==0,'SDK complete positive owner cleanup')
 need(receipt['container_id']==t['container_id'] and receipt['owner_nonce']==t['owner_nonce'],'SDK actual CID/request nonce')
 post=checked(t['postflight_proof']);need(post==receipt['postflight'] and post['container_absent'] is True and post['all_clients_reaped'] is True,'whole SDK postflight')
 groups=receipt['client_group_checks']+receipt['admission_client_group_checks']
 need(len(groups)==t['counts']['empty_group_checks']==42 and all(g['empty'] is True and g['surviving_members']==[] for g in groups),'all actual SDK owned groups empty')
 need(len(t['clients'])==t['counts']['unique_clients']==15 and receipt['client_count']==14 and receipt['admission_client_count']==1,'full SDK client cardinality')
 statuses={}
 for client in t['clients']:
  v=checked(client['status']);need(v['state']==client['state']=='exited' and v['exit_code']==client['exit_code']==0 and v['pid']==client['pid'],'positive exact SDK client exit')
  need(client['status']['path'] not in statuses,'unique SDK clients');statuses[client['status']['path']]=v
 need(set(statuses)=={g['status_path'] for g in groups} and all(statuses[g['status_path']]['pid']==g['pid'] for g in groups),'SDK complete client/group data join')
 terminal=checked(t['terminal_fresh_inspect']);state=terminal['State']
 need(terminal['Id']==t['container_id'] and terminal['Config']['Labels']['mckernel.owner']==t['owner_nonce'] and state['Status']=='exited' and state['Running'] is False and state['Pid']==0 and state['ExitCode']==0 and state['OOMKilled'] is False and state['Error']=='','SDK actual terminal state and owner')
 rm=checked(t['remove_command']['status']);need(rm['exit_code']==0 and rm['argv'][-2:]==['rm',t['container_id']],'same CID SDK removal')
 expected=['name=^/'+receipt['container_name']+'$','label=mckernel.owner='+t['owner_nonce'],'id='+t['container_id']]
 need(len(t['postremoval_censuses'])==3,'three SDK postremoval censuses')
 selectors=[]
 for client in t['postremoval_censuses']:
  v=statuses[client['status']['path']];need(v['argv'][-1] in expected and v['exit_code']==0,'actual selected SDK postremoval query');selectors.append(v['argv'][-1])
  need(read_bytes(ctx['census_streams'][client['status']['path']]['stdout'])==read_bytes(ctx['census_streams'][client['status']['path']]['stderr'])==b'','SDK postremoval census streams empty')
 need(set(selectors)==set(expected),'all three distinct SDK census selectors')
 need(post['absence']==dict(absent=True,container_id=t['container_id'],name=receipt['container_name'],nonce=t['owner_nonce'],queries=['name','label','id']),'exact SDK absence selectors')
 archive=checked(t['ownership_archive']);authorized=checked(t['record_release_authorized']);complete=checked(t['record_release_complete'])
 need(archive['postflight']==post,'SDK archive whole postflight');record_join(t,ctx,receipt,archive,authorized,complete,outer)
 request=receipt['request'];paths=[r['path'] for r in archive['records']]
 need(paths[:2]==[request['lease_path'],request['common_exclusion_path']] and paths[2]=='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock','genuine SDK owned paths')
 need(archive['records'][1]['record']['boot_id']==archive['records'][2]['record']['boot_id']==request['boot_id'],'SDK current boot data join')
 # SDK artifacts and compiler source tuple intentionally have no role here.
 return dict(boot_id=request['boot_id'],filesystem_uuid=ctx['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['owner_nonce'],lease_path=paths[0],common_exclusion=paths[1],shared_heavy=paths[2])
