"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent exact-placement and complete source location identity review only.
"""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;P=D.parent;OLD=P.parent

def read(p):return json.loads(p.read_bytes())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):assert ref(Path(row['path']))==row;return Path(row['path'])
ready=read(P/'SOURCE-READY.json');assert ref(P/'SOURCE-READY.json')['sha256']=='41a3fc9cc087008c30f2e5bc34919a25419e5bfd8f6f89d2d216dd0da2cad4f4'
for row in ready['files'].values():auth(row)
prior=read(auth(ready['prior_body_acceptance_and_composition_defect_review']));assert prior['decision']=='FAIL_SOURCE_COMPOSITION_REQUIRES_LINE_PRESERVING_MODULE_PLACEMENT'and prior['new_two_leaf_body_decision']=='PASS_SOURCE_AT_ORIGINAL_DEFINED_CALLBACK_SCOPE_ONLY'
m=read(P/'FILEMAP.SOURCE-ONLY.json');old=read(OLD/'FILEMAP.SOURCE-ONLY.json');rows={r['proposed_path']:r for r in m['files']};oldrows={r['proposed_path']:r for r in old['files']};assert set(rows)==set(oldrows)and len(rows)==11
for name,row in rows.items():
 auth(row['postimage']);assert row['canonical_preimage']==oldrows[name]['canonical_preimage']
 if name!='kernel/rust/syscall_policy.rs':assert Path(row['postimage']['path']).read_bytes()==Path(auth(oldrows[name]['postimage'])).read_bytes()
name='kernel/rust/syscall_policy.rs';pre=(P/'preimage'/name).read_text();post=(P/'postimage'/name).read_text();bad=Path(auth(oldrows[name]['postimage'])).read_text();assert pre==(OLD/'preimage'/name).read_text()
modules=m['moved_module_blocks'];assert len(modules)==len(set(modules))==6
blocks=[];stripped=bad
for module in modules:
 pattern=r'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing\.\n(?:#\[cfg\([^\n]+\)\]\n)?#\[path = "'+module+r'\.rs"\]\nmod '+module+r';\n'
 hits=list(re.finditer(pattern,stripped));assert len(hits)==1;block=hits[0].group();blocks.append(block);stripped=stripped.replace(block,'',1)
assert stripped==pre and post==pre+''.join(blocks)
assert all(post.count('mod '+module+';')==1 for module in modules)

def sites(text,macro):
 return[dict(line=i,column=match.start()+1,text=line)for i,line in enumerate(text.splitlines(),1)for match in re.finditer(r'\b'+macro+r'!\s*\(',line)]
source_table={}
for filename in ['kernel/rust/syscall_policy.rs','kernel/rust/lib.rs']:
 before=(P/'preimage'/filename).read_text();after=(P/'postimage'/filename).read_text();source_table[filename]={}
 for macro in ['line','file','column']:
  a=sites(before,macro);b=sites(after,macro);assert a==b;source_table[filename][macro]=a
assert len(source_table[name]['line'])==53
retained_table=read(P/'LOCATION-MACRO-IDENTITIES.json');assert retained_table['macros']==source_table
assert [b['line']-a['line']for a,b in zip(sites(pre,'line'),sites(bad,'line'))]==[25]*53
# Original negative candidate still fails; corrected insertion only at EOF cannot
# move any preexisting expansion coordinate. No expected metadata is rewritten.
assert sites(bad,'line')!=sites(pre,'line')
leaves=[r for r in m['files']if r['reused_leaf_exact']];assert len(leaves)==7
oracle_path=OLD.parents[1]/'F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle_path)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';oracle=read(oracle_path)['records'];projected=[]
for row in leaves:
 leaf=Path(row['postimage']['path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',leaf,re.S):
  body=match.group(1);get=lambda field:ast.literal_eval(re.search(field+r': b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()'in body
  projected.append(dict(file=get('file'),function=get('func'),fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda r:tuple(r[f]for f in fields);moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};assert len(projected)==4;assert Counter(map(key,[r for r in oracle if r['function']not in moved]+projected))==Counter(map(key,oracle))
cpre=(P/'preimage/kernel/syscall.c').read_text();cpost=(P/'postimage/kernel/syscall.c').read_text();assert cpre.count('\n')==cpost.count('\n');directives=lambda text:[(i,line)for i,line in enumerate(text.splitlines(),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert directives(cpre)==directives(cpost)
result=dict(scope=__doc__.splitlines()[0],status='PASS_EXACT_EOF_PLACEMENT_AND_ALL_INHERITED_SOURCE_LOCATION_IDENTITIES',source_ready=ref(P/'SOURCE-READY.json'),patch=ready['patch'],new_policy=ref(P/'postimage'/name),prior_body_review=ready['prior_body_acceptance_and_composition_defect_review'],all11paths_checked=True,only_policy_postimage_changed=True,entire_frozen119policy_exact_prefix=True,six_original_module_blocks_exact_EOF=True,all_seven_leaves_unchanged=True,macro_counts={file:{macro:len(rows)for macro,rows in values.items()}for file,values in source_table.items()},all_macro_line_column_fulltext_exact=True,original_failed_plus25_preserved=True,original389_source_projection_equal=True,original389_oracle=ref(oracle_path),C_directives_newlines_and_other_nonpolicy_postimages_exact=True,actual_compiler_preprocessor_ELF_HOST_native_guard_cleanup_calls=0,runtime_authority=None)
(D/'CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],macro_counts=result['macro_counts'],report=ref(D/'CHECKS.json'))))
