"""Pure, exact-kind current205 terminal-cleanup physical receipt decoder.
No snapshot/root/guest operations. Full authoritative descriptors retained.
"""
from pathlib import Path
import hashlib,json,os,stat
SCHEMA='mckernel.independent-current205-cleanup-physical-release-review.v1'
STATUS='PASS_ACTUAL_CURRENT205_CLEANUP_POSTJOIN_AND_POSITIVE_PHYSICAL_RETIREMENT'
TRANSACTION_FIELDS={'path','sha256','size','device','inode','uid','gid','mode','nlink'}
def need(ok,why):
 if not ok:raise ValueError(why)
COMPACT_FIELDS = {'path', 'sha256', 'bytes'}
IDENTITY_FIELDS = {'path', 'sha256', 'size', 'device', 'inode', 'uid', 'gid',
                   'mode', 'nlink', 'mtime_ns', 'ctime_ns'}
STREAM_FIELDS=(IDENTITY_FIELDS-{'size'})|{'bytes'}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink',
               'st_size', 'st_mtime_ns', 'st_ctime_ns')

def no_duplicates(pairs):
 result = {}
 for key, value in pairs:
  need(key not in result, 'duplicate physical JSON key')
  result[key] = value
 return result

def checked_bytes(r, limit=4<<20):
 """Read one known full descriptor through a stable, bounded regular-file FD."""
 need(isinstance(r, dict) and set(r) in (COMPACT_FIELDS, TRANSACTION_FIELDS, IDENTITY_FIELDS, STREAM_FIELDS),
      'known full authoritative descriptor shape')
 p = Path(r['path'])
 need(p.is_absolute() and p.resolve(strict=True) == p and not p.is_symlink(),
      'canonical physical descriptor')
 expected = r['bytes'] if set(r) in (COMPACT_FIELDS,STREAM_FIELDS) else r['size']
 need(type(expected) is int and 0 <= expected <= limit, 'bounded physical descriptor size')
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
  if set(r) in (TRANSACTION_FIELDS, IDENTITY_FIELDS, STREAM_FIELDS):
   actual = dict(device=after.st_dev, inode=after.st_ino, uid=after.st_uid,
                 gid=after.st_gid, mode=oct(stat.S_IMODE(after.st_mode)),
                 nlink=after.st_nlink, size=after.st_size,
                 mtime_ns=after.st_mtime_ns, ctime_ns=after.st_ctime_ns,bytes=after.st_size)
   need(all(r[k] == actual[k] for k in r if k not in ('path','sha256')), 'full actual transaction/raw record identity')
  return bytes(raw)
 finally:
  os.close(fd)

def parsed(raw):
 return json.loads(raw, object_pairs_hook=no_duplicates)
def checked(r, limit=4<<20):
 return parsed(checked_bytes(r,limit))
def compact(r):
 need(type(r) is dict and set(r)==COMPACT_FIELDS,'complete compact authority descriptor')
 need(type(r['path']) is str and Path(r['path']).is_absolute() and type(r['bytes']) is int and r['bytes']>=0,'compact descriptor path/length')
 need(type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'compact SHA256')
 return r

CURRENT_EXECUTION_REF=dict(path='/home/holden/mckernel-work/host-preparation/phase5-opt-in-production-link-image-independent-review-20261020-1/EXACT-SUCCESSOR-TWO-PHASE-CLEANUP-EXECUTION-REVIEW.json',sha256='7aacf3d2201fc3c59f01e017a8c68333d04259f90e36793435e90c8cb36b1ee0',bytes=375643)
CURRENT_EXECUTION_SCHEMA='mckernel.independent-current-image.successor-cleanup-exact-conditional-execution-review.v1'
CURRENT_EXECUTION_DECISION='PASS_EXACT_SUCCESSOR_READ_ONLY_PREFLIGHT_THEN_CONDITIONAL_CLEANUP_AND_POSTJOIN'

