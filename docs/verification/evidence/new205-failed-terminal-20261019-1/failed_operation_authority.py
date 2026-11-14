"""Exact failed-operation preservation gate; never grants root/cleanup authority."""
from pathlib import Path
import hashlib,json,os,stat
SCHEMA='mckernel.independent-rust-image-failed-build-preservation-authority.v1'
DECISION='PASS_FAILED_BUILD_LOG_RETENTION_AND_TERMINAL_BINDINGS_ONLY'
N=Path(__file__).resolve().parent.parent
OWNER_SHA = '23de50fbe9d21cbbb16edfe0cafc270f635b6aa4298a8901f720d511ce235771'
REVIEW_SHA = 'a55469e628dbec12ffefcec85f18770d89aa1a8383d3fb7d7104fbc4a9e1a8dc'
CID = '6f490dad40bf7de8e293762c9933bc444db19ecf01c1c57be6bd390d2da7dc5c'

def need(ok,why):
 if not ok:raise RuntimeError('failed-preservation:'+why)
def verify(ref,parse=False):
 p=Path(ref['path']);need(p.is_absolute() and p.resolve()==p,'exact source path');fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<128<<20,'bounded regular source')
  h=hashlib.sha256();parts=[]
  with os.fdopen(os.dup(fd),'rb') as f:
   for block in iter(lambda:f.read(65536),b''):h.update(block);parts.append(block) if parse else None
  after=os.fstat(fd);named=p.lstat();represented=dict(device=before.st_dev,inode=before.st_ino,uid=before.st_uid,gid=before.st_gid,nlink=before.st_nlink,size=before.st_size,mtime_ns=before.st_mtime_ns,ctime_ns=before.st_ctime_ns)
  for key,value in represented.items():
   if key in ref:need(ref[key]==value,'represented FD '+key)
  if 'mode' in ref:need((int(ref['mode'],8) if isinstance(ref['mode'],str) else ref['mode'])==stat.S_IMODE(before.st_mode),'represented FD mode')
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')),'source FD stability');need(h.hexdigest()==ref['sha256'],'exact source hash')
  return json.loads(b''.join(parts)) if parse else True
 finally:os.close(fd)

def validate_failure_authority(authority):
 need(authority.get('schema')==SCHEMA and authority.get('decision')==DECISION,'dedicated literal authority')
 for flag in ('production_image_acceptance','native_acceptance','compute_C_retirement','cleanup_authorized','physical_release'):need(authority.get(flag) is False,'no acceptance/release '+flag)
 need(authority.get('implementation_ownership') is False and authority.get('reviewer') and authority['reviewer']!=authority.get('implementation_author'),'independent preservation reviewer')
 need(authority['owner_receipt']['sha256']==OWNER_SHA and authority['current_retirement_review']['sha256']==REVIEW_SHA,'exact current failed operation refs')
 owner=verify(authority['owner_receipt'],True);guard=verify(authority['guard_result'],True);review=verify(authority['current_retirement_review'],True)
 need(owner['status']=='FAIL' and owner['exit_code']==1 and owner['retired'] is True and owner['terminal_container_retained'] is True and owner['container_id']==CID,'exact retired failed owner')
 need(guard==dict(owner_status='FAIL',owner_receipt_sha256=OWNER_SHA,container_id=CID,retired=True,retained_for_separate_cleanup=True,interrupted_signal=None),'exact failed guard RESULT')
 validate_retirement_evidence(authority['current_retirement_review'])
 source=authority['source11'];need(source['count']==11 and source['host_owner']==str(N/'adapters/native_rust_exact_build_container_owner.py'),'source11 host owner scalar')
 source_wrapper=verify(source['source11ref'],True);source_map=source_wrapper['source_sha256'];need(len(source_map)==11 and source['host_owner'] in source_map,'actual source11 closure')
 gs=authority['guard_source'];need(gs['path'] in source_map and source_map[gs['path']]==gs['sha256'] and gs['path']!=authority['guard_result']['path'],'guard SOURCE distinct from guard RESULT')
 for path,sha in source_map.items():verify(dict(path=path,sha256=sha))
 need(source['additional_dispatcher']==source_wrapper['additional_dispatcher'],'actual additional dispatcher')
 verify(source['additional_dispatcher'])
 actual=dict(source_map);additional=source['additional_dispatcher'];need(additional['path'] not in actual,'additional dispatcher distinct');actual[additional['path']]=additional['sha256']
 need(len(actual)==12 and authority['actual_control_source12']==actual,'exact source11 plus actual additional dispatcher')
 for key in ('request','provenance','materialization','fullsource','additional_dispatcher','toolchain'):verify(source[key])
 request=verify(source['request'],True);need(request['host_owner_path']==source['host_owner'] and request['host_owner_sha256']==source_map[source['host_owner']],'actual request host owner digest')
 need(source['request']['path']==str(N/'image-request.json') and source['request']['sha256']=='902f482227f3510c86a2624fa9f255abb3d0c82996191f4e3ca4c227877765f8','actual failed request')
 logs=authority['retained_logs'];pairs=verify(logs['pairs'],True);release=verify(logs['release'],True);result=verify(logs['result'],True);joined=verify(logs['direct_join'],True)
 rows=verify(authority['original_log_authorities'],True);need(len(rows)==len(pairs)==12 and all(r['action']=='copy' for r in rows),'exact twelve copy-only failed logs')
 expected={(r['original']['path'],r['retained']) for r in rows};need({(p['original']['path'],p['retained']['path']) for p in pairs}==expected,'exact failed log paths')
 for pair in pairs:
  a,b=pair['original'],pair['retained'];need(pair['outside_generic_receipt_inventory'] is True and a['sha256']==b['sha256'] and a['size']==b['size'] and a['nlink']==b['nlink']==1 and (a['device'],a['inode'])!=(b['device'],b['inode']),'independent samebyte failed log pair')
  verify(a);verify(b)
 need(release['status']=='PASS_EXECUTION_RELEASE' and result['status']=='PASS_FINITE_EXACT_RETENTION_ONLY' and result['artifact_acceptance'] is False and result['cleanup_authorized'] is False and result['source_release_sha256']==logs['release']['sha256'],'actual failed-log retention result')
 need(joined['returncode']==0 and joined['direct_child_joined'] is True,'actual ordinary retention direct join')
 expected_dirs=[str(N/'owner-work/output/build'),str(N/'owner-work/evidence')];need(authority['required_preserved_directories']==expected_dirs,'in-place partial build preservation')
 need(authority['ownership']['lease_absent'] is True and authority['target']['container_id']==CID,'current retained failure ownership')
 return authority

