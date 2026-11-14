"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Three exact live C callbacks select existing Rust providers; private source only.
"""
from pathlib import Path
import ast,difflib,hashlib,json,re
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel')
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def function(text,name):
 m=re.search(r'(?m)^(?:static )?(?:pub )?(?:unsafe )?(?:extern "C" )?fn '+re.escape(name)+r'\(',text)
 if m:
  start=m.start();brace=text.index('{',m.end())
 else:
  m=re.search(r'(?m)^'+re.escape(name)+r'\(',text);assert m,name;start=text.rfind('\n',0,m.start()-1)+1;brace=text.index('{',m.end())
 depth=1;end=brace+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]+'\n'
def logical_following(text,end):
 line=1
 for s in text[:end].splitlines():
  m=re.match(r'^\s*#line\s+(\d+)(?:\s+"[^"]*")?\s*$',s)
  line=int(m.group(1)) if m else line+1
 return line
cursor=E/'CURRENT26EB-SELECTED-F03-F06-REMAINING-SOURCE-CURSOR.json';cur=json.loads(cursor.read_text());assert cur['rows']['F03']['count']==75
C=(R/'kernel/syscall.c').read_text();policy=(R/'kernel/rust/syscall_policy.rs').read_text();assert ref(R/'kernel/syscall.c')['sha256']=='aeeb1d71cfd5b8d97935981aa3fc29674586289748e7e61514d247a43b473984';assert ref(R/'kernel/rust/syscall_policy.rs')['sha256']=='02ddaecff895693d389b0a6710c0ff4579c91caf2b53ea5f62746f4b8125d812'
specs=[dict(C='ptrace_wakeup_find_thread_bridge',Rust='f03_ptrace_io_find',define='MCKERNEL_RUST_F03_WAKEUP_FIND',declaration='extern unsigned long f03_ptrace_io_find(int, int);',existing_export_cfg='f03_ptrace_io_find_selected_candidate'),dict(C='ptrace_wakeup_thread_unlock_bridge',Rust='f03_ptrace_io_unlock',define='MCKERNEL_RUST_F03_WAKEUP_UNLOCK',declaration='extern void f03_ptrace_io_unlock(unsigned long);',existing_export_cfg='f03_ptrace_io_unlock_selected_candidate'),dict(C='thread_exit_waitq_wake_bridge',Rust='f03_exit_notify_wake',define='MCKERNEL_RUST_F03_EXIT_WAITQ_WAKE',declaration='extern void f03_exit_notify_wake(void *);',new_export_cfg='f03_exit_waitq_wake_selected_candidate')]
changed=C
for i,spec in enumerate(specs):
 assert spec['C'] in cur['rows']['F03']['defined_FUNC_names'];old=function(C,spec['C']);assert C.count(old)==1
 start=C.index(old);following=logical_following(C,start+len(old));tail='#line '+str(following)+'\n'
 if spec['C']=='thread_exit_waitq_wake_bridge':
  endline=len(C[:start+len(old)].splitlines());resetline=C[:C.index('#line 119\n')].count('\n')+1;fallback=119+endline-resetline
  tail='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line '+str(following-3)+'\n#else\n#line '+str(fallback-1)+'\n#endif\n';spec['old_logical_following_line_without_dispatch_context']=fallback
 replacement='#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined('+spec['define']+')\n'+spec['declaration']+'\n#define '+spec['C']+' '+spec['Rust']+'\n#else\n'+old+'#endif\n'+tail
 changed=changed.replace(old,replacement,1)
 leaf=D/('%02d-'%(i+1)+spec['C']);leaf.mkdir(mode=0o700);(leaf/'original.C.inc').write_text(old);(leaf/'paired-selector.C.inc').write_text(replacement);(leaf/'reused.Rust.inc').write_text(function(policy,spec['Rust']))
 cfg=spec.get('existing_export_cfg') or spec['new_export_cfg'];(leaf/'selected.Rust.inc').write_text('#[cfg_attr('+cfg+',no_mangle)]\n'+function(policy,spec['Rust']))
 spec.update(original_C=ref(leaf/'original.C.inc'),selected_C=ref(leaf/'paired-selector.C.inc'),unchanged_Rust_body=ref(leaf/'reused.Rust.inc'),old_logical_following_line=following)
before='unsafe extern "C" fn f03_exit_notify_wake(waitq: *mut c_void) {';assert policy.count(before)==1;selected=policy.replace(before,'#[cfg_attr(f03_exit_waitq_wake_selected_candidate,no_mangle)]\n'+before,1)
for rel,old,new in [('kernel/syscall.c',C,changed),('kernel/rust/syscall_policy.rs',policy,selected)]:
 p=D/'candidate'/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text(new);p.chmod(0o400);p=D/(Path(rel).name+'.patch');p.write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=rel,tofile=rel)))
for src,name in [(R/'kernel/rust/abi.rs','retained-abi.rs')]: (D/name).write_bytes(src.read_bytes())
waitq=(R/'kernel/rust/waitq.rs').read_text();layout='\n\n'.join(waitq[waitq.rfind('#[repr(C)]',0,waitq.index('pub(crate) struct '+name)):waitq.index('\n}',waitq.index('pub(crate) struct '+name))+2] for name in ['IhkSpinlock','ListHead','Waitq'])+'\n';(D/'retained-waitq-layout.Rust.inc').write_text(layout)
save('THREE-SOURCE-SLICES.json',dict(scope=__doc__.splitlines()[0],status='PRIVATE_REUSED_THREE_CALLBACK_SELECTOR_SOURCE_NOT_COMPILED',cursor=ref(cursor),actual_selected_object=cur['rows']['F03']['object'],slices=specs,source_preimages={rel:ref(R/rel) for rel in ['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']},source_postimages={rel:ref(D/'candidate'/rel) for rel in ['kernel/syscall.c','kernel/rust/syscall_policy.rs']},new_Rust_algorithm_bodies=0,existing_Rust_exports_reused=2,newly_exported_existing_Rust_provider=1,new_C_function_bodies=0,logical_line_file_semantics='Each guard restores the exact preexisting logical following line; original fallback bodies unchanged; no __FILE__ override',CMake_Root_plan=dict(preimage=ref(R/'kernel/CMakeLists.txt'),kernel_C_defines=[s['define'] for s in specs],new_Rust_cfgs=['f03_exit_waitq_wake_selected_candidate'],required_existing_Rust_cfgs=['f03_ptrace_io_find_selected_candidate','f03_ptrace_io_unlock_selected_candidate'],new_source_files=[],placement='Append centrally inside existing supported Linux6.12/x86_64 non-UBSAN branch; preserve enable_perf and current non-DCFA lock ABI; no NOCACHE expansion'),current_count=75,expected_selected_count=72,expected_removed_C_names=[s['C'] for s in specs],canonical_Git_compiler_Docker_native_actions=0,default_acceptance=False,native_acceptance=False,whole_file_retired=False))
print(json.dumps(dict(status='PRIVATE_THREE_REAL_SOURCE_SLICES_READY',C_callbacks=[s['C'] for s in specs],new_bodies=0,logical_line_restoration=True)))
if __name__!='__main__':raise RuntimeError('One private preparation command only')
