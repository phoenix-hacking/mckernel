"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact failed-owner shared-record and held-parent READONLY observation. No signals,
pidfd, flock, unlock, record mutation, Docker mutation, or owner execution.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess
D=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/diagnostic-c252-refusal-successor-source-1/owner-validation-provenance-failure-recovery-source-1')
PROFILE=D/'EXACT-OWNER-PROVENANCE-FAILURE-READONLY-PROFILE.json'
PROFILE_SHA='7698791af550575be73343f483f9afa358fb01780bd09226dd8039825e75a9fd'
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest()==PROFILE_SHA
p=json.loads(PROFILE.read_bytes())
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
def load(ref,name):
 path=Path(ref['path']);raw=path.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',ref.get('size'))
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load(p['primitive'],'accepted_recovery_readonly_functions')
h=load(p['h990'],'accepted_h990_members')
normal=load(p['normal_engine'],'accepted_metadata_inventory')
m.PID=866814;m.START='76706306';m.PARENT=866813;m.BOOT=p['boot_id'];m.ABSENT=set(p['required_absent_pids'])
OUT=D/'actual-fixed44-structured-inspect-diagnostic-only4-capture-1'
assert OUT.is_dir()
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
m.proc_bytes=proc_bytes_eof
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
# Preserve the accepted d503 PROC domain in addition to this failed owner.
historical=json.loads(fixed(p['historical_profile'])[1])
current=json.loads(fixed(p['current_profile'])[1])
m.ABSENT=(set(historical['required_absent_pids']) |
          set(current['required_absent_pids']) | set(p['required_absent_pids']))
assert len(historical['required_absent_pids'])==22
assert len(current['required_absent_pids'])==16
assert len(p['required_absent_pids'])==7 and len(m.ABSENT)==45
assert 866814 not in m.ABSENT

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
def current_parent():
 identity=m.guard_identity(p);locks=m.require_lock_holder(866814)
 if os.readlink('/proc/866814/fd/3')!='/run/lock/mckernel-development.lock':raise m.Refusal('parent held FD3 differs')
 st=os.stat('/proc/866814/fd/3');named=os.stat('/run/lock/mckernel-development.lock',follow_symlinks=False)
 if (st.st_dev,st.st_ino,st.st_size)!=(27,4,0) or (named.st_dev,named.st_ino,named.st_size)!=(27,4,0):raise m.Refusal('permanent mutex identity differs')
 fdinfo=m.proc_bytes('/proc/866814/fdinfo/3').decode('ascii')
 if [line.split()[2:] for line in fdinfo.splitlines() if line.startswith('lock:')]!=locks:raise m.Refusal('parent exact locked description differs')
 return {'identity':identity,'root_locks':locks,'fd3_info':fdinfo}
def shared_record():
 row,raw=m.file_identity(Path(p['shared_identity']['path']),keep=True)
 if row!=p['shared_identity'] or json.loads(raw)!=p['shared_value']:raise m.Refusal('exact failed-owner shared record changed')
 if any(os.path.lexists(path) for path in p['affected_absent_paths']):raise m.Refusal('pre-Docker affected path unexpectedly exists')
 return {'identity':row,'raw_hex':raw.hex(),'value':json.loads(raw),'affected_absent_paths':p['affected_absent_paths']}
def readonly(argv):
 result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},timeout=20,check=False)
 if result.returncode or result.stderr or len(result.stdout)>m.SMALL_LIMIT:raise m.Refusal('bounded fixed readonly child failed')
 return result.stdout
