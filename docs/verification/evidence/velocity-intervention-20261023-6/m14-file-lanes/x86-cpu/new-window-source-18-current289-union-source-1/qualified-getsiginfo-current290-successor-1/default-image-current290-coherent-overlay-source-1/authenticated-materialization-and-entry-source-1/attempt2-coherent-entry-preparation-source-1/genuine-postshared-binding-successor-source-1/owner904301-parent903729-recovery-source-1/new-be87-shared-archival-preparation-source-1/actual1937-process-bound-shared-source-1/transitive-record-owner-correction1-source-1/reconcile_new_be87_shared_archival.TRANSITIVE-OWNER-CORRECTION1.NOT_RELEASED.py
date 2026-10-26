"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact separately reviewed shared-record-only archival/reconciliation. No normal
owner PASS receipt is fabricated. No Docker/container/other-record/mutex unlink.
Post-unlink uncertainty retains existing replacement-lock quarantine indefinitely.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-NEW-BE87-SHARED-ARCHIVAL.TRANSITIVE-OWNER-CORRECTION1.NOT-RELEASED.json'
PROFILE_SHA='35ca99a281fdfc0319883f7eae2597b77f02fe70d7c3e554623d67bc0eeed665'
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest()==PROFILE_SHA
r=json.loads(PROFILE.read_bytes())
for pending_key in ('process_retirement_source','process_retirement_acceptance','new_process_retirement_complete','new_external_wrapper_join','new_process_postreturn','new_process_helper','new_process_acceptance_contract'):
 if not isinstance(r.get(pending_key),dict):raise RuntimeError('source-only NEWbe87 shared archival: genuine process prerequisite pending:'+pending_key)
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
m.ABSENT=set(historical['required_absent_pids'])|set(current['required_absent_pids'])|set(p['required_absent_pids'])|set(r['additional_absent_pids']);assert len(m.ABSENT)==r['total_absent_count']
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
sources=list(historical['publisher_source_paths'])+list(current['source_paths'])+[p['bound_guard']['source'],str(Path(p['bound_guard']['source']).parent.parent/'native_rust_exact_mckernel_image_container_owner.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py'),r['historical_process_retirement_source']['path']]+[row['path'] for row in r['new_exact_publisher_sources']]+[row['path'] for row in r['new_family_publisher_sources']]+[str(Path(r['bound_guard']['source']).parent/'owner904301-parent903729-recovery-source-1'/'observe_new_be87_owner904301_parent903729_held.READONLY.NOT_RELEASED.py'),r['process_retirement_source']['path']];assert len(sources)==len(set(sources))==r['explicit_publisher_source_count']
original_process_code=m.process_code
def process_code():
 code=original_process_code();marker='    for arg in argv:\n';assert code.count(marker)==1
 return code.replace(marker,'    if any(path in argv for path in '+repr(sources)+'): return True\n'+marker,1)

def runtime_limits():
 if resource.getrlimit(resource.RLIMIT_CPU)!=(resource.RLIM_INFINITY,resource.RLIM_INFINITY):raise m.Refusal('actual shared reconciliation requires unlimited CPU; no timeoutkill envelope')

