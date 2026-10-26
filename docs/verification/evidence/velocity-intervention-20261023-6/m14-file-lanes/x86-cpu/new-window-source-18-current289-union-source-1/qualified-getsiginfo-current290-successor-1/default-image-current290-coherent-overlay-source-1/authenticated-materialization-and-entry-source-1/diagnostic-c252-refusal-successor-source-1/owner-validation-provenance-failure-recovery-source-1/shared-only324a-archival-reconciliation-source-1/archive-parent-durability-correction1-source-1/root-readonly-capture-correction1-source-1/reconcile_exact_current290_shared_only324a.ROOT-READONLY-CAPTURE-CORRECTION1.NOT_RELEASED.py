"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact separately reviewed shared-record-only archival/reconciliation. No normal
owner PASS receipt is fabricated. No Docker/container/other-record/mutex unlink.
Post-unlink uncertainty retains existing replacement-lock quarantine indefinitely.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-SHARED-ONLY324A-PRIVATE-ROOT-READONLY-CAPTURE-CORRECTION1-PROFILE.json'
PROFILE_SHA='35268714bc84345e4c46f9361264ae167aeecde49be6a0c0a927f7640b8db780'
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
m.PID,m.START,m.PARENT=866814,'76706306',866813;m.BOOT=p['boot_id']
m.ABSENT=set(historical['required_absent_pids'])|set(current['required_absent_pids'])|set(p['required_absent_pids'])|set(r['additional_absent_pids']);assert len(m.ABSENT)==48
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
sources=list(historical['publisher_source_paths'])+list(current['source_paths'])+[p['bound_guard']['source'],str(Path(p['bound_guard']['source']).parent.parent/'native_rust_exact_mckernel_image_container_owner.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py'),r['process_retirement_source']['path']];assert len(sources)==len(set(sources))==9
original_process_code=m.process_code
def process_code():
 code=original_process_code();marker='    for arg in argv:\n';assert code.count(marker)==1
 return code.replace(marker,'    if any(path in argv for path in '+repr(sources)+'): return True\n'+marker,1)

def runtime_limits():
 if resource.getrlimit(resource.RLIMIT_CPU)!=(resource.RLIM_INFINITY,resource.RLIM_INFINITY):raise m.Refusal('actual shared reconciliation requires unlimited CPU; no timeoutkill envelope')

def accepted_prerequisites():
 accepted=m.read_json(Path(r['process_retirement_acceptance']['path']),r['process_retirement_acceptance']['sha256'])
 if accepted.get('decision')!='PASS_PROCESS_ONLY_RETIREMENT_AND_POSTRETURN_FREE_MUTEX_SHARED_FENCE_RETAINED' or accepted.get('reviewer')!='/root/review18h' or accepted.get('implementation_ownership') is not False or accepted.get('target_retired')!={'pid':866814,'starttime':'76706306'} or accepted.get('original_session_join_returncode')!=137 or accepted.get('helper_join_returncode')!=0 or accepted.get('mutex27_4_free_after_return') is not True or accepted.get('shared_record_preserved') is not True or accepted.get('historical_label_map_equality')!='UNPROVEN' or any(accepted.get(key) is not False for key in ('shared_reconciliation_authorized','Docker_mutation_authorized','new_admission_authorized')):raise m.Refusal('exact accepted process-only retirement/postreturn shared fence required')
 currentproof=m.read_json(Path(r['current_quiescence_acceptance']['path']),r['current_quiescence_acceptance']['sha256']);actual=m.read_json(Path(currentproof['raw_stdout']['path']),currentproof['raw_stdout']['sha256']);baseline=actual['snapshots'][0]['structured_inspect_projection'];labels.compare(baseline,actual['snapshots'][1]['structured_inspect_projection'])
 if m.sha(m.canonical(baseline))!=r['current_structured_projection_sha256']:raise m.Refusal('accepted NEW current typed baseline changed')
 return baseline

def original_request_relation():
 row=next(ref for ref in p['evidence_inputs'] if Path(ref['path']).name=='image-request.CURRENT290.IMAGE-ONLY.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json')
 _,raw=fixed(row);request=m.strict(raw)
 if archive_ops._request_hash(request)!=r['original_failed_owner']['request_sha256'] or r['shared_value'].get('request_sha256')!=r['original_failed_owner']['request_sha256'] or r['shared_value'].get('pid')!=867329 or r['shared_value'].get('starttime')!='76715862' or r['shared_value'].get('kind')!='image':raise m.Refusal('original failed request/shared owner relation differs')
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
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth differs')
 return result

def capture(label,kind,raw):
 path=OUT/(label+'.'+kind);m.publish(path,raw)
 return {'path':str(path),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
fixed_typed_profile=m.read_json(Path(r['typed_diagnostic_profile']['path']),r['typed_diagnostic_profile']['sha256']);fixedrows=fixed_typed_profile['fixed_rows'];inspectargv=fixed_typed_profile['inspect_argv']
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
 if release.get('schema')!='mckernel.current290.exact-shared-only324a-reconciliation.release.v1' or release.get('status')!='PASS_EXECUTION_RELEASE' or type(release.get('execution_count')) is not int or release['execution_count']!=1 or type(release.get('unlink_budget')) is not int or release['unlink_budget']!=1 or release.get('profile_sha256')!=PROFILE_SHA or release.get('shared_identity')!=r['shared_identity'] or release.get('process_retirement_acceptance')!=r['process_retirement_acceptance'] or release.get('fetched_source_verified') is not True or release.get('outer_timeout_or_kill_authorized') is not False or not m.re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) or not release.get('author'):raise m.Refusal('separate exact shared-only one-shot execution release required')
 accepted_prerequisites();original_request_relation()
 files={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA}
 for key in ('archive_primitives','primitive','h990','parent_readonly_profile','typed_diagnostic_source','typed_diagnostic_profile','typed_comparator','process_retirement_source','sdk_record_source','shared_request_hash_source','private_root_readonly_capture'):
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
