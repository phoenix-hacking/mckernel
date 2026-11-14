"""Functional OS composition-only checks; no security testing/compiler/runtime.
Unchanged seven-body and forwarding fixture findings are reused, not rerun.
"""
from pathlib import Path
from collections import Counter
import re,json,hashlib,ast
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-PRIVATE-SEVEN-LEAF-BATCH-1/line-preserving-composition-correction-1';N=A/'M14-PRIVATE-NEXT-GENERIC-BODY-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
m=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());rows={r['proposed_path']:r for r in m['files']};assert len(rows)==12
for f,r in rows.items():
 assert ref(D/'postimage'/f)==r['postimage']
 if r['canonical_preimage']is not None:assert ref(ROOT/f)==r['canonical_preimage']and (D/'preimage'/f).read_bytes()==(ROOT/f).read_bytes()
leaves=[r for r in m['files']if r['reused_leaf_exact']];assert len(leaves)==8
for r in leaves:
 source=N if r['proposed_path'].endswith('syscall_munmap_clear_host_forward.rs')else B
 assert (D/'postimage'/r['proposed_path']).read_bytes()==(source/'postimage'/r['proposed_path']).read_bytes()
assert (D/'postimage/kernel/rust/lib.rs').read_bytes()==(B/'postimage/kernel/rust/lib.rs').read_bytes()
pre=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();old=(B/'postimage/kernel/rust/syscall_policy.rs').read_text();new=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();assert new.startswith(old)and old.startswith(pre);added=new[len(old):];assert added.count('mod syscall_munmap_clear_host_forward;')==1 and '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]'in added
sites=lambda s,macro:[(i,x.start()+1,line)for i,line in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+macro+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(pre,macro)==sites(old,macro)==sites(new,macro)
assert len(sites(new,'line'))==53
cm=(D/'postimage/kernel/CMakeLists.txt').read_text();oldcm=(B/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"\n';assert cm.count(dep)==1 and cm.replace(dep,'',1)==oldcm
for r in leaves:
 name=Path(r['proposed_path']).stem;assert cm.count('rust/'+name+'.rs')==1
 if name!='ptrace_clone_noirq':assert new[len(pre):].count('mod '+name+';')==1
assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")'in cm and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
oc=(B/'postimage/kernel/syscall.c').read_text();nc=(D/'postimage/kernel/syscall.c').read_text();cc=(D/'preimage/kernel/syscall.c').read_text();start=oc.index('static long\ndo_munmap_clear_host_bridge(');end=oc.index('\nstatic int\ndo_munmap_set_host_bridge',start);first=oc.count('\n',0,start);stop=oc.count('\n',0,end);a=oc.splitlines(True);b=nc.splitlines(True);assert len(a)==len(b)==len(cc.splitlines(True))and a[:first]==b[:first]and a[stop:]==b[stop:]
tokens=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',s);assert tokens(''.join(a[first:stop]))==tokens(b[first+3]);assert b[first].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)'and b[first+1].strip().startswith('extern long do_munmap_clear_host_bridge(')
directives=lambda s:[(i,line)for i,line in enumerate(s.splitlines(True),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert directives(cc)==directives(oc)==directives(nc)
# No unchanged leaf behavior re-test: exact bytes inherit reviewed7leaf and
# newbody42stub findings. Preserve originalCounter identities structurally too.
oracle=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389;projected=[]
for r in leaves:
 s=(D/'postimage'/r['proposed_path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',s,re.S):
  body=match.group(1);file=ast.literal_eval(re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');func=ast.literal_eval(re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()'in body;projected.append(dict(file=file,function=func,fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda x:tuple(x[f]for f in fields);moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};assert len(projected)==4 and Counter(map(key,projected))==Counter(map(key,[r for r in records if r['function']in moved]));assert Counter(map(key,[r for r in records if r['function']not in moved]+projected))==Counter(map(key,records))
checks=['eight Rust leaves exact reuse; prior lib.rs unchanged','only new syscallpolicy EOFmodule appended, fullfrozen119prefix and all53line!/file!/column! coordinates exact','C delta against reviewed7 only new forwardingcallback; OFF C tokens and original #line/physical origins unchanged','one added CMake dependency, module/dependency each once, existing paired selector+x86 preserved','original389sourceCounter retained including fourmoved rows and all inherited location macro identities','no unchanged body fixture reruns; reuse prior7source acceptance and new42case sourceforwarding proof']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_EIGHT_LEAF_COMPOSITION_SOURCE_ONLY',checks=checks,reused_leaves=8,source_paths=12,original389_source_counter_equal=True,actual_compile_link_native=False),indent=2)+'\n');print('PASS',len(checks),'composition groups')