def validate_retirement_evidence(reference):
 need(reference['sha256']==REVIEW_SHA,'fixed actual independent retirement review')
 review=verify(reference,True)
 need(review['schema']=='mckernel.independent-new205-failed-producer-and-client-retirement-review.v1' and review['status']=='PASS' and review['decision']=='PASS_ACTUAL_FAILED_PRODUCER_CLASSIFICATION_AND_POSITIVE_CLIENT_RETIREMENT_ONLY','typed actual failure retirement decision')
 need(review['implementation_ownership'] is False and review['positive_client_retirement'] is True and review['client_count']==8 and review['container_id']==CID,'actual eight client retirement')
 for flag in ('physical_retirement_accepted','producer_accepted_as_success','production_artifact_acceptance','native_acceptance'):need(review[flag] is False,'no release/acceptance '+flag)
 need(review['producer_status']=='FAIL' and review['successful_prefix_count']==9,'actual failed producer phase classification')
 need(review['owner_receipt']['sha256']==OWNER_SHA,'actual owner receipt binding')
 owner=verify(review['owner_receipt'],True);guard=verify(review['guard_result'],True)
 need(owner['status']=='FAIL' and owner['exit_code']==1 and owner['retired'] is True and owner['terminal_container_retained'] is True and owner['container_id']==CID,'actual failed stopped owner')
 need(guard==dict(owner_status='FAIL',owner_receipt_sha256=OWNER_SHA,container_id=CID,retired=True,retained_for_separate_cleanup=True,interrupted_signal=None),'actual failed guard result')
 for role in ('guard_status','outer_status'):
  status=verify(review[role],True)
  need(status['returncode']==1 and status['direct_child_joined'] is True,'actual closed '+role)
 need(len(review['clients'])==8,'all eight client evidence rows retained')
 mutex=verify(dict(path=str(N/'heavy-proposal-1/failure-mutex-postjoin-readback-1.json'),sha256='48436d2f7a3eee5c65fc6622feaaf0bafaa889033628e2bfb9507df12139305d'),True)
 need(mutex['schema']=='mckernel.failed-image.ordinary-postjoin-mutex-readback.v1' and mutex['status']=='PASS_ORDINARY_FAILED_GUARD_MUTEX_POSTJOIN_ONLY','genuine current failure mutex postjoin')
 need(mutex['root27_4_reacquired_after_join'] is True and mutex['guard_direct_joined'] is True and mutex['guard_returncode']==1,'mutex acquired after failed guard direct join')
 need(mutex['cleanup_authorized'] is False and mutex['physical_release'] is False and mutex['container_or_records_reobserved'] is False,'mutex-only observation authority')
 need(mutex['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mutex actual boot')
 lock=mutex['root_lock'];need((lock['device'],lock['inode'],lock['uid'],lock['gid'],stat.S_IMODE(int(lock['mode'],8)),lock['nlink'],lock['size'])==(27,4,0,0,0o644,1,0),'exact persistent root mutex identity')
 need(mutex['root_lock_sha256']==hashlib.sha256(b'').hexdigest(),'empty persistent root mutex bytes')
 for role in ('guard_status','outer_status'):
  need(all(mutex[role][key]==review[role][key] for key in ('path','sha256')),'mutex same actual '+role)
 return review

