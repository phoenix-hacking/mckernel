"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact accepted publication aliases only; no mutation or global shape relaxation.
"""
from pathlib import Path
import hashlib,json,difflib
D=Path(__file__).resolve().parent;P=D.parent;E=P.parents[2]
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(n,v):
 p=D/n;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
b=json.loads((P/'BINDINGS.json').read_text());A=E/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3';C=E/'next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort'
names=[('physical.CHILD-STARTED.json',2221578),('held.CHILD-STARTED.json',2222140),('ROOT-PHYSICAL-CAPTURE.COMPLETE.json',2221578),('ROOT-HELD-CAPTURE.COMPLETE.json',2222140),('INDEPENDENT-FINITE-REVIEW.PASS.json',2221500),('PREWARM_READY.json',2221500)]
fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns');pairs=[]
for name,pid in names:
 canonical=A/'FINITE-REVIEW-HANDOFF'/name;alias=canonical.with_name(name+'.complete-source-'+str(pid));r=ref(canonical);a=ref(alias);s=canonical.lstat();z=alias.lstat()
 assert all(getattr(s,k)==getattr(z,k) for k in fields) and (s.st_uid,s.st_gid,s.st_mode&4095,s.st_nlink)==(1000,1000,0o400,2)
 assert r in b['protected'] and (r['bytes'],r['sha256'])==(a['bytes'],a['sha256'])
 pairs.append(dict(canonical=r,alias=a,publisher_pid=pid,expected={k:getattr(s,k) for k in fields}))
contract=put('EXACT-PUBLISHER-ALIAS-CONTRACT.json',dict(scope=b['scope'],runtime_authority=None,publisher_source=ref(C/'handoff_common.py'),actual_publication=ref(A/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json'),actual_reviewer_bindings=ref(C/'REVIEWER-ACTUAL-BINDINGS.json'),source_function='atomic_json',source_lines='42-57',contract='O_EXCL complete-source0400, complete write+fsync, os.link(tmp,path), retain both names, dirfsync',pairs=pairs,expected_nlink=2,other_files_keep_original_nlink1=True))
failure=put('ACTUAL-FULL-CALLBACK-REFUSAL-1.json',dict(scope=b['scope'],runtime_authority=None,status='PRESERVED_READONLY_PREFLIGHT_REFUSAL',source=ref(P/'retire_exact_failed_guard.py'),bindings=ref(P/'BINDINGS.json'),script=ref(P/'actual_cid_preflight.py'),actual_tool_chunk='6bd2e2',actual_tool_exit_code=1,error='reviewed_exact_idle_guard_kernel_protocol.Refusal: protected regular file shape',first_refusing_protected_row_identified_by_exact_declared_metadata=pairs[0],actor_pid_birth_not_persisted=True,actual_guard_returned_before_callback_by_control_flow=True,guard_clock_not_persisted_by_failed_script=True,target_process_or_query_or_pidfd_or_signal_or_lock_effects=0))
b.update(publisher_alias_contract=contract,pre_alias_correction_executor=ref(P/'retire_exact_failed_guard.py'),actual_cid_leaf_read=ref(P/'ACTUAL-CID-LEAF-READ-1.json'),preserved_full_callback_refusal=failure)
binding=put('BINDINGS.json',b);code=(P/'retire_exact_failed_guard.py').read_text().replace("BINDINGS_SHA='6672c9eaa066b4c134c9fb3c30417bfc11a4e57b343837547b37d86029ea1ce2'","BINDINGS_SHA='"+binding['sha256']+"'")
addition='''def publisher_alias_identity(path):
 contract=T.authenticated(B['publisher_alias_contract'],True)
 pair=next((p for p in contract['pairs'] if p['canonical']['path']==str(path)),None)
 need(pair is not None,'only exact accepted publisher canonical row')
 tree=ast.parse(T.authenticated(B['primitive']))
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='file_identity')
 comparisons=[n for n in ast.walk(node) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Attribute) and isinstance(n.left.value,ast.Name) and n.left.value.id=='before' and n.left.attr=='st_nlink' and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Constant) and n.comparators[0].value==1]
 need(len(comparisons)==1 and pair['expected']['st_nlink']==contract['expected_nlink']==2,'exact original single-link shape anchor to fixed expected2')
 comparisons[0].comparators[0].value=2;ast.fix_missing_locations(node);context=dict(vars(M))
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SELF),'exec'),context)
 rows=[]
 for key in ('canonical','alias'):
  subject=pair[key];T.authenticated(subject);p=Path(subject['path']);before=p.lstat()
  need(all(getattr(before,k)==v for k,v in pair['expected'].items()),'fixed accepted alias node/owner/mode/link/size/time identity')
  row,raw=context['file_identity'](p);after=p.lstat()
  need(raw is None and all(getattr(after,k)==v for k,v in pair['expected'].items()) and row['sha256']==subject['sha256'] and row['size']==subject['bytes'],'same original stable FD/linked-node/byte checks for both retained names')
  rows.append(row)
 need({k:v for k,v in rows[0].items() if k!='path'}=={k:v for k,v in rows[1].items() if k!='path'},'both exact names remain same protected inode')
 return rows[0],None

'''
code=code.replace('def protected_inputs(release,profile):',addition+'def protected_inputs(release,profile):')
old="T.authenticated(r);row,_=(controlled_cid_identity(Path(r['path'])) if r==B['controlled_cid_subject'] else M.file_identity(Path(r['path'])))"
new="T.authenticated(r);aliases=T.authenticated(B['publisher_alias_contract'],True)['pairs'];row,_=(controlled_cid_identity(Path(r['path'])) if r==B['controlled_cid_subject'] else publisher_alias_identity(Path(r['path'])) if any(p['canonical']==r for p in aliases) else M.file_identity(Path(r['path'])))"
assert code.count(old)==1;code=code.replace(old,new)
anchor="for key in ['controlled_cid_subject','pre_identity_correction_executor','failed_rebind_attempt']:T.authenticated(B[key])";assert code.count(anchor)==1
checks="""
 for key in ['publisher_alias_contract','pre_alias_correction_executor','actual_cid_leaf_read','preserved_full_callback_refusal']:T.authenticated(B[key])
 contract=T.authenticated(B['publisher_alias_contract'],True)
 for key in ['publisher_source','actual_publication','actual_reviewer_bindings']:T.authenticated(contract[key])
 pub=T.authenticated(contract['actual_publication'],True);reviewer=T.authenticated(contract['actual_reviewer_bindings'],True)
 need(pub['status'].startswith('PASS_FETCHED_CURRENT118_') and pub['runtime_authority'] is None and any(r['actual']==contract['publisher_source'] for r in pub['rows']) and reviewer['static_refs']['handoff_common']==contract['publisher_source'],'actual accepted publisher source contract')
 need(len(contract['pairs'])==6 and all(p['canonical'] in B['protected'] and p['alias']['path']==p['canonical']['path']+'.complete-source-'+str(p['publisher_pid']) and p['expected']['st_nlink']==2 for p in contract['pairs']),'only six fixed accepted publication pairs')
