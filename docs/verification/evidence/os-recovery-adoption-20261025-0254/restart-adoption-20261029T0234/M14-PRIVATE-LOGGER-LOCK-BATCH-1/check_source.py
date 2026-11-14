"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only private source checks; no compiler, preprocessor, host or native work.
"""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;A=D.parent;R=Path('/home/holden/mckernel');F=A/'M14-PRIVATE-FOUR-LOGGER-BATCH-1';L=A/'M14-PRIVATE-PTRACE-CLONE-LOCK-BRIDGE-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def token(s):return re.findall(r'"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]',s)
m=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());fm=json.loads((F/'FILEMAP.SOURCE-ONLY.json').read_text());lr=json.loads((L/'SOURCE-READY.json').read_text());assert ref(F/'FILEMAP.SOURCE-ONLY.json')==m['four_logger_filemap'] and ref(F/'SOURCE_READY.json')==m['four_logger'] and ref(L/'SOURCE-READY.json')==m['lock_pair']
rows={x['proposed_path']:x for x in m['files']};assert len(rows)==9
for name,row in rows.items():
 assert ref(D/'postimage'/name)==row['postimage']
 if row['canonical_preimage'] is not None:assert ref(R/name)==row['canonical_preimage'] and (D/'preimage'/name).read_bytes()==(R/name).read_bytes()
for x in fm['files']:
 assert ref(Path(x['postimage']['path']))==x['postimage']
 if x['reused_leaf_exact']:assert (D/'postimage'/x['proposed_path']).read_bytes()==Path(x['postimage']['path']).read_bytes()
assert (D/'postimage/kernel/rust/ptrace_clone_noirq.rs').read_bytes()==Path(lr['source']['path']).read_bytes()
old=(F/'postimage/kernel/syscall.c').read_text().splitlines(True);new=(D/'postimage/kernel/syscall.c').read_text().splitlines(True);original=(R/'kernel/syscall.c').read_text().splitlines(True);first=m['lock_first_line']-1;stop=first+m['lock_lines'];assert len(old)==len(new)==len(original) and m['lock_lines']==13
assert old[:first]==new[:first] and old[stop:]==new[stop:]
a=''.join(old[first:stop]);b=new[first:stop];assert b[0].strip()=='#if defined(MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ)' and b[3].strip()=='#else' and b[-1].strip()=='#endif';assert token(a)==token(b[4]+b[5]);assert all(not x.strip() for x in b[6:-1]);assert b[1].strip().startswith('extern void ptrace_report_clone_noirq_lock_bridge(') and b[2].strip().startswith('extern void ptrace_report_clone_noirq_unlock_bridge(')
directives=lambda lines:[(i+1,s)for i,s in enumerate(lines)if re.match(r'\s*#\s*(?:line\b|[0-9])',s)]
assert directives(original)==directives(old)==directives(new)
leaf=(D/'postimage/kernel/rust/ptrace_clone_noirq.rs').read_text()
for op in ('lock','unlock'):
 assert leaf.count('lock_helpers::__mcs_rwlock_writer_'+op+'_noirq(lock_addr as *mut McsRwlockLock, node);')==1
assert leaf.count('#[no_mangle]')==2 and 'cpu_disable_interrupt' not in leaf and 'cpu_restore_interrupt' not in leaf
assert (D/'postimage/kernel/rust/syscall_policy.rs').read_bytes()==(F/'postimage/kernel/rust/syscall_policy.rs').read_bytes()
assert 'ptrace_report_clone_body_result(' not in (D/'LOGGER-LOCK-BATCH.PRIVATE-NOT-APPLIED.patch').read_text()
cmake=(D/'postimage/kernel/CMakeLists.txt').read_text();lib=(D/'postimage/kernel/rust/lib.rs').read_text()
for needle in ('f03_ptrace_clone_noirq_candidate','MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ','rust/ptrace_clone_noirq.rs'):assert cmake.count(needle)==1
assert lib.count('mod ptrace_clone_noirq;')==1 and 'all(f03_ptrace_clone_noirq_candidate, target_arch = "x86_64")' in lib
oracle=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389
moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};expected=[r for r in records if r['function'] in moved];assert len(expected)==4
projected=[]
for row in fm['files']:
 if not row['reused_leaf_exact']:continue
 s=(D/'postimage'/row['proposed_path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',s,re.S):
  body=match.group(1);filelit=re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1);funclit=re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1);line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()' in body;projected.append(dict(file=ast.literal_eval(filelit).rstrip('\0'),function=ast.literal_eval(funclit).rstrip('\0'),fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda row:tuple(row[k]for k in fields)
assert Counter(map(key,projected))==Counter(map(key,expected));assert Counter(map(key,[r for r in records if r['function'] not in moved]+projected))==Counter(map(key,records))
print(json.dumps(dict(status='PASS_PRIVATE_COMPOSITION_SOURCE_CHECKS',source_paths=len(rows),reused_leaf_count=5,unmodified_syscall_lines_outside_13=True,unchanged_original_newline_and_directive_positions=True,existing_unselected_C_lock_tokens_exact=True,exact_lock_pointer_and_node_forwarding=True,original389_counter_equal=True,projected_rows=projected,compiler_or_preprocessor_or_native_calls=0,oracle=ref(oracle)),indent=2))
