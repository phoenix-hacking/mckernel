#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source composition only; no compiler or native operations.
"""
import ast
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import re

D = Path(__file__).resolve().parent
A = D.parent
N = A / 'M14-PRIVATE-NINE-LEAF-BATCH-1'
M = A / 'M14-UPGRADED-F03-MUNMAP-SET-HOST-1'
ROOT = Path('/home/holden/mckernel')
def ref(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
assert ref(N/'SOURCE-READY.json')['sha256'] == '5f407e2c865295a60e18c7dd9b3f2c30d15269f68cd4f6abf6248558931c0034'
nine = json.loads((N/'FILEMAP.SOURCE-ONLY.json').read_text())
assert ref(N/'NINE-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch')['sha256'] == 'c5e8b6fe8967ebdf07a8481910431203496dd8235f87c8c19fa99c875bd75ec9'
assert ref(M/'MUNMAP-SET-HOST.PRIVATE-NOT-APPLIED.patch')['sha256'] == 'd698d54895f7ec12f6444eb3ad4819df9113fb7f0f4141bcc5e6ec1a384f3ce0'
assert json.loads((N/'SOURCE-CHECKS.json').read_text())['original389_source_counter_equal']
assert json.loads((M/'SOURCE-CHECKS.json').read_text())['status'] == 'PASS_SOURCE_ONLY_ALIAS_AND_PROVENANCE'
alias_pre = (M/'preimage/kernel/syscall.c').read_text()
alias_post = (M/'postimage/kernel/syscall.c').read_text()
start = alias_pre.index('static int\ndo_munmap_set_host_bridge(')
end = alias_pre.index('\n\n#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS)', start)
old = alias_pre[start:end]
newstart = alias_post.index('#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern int mprotect_set_host_vma_bridge')
newend = alias_post.index('\n\n#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS)', newstart)
new = alias_post[newstart:newend]
assert alias_pre.replace(old, new) == alias_post and old.count('\n') == new.count('\n')
rows = []
patch = ''
for row in nine['files']:
    path = row['proposed_path']
    nine_post = N / 'postimage' / path
    assert ref(nine_post) == row['postimage']
    post = nine_post.read_text()
    before = ''
    if row['canonical_preimage'] is not None:
        source = N / 'preimage' / path
        assert source.read_bytes() == Path(row['canonical_preimage']['path']).read_bytes()
        before = source.read_text()
        dest = D / 'preimage' / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(before)
    if path == 'kernel/syscall.c':
        assert before == alias_pre and post.count(old) == 1
        post = post.replace(old, new)
        assert post.replace(new, old) == nine_post.read_text()
        directives = lambda s: [(i, line) for i, line in enumerate(s.splitlines(), 1) if re.match(r'^\s*#\s*(?:line\b|\d)', line)]
        assert directives(before) == directives(post)
        assert len(before.splitlines()) == len(post.splitlines())
        tokens = lambda s: re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]', s)
        assert tokens(old) == tokens(new.split('#else\n', 1)[1].split('\n#endif', 1)[0])
    dest = D / 'postimage' / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(post)
    patch += ''.join(difflib.unified_diff(before.splitlines(True), post.splitlines(True), fromfile='a/'+path if row['canonical_preimage'] else '/dev/null', tofile='b/'+path))
    rows.append({'proposed_path':path, 'nine_postimage':ref(nine_post), 'postimage':ref(dest), 'preimage':ref(D/'preimage'/path) if row['canonical_preimage'] else None, 'reused_leaf_exact':row['reused_leaf_exact']})
assert len(rows) == 13 and sum(row['reused_leaf_exact'] for row in rows) == 9
p = D/'TEN-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch'
p.write_text(patch)
policy_pre=(D/'preimage/kernel/rust/syscall_policy.rs').read_text()
policy_post=(D/'postimage/kernel/rust/syscall_policy.rs').read_text()
sites=lambda s, macro:[(i,x.start()+1,line) for i,line in enumerate(s.splitlines(),1) for x in re.finditer(r'\b'+macro+r'!\s*\(',line)]
for macro in ['line','file','column']:
    assert sites(policy_pre,macro)==sites(policy_post,macro)
assert len(sites(policy_post,'line'))==53
oracle=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json'
assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2'
records=json.loads(oracle.read_text())['records']
assert len(records)==389
projected=[]
for row in rows:
    if not row['reused_leaf_exact']: continue
    text=(D/'postimage'/row['proposed_path']).read_text()
    for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',text,re.S):
        body=match.group(1)
        file=ast.literal_eval(re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0')
        func=ast.literal_eval(re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0')
        line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups())
        assert 'fmt: core::ptr::null()' in body
        projected.append(dict(file=file,function=func,fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding']
key=lambda x:tuple(x[f] for f in fields)
moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'}
assert len(projected)==4 and Counter(map(key,projected))==Counter(map(key,[r for r in records if r['function'] in moved]))
assert Counter(map(key,[r for r in records if r['function'] not in moved]+projected))==Counter(map(key,records))
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status':'PASS_PRIVATE_TEN_LEAF_SOURCE_COMPOSITION_ONLY', 'nine_ready':ref(N/'SOURCE-READY.json'), 'nine_patch':ref(N/'NINE-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch'), 'alias_patch':ref(M/'MUNMAP-SET-HOST.PRIVATE-NOT-APPLIED.patch'), 'alias_checks':ref(M/'SOURCE-CHECKS.json'), 'oracle':ref(oracle), 'patch':ref(p), 'files':rows, 'checks':['nine leaf modules and all non-C postimages byte-identical to nine-leaf batch','only selected munmap alias region changes relative to nine-leaf C','fallback token-identical, line count and all original C #line origins retained','all syscall_policy line!/file!/column! sites retained, 53 line! sites','source projection of all 389 registry identities matches original counter'], 'real_compile_link_native':False,'source_composition_review':None,'runtime_authority':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'])
