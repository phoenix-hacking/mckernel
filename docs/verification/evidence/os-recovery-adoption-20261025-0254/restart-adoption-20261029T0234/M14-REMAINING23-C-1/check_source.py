from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent
family=here.parent/'M14-TERMINATION-FAMILY-COMPOSITION-1'/'postimage'/'kernel'
nine=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
kfree=here.parent/'M14-UPGRADED-F03-PTRACE-KFREE-1'/'Rust-owned-metadata-correction-1'/'postimage'/'kernel';out=here/'postimage'/'kernel'
a=(family/'syscall.c').read_text();s=(out/'syscall.c').read_text();oldnine=(nine/'syscall.c').read_text();kc=(kfree/'syscall.c').read_text()
oldfree='static void\nptrace_detach_kfree_bridge(void *ptr)\n{\n\tkfree_tracked(ptr, __FILE__, __LINE__);\n}\n'
anchor='\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic void\nptrace_detach_clear_single_step_bridge'
i=oldnine.index(oldfree);j=kc.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__) && defined(MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)\n',i);z=kc.index(anchor,j); kchunk=kc[j:z]
assert s.count(kchunk)==1 and a.count(oldfree)==1
current=s.replace(kchunk,oldfree)
kill_start=a.index('static long\nptrace_detach_do_kill_bridge(');kill_end=a.index('\n}\n',kill_start)+3;kill=a[kill_start:kill_end]
int_start=a.index('void\ninterrupt_syscall(');int_end=a.index('\n}\n',int_start)+3;interrupt=a[int_start:int_end]
cases=[('kill',kill,4690,4697,'#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern long ptrace_detach_do_kill_bridge'),('interrupt',interrupt,5656,5663,'#if defined(MCKERNEL_RUST_F03_INTERRUPT_ARITY3_DEFINED) && defined(MCKERNEL_RUST_F03_INTERRUPT_ORIGIN_PROFILE_119) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(__x86_64__)\nextern void interrupt_syscall')]
def model(chunk,dispatch,selected,start,kind):
 sy={'MCKERNEL_RUST_F03_LEAF_CALLBACKS':selected,'__x86_64__':True,'MCKERNEL_RUST_F03_INTERRUPT_ARITY3_DEFINED':selected,'MCKERNEL_RUST_F03_INTERRUPT_ORIGIN_PROFILE_119':True,'MCKERNEL_RUST_SYSCALL_OFFLOAD':True if kind=='interrupt' else dispatch,'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':True,'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch}
 active=True;stack=[];n=start;events={}
 for line in chunk.splitlines():
  t=line.strip()
  if t.startswith('#if '):
   expr=re.sub(r'defined\((\w+)\)',lambda m:str(bool(sy.get(m.group(1),False))),t[4:]);assert re.fullmatch(r'[TrueFals &|!()]+',expr)
   cond=eval(expr.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
   stack.append((active,cond));active=active and cond
  elif t=='#else':parent,cond=stack[-1];active=parent and not cond
  elif t=='#endif':parent,_=stack.pop();active=parent
  elif active and t.startswith('#line '):n=int(t.split()[1]);continue
  elif active and t.startswith('extern '):events['selected_decl']=n
  elif active and ((kind=='kill' and t=='static long') or (kind=='interrupt' and t=='void')):events['fallback_start']=n
  if active and t.startswith('dkprintf("interrupt_syscall pid='):events['debug']=n
  n+=1
 assert not stack;events['next_line']=n;return events
observed={}
for kind,body,on,off,selector in cases:
 assert a.count(body)==current.count(body)==1
 pos=current.index(body);begin=current.rfind(selector,0,pos);assert begin>=0
 end=current.index('#endif\n',current.index('#line '+str(off+body.count('\n')-1)+'\n',pos))+len('#endif\n')
 chunk=current[begin:end]
 for d in (False,True):
  for selected in (False,True):
   start=on if d else off;e=model(chunk,d,selected,start,kind)
   assert e['next_line']==start+body.count('\n'),(kind,e)
   if selected:assert 'selected_decl' in e and 'fallback_start' not in e
   else:
    assert e['fallback_start']==start and 'selected_decl' not in e
    if kind=='interrupt':assert e['debug']==(5662 if d else 5669)
   observed[f'{kind}:dispatch={d}:selected={selected}']=e
 current=current[:begin]+body+current[end:]
assert current==a
oldpolicy=(family/'rust/syscall_policy.rs').read_text();policy=(out/'rust/syscall_policy.rs').read_text();assert policy.startswith(oldpolicy)
for f in ['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs']:
 assert (out/'rust'/f).read_bytes()==(family/'rust'/f).read_bytes()
assert (out/'rust/syscall_ptrace_detach_kfree.rs').read_bytes()==(kfree/'rust/syscall_ptrace_detach_kfree.rs').read_bytes()
killrs=(out/'rust/syscall_ptrace_detach_kill.rs').read_text();intrs=(out/'rust/syscall_interrupt_arity3.rs').read_text()
assert 'super::f06_ptrace_report_signal_kill(' in killrs and 'info.cast::<SigInfo>(), ptracecont' in killrs
assert 'unsafe extern "C" fn ptrace_detach_do_kill_bridge(' in killrs
assert 'thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,' in killrs and 'info: *const c_void, ptracecont: CInt' in killrs
assert 'MaybeUninit::<X86UserContext>::uninit()' in intrs and 'assume_init()' not in intrs
assert 'syscall_generic_forwarding(62, ctx_ptr)' in intrs
for field in ('rdi','rsi','rdx','r10','r8','r9'):
 assert intrs.count('write_volatile(addr_of_mut!((*ctx_ptr).gpr.'+field+')')==1
for field in ('r10','r8','r9'):
 assert 'write_volatile(addr_of_mut!((*ctx_ptr).gpr.'+field+'), 0);' in intrs
x86=Path('/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs').read_text()
for i,field in enumerate(('rdi','rsi','rdx','r10','r8','r9')):
 assert str(i)+' => read_volatile(&(*uctx).gpr.'+field+')' in x86
forward=oldpolicy[oldpolicy.index('pub unsafe extern "C" fn syscall_generic_forwarding('):oldpolicy.index('/// Owns the offload reply wait state machine')]
for i in range(6):assert 'ihk_mc_syscall_arg'+str(i)+'(ctx)' in forward
assert '(*ctx)' not in forward
assert 'f03_interrupt_origin_dispatch' in intrs and 'DEBUG_LINE: u32 = 5662;' in intrs and 'DEBUG_LINE: u32 = 5669;' in intrs
assert 'b"/src/kernel/syscall.c\\0"' in intrs and '#[link_section = "__verbose"]' in intrs
assert '__NR_kill = 62,' in Path('/home/holden/mckernel/kernel/include/syscall.h').read_text()
assert 'f03_interrupt_arity3_defined_candidate' not in (out/'CMakeLists.txt').read_text()
assert 'f03_ptrace_kfree_profile_119' not in (out/'CMakeLists.txt').read_text()
for fname in ['syscall_ptrace_detach_kfree.rs','syscall_ptrace_detach_kill.rs','syscall_interrupt_arity3.rs']:
 assert (out/'CMakeLists.txt').read_text().count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+fname+'"')==1
assert 'fn f06_ptrace_report_signal_kill(' in oldpolicy and 'fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong' in oldpolicy
assert a.count('static int ptrace_wakeup_sig(')==s.count('static int ptrace_wakeup_sig(')==1
assert a.count('static void\nptrace_wakeup_log_bridge(')==s.count('static void\nptrace_wakeup_log_bridge(')==1
def info(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SOURCE_ONLY_CONTRACTS_OPEN','checks':['reverse all three C changes to exact family C preimage','exact previously prepared tracked-free code and provenance reused','direct kill ABI, raw forwarding, signed conversion provider, original fallback','interrupt defined zero-unused-args proposal, original fallback and Rust-owned debug row','both selected/fallback branches and dispatch line origins modeled','termination family Rust code unchanged','held ptrace wakeup/logger C source unchanged','all new modules paired with dependencies; contract-gated candidates default off'],'model':observed,'patch':info(here/'QUEUE-C.PRIVATE-NOT-APPLIED.patch'),'postimages':[info(out/'syscall.c'),info(out/'CMakeLists.txt'),info(out/'rust/syscall_policy.rs')]+[info(out/'rust'/x) for x in ['syscall_ptrace_detach_kfree.rs','syscall_ptrace_detach_kill.rs','syscall_interrupt_arity3.rs']],'limitations':'Source-only. No preprocessor, compiler, link, runtime, actual 389 readback or retirement claim. Interrupt zero-unused-argument contract and exact C/Rust source-profile pairing require Root decision/review.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'patch':result['patch'],'checks':result['checks']},indent=2))
