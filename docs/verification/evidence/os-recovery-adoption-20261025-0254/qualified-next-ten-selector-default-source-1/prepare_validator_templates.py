"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare the existing actual-artifact gates BEFORE compiler; no gate execution here.
"""
from pathlib import Path
import ast,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;S=E/'next-cohort-artifact-qualification-source-1';T=D/'validator-templates';T.mkdir(mode=0o700)
expected=json.loads((D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());BASE='ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1';marker='__ACTUAL_ADMISSION_BASENAME__';refs={}
for name in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py','qualify_next_providers.py','qualify_retained_f02_owners.py']:
 old=(S/name).read_text();new=old.replace(BASE,marker)
 alias='HostPath' if 'from pathlib import Path as HostPath' in new else 'HP' if 'from pathlib import Path as HP' in new else 'Path'
 new=new.replace('E=D.parent','E='+alias+'('+repr(str(E))+')')
 if name in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_next_providers.py']:
  split=new.index('\nD=');end=new.index('\n',split+1);new=new[:end]+"\nEXPECTED=json.loads("+alias+'('+repr(str(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'))+").read_text())"+new[end:]
 if name=='qualify_clone_pointer_and_warning_suffix.py':
  start=new.index('newwarn=');end=new.index('\nreport=dict(',start)
  new=new[:start]+'''newwarn=(A/'00.stderr').read_text();headers=re.findall(r'^warning(?:\\[[^\\]]+\\])?: .+$',newwarn,re.M)
count_matches=re.findall(r'^warning: ([0-9]+) warnings emitted$',newwarn,re.M);assert len(count_matches)==1;warning_count=int(count_matches[0])
oldwarning=Path(EXPECTED['warning_policy']['baseline_Rust_stderr']['path']);oldtext=oldwarning.read_text();oh=re.findall(r'^warning(?:\\[[^\\]]+\\])?: .+$',oldtext,re.M)
added=Counter(headers)-Counter(oh);removed=Counter(oh)-Counter(headers)
new_actual_headers=[h for h in added if not re.fullmatch(r'warning: [0-9]+ warnings emitted',h)]
allowed=lambda h: h.startswith('warning: unused import:') or ('redeclares' in h and any(name in h for name in ['lookup_user_context','ihk_mc_pt_set_range']))
unknown=[h for h in new_actual_headers if not allowed(h)];assert not unknown,('new Rust warnings need exact source/ABI disposition',unknown)
Cwarning_rows={}
for index,label,baseline_key in [(1,'kernel','baseline_kernel_C_stderr'),(2,'arch','baseline_arch_C_stderr')]:
 text=(A/('%02d.stderr'%index)).read_text();rows=[line for line in text.splitlines() if 'warning:' in line]
 assert all('[-Wunused-variable]' in line or '[-Wunused-const-variable=]' in line for line in rows),('unreviewed C warning category',rows)
 prior=Path(EXPECTED['warning_policy'][baseline_key]['path']).read_text();oldrows=[line.split('warning:',1)[1].strip() for line in prior.splitlines() if 'warning:' in line];newrows=[line.split('warning:',1)[1].strip() for line in rows]
 Cwarning_rows[label]=dict(actual_rows=rows,added=dict(Counter(newrows)-Counter(oldrows)),removed=dict(Counter(oldrows)-Counter(newrows)),stderr=ref(A/('%02d.stderr'%index)))
ld=(A/'03.stderr').read_text();assert ld==EXPECTED['warning_policy']['new_ld_warning_must_equal']
comparison=dict(original=ref(oldwarning),warning_headers_equal=oh==headers,new_only=dict(added),old_only=dict(removed),Rust_warning_count=warning_count,new_source_bound_warning_headers=new_actual_headers,new_warning_disposition_required=bool(new_actual_headers),C_warnings=Cwarning_rows,prior_two_fixed_LP64_declaration_warnings_remain_debt=True)
''' +new[end:]
  new=new.replace('Rust_warning_count=140','Rust_warning_count=warning_count').replace('Rust_warnings=140','Rust_warnings=warning_count').replace('kernel_C_warning_count=7,arch_C_compiler_stderr_empty=True',"current_C_warning_rows=Cwarning_rows")
 elif name=='qualify_actual_f02_profile.py':
  # Reuse the accepted universal formatting/panic/scoped-clone body with only
  # the exact source-predicted provider-set change and fresh clone proof hash.
  tree=ast.parse(new)
  for node in tree.body:
   if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
    target=node.targets[0].id
    if target=='NEXT_REMOVED':new=new.replace(ast.get_source_segment(new,node),"NEXT_REMOVED=set(EXPECTED['cumulative_seed_undefined_removed'])-F02_OWNERS")
  # Reparse after the first replacement to retain correct source offsets.
  tree=ast.parse(new)
  node=next(n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='new_assert')
  new=new.replace(ast.get_source_segment(new,node),"new_assert=\"assert _reuse_elf_undefined(new) == (_reuse_elf_undefined(old) - set(original_panics) - _exact_removed) | _exact_added, 'unexpected provider delta outside frozen ten-selector ABI'\"")
  needle="exec(compile(ast.Module(body=nodes,type_ignores=[]),str(DRIVER)+':UNCHANGED_READONLY_RUST_GATES','exec'),ns)";assert needle in new;new=new.replace(needle,"ns.update(_exact_removed=set(EXPECTED['cumulative_seed_undefined_removed']),_exact_added=set(EXPECTED['cumulative_seed_undefined_added']))\n"+needle)
  # The accepted scoped witness starts at original current290, so F02+all later
  # exact providers must be removed; NEXT_ADDED remains the same two C exports.
  start=new.index(" expected=(E/'f02-default");end=new.index(" report['phases']['current_profile",start)
  new=new[:start]+" actual_names={line.split(None,1)[1] for line in undefined.stdout.splitlines()}\n assert actual_names==set(EXPECTED['expected_new_undefined']), 'all other provider witnesses remain exact beyond frozen ten-selector ABI'\n"+new[end:]
 elif name=='qualify_next_providers.py':
  start=new.index('expected=[');end=new.index(';report=',start)
  new=new[:start]+"expected=EXPECTED['all_Rust_exports']\nremoved_kernel=set(EXPECTED['expected_C_function_sets']['CMakeFiles/mckernel.img.dir/syscall.c.o']['remove'])\nremoved_arch=set(EXPECTED['expected_C_function_sets']['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']['remove'])"+new[end:]
  start=new.index(' source_path=Path(');end=new.index(' for name,type_,size in',start);new=new[:start]+new[end:]
  new=new.replace('actual_twenty_three_Rust_exports','actual_thirty_three_Rust_exports').replace('PASS_ACTUAL_NEXT_23_RUST_EXPORTS','PASS_ACTUAL_TEN_SELECTOR_33_RUST_EXPORTS')
  # Root's actual copied profile must select exactly this frozen compiler plan.
  needle=" # Reuse the exact Root runner's source-only map"
  replacement=" assert P['exact_commands']==json.loads(Path(EXPECTED['profile_template']['path']).read_text())['exact_commands'], 'actual compiler argv differs from prepublished plan'\n"+needle
  new=new.replace(needle,replacement)
 # Do not infer completed actual statuses from the static templates.
 ast.parse(new,filename=name);(T/name).write_text(new)
 refs[name]=dict(parent=expected['existing_completed_base_gate_sources'][name],template_sha256=hashlib.sha256(new.encode()).hexdigest())
for name in ['profile_clone_witness.py','narrow_f02_alias_identity.py']:(T/name).write_bytes((S/name).read_bytes())
(D/'VALIDATOR-TEMPLATE-SOURCES.json').write_text(json.dumps(dict(scope=__doc__.splitlines()[0],status='STATIC_PREPARED_NOT_EXECUTED_NEW_ARTIFACT_GATES',runtime_authority=None,templates=refs,reuse='Same accepted observer gate bodies; exact ten-selector expected sets prepublished; actual Root basename/produced bytes remain unbound.'),indent=2)+'\n')
print(json.dumps(dict(status='FIVE_READONLY_GATE_TEMPLATES_AND_TWO_UNCHANGED_HELPERS_READY',future_admission=None,compiler_runs=0)))
