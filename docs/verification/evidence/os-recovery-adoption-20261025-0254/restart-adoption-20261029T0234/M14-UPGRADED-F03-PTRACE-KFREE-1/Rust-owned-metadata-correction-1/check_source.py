from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent
root=here.parent.parent
base=root/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
out=here/'postimage'/'kernel'
record=root/'M14-CURRENT119-ACTUAL-ARTIFACT-QUALIFICATION-1'/'independent-review-1'/'INDEPENDENT-ACTUAL-CURRENT119-ARTIFACT-ACCEPTANCE.json'
accepted=json.loads(record.read_text())
commands=accepted['actual_commands']
c=next(x for x in commands if '/src/kernel/syscall.c' in x['argv'])
r=next(x for x in commands if '/src/kernel/rust/lib.rs' in x['argv'])
for f in ['-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS','-DMCKERNEL_RUST_SYSCALL_OFFLOAD','-DMCKERNEL_RUST_F03_DISPATCH_CONTEXT','-DMCKERNEL_RUST_F03_LEAF_CALLBACKS']:
 assert f in c['argv']
assert 'f03_dispatch_context_candidate' in r['argv'] and 'f03_leaf_callbacks_candidate' in r['argv']
assert c['argv'][-1]=='/src/kernel/syscall.c'
assert not any(x.startswith(('-ffile-prefix-map=', '-fmacro-prefix-map=', '-fdebug-prefix-map=')) for x in c['argv'])
original=(base/'syscall.c').read_text(); changed=(out/'syscall.c').read_text()
old='static void\nptrace_detach_kfree_bridge(void *ptr)\n{\n\tkfree_tracked(ptr, __FILE__, __LINE__);\n}\n'
a=original.index(old)
assert all(re.fullmatch(r'#line\s+\d+\s*', x) for x in original[:a].splitlines() if x.startswith('#line '))
b=changed.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__) && defined(MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)\n',a)
end='\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic void\nptrace_detach_clear_single_step_bridge'
cend=changed.index(end,b); dend=original.index(end,a)
assert original[:a]==changed[:b] and original[dend:]==changed[cend:]
chunk=changed[b:cend]
assert old in chunk
anchor='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line 4490\n#else\n#line 4499\n#endif\n'
assert original.count(anchor)==1
apos=original.index(anchor); anchor_line=original[:apos].count('\n')+1; original_call=original[:a].count('\n')+4
assert (anchor_line,original_call)==(4521,4690)
logical_original={True:4490+original_call-(anchor_line+2),False:4499+original_call-(anchor_line+4)}
assert logical_original=={True:4657,False:4664}
def fragment(dispatch,selected):
 symbols={'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':True,'MCKERNEL_RUST_F03_LEAF_CALLBACKS':True,'__x86_64__':True,'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119':selected,'MCKERNEL_RUST_SYSCALL_OFFLOAD':dispatch,'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch}
 active=True; stack=[]; logical=logical_original[dispatch]-3; events={}
 for line in chunk.splitlines():
  t=line.strip()
  if t.startswith('#if '):
   e=re.sub(r'defined\((\w+)\)',lambda m:str(bool(symbols.get(m.group(1),False))),t[4:]); assert re.fullmatch(r'[TrueFals &|!()]+',e)
   cond=eval(e.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
   stack.append((active,cond)); active=active and cond
  elif t=='#else': parent,cond=stack[-1];active=parent and not cond
  elif t=='#endif': parent,_=stack.pop();active=parent
  elif active and t.startswith('#line '): logical=int(t.split()[1]);continue
  elif active and 'extern void ptrace_detach_kfree_bridge' in line: events['extern']=logical
  elif active and 'kfree_tracked(ptr, __FILE__, __LINE__)' in line: events['fallback_call']=logical
  logical+=1
 assert not stack
 events['next_line']=logical
 return events
observed={}
for dispatch in (False,True):
 for selected in (False,True):
  events=fragment(dispatch,selected); expected=logical_original[dispatch]
  assert events['next_line']==expected+2
  if selected: assert 'extern' in events and 'fallback_call' not in events
  else: assert events.get('fallback_call')==expected and 'extern' not in events
  observed[f'dispatch={dispatch},selected={selected}']=events
leaf=(out/'rust/syscall_ptrace_detach_kfree.rs').read_text()
assert 'b"/src/kernel/syscall.c\\0"' in leaf
assert '#[cfg(f03_ptrace_kfree_dispatch_origin)]\nconst SOURCE_LINE: c_int = 4657;' in leaf
assert '#[cfg(not(f03_ptrace_kfree_dispatch_origin))]\nconst SOURCE_LINE: c_int = 4664;' in leaf
assert re.search(r'pub unsafe extern "C" fn ptrace_detach_kfree_bridge\(ptr: \*mut c_void\)',leaf)
assert leaf.count('crate::mem_helpers::kfree_tracked(')==1
assert re.search(r'kfree_tracked\(\s*ptr, SOURCE_FILE\.as_ptr\(\)\.cast_mut\(\)\.cast\(\), SOURCE_LINE,\s*\)',leaf)
assert 'if ' not in leaf and 'file!(' not in leaf and 'line!(' not in leaf
assert original.count('\n\t\t\tptrace_detach_kfree_bridge,')==changed.count('\n\t\t\tptrace_detach_kfree_bridge,')==2
oldpolicy=(base/'rust/syscall_policy.rs').read_text();newpolicy=(out/'rust/syscall_policy.rs').read_text()
assert newpolicy.startswith(oldpolicy) and 'f03_ptrace_kfree_profile_119' in newpolicy[len(oldpolicy):]
cmake=(out/'CMakeLists.txt').read_text()
assert cmake.count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"')==1
assert 'f03_ptrace_kfree_profile_119' not in cmake and 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119' not in cmake
assert 'f03_ptrace_detach_kfree_file_v1' not in changed and 'f03_ptrace_detach_kfree_line_v1' not in changed
mem=Path('/home/holden/mckernel/kernel/rust/mem_helpers.rs').read_text()
assert re.search(r'pub unsafe extern "C" fn kfree_tracked\(ptr: \*mut c_void, file: \*mut i8, line: CInt\)\s*\{\s*unsafe\s*\{\s*_kfree\(ptr, file, line\);',mem)
def digest(p):
 v=p.read_bytes();return {'path':str(p),'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_ONLY_INERT_UNTIL_PROFILE_BOUND','retained119_record':digest(record),'source_profile':{'c_source_argument':c['argv'][-1],'recorded_dispatch_flags':'present','recorded_line_model':4657,'alternate_dispatch_line_model':4664,'alternate':'not independently profile-qualified'},'line_model':observed,'checks':['original prefix and suffix and exact OFF body','four conditional logical-line paths and following-line reset','two unchanged callback consumers','Rust C ABI, static Rust byte-string, unconditional tracked-free forwarding','profile selectors default OFF','existing allocator source signature'], 'files':[digest(here/'RUST-METADATA.PRIVATE-NOT-APPLIED.patch'),digest(out/'syscall.c'),digest(out/'rust/syscall_ptrace_detach_kfree.rs'),digest(out/'rust/syscall_policy.rs'),digest(out/'CMakeLists.txt')], 'limitations':'No preprocessor/compiler/link/native or retirement evidence. Explicit paired profile, actual selected C path/flags and preprocessor proof required before selection.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