def publish(name,raw):
 path=OUT/name;m.publish(path,raw);os.chown(path,1000,1000,follow_symlinks=False)
 return {'path':str(path),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
code=m.process_code();marker='    for arg in argv:\n';assert code.count(marker)==1
sources=(list(historical['publisher_source_paths']) + list(current['source_paths']) +
         [p['bound_guard']['source'],str(Path(p['bound_guard']['source']).parent.parent/'native_rust_exact_mckernel_image_container_owner.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py')])
assert len(historical['publisher_source_paths'])==3 and len(current['source_paths'])==3
assert len(sources)==8 and len(set(sources))==8
code=code.replace(marker,'    if any(path in argv for path in '+repr(sources)+'): return True\n'+marker,1)
# Two independent process sweeps in each of two snapshots, plus complete Docker
# inventory matching the retained44 stopped-container identities: no new target.
def snapshot(label):
 before=current_parent();record=shared_record();inputs=evidence();domain=retained_domain()
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth differs')
 for pid in sorted(m.ABSENT):
  if h.members(pid):raise m.Refusal('historical/SDK/failed-owner/query/census group remains')
 caller=[os.getpid(),m.proc_stat(os.getpid())[19]];challenge='failed-owner-provenance-'+label
 raw=readonly(['/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]])
 report=m.strict(raw);m.validate_process_report(report,challenge,caller,True)
 captures={'process':publish(label+'.process.json',raw)}
 fixed(p['docker_baseline'])
 raw=readonly(['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'])
 captures['containers']=publish(label+'.containers.jsonl',raw)
 rows=[m.strict(line) for line in raw.splitlines()]
 selected=[{key:row[key] for key in ('ID','Names','Image','Labels','State')} for row in rows]
 if sorted(selected,key=lambda row:row['ID'])!=sorted(p['docker_fixed_rows'],key=lambda row:row['ID']) or any(row['State'] not in ('exited','created','dead') for row in rows):raise m.Refusal('Docker inventory changed/new target or running workload')
 after=current_parent()
 if before!=after or record!=shared_record():raise m.Refusal('held parent/shared record changed during snapshot')
 return {'parent':before,'shared_record':record,'evidence_inputs':inputs,'retained_domain':domain,'docker_count':len(rows),'captures':captures}

DIAGNOSTIC_PROFILE=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/diagnostic-c252-refusal-successor-source-1/owner-validation-provenance-failure-recovery-source-1/structured-label-diagnostic-only4-source-1/EXACT-FIXED44-STRUCTURED-LABEL-DIAGNOSTIC-ONLY-PROFILE.json')
assert hashlib.sha256(DIAGNOSTIC_PROFILE.read_bytes()).hexdigest()=='702b28e306acae22a664d10a7f64045e963fa25f0a48eea1c3dae898c45c184c'
q=json.loads(DIAGNOSTIC_PROFILE.read_bytes());label_projection=load(q['comparator'],'structured_labels_diagnostic_only')
def diagnostic_snapshot(label):
 before=current_parent();record=shared_record();inputs=evidence();domain=retained_domain()
 for pid,start in p['preserved_controllers']:
  if m.proc_stat(pid)[19]!=start:raise m.Refusal('campaign controller birth differs')
 for pid in sorted(m.ABSENT):
  if h.members(pid):raise m.Refusal('historical/SDK/failed-owner/query/census group remains')
 caller=[os.getpid(),m.proc_stat(os.getpid())[19]];challenge='structured-label-diagnostic-'+label
 raw=readonly(['/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]])
 report=m.strict(raw);m.validate_process_report(report,challenge,caller,True)
 captures={'process':publish(label+'.process.json',raw)}
 psraw=readonly(['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'])
 captures['ps']=publish(label+'.ps.raw.jsonl',psraw)
 ps_identity=label_projection.validate_ps_identity(psraw,q['fixed_rows'])
 result=subprocess.run(q['inspect_argv'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},timeout=q['inspect_timeout_seconds'],check=False)
 # Raw bytes and actual status are retained before decoding or any oracle.
 captures['inspect']=publish(label+'.inspect.raw.json',result.stdout)
 captures['inspect_stderr']=publish(label+'.inspect.stderr',result.stderr)
 captures['inspect_status']=publish(label+'.inspect.status.json',json.dumps({'argv':q['inspect_argv'],'returncode':result.returncode,'stdout_bytes':len(result.stdout),'stderr_bytes':len(result.stderr)},sort_keys=True).encode())
 if result.returncode or result.stderr or len(result.stdout)>q['inspect_stdout_bound']:raise m.Refusal('diagnostic fixed44 inspect child failed/bound')
 projections=label_projection.project(result.stdout,q['fixed_rows'],q['known_owner_anchors'],ps_identity['unparsed_current_Labels_display'])
 after=current_parent()
 if before!=after or record!=shared_record():raise m.Refusal('held parent/shared record changed during diagnostic')
 return {'parent':before,'shared_record':record,'evidence_inputs':inputs,'retained_domain':domain,'captures':captures,'ps_historical_identity_and_unparsed_display':ps_identity,'structured_inspect_projection':projections}
first=diagnostic_snapshot('diagnostic1');second=diagnostic_snapshot('diagnostic2')
for key in ('parent','shared_record','evidence_inputs','retained_domain'):
 if first[key]!=second[key]:raise m.Refusal('diagnostic readonly snapshots differ:'+key)
label_projection.compare(first['structured_inspect_projection'],second['structured_inspect_projection'])
print(json.dumps({'scope':__doc__,'status':'DIAGNOSTIC_ONLY_FIXED44_STRUCTURED_LABEL_MAPS_OBSERVED_NOT_HISTORICAL_BASELINE_OR_RECOVERY_ACCEPTANCE','parent_profile_sha256':PROFILE_SHA,'diagnostic_profile_sha256':'702b28e306acae22a664d10a7f64045e963fa25f0a48eea1c3dae898c45c184c','historical_label_map_coverage':0,'new_maps_are_historical_baseline':False,'historical_label_map_equality':'UNPROVEN','new_current_structured_baseline':True,'Docker_mutation_or_target_cleanup_authorized':False,'process_recovery_or_shared_reconciliation_authorized':False,'snapshots':[first,second],'signals_sent':0,'pidfd_operations':0,'flock_operations':0,'record_mutations':0,'container_mutations':0,'hold_clearance':False,'process_recovery_executed':False},sort_keys=True))
