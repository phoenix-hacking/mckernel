"""Pure, exact-kind M03 native-failure physical receipt decoder.
No snapshot/root/guest operations. Full authoritative descriptors retained.
"""
from pathlib import Path
import hashlib,json,os,stat
SCHEMA='mckernel.independent-actual-m03-native-failure-physical-retirement-review.v1'
def need(ok,why):
 if not ok:raise ValueError(why)
COMPACT_FIELDS = {'path', 'sha256', 'bytes'}
IDENTITY_FIELDS = {'path', 'sha256', 'size', 'device', 'inode', 'uid', 'gid',
                   'mode', 'nlink', 'mtime_ns', 'ctime_ns'}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink',
               'st_size', 'st_mtime_ns', 'st_ctime_ns')

def no_duplicates(pairs):
 result = {}
 for key, value in pairs:
  need(key not in result, 'duplicate physical JSON key')
  result[key] = value
 return result

def read_bytes(r):
 """Read one known full descriptor through a stable, bounded regular-file FD."""
 need(isinstance(r, dict) and set(r) in (COMPACT_FIELDS, IDENTITY_FIELDS),
      'known full authoritative descriptor shape')
 p = Path(r['path'])
 need(p.is_absolute() and p.resolve(strict=True) == p and not p.is_symlink(),
      'canonical physical descriptor')
 expected = r['bytes'] if set(r) == COMPACT_FIELDS else r['size']
 need(type(expected) is int and 0 <= expected <= 4 << 20, 'bounded physical descriptor size')
 fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
 try:
  before = os.fstat(fd)
  need(stat.S_ISREG(before.st_mode) and before.st_size == expected,
       'bounded regular physical descriptor')
  raw = bytearray()
  while len(raw) <= expected:
   block = os.read(fd, min(65536, expected + 1 - len(raw)))
   if not block:
    break
   raw.extend(block)
  after = os.fstat(fd)
  linked = p.lstat()
  need(all(getattr(before, k) == getattr(after, k) == getattr(linked, k)
           for k in STAT_FIELDS), 'stable physical descriptor FD/path identity')
  need(len(raw) == expected and hashlib.sha256(raw).hexdigest() == r['sha256'],
       'exact physical descriptor bytes')
  if set(r) == IDENTITY_FIELDS:
   actual = dict(device=after.st_dev, inode=after.st_ino, uid=after.st_uid,
                 gid=after.st_gid, mode=oct(stat.S_IMODE(after.st_mode)),
                 nlink=after.st_nlink, size=after.st_size,
                 mtime_ns=after.st_mtime_ns, ctime_ns=after.st_ctime_ns)
   need(all(r[k] == v for k, v in actual.items()), 'full actual raw record identity')
  return bytes(raw)
 finally:
  os.close(fd)

def checked(row):return json.loads(read_bytes(row),object_pairs_hook=no_duplicates)
CONTEXT_REF={'path': '/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/runtime-source-1/NATIVE-FAILURE-PHYSICAL-CONTEXT.json', 'sha256': 'e447e5be04965f946413a0498aade1bee7f7021145c3c6ef5fcfe21f83a66f12', 'bytes': 2243}

def kind(t):
 need(t['schema']==SCHEMA and t['status']=='PASS' and t['decision']=='PASS_PHYSICAL_RETIREMENT_M03_NATIVE_FAILURE_ONLY','exact current native-failure physical kind')

def captured_bytes(row):
 need(set(row)=={'path','sha256','metadata'} and set(row['metadata'])=={'device','inode','uid','gid','mode','nlink','size','mtime_ns','ctime_ns'},'full native captured stream identity')
 fd=dict(row['metadata'],path=row['path'],sha256=row['sha256'])
 # Native caller serializes permission bits as an integer; f78 reader uses
 # octal text. Preserve original rows in report and normalize only this scalar.
 need(type(fd['mode']) is int and 0<=fd['mode']<=0o7777,'native captured permission bits')
 fd['mode']=oct(fd['mode'])
 return read_bytes(fd)

def tar_members(raw, expected):
 import io,tarfile
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
  members=archive.getmembers();files=[m for m in members if m.isfile()]
  need(len(files)==expected and len({m.name for m in members})==len(members)
       and all(m.isfile() or (m.isdir() and m.name=='.') for m in members),'exact regular retained archive members')
  result={}
  for member in files:
   need(member.name.startswith('./') and '/' not in member.name[2:] and member.size<=4<<20,'bounded flat saved member')
   value=archive.extractfile(member).read((4<<20)+1)
   need(len(value)==member.size,'whole saved archive member')
   result[member.name]=value
  return result

