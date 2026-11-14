from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent;base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
orig=(base/'syscall.c').read_text();policy=(base/'rust/syscall_policy.rs').read_text();cmake=(base/'CMakeLists.txt').read_text()
cases=[
 ('wakeup','ptrace_detach_wakeup_bridge','syscall_ptrace_detach_wakeup.rs','static void\nptrace_detach_wakeup_bridge(void *thread, int valid_states)\n{\n\tsched_wakeup_thread((struct thread *)thread, valid_states);\n}\n',(4731,4698,4705)),
 ('terminate_mcexec','terminate_mcexec_do_syscall_bridge','syscall_terminate_mcexec_forward.rs','static long\nterminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu)\n{\n\treturn do_syscall(request, cpu);\n}\n',(5208,5138,5145)),
 ('perf_open','perf_event_open_do_syscall_bridge','syscall_perf_open_forward.rs','static long\nperf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu)\n{\n\treturn do_syscall(request, cpu);\n}\n',(21448,21115,21115))]
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;' in policy
assert 'typedef void (*ptrace_wakeup_thread_fn_t)(void *thread, int valid_states);' in orig
assert 'long do_syscall(struct syscall_request *req, int cpu)\n{' in orig
assert 'typedef long (*terminate_mcexec_syscall_fn_t)(struct syscall_request *request,' in orig
assert 'typedef long (*perf_open_syscall_fn_t)(struct syscall_request *request,' in orig
assert 'type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;' in policy
scheduler=Path('/home/holden/mckernel/kernel/rust/sched_helpers.rs').read_text()
assert re.search(r'pub unsafe extern "C" fn sched_wakeup_thread\(thread: \*mut Thread, valid_states: CInt\) -> CInt',scheduler)
def info(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def model(chunk, dispatch, selected, initial):
 sy={'MCKERNEL_RUST_F03_LEAF_CALLBACKS':selected,'__x86_64__':True,'MCKERNEL_RUST_SYSCALL_OFFLOAD':dispatch,'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':dispatch,'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch}
 active=True;stack=[];n=initial;e={}
 for line in chunk.splitlines():
  t=line.strip()
  if t.startswith('#if '):
   ex=re.sub(r'defined\((\w+)\)',lambda m:str(bool(sy.get(m.group(1),False))),t[4:]);assert re.fullmatch(r'[TrueFals &|!()]+',ex)
   cond=eval(ex.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
   stack.append((active,cond));active=active and cond
  elif t=='#else': parent,cond=stack[-1];active=parent and not cond
  elif t=='#endif': parent,_=stack.pop();active=parent
  elif active and t.startswith('#line '):n=int(t.split()[1]);continue
  elif active and t.startswith('extern '):e['selected_decl']=n
  elif active and t.startswith('static '):e['fallback_start']=n
  elif active and ('return do_syscall(request, cpu);' in t or 'sched_wakeup_thread((struct thread *)thread, valid_states);' in t):e['fallback_call']=n
  n+=1
 assert not stack;e['next_line']=n;return e
results=[]
for directory,name,filename,old,(physical,on,off) in cases:
 folder=here/directory;out=folder/'postimage'/'kernel';s=(out/'syscall.c').read_text();a=orig.index(old);assert orig[:a].count('\n')+1==physical
 b=s.index('#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern ',a);oldend=a+len(old)
 assert s[:b]==orig[:a]
 # Identify exact preserved suffix by its full bytes, then examine only the delta.
 suffix=orig[oldend:];assert s.endswith(suffix);chunk=s[b:len(s)-len(suffix)]
 assert chunk.count(old)==1
 if directory=='wakeup':
  assert orig.splitlines()[4521]=='#line 4490' and orig.splitlines()[4523]=='#line 4499'
  assert (4490+physical-4523,4499+physical-4525)==(on,off)
 elif directory=='terminate_mcexec':
  assert orig.splitlines()[5144]=='#line 5076' and orig.splitlines()[5146]=='#line 5085'
  assert (5076+physical-5146,5085+physical-5148)==(on,off)
 else:
  assert orig.splitlines()[21444]=='#line 21113' and 21113+physical-21446==on
  assert suffix.startswith('#endif /*ENABLE_PERF*/\n#ifdef ENABLE_PERF\n#line 21118')
  guards=[]
  for line in orig[:a].splitlines():
   t=line.strip()
   if t.startswith(('#if ', '#ifdef ', '#ifndef ')): guards.append(t)
   elif t.startswith('#endif'): guards.pop()
   elif t.startswith(('#else', '#elif')): guards[-1] += ' THEN ' + t
  assert guards==['#ifdef ENABLE_PERF']
 observations={}
 for dispatch in [False,True]:
  for selected in [False,True]:
   startline=on if dispatch else off;e=model(chunk,dispatch,selected,startline)
   assert e['next_line']==startline+5,(name,e)
   if selected: assert 'selected_decl' in e and 'fallback_start' not in e and 'fallback_call' not in e
   else: assert e.get('fallback_start')==startline and e.get('fallback_call')==startline+3 and 'selected_decl' not in e
   observations[f'dispatch={dispatch},selected={selected}']=e
 rust=(out/'rust'/filename).read_text();p=(out/'rust/syscall_policy.rs').read_text();assert p.startswith(policy)
 extra=', enable_perf' if directory=='perf_open' else ''
 assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"'+extra+'))]' in p[len(policy):]
 assert (out/'CMakeLists.txt').read_text().count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+filename+'"')==1
 assert '"--cfg" "f03_leaf_callbacks_candidate"' in cmake
 if directory=='wakeup':
  assert re.search(r'pub unsafe extern "C" fn ptrace_detach_wakeup_bridge\(thread: \*mut c_void, valid_states: c_int\)',rust)
  assert rust.count('crate::sched_helpers::sched_wakeup_thread(thread.cast(), valid_states)')==1 and 'let _ = unsafe' in rust
  assert orig.count('\n\t\t\tptrace_detach_wakeup_bridge')==s.count('\n\t\t\tptrace_detach_wakeup_bridge')==2
 else:
  assert re.search(r'pub unsafe extern "C" fn '+name+r'\(request: \*mut SyscallRequest, cpu: CInt\) -> CLong',rust)
  assert rust.count('super::do_syscall(request, cpu)')==1
  suffix_token = ');' if directory=='terminate_mcexec' else ','
  assert orig.count(name+suffix_token)==s.count(name+suffix_token)==1
  if directory=='perf_open':assert '"--cfg" "enable_perf"' in cmake
 assert 'if ' not in rust and all(x not in old for x in ('__FILE__','__LINE__','dkprintf','kprintf','__verbose'))
 result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_ONLY','symbol':name,'checks':['byte-identical C prefix/suffix and OFF fallback','both dispatch variants modeled, including original and following logical lines','Rust/C selector pairing and original callback users','matching raw C/Rust pointer/integer/return signature','one original provider call, argument order, no guard','no target C debug/metadata producer']+(['ENABLE_PERF enclosing C boundary preserved and matching Rust cfg'] if directory=='perf_open' else []),'line_model':observations,'preimage':info(base/'syscall.c'),'patch':info(folder/'PRIVATE-NOT-APPLIED.patch'),'postimage':[info(out/'syscall.c'),info(out/'rust'/filename),info(out/'rust/syscall_policy.rs'),info(out/'CMakeLists.txt')],'limitations':'Source/model only; no real preprocessor, compiler, link, native, metadata readback, or retirement acceptance. Existing callee and all its behavior remain open.'}
 (folder/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');results.append({'symbol':name,'status':result['status'],'patch':result['patch'],'line_model':observations})
print(json.dumps(results,indent=2))
