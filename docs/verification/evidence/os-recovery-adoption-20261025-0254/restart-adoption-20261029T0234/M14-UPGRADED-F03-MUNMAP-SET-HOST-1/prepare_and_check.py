#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Create and check a source-only alias against the frozen callback and reviewed provider.
"""
import difflib
import hashlib
import json
import re
from pathlib import Path

here = Path(__file__).resolve().parent
base = here.parent
frozen = base / 'M14-PRIVATE-NINE-LEAF-BATCH-1/preimage/kernel/syscall.c'
provider = base / 'M14-PRIVATE-MPROTECT-HOST-VMA-BRIDGE-1'
pre = frozen.read_text()
old = '''static int
do_munmap_set_host_bridge(unsigned long addr, size_t len, int prot,
		int holding_lock)
{
	return set_host_vma(addr, len, prot, holding_lock);
}'''
new = '''#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
extern int mprotect_set_host_vma_bridge(unsigned long start, size_t len, int prot, int holding_lock);
#define do_munmap_set_host_bridge mprotect_set_host_vma_bridge
#else
static int do_munmap_set_host_bridge(unsigned long addr, size_t len, int prot, int holding_lock) { return set_host_vma(addr, len, prot, holding_lock); }
#endif'''
assert pre.count(old) == 1
assert old.count('\n') == new.count('\n')
post = pre.replace(old, new)
assert pre.split(old)[0] == post.split(new)[0]
assert pre.split(old)[1] == post.split(new)[1]
assert len(pre.splitlines()) == len(post.splitlines())
tokens = lambda s: re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]', s)
assert tokens(old) == tokens(new.split('#else\n',1)[1].split('\n#endif',1)[0])
assert 'typedef int (*mprotect_set_host_vma_fn_t)(unsigned long start,\n\t\tsize_t len, int prot, int holding_lock);' in pre
assert '.set_host = do_munmap_set_host_bridge,' in pre
assert 'do_munmap_clear_host_bridge, do_munmap_set_host_bridge,' in pre
rust = (provider/'postimage/kernel/rust/syscall_mprotect_host_vma.rs').read_text()
assert 'type HostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;' in rust
assert 'const _: HostVmaFn = mprotect_set_host_vma_bridge;' in rust
assert '#[no_mangle]\npub(super) unsafe extern "C" fn mprotect_set_host_vma_bridge(' in rust
for clause in ['(*get_this_cpu_local_var()).current', 'ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);', 'ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);', 'ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);', 'set_host_vma_body_result(start, len, prot, holding_lock)']:
    assert clause in rust
positions = [rust.index(s) for s in ['(*get_this_cpu_local_var()).current', 'ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);', 'ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);', 'ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);', 'set_host_vma_body_result(start, len, prot, holding_lock)']]
assert positions == sorted(positions)
provider_patch = (provider/'MPROTECT-HOST-VMA.PRIVATE-NOT-APPLIED.patch').read_text()
assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]' in provider_patch
assert '#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)' in provider_patch
review = json.loads((provider/'independent-source-review-1/REVIEW.ACTUAL.json').read_text())
assert review['decision'] == 'PASS_SOURCE_FULL_MPROTECT_REACHABLE_PREFIX_AND_UNSAFE_ABI_CONTRACT'
assert hashlib.sha256(rust.encode()).hexdigest() == review['leaf']['sha256']
assert hashlib.sha256(provider_patch.encode()).hexdigest() == review['patch']['sha256']
prepath = here/'preimage/kernel/syscall.c'
postpath = here/'postimage/kernel/syscall.c'
prepath.parent.mkdir(parents=True, exist_ok=True)
postpath.parent.mkdir(parents=True, exist_ok=True)
prepath.write_text(pre)
postpath.write_text(post)
patch = ''.join(difflib.unified_diff(pre.splitlines(keepends=True), post.splitlines(keepends=True), fromfile='a/kernel/syscall.c', tofile='b/kernel/syscall.c'))
(here/'MUNMAP-SET-HOST.PRIVATE-NOT-APPLIED.patch').write_text(patch)
def ref(p):
    b=p.read_bytes()
    return {'path':str(p), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
result = {
 'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 'status':'PASS_SOURCE_ONLY_ALIAS_AND_PROVENANCE',
 'symbol':'do_munmap_set_host_bridge',
 'source_checks':['single frozen target and unchanged prefix/suffix', 'same line count; fallback tokens match original', 'callback typedef and both binding uses retained', 'Rust C ABI assertion and no_mangle provider match C signature', 'reviewed provider exact SHA256 and reachable prefix order', 'matching C/Rust x86 leaf selection predicates'],
 'frozen_source':ref(frozen), 'preimage':ref(prepath), 'postimage':ref(postpath), 'patch':ref(here/'MUNMAP-SET-HOST.PRIVATE-NOT-APPLIED.patch'),
 'provider_patch':ref(provider/'MPROTECT-HOST-VMA.PRIVATE-NOT-APPLIED.patch'), 'provider_leaf':ref(provider/'postimage/kernel/rust/syscall_mprotect_host_vma.rs'), 'provider_review':ref(provider/'independent-source-review-1/REVIEW.ACTUAL.json'),
 'dependency':'Compose with the complete reviewed full-prefix mprotect provider patch under its matching selection predicate; this alias alone cannot link the selected configuration.',
 'limits':'Source-only; no compilation, linking, callback execution, native proof, C retirement or runtime authorization.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'])
