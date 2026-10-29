from pathlib import Path
import hashlib, json, re

here = Path(__file__).resolve().parent
base = here.parent / 'M14-PRIVATE-NINE-LEAF-BATCH-1' / 'postimage' / 'kernel'
out = here / 'postimage' / 'kernel'
original = (base/'syscall.c').read_text()
changed = (out/'syscall.c').read_text()
start = 'static void\nptrace_detach_kfree_bridge(void *ptr)\n{\n\tkfree_tracked(ptr, __FILE__, __LINE__);\n}\n'
a = original.index(start)
b = changed.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\n', a)
end_marker = '\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic void\nptrace_detach_clear_single_step_bridge'
c = changed.index(end_marker, b)
d = original.index(end_marker, a)
assert original[:a] == changed[:b] and original[d:] == changed[c:]
chunk=changed[b:c]
assert start in chunk
anchor = '#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line 4490\n#else\n#line 4499\n#endif\n'
assert original.count(anchor)==1
anchor_start=original.index(anchor)
anchor_lines=original[:anchor_start].count('\n')+1
original_call_line=original[:a].count('\n')+4
assert (anchor_lines, original_call_line)==(4521,4690)
# A #line directive maps the following physical line even in skipped blocks.
logical_original = {True:4490 + (original_call_line-(anchor_lines+2)), False:4499+(original_call_line-(anchor_lines+4))}
assert logical_original == {True:4657,False:4664}

def fragment(dispatch, selected):
    symbols={'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS':selected, 'MCKERNEL_RUST_F03_LEAF_CALLBACKS':selected, '__x86_64__':selected, 'MCKERNEL_RUST_SYSCALL_OFFLOAD':dispatch, 'MCKERNEL_RUST_F03_DISPATCH_CONTEXT':dispatch}
    # Dispatch can be enabled while selection is disabled (e.g., non-x86).
    if dispatch: symbols['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS']=True
    if not selected: symbols['__x86_64__']=False
    active=True; stack=[]; logical=logical_original[dispatch]-3; events={}
    for line in chunk.splitlines():
        stripped=line.strip()
        if stripped.startswith('#if '):
            expr=stripped[4:]
            expr=re.sub(r'defined\((\w+)\)',lambda m:str(bool(symbols.get(m.group(1),False))),expr)
            assert re.fullmatch(r'[TrueFals &|!()]+',expr)
            cond=eval(expr.replace('&&',' and ').replace('||',' or ').replace('!',' not '),{'__builtins__':{}},{})
            stack.append((active,cond)); active=active and cond
        elif stripped == '#else':
            parent,cond=stack[-1]; active=parent and not cond
        elif stripped == '#endif':
            parent,_=stack.pop(); active=parent
        elif active and stripped.startswith('#line '):
            logical=int(stripped.split()[1]); continue
        elif active:
            if 'const char f03_ptrace_detach_kfree_file_v1[]' in line: events['metadata']=logical
            if 'kfree_tracked(ptr, __FILE__, __LINE__)' in line: events['fallback_call']=logical
        logical+=1
    assert not stack
    events['next_line']=logical
    return events

observed={}
for dispatch in (False,True):
    for selected in (False,True):
        events=fragment(dispatch,selected)
        expected=logical_original[dispatch]
        assert events['next_line']==expected+2, events
        assert events.get('metadata' if selected else 'fallback_call')==expected,events
        assert len(events)==2,events
        observed[f'dispatch={dispatch},selected={selected}']=events
leaf=(out/'rust/syscall_ptrace_detach_kfree.rs').read_text()
assert re.search(r'pub unsafe extern "C" fn ptrace_detach_kfree_bridge\(ptr: \*mut c_void\)',leaf)
assert leaf.count('crate::mem_helpers::kfree_tracked(')==1
assert re.search(r'kfree_tracked\(\s*ptr,\s*addr_of!\(f03_ptrace_detach_kfree_file_v1\)\.cast_mut\(\),\s*f03_ptrace_detach_kfree_line_v1,\s*\)',leaf)
assert 'if ' not in leaf and 'file!(' not in leaf and 'line!(' not in leaf
assert original.count('\n\t\t\tptrace_detach_kfree_bridge,') == changed.count('\n\t\t\tptrace_detach_kfree_bridge,') == 2
oldpolicy=(base/'rust/syscall_policy.rs').read_text(); newpolicy=(out/'rust/syscall_policy.rs').read_text()
assert newpolicy.startswith(oldpolicy) and newpolicy[len(oldpolicy):].count('mod syscall_ptrace_detach_kfree;')==1
assert (out/'CMakeLists.txt').read_text().count('"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"')==1
mem=Path('/home/holden/mckernel/kernel/rust/mem_helpers.rs').read_text()
assert re.search(r'pub unsafe extern "C" fn kfree_tracked\(ptr: \*mut c_void, file: \*mut i8, line: CInt\)\s*\{\s*unsafe\s*\{\s*_kfree\(ptr, file, line\);',mem)
def digest(path):
    data=path.read_bytes(); return {'path':str(path), 'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status':'PASS_SOURCE_ONLY', 'checks':['unchanged prefix/suffix and exact C fallback','C conditional logical source origin and downstream logical position, four configurations','two unchanged callback consumers','Rust C ABI and single unconditional tracked-free forwarding','paired cfg and CMake dependency','existing tracked allocator forwarding source'], 'origin':observed, 'files':[digest(here/'PTRACE-KFREE.PRIVATE-NOT-APPLIED.patch'),digest(out/'syscall.c'),digest(out/'rust/syscall_policy.rs'),digest(out/'rust/syscall_ptrace_detach_kfree.rs'),digest(out/'CMakeLists.txt'),digest(Path('/home/holden/mckernel/kernel/rust/mem_helpers.rs'))], 'limitations':'Source checks only; no compiler/preprocessor/link/native/behavior/retirement acceptance.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
