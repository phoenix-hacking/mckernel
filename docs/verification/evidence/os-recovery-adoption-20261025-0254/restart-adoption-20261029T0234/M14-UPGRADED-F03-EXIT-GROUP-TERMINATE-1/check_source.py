from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent
base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
out=here/'postimage'/'kernel'
orig=(base/'syscall.c').read_text(); new=(out/'syscall.c').read_text()
old='void\nexit_group_terminate_bridge(int status, int group)\n{\n\tterminate(status, group);\n}\n'
a=orig.index(old)
start='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern void exit_group_terminate_bridge'
b=new.index(start,a)
end='\n#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern int exit_group_current_pid_bridge'
c=new.index(end,b); d=orig.index(end,a)
assert orig[:a]==new[:b] and orig[d:]==new[c:]
chunk=new[b:c]
assert chunk.count(old)==1
anchor='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line 5076\n#else\n#line 5085\n#endif\n'
assert orig.count(anchor)==1
pos=orig.index(anchor); anchor_line=orig[:pos].count('\n')+1; start_line=orig[:a].count('\n')+1
assert (anchor_line,start_line)==(5144,5751)
logical={True:5076+start_line-(anchor_line+2),False:5085+start_line-(anchor_line+4)}
assert logical=={True:5681,False:5688}
def fragment(dispatch,selected):
 symbols={'MCKERNEL_RUST_F03_LEAF_CALLBACKS':selected,'__x86_64__':True,'MCKERNEL_RUST_SYSCALL_OFFLOAD':dispatch,'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':dispatch,'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch}
 active=True;stack=[];ln=logical[dispatch];events={}
 for line in chunk.splitlines():
  x=line.strip()
  if x.startswith('#if '):
   e=re.sub(r'defined\((\w+)\)',lambda m:str(bool(symbols.get(m.group(1),False))),x[4:]);assert re.fullmatch(r'[TrueFals &|!()]+',e)
   cond=eval(e.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
   stack.append((active,cond));active=active and cond
  elif x=='#else': parent,cond=stack[-1];active=parent and not cond
  elif x=='#endif': parent,_=stack.pop();active=parent
  elif active and x.startswith('#line '):ln=int(x.split()[1]);continue
  elif active and x.startswith('extern void exit_group_terminate_bridge'):events['external_declaration']=ln
  elif active and x=='void':events['fallback_start']=ln
  elif active and x=='terminate(status, group);':events['fallback_call']=ln
  ln+=1
 assert not stack
 events['next_line']=ln;return events
observed={}
for dispatch in (False,True):
 for selected in (False,True):
  e=fragment(dispatch,selected); assert e['next_line']==logical[dispatch]+5
  if selected: assert 'external_declaration' in e and 'fallback_start' not in e and 'fallback_call' not in e
  else: assert e['fallback_start']==logical[dispatch] and e['fallback_call']==logical[dispatch]+3 and 'external_declaration' not in e
  observed[f'dispatch={dispatch},selected={selected}']=e
assert 'typedef void (*syscall_terminate_fn_t)(int status, int group);' in orig
assert 'void terminate(int rc, int sig)\n{' in orig
assert 'extern void terminate(int, int);' in Path('/home/holden/mckernel/kernel/include/syscall.h').read_text()
policy=(base/'rust/syscall_policy.rs').read_text(); updated=(out/'rust/syscall_policy.rs').read_text()
assert 'type SyscallTerminateFn = unsafe extern "C" fn(CInt, CInt);' in policy
assert 'fn exit_group_terminate_bridge(status: CInt, group: CInt);' in policy
assert '#[link_name = "terminate"]\n    fn f03_do_exit_existing_terminate_v2(status: CInt, signal: CInt);' in policy
assert updated.startswith(policy)
assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]' in updated[len(policy):]
leaf=(out/'rust/syscall_exit_group_terminate.rs').read_text()
assert re.search(r'unsafe extern "C" \{\s*fn terminate\(status: c_int, group: c_int\);\s*\}',leaf)
assert re.search(r'pub unsafe extern "C" fn exit_group_terminate_bridge\(status: c_int, group: c_int\)\s*\{\s*//[^\n]*\n\s*//[^\n]*\n\s*unsafe \{ terminate\(status, group\) \};\s*\}',leaf)
assert leaf.count('terminate(status, group)')==1 and 'if ' not in leaf
cmake=(out/'CMakeLists.txt').read_text()
assert cmake.count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_terminate.rs"')==1
assert '"--cfg" "f03_leaf_callbacks_candidate"' in cmake and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS' in cmake
assert orig.count('exit_group_log_bridge, exit_group_terminate_bridge')==new.count('exit_group_log_bridge, exit_group_terminate_bridge')==1
assert 'Some(exit_group_terminate_bridge)' in policy
assert '#line' not in old and not any(x in old for x in ('__FILE__','__LINE__','dkprintf','kprintf','__verbose'))
def info(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_ONLY','checks':['C original prefix and suffix and byte-identical OFF fallback','selected/OFF conditional and modeled original and downstream line origins in both dispatch cases','C and Rust callback/provider ABI source declarations','same argument order and one unconditional void provider call','preserved callback users and Rust parent prefix','paired existing leaf/x86 cfg and CMake dependency','no target C debug/metadata producer'], 'line_model':observed,'inputs':[info(base/'syscall.c'),info(base/'rust/syscall_policy.rs'),info(Path('/home/holden/mckernel/kernel/include/syscall.h'))], 'files':[info(here/'EXIT-GROUP-TERMINATE.PRIVATE-NOT-APPLIED.patch'),info(out/'syscall.c'),info(out/'rust/syscall_policy.rs'),info(out/'rust/syscall_exit_group_terminate.rs'),info(out/'CMakeLists.txt')], 'limitations':'Pure source checks only; selected C terminate body/dependency remains open. Actual preprocessing, 389 metadata readback, compile/link, independent review and native proof remain open.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