def accepted_prerequisites():
 # The concrete process acceptance schema/fields are bound only after the real
 # process-only retirement, original wrapper join and helper postreturn proof.
 contract=r['new_process_acceptance_contract']
 if contract.get('reviewed') is not True or contract.get('implementation_ownership') is not False or contract.get('reviewer')!='/root/review18h':raise m.Refusal('new actual903 process acceptance contract not independently approved')
 acceptance=m.read_json(Path(r['process_retirement_acceptance']['path']),r['process_retirement_acceptance']['sha256'])
 if acceptance.get('schema')!=contract.get('schema') or acceptance.get('decision')!=contract.get('decision') or acceptance.get('reviewer')!='/root/review18h' or acceptance.get('implementation_ownership') is not False:raise m.Refusal('genuine NEW903 process acceptance schema/decision differs')
 expected=contract.get('exact_acceptance_fields')
 if not isinstance(expected,dict) or expected.get('target_retired')!={'pid':903729,'starttime':'77387104'} or expected.get('shared_record_preserved') is not True or expected.get('postreturn_same_mutex27_4_free') is not True:raise m.Refusal('new process contract exact retirement/free/shared facts missing')
 if any(acceptance.get(k)!=v for k,v in expected.items()):raise m.Refusal('new actual process acceptance exact fields differ')
 for key in ('new_process_retirement_complete','new_external_wrapper_join','new_process_postreturn'):
  fixed(r[key])
 completed=m.read_json(Path(r['new_process_retirement_complete']['path']),r['new_process_retirement_complete']['sha256'])
 if completed.get('schema')!='scratch22-authority1.quarantine-recovery-complete.v1' or completed.get('status')!='COMPLETE_PROCESS_RECOVERY' or completed.get('build_status')!='FAIL' or completed.get('cleanup_required') is not True or completed.get('acceptance_credit') is not False or completed.get('target',{}).get('pid')!=903729 or completed['target'].get('starttime')!='77387104' or completed['target'].get('parent')!=903728 or completed.get('replacement_root_lock')!=[27,4]:raise m.Refusal('actual NEW903 process COMPLETE identity/scope differs')
 post=m.read_json(Path(r['new_process_postreturn']['path']),r['new_process_postreturn']['sha256'])
 if r['new_external_wrapper_join']!=r['new_process_postreturn'] or post.get('original_session')!=68064 or post.get('original_tool_joined_exit')!=137 or post.get('helper_session')!=53284 or post.get('helper_tool_joined_exit')!=0 or post.get('helper_pid')!=916592 or post.get('helper_starttime')!='77624073' or post.get('helper_parent_retained_PROC_row')!=[916591,842942,'77624072'] or post.get('complete_sha256')!=r['new_process_retirement_complete']['sha256'] or post.get('shared_reconciliation_authorized') is not False or post.get('new_admission_authorized') is not False:raise m.Refusal('actual original/helper joins and retained wrapper birth proof differs')
 observations=post.get('observations')
 if not isinstance(observations,list) or len(observations)!=2:raise m.Refusal('two actual process postreturn observations required')
 for row in observations:
  wanted={k:v for k,v in r['shared_identity'].items() if k not in ('path','size')};wanted['bytes']=r['shared_identity']['size']
  if row.get('all_four_PIDs_absent')!=[903729,903728,916592,916591] or row.get('checked_group_members')!={'903729':[],'903728':[],'916592':[],'916591':[]} or row.get('existing_mutex27_4_nonblocking_acquire_release') is not True or row.get('shared')!=wanted:raise m.Refusal('actual NEW903 postreturn free mutex/absence/shared unchanged proof differs')
 helper=r['new_process_helper']
 if type(helper.get('pid')) is not int or helper['pid']<=0 or not isinstance(helper.get('starttime'),str) or helper.get('joined_group_absent_closed') is not True or helper.get('returncode')!=0 or helper['pid'] not in m.ABSENT:raise m.Refusal('new helper direct join and absence binding missing')
 held=m.read_json(Path(r['current_held_acceptance']['path']),r['current_held_acceptance']['sha256'])
 if held.get('decision')!='PASS_NEW_BE87_HELD_READONLY_PROCESS_RECOVERY_PREREQUISITE_ONLY' or held.get('reviewer')!='/root/review18h' or held.get('implementation_ownership') is not False or held.get('result')!=r['current_held_result'] or held.get('current_shared_sha256')!=r['shared_identity']['sha256'] or held.get('current_shared_request_sha256')!=r['new_failed_owner']['request_sha256']:raise m.Refusal('actual NEWbe87 held prerequisite differs')
 observed=m.read_json(Path(r['current_held_result']['path']),r['current_held_result']['sha256']);baseline=observed['snapshots'][0]['structured_inspect_projection']
 for snap in observed['snapshots']:labels.compare(baseline,snap['structured_inspect_projection'])
 if m.sha(m.canonical(baseline))!=r['current_structured_projection_sha256']:raise m.Refusal('accepted current typed44 baseline differs')
 return baseline


