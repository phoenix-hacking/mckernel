"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact separately reviewed shared-record-only archival/reconciliation. No normal
owner PASS receipt is fabricated. No Docker/container/other-record/mutex unlink.
Post-unlink uncertainty retains existing replacement-lock quarantine indefinitely.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-NEW-BE87-OWNER904301-PARENT903729-HELD-READONLY-PROFILE.json'
PROFILE_SHA='a7fd7da249080a66d47c2dbffcb1556e6695d5c466eac40d4b2e4ba87ba650e8'
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest()==PROFILE_SHA
r=json.loads(PROFILE.read_bytes())
def initial_load(ref,name):
 raw=Path(ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',ref.get('size'))
 spec=importlib.util.spec_from_file_location(name,ref['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
praw=Path(r['parent_readonly_profile']['path']).read_bytes();assert hashlib.sha256(praw).hexdigest()==r['parent_readonly_profile']['sha256'];p=json.loads(praw)
m=initial_load(r['primitive'],'accepted_authority1_shared_custody')
h=initial_load(r['h990'],'accepted_h990_groups')
normal=initial_load(p['normal_engine'],'accepted_normal_exact_identity')
labels=initial_load(r['typed_comparator'],'accepted_tagged_current_labels')
archive_ops=initial_load(r['archive_primitives'],'reviewed_single_record_archive_units')
private_root_capture=initial_load(r['private_root_readonly_capture'],'private_exact_root_readonly_capture')
historical=json.loads(Path(p['historical_profile']['path']).read_bytes());current=json.loads(Path(p['current_profile']['path']).read_bytes())
assert (os.getuid(),os.getgid(),os.geteuid(),os.getegid())==(1000,1000,1000,1000) and os.sched_getaffinity(0)=={0}
m.PID,m.START,m.PARENT=903729,'77387104',903728;m.BOOT=p['boot_id']
m.ABSENT=set(historical['required_absent_pids'])|set(current['required_absent_pids'])|set(p['required_absent_pids'])|set(r['additional_absent_pids']);assert len(m.ABSENT)==58
OUT=Path(r['archive_directory']);m.PREFIX=OUT/'retained-current290-shared-only';m.PREPARED=OUT/'PREPARED.json';m.COMPLETE=OUT/'COMPLETE.json';m.QUARANTINE=OUT/'QUARANTINE.json'
SHARED=Path(r['allowed_record_path']);assert str(SHARED)=='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'
private_root_capture.CAPTURE_DIRECTORY=OUT;private_root_capture.PUBLISH=m.publish;private_root_capture.SMALL_LIMIT=m.SMALL_LIMIT;private_root_capture.Refusal=m.Refusal
m.root_readonly=private_root_capture.root_readonly
def load(ref,name):
 path=Path(ref['path']);raw=path.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',ref.get('size'))
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def proc_bytes_eof(path,maximum=65536):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  result=bytearray()
  while True:
   block=os.read(fd,min(65536,maximum+1-len(result)))
   if not block:return bytes(result)
   result.extend(block)
   if len(result)>maximum:raise m.Refusal('proc byte bound')
 finally:os.close(fd)

def fixed(ref):
 row,raw=m.file_identity(Path(ref['path']),keep=True)
 if row['sha256']!=ref['sha256'] or row['size']!=ref.get('bytes',ref.get('size')):raise m.Refusal('fixed source/evidence bytes changed:'+ref['path'])
 return row,raw

def exact_identity(expected):
 # Preserve each accepted profile's exact original observation contract:
 # old55 authority1 integer modes; SDK79 normal-engine string modes.
 if isinstance(expected['mode'],str):
  row=normal.observe_identity(Path(expected['path']))
 else:
  row,_=m.file_identity(Path(expected['path']))
 if row!=expected:raise m.Refusal('protected metadata/bytes changed:'+expected['path'])
 return row

def retained_domain():
 result={}
 for key in ('historical_profile','current_profile'):
  _,raw=fixed(p[key]);profile=json.loads(raw)
  for expected in profile['protected_inputs']:
   archive=profile['archived_records'].get(expected['path'])
   if archive:
    exact_identity(archive)
    if os.path.lexists(expected['path']) and expected['path']!=p['shared_identity']['path']:raise m.Refusal('retired prior owned record reappeared')
    result[expected['path']]={'historical_archive_preserved':archive,'new_owned_shared_record_expected':expected['path']==p['shared_identity']['path']}
   else:result[expected['path']]=exact_identity(expected)
  for path,rows in profile['preserved_inventories'].items():
   if normal.metadata_inventory(Path(path))!=rows:raise m.Refusal('retained metadata inventory changed')
  for path,expected in profile['preserved_directory_identities'].items():
   if normal.observe_identity(Path(path))!=expected:raise m.Refusal('retained directory identity changed')
 return result

def evidence():
 result={}
 for ref in p['evidence_inputs']:
  row,raw=fixed(ref);result[ref['path']]=row
 # Existing actual bytes prove a joined failed child and a parent quarantine;
 # they are preserved as failures rather than rewritten into normal cleanup.
 base=Path(p['bound_guard']['source']).parent/'actual-entry-1'
 joined=json.loads((base/'owner.JOIN.json').read_bytes());process=json.loads((base/'owner.PROCESS.json').read_bytes());entry=json.loads((base/'ACTUAL-OWNER-ENTRY.json').read_bytes());quarantine=json.loads((base/'OWNERSHIP-QUARANTINE.json').read_bytes())
 if joined['pid']!=867329 or joined['starttime']!='76715862' or joined['returncode']!=1 or not all(joined[k] is True for k in ('closed_streams','direct_child_joined','group_absent')):raise m.Refusal('genuine failed-owner join changed')
 if process['pid']!=867329 or process['parent_pid']!=866814 or entry['caller_pid']!=866814 or entry['caller_starttime']!='76706306' or entry['holder']['fd']!=3 or quarantine['holder_pid']!=866814 or quarantine['holder_fd']!=3 or not quarantine['owner_joined']:raise m.Refusal('exact failed-child/held-parent relation changed')
 owner=Path(process['argv'][-2]);raw=owner.read_bytes();tree=ast.parse(raw)
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ImageOwner');run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
 if run.body[1].lineno!=1488 or run.body[2].lineno!=1490 or b'OwnerError: offline provenance release hash' not in (base/'owner.stderr').read_bytes():raise m.Refusal('actual pre-Docker validation failure/controlflow differs')
 return result
m.proc_bytes=proc_bytes_eof
sources=list(historical['publisher_source_paths'])+list(current['source_paths'])+[p['bound_guard']['source'],str(Path(p['bound_guard']['source']).parent.parent/'native_rust_exact_mckernel_image_container_owner.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py'),r['process_retirement_source']['path']]+[row['path'] for row in r['new_exact_publisher_sources']]+[row['path'] for row in r['new_family_publisher_sources']];assert len(sources)==len(set(sources))==14
original_process_code=m.process_code
def process_code():
 code=original_process_code();marker='    for arg in argv:\n';assert code.count(marker)==1
 return code.replace(marker,'    if any(path in argv for path in '+repr(sources)+'): return True\n'+marker,1)


def accepted_prerequisites():
 # Reuse only the accepted typed44 baseline, never historical owner/shared clearance.
 old=m.read_json(Path(r['current_quiescence_acceptance']['path']),r['current_quiescence_acceptance']['sha256']);actual=m.read_json(Path(old['raw_stdout']['path']),old['raw_stdout']['sha256']);baseline=actual['snapshots'][0]['structured_inspect_projection'];labels.compare(baseline,actual['snapshots'][1]['structured_inspect_projection'])
 if m.sha(m.canonical(baseline))!=r['current_structured_projection_sha256'] or old.get('historical_label_map_equality')!='UNPROVEN':raise m.Refusal('accepted typed44 baseline differs')
 return baseline


def original_request_relation():
 _,raw=fixed(r['new_request']);request=m.strict(raw)
 if archive_ops._request_hash(request)!=r['new_failed_owner']['request_sha256'] or r['shared_value'].get('request_sha256')!=r['new_failed_owner']['request_sha256']:raise m.Refusal('new369 request/newbe87 record relation differs')
 return request

def shared_phase(before):
 if before is not True:raise m.Refusal('held readonly observer has no shared-release phase')
 row,raw=m.file_identity(SHARED,keep=True)
 if row!=r['shared_identity'] or m.strict(raw)!=r['shared_value']:raise m.Refusal('exact NEWbe87 shared node/raw/owner differs')
 if any(os.path.lexists(path) for path in r['new_affected_absent_paths']):raise m.Refusal('new precompiler/preDocker affected path unexpectedly present')
 return {'original_identity':row,'raw_hex':raw.hex(),'original_record':r['shared_value']}

def retained_inputs(before):
 domain=retained_domain()
 # Original archived-record pins remain exact; phase-specific active shared
 # ownership is proved separately, so this historical map is never clearance.
 if str(SHARED) in domain and isinstance(domain[str(SHARED)],dict):
  value=dict(domain[str(SHARED)]);value.pop('new_owned_shared_record_expected',None);value['current_shared_phase_proved_separately']=True;domain[str(SHARED)]=value
 result={'retained_domain':domain,'actual_failure_evidence':evidence(),'original_shared_binding':shared_phase(before)}
 proofs={}
 for ref in r['retirement_proofs']:
  actual,_=fixed(ref);proofs[ref['path']]=actual
 result['accepted_retirement_and_current_proofs']=proofs
 result['new_actual_failure_evidence']=new_failure_inputs()
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth differs')
 return result

def capture(label,kind,raw):
 path=OUT/(label+'.'+kind);m.publish(path,raw)
 return {'path':str(path),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
fixed_typed_profile=m.read_json(Path(r['typed_diagnostic_profile']['path']),r['typed_diagnostic_profile']['sha256']);fixedrows=fixed_typed_profile['fixed_rows'];inspectargv=fixed_typed_profile['inspect_argv']
def snapshot(label,before):
 if before is not True:raise m.Refusal('new held-owner observer is readonly before-phase only')
 m.boot_check();held_parent_identity();locks=m.require_lock_holder(903729);inputs=retained_inputs(True)
 for pid in sorted(m.ABSENT):
  if h.members(pid):raise m.Refusal('required original/new owner/query/census group remains')
 caller=[os.getpid(),m.proc_stat(os.getpid())[19]];challenge=os.urandom(24).hex()
 raw=m.root_readonly(['/usr/bin/python3','-I','-B','-c',process_code(),challenge,str(caller[0]),caller[1]]);report=m.strict(raw);m.validate_process_report(report,challenge,caller,True)
 captures={'process':capture(label,'process.json',raw)}
 raw=m.root_readonly(['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}']);captures['ps']=capture(label,'ps.raw.jsonl',raw);ps=labels.validate_ps_identity(raw,fixedrows)
 raw=m.root_readonly(inspectargv);captures['inspect']=capture(label,'inspect.raw.json',raw);typed=labels.project(raw,fixedrows,{},ps['unparsed_current_Labels_display']);labels.compare(accepted_prerequisites(),typed)
 if shared_phase(True)!=inputs['original_shared_binding']:raise m.Refusal('new shared node changed during held readonly snapshot')
 held_parent_identity();m.require_lock_holder(903729)
 return {'inputs':inputs,'captures':captures,'root_locks':locks,'held_parent':r['held_parent'],'active_shared_present':True,'structured_inspect_projection':typed,'historical_label_map_equality':'UNPROVEN'}




# Exact original process-validator body; only executable literal repinned to actual parent.
validator_node=next(node for node in ast.parse(Path(r['primitive']['path']).read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='validate_process_report')
validator_code=ast.get_source_segment(Path(r['primitive']['path']).read_text(),validator_node).replace("'/usr/bin/python3.8'",repr(r['bound_guard']['exe']))
exec(compile(validator_code,r['primitive']['path'],'exec'),m.__dict__)
def held_parent_identity():
 identity=m.guard_identity(r);fd=Path('/proc/903729/fd/3');meta=fd.stat();named=Path('/run/lock/mckernel-development.lock').lstat()
 if (meta.st_dev,meta.st_ino,meta.st_size,meta.st_uid,meta.st_gid,meta.st_mode,meta.st_nlink)!=(27,4,0,0,0,0o100644,1) or (named.st_dev,named.st_ino)!=(27,4) or os.readlink(fd)!='/run/lock/mckernel-development.lock':raise m.Refusal('new exactparentFD3 permanent node differs')
 locks=m.require_lock_holder(903729)
 if [line.split()[2:] for line in m.proc_bytes('/proc/903729/fdinfo/3').decode('ascii').splitlines() if line.startswith('lock:')]!=locks:raise m.Refusal('new parentFD3 same-description custody differs')
 return identity

def new_failure_inputs():
 result={}
 for ref in r['new_failure_pins']:
  row,_=fixed(ref);result[row['path']]=row
 summary=m.read_json(Path(r['new_failure_summary']['path']),r['new_failure_summary']['sha256']);base=Path(r['new_quarantine']['path']).parent;joined=m.read_json(base/'owner.JOIN.json');process=m.read_json(base/'owner.PROCESS.json');entry=m.read_json(base/'ACTUAL-OWNER-ENTRY.json');quarantine=m.read_json(Path(r['new_quarantine']['path']),r['new_quarantine']['sha256'])
 if summary.get('status')!='FAIL_IMAGE_RECEIPT_CANDIDATE_IDENTITY_BEFORE_COMPILER_OWNERSHIP_RETAINED' or summary['shared']['sha256']!=r['shared_identity']['sha256'] or summary['shared']['record']!=r['shared_value']:raise m.Refusal('actual new failure summary differs')
 if joined.get('pid')!=904301 or joined.get('starttime')!='77396514' or joined.get('returncode')!=1 or not all(joined.get(k) is True for k in ('direct_child_joined','group_absent','closed_streams')) or process.get('parent_pid')!=903729 or entry.get('caller_pid')!=903729 or entry.get('caller_starttime')!='77387104' or quarantine.get('holder_pid')!=903729 or quarantine.get('holder_fd')!=3:raise m.Refusal('actual new owner join/quarantine/parent relation differs')
 for ref in (r['new_query_result'],r['new_census_receipt']):
  value=m.read_json(Path(ref['path']),ref['sha256']);rows=value['results'] if 'results' in value else [value]
  for row in rows:
   if row.get('returncode')!=0 or not all(row.get(k) is True for k in ('direct_child_joined','group_absent','closed_streams')):raise m.Refusal('new five/census original join differs')
 return result

def bind_readonly_release(path,expected):
 if resource.getrlimit(resource.RLIMIT_CPU)!=(60,60):raise m.Refusal('finite CPU60 held readonly profile required')
 release=m.read_json(path,expected)
 if release.get('schema')!='mckernel.current290.newbe87-parent903729-held-readonly.release.v1' or release.get('status')!='PASS_READONLY_DIAGNOSTIC_EXECUTION_RELEASE' or type(release.get('execution_count')) is not int or release['execution_count']!=1 or type(release.get('unlink_budget')) is not int or release['unlink_budget']!=0 or type(release.get('signal_budget')) is not int or release['signal_budget']!=0 or release.get('profile_sha256')!=PROFILE_SHA or release.get('shared_identity')!=r['shared_identity'] or release.get('held_parent')!=r['held_parent'] or release.get('new_failure_summary')!=r['new_failure_summary'] or release.get('fetched_source_verified') is not True or not m.re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) or not release.get('author'):raise m.Refusal('separate exact newbe87 held readonly release required')
 accepted_prerequisites();original_request_relation();new_failure_inputs()
 files={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA}
 for key in ('archive_primitives','primitive','h990','parent_readonly_profile','typed_diagnostic_source','typed_diagnostic_profile','typed_comparator','process_retirement_source','sdk_record_source','shared_request_hash_source','private_root_readonly_capture'):
  row=r[key];fixed(row);files[row['path']]=row['sha256']
 if release.get('files_sha256')!=files:raise m.Refusal('exact newheld readonly source/profile/dependency map differs')
 review=m.read_json(Path(release['source_review']['path']),release['source_review']['sha256'])
 if review.get('decision')!='PASS_SOURCE' or review.get('implementation_ownership') is not False or not review.get('reviewer') or review['reviewer']==release['author'] or review.get('files_sha256')!=files or review.get('source_checkpoint')!=release['source_checkpoint'] or review.get('profile_sha256')!=PROFILE_SHA:raise m.Refusal('independent exact newheld readonly source review required')
 execution=m.read_json(Path(release['execution_review']['path']),release['execution_review']['sha256']);payload={k:v for k,v in release.items() if k!='execution_review'}
 if execution.get('decision')!='PASS_EXECUTION' or execution.get('implementation_ownership') is not False or not execution.get('reviewer') or execution['reviewer']==release['author'] or execution.get('reviewed_release_payload_sha256')!=m.sha(m.canonical(payload)):raise m.Refusal('independent exact held readonly execution review required')
 if os.path.lexists(OUT):raise m.Refusal('fresh held readonly namespace required')
 OUT.mkdir(mode=0o700);return release

def execute_readonly(path,checksum):
 bind_readonly_release(path,checksum);first=snapshot('held1',True);second=snapshot('held2',True)
 if first['inputs']!=second['inputs']:raise m.Refusal('new held readonly input maps differ')
 labels.compare(first['structured_inspect_projection'],second['structured_inspect_projection'])
 record={'schema':'mckernel.current290.newbe87-parent903729-held-readonly.result.v1','scope':__doc__,'status':'PASS_READONLY_NEW_BE87_SHARED_RETAINED_PARENT903729_HELD','profile_sha256':PROFILE_SHA,'release_sha256':checksum,'parent':r['held_parent'],'new_owner':r['new_failed_owner'],'new_shared_identity':r['shared_identity'],'required_absent_pids':sorted(m.ABSENT),'publisher_source_paths':sources,'snapshots':[first,second],'root_queries':6,'signals_sent':0,'pidfd_operations':0,'flock_operations':0,'record_unlinks':0,'Docker_mutations':0,'historical_label_map_equality':'UNPROVEN','old324a_or004f_clearance_for_new_record':False,'process_or_shared_recovery_released':False,'new_admission_authorized':False};m.publish(OUT/'READONLY-RESULT.json',m.canonical(record));return {'status':record['status'],'path':str(OUT/'READONLY-RESULT.json'),'sha256':m.sha(m.canonical(record))}

def main():
 parser=m.argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--release',type=Path,required=True);parser.add_argument('--release-sha256',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if not args.execute:raise m.Refusal('explicit exact held readonly release required')
 print(json.dumps(execute_readonly(args.release,args.release_sha256),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
