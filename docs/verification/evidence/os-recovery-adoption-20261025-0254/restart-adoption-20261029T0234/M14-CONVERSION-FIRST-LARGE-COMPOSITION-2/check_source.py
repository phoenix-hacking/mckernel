"""Functional OS source composition checks only; no security testing/runtime/compiler."""
from pathlib import Path
import json,re,hashlib,subprocess,os
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';S=A/'M14-LARGE-DO-SYSCALL-REUSE-1';U=A/'M14-LARGE-UTIL-THREAD-REUSE-1';R=A/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
m=read(D/'FILEMAP.SOURCE-ONLY.json');rows={r['target']:r for r in m['files']};old=read(B/'FILEMAP.SOURCE-ONLY.json')['files'];assert len(rows)==21
for r in rows.values():assert ref(Path(r['source']['path']))==r['source']
for r in old:
 if r['reused_leaf']:assert rows[r['target']]==r
assert rows['kernel/rust/lib.rs']['source']['sha256']==next(x for x in old if x['target']=='kernel/rust/lib.rs')['source']['sha256']
policy=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();base=(B/'postimage/kernel/rust/syscall_policy.rs').read_text();assert policy.startswith(base)
pre=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();suffix=''
for p in [S,U]:
 t=(p/'syscall_policy.PRIVATE.rs').read_text();assert t.startswith(pre);fragment=(p/'RUST-BODY.REUSED.rs.inc').read_text();assert t==pre+'\n'+fragment;suffix+='\n'+fragment
rp=(R/'preimage/kernel/rust/syscall_policy.rs').read_text();rt=(R/'postimage/kernel/rust/syscall_policy.rs').read_text();assert rt.startswith(rp);suffix+=rt[len(rp):];assert policy==base+suffix
sites=lambda s,n:[(i,x.start(),line)for i,line in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+n+r'!\s*\(',line)]
for n in ['line','file','column']:assert sites(pre,n)==sites(policy,n)
assert len(sites(policy,'line'))==53
# Exact inverse of the three contributed C hunks restores the accepted first20
# C postimage, including every inherited fallback token, directive and origin.
p=D/'projection-check/kernel/syscall.c';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((D/'postimage/kernel/syscall.c').read_bytes());results=[]
for patch in [R/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch',U/'CURRENT119-PRIVATE-REBASE.patch',S/'CURRENT119-PRIVATE-REBASE.patch']:
 argv=['git','apply','--reverse','--no-index','--include=kernel/syscall.c',str(patch)];r=subprocess.run(argv,cwd=D/'projection-check',capture_output=True,text=True,env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D)));results.append(dict(argv=argv,returncode=r.returncode,stderr=r.stderr));assert r.returncode==0,results[-1]
assert p.read_bytes()==(B/'postimage/kernel/syscall.c').read_bytes()
c=(D/'postimage/kernel/syscall.c').read_text();cm=(D/'postimage/kernel/CMakeLists.txt').read_text()
for f in ['MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED','MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE','MCKERNEL_RUST_F03_UTIL_REQUEST_ARG5_ZERO']:
 assert f in c and f not in cm
for cfg in ['f03_do_syscall_supported_candidate','f03_util_thread_whole_candidate','f03_util_thread_arg5_zero_candidate']:
 assert cfg in policy and cfg not in cm
assert 'option(MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL'not in cm and 'set(MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL'not in cm
assert cm.count('if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)')==2
assert cm.count('rust/f03_request_constructors.rs')==1 and policy.count('mod f03_request_constructors;')==1
# No new lookup/type/API introduced by composition; exact incoming ABI leaves.
leaf=Path(rows['kernel/rust/f03_request_constructors.rs']['source']['path']).read_text();assert 'align(64)'not in leaf and 'let mut storage = MaybeUninit::<SyscallRequest>::uninit();'in leaf
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;'in policy
for p in [S,U]:assert (p/'RUST-BODY.REUSED.rs.inc').read_text() in policy
# Full complete patch applies to the frozen119 four-file preimage. No compiler.
argv=['git','apply','--check','--no-index',str(D/'LARGE-COMPOSITION.PRIVATE-NOT-APPLIED.patch')];r=subprocess.run(argv,cwd=D/'preimage',capture_output=True,text=True,env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D)));assert r.returncode==0,r.stderr
checks=['all16 inherited external leafrefs and lib byteexact; new natural-alignment constructor leaf byteexact','entire first20 Rust prefix unchanged plus exact two incoming modules and one EOF module','all53 inherited line!/file! coordinates/text unchanged, no macro-site movement','three exact original C patch hunks apply and reverse to entire first20 C bytes, all inherited origin/fallback directives preserved','do_syscall/util whole selectors absent from CMake; constructors explicit opt-in absent default; all inherited flags unchanged','existing request ABI declaration reused, natural storage correction exact; no invented API or duplicated body','complete21-target patch applies to frozen119 preimages']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_COMPOSITION_SOURCE_CHECKS_ONLY',checks=checks,reverse_projection=results,full_patch_check=dict(argv=argv,returncode=r.returncode,stderr=r.stderr),original389_counter='INHERITED_FIRST20_SOURCE_PROJECTION_UNCHANGED; selected large metadata/ABI acceptance remains OPEN',actual_compile_link_native=False),indent=2)+'\n');print('PASS',len(checks),'focused composition groups')