def accepted_recent_zero_unlink_diagnostic(baseline):
 raise m.Refusal('old zero-unlink diagnostic is historical only for newbe87; cannot authorize current archival')

def original_request_relation():
 _,raw=fixed(r['new_request']);request=m.strict(raw)
 if archive_ops._request_hash(request)!=r['new_failed_owner']['request_sha256'] or r['shared_value'].get('request_sha256')!=r['new_failed_owner']['request_sha256']:raise m.Refusal('new369 request/newbe87 record relation differs')
 return request

def shared_phase(before):
 if before:
  row,raw,st,_=archive_ops.bind_node(SHARED,r['shared_value'],r['shared_identity'])
 else:
  if os.path.lexists(SHARED):raise m.Refusal('released owned shared path reappeared')
  rawrow,raw=m.file_identity(OUT/'shared.record.raw',keep=True);statrow,statraw=m.file_identity(OUT/'shared.record.stat.json',keep=True);manifestrow,manifestraw=m.file_identity(OUT/'shared.archive-manifest.json',keep=True)
  document=m.strict(statraw);manifest=m.strict(manifestraw);row=document['original_identity'];st=document['original_stat']
  if row!=r['shared_identity'] or rawrow['sha256']!=r['shared_identity']['sha256'] or rawrow['size']!=268 or m.strict(raw)!=r['shared_value'] or document['raw_sha256']!=rawrow['sha256'] or document['raw_bytes']!=268 or document['record_snapshot']['record']!=r['shared_value'] or manifest['original_identity']!=row or manifest['original_stat']!=st or manifest['raw_archive']!={'path':str(OUT/'shared.record.raw'),'sha256':rawrow['sha256'],'bytes':268} or manifest['stat_archive']!={'path':str(OUT/'shared.record.stat.json'),'sha256':statrow['sha256'],'bytes':statrow['size']} or manifest['original_record']!=r['shared_value']:raise m.Refusal('exclusive HOST raw/stat archive differs from original shared record')
  if any(meta['device']!=r['archive_host_device'] or meta['mode']!=0o600 or meta['uid']!=1000 or meta['gid']!=1000 or meta['nlink']!=1 for meta in (rawrow,statrow,manifestrow)):raise m.Refusal('exclusive HOST archive node shape differs')
 return {'original_identity':row,'raw_hex':raw.hex(),'original_record':r['shared_value']}

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
 if any(os.path.lexists(path) for path in r['new_affected_absent_paths']):raise m.Refusal('new failed owner affected path unexpectedly exists')
 return result

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
 for ref in r['historical_old_shared_proofs']:
  actual,_=fixed(ref);result.setdefault('historical_old324a_archival_preserved_not_current_clearance',{})[actual['path']]=actual
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth differs')
 return result

