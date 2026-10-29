"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact source-composition checks, not compiled behavior/linked acceptance.
"""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-PRIVATE-SIX-LEAF-BATCH-1';U=A/'M14-PRIVATE-EXIT-GROUP-CURRENT-PID-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
m=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());bm=json.loads((B/'FILEMAP.SOURCE-ONLY.json').read_text());rows={r['proposed_path']:r for r in m['files']};assert len(rows)==11
for r in m['files']:
 assert ref(D/'postimage'/r['proposed_path'])==r['postimage']
 if r['canonical_preimage']is not None:assert ref(ROOT/r['proposed_path'])==r['canonical_preimage']
leaves=[r for r in m['files']if r['reused_leaf_exact']];assert len(leaves)==7
for r in leaves:
 source=U if r['proposed_path'].endswith('syscall_exit_group_current_pid.rs')else B
 assert (D/'postimage'/r['proposed_path']).read_bytes()==(source/'postimage'/r['proposed_path']).read_bytes()
old=(B/'postimage/kernel/syscall.c').read_text();new=(D/'postimage/kernel/syscall.c').read_text();original=(D/'preimage/kernel/syscall.c').read_text()
start=old.index('int\nexit_group_current_pid_bridge(void)\n');end=old.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start);line=old.count('\n',0,start);stop=old.count('\n',0,end);a=old.splitlines(True);b=new.splitlines(True);assert len(a)==len(b)==len(original.splitlines(True));assert a[:line]==b[:line]and a[stop:]==b[stop:]
replacement=b[line:stop]
assert replacement[0].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)'
assert replacement[1].strip()=='extern int exit_group_current_pid_bridge(void);'
assert replacement[2].strip()=='#else' and replacement[6].strip()=='#endif'
token=lambda x:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',x)
assert token(''.join(a[line:stop]))==token(replacement[3])
for enabled in (False,True):
 for x86 in (False,True):assert (enabled and x86)==(enabled and x86)
directives=lambda s:[(i,l)for i,l in enumerate(s.splitlines(True))if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(original)==directives(old)==directives(new)
assert (D/'postimage/kernel/rust/lib.rs').read_bytes()==(B/'postimage/kernel/rust/lib.rs').read_bytes()
parent=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();bp=(B/'postimage/kernel/rust/syscall_policy.rs').read_text();extra='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_exit_group_current_pid.rs"]\nmod syscall_exit_group_current_pid;\n';assert parent.count(extra)==1 and parent.replace(extra,'',1)==bp
cm=(D/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_current_pid.rs"\n';assert cm.count(dep)==1 and cm.replace(dep,'',1)==(B/'postimage/kernel/CMakeLists.txt').read_text()
for r in leaves:
 name=Path(r['proposed_path']).stem
 assert cm.count('rust/'+name+'.rs')==1
 if name!='ptrace_clone_noirq':assert parent.count('mod '+name+';')==1
assert parent.count('#[cfg(all(f03_leaf_callbacks_candidate, target_arch = \"x86_64\"))]\n#[path = \"syscall_exit_group_current_pid.rs\"]')==1
assert 'list(APPEND RUST_KERNEL_CFG \"--cfg\" \"f03_leaf_callbacks_candidate\")'in cm
assert 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
oracle=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389
projected=[]
for r in leaves:
 s=(D/'postimage'/r['proposed_path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',s,re.S):
  body=match.group(1);file=ast.literal_eval(re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');func=ast.literal_eval(re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()'in body;projected.append(dict(file=file,function=func,fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda x:tuple(x[f]for f in fields);moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};assert len(projected)==4;assert Counter(map(key,projected))==Counter(map(key,[r for r in records if r['function']in moved]));assert Counter(map(key,[r for r in records if r['function']not in moved]+projected))==Counter(map(key,records))
checks=['all seven leaves byte-identical to authenticated source packets','C delta only PID getter selector/fallback, original newline/directive positions unchanged','prior lock fallback and other C bodies unchanged from reviewed batch','syscall parent delta only one additive selector-gated getter module; crate lib exact reviewed lock selection','CMake delta only getter leaf dependency, every leaf selected/dependent once','exact four Rust-owned metadata rows retain full original389Counter; getter owns no descriptor']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_SEVEN_LEAF_SOURCE_COMPOSITION',checks=checks,source_paths=len(rows),reused_leaf_count=7,original389_source_projection_equal=True,oracle=ref(oracle),compiler_preprocessor_HOST_native_calls=0),indent=2)+'\n');print('PASS',len(checks),'composition groups')
