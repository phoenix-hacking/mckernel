"""Exact failed-operation preservation gate; never grants root/cleanup authority."""
from pathlib import Path
import hashlib,json,os,stat
SCHEMA='mckernel.independent-rust-image-failed-build-preservation-authority.v1'
DECISION='PASS_FAILED_BUILD_LOG_RETENTION_AND_TERMINAL_BINDINGS_ONLY'
N=Path(__file__).resolve().parents[2]
OWNER_SHA='a6581507617e25886628ae324cf617c5c7c2c3b83308ff0518780f9a6150d442'
REVIEW_SHA='def58a4fcc50a63f2da763f6655eab47ca2614e4ade959153c853d15f07090e4'
MUTEX_SHA='58cd06564cf0936a2f345de30e48b7ad964a416baf3b85cd4f3ce3478d825f2c'
CID='dadedd81537c2121aad6ac8fc1141c4612857c22b0314f5cc67205b05dd1c08f'

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
 need(authority['owner_receipt']['sha256']==OWNER_SHA and authority['current_retirement_review']['sha256']==REVIEW_SHA and authority['mutex_postjoin']['sha256']==MUTEX_SHA,'exact current failed operation refs')
 owner=verify(authority['owner_receipt'],True);guard=verify(authority['guard_result'],True);review=verify(authority['current_retirement_review'],True);post=verify(authority['mutex_postjoin'],True)
 need(owner['status']=='FAIL' and owner['exit_code']==1 and owner['retired'] is True and owner['terminal_container_retained'] is True and owner['container_id']==CID,'exact retired failed owner')
 need(guard==dict(owner_status='FAIL',owner_receipt_sha256=OWNER_SHA,container_id=CID,retired=True,retained_for_separate_cleanup=True,interrupted_signal=None),'exact failed guard RESULT')
 need(review['decision']=='PASS_POSITIVE_CLIENT_OWNER_GUARD_RETIREMENT_WITH_FAILED_PRODUCER' and review['container_id']==CID and review['cleanup_authority'] is False,'current positive client retirement')
 need(post['schema']=='mckernel.failed-build.ordinary-postjoin-mutex-readback.v1' and post['status']=='PASS_FAILURE_POSTJOIN_MUTEX_REACQUIRED' and post['root27_4_reacquired_after_join'] is True and post['cleanup_authority'] is False and post['physical_release'] is False and post['container_id']==CID and post['lease_absent'] is True,'real alternative failure mutex join')
 source=authority['source11'];need(source['count']==11 and source['host_owner']==str(N/'adapters/native_rust_exact_build_container_owner.py'),'source11 host owner scalar')
 source_wrapper=verify(source['source11ref'],True);source_map=source_wrapper['source_sha256'];need(len(source_map)==11 and source['host_owner'] in source_map,'actual source11 closure')
 gs=authority['guard_source'];need(gs['path'] in source_map and source_map[gs['path']]==gs['sha256'] and gs['path']!=authority['guard_result']['path'],'guard SOURCE distinct from guard RESULT')
 for path,sha in source_map.items():verify(dict(path=path,sha256=sha))
 need(source['additional_dispatcher']==source_wrapper['additional_dispatcher'],'actual additional dispatcher')
 for key in ('request','provenance','materialization','fullsource','additional_dispatcher','toolchain'):verify(source[key])
 request=verify(source['request'],True);need(request['host_owner_path']==source['host_owner'] and request['host_owner_sha256']==source_map[source['host_owner']],'actual request host owner digest')
 need(source['request']['path']==str(N/'image-request.json') and source['request']['sha256']=='e9497da4204aed95708bb0f2ceb062a88c45517c13e3c69e65510fb59334cec0','actual failed request')
 logs=authority['retained_logs'];pairs=verify(logs['pairs'],True);release=verify(logs['release'],True);result=verify(logs['result'],True);joined=verify(logs['direct_join'],True)
 rows=verify(authority['original_log_authorities'],True);need(len(rows)==len(pairs)==11 and all(r['action']=='copy' for r in rows),'exact eleven copy-only failed logs')
 expected={(r['original']['path'],r['retained']) for r in rows};need({(p['original']['path'],p['retained']['path']) for p in pairs}==expected,'exact failed log paths')
 for pair in pairs:
  a,b=pair['original'],pair['retained'];need(pair['outside_generic_receipt_inventory'] is True and a['sha256']==b['sha256'] and a['size']==b['size'] and a['nlink']==b['nlink']==1 and (a['device'],a['inode'])!=(b['device'],b['inode']),'independent samebyte failed log pair')
  verify(a);verify(b)
 need(release['status']=='PASS_EXECUTION_RELEASE' and result['status']=='PASS_FINITE_EXACT_RETENTION_ONLY' and result['artifact_acceptance'] is False and result['cleanup_authorized'] is False and result['source_release_sha256']==logs['release']['sha256'],'actual failed-log retention result')
 need(joined['returncode']==0 and joined['direct_child_joined'] is True,'actual ordinary retention direct join')
 expected_dirs=[str(N/'owner-work/output/build'),str(N/'owner-work/evidence')];need(authority['required_preserved_directories']==expected_dirs,'in-place partial build preservation')
 need(authority['ownership']['lease_absent'] is True and authority['target']['container_id']==CID,'current retained failure ownership')
 return authority
