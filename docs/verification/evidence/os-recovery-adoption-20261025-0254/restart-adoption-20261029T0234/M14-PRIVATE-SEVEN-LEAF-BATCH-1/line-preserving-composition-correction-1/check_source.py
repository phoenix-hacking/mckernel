"""Functional OS source identity/composition checks only; no security testing.
No compiler/preprocessor/ELF/HOST/native or oracle mutation.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,re,ast
D=Path(__file__).resolve().parent;OLD=D.parent;ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
m=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());old=json.loads((OLD/'FILEMAP.SOURCE-ONLY.json').read_text());rows={r['proposed_path']:r for r in m['files']};assert len(rows)==11
for r in m['files']:
 f=r['proposed_path'];assert ref(D/'postimage'/f)==r['postimage']
 if r['canonical_preimage']is not None:assert ref(ROOT/f)==r['canonical_preimage'] and (D/'preimage'/f).read_bytes()==(ROOT/f).read_bytes()
 if f!='kernel/rust/syscall_policy.rs':assert (D/'postimage'/f).read_bytes()==(OLD/'postimage'/f).read_bytes()
leaves=[r for r in m['files']if r['reused_leaf_exact']];assert len(leaves)==7
name='kernel/rust/syscall_policy.rs';pre=(D/'preimage'/name).read_text();post=(D/'postimage'/name).read_text();bad=(OLD/'postimage'/name).read_text();assert post.startswith(pre);tail=post[len(pre):];assert len(re.findall(r'^mod [A-Za-z_]+;',tail,re.M))==6
for module in m['moved_module_blocks']:
 assert post.count('mod '+module+';')==1 and tail.count('mod '+module+';')==1
 assert post.index('mod '+module+';')>=len(pre)
# Every physical source location consumed by Rust built-in location macros,
# not merely four moved C-origin Ddebug rows. Preserve line text and columns too.
def sites(text,macro):
 found=[]
 for line_no,line in enumerate(text.splitlines(),1):
  for match in re.finditer(r'\b'+macro+r'!\s*\(',line):found.append(dict(line=line_no,column=match.start()+1,text=line))
 return found
macro_map={}
for f in ['kernel/rust/syscall_policy.rs','kernel/rust/lib.rs']:
 a=(D/'preimage'/f).read_text();b=(D/'postimage'/f).read_text();macro_map[f]={}
 for macro in ['line','file','column']:
  assert sites(a,macro)==sites(b,macro),(f,macro);macro_map[f][macro]=sites(b,macro)
assert len(macro_map[name]['line'])==53
assert len(sites(bad,'line'))==53 and [b['line']-a['line']for a,b in zip(sites(pre,'line'),sites(bad,'line'))]==[25]*53
assert all(not sites((D/'postimage'/r['proposed_path']).read_text(),'line')for r in leaves)
# Exact C bytes from predecessor preserve every previous callback/fallback flag
# and logical-source directive; compare every original #line physical position.
cpre=(D/'preimage/kernel/syscall.c').read_text();cpost=(D/'postimage/kernel/syscall.c').read_text();assert cpre.count('\n')==cpost.count('\n')
directives=lambda s:[(i,l)for i,l in enumerate(s.splitlines(True),1)if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(cpre)==directives(cpost)
assert (D/'postimage/kernel/CMakeLists.txt').read_bytes()==(OLD/'postimage/kernel/CMakeLists.txt').read_bytes()
cm=(D/'postimage/kernel/CMakeLists.txt').read_text();lib=(D/'postimage/kernel/rust/lib.rs').read_text()
for r in leaves:
 stem=Path(r['proposed_path']).stem;assert cm.count('rust/'+stem+'.rs')==1
 if stem=='ptrace_clone_noirq':assert lib.count('mod ptrace_clone_noirq;')==1
 else:assert tail.count('mod '+stem+';')==1
assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_exit_group_current_pid.rs"]'in tail
oracle=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389
projected=[]
for r in leaves:
 s=(D/'postimage'/r['proposed_path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',s,re.S):
  body=match.group(1);file=ast.literal_eval(re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');func=ast.literal_eval(re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()'in body;projected.append(dict(file=file,function=func,fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda x:tuple(x[f]for f in fields);moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};assert len(projected)==4;assert Counter(map(key,projected))==Counter(map(key,[r for r in records if r['function']in moved]));assert Counter(map(key,[r for r in records if r['function']not in moved]+projected))==Counter(map(key,records))
checks=['entire original syscall_policy byte-prefix exact; only six original module blocks appended EOF','all53preexisting line! sites exact physical line/column/text, plus every file!/column! site in policy and lib','old7leaf source reproduced uniform+25 at all53sites; correction restores original sites','all7leaves and every nonpolicy postimage byte-identical, C selections/fallback/ABI/dependencies unchanged','C newline count and all original logical #line directive physical positions retained','four moved Rust-owned metadata rows plus all unchanged source identities preserve original389Counter; no oracle edit']
(D/'LOCATION-MACRO-IDENTITIES.json').write_text(json.dumps(dict(status='SOURCE_IDENTITY_ONLY',source_origin='/src/kernel/rust/syscall_policy.rs',macros=macro_map),indent=2)+'\n')
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_LINE_PRESERVING_SOURCE_COMPOSITION_CORRECTION',checks=checks,inherited_line_sites=53,reused_leaves=7,source_paths=11,original389_source_counter_equal=True,actual_linked389=False,compiler_preprocessor_native_calls=0),indent=2)+'\n');print('PASS',len(checks),'focused composition groups;53line sites restored')
