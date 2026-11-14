"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One retained-only complete actual archive readback. No archive generation/extraction.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,stat
B=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
D=Path(__file__).parent
ROOT=B/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1'
IDENTITY=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')

def need(ok,label):
 if not ok:raise ValueError(label)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def write(name,value):
 p=D/name
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 return dict(path=str(p),bytes=p.stat().st_size,sha256=digest(p.read_bytes()))
def read_bound(row,limit=32<<20):
 p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());need(stat.S_ISREG(before.st_mode) and before.st_size<=limit,'bounded regular subject '+str(p));raw=f.read(limit+1);after=os.fstat(f.fileno())
 need(all(getattr(before,k)==getattr(after,k) for k in IDENTITY),'subject changed '+str(p))
 size=row.get('bytes',row.get('size'));need(len(raw)==size and digest(raw)==row['sha256'],'subject byte mismatch '+str(p))
 if 'mode'in row:need(before.st_mode==row['mode'],'subject mode mismatch '+str(p))
 return raw,dict(path=str(p),bytes=len(raw),sha256=digest(raw)),{k:getattr(after,k) for k in IDENTITY}
def file_ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=digest(raw))
def load(row,name):
 read_bound(row);spec=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 need(os.getuid()==os.geteuid()==1000,'unprivileged actual stage review')
 need(sorted(os.sched_getaffinity(0))==[0],'CPU0 profile')
 need(resource.getrlimit(resource.RLIMIT_AS)==(2<<30,2<<30) and resource.getrlimit(resource.RLIMIT_CPU)==(60,60),'exact helper limits')
 stage_ref=dict(path=str(ROOT/'ROOT-ACTUAL-SCRATCH-STAGE.json'),bytes=934,sha256='6ceccfb91b0ad7fc1ff7d6353613345db4ab625670871b126114cbaca73ffb99')
 raw,_,_=read_bound(stage_ref);stage=json.loads(raw)
 source_raw,source_ref,_=read_bound(stage['source_manifest']);scratch_raw,scratch_ref,_=read_bound(stage['scratch_manifest']);need(source_raw==scratch_raw,'source/scratch exact manifest')
 manifest=json.loads(source_raw);need(manifest['case_id']=='P-M01-02-child-SIGTERM-and-exec-recovery-227B','original227 case')
 need(stage['nonce'] is stage['runtime_authority'] is None,'stage source scope')
 receipt_row=manifest['staging']['overlay_manifest'];raw,receipt_ref,receipt_identity=read_bound(receipt_row);receipt=json.loads(raw)
 parser_row=manifest['staging']['overlay_source'];need(parser_row['sha256']=='46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d','reviewed parser source');parser=load(parser_row,'reviewed_retained_newc_parser')
 base_raw,base_ref,base_identity=read_bound(manifest['staging']['base_initramfs'])
 archive_raw,archive_ref,archive_identity=read_bound(manifest['staging']['derived_initramfs'])
 need(archive_ref['sha256']==receipt['output_sha256']=='636f229b2602d22185475e805eb451165b7f3bc41ad18e961ffcc6206cf4e3de','exact retained archive')
 need(archive_ref['bytes']==receipt['size'] and archive_identity==receipt['output_identity'],'actual archive size/identity')
 base_cpio=parser._authenticate_base(base_raw,base_sha256=receipt['base_sha256'],base_size=len(base_raw),base_cpio_sha256=receipt['base_cpio_sha256'],base_cpio_size=receipt['base_cpio_size'])
 need(digest(base_cpio)=='d983c1747414b3a676676108de2cf91a98983698356a2353aab03e236f83b31c' and len(base_cpio)==44428264,'original exact base raw CPIO')
 actual=parser._inflate(archive_raw,parser.MAX_CPIO_SIZE)
 need(actual[:len(base_cpio)]==base_cpio,'original raw base prefix byte exact')
 overlay=actual[len(base_cpio):];need(digest(overlay)==receipt['overlay_sha256'],'actual appended overlay digest')
 records,trailer=parser.parse_newc(actual) # EXACTLY ONE complete actual derived archive parse.
 final=parser._replay_records(records);fullmap=parser._manifest(final)
 need(fullmap==receipt['final_map'],'ENTIRE actual final map/metadata/content differs from retained receipt')
 overlay_records=[r for r in records if r['archive']==max(r['archive']for r in records)]
 need(tuple(r['name']for r in overlay_records)==parser.OVERLAY_NAMES,'exact appended member order/multiplicity')
 for row,mode in zip(overlay_records,parser.OVERLAY_MODES):
  need(row['mode']==mode and row['uid']==row['gid']==row['mtime']==row['devmajor']==row['devminor']==row['rdevmajor']==row['rdevminor']==0,'overlay exact type/mode/ownership/device metadata')
  need(row['nlink']==(2 if stat.S_ISDIR(mode)else 1),'overlay hardlink multiplicity')
 names={'apps/app':manifest['artifacts']['payload'],'bin/mcexec':manifest['artifacts']['mcexec'],'init':manifest['staging']['collector'],'images/mckernel.img':manifest['artifacts']['mckernel_image']}
 names.update({'modules/'+Path(r['path']).name:r for r in manifest['modules']})
 for member,row in names.items():
  need(member in fullmap,'required member '+member);need(fullmap[member]['sha256']==row['sha256']and fullmap[member]['size']==row['size'],'actual content '+member)
 need(fullmap['images/mckernel.img']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57','original110 kernel scope')
 contract_ref=file_ref(ROOT/'original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json');need(contract_ref['sha256']=='7f06ce9bce0d58a6baeb9df1e1c1fd24d26c7b6d825db384dbf12c2693c629a6','original227 additive contract')
 contract=json.loads(read_bound(contract_ref)[0]);supplement_row=dict(path=str(B/'m15-mcexec-default-f4d-actual-native-preparation-source-1/validate_staged_executor_binding.py'),bytes=4386,sha256='29f9add4327e6eff4dffe7dcac02ad1b10a8349ae621b8b3ee673426ba2bfaca');supplement=load(supplement_row,'retained_executor_contract_checks');supplement.check(manifest,receipt,contract)
 binding=json.loads((ROOT/'original227-contract-case-correction-source-1/COLLECTOR-AND-STAGE-BINDING.json').read_bytes());owner=load(binding['normal_owner'],'retained_normal_owner_stage_APIs');owner._manifest_identity(stage['scratch_manifest']['path'],stage['scratch_manifest']['sha256']);owner._manifest_outside_writable_parent(stage['scratch_manifest']['path'],stage['planned_attempt_parent'])
 # Final source/output identities still match after full parsing; no second archive read.
 for row,identity in [(manifest['staging']['base_initramfs'],base_identity),(manifest['staging']['derived_initramfs'],archive_identity),(receipt_row,receipt_identity)]:
  after=Path(row['path']).lstat();need(all(getattr(after,k)==identity[k]for k in IDENTITY),'input identity changed during parse')
 map_ref=write('ACTUAL-FULL-FINAL-MAP.json',fullmap)
 summaries=[]
 for row in records:
  record={k:row[k]for k in ['name','ino','mode','uid','gid','nlink','mtime','size','devmajor','devminor','rdevmajor','rdevminor','sha256','archive']}
  if stat.S_ISLNK(row['mode']):record['symlink_target_hex']=row['data'].hex()
  summaries.append(record)
 records_ref=write('ACTUAL-ORDERED-ARCHIVE-RECORDS.json',summaries)
 report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_RETAINED_ORIGINAL227_ARCHIVE_FULLMAP_READBACK',source_manifest=source_ref,scratch_manifest=scratch_ref,stage=stage_ref,derived_archive=archive_ref,derived_archive_identity=archive_identity,base_archive=base_ref,base_raw_sha256=digest(base_cpio),base_raw_bytes=len(base_cpio),derived_raw_sha256=digest(actual),derived_raw_bytes=len(actual),overlay_raw_sha256=digest(overlay),overlay_raw_bytes=len(overlay),receipt=receipt_ref,parser_source=parser_row,executor_validator=supplement_row,executor_contract=contract_ref,normal_owner=binding['normal_owner'],full_final_map=map_ref,ordered_records=records_ref,record_count=len(records),final_member_count=len(fullmap),last_trailer_offset=trailer,archive_layers=max(r['archive']for r in records)+1,symlink_record_count=sum(stat.S_ISLNK(r['mode'])for r in records),hardlink_record_count=sum(stat.S_ISREG(r['mode'])and r['nlink']>1 for r in records),complete_map_equal=True,all_metadata_content_exact=True,original227_CURRENT110_scope_only=True,guard_native_Docker_compiler_compose_archivewrite_staging_nonce_calls=0,runtime_authority=None)
 write('ACTUAL-READBACK-RESULT.json',report);print(json.dumps(report))

if __name__=='__main__':
 try:main()
 except BaseException as error:
  write('FAILURE.json',dict(status='ACTUAL_STAGE_READBACK_FAILED_NO_RETRY',error=repr(error),runtime_authority=None));raise