def execution_join(execution, execution_ref, release):
 """Two explicit existing kinds; current release uses exact reviewed body+inline."""
 compact(execution_ref)
 if execution['schema']==CURRENT_EXECUTION_SCHEMA:
  need(execution_ref==CURRENT_EXECUTION_REF,'exact complete current execution review descriptor')
  need(execution['status']=='PASS_EXECUTION' and execution['decision']==CURRENT_EXECUTION_DECISION and execution['implementation_ownership'] is False and execution['reviewer']=='/root/owned_offload_review' and execution['payload_author']=='/root','exact independent current successor execution tuple')
  payload=execution['cleanup_payload_without_execution_review']
  raw=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode()
  expected='cce1519420d4b306ec2dca51943c56660e667d2261a0c14bb9d23b840f0cc2d8'
  need(hashlib.sha256(raw).hexdigest()==expected==execution['reviewed_cleanup_payload_sha256'] and len(raw)==execution['reviewed_cleanup_payload_bytes']==256436,'whole reviewed current cleanup payload compact JSON plus LF')
  payload_ref=compact(execution['reviewed_payload_without_execution_review'])
  need(payload_ref['sha256']==expected and payload_ref['bytes']==256436 and checked_bytes(payload_ref)==raw,'full actual reviewed body descriptor and bytes')
  need(set(release)==set(payload)|{'execution_review'} and {k:v for k,v in release.items() if k!='execution_review'}==payload,'release differs from exact reviewed body only by execution_review')
  inline=execution['execution_review_inline_fields']
  need(set(inline)=={'evidence_sha256','implementation_ownership','reviewed_cleanup_payload_sha256','reviewer','status'} and inline['evidence_sha256']=='REPLACE_WITH_ACTUAL_SHA256_OF_THIS_REPORT_AFTER_WRITE','exact documented current inline slots')
  expected_inline=dict(inline,evidence_sha256=execution_ref['sha256'])
  need(release['execution_review']==expected_inline and expected_inline['status']=='PASS' and expected_inline['implementation_ownership'] is False and expected_inline['reviewed_cleanup_payload_sha256']==expected and expected_inline['reviewer']==execution['reviewer'],'exact actual full current inline review SHA and payload ownership')
  return payload['observation']['target']
 need(execution['schema']=='mckernel.independent-exact-terminal-cleanup-execution-review.v1' and execution['status']=='PASS' and execution['decision']=='PASS_EXACT_CURRENT_CONTAINER_JOURNALED_CLEANUP_AND_CONDITIONAL_POSTJOIN_ONLY' and execution['native_authorized'] is False and execution['implementation_ownership'] is False,'exact independent legacy terminal execution review')
 need(release['execution_review']['execution_review']==execution_ref and release['execution_review']['evidence_sha256']==execution_ref['sha256'],'full legacy cleanup execution authority descriptor')
 return execution['target']

def terminal_kind(t):
 need(t['schema']==SCHEMA and t['status']==t['decision']==STATUS,'exact existing cleanup physical kind')

def release_hash_join(engine, journal, release, current):
 # Source-defined internal canonical noLF hash and external file hash are
 # distinct authorities; checked(cleanup_release) already pins external bytes.
 expected=hashlib.sha256(json.dumps(release,sort_keys=True,separators=(',',':')).encode()).hexdigest() if current else None
 need(engine['release_sha256']==journal['release_sha256'] and (not current or engine['release_sha256']==expected),'actual canonical release/journal hash')

def absence_join(absent, expected_paths, current):
 need(absent['uid']==(0 if current else 1000) and absent['errno']=='ENOENT' and absent['paths']==expected_paths,'exact source-kind independent lease/quarantine/common/shared absence')

