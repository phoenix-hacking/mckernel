"""Functional OS changed-composition checks only; no security testing/runtime."""
from pathlib import Path
import json,re,hashlib,subprocess,os
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';ARCH=A/'M14-ARCH5-CUTOVER-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
m=read(D/'FILEMAP.SOURCE-ONLY.json');rows={r['target']:r for r in m['files']};assert len(rows)==len(m['files'])==37
for n,r in rows.items():
 assert ref(Path(r['source']['path']))==r['source'],n
 if r['frozen119_preimage']:
  p=D/'preimage'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path(r['frozen119_preimage']['path']).read_bytes())
# All old leaf bodies exact, no duplicate port or new ABI replacement.
for r in read(B/'FILEMAP.SOURCE-ONLY.json')['files']:
 if r['reused_leaf']:assert rows[r['target']]['source']==r['source']
policy=Path(rows['kernel/rust/syscall_policy.rs']['source']['path']).read_text();archpolicy=(ARCH/'postimage/kernel/rust/syscall_policy.rs').read_text();assert policy.startswith(archpolicy)
sites=lambda s,n:[(i,x.start(),l)for i,l in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+n+r'!\s*\(',l)]
for macro in ['line','file','column']:assert sites(policy,macro)==sites(archpolicy,macro)
assert len(sites(policy,'line'))==47
for r in read(ARCH/'FILEMAP.json'):
 if r['target']!='kernel/rust/syscall_policy.rs'and r['target']!='kernel/CMakeLists.txt':assert rows[r['target']]['source']['sha256']==r['postimage_sha256']
cm=Path(rows['kernel/CMakeLists.txt']['source']['path']).read_text();c=Path(rows['kernel/syscall.c']['source']['path']).read_text()
for n,r in rows.items():
 if r['reused_leaf']and n.startswith('kernel/rust/'):
  dep='rust/'+Path(n).name;assert cm.count(dep)==1,(n,cm.count(dep))
  stem=Path(n).stem;roots=policy+Path(rows['kernel/rust/lib.rs']['source']['path']).read_text();assert len(re.findall(r'\bmod\s+'+re.escape(stem)+r'\s*;',roots))==1,n
assert policy.count('mod syscall_ptrace_detach_kfree;')==1
assert c.count('extern void ptrace_detach_kfree_bridge(void *ptr);')==1
assert 'f03_ptrace_kfree_profile_119'not in cm and 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119'not in cm
assert cm.count('MCKERNEL_RUST_F03_EXECVEAT_BRIDGE')==1 and cm.count('"--cfg" "f03_execveat_bridge_candidate"')==1
# The bridge C APPEND follows the baseline C source properties, so it is not
# silently overwritten by their later COMPILE_DEFINITIONS assignment.
assert cm.index('MCKERNEL_RUST_F03_EXECVEAT_BRIDGE')>cm.index('MCKERNEL_RUST_SHMID_HELPERS;MCKERNEL_RUST_SHM_PERM_HELPERS;')
for pair in [('f03_signal_forward_defined_candidate','MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL'),('f03_perf_entry_candidate','MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL'),('f03_credential_refresh_candidate','MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL')]:
 assert cm.count('"--cfg" "'+pair[0]+'"')==1 and cm.count(pair[1])==1
# Exact inherited supported Rust cohort remains around all D option blocks;
# no D flag inserted in a B nested option conditional.
lines=cm.splitlines();stack=[];cohorts={}
for l in lines:
 s=l.strip()
 if s.startswith('if (')or s.startswith('if('):stack.append(s)
 if '"--cfg" "f03_'in s and any(x in s for x in ['signal_forward_defined','perf_entry_candidate','credential_refresh']):cohorts[s]=list(stack)
 if s=='endif()':assert stack;stack.pop()
for k,v in cohorts.items():
 assert 'if (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)'in v
 assert not any('DO_SYSCALL_SUPPORTED_EXPERIMENTAL' in t or 'UTIL_THREAD_WHOLE_EXPERIMENTAL'in t for t in v)
assert len(cohorts)==3
# Full actual C tuple transfer and source-origin intent is the unchanged ARCH5
# supplied metadata overlay; generic additions retain exact supplied fallbacks.
assert (A/'M14-REMAINING23-A-1/defined-callers-correction-1/do_execveat.defined-arity.PRIVATE.rs.inc').read_text()in policy
assert 'f03_execveat_whole_candidate'not in cm
argv=['git','apply','--check','--no-index',str(D/'COMBINED.PRIVATE-NOT-APPLIED.patch')];r=subprocess.run(argv,cwd=D/'preimage',env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D)),capture_output=True,text=True);assert r.returncode==0,r.stderr
x=read(D/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');assert len(x['original_link_order'])==11;assert sum(r['candidate_action']=='REUSE_QUALIFIED_EXISTING_OBJECT'for r in x['original_link_order'])==8;assert sum(r['candidate_action']=='REBUILD_AFFECTED_ARCH_C_OBJECT'for r in x['original_link_order'])==1
assert not x['C_test_probe_link_inputs'];abi=read(D/'ACTUAL-ABI-WITNESS-MAP.PROPOSED.json');assert abi['C_probe_objects_in_production_rawlink']==[]
checks=['37unique source targets authenticate; inherited17 leafrefs exact; no duplicate ports','ARCH5 overlay and six-tuple transfer preserved;47 remaining originalmacro sites exact; all source2 prefix corrections reused','all leaf modules/dependencies once; kfree line-neutral wiring/module reused exactly and OFF activation','Abridge paired opt-in C flag appended after baseline property assignment, no overwritten selector','D Root-confirmed unique inherited Rust/C cohort anchors; all3D paired flags once and outside B nested options','exact approved exec-field fragment retained wholeOFF; no invented request/all-caller proof','complete patch applies against frozen119 preimages with isolated Git discovery','11linkinputs: Rust+generic+arch rebuild,8exactreuses; C ABI probe arrays/functions excluded from productionlink']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_CHANGED_COMPOSITION_SOURCE_ONLY',checks=checks,full_patch_check=dict(argv=argv,returncode=r.returncode,stderr=r.stderr),actual_compiler_or_CPP=False,actual_389_registry='PENDING_ACTUAL_CANDIDATE; no rewritten expected tuples',independent_review=None,native=False),indent=2)+'\n');print('PASS',len(checks),'focused changed-composition groups')
