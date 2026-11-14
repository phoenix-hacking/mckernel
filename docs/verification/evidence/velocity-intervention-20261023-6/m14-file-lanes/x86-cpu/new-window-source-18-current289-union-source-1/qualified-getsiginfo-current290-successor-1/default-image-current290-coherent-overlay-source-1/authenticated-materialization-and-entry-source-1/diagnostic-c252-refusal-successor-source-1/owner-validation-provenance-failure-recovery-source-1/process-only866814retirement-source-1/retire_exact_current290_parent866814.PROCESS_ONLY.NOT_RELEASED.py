"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact parent866814 HOST-process retirement adapter for existing authority1.execute.
No shared-record or Docker mutation. Existing uncertainty quarantine is retained;
no outer timeout/kill is authorized. Source/pure tests only until exact release.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-CURRENT290-PARENT866814-PROCESS-ONLY-RETIREMENT-PROFILE.json'
PROFILE_SHA='0fc0bddec0bab50bebf4476c950ef7e3ca8d5af3fad9288420a4651a9dd0198b'
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest()==PROFILE_SHA
r=json.loads(PROFILE.read_bytes())
raw=Path(r['parent_readonly_profile']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['parent_readonly_profile']['sha256'];p=json.loads(raw)
def initial_load(ref,name):
 raw=Path(ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',ref.get('size'))
 spec=importlib.util.spec_from_file_location(name,ref['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=initial_load(r['primitive'],'accepted_authority1_exact_execute')
h=initial_load(r['h990'],'accepted_h990_members')
historical=json.loads(Path(p['historical_profile']['path']).read_bytes());current=json.loads(Path(p['current_profile']['path']).read_bytes())
normal=initial_load(p['normal_engine'],'accepted_normal_identity_inventory')
label_projection=initial_load(r['typed_comparator'],'accepted_tagged_label_projection')
assert (os.getuid(),os.getgid(),os.geteuid(),os.getegid())==(1000,1000,1000,1000) and os.sched_getaffinity(0)=={0} and os.uname().machine=='x86_64'
m.PID,m.START,m.PARENT=866814,'76706306',866813
m.ABSENT=set(historical['required_absent_pids'])|set(current['required_absent_pids'])|set(p['required_absent_pids']);assert len(m.ABSENT)==45 and 866814 not in m.ABSENT
m.PROFILE=PROFILE;m.PROFILE_SHA=PROFILE_SHA
m.PREFIX=Path(r['capture_directory'])/'retained-current290'
m.PREPARED=Path(str(m.PREFIX)+'.prepared.json');m.COMPLETE=Path(str(m.PREFIX)+'.complete.json');m.QUARANTINE=Path(str(m.PREFIX)+'.quarantine.json')
m.ORIGINAL_FAILURE_SHA256=r['failure_evidence']
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

def shared_record():
 row,raw=m.file_identity(Path(p['shared_identity']['path']),keep=True)
 if row!=p['shared_identity'] or json.loads(raw)!=p['shared_value']:raise m.Refusal('exact failed-owner shared record changed')
 if any(os.path.lexists(path) for path in p['affected_absent_paths']):raise m.Refusal('pre-Docker affected path unexpectedly exists')
 return {'identity':row,'raw_hex':raw.hex(),'value':json.loads(raw),'affected_absent_paths':p['affected_absent_paths']}
m.proc_bytes=proc_bytes_eof
# The accepted complete process census and all eight explicit owner-source paths.
sources=list(historical['publisher_source_paths'])+list(current['source_paths'])+[p['bound_guard']['source'],str(Path(p['bound_guard']['source']).parent.parent/'native_rust_exact_mckernel_image_container_owner.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py')]
assert len(sources)==len(set(sources))==8
original_process_code=m.process_code
def process_code():
 code=original_process_code();marker='    for arg in argv:\n';assert code.count(marker)==1
 return code.replace(marker,'    if any(path in argv for path in '+repr(sources)+'): return True\n'+marker,1)
m.process_code=process_code
original_guard_identity=m.guard_identity
def guard_identity(profile):
 identity=original_guard_identity(profile)
 fdpath=Path('/proc/866814/fd/3');meta=fdpath.stat();named=Path('/run/lock/mckernel-development.lock').lstat()
 if (meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,meta.st_mode,meta.st_size,meta.st_nlink)!=(27,4,0,0,0o100644,0,1) or (named.st_dev,named.st_ino)!=(27,4) or os.readlink(fdpath)!='/run/lock/mckernel-development.lock':raise m.Refusal('exact parentFD3 permanent identity differs')
 locks=m.require_lock_holder(866814)
 if [line.split()[2:] for line in m.proc_bytes('/proc/866814/fdinfo/3').decode('ascii').splitlines() if line.startswith('lock:')]!=locks:raise m.Refusal('exact parentFD3 same-description lock differs')
 return identity
m.guard_identity=guard_identity

def typed_baseline():
 accepted=m.read_json(Path(r['readonly_acceptance']['path']),r['readonly_acceptance']['sha256'])
 if accepted.get('decision')!='PASS_CURRENT_QUIESCENCE_BASELINE_PROCESS_RECOVERY_PREREQUISITE_ONLY' or accepted.get('reviewer')!='/root/review18h' or accepted.get('implementation_ownership') is not False or accepted.get('current_process_recovery_target')!={'pid':866814,'starttime':'76706306','fd':3,'mutex_device':27,'mutex_inode':4} or accepted.get('historical_label_map_equality')!='UNPROVEN' or accepted.get('new_current_structured_baseline') is not True or any(accepted.get(key) is not False for key in ('process_retirement_released','shared_reconciliation_released','Docker_mutation_authorized','hold_clearance')):raise m.Refusal('exact independent current-quiescence prerequisite acceptance differs')
 observed=m.read_json(Path(accepted['raw_stdout']['path']),accepted['raw_stdout']['sha256']);a=observed['snapshots'][0]['structured_inspect_projection'];b=observed['snapshots'][1]['structured_inspect_projection'];label_projection.compare(a,b)
 if m.sha(m.canonical(a))!=r['current_structured_projection_sha256'] or r['current_structured_projection_sha256']!=accepted['current_structured_projection_sha256']:raise m.Refusal('accepted NEW current typed baseline differs')
 return a

def protected_inputs(_release,_profile):
 result={'retained_domain':retained_domain(),'actual_failure_evidence':evidence(),'shared_record':shared_record()}
 proof={}
 for row in r['actual_typed_baseline_proofs']:
  actual,_=fixed(row);proof[row['path']]=actual
 actual,_=fixed(r['readonly_acceptance']);proof[actual['path']]=actual
 result['accepted_current_baseline_proofs']=proof
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth changed')
 return result
m.protected_inputs=protected_inputs

def capture(label,kind,raw):
 path=Path(str(m.PREFIX)+'.'+label+'.'+kind);m.publish(path,raw)
 return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}

def snapshot(label,release,profile,before):
 inputs=protected_inputs(release,profile)
 if before:
  guard_identity(profile);locks=m.require_lock_holder(866814)
 else:
  m.boot_check();locks=m.require_lock_holder(os.getpid())
 for pid in sorted(m.ABSENT|({866814} if not before else set())):
  if h.members(pid):raise m.Refusal('prior/target PID or process group remains')
 caller=[os.getpid(),m.proc_stat(os.getpid())[19]];challenge=os.urandom(24).hex()
 raw=m.root_readonly(['/usr/bin/python3','-I','-B','-c',process_code(),challenge,str(caller[0]),caller[1]])
 report=m.strict(raw);m.validate_process_report(report,challenge,caller,before)
 if not before and any(row[0]==866814 for sweep in report['snapshots'] for row in sweep):raise m.Refusal('target remains in post-retirement complete PROC census')
 captures={'process':capture(label,'process.json',raw)}
 raw=m.root_readonly(['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'])
 captures['ps']=capture(label,'ps.raw.jsonl',raw);ps=label_projection.validate_ps_identity(raw,current_fixed_rows)
 raw=m.root_readonly(fixed_inspect_argv)
 captures['inspect']=capture(label,'inspect.raw.json',raw)
 projections=label_projection.project(raw,current_fixed_rows,{},ps['unparsed_current_Labels_display'])
 label_projection.compare(typed_baseline(),projections)
 if shared_record()!=inputs['shared_record']:raise m.Refusal('exact shared record changed during process-only snapshot')
 m.boot_check();m.require_lock_holder(866814 if before else os.getpid())
 return {'inputs':inputs,'captures':captures,'root_locks':locks,'structured_inspect_projection':projections,'historical_label_map_equality':'UNPROVEN','new_current_structured_baseline':True,'shared_reconciliation_authorized':False,'Docker_mutation_authorized':False}
m.snapshot=snapshot
fixed_typed_profile=m.read_json(Path(r['typed_diagnostic_profile']['path']),r['typed_diagnostic_profile']['sha256']);current_fixed_rows=fixed_typed_profile['fixed_rows'];fixed_inspect_argv=fixed_typed_profile['inspect_argv']

def bind_release(path,expected):
 release=m.read_json(path,expected);profile=m.read_json(PROFILE,PROFILE_SHA)
 if release.get('schema')!='mckernel.current290.parent866814.process-only-retirement.release.v1' or release.get('status')!='PASS_EXECUTION_RELEASE' or type(release.get('execution_count')) is not int or release['execution_count']!=1 or (type(release.get('signal_budget')) is not int or release.get('signal_budget')!=1) or release.get('profile_sha256')!=PROFILE_SHA or release.get('target')!=profile['target'] or release.get('readonly_acceptance')!=profile['readonly_acceptance'] or release.get('preserve_shared_record_sha256')!=profile['shared_identity']['sha256'] or release.get('fetched_source_verified') is not True or not m.re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) or not release.get('author'):raise m.Refusal('exact current-parent one-shot process-only execution release required')
 typed_baseline()
 files={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA}
 for key in ('primitive','h990','parent_readonly_profile','typed_diagnostic_source','typed_diagnostic_profile','typed_comparator'):
  row=profile[key];fixed(row);files[row['path']]=row['sha256']
 if release.get('files_sha256')!=files:raise m.Refusal('exact source/profile/dependency map differs')
 review=m.read_json(Path(release['source_review']['path']),release['source_review']['sha256'])
 if review.get('decision')!='PASS_SOURCE' or review.get('implementation_ownership') is not False or not review.get('reviewer') or review['reviewer']==release['author'] or review.get('files_sha256')!=files or review.get('profile_sha256')!=PROFILE_SHA or review.get('source_checkpoint')!=release['source_checkpoint']:raise m.Refusal('independent exact process-only source review required')
 execution=m.read_json(Path(release['execution_review']['path']),release['execution_review']['sha256']);payload={key:value for key,value in release.items() if key!='execution_review'}
 if execution.get('decision')!='PASS_EXECUTION' or execution.get('implementation_ownership') is not False or not execution.get('reviewer') or execution['reviewer']==release['author'] or execution.get('reviewed_release_payload_sha256')!=m.sha(m.canonical(payload)):raise m.Refusal('independent exact process-only execution release required')
 for original,digest in profile['failure_evidence'].items():
  if m.file_identity(Path(original))[0]['sha256']!=digest:raise m.Refusal('original observer failure changed')
 if any(os.path.lexists(fixed) for fixed in (m.PREPARED,m.COMPLETE,m.QUARANTINE,m.PREFIX.parent)):raise m.Refusal('fresh one-shot recovery namespace required')
 m.PREFIX.parent.mkdir(mode=0o700)
 return release,profile
m.bind_release=bind_release
if __name__=='__main__':raise SystemExit(m.main())
