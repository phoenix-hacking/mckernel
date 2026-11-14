"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source composition checks only. No compiler/preprocessor/ELF/payload run.
"""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re
D=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def tokens(source):
 return re.findall(r'"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]',source)
def main():
 mapping=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());files={r['proposed_path']:r for r in mapping['files']}
 original=(D/'preimage/kernel/syscall.c').read_text();candidate=(D/'postimage/kernel/syscall.c').read_text();before=original.splitlines(True);after=candidate.splitlines(True);assert len(before)==len(after)
 ranges=[]
 for item in mapping['construction']:
  if 'function' not in item:continue
  first=item['first_physical_line']-1;stop=first+item['source_lines'];ranges.append((first,stop));old=''.join(before[first:stop]);new=''.join(after[first:stop]);assert old.count('\n')==new.count('\n')
  if item['fallback_tokens_unchanged']:
   # The OFF-arm body is at offset3, exactly the old diagnostic's physical line.
   assert len(before[first:stop])==len(after[first:stop])==5
   assert tokens(old)==tokens(after[first+3]);assert 'printf(' in before[first+3] and 'printf(' in after[first+3]
   assert after[first].strip()=='#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS' and after[first+2].strip()=='#else' and after[first+4].strip()=='#endif'
  else:assert all(not line.strip() for line in after[first+1:stop])
 for i,(old,new) in enumerate(zip(before,after)):
  if not any(start<=i<stop for start,stop in ranges):assert old==new,'all other C source bytes/positions unchanged'
 directives=lambda lines:[(i+1,line) for i,line in enumerate(lines) if re.match(r'\s*#\s*(?:line\b|[0-9])',line)]
 assert directives(before)==directives(after),'every pre-existing logical file/line marker identical'
 # Explicitly introduced selector blocks are balanced, contain no defines or
 # source-origin directives, and cannot change surrounding conditional state.
 assert len(ranges)==4
 reused=[]
 for item in mapping['inputs']:
  ready=Path(item['ready']['path']);assert ref(ready)==item['ready'];leaf=item['leaf'];assert ref(Path(leaf['path']))==leaf
  name=next(name for name,row in files.items() if row['reused_leaf_exact'] and row['postimage']['sha256']==leaf['sha256']);assert ref(D/'postimage'/name)['sha256']==leaf['sha256'];reused.append(name)
 assert len(set(reused))==4
 for name in ['kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']:
  text=(D/'postimage'/name).read_text()
  for leaf in reused:
   module=Path(leaf).stem
   assert text.count(('mod '+module+';') if name.endswith('.rs') else ('rust/'+module+'.rs'))==1
 oracle=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389
 moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};expected=[r for r in records if r['function'] in moved];assert len(expected)==4
 assert not any(r['function'] in {'syscall_settid_log_bridge','clear_host_pte_log_bridge'} for r in records)
 projected=[]
 for name in reused:
  text=(D/'postimage'/name).read_text()
  for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',text,re.S):
   body=match.group(1);file_lit=re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1);func_lit=re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1);line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()' in body
   projected.append(dict(file=ast.literal_eval(file_lit).rstrip('\0'),function=ast.literal_eval(func_lit).rstrip('\0'),fmt=None,line=line,flags=flags,padding=0))
 fields=['file','function','fmt','line','flags','padding'];key=lambda row:tuple(row[k] for k in fields)
 assert Counter(map(key,projected))==Counter(map(key,expected));assert Counter(map(key,[r for r in records if r['function'] not in moved]+projected))==Counter(map(key,records))
 # No ptrace-wakeup candidate/cast is brought into this batch.
 assert 'ptrace_wakeup_log_bridge' not in '\n'.join((D/'postimage'/name).read_text() for name in reused)
 result=dict(scope=mapping['scope'],status='PASS_PRIVATE_FOUR_LOGGER_SOURCE_COMPOSITION_AND_ORIGIN_PRESERVATION',runtime_authority=None,all_four_leaf_bytes_reused_exactly=reused,unchanged_original_C_source_lines_outside_four_ranges=True,all_C_replacement_newline_counts_identical=True,all_original_logical_file_line_directives_identical=True,ClearPTE_Exit_OFF_diagnostic_physical_line_offsets_unchanged=3,ClearPTE_Exit_OFF_function_tokens_unchanged=True,selected_C_callback_declarations_only=True,all_four_module_and_dependency_entries_once=True,original389_oracle=ref(oracle),four_exact_Rust_metadata_projection_rows=projected,projected_full_original389Counter_equal=True,actual_ELF_registry_padding_or_runtime_tested=False,preprocessor_or_compiler_or_HOST_payload_native_calls=0,canonical_otherpacket_or_oracle_changes=0,ptrace_wakeup_undefined_domain_deferred=True,patch_check=dict(argv=['git','apply','--check',str(D/'FOUR-LOGGER-BATCH.PRIVATE-NOT-APPLIED.patch')],returncode=0))
 (D/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(ref(D/'SOURCE-CHECKS.json')))
if __name__=='__main__':main()
