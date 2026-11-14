"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse exact accepted failed-owner export algorithm with only ROOT literal changed.
"""
from pathlib import Path
import ast,difflib,hashlib,json,os,stat
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7}
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1')
OLD=B/'following-process-recovery-cases-1/abi2-helper-c020-successor-1/case-235/retirement-preparation-1'
CASE=B/'fork-v3-matched-process-successor-1/case-235';CAP=CASE/'actual-v3-native235-owner-capture-1'
NONCE='8646cb69db21440ca31573ab1b3d0691';PARENT=Path('/home/holden/mckernel-work/scratch/n235v1/p');ATTEMPT=PARENT/('attempt-'+NONCE);OWNER=PARENT.with_name(PARENT.name+'.owner-'+NONCE)
def ref(p):
 r=p.read_bytes();s=p.stat();return dict(path=str(p),bytes=len(r),sha256=hashlib.sha256(r).hexdigest(),identity={k:getattr(s,k)for k in ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')})
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
source=OLD/'readonly_export_exact_owner.py';a=source.read_text();assert hashlib.sha256(a.encode()).hexdigest()=='29de9ca48b7a4ad1b1570123ed4a92eddabeae597ebe32c397978bf91e656aa2'
oldroot="/home/holden/mckernel-work/scratch/n235a1/p.owner-96b6b07d17d149f799c3ebf4e6b95e35";assert a.count(oldroot)==1
b=a.replace(oldroot,str(OWNER));out=D/'readonly_export_exact_owner.py';out.write_text(b);ast.parse(b)
# Enforce unchanged executable AST except the ROOT assignment.
def normalized(txt):
 t=ast.parse(txt)
 for n in t.body:
  if isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='ROOT'for z in n.targets):n.value=ast.Constant(value='ROOT_LITERAL_ONLY')
 return ast.dump(t,include_attributes=False)
assert normalized(a)==normalized(b)
(D/'ROOT-LITERAL-ONLY.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(source),tofile=str(out))))
retained=D/'retained-failed-inputs';retained.mkdir(mode=0o700);rows=[]
for category,root,names in [('owner-capture',CAP,['status.json','stdout','stderr','child-start.json','direct-join.json','stream-and-group-close.json','case-binding.json']),('actual-guest',ATTEMPT,['result.json','serial.log','debugcon.log','qemu.stdout','qemu.stderr','qmp.transcript.json'])]:
 target=retained/category;target.mkdir(mode=0o700)
 for name in names:
  p=root/name
  if not p.exists():continue
  s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size<=32*2**20
  r=ref(p);raw=p.read_bytes();q=target/name;q.write_bytes(raw);assert ref(q)['sha256']==r['sha256'];rows.append(dict(original=r,retained=ref(q)))
write(D/'FAILED-RAW-RETENTION-MAP.json',dict(scope=__doc__.splitlines()[0],status='RETAINED_ACTUAL_FAILED_GUEST_AND_OUTER_CAPTURE_ONLY_ROOT_OWNER_EXPORT_PENDING',files=rows,root_owner_export=None))
prior=json.loads((OLD/'READY-RETIREMENT-PACKET.json').read_text());argv=list(prior['exact_next_argv']);argv[-1]=str(out)
queries=[[x.replace('96b6b07d17d149f799c3ebf4e6b95e35',NONCE)for x in q]for q in prior['exact_separate_query_argv']]
# Native diagnostic owner owns permanent lock and Docker name/label. It does
# not publish native SDK/image lease files; those are conflict gates elsewhere.
paths=json.loads((CASE/'final-runtime-ready-1/root-live-admission-1/ROOT-EXACT-READONLY-ADMISSION-OPERATION-1.json').read_text())
adir=CASE/'final-runtime-ready-1/root-live-admission-1/read_only_native235_admission.py'
t=ast.parse(adir.read_text());canonical=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='paths'for z in n.targets))
status=json.loads((CAP/'status.json').read_text());assert status['returncode']==1 and status['direct_child_joined'] and status['process_group_absent'] and status['streams_closed']
r=dict(scope=__doc__.splitlines()[0],status='CURRENT_FAILED235_RETENTION_AND_READONLY_EXPORT_READY_PENDING_FRESH_INDEPENDENT_ROOT_REVIEW',nonce=NONCE,attempt=str(ATTEMPT),owner_root=str(OWNER),owner_root_algorithm='DiagnosticOwner.__init__: evidence=parent.with_name(parent.name+".owner-"+nonce); native owner holds permanent27:4, owns exact Docker nonce/name/label and command ledgers; no native SDK/image lease publication.',accepted_algorithm=ref(source),accepted_prior_physical_review=ref(OLD/'INDEPENDENT-FAILED-NATIVE235-PHYSICAL-ACCEPTANCE-1.json'),new_export_source=ref(out),source_algorithm_changes=0,next_readonly_export_argv=argv,separate_current_name_label_query_argv=queries,failed_capture=ref(CAP/'status.json'),failed_guest=ref(ATTEMPT/'result.json'),retention_map=ref(D/'FAILED-RAW-RETENTION-MAP.json'),canonical_conflict_paths=canonical,
profile=prior['profile'],fresh_export=None,fresh_name_label_queries=None,fresh_current_proc_census=None,fresh_mutex_and_conflict_absence=None,physical_clearance=False,native_acceptance=False,cleanup_authorized=False,
sequence=['Root independently reviews exact new export source/argv and executes under existing joined closed capture. No old release reused.','Decode every exported file; verify source length/hash and root metadata, command reaps, exact container identity, inspect exited/no host PID and successful exact authenticated removal/postremove queries, terminal absence_verified/lease_retained and no unresolved command ledgers. Guest result reapedtrue/QEMUnamespacePID10 exit-9 is evidence, not alone host physical acceptance.','Root executes separate fresh exactnonce name and label queries; fresh PROC59ef complete publisher-free census and mutex27:4 exact acquire/readback under existing reviewed observer; all8current canonical paths positively absent. Source/export identifies container-ID needed for fresh exact-ID query.','If export/queries prove owner already removed exact container and releasedlock, no duplicate cleanup effect is needed; independently accept actual physical retirement from current evidence.','If any container/QEMU/group/ownership remains or export is uncertain, retain all records and root-ownedlease; bind actual exported identities into separately reviewed existing cleanup/preflight/postjoin engine. No guessedCID, rawrm/unlink or new cleanup authorized by source-onlypacket.'],
failed_family='New actual tuple failed:13/235B parentstart; childexec34bytes+exit231; parentcapturedeadline. Earlier poolquery235failure remains separate and retired; no unchanged native retry.',worker_root_Docker_guest_effects=0)
write(D/'CURRENT-FAILED235-RETIREMENT-PACKET.json',r)
print(json.dumps(dict(status=r['status'],retained_files=len(rows),export_source=r['new_export_source'],canonical_paths=len(canonical))))