def project(t, physical_ref):
 """Project only the current independently released terminal transaction.

 Complete authority/transaction descriptors remain unchanged in t and are
 joined against actual bounded saved bytes. The returned eleven fields are
 the existing snapshot caller's interface, never a replacement report.
 """
 import io, tarfile
 need(t==checked(compact(physical_ref)),'whole independent terminal report')
 terminal_kind(t)
 current=t['execution_review']==CURRENT_EXECUTION_REF
 for k in ('physical_release','terminal','owned_groups_empty','root_mutex_available','container_absent','common_shared_records_absent'):
  need(t[k] is True,'positive terminal physical fact '+k)
 need(t['lease_retained'] is False and t['operation_status']=='PASS','actual lease release and cleanup success')
 for k in ('application_acceptance','native_acceptance','runtime_acceptance'):
  need(t[k] is False,'physical report carries no app/runtime credit '+k)
 need(t['implementation_ownership'] is False,'independent physical review')
 cleanup=checked(compact(t['actual_cleanup_status']))
 post=checked(compact(t['actual_postjoin_status']))
 if current:
  capture_fields={'argv','cpu7_released','direct_child_joined','elapsed_seconds','pid','proc_start_ticks','process_group_absent','returncode','status','stderr','stdout','streams_closed'}
  for label,row in (('cleanup',cleanup),('postjoin',post)):
   need(set(row)==capture_fields and row['status']=='PASS' and row['returncode']==0 and row['direct_child_joined'] is True and row['process_group_absent'] is True and row['streams_closed'] is True and row['cpu7_released'] is True,'actual current '+label+' closed capture contract')
   for key in ('stdout','stderr'):
    need(set(row[key])==STREAM_FIELDS,'complete current captured FD bytes identity')
    checked_bytes(row[key])
  need(cleanup['stderr']['bytes']==0 and cleanup['stderr']['sha256']==hashlib.sha256(b'').hexdigest(),'empty actual cleanup stderr')
  for stream,reference in ((cleanup['stdout'],t['raw_engine']),(post['stdout'],t['actual_postjoin_archive']),(post['stderr'],t['actual_postjoin_stderr'])):
   need(stream['sha256']==reference['sha256'] and stream['bytes']==reference['bytes'],'closed actual current stream/complete report authority bytes')
 else:
  for label,row in (('cleanup',cleanup),('postjoin',post)):
   need(row['returncode']==0 and row['direct_child_joined'] is True and row['process_group_absent'] is True and row['observer_error'] is None,'actual '+label+' direct/group retirement')
  need(cleanup['streams']['stderr']['metadata']['size']==0 and cleanup['streams']['stderr']['sha256']==hashlib.sha256(b'').hexdigest(),'empty actual cleanup stderr')
  for stream,reference in ((cleanup['streams']['stdout'],t['raw_engine']),(post['streams']['stdout'],t['actual_postjoin_archive']),(post['streams']['stderr'],t['actual_postjoin_stderr'])):
   need(stream['sha256']==reference['sha256'] and stream['metadata']['size']==reference['bytes'],'closed actual captured stream/complete report authority bytes')
 engine=checked(compact(t['raw_engine']))
 release=checked(compact(t['cleanup_release']))
 execution=checked(compact(t['execution_review']))
 normal=checked(compact(t['normal_postjoin_record']))
 need(engine['schema']=='fp-save-image.cleanup-result.v1' and engine['status']=='PASS_EXECUTED' and engine['terminal'] is True and engine['container_absent'] is True,'actual engine terminal success')
 need(release['schema']=='fp-save-image.cleanup-release.v1' and release['status']=='PASS_EXECUTION_RELEASE' and release['fetched_source_verified'] is True,'genuine source-bound cleanup execution release')
 execution_target=execution_join(execution,t['execution_review'],release)
 release_hash_join(engine,t['full_journal'],release,current)
 if not current:need(engine['release_sha256']==t['cleanup_release']['sha256'],'legacy external/internal identical release bytes')
 # The request is the only larger authority: read its actual complete closed
 # bytes once under64MiB; never copy it or traverse its build/toolchain inputs.
 compact(t['source_request'])
 obs=release['observation'];request_identity=obs['request']
 need(set(request_identity)==TRANSACTION_FIELDS,'full original request identity')
 need(request_identity['path']==t['source_request']['path'] and request_identity['sha256']==t['source_request']['sha256'] and request_identity['size']==t['source_request']['bytes'],'complete source request authority join')
 request=checked(request_identity,64<<20)
 target=obs['target']
 need(execution_target==target and target['container_id']==engine['container_id']==t['container_id'] and target['owner_nonce']==t['owner_nonce'],'actual cleanup target/CID/nonce')
 need(engine['boot_id']==t['boot_id']==obs['boot_id'] and engine['filesystem_uuid']==t['filesystem_uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52','actual boot and scratch UUID')
 ownership=t['ownership_archives'];archives=ownership['archives']
 need(ownership['count']==2 and len(archives)==2 and ownership['exact_original_device_inode_bytes_uid_gid_mode_nlink'] is True,'exact two full original ownership archives')
 need(all(set(row)==TRANSACTION_FIELDS for row in archives) and len({row['path'] for row in archives})==2,'known nine-field archive identities')
 need(engine['archives']==archives,'whole engine/report original archive rows')
 common=request['common_exclusion_path'];lease=request['lease_path']
 originals=ownership['original_paths'];shared='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'
 need(originals==[common,shared] and common!=shared and lease not in originals,'actual source-family common/shared/lease paths')
 # Saved TAR is read without extraction: exactly plan,journal,capture,two
 # archives, all regular unique basenames and exact complete9field rows.
 rawtar=checked_bytes(compact(t['actual_postjoin_archive']),32<<20)
 members=t['postjoin_members'];expected=[engine[k] for k in ('plan','journal','capture')]+archives
 need(len(members)==5 and [row['metadata'] for row in members]==expected,'all five full postjoin descriptors')
 saved={}
 with tarfile.open(fileobj=io.BytesIO(rawtar),mode='r:') as archive:
  actual=archive.getmembers()
  need(len(actual)==5 and len({m.name for m in actual})==5,'exact five unique TAR members')
  for member,row in zip(actual,members):
   descriptor=row['metadata'];need(set(descriptor)==TRANSACTION_FIELDS,'full nine-field TAR identity')
   need(member.isreg() and member.name==row['name']==Path(descriptor['path']).name and member.size==descriptor['size'],'exact regular postjoin member')
   data=archive.extractfile(member).read((4<<20)+1)
   need(len(data)==descriptor['size'] and hashlib.sha256(data).hexdigest()==descriptor['sha256'],'exact postjoin member bytes')
   need(checked_bytes(descriptor)==data,'actual retained member FD identity/bytes')
   saved[descriptor['path']]=data
 plan=parsed(saved[engine['plan']['path']])
 canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':')).encode()
 plan_sha=hashlib.sha256(canonical(plan)).hexdigest()
 need(saved[engine['plan']['path']]==canonical(plan)+b'\n' and plan_sha==engine['plan_sha256']==t['full_journal']['plan_canonical_sha256'],'whole exact canonical plan hash and stored newline')
 lines=saved[engine['journal']['path']].splitlines(keepends=True)
 events=[(event,index) for index in range(2) for event in ('before_exchange','after_exchange','release','after_release')]+[('complete',2)]
 need(len(lines)==len(events)==t['full_journal']['rows']==9 and t['full_journal']['chain_exact'] is True and t['full_journal']['complete_event'] is True,'exact nine-event completed journal')
 previous=plan_sha
 for sequence,(line,(event,index)) in enumerate(zip(lines,events)):
  row=parsed(line)
  need(set(row)=={'event','index','sequence','plan_sha256','previous','plan_identity','hash'},'exact journal row schema')
  body={k:row[k] for k in ('event','index','sequence','plan_sha256','previous','plan_identity')}
  need(body==dict(event=event,index=index,sequence=sequence,plan_sha256=plan_sha,previous=previous,plan_identity=[engine['plan']['device'],engine['plan']['inode']]),'ordered exact journal ownership chain')
  need(row['hash']==hashlib.sha256(canonical(body)).hexdigest() and line==canonical(row)+b'\n','canonical full journal hash and newline')
  previous=row['hash']
 need(plan['schema']=='fp-save-image.terminal-cleanup.v1' and plan['release_sha256']==engine['release_sha256'],'exact terminal plan schema/internal release')
 terminal=plan['terminal']
 need(type(terminal) is list and len(terminal)==4 and terminal[0]=='owner-receipt.json','exact producer terminal receipt tuple')
 terminal_rows=[row for row in obs['selected_files'] if [Path(row['path']).name,row['sha256'],row['inode'],row['size']]==terminal]
 need(len(terminal_rows)==1 and set(terminal_rows[0])==TRANSACTION_FIELDS,'unique complete selected terminal receipt identity')
 receipt=checked(terminal_rows[0])
 need(receipt['schema']=='mckernel.native-exact-mckernel-image-container-receipt.v1' and receipt['container_id']==target['container_id'] and receipt['container_name']==target['container_name'] and receipt['owner_nonce']==target['owner_nonce'],'actual selected terminal receipt kind and exact target identity')
 # Receipt status FAIL is retained image-build history. Current cleanup
 # retirement comes from the independently checked engine/report, not here.
 need(plan['container']==[target['container_id'],target['container_name'],target['owner_nonce']] and plan['owner']==[t['boot_id'],target['owner_pid'],target['owner_starttime']],'actual plan target/owner identity; no invented raw nonce')
 need(plan['filesystem_uuid']==t['filesystem_uuid'] and plan['publisher_contract']==engine['publisher_contract']==release['publisher_contract'],'same fixed publisher/transaction contract')
 root_lock=plan['root_lock'];need(set(root_lock)==TRANSACTION_FIELDS and root_lock['path']=='/run/lock/mckernel-development.lock' and root_lock['device']==27 and root_lock['inode']==4 and root_lock['uid']==root_lock['gid']==0 and root_lock['mode']=='0o644','preserved permanent root mutex identity')
 mutex_path=Path(release['transaction_paths'][0]);fd=os.open(mutex_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  mutex=os.fstat(fd);named=mutex_path.lstat()
  need(stat.S_ISREG(mutex.st_mode) and [mutex.st_dev,mutex.st_ino]==plan['mutex'] and mutex.st_nlink==1 and all(getattr(mutex,k)==getattr(named,k) for k in STAT_FIELDS),'transaction mutex preserved in place without unlink or lock mutation')
 finally:os.close(fd)
 need(len(plan['records'])==2,'exact plan ownership pair')
 for original,row,archive in zip(originals,plan['records'],archives):
  need(row==[original,str(Path(archive['path']).parent),Path(archive['path']).name,archive['sha256'],archive['inode'],archive['size']],'complete plan/original/archive assignment and order')
  value=parsed(saved[archive['path']])
  need(value['boot_id']==t['boot_id'] and value['pid']==target['owner_pid'] and value['starttime']==target['owner_starttime'] and value['inode']==archive['inode'],'actual original ownership record')
 need(parsed(saved[archives[0]['path']])['schema']=='mckernel.native-exact-operational-exclusion.v1' and parsed(saved[archives[1]['path']])['schema']=='mckernel.heavy-operation.v1','exact common/shared record kinds')
 absent=t['ordinary_exact_absence_check']
 expected_paths=[lease,release['transaction_paths'][4],common,shared]
 absence_join(absent,expected_paths,current)
 need(obs['request_lease_absent'] is True,'original request lease absent')
 if current:
  need(set(normal)=={'argv','direct_child_joined','elapsed_seconds','process_group_absent','returncode','stderr','stdout'} and normal['returncode']==0 and normal['direct_child_joined'] is True and normal['process_group_absent'] is True and normal['stderr']=='','closed current root normal proof wrapper')
  proof=normal['stdout'];arguments=parsed(normal['argv'][-1])
  need(proof['status']=='PASS_ACTUAL_NORMAL_POSTJOIN_PROCESS_MUTEX_AND_RELEASED_NAMES' and proof['boot_id']==arguments['boot']==t['boot_id'],'current root normal proof kind and boot')
  need(arguments['paths']==expected_paths and proof['released_names']==[dict(path=path,errno=2,absent=True) for path in expected_paths],'exact current four released names')
  pids=arguments['pids']
  need(len(pids)==len(set(pids))==14 and all(type(pid) is int and pid>0 for pid in pids) and proof['processes']==[dict(pid=pid,absent=True) for pid in pids] and {target['owner_pid'],cleanup['pid'],post['pid']}.issubset(pids),'actual full current14PID normal proof; owner/client groups remain separately checked')
  need(proof['root_lock']==dict(path='/run/lock/mckernel-development.lock',device=27,inode=4,acquired_and_released=True),'current permanent mutex acquired/released in place')
  corrected=checked(compact(t['corrected_postjoin_execution_review']))
  need(corrected['schema']=='mckernel.independent-current-image.corrected-read-only-postjoin-execution-review.v1' and corrected['status']=='PASS_EXECUTION' and corrected['decision']=='PASS_EXACT_DIAGNOSTIC_ONLY_POSTJOIN_CORRECTION_WITH_UNCHANGED_ACCEPTANCE_PREDICATES' and corrected['implementation_ownership'] is False,'exact corrected read-only postjoin authority kind')
  need(corrected['actual_cleanup_release']==t['cleanup_release'] and corrected['actual_cleanup_result']==t['raw_engine'] and corrected['source']==t['corrected_postjoin_source'] and corrected['argv']==post['argv'],'whole corrected postjoin release/result/source/actual argv roles')
  need(all(corrected[k] is False for k in ('cleanup_replay_authorized','physical_release','native_acceptance','next_heavy_authorized')),'corrected reader grants no cleanup replay/runtime authority')
  checked_bytes(compact(t['corrected_postjoin_source']))
 else:
  need(normal['status']=='PASS_ORDINARY_POSTJOIN_PROCESS_GROUP_MUTEX_AND_TWO_RECORD_ABSENCE' and normal['owner_nonce_from_bound_plan']==t['owner_nonce'] and normal['boot_id']==t['boot_id'] and normal['plan_sha256']==engine['plan']['sha256'],'normal independent postjoin identity')
  need(normal['absent_records']==originals and normal['mutex_nonblocking_acquired_and_released'] is True and normal['mutex']['device']==27 and normal['mutex']['inode']==4,'actual original record absence and permanent mutex')
  need(len(normal['processes'])==2 and [row['role'] for row in normal['processes']]==['cleanup','postjoin'] and all(row['group_absent'] is True and row['original_process_absent'] is True for row in normal['processes']),'actual cleanup/postjoin process retirement')
 for path in absent['paths']:need(not os.path.lexists(path),'released path currently absent')
 postreader=checked(compact(t['actual_postjoin_stderr']))
 need(postreader['status']=='PASS_CLEANUP_POSTJOIN_READBACK_ONLY' and postreader['members']==5 and postreader['application_acceptance'] is False,'saved positive postjoin readback only')
 # Fixed current transaction inventories are compared as descriptors only;
 # do not rehash build images, toolchains or the protected preservation set.
 need(len(obs['selected_files'])==58 and len(obs['inventories'])==2 and sorted(len(rows) for rows in obs['inventories'].values())==[4,570],'current selected58/twoinventory roots4and570 source contract')
 need(len(postreader['actual_object_rows'])==52 and all(set(row)==TRANSACTION_FIELDS for row in postreader['actual_object_rows']),'actual current52postreader full nine-field protocol; no invented timestamps')
 selected={row['path']:row for row in obs['selected_files']}
 need(len(selected)==58 and len({row['path'] for row in postreader['actual_object_rows']})==52 and all(row==selected.get(row['path']) for row in postreader['actual_object_rows']),'unique actual52 subset of source-bound58 full descriptors')
 need(t['preservation']['all_rows_exact_pre_cleanup'] is True,'independent exact preservation finding')
 # Preserve the actual descriptor and all authority roles; these are the
 # existing snapshot interface fields, not a shortened report descriptor.
 return dict(boot_id=t['boot_id'],filesystem_uuid=t['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['owner_nonce'],lease_path=lease,common_exclusion=common,shared_heavy=shared)
