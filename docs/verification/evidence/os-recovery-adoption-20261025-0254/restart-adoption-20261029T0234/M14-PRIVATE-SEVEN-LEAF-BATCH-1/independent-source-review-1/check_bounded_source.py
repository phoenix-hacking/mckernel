"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only two new leaves and composition/sourceidentity; no unchanged-body re-audit.
"""
from pathlib import Path
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent

def read(p):return json.loads(p.read_bytes())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(Path(r['path']))==r;return Path(r['path'])
ready=read(P/'SOURCE-READY.json');assert ref(P/'SOURCE-READY.json')['sha256'].startswith('d323a920');auth(ready['patch']);assert ready['patch']['sha256']=='9e51595ab639964eefaab827ce6267b16a49f44dcfbafcc30beeb49c85b2af05'
five=A/'M14-PRIVATE-LOGGER-LOCK-BATCH-1';review=read(five/'independent-source-review-1/REVIEW.ACTUAL.json');assert review['decision']=='PASS_SOURCE'and review['independent']and not review['implementation_ownership']
fm=read(auth(ready['filemap']));rows={r['proposed_path']:r for r in fm['files']};assert len(rows)==11
for row in rows.values():auth(row['postimage'])
priorleaves={k:v for k,v in review['changed_postimages'].items()if k.endswith('.rs')and not k.endswith(('syscall_policy.rs','lib.rs'))};assert len(priorleaves)==5
for name,row in priorleaves.items():assert Path(auth(row)).read_bytes()==Path(auth(rows[name]['postimage'])).read_bytes()
assert(P/'postimage/kernel/rust/lib.rs').read_bytes()==(five/'postimage/kernel/rust/lib.rs').read_bytes()
leaf_pid=(P/'postimage/kernel/rust/syscall_exit_group_current_pid.rs').read_text();leaf_util=(P/'postimage/kernel/rust/syscall_util_clone_disabled_logger.rs').read_text();cpre=(P/'preimage/kernel/syscall.c').read_text();cpost=(P/'postimage/kernel/syscall.c').read_text()
assert 'pub(super) unsafe extern "C" fn exit_group_current_pid_bridge() -> CInt'in leaf_pid and 'unsafe { (*(*current_thread_ptr()).proc).pid }'in leaf_pid
for text in ['size_of::<CInt>() == 4','offset_of!(Thread, proc) == 4304','offset_of!(Process, pid) == 456']:assert text in leaf_pid
assert 'read_volatile'not in leaf_pid and 'kprintf'not in leaf_pid and 'Ddebug'not in leaf_pid
parent=(P/'postimage/kernel/rust/syscall_policy.rs').read_text();assert 'unsafe fn current_thread_ptr() -> *mut Thread'in parent
selector='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)';assert selector in cpost;assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]'in parent
start=cpre.index('void\nsyscall_util_indicate_clone_disabled_bridge(void)\n');end=cpre.index('\nlong sys_util_indicate_clone',start);original_util=cpre[start:end]
old_literals=[ast.literal_eval(s).encode()for s in re.findall(r'"(?:[^"\\]|\\.)*"',original_util)];new_literals=[ast.literal_eval(s[1:]).encode()for s in re.findall(r'c"(?:[^"\\]|\\.)*"',leaf_util)]
assert old_literals==new_literals==[b'%s: error: --enable-uti mcexec option not specified\n',b'sys_util_indicate_clone'];assert leaf_util.count('kprintf(')==original_util.count('kprintf(')==1
assert 'extern "C" fn syscall_util_indicate_clone_disabled_bridge()'in leaf_util and 'cast::<i8>()'in leaf_util and 'Ddebug'not in leaf_util
assert cpre.count('\n')==cpost.count('\n')
directives=lambda text:[(i,l)for i,l in enumerate(text.splitlines(),1)if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(cpre)==directives(cpost)
# Independent negative applicability check, absent from the owner descriptor-only test.
sites=lambda text:[dict(line=i,text=l.strip())for i,l in enumerate(text.splitlines(),1)if re.search(r'\bline!\s*\(',l)]
pre=sites((P/'preimage/kernel/rust/syscall_policy.rs').read_text());post=sites(parent);reviewed5=sites((five/'postimage/kernel/rust/syscall_policy.rs').read_text());six=sites((A/'M14-PRIVATE-SIX-LEAF-BATCH-1/postimage/kernel/rust/syscall_policy.rs').read_text())
assert len(pre)==len(post)==len(reviewed5)==len(six)==53
assert [r['text']for r in pre]==[r['text']for r in post]==[r['text']for r in reviewed5]
delta=lambda a,b:sorted(set(y['line']-x['line']for x,y in zip(a,b)))
assert delta(reviewed5,six)==[4]and delta(six,post)==[5]and delta(reviewed5,post)==[9]and delta(pre,post)==[25]
assert pre!=post
result=dict(scope=__doc__.splitlines()[0],status='NEW_TWO_LEAF_SOURCE_FACTS_PASS_COMPOSITION_METADATA_APPLICABILITY_FAIL',source_ready=ref(P/'SOURCE-READY.json'),patch=ready['patch'],reused_five_review=ref(five/'independent-source-review-1/REVIEW.ACTUAL.json'),reused_lock_review=review.get('reused_lock_review'),new_leaf_source_checks=dict(pid_getter='PASS raw current→proc→pid/noargsCInt; same nonnull live context, no added ownership/nullpolicy',util_logger='PASS exactstaticformat/one%s/matchingi8ptr/onecall/no descriptor'),reused_five_leaves_exact=True,crate_lib_exact_reviewed=True,Cnewline_and_directive_positions_unchanged=True,genuine_Rust_line_macro_sites=dict(count=53,seven_vs_reviewed5_shift=9,util_increment=4,getter_increment=5,seven_vs_frozen119_shift=25,preimage=pre,reviewed5=reviewed5,sixleaf=six,sevenleaf=post),blocking_defect='Added child-module declarations precede53genuineRustline!() descriptor sites. Newutil/getter additions shift all53by+9 relative reviewedfive; entireseven shifts+25relativefrozen119. Four movedCdescriptor projection test omits inheritedRustline identities; sourceprojection cannot satisfy untouched389oracle.',smallest_source_correction='Reuse accepted119pattern: move all six introduced syscall_policy child-module declaration blocks to EOF, preserving sameparent lexicalscope/cfg/path and all7leafbytes; recover exactfrozen119prefix/macropositions. Never alteroriginal389oracle/lineconstants/ELF.',undefined_variadic_hold_preserved='ptrace_wakeup undefinedlong/format-domain remains excluded; no cast or domainwidening is approved.',compiler_preprocessor_HOST_ELF_native_guard_cleanup_calls=0,canonical_writes=0,runtime_authority=None)
(D/'CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],macro_sites=53,new_shift=9,total_shift=25,report=ref(D/'CHECKS.json'))))
