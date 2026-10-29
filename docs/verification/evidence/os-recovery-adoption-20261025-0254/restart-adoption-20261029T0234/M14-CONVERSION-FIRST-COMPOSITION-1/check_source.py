"""Functional OS changed-composition contracts only; no security testing/runtime.
No unchanged body-test reruns, source inventory, compiler or native operations.
"""
from pathlib import Path
from collections import Counter
import json,re,hashlib,ast
D=Path(__file__).resolve().parent;A=D.parent;TEN=A/'M14-PRIVATE-TEN-LEAF-BATCH-1';CTX=A/'M14-UPGRADED-F03-CONTEXT-FORWARD-PAIR-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
m=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text());rows={x['target']:x for x in m['files']};assert len(rows)==20;leaves=[x for x in m['files']if x['reused_leaf']];assert len(leaves)==16 and not (D/'postimage/kernel/rust/syscall_ptrace_detach_kfree.rs').exists()
for r in m['files']:assert ref(Path(r['source']['path']))==r['source']
for r in json.loads((TEN/'SOURCE-CHECKS.json').read_text())['files']:
 if r['reused_leaf_exact']:assert rows[r['proposed_path']]['source']['sha256']==r['postimage']['sha256']
# Common source changes only; all sixteen leaf bodies are immutable external refs.
pre=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();policy=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();assert policy.startswith((CTX/'postimage/kernel/rust/syscall_policy.rs').read_text())and policy.startswith(pre)
prelib=(D/'preimage/kernel/rust/lib.rs').read_text();lib=(D/'postimage/kernel/rust/lib.rs').read_text();assert lib.startswith((TEN/'postimage/kernel/rust/lib.rs').read_text())
sites=lambda s,name:[(i,x.start()+1,line)for i,line in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+name+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(pre,macro)==sites(policy,macro)and sites(prelib,macro)==sites(lib,macro)
assert len(sites(policy,'line'))==53
c=(D/'postimage/kernel/syscall.c').read_text();cp=(D/'preimage/kernel/syscall.c').read_text();assert c.count('\n')==cp.count('\n')
directives=lambda s:[(i,line)for i,line in enumerate(s.splitlines(True),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert directives(c)==directives(cp)
# Every C builtin origin/diagnostic producer stays on its prior physical line.
# Kfree's compact fallback keeps __LINE__ on originaloffset3; columns are not
# part of C __LINE__/__FILE__/__func__/__FUNCTION__ semantics.
for macro in ['__LINE__','__FILE__','__func__','__FUNCTION__']:
 occurrences=lambda s:[(i,macro)for i,line in enumerate(s.splitlines(),1)for _ in re.finditer(r'\b'+macro+r'\b',line)]
 assert occurrences(c)==occurrences(cp),macro
wiring=json.loads((D/'C-WIRING-DELTAS.json').read_text());tokens=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',s)
for r in wiring:
 assert r['old'].count('\n')==r['new'].count('\n');fallback=r['new'].split('#else\n',1)[1].rsplit('#endif',1)[0];assert tokens(fallback)==tokens(r['old']);assert c.count(r['new'])==1
assert len(wiring)==7
cm=(D/'postimage/kernel/CMakeLists.txt').read_text()
for r in leaves:
 f=r['target'];stem=Path(f).stem;assert cm.count('rust/'+stem+'.rs')==1
 root=lib if stem in ['ptrace_clone_noirq','f03_wakeup_writer_pair']else policy;assert root.count('mod '+stem+';')==1
assert 'f03_ptrace_kfree_profile_119' in policy and 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119'in c
assert not re.search(r'list\(APPEND RUST_KERNEL_CFG[^\n]*f03_ptrace_kfree_(?:profile_119|dispatch_origin)',cm)
assert 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119'not in cm
for rustflag,cflag in [('f03_ptrace_clone_noirq_candidate','MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ'),('f03_context_forward_pair_candidate','MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR'),('f03_wakeup_writer_pair_candidate','MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR')]:
 assert cm.count('"--cfg" "'+rustflag+'"')==1 and cm.count(cflag)==1
assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64", enable_perf))]'in policy
# Perf bridge remains under original enclosing ENABLE_PERF; no profile widening.
perf=c.index('extern long perf_event_open_do_syscall_bridge');assert c.rfind('#ifdef ENABLE_PERF',0,perf)>0
kf=next(r for r in wiring if r['symbol']=='ptrace_detach_kfree_bridge');original_start=cp.index(kf['old']);new_start=c.index(kf['new']);assert cp.count('\n',0,original_start)==c.count('\n',0,new_start);assert kf['new'].splitlines()[3].count('__LINE__')==1
# Existing original389 source identity projection: unchanged full parent prefix,
# same C origins, exact four Rust-owned moved records; other new leaves no verbose.
oracle=A.parent/'F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';assert ref(oracle)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2';records=json.loads(oracle.read_text())['records'];assert len(records)==389;projected=[]
for r in leaves:
 s=Path(r['source']['path']).read_text()
 for match in re.finditer(r'static mut [A-Z_]+: Ddebug = Ddebug \{(.*?)\n\};',s,re.S):
  body=match.group(1);file=ast.literal_eval(re.search(r'file: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');func=ast.literal_eval(re.search(r'func: b("(?:[^"\\]|\\.)*")',body).group(1)).rstrip('\0');line,flags=map(int,re.search(r'line_flags: ([0-9]+) \| \(([0-9]+) << 24\)',body).groups());assert 'fmt: core::ptr::null()'in body;projected.append(dict(file=file,function=func,fmt=None,line=line,flags=flags,padding=0))
fields=['file','function','fmt','line','flags','padding'];key=lambda x:tuple(x[f]for f in fields);moved={'exit_group_log_bridge','ptrace_report_clone_log_bridge'};assert len(projected)==4 and Counter(map(key,projected))==Counter(map(key,[x for x in records if x['function']in moved]));assert Counter(map(key,[x for x in records if x['function']not in moved]+projected))==Counter(map(key,records))
queue=json.loads((D/'47-SYMBOL-QUEUE.json').read_text());assert len(queue['rows'])==47 and len({r['symbol']for r in queue['rows']})==47
exports=[]
for leaf in leaves:
 text=Path(leaf['source']['path']).read_text();exports+=re.findall(r'#[\[]no_mangle\]\s*pub(?:\([^)]*\))?\s+(?:unsafe\s+)?extern "C" fn (\w+)',text)
assert len(exports)==len(set(exports))==19
assert 'ptrace_detach_kfree_bridge'in exports
assert sum(r['candidate_default_selection_intent']is True for r in queue['rows'])==19
candidate_inputs=json.loads((D/'AFFECTED-UNIT-CANDIDATE-INPUTS.json').read_text());assert candidate_inputs['native119_gate_for_next_affected_build']is False
assert len(candidate_inputs['original_link_order'])==11 and sum(r['candidate_action']=='REUSE_QUALIFIED_EXISTING_OBJECT'for r in candidate_inputs['original_link_order'])==8
checks=['47queue exact,19unique Rustexports includingkfreeOFF, oneadditionalCnamealias explicitly separate','all16leaf BYTErefs authenticate; no leaf source copies or duplicate ports','entire frozen119 parentprefix/all53location macros and libmacro positions retained','allC newline/#line and builtin origin producer lines retained, seven simple wiring OFFtokens exact','every module/dependency once; three new paired selectors and existingperf pair preserved','Rustownedkfree metadata reused, actual activation/origin cfgs absent fromCMake OFF, fallbackline preserved','original389sourceCounter projection retained, no oracle/constants/ELF rewrite']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_CONVERSION_FIRST_COMPOSITION_ONLY',checks=checks,source_targets=20,reused_external_leaf_refs=16,source_candidate_Rust_exports=19,default_candidate_Rust_exports=18,C_symbol_queue_coverage=20,kfree_candidate_cfg='OFF',original389_source_counter_equal=True,actual_compile_link_native=False),indent=2)+'\n');print('PASS',len(checks),'changed-composition groups')
