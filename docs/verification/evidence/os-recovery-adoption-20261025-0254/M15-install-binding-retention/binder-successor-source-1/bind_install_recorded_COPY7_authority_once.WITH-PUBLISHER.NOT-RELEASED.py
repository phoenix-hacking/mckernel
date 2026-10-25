"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source/data binding only. No query/owner/compiler/subprocess imports or execution.
"""
from pathlib import Path
import ast,hashlib,json,os,re,stat,sys
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
ROOT='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1'
OUTPUT='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/binder-successor-source-1/actual-copy7-late-bound-1'
SOURCES = {'query': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/admission-preparation-1/run_root_sdk_readonly_admission.PHYSICAL-PENDING.py', 'sha256': '9e1553c4740e31b2dcfb5d02977724c5cf39415370ed94d2f6348b0ea0e945c7', 'bytes': 39070}, 'fill': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/fill_install_runtime_review_payload.PHYSICAL-SOURCEPROOF-PENDING.py', 'sha256': '9da7aff68b3bc1d16358a6ff8c5a72eeab8ac94b4d15c88fd49db978c3f521a8', 'bytes': 16556}, 'request': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/REQUEST.ROOT.FINAL.json', 'sha256': '74def32a434f42ddeb3abd90ca5c728d43696262fdf387fd4059575533775fea', 'bytes': 3914}, 'source_map': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json', 'sha256': '6b2ed04a5d0c676dea2f6cea8cb1275ca13cc303ea2a6f3e0d4bb71ef491b7b6', 'bytes': 3406}, 'ready': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/READY.SDK-INSTALL-OWNER-FOUR-PHASES.SOURCE-ONLY.NOT-RELEASED.json', 'sha256': 'ff783ff1eb81291dbd9429d96f3349817f9510fa6ad2d6c2ac5730e37401659a', 'bytes': 9068}, 'capture': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/admission-preparation-1/capture_root_sdk_readonly_admission_once.py', 'sha256': '5d625437e6904e95cf0c30447cc00fff283380d8d1222066d6cbaea0e6511dd4', 'bytes': 1742}, 'inputs': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/admission-preparation-1/QUERY-INPUTS.ROOT.json', 'sha256': '7ec2eb38bc13b0d28bfbffb3f2857759dafb0dddc8053a4877809c8f9b25b1a6', 'bytes': 319}, 'entry': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/ROOT-OWNER-ENTRY.PENDING.json', 'sha256': '634e33d5ee4d413d851781426fbef047ef3d53ca9676b7749e12f12d926981d0', 'bytes': 1540}, 'publisher_template': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/selected-source-1/publication-admission-preparation-1/late-current-physical-overlay-preparation-1/actual-copy2-current-binding-1/publish_copy2_current_overlay_once.NOT-GRANTED.py', 'sha256': '95f4c0caad32de7043ff6575eada40d2f8f1d463f32484e93b88507796f7d840', 'bytes': 3546}}
PUBLISHED_SOURCE_PROOF={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/ROOT-FETCHED-INSTALL-FIFTEEN-SOURCE-PROOF.json', 'sha256': '56a3071f0ee22df3ba4936da19f6d620d2bf861914bdb30821905ee300506fed', 'bytes': 2019}
def need(v,m):
 if not v:raise ValueError(m)

def digest(b):return hashlib.sha256(b).hexdigest()

def read(ref):
 p=Path(ref['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'regular singlelink source/data input')
  blocks=[];size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   size+=len(block);need(size<=32<<20,'bounded source/data input');blocks.append(block)
  raw=b''.join(blocks);after=os.fstat(fd);named=p.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS) and size==after.st_size,'stable9 source/data identity (atime excluded)')
  need(digest(raw)==ref['sha256'] and len(raw)==ref['bytes'],'source/data pin '+str(p));return raw
 finally:os.close(fd)

def publish(path,raw,mode=0o600):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(fd)
 finally:os.close(fd)
 parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(parent)
 finally:os.close(parent)
 return dict(path=str(path),sha256=digest(raw),bytes=len(raw))

def data_ref(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=digest(raw),bytes=len(raw))
def write(path,value):
 raw=value.encode() if isinstance(value,str) else (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 return publish(path,raw)
def assign(source,values):
 lines=source.splitlines(True)
 for node in reversed(ast.parse(source).body):
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   lines[node.lineno-1:node.end_lineno]=[node.targets[0].id+' = '+values[node.targets[0].id]+'\n']
 return ''.join(lines)
COPY7_AUTHORITY={'physical_acceptance': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'bytes': 1657, 'sha256': 'dda45e6348748469bb15734ff585733b5a18c405f907f82e9e9e0f9c4c1e0129'}, 'current_postjoin': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/CURRENT-LIVE-POSTJOIN.json', 'bytes': 3918, 'sha256': 'f37ff2d1507d6cacd69c76ca0749c91b44b8b5783dd5b3716ff775f80375393f'}, 'normal_retirement': {'bytes': 369056, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/actual-normal-cleanup-1/stdout', 'sha256': 'eef16afae29dd5441d393c22c9010ffa49a698e1eb371f81577a52c4df0eba4e'}}

def require_copy7_identity(ph, post, normal):
 need(ph['schema']=='mckernel.copy7.normal-retirement.physical-acceptance.v1' and ph['status']=='PASS_ACTUAL_M14_COPY7_NORMAL_FAILED_IMAGE_PHYSICAL_RETIREMENT' and ph['reviewer']=='/root/recovery_review', 'exact current COPY7 independent reviewer/schema/status')
 need(post['schema']=='mckernel.current-live-postjoin.v1' and post['reviewer']=='/root/recovery_review' and post['implementation_ownership'] is False,'genuine independently accepted current postjoin')
 need(ph['cleanup_pid']==post['cleanup_pid']==473751 and ph['cleanup_starttime']==post['cleanup_starttime']=='69456080' and ph['reported_parent_pid']==post['reported_parent_pid']==473748,'exact actual COPY7 cleanup identities')
 need(ph['container_id']==post['container_id']==normal['container_id'] and ph['closed_nonce']=='76b2af948f3440219ad33c013fc3fbcb' and ph['boot_id']==post['boot_id']==normal['boot_id'],'exact COPY7 container/nonce/boot binding')
 need(ph['consumed_cleanup_release_sha256']==post['consumed_cleanup_release']['sha256'],'actual consumed cleanup release raw-file binding')
 consumed_release=json.loads(read(post['consumed_cleanup_release']))
 need(normal['release_sha256']==digest(json.dumps(consumed_release,sort_keys=True,separators=(',',':')).encode()),'actual consumed cleanup release canonical binding')
 need(ph['journal_events']==9 and ph['preserved_selected_files']==71 and ph['preserved_inventory_rows']==617,'actual accepted COPY7 preservation counts')
 need(ph['owner_pid']==413643 and ph['owner_starttime']=='68359948' and
      post['owner_pid']==413643 and post['owner_starttime']=='68359948',
      'exact COPY7 owner/birth required; historical COPY6 cannot clear COPY7')
 need(normal['schema']=='fp-save-image.cleanup-result.v1' and
      normal['terminal'] is True and normal['container_absent'] is True and
      normal['container_id']=='0e41e2cf1f390c77108eafef7d031a1d1e561485a38ed7524f77d953e0c62d70' and
      normal['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',
      'exact COPY7 normal retirement result required')

def main():
 need(os.getuid()==os.geteuid()==os.getgid()==1000,'ordinary source binding UID')
 need(len(sys.argv)==5 and sys.argv[1]=='--bind-current-authority' and sys.argv[4]==digest(Path(__file__).read_bytes()),'exact sourcebound binding argv')
 raw=Path(sys.argv[2]).read_bytes();need(digest(raw)==sys.argv[3],'exact actual authority data')
 packet=json.loads(raw);need(set(packet)=={'physical_acceptance','current_postjoin','normal_retirement','source_approval','fetched_source_proof'},'finite binding schema')
 need(all(isinstance(packet[k],dict) and set(packet[k])=={'path','sha256','bytes'} for k in packet),'all genuine references required before effects')
 need(packet['fetched_source_proof']==PUBLISHED_SOURCE_PROOF,'exact fetched15 source proof')
 need(all(packet[k]==v for k,v in COPY7_AUTHORITY.items()),'exact recorded COPY7 authority descriptors')
 rows={k:json.loads(read(v)) for k,v in packet.items()};ph=rows['physical_acceptance'];post=rows['current_postjoin'];normal=rows['normal_retirement'];approval=rows['source_approval'];fetched=rows['fetched_source_proof']
 require_copy7_identity(ph,post,normal)
 need(ph['reviewer']=='/root/recovery_review' and ph['implementation_ownership'] is False and post['status']=='ACCEPTED_NON_NULL' and post['independent_physical']==packet['physical_acceptance'],'independent positive physical authority')
 need(ph['status'].startswith('PASS_ACTUAL_M14_') and ph['original_workload_status']=='FAIL' and ph['artifact_native_acceptance'] is False,'exact failed M14 retirement scope')
 need(ph['client_births'] is None and ph['host_init_identity'] is None and 'historical_outer_identity' not in ph,'explicit actual COPY7 qualifications')
 need(post['status']=='ACCEPTED_NON_NULL' and post['independent_physical']==packet['physical_acceptance'] and post['native_acceptance'] is False and post['original_workload_status']=='FAIL','actual nonNULL postjoin schema')
 need(ph['normal_result_sha256']==packet['normal_retirement']['sha256'] and normal['status']=='PASS_EXECUTED','bound genuine normal result')
 need(post['owner_pid']==ph['owner_pid'] and post['owner_starttime']==ph['owner_starttime'] and post['cleanup_pid']==ph['cleanup_pid'],'postjoin exact owner/cleanup')
 need(type(ph['owner_pid']) is int and ph['owner_pid']>1 and type(ph['cleanup_pid']) is int and ph['cleanup_pid']>1 and ph['owner_starttime'].isdigit() and ph['cleanup_starttime'].isdigit(),'positive actual owner/births')
 joins={'proc':post['proc_whole_join'],'mutex':post['mutex_whole_join']};need(ph['proc_whole_join_sha256']==joins['proc']['sha256'] and ph['mutex_whole_join_sha256']==joins['mutex']['sha256'],'exact physical join hashes')
 nine=[packet['physical_acceptance'],packet['current_postjoin'],packet['normal_retirement'],joins['proc'],joins['mutex']]
 for logical,row in joins.items():
  join=json.loads(read(row));need(join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams'] and join['error'] is None and join['retirement_error'] is None and not join['timed_out'],'positive closed observation join')
  for stream in ('stdout','stderr'):
   item=join['captures'][stream];streamref=dict(path=item['path'],sha256=item['sha256'],bytes=item.get('size',item.get('bytes')));data=read(streamref)
   if stream=='stderr':need(len(data)==0,'no observation stderr')
   nine.append(streamref)
 need(len(nine)==9,'finite nine authority files')
 runtime=Path(ROOT);query=read(SOURCES['query']).decode();fill=read(SOURCES['fill']).decode();request=json.loads(read(SOURCES['request']));source_map=json.loads(read(SOURCES['source_map']))
 need(approval['decision']=='PASS_SOURCE' and approval['implementation_ownership'] is False and approval['source_sha256']==source_map['source_sha256'] and approval['reviewed_ready_sha256']==SOURCES['ready']['sha256'],'exact current runtime source approval')
 need(fetched['status']=='PASS_ACTUAL_FETCHED_SOURCE_BLOBS' and fetched['archive_exact_members']==15 and fetched['commit']=='84524a8237bed8030d9bf0d111bd02e261fcaff9','actual source15 proof schema')
 # Query/function algorithms unchanged; bind actual typed authority literals only.
 query=query.replace("assert False, 'INSTALL QUERY TEMPLATE ONLY: new accepted physical9 required'\n",'')
 values={'EXPECTED_CURRENT_PHYSICAL_STATUS':repr(ph['status']),'EXPECTED_OWNER_PID':repr(ph['owner_pid']),'EXPECTED_OWNER_START':repr(ph['owner_starttime']),'EXPECTED_CLEANUP_PID':repr(ph['cleanup_pid']),'EXPECTED_CLEANUP_START':repr(ph['cleanup_starttime']),'current_normal_cfg_physical':repr(packet['physical_acceptance']),'current_normal_cfg_postjoin':repr(packet['current_postjoin']),'normal_cfg_normal_ref':repr(packet['normal_retirement']),'normal_cfg_links':repr(joins)}
 query=assign(query,values)
 # Update only the current COPY7 reviewer assertion. Historical reviewer bytes remain exact.
 old_reviewer="normal_cfg['implementation_ownership'] is False and normal_cfg['reviewer']=='/root/native235_release_review'"
 new_reviewer="normal_cfg['implementation_ownership'] is False and normal_cfg['reviewer']=='/root/recovery_review'"
 need(query.count(old_reviewer)==1, 'one exact current reviewer assertion required')
 query=query.replace(old_reviewer,new_reviewer)
 current_boolean="normal_cfg['current_live_postjoin_accepted_non_null'] is True"
 current_actual="normal_cfg['schema']=='mckernel.copy7.normal-retirement.physical-acceptance.v1' and normal_cfg_live['status']=='ACCEPTED_NON_NULL' and normal_cfg_live['independent_physical']==current_normal_cfg_physical"
 need(query.count(current_boolean)==1,'one exact predecessor current acceptance boolean')
 query=query.replace(current_boolean,current_actual)
 replacements={"normal_cfg['client_births'] is None and normal_cfg['historical_outer_identity'] is None and normal_cfg['host_init_identity'] is None":"normal_cfg['client_births'] is None and 'historical_outer_identity' not in normal_cfg and normal_cfg['host_init_identity'] is None", "normal_cfg_live['physical_acceptance']==current_normal_cfg_physical":"normal_cfg_live['independent_physical']==current_normal_cfg_physical", "normal_cfg_live['actual_cleanup']==normal_cfg_normal_ref and normal_cfg_live['current_live_postjoin']==normal_cfg_links":"normal_cfg_live['proc_whole_join']==normal_cfg_links['proc'] and normal_cfg_live['mutex_whole_join']==normal_cfg_links['mutex']", "normal_cfg_live['artifact_native_acceptance']":"normal_cfg_live['native_acceptance']"}
 for old,new in replacements.items():need(old in query,'exact schema predecessor '+old);query=query.replace(old,new)
 mount=request['libdwarf_mountpoint_identity'];need(repr(mount) in query and mount['path'] in query,'current request path+node exact literal')
 ast.parse(query);need('assert False' not in query,'no pending query literal')
 out=Path(OUTPUT);need(not out.exists(),'exclusive late binding namespace');out.mkdir(mode=0o700);A=out/'admission-preparation-1';A.mkdir(mode=0o700)
 qr=write(A/'run_root_sdk_readonly_admission.py',query);cap=write(A/'capture_root_sdk_readonly_admission_once.py',read(SOURCES['capture']).decode());inputs=write(A/'QUERY-INPUTS.ROOT.json',json.loads(read(SOURCES['inputs'])));entry=write(out/'ROOT-OWNER-ENTRY.PENDING.json',json.loads(read(SOURCES['entry'])))
 oldpins=ast.literal_eval(next(n.value for n in ast.parse(fill).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets)));pins={k:v for k,v in oldpins.items() if k not in [SOURCES['capture']['path'],SOURCES['inputs']['path'],SOURCES['entry']['path']]};pins.update({x['path']:x['sha256'] for x in [qr,cap,inputs,entry,packet['physical_acceptance'],packet['current_postjoin'],packet['source_approval']]})
 fill=fill.replace("assert False, 'SOURCE TEMPLATE ONLY: actual new physical + final query + fetched current overlay bindings required'\n",'')
 fill=assign(fill,{'PINS':repr(pins),'P':'Path('+repr(str(out))+')','A':'Path('+repr(str(A))+')','PHYSICAL_PATH':'Path('+repr(packet['physical_acceptance']['path'])+')','POSTJOIN_PATH':'Path('+repr(packet['current_postjoin']['path'])+')','SOURCE_APPROVAL_PATH':'Path('+repr(packet['source_approval']['path'])+')','FETCHED_COMMIT':repr(fetched['commit'])})
 fill=fill.replace('PASS_ACTUAL_M14_RETAINED_NORMAL_FAILED_IMAGE_PHYSICAL_RETIREMENT',ph['status']).replace("postjoin['physical_acceptance']['sha256']","postjoin['independent_physical']['sha256']").replace("postjoin['artifact_native_acceptance']","postjoin['native_acceptance']")
 fill=fill.replace(str(runtime/'ROOT-FETCHED-INSTALL-RUNTIME-SOURCE-PROOF.json'),PUBLISHED_SOURCE_PROOF['path']).replace("assert fetched['status']=='PASS_FETCHED_SELECTED_SDK_INSTALL_RUNTIME_SOURCE'","assert fetched['status']=='PASS_ACTUAL_FETCHED_SOURCE_BLOBS'").replace("assert fetched['archive_members_verified']==15","assert fetched['archive_exact_members']==15").replace("fetched['retained_base18and66_proof']","fetched['base_source_proofs']").replace("assert FETCHED_COMMIT is not None and fetched['commit']==fetched['fetched_commit']==FETCHED_COMMIT","assert fetched['commit']==FETCHED_COMMIT and expected_fetch_sha=="+repr(PUBLISHED_SOURCE_PROOF['sha256']))
 anchor="if sys.argv[1]=='--prepare-review-payload':\n    assert not E.exists() and not payload_path.exists()"
 check="CURRENT_OVERLAY_FETCHED_PROOF=None\nassert CURRENT_OVERLAY_FETCHED_PROOF is not None, 'genuine fetched currentauthority overlay required'\noverlay,overlay_ref,_=read(CURRENT_OVERLAY_FETCHED_PROOF['path'],CURRENT_OVERLAY_FETCHED_PROOF['sha256'])\nassert overlay['status']=='PASS_FETCHED_SELECTED_INSTALL_CURRENT_AUTHORITY_OVERLAY'\nassert overlay['source_proof']=="+repr(PUBLISHED_SOURCE_PROOF)+"\nassert overlay['current_physical']=="+repr(packet['physical_acceptance'])+" and overlay['current_postjoin']=="+repr(packet['current_postjoin'])+"\nassert overlay['query_source']=="+repr(qr)+" and overlay['query_inputs']=="+repr(inputs)+"\nassert overlay['member_count']==15 and overlay['retirement_members']==9\nassert overlay['commit']==overlay['fetched_commit'] and re.fullmatch('[0-9a-f]{40}',overlay['commit']) and re.fullmatch('[0-9a-f]{40}',overlay['tree'])\n"
 need(anchor in fill,'existing fill pre-effect anchor');fill=fill.replace(anchor,check+'\n'+anchor);fill=fill.replace("base.update(status='PASS_EXECUTION_RELEASE',fetched_source_verified=True,","base.update(current_authority_source_proof={k:overlay_ref[k] for k in ('path','sha256')},status='PASS_EXECUTION_RELEASE',fetched_source_verified=True,")
 ast.parse(fill);need('assert False' not in fill,'no pending fill literal other than actual overlay proof');fr=write(out/'fill_install_current_review_payload.OVERLAY-FETCH-PENDING.py',fill)
 binding=write(out/'CURRENT-INSTALL-AUTHORITY-BINDINGS.json',dict(source_proof=PUBLISHED_SOURCE_PROOF,current_physical=packet['physical_acceptance'],current_postjoin=packet['current_postjoin'],nine_records=nine,query=qr,inputs=inputs,finalfill=fr,actual_query=None,actual_release=None))
 labels=['physical.json','postjoin.json','normal.json','proc-join.json','mutex-join.json','proc-stdout.json','proc-stderr','mutex-stdout.json','mutex-stderr'];files={'retirement/'+k:v for k,v in zip(labels,nine)};files.update({'adjacent/query.py':qr,'adjacent/capture.py':cap,'adjacent/inputs.json':inputs,'adjacent/finalfill.py':fr,'CURRENT-INSTALL-AUTHORITY-BINDINGS.json':binding,'ROOT-OWNER-ENTRY.PENDING.json':entry});need(len(files)==15,'exact finite overlay')
 spec=write(out/'EXACT-FIFTEEN-CURRENT-AUTHORITY-OVERLAY.json',dict(files=files,member_count=15,retirement_members=9,source_proof=PUBLISHED_SOURCE_PROOF,base_source_proof=PUBLISHED_SOURCE_PROOF,current_physical=packet['physical_acceptance'],current_postjoin=packet['current_postjoin'],query_source=qr,query_inputs=inputs,destination='/home/holden/mckernel/docs/verification/evidence/m15-installed-consumer-runtime-20261024-1/current-authority-overlay-1'))
 pubsource=assign(read(SOURCES['publisher_template']).decode(),{'SPEC':repr(spec)}).replace('PASS_FINITE_CURRENT_COPY2_SOURCE_AUTHORITY_OVERLAY_ONLY','PASS_FINITE_INSTALL_CURRENT_AUTHORITY_OVERLAY_ONLY')
 pubref=write(out/'publish_install_current_authority_overlay_once.NOT-GRANTED.py',pubsource)
 ready=write(out/'READY.ACTUAL-LATE-INSTALL-QUERY-AND-FILL.NOT-RELEASED.json',dict(scope=__doc__,query=qr,capture=cap,inputs=inputs,query_argv=['/home/holden/anaconda3/bin/python3','-I','-B',cap['path'],inputs['sha256']],finalfill=fr,current_overlay_spec=spec,current_overlay_publisher=pubref,publication_argv=['/home/holden/anaconda3/bin/python3','-I','-B',pubref['path'],'--publish-overlay-once',pubref['sha256']],actual_query=None,actual_payload=None,actual_release=None,publication_and_fetch_required=True))
 print(json.dumps(ready,sort_keys=True))
if __name__=='__main__':main()
