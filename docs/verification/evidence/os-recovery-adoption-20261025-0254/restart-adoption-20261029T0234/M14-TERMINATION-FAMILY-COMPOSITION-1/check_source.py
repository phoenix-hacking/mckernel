from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent;base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel';out=here/'postimage'/'kernel'
reuse=here.parent/'M14-LARGE-TERMINATE-REUSE-1'
host=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-host-whole-entry-source-1')
oldterm=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-whole-orchestration-source-1')
orig=(base/'syscall.c').read_text();new=(out/'syscall.c').read_text()
mc_start=orig.index('void terminate_mcexec(int rc, int sig)\n{');mc_end=orig.index('\n}\n',mc_start)+3
cases=[('terminate_mcexec','MCKERNEL_RUST_F03_TERMINATE_MCEXEC_WHOLE',orig[mc_start:mc_end],5183,5190),('terminate','MCKERNEL_RUST_F03_TERMINATE_WHOLE',(oldterm/'terminate.ACTUAL-ORIGINAL-FULL-C.inc').read_text(),5242,5249),('terminate_host','MCKERNEL_RUST_F03_TERMINATE_HOST_WHOLE',(host/'terminate_host.ORIGINAL-C.inc').read_text(),5620,5627)]
def model(chunk,dispatch,selected,start,selector,origbody):
 symbols={'__x86_64__':True,'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':True,'MCKERNEL_RUST_ATOMIC_HELPERS':True,'MCKERNEL_RUST_F03_TERMINATE_CMPXCHG':True,'MCKERNEL_RUST_F03_TERMINATE_REFCOUNT':True,'MCKERNEL_RUST_F03_TERMINATE_PROFILE_119':True,'MCKERNEL_RUST_SYSCALL_OFFLOAD':dispatch,'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch,selector:selected}
 active=True;stack=[];n=start;events={};body_first=origbody.splitlines()[0]
 for line in chunk.splitlines():
  t=line.strip()
  if t.startswith(('#if ','#ifdef ','#ifndef ')):
   if t.startswith('#ifdef '):cond=bool(symbols.get(t[7:].strip(),False))
   elif t.startswith('#ifndef '):cond=not bool(symbols.get(t[8:].strip(),False))
   else:
    e=re.sub(r'defined\((\w+)\)',lambda m:str(bool(symbols.get(m.group(1),False))),t[4:]);assert re.fullmatch(r'[TrueFals &|!()]+',e),e
    cond=eval(e.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
   stack.append((active,cond));active=active and cond
  elif t.startswith('#else'):parent,cond=stack[-1];active=parent and not cond
  elif t.startswith('#endif'):parent,_=stack.pop();active=parent
  elif active and t.startswith('#error'):raise AssertionError(t)
  elif active and t.startswith('#line '):n=int(t.split()[1]);continue
  elif active and line==body_first:events['fallback_start']=n
  elif active and t.startswith('extern void '):events['selected_decl']=n
  if active and 'dkprintf("%s: PID: %d, TID: %d PS_EXITED already' in line:events['debug0']=n
  if active and 'dkprintf("%s: PID: %d, TID: %d setting PS_EXITED' in line:events['debug1']=n
  if active and 'dkprintf("terminate,pid=%d' in line:events['debug2']=n
  if active and 'ids = kmalloc_tracked(sizeof(int) * n' in line:events['alloc']=n
  if active and 'kfree_tracked(ids, __FILE__, __LINE__)' in line:events['idfree']=n
  if active and 'kfree_tracked(proc->saved_cmdline, __FILE__, __LINE__)' in line:events['savedfree']=n
  n+=1
 assert not stack;events['next_line']=n;return events
restored=new;observed={}
for name,selector,body,on,off in cases:
 assert orig.count(body)==restored.count(body)==1
 bodypos=restored.index(body);start=restored.rfind('#ifdef '+selector+'\n',0,bodypos);assert start>=0
 finish=restored.index('#endif\n',restored.index('#line '+str(off+body.count('\n')-1)+'\n',bodypos))+len('#endif\n')
 chunk=restored[start:finish]
 assert chunk.count(body)==1
 for dispatch in (False,True):
  for selected in (False,True):
   logical=on if dispatch else off;e=model(chunk,dispatch,selected,logical,selector,body)
   assert e['next_line']==logical+body.count('\n'),(name,e)
   if selected:assert 'selected_decl' in e and 'fallback_start' not in e
   else:
    assert e.get('fallback_start')==logical and 'selected_decl' not in e
    if name=='terminate':
     expected=[5271,5292,5511,5346,5363,5403] if dispatch else [5278,5299,5518,5353,5370,5410]
     assert [e[k] for k in ('debug0','debug1','debug2','alloc','idfree','savedfree')]==expected
   observed[f'{name}:dispatch={dispatch}:selected={selected}']=e
 restored=restored[:start]+body+restored[finish:]
assert restored==orig
oldp=(base/'rust/syscall_policy.rs').read_text();p=(out/'rust/syscall_policy.rs').read_text();assert p.startswith(oldp)
cm=(out/'CMakeLists.txt').read_text();leafs=['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs']
for filename in leafs:assert cm.count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+filename+'"')==1 and p[len(oldp):].count('#[path = "'+filename+'"]')==1
for cfg in ['f03_terminate_whole_candidate','f03_terminate_origin_profile_119','f03_terminate_mcexec_whole_candidate','f03_terminate_host_whole_candidate','f03_terminate_origin_dispatch']:
 assert cfg not in cm
for selector in ['MCKERNEL_RUST_F03_TERMINATE_WHOLE','MCKERNEL_RUST_F03_TERMINATE_MCEXEC_WHOLE','MCKERNEL_RUST_F03_TERMINATE_HOST_WHOLE','MCKERNEL_RUST_F03_TERMINATE_PROFILE_119']:
 assert selector not in cm
term=(out/'rust/syscall_terminate_whole.rs').read_text();mcexec=(out/'rust/syscall_terminate_mcexec_whole.rs').read_text();hostfrag=(out/'rust/syscall_terminate_host_whole.rs').read_text()
assert 'const _: unsafe extern "C" fn(CInt, CInt) = f03_terminate_whole_v1;' in term
assert 'const _: unsafe extern "C" fn(CInt, CInt) = f03_terminate_mcexec_v1;' in mcexec
assert 'const _: unsafe extern "C" fn(CInt, *mut Thread) = terminate_host;' in hostfrag
assert 'b"/src/kernel/syscall.c\\0"' in term and term.count('Ddebug { file: SOURCE_FILE.as_ptr().cast()')==3
assert '[5271, 5292, 5511, 5346, 5363, 5403]' in term and '[5278, 5299, 5518, 5353, 5370, 5410]' in term
assert 'f03_terminate_origins_v1' not in term and 'f03_terminate_nowait_v1' not in term
assert '#[cfg(all(f03_terminate_whole_candidate, f03_terminate_origin_profile_119, target_arch = "x86_64"))]' in p
assert 'Some(super::do_syscall)' in mcexec and 'Some(crate::atomic_helpers::atomic_cmpxchg_ulong)' in mcexec
assert 'Some(syscall_do_kill_thread_bridge)' in hostfrag and 'Some(f03_terminate_host_release_thread_v2)' in hostfrag
# The host entry fragment is reused verbatim, with only parent imports/ABI check.
hostsource=(host/'terminate_host.RUST-FRAGMENT.rs.inc').read_text();assert hostfrag=='use super::*;\n\n'+hostsource+'\nconst _: unsafe extern "C" fn(CInt, *mut Thread) = terminate_host;\n'
# Raw parent provider definitions and callbacks retain the existing ABI.
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;' in oldp
assert 'type TerminateMcexecCmpxchgFn = unsafe extern "C" fn(*mut CULong, CULong, CULong) -> CULong;' in oldp
assert 'fn syscall_do_kill_thread_bridge(' in oldp and 'pub unsafe extern "C" fn terminate_host_body_result(' in oldp
assert orig.count('void\ninterrupt_syscall(struct thread *thread, int sig)')==1
assert 'void\ninterrupt_syscall(struct thread *thread, int sig)' in restored
for filename in leafs:assert '#[export_name' in (out/'rust'/filename).read_text() or '#[no_mangle]' in (out/'rust'/filename).read_text()
def info(path):
 data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SOURCE_COMPOSITION_ONLY','checks':['three exact original C bodies restored by reversing selection edits','four modeled C branch/dispatch combinations per body with original next-line origins','six terminate debug/allocation origins in both fallback dispatch modes','three Rust-owned writable debug records and source-profile pair present','existing policy Rust prefix and interrupt source preserved','three default-disabled selectors and C/Rust paired type declarations','exact host fragment reused and current provider source signatures checked','CMake carries only Rust source dependencies'], 'line_model':observed,'files':[info(here/'TERMINATION-FAMILY.PRIVATE-NOT-APPLIED.patch'),info(out/'syscall.c'),info(out/'CMakeLists.txt'),info(out/'rust/syscall_policy.rs')]+[info(out/'rust'/f) for f in leafs], 'limitations':'Source model only; no actual preprocessing, compiler, link, ABI, 389 metadata, native, or ownership/retirement acceptance. Integration requires matching C/Rust flags and source path, all lifecycle/provider holds and independent review.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':result['checks'],'patch':result['files'][0]},indent=2))
