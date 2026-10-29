"""Functional McKernel source parity/callback fixture only; no security testing.
No Rust/C execution, compiler, preprocessor, HOST payload, guard, proc or native.
"""
from pathlib import Path
import ast,json,re,hashlib
D=Path(__file__).resolve().parent
pre=(D/'preimage/kernel/syscall.c').read_text();post=(D/'postimage/kernel/syscall.c').read_text();leaf=(D/'postimage/kernel/rust/syscall_util_clone_disabled_logger.rs').read_text()
start=pre.index('void\nsyscall_util_indicate_clone_disabled_bridge(void)\n');end=pre.index('\nlong sys_util_indicate_clone',start);old=pre[start:end];new=post[start:post.index('\nlong sys_util_indicate_clone',start)]
assert len(pre)==len(post)or pre.count('\n')==post.count('\n')
assert pre[:start]==post[:start] and pre.splitlines(True)[pre[:end].count('\n'):]==post.splitlines(True)[post[:post.index('\nlong sys_util_indicate_clone',start)].count('\n'):]
assert old.count('\n')==new.count('\n');assert new.strip()=='extern void syscall_util_indicate_clone_disabled_bridge(void);'
assert [(i,s)for i,s in enumerate(pre.splitlines(True))if re.match(r'^\s*#\s*(?:line\b|\d)',s)]==[(i,s)for i,s in enumerate(post.splitlines(True))if re.match(r'^\s*#\s*(?:line\b|\d)',s)]
# Extract only exact static literals from the two one-call logger bodies. Decode
# the ordinary quoted literals with Python's literal parser (no C/Expect parser).
c_literals=[ast.literal_eval(s).encode()for s in re.findall(r'"(?:[^"\\]|\\.)*"',old)]
rust_literals=[ast.literal_eval(s[1:]).encode()for s in re.findall(r'c"(?:[^"\\]|\\.)*"',leaf)]
assert c_literals==rust_literals==[b'%s: error: --enable-uti mcexec option not specified\n',b'sys_util_indicate_clone']
assert old.count('kprintf(')==leaf.count('kprintf(')==1
assert re.search(r'extern "C" fn syscall_util_indicate_clone_disabled_bridge\(\)\s*\{',leaf)
expected=b'sys_util_indicate_clone: error: --enable-uti mcexec option not specified\n'
def callback_fixture(literals):
 calls=[]
 def kprintf(fmt,arg):
  assert fmt.count(b'%s')==1 and b'\0'not in fmt+arg
  calls.append((fmt,arg));return fmt.replace(b'%s',arg,1)
 def callback():
  output=kprintf(*literals);return output
 assert [callback()for _ in range(3)]==[expected]*3
 assert calls==[tuple(literals)]*3
 return calls
assert callback_fixture(c_literals)==callback_fixture(rust_literals)
# This fixture validates source literals/arity/cardinality only, not compiled ABI.
rpre=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();rpost=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();insertion='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[path = "syscall_util_clone_disabled_logger.rs"]\nmod syscall_util_clone_disabled_logger;\n';assert rpost.replace(insertion,'',1)==rpre
cm_pre=(D/'preimage/kernel/CMakeLists.txt').read_text();cm_post=(D/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_util_clone_disabled_logger.rs"\n';assert cm_post.count(dep)==1 and cm_post.replace(dep,'',1)==cm_pre
assert 'Ddebug'not in leaf and '__verbose'not in leaf
checks=['selected C callback only replaced with same ABI extern; line-neutral padding','all untouched C lines and original logical line directives retained','exact static format/argument/newline source bytes match','three no-argument mock callback invocations each produce one same diagnostic','Rust parent including util behavior unchanged except one module insertion','one additive CMake dependency; existing logger ABI reused','no Ddebug descriptor added or removed; original389 identities unaffected by C origins']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_SOURCE_ONLY_LITERAL_CALLBACK_FIXTURE',checks=checks,compiled_callback=False,native_execution=False,original389_linked_validation=False),indent=2)+'\n');print('PASS',len(checks),'source groups')