def status_join(row, rc):
 need(row['returncode']==rc and row['direct_child_joined'] is True and row['process_group_absent'] is True and row['observer_error'] is None,'closed current native/readback direct and group status')
 if 'streams' in row:
  need(set(row['streams'])=={'stdout','stderr'},'both full captured streams')
  for stream in row['streams'].values():captured_bytes(stream)

def project(t,physical_ref):
 kind(t);ctx=checked(CONTEXT_REF)
 need(physical_ref==ctx['physical'] and t==checked(physical_ref),'whole actual current native-failure report authority')
 for key in ('physical_release','retired','all_owned_groups_empty','container_absent'):
  need(t[key] is True,'positive native retirement fact '+key)
 need(t['lease_retained'] is False and t['implementation_ownership'] is False,'independent released native owner')
 for key in ('application_acceptance','native_acceptance','module_load_acceptance','semantic_case_acceptance'):
  need(t[key] is False,'physical report grants no semantic/native acceptance '+key)
 facts=t['physical_facts'];counts=t['counts'];scan=facts['host_proc_scan']
 need(scan['matches']==[] and scan['permission_denials']==[] and counts['live_matches']==counts['proc_permission_denials']==0,'complete host census has no survivors or denials')
 need(len(scan['pid_start_tuples'])==counts['host_pid_start_tuples_checked'] and len(scan['groups'])==counts['owned_host_groups_checked'] and len(scan['sessions'])==counts['owned_host_sessions_checked'],'whole authentic host census cardinalities')
 need(counts['new_native_persistent_ownership_record_files']==0,'native owner has no new persistent record transaction')
 need(facts['all_25_clients_positive_reaped'] is True and facts['container_rm_zero'] is True and facts['exact_current_name_owner_label_and_CID_post_rm_censuses_zero'] is True and facts['all_recorded_stream_hashes_and_nine_field_identities_verified'] is True,'accepted native owner client/record retirement predicates')
 statuses=[checked(r) for r in t['completed_statuses']]
 need(len(statuses)==6 and len(t['closed_readbacks'])==3,'whole native/atomic/three-reader status set')
 for i,row in enumerate(statuses):status_join(row,1 if i<2 else 0)
 atomic=checked(t['atomic_terminal_stdout']);receipt=facts['atomic_receipt']
 need(atomic['status']=='PASS_CLOSED_OWNER_TERMINAL_RECEIPT_READBACK_ONLY' and atomic['owner_status_sha256']==t['completed_statuses'][1]['sha256'] and atomic['receipt']==receipt and atomic['root_mutations']==0,'whole exact atomic terminal receipt proof')
 need(receipt['status']=='FAIL' and receipt['absence_verified'] is True and receipt['lease_retained'] is False and receipt['container']==t['container_id'] and receipt['secondary']==[],'actual native failure receipt CID and positive absence')
 need(captured_bytes(statuses[2]['streams']['stdout'])==read_bytes(t['atomic_terminal_stdout']),'atomic captured stream exact authority bytes')
 archives=[read_bytes(r) for r in t['closed_readbacks']]
 for i,raw in enumerate(archives):
  need(captured_bytes(statuses[i+3]['streams']['stdout'])==raw and captured_bytes(statuses[i+3]['streams']['stderr'])==b'','exact closed failure archive/cat stream identities')
 owner=tar_members(archives[0],counts['owner_archive_regular_files'])
 attempt=tar_members(archives[2],counts['attempt_archive_regular_files'])
 need(owner['./result.json']==json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()+b'\n' or json.loads(owner['./result.json'])==receipt,'whole archived terminal receipt')
 need(hashlib.sha256(owner['./result.json']).hexdigest()==atomic['receipt_sha256'] and len(owner['./result.json'])==atomic['receipt_bytes'],'atomic receipt authenticates archived exact bytes')
 need(archives[1]==attempt['./result.json'] and facts['attempt_result_byte_identical_tar_and_cat'] is True,'whole actual result equality across cat and TAR')
 result=json.loads(archives[1]);need(result['cleanup']==facts['qemu_cleanup'] and result['cleanup']['reaped'] is True and result['cleanup']['errors']==[] and result['capture_errors']==facts['capture_errors']==[] and result['qemu_evidence']==facts['qemu_namespace_identity'],'actual QEMU reaped without capture/cleanup errors; guest namespace kept separate')
 meta=json.loads(owner['./owner.json']);need(meta['nonce']==t['owner_nonce'] and meta['lock']==dict(dev=27,ino=4,uid=0,gid=0,mode=420,nlink=1),'actual archived native owner nonce and permanent mutex identity')
 argv=statuses[1]['argv'];need(meta['owner_sha256']==argv[argv.index('--owner-sha256')+1] and t['owner_nonce']==argv[argv.index('--nonce')+1],'exact archived owner source/actual argv/nonce')
 clients=[(name,json.loads(raw)) for name,raw in sorted(owner.items()) if len(name)>6 and name[2:5].isdigit() and name.endswith('.json')]
 need(len(clients)==counts['docker_clients']==25,'all current owner Docker client records')
 codes=[]
 for name,client in clients:
  need(client['command']['reaped'] is True and type(client['command']['returncode']) is int,'positive actual Docker client wait')
  codes.append(dict(record=name,returncode=client['command']['returncode']))
 need(codes==facts['client_returncodes'],'all current saved client exit codes')
 ps=clients[-3:]
 need(all(x['argv'][3]=='ps' and x['command']['returncode']==0 and owner[name[:-5]+'.stdout']==b'' and owner[name[:-5]+'.stderr']==b'' for name,x in ps),'three actual post-rm empty censuses')
 terminal=facts['terminal_container_state'];need(terminal['Status']=='exited' and terminal['Running'] is False and terminal['Pid']==0 and terminal['OOMKilled'] is False,'actual exited terminal container')
 mutex=facts['permanent_development_mutex'];need(mutex['device']==27 and mutex['inode']==4 and mutex['never_unlinked'] is True and mutex['reviewer_reacquisition_attempted'] is False,'truthful preserved permanent mutex; live admission rechecks separately')
 pipeline=checked(t['whole_failed_owner_pipeline']);need(len(pipeline['rows'])==4 and [r['returncode'] for r in pipeline['rows']]==[0,0,0,1] and pipeline['rows'][0]['status_path']==ctx['LAST_status']['path'],'actual completed snapshot/assembly/guard/failure pipeline')
 join=checked(t['original_root_tool_wholejoin']);need(join['schema']=='mckernel.root-original-tool-wholejoin.v1' and join['whole_join_observed'] is True and join['actual_controller_whole']==t['whole_failed_owner_pipeline'],'positive original controller whole join')
 last=checked(ctx['LAST_status']);status_join(last,0);lastargv=last['argv']
 need(lastargv[:8]==['/usr/bin/prlimit','--as=1073741824','--cpu=30','--','/home/holden/anaconda3/bin/python3','-I','-B',ctx['caller_source']['path']],'same complete actual LAST caller prefix')
 need(lastargv[lastargv.index('--commands-file')+1]==ctx['LAST_command_data']['path'] and lastargv[lastargv.index('--commands-sha256')+1]==ctx['LAST_command_data']['sha256'],'full hashed actual LAST command data')
 data=checked(ctx['LAST_command_data']);need(data['release']==t['accepted_static_release'],'same actual static authority as spent native owner')
 snap=data['operations'][1]['argv_template'];need(snap[snap.index('--bindings-sha256')+1]==ctx['snapshot_bindings']['sha256'] and str(Path(ctx['snapshot_source']['path']).parent/'fresh-snapshot-bindings.json')==ctx['snapshot_bindings']['path'] and ctx['snapshot_source']['path'] in snap,'exact source-relative LAST full binding authority')
 read_bytes(ctx['snapshot_source']);read_bytes(ctx['caller_source']);b=checked(ctx['snapshot_bindings']);need(b['static_review']==t['accepted_static_release'] and b['root_owner_argv']==statuses[1]['argv'],'actual selected prior snapshot and native-owner source context')
 predecessor=b['physical_predecessor'];paths=[predecessor[k] for k in ('lease_path','common_exclusion','shared_heavy')]
 need(set(paths)==set(facts['predecessor_active_lease_and_common_shared_paths_absent']) and len(set(paths))==3,'prior active path identity; no fabricated current native records')
 for path in paths:need(not os.path.lexists(path),'prior active path currently remains absent')
 # The lease/common/shared interface is ONLY persistent predecessor-absence
 # identity. Latest CID/nonce are directly from39cd, never from old0e99.
 return dict(boot_id=predecessor['boot_id'],filesystem_uuid=predecessor['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['owner_nonce'],lease_path=paths[0],common_exclusion=paths[1],shared_heavy=paths[2])