def capture(label,kind,raw):
 path=OUT/(label+'.'+kind);m.publish(path,raw)
 return {'path':str(path),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
fixed_typed_profile=m.read_json(Path(r['typed_diagnostic_profile']['path']),r['typed_diagnostic_profile']['sha256']);fixedrows=fixed_typed_profile['fixed_rows'];inspectargv=fixed_typed_profile['inspect_argv']
# Exact original process-validator body; only executable literal repinned to actual parent.
validator_node=next(node for node in ast.parse(Path(r['primitive']['path']).read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='validate_process_report')
validator_code=ast.get_source_segment(Path(r['primitive']['path']).read_text(),validator_node).replace("'/usr/bin/python3.8'",repr(r['bound_guard']['exe']))
exec(compile(validator_code,r['primitive']['path'],'exec'),m.__dict__)

def snapshot(label,before):
 m.boot_check();locks=m.require_lock_holder(os.getpid());inputs=retained_inputs(before)
 for pid in sorted(m.ABSENT):
  if h.members(pid):raise m.Refusal('retired original owner/caller/wrapper/helper/prior group remains')
 caller=[os.getpid(),m.proc_stat(os.getpid())[19]];challenge=os.urandom(24).hex()
 raw=m.root_readonly(['/usr/bin/python3','-I','-B','-c',process_code(),challenge,str(caller[0]),caller[1]]);report=m.strict(raw);m.validate_process_report(report,challenge,caller,False)
 captures={'process':capture(label,'process.json',raw)}
 raw=m.root_readonly(['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}']);captures['ps']=capture(label,'ps.raw.jsonl',raw);ps=labels.validate_ps_identity(raw,fixedrows)
 raw=m.root_readonly(inspectargv);captures['inspect']=capture(label,'inspect.raw.json',raw);typed=labels.project(raw,fixedrows,{},ps['unparsed_current_Labels_display']);labels.compare(accepted_prerequisites(),typed)
 if shared_phase(before)!=inputs['original_shared_binding']:raise m.Refusal('original shared phase changed during snapshot')
 m.boot_check();m.require_lock_holder(os.getpid())
 return {'inputs':inputs,'captures':captures,'root_locks':locks,'active_shared_present':before,'structured_inspect_projection':typed,'historical_label_map_equality':'UNPROVEN'}

def bind_release(path,expected):
 runtime_limits();release=m.read_json(path,expected)
 if release.get('schema')!='mckernel.current290.exact-new-be87-shared-archival.release.v1' or release.get('status')!='PASS_EXECUTION_RELEASE' or type(release.get('execution_count')) is not int or release['execution_count']!=1 or type(release.get('unlink_budget')) is not int or release['unlink_budget']!=1 or release.get('profile_sha256')!=PROFILE_SHA or release.get('shared_identity')!=r['shared_identity'] or release.get('process_retirement_acceptance')!=r['process_retirement_acceptance'] or release.get('current_held_acceptance')!=r['current_held_acceptance'] or release.get('new_process_retirement_complete')!=r['new_process_retirement_complete'] or release.get('new_external_wrapper_join')!=r['new_external_wrapper_join'] or release.get('new_process_postreturn')!=r['new_process_postreturn'] or release.get('fetched_source_verified') is not True or release.get('outer_timeout_or_kill_authorized') is not False or not m.re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) or not release.get('author'):raise m.Refusal('separate exact shared-only one-shot execution release required')
 accepted_prerequisites();original_request_relation()
 files={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA}
 for key in ('archive_primitives','primitive','h990','parent_readonly_profile','typed_diagnostic_source','typed_diagnostic_profile','typed_comparator','process_retirement_source','sdk_record_source','shared_request_hash_source','private_root_readonly_capture','current_held_acceptance','current_held_result','current_held_whole_join','current_held_postreturn','new_process_retirement_complete','new_external_wrapper_join','new_process_postreturn'):
  row=r[key];fixed(row);files[row['path']]=row['sha256']
 if release.get('files_sha256')!=files:raise m.Refusal('exact shared-only source/profile/dependency map differs')
 review=m.read_json(Path(release['source_review']['path']),release['source_review']['sha256'])
 if review.get('decision')!='PASS_SOURCE' or review.get('implementation_ownership') is not False or not review.get('reviewer') or review['reviewer']==release['author'] or review.get('files_sha256')!=files or review.get('source_checkpoint')!=release['source_checkpoint'] or review.get('profile_sha256')!=PROFILE_SHA:raise m.Refusal('independent shared-only source review required')
 execution=m.read_json(Path(release['execution_review']['path']),release['execution_review']['sha256']);payload={key:value for key,value in release.items() if key!='execution_review'}
 if execution.get('decision')!='PASS_EXECUTION' or execution.get('implementation_ownership') is not False or not execution.get('reviewer') or execution['reviewer']==release['author'] or execution.get('reviewed_release_payload_sha256')!=m.sha(m.canonical(payload)):raise m.Refusal('independent exact shared-only execution review required')
 if os.path.lexists(OUT):raise m.Refusal('fresh exclusive HOST archive namespace required')
 OUT.mkdir(mode=0o700)
 if OUT.stat().st_dev!=r['archive_host_device'] or OUT.stat().st_uid!=1000 or OUT.stat().st_gid!=1000 or OUT.stat().st_mode&0o777!=0o700:raise m.Refusal('new HOST archive directory identity differs')
 return release

def execute(release_path,checksum):
 release=bind_release(release_path,checksum);lockfd=None;attempted=complete=False;requested=[];handlers={}
 def defer(number,_frame):
  if not requested:requested.append(number)
 oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,m.DEFERRED_SIGNALS)
 try:
  for number in m.DEFERRED_SIGNALS:handlers[number]=signal.getsignal(number);signal.signal(number,defer)
  signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
  if m.lock_rows()!=[]:raise m.Refusal('permanent mutex must be currently free before acquisition')
  lockfd=m.acquire_root_lock();m.require_lock_holder(os.getpid())
  first=snapshot('before1',True);second=snapshot('before2',True)
  if first['inputs']!=second['inputs'] or requested:raise m.Refusal('pre-unlink inputs changed or termination requested')
  prepared={'schema':'mckernel.current290.shared-only-reconciliation.prepared.v1','scope':__doc__,'profile_sha256':PROFILE_SHA,'release_sha256':checksum,'process_retirement_acceptance':r['process_retirement_acceptance'],'original_shared_identity':r['shared_identity'],'unlink_budget':1,'before':[first,second],'source_workload_status':'FAIL'};m.publish(m.PREPARED,m.canonical(prepared))
  safety_count=0
  def safety():
   nonlocal safety_count
   if requested:raise m.Refusal('termination requested before owned shared unlink')
   safety_count+=1;current=snapshot('archive-safety'+str(safety_count),True)
   if current['inputs']!=first['inputs']:raise m.Refusal('inputs changed before owned shared unlink')
  def mark_unlink_attempt():
   nonlocal attempted
   if attempted:raise m.Refusal('sole shared unlink budget already consumed')
   attempted=True
  result=archive_ops.archive_and_unlink_one(SHARED,r['shared_value'],r['shared_identity'],OUT,safety,m.publish,mark_unlink_attempt,r['archive_parent_identity'])
  after=snapshot('after',False)
  if after['inputs']!=first['inputs']:raise m.Refusal('retained inputs/current typed baseline changed after shared unlink')
  m.require_lock_holder(os.getpid())
  record={'schema':'mckernel.current290.shared-only-reconciliation.complete.v1','scope':__doc__,'status':'COMPLETE_EXACT_SHARED_ONLY_ARCHIVAL_RECONCILIATION_PENDING_POSTRETURN_PHYSICAL','profile_sha256':PROFILE_SHA,'release_sha256':checksum,'prepared_sha256':m.sha(m.canonical(prepared)),'archive_result':result,'after':after,'original_failed_owner_status':'FAIL','original_shared_identity':r['shared_identity'],'active_shared_absent':True,'record_unlinks':1,'other_record_unlinks':0,'Docker_mutations':0,'signals_sent':0,'permanent_mutex':[27,4],'held_through_complete':True,'historical_label_map_equality':'UNPROVEN','new_heavy_admission_authorized':False};m.publish(m.COMPLETE,m.canonical(record));complete=True
  return {'status':record['status'],'complete_path':str(m.COMPLETE),'complete_sha256':m.sha(m.canonical(record)),'new_heavy_admission_authorized':False}
 except BaseException:
  if attempted and not complete:m.quarantine_hold(lockfd)
  raise
 finally:
  if lockfd is not None and (not attempted or complete):os.close(lockfd)
  if not attempted or complete:
   signal.pthread_sigmask(signal.SIG_BLOCK,m.DEFERRED_SIGNALS)
   for number,handler in handlers.items():signal.signal(number,handler)
   signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)

def main():
 parser=m.argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--release',type=Path,required=True);parser.add_argument('--release-sha256',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if not args.execute:raise m.Refusal('explicit execution and exact separate release required')
 print(json.dumps(execute(args.release,args.release_sha256),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
