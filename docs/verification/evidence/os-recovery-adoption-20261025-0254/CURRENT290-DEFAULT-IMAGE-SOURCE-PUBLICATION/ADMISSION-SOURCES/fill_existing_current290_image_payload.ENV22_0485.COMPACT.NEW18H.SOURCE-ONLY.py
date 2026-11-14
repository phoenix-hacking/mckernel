#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing five-output normal-image payload fill, with a compact reference-only
c252 census stage. Reads authentic closed outputs/ROOT declarations; no queries,
owner imports, root, compiler, Docker, locks or execution-release effects.
"""
from pathlib import Path
import hashlib,json,re,sys,time,stat
D=Path(__file__).parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PUBLICATION_ROOT='docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT290-DEFAULT-IMAGE-SOURCE-PUBLICATION'
EXPECTED_REQUEST_SHA='586f157112403f08d570dfb078bba8e6c6709020b793ea01ac2d788c07c97737'
EXPECTED_SOURCE_MANIFEST_SHA='3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018'
C252_SHA='c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1'
SOURCE_RETENTION_OUTPUT_FILES=None  # FUTURE_TYPED: actual retention output count
SOURCE_PLAN_SHA=None  # FUTURE_TYPED: exact290 source retention plan SHA after reviewed preparation
SOURCES=['READONLY-ADMISSION-ARGV.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.json','capture_readonly_admission.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.py','COMPACT-C252-CENSUS-REQUEST.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json','ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json','ROOT-CURRENT-CONTINUITY-AGGREGATE-PHYSICAL.TEMPLATE.json','NAMESPACE-INITIALIZATION.NOT-EXECUTED.json','fill_existing_current290_image_payload.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py']
EXPECTED_NAMESPACE=['/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/owner-work', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/owner-evidence', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/owner-evidence/attempt', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/common-exclusion.json', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/lease.json', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/owner-work/output', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-current290-default-image-attempt-1/owner-work/evidence', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/actual-build-owner-capture-1', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock']
def need(c,m):
 if not c:raise RuntimeError(m)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def ref(p):return dict(path=str(p),sha256=digest(p),bytes=p.stat().st_size)
def auth(row):
 p=Path(row['path']);need(ref(p)==row,'exact authentic metadata reference');return p
def load(p):return json.loads(p.read_bytes())
def put(name,value):
 p=D/name;raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();need(len(raw)<1<<20,'compact admission/payload per-file1MiB bound')
 with p.open('xb') as f:f.write(raw)
 return ref(p)
def fetched(proof_path,checksum):
 need(digest(proof_path)==checksum,'root exact fetched-proof SHA');pub=load(proof_path)
 need(pub['status']=='PASS_ACTUAL_FETCHED_SOURCE_BLOBS' and re.fullmatch('[0-9a-f]{40}',pub['commit']),'actual fetched publication')
 rows={x['path']:x for x in pub['files']};need(len(rows)==len(pub['files']),'unique fetched repository paths')
 for name in SOURCES:
  p=D/name;row=rows[PUBLICATION_ROOT+'/ADMISSION-SOURCES/'+name];need(row['sha256']==digest(p),'published exact admission source '+name)
 repo=Path('/home/holden/mckernel');head=(repo/'.git/HEAD').read_text().strip();need(head.startswith('ref: '),'symbolic current publication HEAD')
 need((repo/'.git'/head[5:]).read_text().strip()==pub['commit'],'actual publication commit remains current at fill; distinct frozen eb3 compute cohort')
 return pub,rows
def prepare(proof_path,proof_sha,context_path):
 pub,rows=fetched(proof_path,proof_sha);context=load(context_path);need(context['author']=='/root','genuine root declarations')
 p=load(D/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json');request_path=auth(p['source']['request']);need(digest(request_path)==EXPECTED_REQUEST_SHA,'reviewed full owner request unchanged');request=load(request_path)
 for row in p['source'].values():auth(row)
 need(p['source']['manifest']['sha256']==EXPECTED_SOURCE_MANIFEST_SHA,'reviewed exact full source manifest')
 retention=load(auth(context['actual_source_retention']));need(retention['status']=='PASS_EXACT_CURRENT290_FULL_SOURCE_AND_METADATA_RETENTION_ONLY' and retention['source_entries']==6153 and retention['source_bytes']==105804031 and type(SOURCE_RETENTION_OUTPUT_FILES) is int and SOURCE_RETENTION_OUTPUT_FILES>0 and retention['output_files']==SOURCE_RETENTION_OUTPUT_FILES and retention['all_reopened_content_verified'] is True,'actual finite source-retention result')
 need(retention['plan']['sha256']==SOURCE_PLAN_SHA and retention['full_owner_request']['sha256']==EXPECTED_REQUEST_SHA,'publication exact input cohort')
 need(rows[PUBLICATION_ROOT+'/SOURCE-RETENTION.json']['sha256']==context['actual_source_retention']['sha256'],'fetched exact source retention receipt')
 for output in retention['outputs']:
  auth({k:output[k] for k in ('path','sha256','bytes')});rp=PUBLICATION_ROOT+'/CAPSULE/'+Path(output['path']).name;need(rows[rp]['sha256']==output['sha256'],'fetched exact source capsule output')
 cap=D/'actual-readonly-admission-capture-1';actual=cap/'ACTUAL-READONLY-RESULT.json';a=load(actual);need(len(a['results'])==5,'five authentic finite query outputs')
 for x in a['results']:need(x['returncode']==0 and x['direct_child_joined'] and x['group_absent'] and x['closed_streams'] and x['error'] is None and x['retirement_error'] is None and x['captures']['stderr']['size']==0,'all query captures cleanjoined')
 observed=[(cap/str(i)/'stdout').read_text() for i in range(1,6)]
 for i,x in enumerate(a['results'],1):
  need(digest(cap/str(i)/'stdout')==x['captures']['stdout']['sha256'] and digest(cap/str(i)/'stderr')==x['captures']['stderr']['sha256'],'sealed actual query streams')
 ident= json.loads(observed[0]);mount=json.loads(observed[1]);loops=json.loads(observed[3]);namespace=json.loads(observed[4])
 need([x['path'] for x in namespace['rows']]==EXPECTED_NAMESPACE,'exact ten namespace paths')
 n=namespace['rows'];need(n[0]['exists'] and sorted(n[0]['entries'])==['owner-evidence','owner-work'],'fresh image attempt contains exactly two owned namespaces')
 for i in [1,2]:need(n[i]['exists'] and n[i]['entries']==[] and n[i]['mode']==0o700 and n[i]['uid']==n[i]['gid']==1000,'fresh private empty work/evidence')
 need(all(not x['exists'] for x in n[3:]),'attempt/common/lease/output/evidence/root-capture/shared-heavy all absent')
 need(ident['identities'][request['source_root']]==request['source_identity'] and request['disk_identity']==request['source_identity'],'actual copied source IDs')
 need(ident['identities'][request['backup_root']]==request['backup_identity'],'retained qualified SDK metadata backup identity')
 back=next(x for x in observed[2].splitlines() if x.startswith('/home/holden/mckernel-work/scratch.ext4 '));size=int(re.search(r' size=(\d+)',back)[1]);blocks=int(re.search(r' blocks=(\d+)',back)[1]);gap=max(0,size-512*blocks)
 need(size==118111600640,'unchanged admitted full scratch backing size')
 filesystems=mount['filesystems'];need(len(filesystems)==1 and filesystems[0]['uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52' and filesystems[0]['target']=='/home/holden/mckernel-work/scratch','actual scratch UUID/mount')
 ld=loops['loopdevices'];need(len(ld)==1 and ld[0]['name']==filesystems[0]['source'] and ld[0]['back-file']=='/home/holden/mckernel-work/scratch.ext4' and ld[0]['offset']==ld[0]['sizelimit']==0 and ld[0]['ro'] is False,'exact actual loop/backing association')
 mutex=next(x for x in observed[2].splitlines() if x.startswith('/run/lock/mckernel-development.lock '));md=int(re.search(r' dev=(\d+)',mutex)[1]);mi=int(re.search(r' inode=(\d+)',mutex)[1])
 cont=context['continuity'];need(cont['no_heavy_since_latest_physical'] is True and cont['permanent_mutex']==dict(device=md,inode=mi,campaign_holds_dev_flock=True),'root current physical continuity and exact permanent devflock declaration')
 ag=context['aggregate'];need(ag['actual_no_other_heavy'] is True and ag['durable_memory_lease'] is False and ag['committed_memory_bytes']==21206401024 and ag['host_reserve_bytes']==4294967296 and ag['minimum']==25501368320 and ag['campaign_ceiling_gib']=='22.0485','existing exact aggregate reservation + current campaign ceiling')
 mem=int(next(x.split()[1] for x in ident['memory'] if x.startswith('MemAvailable:')))*1024;HOST=ident['space']['/home/holden']['free'];scratch=ident['space']['/home/holden/mckernel-work/scratch']['free']
 HOST_required=max(50248630272,(16<<30)+gap+(4<<30)+(640<<20));scratch_required=14091616256
 need(mem>=ag['minimum'] and HOST>=HOST_required and scratch>=scratch_required,'complete fresh full-gap HOST growth/scratch/aggregate admission')
 physical=context['actual_current_physical'];postjoin=context['actual_current_live_postjoin'];auth(physical);auth(postjoin)
 compact=load(D/'COMPACT-C252-CENSUS-REQUEST.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json');compact.update(status='ROOT_DERIVED_COMPACT_CENSUS_REQUEST_ONLY_NOT_EXECUTION_RELEASE',host_floor=HOST_required-(512<<20),host_total_required=HOST_required,scratch_floor=scratch_required-(512<<20),full_source_fetch=ref(proof_path),current_physical=physical,current_continuity=ref(context_path))
 need('launcher_aggregate_memory_gib' not in compact and compact['full_owner_request']['sha256']==EXPECTED_REQUEST_SHA,'compact historical census is distinct from full owner/current aggregate')
 compact_ref=put('COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json',compact)
 p.update(status='ROOT_CURRENT290_IMAGE_PAYLOAD_AWAITING_COMPACT_CENSUS_AND_INDEPENDENT_EXECUTION_REVIEW',author='/root',aggregate=dict(ag,MemAvailable=mem),continuity=cont,namespace=namespace,disk=dict(HOST_available=HOST,HOST_required=HOST_required,scratch_available=scratch,scratch_required=scratch_required,full_sparse_gap=gap,preserve_uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52',new_HOST_output_growth=4<<30),fetched_publication=ref(proof_path),actual_five_query=ref(actual),fresh_raw_five=[ref(cap/str(i)/'stdout') for i in range(1,6)],observations_started_at_epoch=a['started_at_epoch'],observations_finished_at_epoch=a['finished_at_epoch'],root_fill_context=ref(context_path),source_publication_retention=context['actual_source_retention'],current_physical=physical,current_live_postjoin=postjoin,actual_loop_association=loops,actual_mount=mount,compact_census_request=compact_ref,entry_reconfirmation='Freshly remeasure complete HOST full-gap growth/scratch/aggregate floors, same published inputs and shared/common/lease/devflock/current physical continuity before ordinary owner exec; no outer CPU/wall watchdog')
 payload_ref=put('ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json',p);print(json.dumps(dict(compact=compact_ref,payload=payload_ref),sort_keys=True))
def finish(census_path,census_sha):
 need(digest(census_path)==census_sha,'exact root-captured closed compact census report');c=load(census_path);p=load(D/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json');compact=auth(p['compact_census_request']);need(c['status']=='PASS_READ_ONLY' and c['execution_released'] is False,'unchanged c252 read-only census PASS only')
 need(c['request']['path']==str(compact) and c['request']['sha256']==digest(compact),'census exact compact request identity')
 need(c['processes']==[] and c['containers']==[],'no live or uncertain heavy owners')
 need(c['resources']['host_free']>=p['disk']['HOST_required'] and c['resources']['scratch_free']>=p['disk']['scratch_required'] and c['resources']['memory_available']>=p['aggregate']['minimum'] and set(range(2,6))<=set(c['resources']['cpus']),'fresh census resource floors and original CPU observation semantics')
 # The unchanged c252 source owns the complete authenticated historical lease
 # rows; do not erase or reinterpret them here.
 need(isinstance(c['leases'],list),'retained authenticated lease census')
 for row in p['source'].values():auth(row)
 p.update(status='ROOT_EXACT_CURRENT290_IMAGE_ONLY_PAYLOAD_AWAITING_INDEPENDENT_EXECUTION_REVIEW',actual_compact_census=ref(census_path),census_completed_at_fill_epoch=time.time(),independent_review=None)
 result=put('ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json',p);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':
 need(len(sys.argv) in (4,5),'exact prepare/finalize argv')
 if sys.argv[1]=='prepare':need(len(sys.argv)==5,'prepare proof proofsha context');prepare(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]))
 elif sys.argv[1]=='finish':need(len(sys.argv)==4,'finish census censussha');finish(Path(sys.argv[2]),sys.argv[3])
 else:raise RuntimeError('unknown metadata-only stage')