"""
code=code.replace(anchor,anchor+checks)
anchor="rows.update({k:B[k] for k in ('pre_identity_correction_executor','failed_rebind_attempt')})";assert code.count(anchor)==1
code=code.replace(anchor,anchor+"\n rows.update({k:B[k] for k in ('publisher_alias_contract','pre_alias_correction_executor','actual_cid_leaf_read','preserved_full_callback_refusal')})")
(D/'retire_exact_failed_guard.py').write_text(code)
for name in ['test_guard_rebind.py','test_controlled_cid_identity.py']:(D/name).write_bytes((P/name).read_bytes())
(D/'test_controlled_cid_identity.py').write_text((D/'test_controlled_cid_identity.py').read_text().replace("m.B['pre_identity_correction_executor']","m.B['pre_alias_correction_executor']"))
(D/'MINIMAL-CORRECTION-DIFF.patch').write_text(''.join(difflib.unified_diff(Path(b['pre_identity_correction_executor']['path']).read_text().splitlines(True),code.splitlines(True),fromfile=b['pre_identity_correction_executor']['path'],tofile=str(D/'retire_exact_failed_guard.py'))))
print(json.dumps(dict(executor=ref(D/'retire_exact_failed_guard.py'),bindings=binding,contract=contract,preserved_failure=failure)))
