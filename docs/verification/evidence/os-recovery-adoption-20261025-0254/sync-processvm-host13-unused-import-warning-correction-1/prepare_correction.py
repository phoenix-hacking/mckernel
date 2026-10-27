"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact unused-import warning observer correction; no production/workload change.
"""
from pathlib import Path
import ast,collections,difflib,hashlib,json,re
D=Path(__file__).resolve().parent;E=D.parent;Q=E/'qualified-sync-processvm-host13-five-stage-source-1';A=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
failure=Q/'actual-qualification-1/FINAL-ARTIFACT-QUALIFICATION.json';first=ref(failure);assert first['sha256'].startswith('8bf9')
P=json.loads((A/'PROFILE.SOURCE-ONLY.json').read_text());X=json.loads((Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());policy=Path(P['inputs']['source_directory_exports'][0]['host_path'])/'syscall_policy.rs';policytext=policy.read_text();new=(A/'OUTPUT/work/evidence/00.stderr').read_text();prior=Path(X['warning_policy']['baseline_Rust_stderr']['path']);old=prior.read_text();header='warning: unused imports: `align_of` and `size_of`'
pattern=r'^warning(?:\[[^\]]+\])?: .+$';delta=collections.Counter(re.findall(pattern,new,re.M))-collections.Counter(re.findall(pattern,old,re.M));removed=collections.Counter(re.findall(pattern,old,re.M))-collections.Counter(re.findall(pattern,new,re.M));assert delta=={header:1,'warning: 142 warnings emitted':1} and removed=={'warning: 141 warnings emitted':1}
for name in ['PROFILE.SOURCE-ONLY.json','ACCEPTANCE-INPUTS.SOURCE-ONLY.json','qualify_produced_cohort.py']:(D/name).write_bytes((Q/name).read_bytes())
T=D/'validator-templates';T.mkdir(mode=0o700);manifest=json.loads((Q/'VALIDATOR-TEMPLATE-SOURCES.json').read_text());changed='qualify_clone_pointer_and_warning_suffix.py'
predicate='''def exact_layout_fixture_unused_import(header, stderr, policy_text, argv):
 if header!='warning: unused imports: `align_of` and `size_of`':return False
 marker='mod f03_sync_child_layout_v2 {';import_line=' use core::mem::{size_of,align_of,offset_of};'
 if policy_text.count(marker)!=1 or policy_text.count(import_line)!=1:return False
 if 'f03_sync_child_event_candidate' not in argv or 'f03_sync_child_fixture' in argv:return False
 body=policy_text.split(marker,1)[1].split('\\n}\\n',1)[0]
 if body.count('#[cfg(f03_sync_child_fixture)]')!=1:return False
 live,fixture=body.split('#[cfg(f03_sync_child_fixture)]',1)
 live=live.replace(import_line,'',1)
 if 'size_of' in live or 'align_of' in live or 'offset_of!(' not in live:return False
 if 'pub static F03_SYNC_CHILD_LAYOUT_ABI' not in fixture or 'size_of::<' not in fixture or 'align_of::<' not in fixture:return False
 line=policy_text[:policy_text.index(import_line)].count('\\n')+1
 context=header+'\\n     --> /src/kernel/rust/syscall_policy.rs:'+str(line)+':18\\n      |\\n'+str(line)+' | '+import_line+'\\n      |                  ^^^^^^^ ^^^^^^^^'
 return stderr.splitlines().count(header)==1 and context in stderr
'''
for path in (Q/'validator-templates').glob('*.py'):
 s=path.read_text()
 if path.name==changed:
  needle="allowed=lambda h: h.startswith('warning: unused import:') or ('redeclares' in h and any(name in h for name in ['lookup_user_context','ihk_mc_pt_set_range']))"
  assert s.count(needle)==1
  replacement=predicate+"policy_path=Path(P['inputs']['source_directory_exports'][0]['host_path'])/'syscall_policy.rs'\npolicy_ref=next(r['postimage'] for r in P['cohort_source_bindings'] if r['relative']=='kernel/rust/syscall_policy.rs')\nassert ref(policy_path)==policy_ref, 'exact compiled policy source changed'\npolicy_text=policy_path.read_text()\nallowed=lambda h: h.startswith('warning: unused import:') or ('redeclares' in h and any(name in h for name in ['lookup_user_context','ihk_mc_pt_set_range'])) or exact_layout_fixture_unused_import(h,newwarn,policy_text,P['exact_commands'][0]['argv'])"
  s=s.replace(needle,replacement,1)
  (D/'EXACT-WARNING-PREDICATE.diff').write_text(''.join(difflib.unified_diff(path.read_text().splitlines(True),s.splitlines(True),fromfile=str(path),tofile=str(T/path.name))))
  manifest['templates'][changed]['template_sha256']=hashlib.sha256(s.encode()).hexdigest()
 ast.parse(s,filename=path.name);(T/path.name).write_text(s)
manifest['single_warning_correction']=dict(parent_manifest=ref(Q/'VALIDATOR-TEMPLATE-SOURCES.json'),changed_template=changed,other_templates_byteexact=True,production_unchanged=True,ABI_policy_unchanged=True);save('VALIDATOR-TEMPLATE-SOURCES.json',manifest)
line=policytext[:policytext.index(' use core::mem::{size_of,align_of,offset_of};')].count('\n')+1
proof=dict(scope=__doc__.splitlines()[0],status='SOURCE_BOUND_MECHANICAL_UNUSED_IMPORT_WARNING_DISPOSITION_FOR_INDEPENDENT_REVIEW',header=header,source=ref(policy),compiled_policy_ref=next(r['postimage'] for r in P['cohort_source_bindings'] if r['relative']=='kernel/rust/syscall_policy.rs'),line=line,column=18,module='f03_sync_child_layout_v2',imported_types='core::mem::size_of/align_of const layout functions; offset_of macro remains used',uses='size_of/align_of occur only inside cfg-disabled49word fixture static; no production expression or ABI declaration changes',actual_fixture_cfg_selected=False,actual_production_cfg_selected=True,baseline_stderr=ref(prior),actual_stderr=ref(A/'OUTPUT/work/evidence/00.stderr'),actual_Rust_warnings=142,baseline_Rust_warnings=141,exact_added_headers=dict(delta),exact_removed_headers=dict(removed),original_failure_preserved=first,actual_producer=ref(A/'OUTPUT/work/evidence/producer-contract.json'),actual_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),retry_driver_byteexact=ref(D/'qualify_produced_cohort.py'),retry_output=str(D/'actual-qualification-1'),original_failed_output_unmodified=True,compiler_container_canonical_Git_grant_actions=0,HOST13_final_consumer_bindings='OPEN_UNLESS_EXACT_REAL_PROOF',independent_disposition_receipt=None);save('WARNING-DISPOSITION.SOURCE-ONLY.json',proof)
assert ref(failure)==first
print(json.dumps(dict(status=proof['status'],line=line,warning_delta=1,new_Rust_warning_count=142,changed_template=ref(T/changed),original_failure=first)))
